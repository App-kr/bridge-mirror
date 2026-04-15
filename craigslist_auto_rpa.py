"""
BRIDGE Craigslist Auto RPA
===========================
master.db jobs → 광고 생성 → Seoul Craigslist 자동 게시

보안 정책:
  - 광고에 업체명·연락처·이메일·정확한 주소 절대 미포함
  - internal_notes 완전 차단 (업체 전화/메일 포함)
  - 노출 허용: 도시명, 급여, 근무시간, 연령대, 복지(일반)
  - 카카오톡 ID 완전 차단
  - 파일 무결성 체크 (해킹 시도 차단)

다중 계정:
  python craigslist_auto_rpa.py --account account1 --limit 10
  python craigslist_auto_rpa.py --account account2 --headless --limit 10

실행:
  python craigslist_auto_rpa.py --dry-run          # 광고 텍스트 출력만
  python craigslist_auto_rpa.py --generate         # ad_posts draft 저장만
  python craigslist_auto_rpa.py --limit 3          # 최대 3건 실제 게시
  python craigslist_auto_rpa.py --job-code Job.1633 --limit 1
"""

import argparse
import hashlib
import io
import json
import logging
import os
import random
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── 경로 설정 (cross-platform) ───────────────────────────────────────────────
BASE_DIR = Path(os.getenv("BRIDGE_APP_DIR", str(Path(__file__).resolve().parent)))
DB_PATH  = Path(os.getenv("BRIDGE_DB_PATH", str(BASE_DIR / "data" / "master.db")))

# DB fallback: data/master.db 없으면 루트의 master.db (기존 Windows 구조 호환)
if not DB_PATH.exists() and (BASE_DIR / "master.db").exists():
    DB_PATH = BASE_DIR / "master.db"

SS_DIR   = BASE_DIR / "screenshots" / "craigslist"
SS_DIR.mkdir(parents=True, exist_ok=True)
LOCK_FILE = BASE_DIR / "logs" / ".rpa_running.lock"
# 사진 폴더: 환경변수 CRAIG_IMAGE_DIR 또는 기본 images/
_IMG_DIR = Path(os.getenv("CRAIG_IMAGE_DIR", str(BASE_DIR / "images")))
_IMG_DIR.mkdir(parents=True, exist_ok=True)
AD_IMAGE = _IMG_DIR / os.getenv("CRAIG_IMAGE_FILE", "B.jpg")

# ── 구조화 에러 로그 (rpa_error.log) ─────────────────────────────────────────
_LOG_DIR = BASE_DIR / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_err_logger = logging.getLogger("rpa_errors")
_err_logger.setLevel(logging.INFO)
_err_handler = logging.FileHandler(str(_LOG_DIR / "rpa_error.log"), encoding="utf-8")
_err_handler.setFormatter(
    logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
)
_err_logger.addHandler(_err_handler)


def _log_event(level: str, job_code: str, stage: str, message: str, extra: dict | None = None):
    """rpa_error.log 에 JSON 구조화 로그 기록."""
    payload = {
        "job_code": job_code,
        "stage":    stage,
        "message":  message,
    }
    if extra:
        payload.update(extra)
    line = json.dumps(payload, ensure_ascii=False)
    if level == "error":
        _err_logger.error(line)
    elif level == "warn":
        _err_logger.warning(line)
    else:
        _err_logger.info(line)

# ── 계정별 .env 로딩 ─────────────────────────────────────────────────────────
# --account account1 → account1.env 로딩
# 미지정 시 기본 .env 사용
def _load_account_env(account_id: str | None = None):
    """계정별 .env 파일 로딩. account_id 없으면 기본 .env."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    if account_id:
        acct_env = Path(__file__).resolve().parent / f"{account_id}.env"
        if acct_env.exists():
            load_dotenv(acct_env, override=True)
            print(f"  [ENV] {account_id}.env 로딩 완료")
            return
        else:
            print(f"  [WARN] {acct_env} 없음 → 기본 .env 사용")

    for _env_candidate in [
        BASE_DIR / ".env",
        BASE_DIR / "backend" / ".env",
        Path(__file__).resolve().parent / ".env",
    ]:
        if _env_candidate.exists():
            load_dotenv(_env_candidate, override=True)
            break

# 초기 로딩 (--account 파싱 전이므로 기본 .env)
_load_account_env()


# ── 파일 무결성 체크 (해킹 시도 차단) ────────────────────────────────────────
_INTEGRITY_FILES = [
    Path(__file__).resolve(),                          # craigslist_auto_rpa.py
    Path(__file__).resolve().parent / "rpa_overlay.py",
]
_HASH_STORE = Path(__file__).resolve().parent / "logs" / ".file_hashes.json"


def _compute_hash(filepath: Path) -> str:
    """SHA-256 해시 계산."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def integrity_init():
    """현재 파일들의 해시를 저장 (최초 실행 또는 업데이트 후)."""
    hashes = {}
    for fp in _INTEGRITY_FILES:
        if fp.exists():
            hashes[str(fp)] = _compute_hash(fp)
    _HASH_STORE.write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    print(f"  [INTEGRITY] 해시 저장 완료: {len(hashes)}개 파일")


def integrity_check() -> bool:
    """파일 무결성 검증. 변조 감지 시 False 반환."""
    if not _HASH_STORE.exists():
        print("  [INTEGRITY] 해시 파일 없음 → 최초 초기화")
        integrity_init()
        return True

    stored = json.loads(_HASH_STORE.read_text(encoding="utf-8"))
    tampered = []
    for fp in _INTEGRITY_FILES:
        if not fp.exists():
            continue
        key = str(fp)
        if key not in stored:
            continue
        current = _compute_hash(fp)
        if current != stored[key]:
            tampered.append(fp.name)

    if tampered:
        print(f"\n  !!!!! [SECURITY ALERT] 파일 변조 감지 !!!!!")
        for name in tampered:
            print(f"    - {name}")
        print(f"  비밀번호 입력 팝업을 확인하세요...")
        try:
            from rpa_overlay import ask_integrity_password
            if ask_integrity_password():
                integrity_init()
                print("  무결성 해시가 재초기화되었습니다. 계속 실행합니다.")
                return True
        except Exception as exc:
            print(f"  [팝업 오류] {exc}")
            print(f"  CLI 리셋: python craigslist_auto_rpa.py --integrity-reset 1234")
        print(f"  실행을 중단합니다.")
        _log_event("error", "SYSTEM", "integrity",
                   f"File tampering detected: {', '.join(tampered)}")
        return False
    return True

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("[ERROR] pip install selenium webdriver-manager")
    sys.exit(1)

# ── 비밀번호 복호화 헬퍼 ──────────────────────────────────────────────────────
def _decrypt_env_password(raw: str) -> str:
    """ENC: 접두사 비밀번호를 Fernet 복호화. 평문이면 그대로 반환."""
    if not raw.startswith("ENC:"):
        return raw
    try:
        from crypto_util import decrypt_value
        return decrypt_value(raw)
    except Exception as e:
        print(f"  [ERROR] 비밀번호 복호화 실패: {e}")
        print(f"  .bridge.key 파일 확인 또는 python crypto_util.py setup 실행")
        sys.exit(1)

# ── Craigslist 설정 ──────────────────────────────────────────────────────────
CL_EMAIL    = os.getenv("CRAIGSLIST_EMAIL",    "")
CL_PASSWORD = _decrypt_env_password(os.getenv("CRAIGSLIST_PASSWORD", ""))
CL_CITY     = os.getenv("CRAIGSLIST_CITY",     "seoul")
CL_CONTACT  = os.getenv("CRAIGSLIST_CONTACT",  "bridgejobkr@gmail.com")

CL_BASE_URL  = f"https://{CL_CITY}.craigslist.org"
CL_LOGIN_URL = "https://accounts.craigslist.org/login/home"

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

# ── 대기 (블로킹 없는 카운트다운) ─────────────────────────────────────────────
def countdown(seconds: int, label: str = ""):
    """CMD 에 카운트다운을 출력하며 대기. 블로킹 없음."""
    for remaining in range(seconds, 0, -1):
        print(f"  ⏳ {label} {remaining}s...", end="\r", flush=True)
        time.sleep(1)
    print(" " * 60, end="\r")


def wait_for_captcha(driver, timeout: int = 120, headless: bool = False):
    """
    CAPTCHA 대기: timeout 초 동안 카운트다운 후 URL 재확인.
    headless=True 이면 즉시 실패 처리 (시각 브라우저 없으므로 해결 불가).
    """
    if headless:
        print("\n  ⚠️  [HEADLESS] CAPTCHA 감지 — 자동 해결 불가, 해당 건 스킵")
        _log_event("warn", "—", "captcha", "CAPTCHA detected in headless mode — skipped")
        return False

    print(f"\n  ⚠️  CAPTCHA 또는 추가 인증 감지")
    print(f"  브라우저에서 직접 풀어주세요. {timeout}초 자동 대기합니다.")
    for remaining in range(timeout, 0, -5):
        time.sleep(5)
        print(f"  ⏳ CAPTCHA 대기 중... {remaining-5}s 남음", end="\r", flush=True)
        if "login" not in driver.current_url.lower():
            print("\n  ✅ CAPTCHA 해결 감지, 계속 진행합니다.")
            return True
    print(f"\n  ❌ {timeout}초 내 해결되지 않음.")
    return False


# ── DB ────────────────────────────────────────────────────────────────────────
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def fetch_jobs(job_code: str | None, limit: int) -> list[dict]:
    conn = get_conn()
    params: list = []
    where_clauses = [
        "j.city IS NOT NULL AND j.city != ''",
        "j.salary_raw IS NOT NULL AND j.salary_raw != ''",
        "j.teaching_age IS NOT NULL AND j.teaching_age != ''",
        """NOT EXISTS (
            SELECT 1 FROM ad_posts ap
            WHERE ap.job_code = j.job_code
              AND ap.seq = j.seq
              AND ap.platform = 'craigslist'
              AND ap.status = 'posted'
        )""",
    ]
    if job_code:
        where_clauses.append("j.job_code = ?")
        params.append(job_code)

    where = "WHERE " + " AND ".join(where_clauses)

    # 내용 풍부도 점수: 필드가 많이 채워진 직업을 우선
    # 동점이면 RANDOM() → 매 실행마다 다른 직업이 선택됨
    content_score = """(
        CASE WHEN j.working_hours  IS NOT NULL AND j.working_hours  != '' THEN 1 ELSE 0 END +
        CASE WHEN j.teach_hrs_week IS NOT NULL AND j.teach_hrs_week != '' THEN 1 ELSE 0 END +
        CASE WHEN j.vacation       IS NOT NULL AND j.vacation       != '' THEN 1 ELSE 0 END +
        CASE WHEN j.native_count   IS NOT NULL AND j.native_count   != '' THEN 1 ELSE 0 END +
        CASE WHEN j.class_size     IS NOT NULL AND j.class_size     != '' THEN 1 ELSE 0 END +
        CASE WHEN j.housing        IS NOT NULL AND j.housing        != '' THEN 1 ELSE 0 END +
        CASE WHEN j.district       IS NOT NULL AND j.district       != '' THEN 1 ELSE 0 END +
        CASE WHEN j.benefits       IS NOT NULL AND j.benefits       != '' THEN 1 ELSE 0 END
    )"""

    sql = f"""
        SELECT j.id, j.job_code, j.seq, j.city, j.district,
               j.teaching_age, j.salary_raw, j.salary_min, j.salary_max,
               j.working_hours, j.daily_hours, j.teach_hrs_week,
               j.housing, j.benefits, j.vacation, j.native_count,
               j.start_date, j.class_size,
               {content_score} AS content_score
        FROM jobs j
        {where}
        ORDER BY content_score DESC, RANDOM()
        LIMIT ?
    """
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_draft(job: dict, title: str, body: str) -> int:
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM ad_posts WHERE job_code=? AND seq=? AND platform='craigslist'",
        (job["job_code"], job["seq"])
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE ad_posts SET ad_title=?, ad_body=?, status='draft', draft_at=? WHERE id=?",
            (title, body, NOW, existing[0])
        )
        conn.commit(); conn.close()
        return existing[0]
    cur = conn.execute(
        "INSERT INTO ad_posts (job_code,seq,platform,status,ad_title,ad_body,draft_at) "
        "VALUES (?,?,'craigslist','draft',?,?,?)",
        (job["job_code"], job["seq"], title, body, NOW)
    )
    aid = cur.lastrowid
    conn.commit(); conn.close()
    return aid


def mark_posted(ad_id: int, posted_url: str, screenshot: str):
    conn = get_conn()
    conn.execute(
        "UPDATE ad_posts SET status='posted',posted_at=?,posted_url=?,screenshot_path=? WHERE id=?",
        (NOW, posted_url, screenshot, ad_id)
    )
    conn.commit(); conn.close()


def mark_error(ad_id: int, msg: str):
    conn = get_conn()
    conn.execute(
        "UPDATE ad_posts SET status='error',error_msg=? WHERE id=?",
        (msg[:500], ad_id)
    )
    conn.commit(); conn.close()


# ── 광고 생성 ─────────────────────────────────────────────────────────────────
# ⚠️  보안: 업체명·연락처·주소 절대 미포함
# 허용: 도시(city), 급여(salary_raw), 근무시간, 연령대, 일반 복지
# ── 제목 생성 (샘플 포맷: ◾◾◾◾ CITY, ... 67~72자) ────────────────────────────

_CITY_UPPER = {
    "서울":"SEOUL","Seoul":"SEOUL","부산":"BUSAN","Busan":"BUSAN",
    "대구":"DAEGU","Daegu":"DAEGU","인천":"INCHEON","Incheon":"INCHEON",
    "광주":"GWANGJU","Gwangju":"GWANGJU","대전":"DAEJEON","Daejeon":"DAEJEON",
    "울산":"ULSAN","Ulsan":"ULSAN","세종":"SEJONG","Sejong":"SEJONG",
    "수원":"SUWON","Suwon":"SUWON","성남":"SEONGNAM","Seongnam":"SEONGNAM",
    "전주":"JEONJU","Jeonju":"JEONJU","청주":"CHEONGJU","Cheongju":"CHEONGJU",
    "제주":"JEJU","Jeju":"JEJU","안양":"ANYANG","Anyang":"ANYANG",
    "안산":"ANSAN","Ansan":"ANSAN","고양":"GYEONGGI","Goyang":"GYEONGGI",
    "용인":"YONGIN","Yongin":"YONGIN","의정부":"UIJEONGBU","Uijeongbu":"UIJEONGBU",
    "춘천":"CHUNCHEON","Chuncheon":"CHUNCHEON","원주":"WONJU","Wonju":"WONJU",
    "천안":"CHEONAN","Cheonan":"CHEONAN","아산":"ASAN","Asan":"ASAN",
    "창원":"CHANGWON","Changwon":"CHANGWON","구미":"GUMI","Gumi":"GUMI",
    "파주":"PAJU","Paju":"PAJU","김포":"GIMPO","Gimpo":"GIMPO",
    "경기":"GYEONGGI","Gyeonggi":"GYEONGGI","Korea":"KOREA",
}

_TITLE_OPENERS = [
    "Energetic ESL Teacher Wanted",
    "Passionate Minds Wanted",
    "Enthusiastic Teacher",
    "Motivated Native Teacher",
    "Nature-Loving Teacher Needed",
    "Bright and Positive Teacher",
    "Passion for Teaching Needed",
    "Creative Minds Wanted",
    "Positive and Adaptable Teacher",
    "Professional and Punctual",
    "Warm-Hearted Teacher",
    "Active and Positive Role",
    "Dedicated Teacher",
    "Experienced and Professional Minds",
    "High Energy Required",
    "Active and Friendly",
    "Enthusiastic and Dedicated Teacher",
    "Dynamic and Creative Teacher",
    "Committed ESL Teacher Wanted",
    "Friendly and Motivated Teacher",
]

def _age_to_level(age_raw: str) -> str:
    a = age_raw.lower()
    if "adult" in a:                          return "ADULT ESL"
    if "high" in a and "school" in a:         return "ELEM-HIGH SCHOOL"
    if "high" in a:                           return "KINDY-HIGH SCHOOL"
    if "middle" in a and ("elem" in a or "kindy" in a or "kinder" in a):
                                              return "ELEM-MIDDLE"
    if "middle" in a:                         return "KINDER-MIDDLE"
    if ("kindy" in a or "kinder" in a) and ("elem" in a):
                                              return "KINDER-ELEM"
    if "kindy" in a or "kinder" in a or "kindergarten" in a:
                                              return "KINDY-ELEM"
    if "elem" in a:                           return "KINDER-ELEM"
    return "KINDER-ELEM"

def _start_to_label(start: str) -> tuple[str, str]:
    """(month_word, suffix) — e.g. ('July', 'July Start') / ('ASAP', 'ASAP')"""
    s = start.strip().lower()
    if not s or s in ("negotiable","tbd","협의","미정"): return ("Negotiable","Negotiable Start")
    if "asap" in s or "즉시" in s:           return ("ASAP","ASAP Start")
    months = [("jan","January"),("feb","February"),("mar","March"),("apr","April"),
              ("may","May"),("jun","June"),("jul","July"),("aug","August"),
              ("sep","September"),("oct","October"),("nov","November"),("dec","December"),
              ("1월","January"),("2월","February"),("3월","March"),("4월","April"),
              ("5월","May"),("6월","June"),("7월","July"),("8월","August"),
              ("9월","September"),("10월","October"),("11월","November"),("12월","December")]
    for key, name in months:
        if key in s: return (name, f"{name} Start")
    return ("Negotiable","Negotiable Start")

def _build_title(city_raw: str, age_raw: str, start_raw: str) -> str:
    """◾◾◾◾ {CITY}, ... 형식 제목 생성. 67~72자 맞춤."""
    city_up = _CITY_UPPER.get(city_raw, city_raw.upper())
    level   = _age_to_level(age_raw) if age_raw else "KINDER-ELEM"
    month, start_suffix = _start_to_label(start_raw)

    prefix = "\u25fe\u25fe\u25fe\u25fe "          # ◾◾◾◾ (6자)
    city_part = f"{city_up}, "

    # 후보 패턴 목록
    candidates = []
    is_month = month not in ("ASAP", "Negotiable")
    abbr = month[:3] + "." if is_month and len(month) > 4 else month
    is_asap = month == "ASAP"
    for opener in _TITLE_OPENERS:
        # 패턴 A: opener for LEVEL (start)
        candidates.append(f"{prefix}{city_part}{opener} for {level} ({start_suffix})")
        if is_month:
            candidates.append(f"{prefix}{city_part}{opener} for {level} ({abbr} Start)")
        # 패턴 B: 달 이름 포함
        if is_month:
            candidates.append(f"{prefix}{city_part}{month} Start: {opener} {level}")
            candidates.append(f"{prefix}{city_part}{opener} {level} for {month} Openings")
        # 패턴 C: opener LEVEL Specialist (start)
        candidates.append(f"{prefix}{city_part}{opener} {level} Specialist ({start_suffix})")
        # 패턴 D: opener for LEVEL Teacher
        candidates.append(f"{prefix}{city_part}{opener} for {level} Teacher")
        # 패턴 E: opener for LEVEL School Level
        candidates.append(f"{prefix}{city_part}{opener} for {level} School Level")
        # 패턴 F: opener for LEVEL Openings Now
        candidates.append(f"{prefix}{city_part}{opener} for {level} Openings Now")
        # 패턴 G: opener for Year-Round LEVEL Classes
        candidates.append(f"{prefix}{city_part}{opener} for Year-Round {level} Classes")
        # 패턴 H: ASAP 전용 — opener for ASAP LEVEL Study Groups
        if is_asap:
            candidates.append(f"{prefix}{city_part}{opener} for ASAP {level} Study Groups")

    # 67~72자 범위 내 후보 선택 (직업코드 해시로 매번 다른 것)
    import hashlib as _h
    seed = int(_h.md5(f"{city_raw}{age_raw}{start_raw}".encode()).hexdigest(), 16)
    valid = [c for c in candidates if 67 <= len(c) <= 72]
    if valid:
        return valid[seed % len(valid)]

    # 범위 밖이면 가장 가까운 것 선택
    return min(candidates, key=lambda c: abs(len(c) - 69))


# 실제 Craigslist 게시 포맷에 맞춤 (◾◾◾ 제목, 백틱 필드, 표준 요건 문구)

_AGE_MAP = {
    "pre":      "Pre-K",
    "kindy":    "Kindy",
    "kindergarten": "Kindy",
    "elem":     "Elem",
    "elementary": "Elem",
    "middle":   "Middle",
    "high":     "High School",
    "adult":    "Adult",
    "conversation": "Adult",
}

def _age_label(raw: str) -> str:
    """'Kindy - Elem' 스타일 짧은 라벨 반환."""
    lower = raw.lower()
    labels, seen = [], set()
    for key, label in _AGE_MAP.items():
        if key in lower and label not in seen:
            labels.append(label); seen.add(label)
    if not labels:
        return raw.strip()
    # 중복 제거 및 순서 정렬 (Pre-K → Kindy → Elem → Middle → High → Adult)
    order = ["Pre-K", "Kindy", "Elem", "Middle", "High School", "Adult"]
    sorted_labels = [l for l in order if l in labels]
    if not sorted_labels:
        sorted_labels = labels
    return " - ".join(sorted_labels)


def _safe_benefits(raw: str) -> list[str]:
    """복지 항목 파싱. 연락처/업체명 포함 항목 차단."""
    defaults = ["Visa sponsorship", "severance pay", "pension", "insurance", "paid vacation"]
    if not raw:
        return defaults
    items = [b.strip() for b in re.split(r"[,;\n]", raw) if b.strip()]
    clean = []
    for item in items:
        if re.search(
            r'@|010[-\s]?\d|02[-\s]?\d{3,4}[-\s]?\d{4}'
            r'|학원|어학원|유치원|센터|학교'
            r'|\d{3}-\d{2}-\d{5}'
            r'|[가-힣]{2,4}\s*(?:원장|팀장|부장|선생님|교감|교장)'
            r'|\+\d{1,3}[-\s]?\d', item):
            continue
        if len(item) > 80:
            continue
        clean.append(item)
    return clean if clean else defaults


def _title_feature(job: dict, teach_hrs: str, vacation: str, benefits: list[str]) -> str:
    """제목 끝에 붙는 핵심 특징 (실제 게시 포맷 참고)."""
    # 수업시간 명시 → 우선
    if teach_hrs and re.search(r'\d', teach_hrs):
        hrs = teach_hrs.strip().split()[0].split("~")[0]
        return f"Teaching Hours per Week : {teach_hrs}"
    # 휴가 20일 이상
    if vacation:
        m = re.search(r'(\d+)\s*days?', vacation, re.I)
        if m and int(m.group(1)) >= 20:
            return f"Vacation : {m.group(1)} days"
    # 복지 중 눈에 띄는 항목
    notable = ["airfare", "housing", "flight", "bonus"]
    for b in benefits:
        for kw in notable:
            if kw in b.lower():
                return b.strip().rstrip(".")
    # 기본
    return "Visa sponsorship"


_HOUSING_KW = re.compile(
    r'(?:accommodat|housing|airbnb|숙소|오피스텔|월세|보증금)', re.I
)


def _extract_housing(housing_col: str, benefits_raw: str) -> tuple[str, str]:
    """
    housing 컬럼 우선. 없으면 benefits 문자열에서 숙소 관련 항목 추출.
    반환: (housing_str, benefits_raw_without_housing)
    데이터에 없는 내용은 절대 추가하지 않음 — 불명확하면 빈 문자열 반환.
    """
    if housing_col:
        return housing_col.strip(), benefits_raw

    # benefits에서 숙소 키워드가 포함된 항목 추출
    items = [b.strip() for b in re.split(r'[,;\n]', benefits_raw) if b.strip()]
    housing_items, other_items = [], []
    for item in items:
        if _HOUSING_KW.search(item):
            housing_items.append(item)
        else:
            other_items.append(item)

    if housing_items:
        # Housing 라인으로 이동 — benefits에서 중복 제거
        return ", ".join(housing_items), ", ".join(other_items)

    # 소스에 없으면 빈 문자열 (임의로 "Not provided" 추가 금지)
    return "", benefits_raw


def generate_ad(job: dict) -> tuple[str, str]:
    """(title, body) 반환. 실제 Craigslist 게시 포맷."""
    city       = (job.get("city")          or "Korea").strip()
    district   = (job.get("district")      or "").strip()
    age_raw    = (job.get("teaching_age")  or "").strip()
    age        = _age_label(age_raw) if age_raw else "Various"
    salary     = (job.get("salary_raw")    or "Negotiable").strip()
    hours      = (job.get("working_hours") or "").strip()
    teach_hrs  = (job.get("teach_hrs_week") or "").strip()
    vacation   = (job.get("vacation")      or "").strip()
    native     = (job.get("native_count")  or "").strip()
    start      = (job.get("start_date")    or "Negotiable").strip()
    class_size = (job.get("class_size")    or "").strip()
    jcode      = (job.get("job_code")      or "").strip()

    # Housing: housing 컬럼 → benefits 파생 → 없으면 빈 문자열 (임의 추가 금지)
    housing, benefits_remaining = _extract_housing(
        job.get("housing") or "",
        job.get("benefits") or "",
    )

    # 도시+구 (구는 city 뒤 공백 구분으로만)
    location = f"{city}{' ' + district if district else ''}"

    benefits   = _safe_benefits(benefits_remaining)
    ben_str    = ", ".join(benefits)

    # ── 제목: 샘플 포맷 ◾◾◾◾ {CITY}, ... (67~72자)
    title = _build_title(city, age_raw, start)

    # ── 본문 필드 구성 (있는 필드 전부 출력, 개인정보만 제외)
    job_num = jcode.replace("Job.", "").strip()
    lines = [location, f"Job. {job_num}"]

    if start:
        lines.append(f"Starting Date : {start}")
    if age_raw:
        lines.append(f"Teaching Age : {age_raw}")
    if class_size:
        lines.append(f"Class size : {class_size}")
    if hours:
        lines.append(f"Working Hours : {hours}")
    if salary:
        lines.append(f"Monthly Salary : {salary}")
    if teach_hrs:
        lines.append(f"Average Teaching Hours per Week : {teach_hrs}")
    if vacation:
        lines.append(f"Vacation : {vacation}")
    if native:
        lines.append(f"Native Teacher (Numbers can change) : {native}")
    if housing:
        lines.append(f"Housing: {housing}")
    if ben_str:
        lines.append(f"Employee Benefits : {ben_str.rstrip('.')}.")

    lines.append("")
    lines.append("\U0001f534REQUIREMENTS:")
    lines.append(" \u2022MUST-Haves: Clean background check & at least Bachelor's degree.")
    lines.append(" \u2022Eligible Passports: UK, US, CA, AUS, NZ, IRL, ZA.")
    lines.append(" \u2022SA: only those currently residing in Korea.")
    lines.append(" \u2022Korean/Gyopo Nationals: Eligible if all requirements are met.")
    lines.append("")
    lines.append("\u26a0\ufe0fIMPORTANT: PLEASE READ CAREFULLY. We CANNOT offer or help for nationalities not listed above. DO NOT APPLY IF INELIGIBLE\u26a0\ufe0f")

    body = "\n".join(lines)
    return title.strip(), body.strip()


# ── Selenium ──────────────────────────────────────────────────────────────────
def _delay(lo=0.8, hi=2.0):
    time.sleep(random.uniform(lo, hi))


def _type_slow(el, text: str):
    for ch in text:
        el.send_keys(ch)
        time.sleep(random.uniform(0.04, 0.10))


def build_driver(headless: bool = False) -> webdriver.Chrome:
    opts = Options()
    if headless:
        # Headless 모드: 화면 미러링 잠금 상태에서 작동
        # CAPTCHA 발생 시 자동 해결 불가 → wait_for_captcha() 가 즉시 실패 처리
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")
        print("  [DRIVER] Headless 모드로 Chrome 시작")
    else:
        # 화면 밖으로 이동 — headless 아니라 봇 감지 없고, 사용자 화면에는 안 보임
        opts.add_argument("--window-position=-10000,-10000")
        opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    # 드라이버 시작 전 기존 Chrome 창 hwnd 목록 저장
    _existing_hwnds: set = set()
    try:
        import win32gui as _wg
        def _collect(hwnd, _):
            if _wg.GetClassName(hwnd) == "Chrome_WidgetWin_1":
                _existing_hwnds.add(hwnd)
        _wg.EnumWindows(_collect, None)
    except Exception:
        pass

    svc    = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=svc, options=opts)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"}
    )

    # 새로 생긴 Chrome 창만 작업표시줄에서 숨김 (기존 창 보존)
    try:
        import win32gui as _wg, win32con as _wc, time as _t
        _t.sleep(1.5)
        def _hide_new(hwnd, _):
            if hwnd in _existing_hwnds:
                return
            if _wg.GetClassName(hwnd) == "Chrome_WidgetWin_1":
                ex = _wg.GetWindowLong(hwnd, _wc.GWL_EXSTYLE)
                _wg.SetWindowLong(hwnd, _wc.GWL_EXSTYLE,
                    (ex | _wc.WS_EX_TOOLWINDOW) & ~_wc.WS_EX_APPWINDOW)
                _wg.ShowWindow(hwnd, _wc.SW_HIDE)
        _wg.EnumWindows(_hide_new, None)
    except Exception:
        pass
    return driver


def _find(driver, selectors: list[str]):
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed():
                return el
        except Exception:
            pass
    return None


def _click_next(driver, timeout=8):
    for sel in [
        "button#go", "button[id*='continue']", "input[value*='continue']",
        "button[type='submit']", "input[type='submit']",
    ]:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
            )
            el.click()
            return True
        except Exception:
            pass
    return False


def _has_captcha(driver) -> bool:
    return any(k in driver.page_source.lower()
               for k in ["recaptcha", "g-recaptcha", "hcaptcha"])


def cl_login(driver: webdriver.Chrome) -> bool:
    print("  [1/7] Craigslist 로그인...")
    driver.get(CL_LOGIN_URL)
    _delay(2, 3)

    try:
        email_el = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "inputEmailHandle"))
        )
        _type_slow(email_el, CL_EMAIL)
        _delay()

        pw_el = driver.find_element(By.ID, "inputPassword")
        _type_slow(pw_el, CL_PASSWORD)
        _delay(0.5, 1.0)
        pw_el.send_keys(Keys.RETURN)

        # Craigslist 는 로그인 후에도 URL 이 accounts.craigslist.org/login/home 유지
        # → URL 대신 페이지 콘텐츠로 로그인 성공 여부 판단
        def _is_logged_in(d):
            src = d.page_source.lower()
            return "log out" in src or "logout" in src or "make new post" in src

        try:
            WebDriverWait(driver, 12).until(_is_logged_in)
            print(f"  [LOGIN] 성공 ✅")
            return True
        except Exception:
            pass

        # CAPTCHA 감지
        if _has_captcha(driver):
            ok = wait_for_captcha(driver, timeout=120)
            return ok

        # 마지막 수단: 추가 30초 대기
        print("  [LOGIN] 30초 추가 대기...")
        countdown(30, "로그인 대기")
        if _is_logged_in(driver):
            print("  [LOGIN] 성공 ✅")
            return True

        ss_path = SS_DIR / "login_fail.png"
        driver.save_screenshot(str(ss_path))
        print(f"  [LOGIN] 실패 — 스크린샷: {ss_path}")
        return False

    except Exception as e:
        print(f"  [LOGIN ERROR] {e}")
        return False


def _js_click(driver, el):
    driver.execute_script("arguments[0].click();", el)


def _step(url: str) -> str:
    """URL 에서 ?s= 파라미터 추출."""
    m = re.search(r'\?s=(\w+)', url)
    return m.group(1) if m else ""


def _wait_step_change(driver, old_step: str, timeout: int = 10) -> str:
    """?s= 파라미터가 바뀔 때까지 대기 후 새 step 반환."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: _step(d.current_url) != old_step
        )
    except Exception:
        pass
    return _step(driver.current_url)


def _advance(driver, old_step: str, timeout: int = 8) -> str:
    """continue/submit 버튼 클릭 후 다음 step 으로 이동."""
    _click_next(driver)
    new_step = _wait_step_change(driver, old_step, timeout)
    _delay(1.5, 2.5)
    print(f"    → ?s={new_step}  ({driver.current_url.split('?')[0][-30:]})")
    return new_step


def _is_category_page(driver) -> bool:
    """
    현재 페이지가 카테고리 선택 페이지인지 판단.
    step 이름이 알 수 없는 값일 때 폴백으로 사용.
    """
    try:
        src = driver.page_source.lower()
        return (
            ("education" in src or "category" in src) and
            ("finance" in src or "accounting" in src or "jobs" in src) and
            ("input" in src and "radio" in src or "type=\"radio\"" in src)
        )
    except Exception:
        return False


def cl_post(driver: webdriver.Chrome, title: str, body: str, job: dict) -> str | None:
    """Craigslist 포스팅 — URL ?s= 파라미터로 현재 단계 감지해 처리."""

    # ── seoul.craigslist.org → "post to classifieds" 클릭 ─
    # accounts.craigslist.org 에서 시작하면 지역이 다르게 잡힘
    # seoul.craigslist.org 에서 시작해야 Seoul 이 자동 선택됨
    print("  [POST] seoul.craigslist.org → post to classifieds...")
    # 이전 ABORT 후 Chrome 세션 초기화 (about:blank로 상태 리셋)
    try:
        driver.get("about:blank")
        _delay(0.5, 1)
    except Exception:
        pass
    driver.get(CL_BASE_URL)   # https://seoul.craigslist.org
    _delay(2, 3)
    try:
        link = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "post to classifieds"))
        )
        link.click()
        _delay(2, 3)
    except Exception:
        # 대안: 직접 URL
        driver.get("https://post.craigslist.org")
        _delay(2, 3)

    # ── 단계별 처리 루프 (최대 15 스텝, 동일 step 3회 연속 시 중단) ──
    _step_count: dict = {}
    for _ in range(15):
        step = _step(driver.current_url)
        _step_count[step] = _step_count.get(step, 0) + 1
        if _step_count[step] > 3:
            ss = SS_DIR / f"stuck_{step}.png"
            driver.save_screenshot(str(ss))
            print(f"  [ABORT] ?s={step} 에서 3회 이상 반복 — 스크린샷: {ss}")
            break
        print(f"  [?s={step}] ", end="", flush=True)

        if step == "copyfromanother":
            # "copy from another posting?" → 그냥 continue (skip)
            print("이전 게시물 복사 스킵")
            _advance(driver, step)

        elif step == "area":
            # 지역 선택 (Seoul 선택 또는 기본값 유지 후 continue)
            print("지역 선택")
            try:
                # Seoul 또는 korea 옵션 찾기
                opts = driver.find_elements(By.CSS_SELECTOR, "input[type='radio'], option")
                for opt in opts:
                    val = (opt.get_attribute("value") or "").lower()
                    txt = (opt.text or "").lower()
                    if "seoul" in val or "seoul" in txt or "korea" in val:
                        _js_click(driver, opt); _delay(0.5, 1); break
            except Exception:
                pass
            _advance(driver, step)

        elif step == "type":
            # 포스팅 타입 → "job offered" 선택
            print("타입: job offered 선택")
            selected = False
            # 방법 1: input[value='jo'] — Craigslist 실제 value 값
            try:
                radio = driver.find_element(By.CSS_SELECTOR, "input[value='jo']")
                _js_click(driver, radio); selected = True
            except Exception:
                pass
            # 방법 2: 레이블 텍스트 폴백
            if not selected:
                try:
                    for lbl in driver.find_elements(By.TAG_NAME, "label"):
                        if "job offered" in lbl.text.lower():
                            _js_click(driver, lbl); selected = True; break
                except Exception:
                    pass
            if not selected:
                print("    [WARN] job offered 라디오 미선택")
            _delay(0.5, 1)
            _advance(driver, step)

        elif step in ("subarea", "cat", "subcat", "category", "subcatselect",
                      "cattype", "jobcat", "jobtype", "catselect") or (
                      step not in ("copyfromanother", "area", "type", "attr", "edit",
                                   "img", "preview", "done", "manage", "") and
                      _is_category_page(driver)):
            # ─────────────────────────────────────────────────────────────────
            # 카테고리 선택 페이지: education 강제 선택
            # Craigslist Seoul education category value = '102' (jobs>education)
            # finance = '110', accounting = '100' 등 — 절대 선택 금지
            #
            # 4단계 fallback 전략:
            #   1) value='102' XPATH (가장 신뢰)
            #   2) 텍스트 "education" 포함 라디오 인접 레이블
            #   3) 레이블 href에 'edu' 포함 링크
            #   4) DOM에 education 텍스트가 있으면 부모 클릭
            # ─────────────────────────────────────────────────────────────────
            print("카테고리: education 선택")

            # 현재 페이지 HTML 저장 (디버그 — 카테고리 선택 실패 시 원인 파악용)
            cat_debug = _LOG_DIR / "debug_category_page.html"
            try:
                cat_debug.write_text(driver.page_source, encoding="utf-8")
                print(f"    [DEBUG] 카테고리 페이지 소스 저장: {cat_debug}")
            except Exception:
                pass

            selected = False

            # 방법 1: value='102' (Craigslist Seoul jobs>education 확인값)
            if not selected:
                try:
                    radio = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@value='102']"))
                    )
                    _js_click(driver, radio); selected = True; _delay(0.5, 1)
                    print("    [OK] education value=102 클릭")
                except Exception:
                    pass

            # 방법 2: 텍스트 "education" 포함 라디오 버튼 (value 변동 대비)
            if not selected:
                try:
                    # label 텍스트로 매칭 후 해당 input 클릭
                    result = driver.execute_script("""
                        var labels = document.querySelectorAll('label');
                        for (var lbl of labels) {
                            var txt = lbl.textContent.toLowerCase();
                            if (txt.includes('education') && !txt.includes('special') && !txt.includes('finance')) {
                                // for 속성으로 연결된 input 찾기
                                var forId = lbl.getAttribute('for');
                                if (forId) {
                                    var inp = document.getElementById(forId);
                                    if (inp) { inp.click(); return 'label-for:' + forId; }
                                }
                                // 인접 input 찾기
                                var inp2 = lbl.querySelector('input') || lbl.previousElementSibling;
                                if (inp2 && inp2.tagName === 'INPUT') { inp2.click(); return 'adjacent:' + inp2.value; }
                                // 레이블 자체 클릭
                                lbl.click(); return 'label-click';
                            }
                        }
                        return null;
                    """)
                    if result:
                        selected = True; _delay(0.5, 1)
                        print(f"    [OK] education 레이블 매칭: {result}")
                except Exception:
                    pass

            # 방법 3: href에 'edu' 또는 'education' 포함 링크
            if not selected:
                try:
                    for a in driver.find_elements(By.TAG_NAME, "a"):
                        href = (a.get_attribute("href") or "").lower()
                        txt  = a.text.lower()
                        if ("edu" in href or "education" in txt) and "finance" not in txt:
                            _js_click(driver, a); selected = True; _delay(0.5, 1)
                            print(f"    [OK] education 링크 클릭: {a.text.strip()}")
                            break
                except Exception:
                    pass

            # 방법 4: li 태그 텍스트 매칭
            if not selected:
                try:
                    for li in driver.find_elements(By.TAG_NAME, "li"):
                        if "education" in li.text.lower() and "finance" not in li.text.lower():
                            _js_click(driver, li); selected = True; _delay(0.5, 1)
                            print(f"    [OK] education li 클릭: {li.text.strip()[:40]}")
                            break
                except Exception:
                    pass

            if not selected:
                _log_event("error", job.get("job_code", "?"), "category",
                           "education selection failed — check debug_category_page.html")
                print("    [ERROR] education 선택 실패 — debug_category_page.html 확인 후 value 값 수정 필요")
                # 게시 중단 (잘못된 카테고리에 올라가는 것보다 중단이 안전)
                return None
            _advance(driver, step)

        elif step in ("attr", "edit"):
            # 광고 폼 입력 (?s=edit 또는 ?s=attr)
            print("폼 입력")
            _delay(1, 2)
            # 첫 진입 시 HTML 소스 저장 (디버그용)
            if _step_count.get(step, 0) == 1:
                debug_path = _LOG_DIR / "debug_edit_page.html"
                debug_path.write_text(driver.page_source, encoding="utf-8")
                print(f"    [DEBUG] 페이지 소스 저장: {debug_path}")

            # ── JS 헬퍼: 값 설정 + input/change 이벤트 강제 발화 ──────────────
            # React/Vue/jQuery 폼에서 send_keys 만으로는 값 인식 안 될 수 있음
            def _js_set(selector: str, val: str) -> bool:
                try:
                    return bool(driver.execute_script("""
                        var el = document.querySelector(arguments[0]);
                        if (!el) return false;
                        var nativeSet = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value') ||
                            Object.getOwnPropertyDescriptor(
                            window.HTMLTextAreaElement.prototype, 'value');
                        if (nativeSet) nativeSet.set.call(el, arguments[1]);
                        else el.value = arguments[1];
                        el.dispatchEvent(new Event('input',  {bubbles:true}));
                        el.dispatchEvent(new Event('change', {bubbles:true}));
                        return true;
                    """, selector, val))
                except Exception:
                    return False

            def _fill(sels, val, slow=False):
                el = _find(driver, sels)
                if not el:
                    return False
                try:
                    el.clear()
                    if slow: _type_slow(el, val)
                    else: el.send_keys(val)
                    _delay(0.3, 0.6)
                    return True
                except Exception:
                    return False

            # ── posting title ─────────────────────────────────────────────────
            # 실제 DOM: input[id='PostingTitle'] (대소문자 주의)
            ok_t = (
                _js_set("input[id='PostingTitle']", title) or
                _js_set("input[name='PostingTitle']", title) or
                _fill(["input[id='PostingTitle']", "input[name='PostingTitle']",
                       "input[id*='posting']"], title, slow=True)
            )

            # ── city / neighborhood ───────────────────────────────────────────
            city_val = job.get("city") or "Seoul"
            try:
                city_el = driver.execute_script("""
                    var labels = document.querySelectorAll('label');
                    for (var l of labels) {
                        var txt = l.textContent.trim().toLowerCase();
                        if (txt.includes('city') || txt.includes('neighborhood')) {
                            var forId = l.getAttribute('for');
                            if (forId) return document.getElementById(forId);
                            return l.nextElementSibling;
                        }
                    }
                    return document.querySelector('input[id*=city], input[name*=city]');
                """)
                if city_el:
                    city_el.clear(); city_el.send_keys(city_val)
                    _delay(0.3, 0.6)
            except Exception:
                _fill(["input[id='city']", "input[name='city']",
                       "input[placeholder*='eighborhood']"], city_val)

            # ── description (본문) ────────────────────────────────────────────
            # 실제 DOM: textarea[id='PostingBody'] (대소문자 주의)
            ok_b = (
                _js_set("textarea[id='PostingBody']", body) or
                _js_set("textarea[name='PostingBody']", body) or
                _fill(["textarea[id='PostingBody']", "textarea[name='PostingBody']",
                       "textarea[id*='description']", "textarea"], body)
            )

            # ── employment type → full-time ───────────────────────────────────
            # 실제 DOM: select[name='employment_type'] (jQuery UI 가 숨김 처리)
            # jQuery UI selectmenu 는 display:none select 를 커스텀 위젯으로 대체
            # → 직접 name 으로 hidden select 를 찾아 값 설정 후 selectmenu refresh
            try:
                emp_result = driver.execute_script("""
                    var sel = document.querySelector('select[name="employment_type"]');
                    if (!sel) return 'NOT FOUND';
                    // full-time 옵션(value=1) 직접 선택
                    sel.value = '1';
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                    // jQuery UI selectmenu 가 있으면 refresh
                    try {
                        if (window.jQuery && jQuery(sel).selectmenu) {
                            jQuery(sel).selectmenu('refresh');
                        }
                    } catch(e) {}
                    var chosen = sel.options[sel.selectedIndex];
                    return 'OK: value=' + sel.value + ' text=' + (chosen ? chosen.text : '?');
                """)
                print(f"    employment type → {emp_result}")
                _delay(0.5, 1.0)
            except Exception as e:
                print(f"    [WARN] employment type: {e}")

            # ── job title ─────────────────────────────────────────────────────
            jt_ok = (
                _js_set("input[name='job_title']", "ESL Teaching Position") or
                _fill(["input[name='job_title']", "input[id*='job_title']",
                       "input[id*='jobtitle']"], "ESL Teaching Position")
            )
            print(f"    job title={'OK' if jt_ok else 'SKIP'}")

            # ── company name ─────────────────────────────────────────────────
            _js_set("input[name='company_name']", "BRIDGE") or \
            _fill(["input[name='company_name']", "input[id*='company']"], "BRIDGE")

            # ── remuneration (보상/급여) ──────────────────────────────────────
            # 실제 필드명: name='remuneration'  (이전 코드는 'compensation' 으로 잘못 조회)
            salary_val = job.get("salary_raw") or ""
            _js_set("input[name='remuneration']", salary_val) or \
            _fill(["input[name='remuneration']", "input[name='compensation']",
                   "input[placeholder*='ompensation']"], salary_val)

            print(f"    제목={'OK' if ok_t else 'SKIP'}  본문={'OK' if ok_b else 'SKIP'}")
            _advance(driver, step, timeout=12)

        elif step in ("img", "editimage"):
            # 이미지 업로드 — B.jpg 첨부
            # ※ Craigslist 이미지 업로드 후 "done" 버튼 클릭 시
            #    자동으로 다음 단계로 넘어가지 않는 경우가 있음
            #    → done 클릭 후 step 변화 없으면 _advance() 로 수동 진행
            print("이미지 업로드")
            img_step_before = step
            if AD_IMAGE.exists():
                try:
                    # file input 은 보통 숨겨져 있음 → visibility 무시하고 send_keys
                    file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    if not file_inputs:
                        # JS로 hidden input 노출 후 찾기
                        driver.execute_script("""
                            var fi = document.querySelectorAll('input[type=file]');
                            fi.forEach(function(el){ el.style.display='block'; el.style.opacity='1'; });
                        """)
                        file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")

                    if file_inputs:
                        abs_path = str(AD_IMAGE.resolve())
                        file_inputs[0].send_keys(abs_path)
                        print(f"    이미지 경로 전송: {abs_path}")

                        # 업로드 진행 대기 — 썸네일 또는 progress 사라질 때까지 최대 30초
                        for _w in range(30):
                            time.sleep(1)
                            src = driver.page_source.lower()
                            if "uploading" not in src and "progress" not in src:
                                break
                        print("    업로드 완료 대기 끝")

                        # "done" 버튼 클릭
                        done_btn = _find(driver, [
                            "button.done", "button[id*='done']", "input[value='done']",
                            "button[type='submit'][class*='done']",
                            ".img-management button[type='submit']",
                        ])
                        if done_btn and done_btn.is_displayed():
                            _js_click(driver, done_btn)
                            _delay(2, 3)
                            print("    done 버튼 클릭 완료")
                            # done 클릭 후 step 자동 변경 여부 확인
                            new_step_check = _step(driver.current_url)
                            if new_step_check != img_step_before:
                                # 자동으로 다음 단계로 넘어감 → _advance() 호출 불필요
                                print(f"    → 자동 진행됨: ?s={new_step_check}")
                                continue  # for loop 다음 iteration
                        else:
                            print("    [INFO] done 버튼 없음 또는 미표시 — continue 버튼으로 진행")
                    else:
                        print("    [WARN] file input 없음 — 이미지 스킵")
                except Exception as img_err:
                    print(f"    [WARN] 이미지 업로드 실패: {img_err} — 계속 진행")
            else:
                print(f"    [WARN] 이미지 파일 없음: {AD_IMAGE}")
                print(f"    확인: {AD_IMAGE} 가 존재해야 합니다")
            _advance(driver, step)

        elif step == "preview":
            # 미리보기 → CAPTCHA 체크 후 publish
            print("미리보기 → publish")
            if _has_captcha(driver):
                print("    CAPTCHA 감지 — 브라우저에서 해결하세요...")
                wait_for_captcha(driver, timeout=120)
            pub = _find(driver, [
                "button#publish", "button[id*='publish']",
                "input[value='publish']", "button[type='submit']",
                "input[type='submit']",
            ])
            if pub:
                _js_click(driver, pub)
                _delay(3, 5)
                print(f"    → Publish 완료: {driver.current_url}")
            else:
                print("    [WARN] Publish 버튼 없음")
            break  # 게시 완료 후 루프 종료

        elif step in ("done", "manage", ""):
            print("완료")
            break

        else:
            # 알 수 없는 단계 → continue 시도
            print(f"알 수 없는 단계 → continue 시도")
            old = step
            new = _advance(driver, step)
            if new == old:   # 진행 없으면 중단
                print("    [WARN] 페이지 진행 없음 — 중단")
                break

    # 이메일 인증 페이지 대기
    if any(k in driver.current_url.lower() for k in ["confirm", "verify"]):
        print("  📧 이메일 인증 필요. 60초 대기...")
        countdown(60, "이메일 인증 대기")

    return driver.current_url


def take_screenshot(driver, job_code: str) -> str:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SS_DIR / f"{job_code}_{ts}.png"
    driver.save_screenshot(str(path))
    return str(path)


# ── PII 강제 치환 (Zero-Leak Redaction) ──────────────────────────────────────
# generate_ad() → redact_pii() → security_check() 순서로 적용
# redact_pii()가 먼저 [REDACTED] 치환 → security_check()가 잔류 PII 최종 검증

_REDACT_RULES: list[tuple[re.Pattern, str]] = [
    # 한국 휴대전화
    (re.compile(r'010[-\s]?\d{3,4}[-\s]?\d{4}'), '[REDACTED-PHONE]'),
    # 한국 유선전화 (02, 031, 032 등)
    (re.compile(r'\b0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}\b'), '[REDACTED-PHONE]'),
    # 국제 전화 (+1 xxx xxx xxxx 등)
    (re.compile(r'\+\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}'), '[REDACTED-PHONE]'),
    # 이메일 — CL_CONTACT 이외 전부 치환
    (re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'), '[REDACTED-EMAIL]'),
    # 카카오톡 ID
    (re.compile(r'(?:kakao(?:talk)?|카[카]?오?톡?|KaTalk|카톡)\s*(?:id)?[:：\s]*[\w.\-]{2,30}', re.I), '[REDACTED-KAKAO]'),
    # LINE ID
    (re.compile(r'(?:LINE|라인)\s*(?:id)?[:：\s]*[\w.\-]{2,30}', re.I), '[REDACTED-LINE]'),
    # 사업자등록번호
    (re.compile(r'\b\d{3}-\d{2}-\d{5}\b'), '[REDACTED-BIZNUM]'),
    # 한국어 학원/기관명
    (re.compile(r'[\uac00-\ud7a3]+(어학원|학원|유치원|학교|센터|원)\b'), '[REDACTED-SCHOOL]'),
    # 상세 도로명 주소 패턴 (x층, x호 등)
    (re.compile(r'\d+층|\d+호\b'), '[REDACTED-ADDR]'),
    # 도로명 주소 (xx로, xx길 + 번지)
    (re.compile(r'[가-힣]+(?:로|길)\s*\d+(?:-\d+)?'), '[REDACTED-ADDR]'),
    # 한국어 이름 — 담당자/성명/이름 컨텍스트 뒤 2-4자 한글
    (re.compile(r'(?:담당자|성명|이름|문의처|연락처)[:：\s]{0,3}([가-힣]{2,4})'), '[REDACTED-NAME]'),
    # 영어 이름 — "Name:", "Contact:", "Teacher:", "Director:" 뒤 Title Case 2단어
    (re.compile(r'(?:Name|Contact|Teacher|Director|Recruiter|Manager):\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)'), '[REDACTED-NAME]'),
    # 한국어 이름+직책 — "홍길동 원장", "김철수 팀장" 패턴
    (re.compile(r'[가-힣]{2,4}\s*(?:원장|팀장|부장|과장|대리|주임|선생님|교감|교장|원감)\b'), '[REDACTED-NAME+TITLE]'),
    # 웹사이트 URL (http/https/www)
    (re.compile(r'(?:https?://|www\.)\S+', re.I), '[REDACTED-URL]'),
    # 회사/업체명 (xx컴퍼니, xx주식회사, xx(주), xx Inc 등)
    (re.compile(r'[\uac00-\ud7a3]+(?:주식회사|컴퍼니|에듀|잉글리시|영어마을|어린이집)\b'), '[REDACTED-COMPANY]'),
    (re.compile(r'(?:주식회사|㈜|\(주\))\s*[\uac00-\ud7a3]+'), '[REDACTED-COMPANY]'),
    (re.compile(r'[\w\s]+(?:Inc\.|Corp\.|Co\.,?\s*Ltd\.?|LLC)\b', re.I), '[REDACTED-COMPANY]'),
    # 위챗 / WeChat ID
    (re.compile(r'(?:WeChat|위챗|微信)\s*(?:id)?[:：\s]*[\w.\-]{2,30}', re.I), '[REDACTED-WECHAT]'),
    # 텔레그램 ID
    (re.compile(r'(?:Telegram|텔레그램|텔레)\s*(?:id)?[:：\s]*@?[\w.\-]{2,30}', re.I), '[REDACTED-TELEGRAM]'),
    # 인스타그램 / SNS 핸들 (\bIG\b 단어경계 — "Eligible"/"INELIGIBLE" 오치환 방지)
    (re.compile(r'(?:Instagram|인스타(?:그램)?|\bIG\b)\s*[:：\s]*@?[\w.\-]{2,30}', re.I), '[REDACTED-SNS]'),
    # 팩스 번호
    (re.compile(r'(?:팩스|FAX|Fax)\s*[:：\s]*[\d\-\s]{8,}', re.I), '[REDACTED-FAX]'),
    # 우편번호 (한국 5자리)
    (re.compile(r'\b\d{5}\b(?=\s*[가-힣])'), '[REDACTED-ZIPCODE]'),
    # 지번 주소 (xx동 xxx-xx번지)
    (re.compile(r'[가-힣]+[동리면읍]\s*\d+(?:-\d+)?(?:\s*번지)?'), '[REDACTED-ADDR]'),
]


def redact_pii(text: str, preserve_email: str = "") -> tuple[str, list[str]]:
    """
    모든 PII 패턴을 [REDACTED-*] 태그로 강제 치환.

    Args:
        text:           원본 텍스트
        preserve_email: 보존할 이메일 주소 (CL 공식 연락처 등)

    Returns:
        (redacted_text, list_of_removed_items)
    """
    out = text
    removed: list[str] = []

    for pattern, tag in _REDACT_RULES:
        def _replacer(m: re.Match, _tag=tag, _preserve=preserve_email) -> str:
            val = m.group(0)
            # 보존 이메일은 치환하지 않음
            if _preserve and val.lower() == _preserve.lower():
                return val
            removed.append(f"{_tag}={val}")
            return _tag
        out = pattern.sub(_replacer, out)

    return out, removed


# ── 보안 최종 검증 ────────────────────────────────────────────────────────────
def security_check(body: str, job_code: str) -> bool:
    """게시 전 광고 본문에서 개인정보 패턴 탐지."""
    passed = True

    # 한국 전화번호
    if re.search(r'010[-\s]?\d{3,4}[-\s]?\d{4}', body):
        print(f"  [보안 차단] {job_code}: '한국 전화번호' 패턴 감지 → 게시 중단")
        passed = False

    # 국제 전화번호 (+82 등)
    if re.search(r'\+\d{1,3}[\s\-]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{4}', body):
        print(f"  [보안 차단] {job_code}: '국제 전화번호' 패턴 감지 → 게시 중단")
        passed = False

    # 이메일 — Bridge 공식 연락처(CL_CONTACT) 이외 이메일 차단
    all_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', body)
    external = [e for e in all_emails if e.lower() != CL_CONTACT.lower()]
    if external:
        print(f"  [보안 차단] {job_code}: '외부 이메일' 감지 {external} → 게시 중단")
        passed = False

    # 학원명/직함 키워드
    if re.search(r'어학원|학원원장|원장님|학원장', body):
        print(f"  [보안 차단] {job_code}: '학원명/직함' 패턴 감지 → 게시 중단")
        passed = False

    # 이름+직책 패턴 (예: 홍길동 원장, 김철수 팀장)
    if re.search(r'[가-힣]{2,4}\s*(?:원장|팀장|부장|과장|대리|주임|교감|교장|원감)', body):
        print(f"  [보안 차단] {job_code}: '이름+직책' 패턴 감지 → 게시 중단")
        passed = False

    # 사업자등록번호
    if re.search(r'\b\d{3}-\d{2}-\d{5}\b', body):
        print(f"  [보안 차단] {job_code}: '사업자등록번호' 패턴 감지 → 게시 중단")
        passed = False

    # 카카오톡 ID
    if re.search(r'(?:kakao(?:talk)?|카[카]?오?톡?|KaTalk|카톡)', body, re.I):
        print(f"  [보안 차단] {job_code}: '카카오톡 ID' 패턴 감지 → 게시 중단")
        passed = False

    # LINE ID
    if re.search(r'(?:LINE|라인)\s*(?:id)?[:：\s]*[\w.\-]{2,}', body, re.I):
        print(f"  [보안 차단] {job_code}: 'LINE ID' 패턴 감지 → 게시 중단")
        passed = False

    # URL 차단
    if re.search(r'(?:https?://|www\.)\S+', body, re.I):
        print(f"  [보안 차단] {job_code}: 'URL' 패턴 감지 → 게시 중단")
        passed = False

    # 회사/업체명
    if re.search(r'(?:주식회사|㈜|\(주\))|[\uac00-\ud7a3]+(?:컴퍼니|에듀|잉글리시|영어마을|어린이집)', body):
        print(f"  [보안 차단] {job_code}: '업체명' 패턴 감지 → 게시 중단")
        passed = False

    # SNS/메신저 ID (위챗, 텔레그램, 인스타)
    if re.search(r'(?:WeChat|위챗|Telegram|텔레그램|Instagram|인스타)', body, re.I):
        print(f"  [보안 차단] {job_code}: 'SNS/메신저 ID' 패턴 감지 → 게시 중단")
        passed = False

    # 팩스
    if re.search(r'(?:팩스|FAX|Fax)\s*[:：\s]*[\d\-\s]{8,}', body, re.I):
        print(f"  [보안 차단] {job_code}: '팩스번호' 패턴 감지 → 게시 중단")
        passed = False

    # 지번/도로명 상세주소
    if re.search(r'[가-힣]+[동리면읍]\s*\d+(?:-\d+)?|[가-힣]+(?:로|길)\s*\d+', body):
        print(f"  [보안 차단] {job_code}: '상세주소' 패턴 감지 → 게시 중단")
        passed = False

    return passed


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="BRIDGE Craigslist Auto RPA")
    parser.add_argument("--dry-run",   action="store_true", help="텍스트 출력만 (게시 없음)")
    parser.add_argument("--generate",  action="store_true", help="draft DB 저장만 (브라우저 없음)")
    parser.add_argument("--headless",  action="store_true", help="Headless Chrome (화면 없이 실행)")
    parser.add_argument("--diagnose",  action="store_true",
                        help="카테고리 페이지까지만 진행 → education 실제 value 자동 탐색 후 종료")
    parser.add_argument("--account",   default=None,
                        help="계정 ID (account1/account2/account3) → 해당 .env 로딩")
    parser.add_argument("--integrity-reset", nargs="?", const="", default=None,
                        help="파일 무결성 해시 재초기화 (비밀번호 필요: --integrity-reset 1234)")
    parser.add_argument("--job-code",  default=None)
    parser.add_argument("--limit",     type=int, default=10)
    args = parser.parse_args()

    # ── 무결성 해시 재초기화 ──
    if args.integrity_reset is not None:
        if args.integrity_reset == "1234":
            integrity_init()
            print("무결성 해시가 재초기화되었습니다.")
        else:
            print("  비밀번호가 틀렸습니다. 사용법: --integrity-reset 1234")
        return

    # ── 계정별 .env 재로딩 (--account 지정 시) ──
    if args.account:
        _load_account_env(args.account)
        # 환경변수 재읽기
        global CL_EMAIL, CL_PASSWORD, CL_CITY, CL_CONTACT, CL_BASE_URL
        CL_EMAIL    = os.getenv("CRAIGSLIST_EMAIL",    "")
        CL_PASSWORD = _decrypt_env_password(os.getenv("CRAIGSLIST_PASSWORD", ""))
        CL_CITY     = os.getenv("CRAIGSLIST_CITY",     "seoul")
        CL_CONTACT  = os.getenv("CRAIGSLIST_CONTACT",  "bridgejobkr@gmail.com")
        CL_BASE_URL = f"https://{CL_CITY}.craigslist.org"

    # ── 파일 무결성 체크 ──
    if not integrity_check():
        sys.exit(99)

    acct_label = args.account or "default"
    print("=" * 60)
    print("  BRIDGE Craigslist Auto RPA")
    print(f"  Target  : {CL_BASE_URL}")
    print(f"  Account : {acct_label} ({CL_EMAIL})")
    mode_str = ('DRY-RUN' if args.dry_run else
                'GENERATE' if args.generate else
                'DIAGNOSE' if args.diagnose else 'POST')
    print(f"  Mode    : {mode_str}")
    print("=" * 60)

    # ── DIAGNOSE 모드: 카테고리 페이지 DOM 분석 ──────────────────────────────
    if args.diagnose:
        if not CL_EMAIL or not CL_PASSWORD:
            print("[ERROR] .env 에 CRAIGSLIST_EMAIL / CRAIGSLIST_PASSWORD 필요")
            sys.exit(1)
        print("\n[DIAGNOSE] 로그인 후 카테고리 선택 페이지까지 진행합니다...")
        driver = build_driver(headless=False)
        try:
            if not cl_login(driver):
                print("[ABORT] 로그인 실패")
                sys.exit(1)
            driver.get(CL_BASE_URL)
            _delay(2, 3)
            try:
                link = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "post to classifieds"))
                )
                link.click(); _delay(2, 3)
            except Exception:
                driver.get("https://post.craigslist.org"); _delay(2, 3)

            # type 선택 (job offered)
            for _ in range(10):
                step = _step(driver.current_url)
                print(f"  현재 step: {step}")
                if step == "type":
                    try:
                        radio = driver.find_element(By.CSS_SELECTOR, "input[value='jo']")
                        _js_click(driver, radio); _delay(0.5, 1)
                    except Exception:
                        pass
                    _advance(driver, step)
                elif step in ("subarea", "cat", "subcat", "category", "subcatselect",
                              "cattype", "jobcat", "jobtype", "catselect"):
                    # 카테고리 페이지 도달 — DOM 분석
                    print("\n" + "="*55)
                    print("[DIAGNOSE] 카테고리 페이지 도달 — education 관련 요소 분석:")
                    result = driver.execute_script("""
                        var out = [];
                        // 모든 라디오 버튼
                        var radios = document.querySelectorAll('input[type=radio]');
                        radios.forEach(function(r) {
                            var lbl = '';
                            var forEl = document.querySelector('label[for="' + r.id + '"]');
                            if (forEl) lbl = forEl.textContent.trim();
                            else {
                                var p = r.parentElement;
                                if (p) lbl = p.textContent.trim().substring(0, 60);
                            }
                            out.push({type:'radio', value: r.value, id: r.id, label: lbl});
                        });
                        // 모든 링크 (a 태그)
                        var links = document.querySelectorAll('a');
                        links.forEach(function(a) {
                            var txt = a.textContent.trim();
                            var href = a.getAttribute('href') || '';
                            if (txt.length > 0 && txt.length < 80)
                                out.push({type:'link', text: txt, href: href});
                        });
                        return JSON.stringify(out, null, 2);
                    """)
                    try:
                        items = json.loads(result)
                        edu_items = [x for x in items if
                                     "edu" in json.dumps(x).lower() or
                                     "teach" in json.dumps(x).lower() or
                                     "tutor" in json.dumps(x).lower()]
                        print(f"education 관련 요소 {len(edu_items)}개:")
                        for item in edu_items:
                            print(f"  {item}")
                        print(f"\n전체 라디오 버튼 {sum(1 for x in items if x.get('type')=='radio')}개:")
                        for item in [x for x in items if x.get('type')=='radio']:
                            print(f"  value={item.get('value'):>5}  label={item.get('label','')[:50]}")
                    except Exception:
                        print(result[:2000])

                    # HTML 저장
                    dbg = _LOG_DIR / "debug_category_page.html"
                    dbg.write_text(driver.page_source, encoding="utf-8")
                    print(f"\n[DIAGNOSE] 전체 HTML 저장: {dbg}")
                    print("[DIAGNOSE] 위 value 값 확인 후 코드의 '102' 를 실제 값으로 수정하세요")
                    print("="*55)
                    break
                elif step in ("attr", "edit", "img", "preview", "done", "manage"):
                    print(f"  [DIAGNOSE] 카테고리 단계를 건너뜀 (step={step}) — 예상치 못한 흐름")
                    break
                else:
                    _advance(driver, step)
        finally:
            input("\n[DIAGNOSE] Enter 를 누르면 브라우저 종료...")
            driver.quit()
        return

    if not args.dry_run and not args.generate:
        if not CL_EMAIL or not CL_PASSWORD:
            print("[ERROR] .env 에 CRAIGSLIST_EMAIL / CRAIGSLIST_PASSWORD 필요")
            sys.exit(1)

    jobs = fetch_jobs(args.job_code, args.limit)
    print(f"\n대상 포지션: {len(jobs)}건\n")
    if not jobs:
        print("게시할 포지션 없음 (이미 전부 posted 또는 조건 없음)")
        return

    # 광고 생성 + PII 강제 치환 + 보안 검증
    ads: list[tuple[dict, str, str, int]] = []
    for job in jobs:
        title, body = generate_ad(job)

        # ── [REDACTED] 강제 치환 ───────────────────────────────────────────
        body_clean, removed = redact_pii(body, preserve_email=CL_CONTACT)
        if removed:
            # 보안: PII 실제 값은 로그에 절대 기록하지 않음 — 카테고리+개수만 기록
            redact_tags = [r.split("=")[0] for r in removed]
            tag_summary = ", ".join(set(redact_tags))
            print(f"  [REDACT] {job['job_code']}: {len(removed)}개 PII 항목 자동 치환 ({tag_summary})")
            _log_event("warn", job["job_code"], "redact",
                       f"{len(removed)} PII items redacted", {"tags": tag_summary})
            body = body_clean

        if args.dry_run:
            print(f"\n{'─'*55}")
            print(f"[{job['job_code']}] {job['city']} | {job['teaching_age']}")
            print(f"TITLE : {title}")
            print(body)
            continue

        # ── 최종 보안 검증 (redact 이후 잔류 PII 재확인) ──────────────────
        if not security_check(body, job["job_code"]):
            _log_event("error", job["job_code"], "security_check",
                       "PII survived redact — post blocked")
            continue

        ad_id = save_draft(job, title, body)
        ads.append((job, title, body, ad_id))
        print(f"  [DRAFT] {job['job_code']} → ad_posts id={ad_id}")

    if args.dry_run or args.generate:
        if args.generate:
            print(f"\n완료: {len(ads)}건 draft 저장")
        return

    # ── 잠금 파일 (중복 실행 방지) ──
    import atexit
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    atexit.register(lambda: LOCK_FILE.unlink(missing_ok=True))

    # 오버레이 알림 (설치되어 있으면 표시)
    try:
        from rpa_overlay import show_working, show_complete, update_progress, close as overlay_close, wants_more, stop_requested
        _HAS_OVERLAY = True
    except ImportError:
        _HAS_OVERLAY = False

    def _run_post_session(ad_list):
        """게시 세션 실행 (최초 + '더 올리기' 공통)."""
        hl_flag = args.headless
        print(f"\nChrome 시작... {len(ad_list)}건 게시 예정 (headless={hl_flag})")
        if _HAS_OVERLAY:
            show_working(current=0, total=len(ad_list), email=CL_EMAIL)
        driver = build_driver(headless=hl_flag)
        posted = 0

        try:
            if not cl_login(driver):
                print("[ABORT] 로그인 실패")
                _log_event("error", "—", "login", "Login failed — aborting session")
                return 0

            for i, (job, title, body, ad_id) in enumerate(ad_list, 1):
                if _HAS_OVERLAY and stop_requested():
                    print("\n[STOP] 사용자 중단 요청 — 게시 루프 종료")
                    _log_event("info", "—", "user_stop", "User requested stop via overlay")
                    break

                jcode = job["job_code"]
                print(f"\n{'='*55}")
                print(f"[{i}/{len(ad_list)}] {jcode} | {job.get('city')} | {job.get('teaching_age')}")

                try:
                    url = cl_post(driver, title, body, job)
                    ss  = take_screenshot(driver, jcode)

                    if url and url not in ("", "None", None):
                        mark_posted(ad_id, url, ss)
                        print(f"  ✅ 게시 완료: {url}")
                        print(f"  📸 스크린샷 : {ss}")
                        _log_event("info", jcode, "posted", "Post successful", {"url": url})
                        posted += 1
                        if _HAS_OVERLAY:
                            update_progress(posted, len(ad_list))
                    elif url is None:
                        mark_error(ad_id, "카테고리 선택 실패 — education 선택 불가, 게시 중단")
                        print(f"  ❌ 카테고리 선택 실패 → debug_category_page.html 확인")
                        _log_event("error", jcode, "category_abort",
                                   "cl_post returned None — education category not selected")
                    else:
                        mark_error(ad_id, "URL 획득 실패 (게시는 됐을 수 있음)")
                        print(f"  ⚠️  게시 URL 획득 실패 (이메일 인증 대기 중일 수 있음)")
                        _log_event("error", jcode, "post", "Posted URL not captured")

                except Exception as exc:
                    import traceback as _tb
                    err_msg = str(exc)[:300]
                    tb_str = _tb.format_exc()
                    mark_error(ad_id, err_msg)
                    _log_event("error", jcode, "post_exception", err_msg, {"traceback": tb_str[-500:]})
                    print(f"  ❌ 예외 발생 → 다음 건으로 이동: {exc}")
                    print(tb_str[-300:])
                    continue

                if i < len(ad_list):
                    wait = random.randint(30, 45)
                    countdown(wait, "다음 게시 대기")

        except Exception as session_exc:
            _log_event("error", "—", "session", f"Session-level exception: {session_exc}")
            print(f"[SESSION ERROR] {session_exc}")
        finally:
            driver.quit()

        return posted

    # ── 첫 게시 세션 ──
    total_posted = _run_post_session(ads)

    # ── 쿨다운 타임스탬프 기록 (수동 실행도 4시간 쿨다운 적용) ──
    if total_posted > 0:
        try:
            from scheduler import stamp_run
            acct_id = args.account or "default"
            stamp_run(acct_id)
            print(f"  [COOLDOWN] {acct_id} — 4시간 쿨다운 기록 완료")
        except Exception:
            pass

    print("\n" + "=" * 60)
    print(f"  완료: {total_posted}건 게시")
    print("=" * 60)

    if _HAS_OVERLAY:
        show_complete(posted_count=total_posted)

        # "5개 더 올리기" 대기 (최대 60초)
        import time as _time
        for _ in range(60):
            _time.sleep(1)
            if wants_more():
                print("\n[OVERLAY] 유저 요청: 5개 더 올리기!")
                overlay_close()

                extra_jobs = fetch_jobs(None, 5)
                if not extra_jobs:
                    print("추가 게시할 포지션 없음")
                    show_complete(posted_count=total_posted)
                    break

                extra_ads = []
                for job in extra_jobs:
                    title, body = generate_ad(job)
                    body_clean, removed = redact_pii(body, preserve_email=CL_CONTACT)
                    if removed:
                        body = body_clean
                    if not security_check(body, job["job_code"]):
                        continue
                    ad_id = save_draft(job, title, body)
                    extra_ads.append((job, title, body, ad_id))

                extra_posted = _run_post_session(extra_ads)
                total_posted += extra_posted
                print(f"\n추가 {extra_posted}건 완료 (총 {total_posted}건)")
                show_complete(posted_count=total_posted)
                break



if __name__ == "__main__":
    main()
