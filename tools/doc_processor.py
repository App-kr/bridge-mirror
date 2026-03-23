"""
BRIDGE Document Processor v2.3
후보자 이력서/커버레터에서 PII 삭제 + 강사번호 입력

사용법:
  python doc_processor.py setup                              # 폴더 구조 확인
  python doc_processor.py batch [--dry]                      # incoming/ 일괄 처리
  python doc_processor.py process <파일> --number 3057       # 단일 파일 처리
  python doc_processor.py download 3057                      # S3 다운로드+처리
  python doc_processor.py lookup "이름 또는 이메일"            # 후보자 검색
  python doc_processor.py init-db                            # file_uploads 테이블 생성

워크플로우:
  1) incoming/ 폴더에 파일 넣기 (파일명에 강사번호 포함: 3057_resume.pdf)
  2) batch --dry  → 미리보기 확인
  3) batch        → 처리 실행 (processed/ 에 결과, originals/ 에 원본 백업)
  4) 처리 완료 파일은 file_uploads 테이블에 자동 기록 (이력 추적)

지원 형식: .docx (서식 보존), .pdf (인-플레이스 redaction)
Python: "D:/Phtyon 3/python.exe"
의존성: python-docx, PyMuPDF (fitz), python-dotenv, cryptography, boto3(S3용)
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# ── 경로 ──────────────────────────────────────────────
BASE_DIR = Path("Q:/Claudework/bridge base")
DB_PATH = BASE_DIR / "master.db"
ENV_PATH = BASE_DIR / ".env"
DEFAULT_OUTPUT = BASE_DIR / "tools" / "processed_docs" / "processed"
INCOMING_DIR = BASE_DIR / "tools" / "processed_docs" / "incoming"
BACKUP_DIR = BASE_DIR / "tools" / "processed_docs" / "originals"
LOG_DIR = BASE_DIR / "tools" / "processed_docs" / "logs"


# ══════════════════════════════════════════════════════
#  1. DB 접근 + 암호화 처리
# ══════════════════════════════════════════════════════

_db_conn = None  # 세션 내 연결 재사용


def _get_db():
    """DB 연결 (세션 내 재사용)"""
    global _db_conn
    if _db_conn is None:
        if not DB_PATH.exists():
            print(f"[ERROR] DB not found: {DB_PATH}")
            sys.exit(1)
        _db_conn = sqlite3.connect(str(DB_PATH))
        _db_conn.row_factory = sqlite3.Row
    return _db_conn


def _try_decrypt(value):
    """암호화 필드 복호화 시도. 실패 시 원문 반환."""
    if not value or not value.strip():
        return value or ""
    try:
        # security_vault가 로드 가능할 때만 복호화 시도
        sys.path.insert(0, str(BASE_DIR))
        from dotenv import load_dotenv
        load_dotenv(str(ENV_PATH))
        from security_vault import decrypt_field
        return decrypt_field(value)
    except (ImportError, EnvironmentError):
        return value
    except (ValueError, Exception):
        # base64 디코딩 실패 등 → 평문으로 간주
        return value


def lookup_candidate(query: str):
    """이름/이메일로 후보자 검색"""
    db = _get_db()
    if "@" in query:
        rows = db.execute(
            "SELECT sheet_number, full_name, nationality, email "
            "FROM candidates WHERE email LIKE ? LIMIT 10",
            (f"%{query}%",),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT sheet_number, full_name, nationality, email "
            "FROM candidates WHERE full_name LIKE ? LIMIT 10",
            (f"%{query}%",),
        ).fetchall()
    return [(r[0], _try_decrypt(r[1]), _try_decrypt(r[2]), _try_decrypt(r[3])) for r in rows]


def get_candidate(number: int):
    """sheet_number로 후보자 조회 → dict or None"""
    db = _get_db()
    row = db.execute(
        "SELECT sheet_number, full_name, nationality, email, "
        "mobile_phone, kakaotalk, current_location, dob, gender "
        "FROM candidates WHERE sheet_number = ?",
        (number,),
    ).fetchone()
    if not row:
        return None
    return {
        "sheet_number": row[0],
        "full_name": _try_decrypt(row[1]),
        "nationality": _try_decrypt(row[2]),
        "email": _try_decrypt(row[3]),
        "mobile_phone": _try_decrypt(row[4]),
        "kakaotalk": _try_decrypt(row[5]),
        "current_location": _try_decrypt(row[6]),
        "dob": _try_decrypt(row[7]) if row[7] else "",
        "gender": _try_decrypt(row[8]) if row[8] else "",
    }


# 국적 영→한 매핑
_NAT_KR = {
    "american": "미국", "us": "미국", "usa": "미국", "united states": "미국",
    "british": "영국", "uk": "영국", "united kingdom": "영국", "english": "영국",
    "irish": "아일랜드", "ireland": "아일랜드", "n. ireland": "아일랜드",
    "northern irish": "아일랜드",
    "canadian": "캐나다", "canada": "캐나다",
    "australian": "호주", "australia": "호주",
    "new zealander": "뉴질랜드", "new zealand": "뉴질랜드", "kiwi": "뉴질랜드",
    "south african": "남아공", "south africa": "남아공",
    "filipino": "필리핀", "philippines": "필리핀",
    "indian": "인도", "india": "인도",
}

_GENDER_KR = {
    "male": "남", "m": "남", "남": "남", "남성": "남",
    "female": "여", "f": "여", "여": "여", "여성": "여",
}


def _is_cover_letter(filepath: Path) -> bool:
    """파일명으로 커버레터 여부 판별"""
    s = filepath.stem.lower()
    return any(kw in s for kw in (
        "cover letter", "coverletter", "cover_letter", "cl_", "cl ",
        "cl-", "커버레터", "커버", "자기소개",
    ))


def _merge_pdfs(cover_pdf: Path, resume_pdf: Path, output_pdf: Path):
    """커버레터 PDF + 이력서 PDF → 단일 PDF 병합"""
    import fitz
    merged = fitz.open()
    for src_path in [cover_pdf, resume_pdf]:
        if src_path and src_path.exists():
            src = fitz.open(str(src_path))
            merged.insert_pdf(src)
            src.close()
    merged.save(str(output_pdf), garbage=4, deflate=True)
    merged.close()


def _build_output_filename(number: int, candidate: dict = None, ext: str = ".docx") -> str:
    """출력 파일명: 3060영국_여(89born).docx"""
    nat_kr = ""
    gender_kr = ""
    birth_yr = ""

    if candidate:
        # 국적
        nat_raw = (candidate.get("nationality") or "").strip().lower()
        nat_kr = _NAT_KR.get(nat_raw, nat_raw[:4] if nat_raw else "")

        # 성별
        gen_raw = (candidate.get("gender") or "").strip().lower()
        gender_kr = _GENDER_KR.get(gen_raw, gen_raw[:1] if gen_raw else "")

        # 생년 (2자리)
        dob = (candidate.get("dob") or "").strip()
        if dob:
            # "1989-05-15", "1989", "89", "May 15, 1989" 등
            yr_match = re.search(r"(19|20)(\d{2})", dob)
            if yr_match:
                birth_yr = yr_match.group(2)
            elif re.match(r"^\d{2}$", dob):
                birth_yr = dob

    parts = [str(number)]
    if nat_kr:
        parts.append(nat_kr)
    if gender_kr:
        parts.append(f"_{gender_kr}")
    if birth_yr:
        parts.append(f"({birth_yr}born)")

    return "".join(parts) + ext


def find_candidate_by_email(email: str):
    """이메일로 후보자 검색 → dict or None (정확 매칭 우선, 없으면 LIKE)"""
    db = _get_db()
    _COLS = ("sheet_number, full_name, nationality, email, "
             "mobile_phone, kakaotalk, current_location, dob, gender")
    # 정확 매칭
    row = db.execute(
        f"SELECT {_COLS} FROM candidates WHERE email = ? LIMIT 1",
        (email,),
    ).fetchone()
    if not row:
        # 암호화된 이메일일 수 있으므로 전체 스캔 (느리지만 정확)
        rows = db.execute(
            f"SELECT {_COLS} FROM candidates WHERE email IS NOT NULL AND email != ''"
        ).fetchall()
        for r in rows:
            decrypted = _try_decrypt(r[3])
            if decrypted and decrypted.lower() == email.lower():
                row = r
                break
    if not row:
        return None
    return {
        "sheet_number": row[0],
        "full_name": _try_decrypt(row[1]),
        "nationality": _try_decrypt(row[2]),
        "email": _try_decrypt(row[3]),
        "mobile_phone": _try_decrypt(row[4]),
        "kakaotalk": _try_decrypt(row[5]),
        "current_location": _try_decrypt(row[6]),
        "dob": _try_decrypt(row[7]) if row[7] else "",
        "gender": _try_decrypt(row[8]) if row[8] else "",
    }


def _extract_emails_from_docx(filepath: Path) -> list[str]:
    """DOCX에서 이메일 주소 추출 (PII 삭제 전 원본에서)"""
    import docx
    doc = docx.Document(str(filepath))
    emails = set()
    all_text = []
    # 본문
    for p in doc.paragraphs:
        all_text.append(p.text)
    # 헤더/푸터
    for sec in doc.sections:
        if sec.header and sec.header.paragraphs:
            for p in sec.header.paragraphs:
                all_text.append(p.text)
        if sec.footer and sec.footer.paragraphs:
            for p in sec.footer.paragraphs:
                all_text.append(p.text)
    # 테이블
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    all_text.append(p.text)
    full = "\n".join(all_text)
    for m in RE_EMAIL.finditer(full):
        emails.add(m.group().lower())
    return list(emails)


# ══════════════════════════════════════════════════════
#  1b. file_uploads 테이블 (로컬 DB 이력 추적)
# ══════════════════════════════════════════════════════

_FILE_UPLOADS_DDL = """
CREATE TABLE IF NOT EXISTS file_uploads (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type   TEXT    NOT NULL DEFAULT 'candidate',
    entity_id     INTEGER,
    file_type     TEXT,
    file_url      TEXT,
    file_size     INTEGER DEFAULT 0,
    is_deleted    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
)
"""


def _ensure_file_uploads_table():
    """file_uploads 테이블이 없으면 생성 (IF NOT EXISTS)."""
    db = _get_db()
    db.execute(_FILE_UPLOADS_DDL)
    db.commit()


def _record_file_upload(entity_id: int, file_type: str, file_url: str, file_size: int = 0):
    """처리 완료 파일을 file_uploads 테이블에 INSERT."""
    _ensure_file_uploads_table()
    db = _get_db()
    db.execute(
        "INSERT INTO file_uploads (entity_type, entity_id, file_type, file_url, file_size) "
        "VALUES (?, ?, ?, ?, ?)",
        ("candidate", entity_id, file_type, file_url, file_size),
    )
    db.commit()


# ══════════════════════════════════════════════════════
#  2. PII 패턴 정의
# ══════════════════════════════════════════════════════

RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# 전화번호: 7자리+ 숫자를 포함하는 시퀀스만 (날짜·연도 충돌 방지)
RE_PHONE = re.compile(
    r"(?:\+?\d{1,3}[\s\-.]?)?\(?\d{2,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}\b"
)

RE_URL = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.I)

RE_LINKEDIN = re.compile(
    r"(?:linkedin\.com/in/[^\s<>\"']+|linkedin\s*:?\s*[^\s,;\n]+)", re.I
)

RE_KAKAO = re.compile(
    r"(?:kakao(?:talk)?|카카오(?:톡)?)\s*:?\s*[A-Za-z0-9._\-]+", re.I
)

RE_SNS = re.compile(
    r"(?:instagram|facebook|twitter|whatsapp|wechat|skype|telegram)"
    r"\s*:?\s*[@]?[A-Za-z0-9._\-]+",
    re.I,
)

RE_KR_ADDRESS = re.compile(
    r"(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)"
    r"(?:특별시|광역시|도|특별자치시|특별자치도)?"
    r"[\s]?(?:\S+(?:시|군|구|읍|면|동|리|로|길|번지)[\s]?){0,5}",
    re.UNICODE,
)

RE_PASSPORT = re.compile(r"\b[A-Z]{1,2}\d{7,8}\b")

# 영문 주소 패턴: "123 Street Name, City, ST 12345"
# 약어(St, Ct, Dr 등)는 오탐 심해서 전체 단어만 매칭
RE_EN_ADDRESS = re.compile(
    r"\d{1,5}\s+[\w\s.]{3,40}\b(?:Street|Avenue|Boulevard|Drive|"
    r"Road|Lane|Court|Place|Trail|Circle|Parkway|Highway)\b"
    r"[.,]?\s*(?:(?:Apt|Suite|Unit|#)\s*\w+[.,]?\s*)?"
    r"(?:\w[\w\s]*,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)?",
    re.I,
)

# 한국 도시/지역 키워드 (소문자)
KR_KEYWORDS = frozenset([
    "korea", "seoul", "busan", "daegu", "incheon", "gwangju",
    "daejeon", "ulsan", "sejong", "gyeonggi", "gangwon",
    "chungbuk", "chungnam", "jeonbuk", "jeonnam",
    "gyeongbuk", "gyeongnam", "jeju",
    "south korea", "republic of korea", "rok",
    "한국", "서울", "부산", "대구", "인천", "광주", "대전", "울산",
    "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
    "suwon", "seongnam", "goyang", "yongin", "changwon",
    "ansan", "anyang", "namyangju", "hwaseong", "pyeongtaek",
    "gimpo", "gwacheon", "uijeongbu", "paju", "yangju",
    "pocheon", "dongducheon", "guri", "hanam", "icheon",
    "osan", "gunpo", "uiwang", "siheung", "bucheon",
    "jeonju", "cheongju", "cheonan", "asan",
    "gimhae", "yangsan", "geoje", "tongyeong",
    "mokpo", "yeosu", "suncheon", "gwangyang",
    "gyeongju", "pohang", "andong", "gumi",
    "chuncheon", "wonju", "gangneung", "sokcho",
    "itaewon", "gangnam", "hongdae", "sinchon", "mapo",
    "jamsil", "songpa", "yongsan", "nowon", "bundang",
    "ilsan", "dongtan", "pangyo",
])

# PII 라벨 → 해당 줄 전체 삭제
# 주의: "line", "cell" 등 짧은 단어는 ":" 필수 조건으로 오탐 방지
PII_LINE_LABELS = [
    # 연락처 (colon 필수)
    ("email", True), ("e-mail", True),
    ("phone", True), ("telephone", True), ("mobile", True),
    ("cell", True), ("tel", True),
    ("korean telephone", True), ("u.k. telephone", True),
    ("uk telephone", True), ("us telephone", True),
    ("home phone", True), ("work phone", True), ("cell phone", True),
    ("contact", True), ("contact number", True),
    # 주소
    ("permanent address", True), ("home address", True),
    ("mailing address", True), ("address", True),
    ("current address", True),
    # SNS (colon 필수)
    ("kakao", True), ("kakaotalk", True),
    ("line id", True), ("line", True),
    ("skype", True), ("whatsapp", True),
    ("wechat", True), ("telegram", True),
    ("instagram", True), ("facebook", True), ("twitter", True),
    # 링크
    ("linkedin", True), ("website", True), ("personal website", True),
    ("portfolio", True),
    # 신원
    ("passport", True), ("passport number", True), ("passport no", True),
    ("date of birth", True), ("dob", True),
    ("national id", True), ("ssn", True),
    # 한국어
    ("이메일", True), ("전화", True), ("연락처", True),
    ("카카오", True), ("여권", True), ("주소", True),
]

# 위치 라벨 → 한국이면 "Korea"로 변환
LOCATION_LABELS = [
    "current location", "current address", "address", "location",
    "residence", "residing in", "living in", "based in",
    "city", "province", "country of residence",
    "현재 위치", "거주지", "주소", "현위치",
]

# 직장명 라벨 → 값 삭제 (institution/university 제외)
WORKPLACE_LABELS = [
    "current employer", "employer", "company", "workplace",
    "school name", "academy name", "hagwon",
    "현 직장", "근무지", "학원명", "학교명",
]

# 한국 학원/학교 키워드 (경력줄에서 한국 근무지 감지용)
KR_WORKPLACE_KEYWORDS = frozenset([
    # 대형 프랜차이즈
    "ecc", "ybm", "pagoda", "avalon", "chungdahm", "cdl", "jle",
    "poly", "sle", "aclipse", "epik", "gepik", "smoe", "jlec",
    "slp", "rise", "cdi", "bcm", "gnb", "iei", "ael", "tel",
    "hess", "ewha", "april", "top edu", "dada", "dadahak",
    "wonderland", "maple bear", "little america", "little fox",
    "english muse", "english plus", "emg education",
    "altiora", "bricks", "jungchul", "jeongchul",
    "sisa", "hansol", "daekyo", "kumon", "chungjae",
    "global adventure", "hampson", "engoo",
    # 일반 유형
    "english village", "language school", "language academy",
    "language institute", "language center", "language centre",
    "hagwon", "학원", "어학원", "영어학원", "유치원", "어린이집",
    "elementary school", "middle school", "high school",
    "international school", "kindergarten", "preschool",
    "after-school", "afterschool", "after school",
    "private academy", "teaching academy", "english academy",
])

# 경력줄에서 한국 근무 상세 축약 패턴
# "YBM ECC, Uijeongbu, South Korea, March 2021 - Sept 2022" → "South Korea, March 2021 - Sept 2022"
# 날짜 패턴: "Jan 2021", "2021-2023", "March 2021 - Sept 2022", "2021 - Present"
_MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
RE_DATE_RANGE = re.compile(
    r"(?:,\s*)?"
    r"(" + _MONTH + r"\.?\s*)?"
    r"(\d{4})"
    r"(?:\s*[-\u2013~]\s*"
    r"(?:" + _MONTH + r"\.?\s*)?"
    r"(?:\d{4}|[Pp]resent|[Cc]urrent)"
    r")?",
    re.I,
)


# ══════════════════════════════════════════════════════
#  3. PII 삭제 엔진
# ══════════════════════════════════════════════════════

def _is_korea(text: str) -> bool:
    lower = text.lower().strip()
    return any(kw in lower for kw in KR_KEYWORDS)


def _name_variants(full_name: str) -> list[str]:
    """
    이름의 모든 인식 가능 변형 생성.
    - 풀네임, First Last, Last First, 각 단어(3글자 이상만)
    - 세미콜론/괄호 별명 처리
    긴 변형부터 정렬 (greedy 매칭)
    """
    if not full_name or not full_name.strip():
        return []

    raw = full_name.strip()
    variants = set()
    variants.add(raw)

    # 별명 분리: "Jashen Arianne ; Shen" → main + nickname
    main_name = raw
    if ";" in raw:
        parts = raw.split(";", 1)
        main_name = parts[0].strip()
        nick = parts[1].strip()
        variants.add(main_name)
        if nick and len(nick) > 2:
            variants.add(nick)

    if "(" in main_name:
        clean = re.sub(r"\s*\([^)]*\)", "", main_name).strip()
        nick_m = re.search(r"\(([^)]+)\)", main_name)
        variants.add(clean)
        if nick_m and len(nick_m.group(1)) > 2:
            variants.add(nick_m.group(1))
        main_name = clean

    words = main_name.split()

    if len(words) >= 2:
        # First Last
        variants.add(f"{words[0]} {words[-1]}")
        # Last, First
        variants.add(f"{words[-1]}, {words[0]}")
        # Last First
        variants.add(f"{words[-1]} {words[0]}")
        # 모든 인접 2-word 조합 (중간이름 포함)
        for i in range(len(words) - 1):
            variants.add(f"{words[i]} {words[i+1]}")

    # 개별 단어 (3글자 이상만, 너무 짧으면 오탐)
    for w in words:
        if len(w) >= 3:
            variants.add(w)

    # 긴 것부터 매칭 (greedy)
    return sorted(variants, key=len, reverse=True)


def _should_skip_line(stripped_lower: str) -> bool:
    """PII 라벨로 시작하는 줄인지 판별"""
    for label, needs_colon in PII_LINE_LABELS:
        if not stripped_lower.startswith(label):
            continue
        rest = stripped_lower[len(label):]
        if not rest:
            return True  # 라벨만 있는 줄
        first_char = rest.lstrip()[0] if rest.lstrip() else ""
        if needs_colon and first_char == ":":
            return True
        if not needs_colon:
            if first_char in (":", " "):
                return True
    return False


def remove_pii(text: str, candidate: dict = None) -> tuple[str, list[str]]:
    """
    텍스트에서 PII 삭제.
    Returns: (cleaned_text, list[삭제 로그])
    """
    log = []

    # ── Pass 1: 줄 단위 PII 라벨 삭제 ──
    lines = text.split("\n")
    kept_lines = []
    for line in lines:
        stripped = line.strip().lower()
        if stripped and _should_skip_line(stripped):
            log.append(f"LINE_DEL: {line.strip()[:80]}")
            continue
        kept_lines.append(line)
    result = "\n".join(kept_lines)

    # ── Pass 2: regex 기반 인라인 삭제 ──
    def _sub(pattern, repl, tag):
        nonlocal result
        def replacer(m):
            log.append(f"{tag}: {m.group()[:60]}")
            return repl
        result = pattern.sub(replacer, result)

    # 여권 먼저 (전화번호 regex와 숫자 충돌 방지)
    _sub(RE_PASSPORT, "", "PASSPORT")
    _sub(RE_EMAIL, "", "EMAIL")
    _sub(RE_LINKEDIN, "", "LINKEDIN")
    _sub(RE_KAKAO, "", "KAKAO")
    _sub(RE_SNS, "", "SNS")
    _sub(RE_URL, "", "URL")

    # 전화번호 (7자리+ 숫자만)
    def phone_replacer(m):
        digits = re.sub(r"\D", "", m.group())
        if len(digits) >= 7:
            log.append(f"PHONE: {m.group()[:40]}")
            return ""
        return m.group()
    result = RE_PHONE.sub(phone_replacer, result)

    # 한국 주소 → "Korea"
    def addr_replacer(m):
        log.append(f"KR_ADDR→Korea: {m.group()[:40]}")
        return "Korea"
    result = RE_KR_ADDRESS.sub(addr_replacer, result)

    # 영문 주소 삭제 (거리+도시+주/zip)
    _sub(RE_EN_ADDRESS, "", "EN_ADDR")

    # ── Pass 2.5: 한국 관련 줄 처리 ──
    lines2 = result.split("\n")
    kept_lines2 = []
    for line in lines2:
        stripped = line.strip()
        s_lower = stripped.lower()
        # 한국 키워드가 포함된 줄인지 확인
        has_kr = any(kw in s_lower for kw in KR_KEYWORDS)
        has_kr_work = any(kw in s_lower for kw in KR_WORKPLACE_KEYWORDS)

        if has_kr:
            # Case 1: 경력줄 — "YBM ECC, Uijeongbu, South Korea, March 2021"
            if has_kr_work:
                date_match = RE_DATE_RANGE.search(stripped)
                if date_match:
                    date_str = date_match.group(0).strip()
                    log.append(f"KR_EXP_REDACT: {stripped[:80]}")
                    kept_lines2.append(f"South Korea, {date_str}")
                    continue

            # Case 2: 위치셀 — "Busan, South Korea" 또는 "Masan, S. Korea"
            # 한국 도시명 제거 → "South Korea"만
            kr_loc_match = re.match(
                r"^[\w\s-]*(?:" + "|".join(re.escape(kw) for kw in KR_KEYWORDS if len(kw) > 2) + r").*$",
                s_lower,
            )
            if kr_loc_match and len(stripped) < 50:
                # 날짜가 같은 줄에 있으면 유지
                date_match = RE_DATE_RANGE.search(stripped)
                if date_match:
                    log.append(f"KR_LOC_CLEAN: {stripped[:60]}")
                    kept_lines2.append(f"South Korea, {date_match.group(0).strip()}")
                else:
                    log.append(f"KR_LOC_CLEAN: {stripped[:60]}")
                    kept_lines2.append("South Korea")
                continue

        # Case 3: 한국 학원명만 있는 줄 (korea 키워드 없이) — "POLY", "TOP Edu"
        if has_kr_work and not has_kr and len(stripped) < 40:
            # 학원명만 단독으로 있는 짧은 줄 → 삭제
            log.append(f"KR_ACADEMY_DEL: {stripped[:40]}")
            continue

        # Case 4: 긴 문장 내 한국 업체명 인라인 삭제 (커버레터 본문)
        # "I taught at POLY in Busan" → "I taught in South Korea"
        if has_kr_work and len(stripped) >= 40:
            modified = stripped
            for kw in KR_WORKPLACE_KEYWORDS:
                pat = re.compile(
                    r"(?:at|for|with|in)\s+" + re.escape(kw) + r"(?:\s+(?:in|at|,))?",
                    re.I,
                )
                if pat.search(modified):
                    log.append(f"KR_INLINE_DEL: {kw}")
                    modified = pat.sub("in", modified)
                # 단독 등장도 제거 (대소문자 무시, 단어 경계)
                pat2 = re.compile(r"\b" + re.escape(kw) + r"\b", re.I)
                if pat2.search(modified):
                    modified = pat2.sub("", modified)
            # 한국 도시명도 인라인 제거
            for city in KR_KEYWORDS:
                if len(city) > 2 and city.lower() not in ("korea", "south korea", "rok",
                        "republic of korea", "한국"):
                    city_pat = re.compile(r"\b" + re.escape(city) + r"\b", re.I)
                    if city_pat.search(modified):
                        log.append(f"KR_CITY_DEL: {city}")
                        modified = city_pat.sub("", modified)
            # 잔여 정리: 이중 공백, 쉼표 연속, "in in"
            modified = re.sub(r"\s{2,}", " ", modified)
            modified = re.sub(r",\s*,", ",", modified)
            modified = re.sub(r"\bin\s+in\b", "in", modified)
            modified = re.sub(r",\s*\.", ".", modified)
            modified = modified.strip()
            if modified != stripped:
                kept_lines2.append(modified)
                continue

        kept_lines2.append(line)
    result = "\n".join(kept_lines2)

    # ── Pass 3: 후보자별 PII (DB에서 가져온 값) ──
    if candidate:
        name = candidate.get("full_name", "")
        if name:
            for variant in _name_variants(name):
                pat = re.compile(re.escape(variant), re.IGNORECASE)
                if pat.search(result):
                    log.append(f"NAME: {variant}")
                    result = pat.sub("", result)

        # DB에서 가져온 이메일/전화/카카오도 직접 삭제
        for field in ("email", "mobile_phone", "kakaotalk"):
            val = candidate.get(field, "")
            if val and len(val) > 2:
                escaped = re.escape(val)
                if re.search(escaped, result, re.I):
                    log.append(f"DB_{field.upper()}: {val[:30]}")
                    result = re.sub(escaped, "", result, flags=re.I)

    # ── Pass 4: 위치/직장 라벨 값 처리 ──
    for label in LOCATION_LABELS:
        pat = re.compile(rf"({re.escape(label)}\s*:?\s*)(.+)", re.I)
        def _loc_rep(m):
            prefix, value = m.group(1), m.group(2).strip()
            if _is_korea(value):
                log.append(f"LOC→Korea: {value[:40]}")
                return f"{prefix}Korea"
            return m.group(0)
        result = pat.sub(_loc_rep, result)

    for label in WORKPLACE_LABELS:
        pat = re.compile(rf"({re.escape(label)}\s*:?\s*)(.+)", re.I)
        def _work_rep(m):
            log.append(f"WORKPLACE_DEL: {m.group(2).strip()[:40]}")
            return m.group(1)
        result = pat.sub(_work_rep, result)

    # 빈줄 정리
    result = re.sub(r"\n{3,}", "\n\n", result)
    # 빈 라벨줄 정리 (라벨: 만 남은 줄)
    result = re.sub(r"^[ \t]*\w[\w\s]*:\s*$", "", result, flags=re.MULTILINE)
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result, log


# ══════════════════════════════════════════════════════
#  4. DOCX 처리 (서식 보존)
# ══════════════════════════════════════════════════════

def _replace_in_runs(paragraph, cleaned_text):
    """
    단락의 run들에서 텍스트를 교체하되 서식을 최대한 보존.
    전략: 각 run의 텍스트 내에서 PII 부분만 교체.
    """
    runs = paragraph.runs
    if not runs:
        return

    original_full = "".join(r.text for r in runs)
    if not original_full.strip():
        return

    # 삭제된 텍스트가 없으면 스킵
    if original_full == cleaned_text:
        return

    # run이 1개면 단순 교체 (서식 유지)
    if len(runs) == 1:
        runs[0].text = cleaned_text
        return

    # run이 여러개: cleaned_text를 run 경계에 맞춰 분배
    # 전략: 각 run의 원래 길이 비율로 배분
    # 단, PII가 run 경계를 걸칠 수 있으므로 최선의 근사치 사용
    # cleaned가 비면 모든 run을 비움
    if not cleaned_text.strip():
        for r in runs:
            r.text = ""
        return

    # 원문과 cleaned의 공통 접두사/접미사 기반 매칭
    # 실용적 접근: 첫 run에 전체 cleaned, 나머지 비움
    # (완벽한 run-level 매칭은 diff 알고리즘이 필요하여 실무 대비 과도)
    #
    # 개선: 각 run의 텍스트가 cleaned에 그대로 존재하면 유지,
    #       아니면 cleaned에서 해당 위치 텍스트 추출
    pos = 0
    remaining = cleaned_text
    for i, run in enumerate(runs):
        orig_len = len(run.text)
        if i == len(runs) - 1:
            # 마지막 run에 나머지 전부
            run.text = remaining
        else:
            # 원래 run의 텍스트가 remaining 시작부에 있으면 유지
            if remaining.startswith(run.text):
                remaining = remaining[orig_len:]
            else:
                # PII가 이 run에 있었음 → 이 run 비우고 다음으로
                run.text = ""


def _extract_names_from_filename(filepath: Path) -> list[str]:
    """파일명에서 사람 이름 추출. 'Resume-DoniaBland2026 (1) - Donia Bland.docx' → ['Donia Bland', ...]"""
    stem = filepath.stem
    # " - Name" 패턴 (가장 흔함)
    parts = re.split(r"\s*-\s*", stem)
    names = []
    for part in parts:
        # 숫자만/키워드만 제외
        clean = re.sub(r"\(\d+\)", "", part).strip()
        clean = re.sub(r"\d{4,}", "", clean).strip()
        if clean.lower() in ("resume", "cv", "cover letter", "coverletter", ""):
            continue
        # 2단어 이상이면 이름으로 간주
        words = clean.split()
        if len(words) >= 2 and all(w[0].isupper() for w in words if w):
            names.append(clean)
            # 개별 단어도 추가 (3글자 이상)
            for w in words:
                if len(w) >= 3:
                    names.append(w)
    return names


def _find_photo_for_candidate(filepath: Path) -> Path | None:
    """incoming 폴더에서 같이 넣은 사진 파일 찾기 (JPG/PNG)"""
    incoming = filepath.parent
    photo_exts = {".jpg", ".jpeg", ".png"}
    # 1) 같은 번호로 시작하는 사진
    stem_numbers = re.findall(r"(\d{3,5})", filepath.stem)
    for f in incoming.iterdir():
        if f.suffix.lower() in photo_exts:
            for num in stem_numbers:
                if num in f.stem:
                    return f
    # 2) incoming에 사진이 1개만 있으면 그거
    photos = [f for f in incoming.iterdir() if f.suffix.lower() in photo_exts]
    if len(photos) == 1:
        return photos[0]
    # 3) processed_docs 폴더에서도 찾기
    proc_parent = incoming.parent
    for subdir in [proc_parent / "incoming", proc_parent]:
        if not subdir.exists():
            continue
        for f in subdir.iterdir():
            if f.suffix.lower() in photo_exts:
                for num in stem_numbers:
                    if num in f.stem:
                        return f
    return None


def process_docx(filepath: Path, brj_number: int, candidate: dict = None,
                 dry: bool = False, photo_path: Path = None):
    """DOCX 처리: PII 삭제 + 번호/사진 삽입. Returns (doc, log_entries)"""
    import docx
    from docx.shared import Pt, Inches, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = docx.Document(str(filepath))
    all_logs = []

    # 파일명에서 이름 추출 (DB 불일치 대비)
    filename_names = _extract_names_from_filename(filepath)

    def _process_paragraphs(paragraphs, section_name="body"):
        for para in paragraphs:
            original = para.text
            if not original.strip():
                continue
            cleaned, log = remove_pii(original, candidate)
            # 파일명에서 추출한 이름도 삭제
            for fn_name in filename_names:
                pat = re.compile(re.escape(fn_name), re.I)
                if pat.search(cleaned):
                    log.append(f"FILENAME_NAME: {fn_name}")
                    cleaned = pat.sub("", cleaned)
            if cleaned != original:
                all_logs.extend([f"[{section_name}] {l}" for l in log])
                if not dry:
                    # South Korea → 볼드 처리
                    if "South Korea" in cleaned:
                        _replace_with_bold_korea(para, cleaned)
                    else:
                        _replace_in_runs(para, cleaned)
                    # 하이퍼링크/필드코드 등 runs에 안 잡히는 요소 강제 클리어
                    if not cleaned.strip() and para.text.strip():
                        from docx.oxml.ns import qn
                        for child in list(para._element):
                            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                            if tag in ("hyperlink", "r", "fldSimple", "smartTag"):
                                para._element.remove(child)

    # 헤더/푸터 — 전체 삭제 (이름/주소/연락처 모두 비움)
    def _clean_header_footer(paragraphs, section_name="header"):
        for para in paragraphs:
            original = para.text
            if not original.strip():
                continue
            all_logs.append(f"[{section_name}] HDR_CLEAR: {original.strip()[:60]}")
            if not dry:
                for run in para.runs:
                    run.text = ""

    # 본문
    _process_paragraphs(doc.paragraphs, "body")

    # 테이블
    for ti, table in enumerate(doc.tables):
        for row in table.rows:
            for cell in row.cells:
                _process_paragraphs(cell.paragraphs, f"table{ti}")

    # 헤더/푸터 — 전체 삭제
    for si, section in enumerate(doc.sections):
        for hf_name, hf in [("header", section.header), ("footer", section.footer)]:
            if hf and hf.paragraphs:
                _clean_header_footer(hf.paragraphs, f"{hf_name}{si}")
        try:
            fph = section.first_page_header
            if fph and fph.paragraphs:
                _clean_header_footer(fph.paragraphs, f"first_header{si}")
        except Exception:
            pass
        try:
            fpf = section.first_page_footer
            if fpf and fpf.paragraphs:
                _clean_header_footer(fpf.paragraphs, f"first_footer{si}")
        except Exception:
            pass

    # 문서 메타데이터 클리어 (이름/제목 제거)
    try:
        cp = doc.core_properties
        cp.title = ""
        cp.author = ""
        cp.subject = ""
        cp.keywords = ""
        cp.comments = ""
        cp.last_modified_by = ""
    except Exception:
        pass

    # 번호 + 사진 삽입 (최상단)
    if not dry:
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement

        photo = photo_path or _find_photo_for_candidate(filepath)
        body = doc.element.body

        # 기존 본문 이미지 모두 제거 (프로필 사진 중복 방지)
        for drawing in body.findall('.//' + qn('w:drawing')):
            parent = drawing.getparent()
            if parent is not None:
                parent.remove(drawing)
                all_logs.append("[photo] 기존 이미지 제거")
        for pict in body.findall('.//' + qn('w:pict')):
            parent = pict.getparent()
            if parent is not None:
                parent.remove(pict)

        # 1행 2열 테이블: [번호 | 사진]
        tbl = doc.add_table(rows=1, cols=2)
        tbl.autofit = True
        # 테두리 없음
        tbl_pr = tbl._element.tblPr
        borders = tbl_pr.find(qn("w:tblBorders"))
        if borders is not None:
            tbl_pr.remove(borders)

        # 왼쪽: 번호 (크고 굵게)
        left_cell = tbl.cell(0, 0)
        left_cell.text = ""
        p_num = left_cell.paragraphs[0]
        run_num = p_num.add_run(str(brj_number))
        run_num.bold = True
        run_num.font.size = Pt(28)
        run_num.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

        # 오른쪽: 사진
        right_cell = tbl.cell(0, 1)
        right_cell.text = ""
        p_photo = right_cell.paragraphs[0]
        p_photo.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if photo and photo.exists():
            run_photo = p_photo.add_run()
            run_photo.add_picture(str(photo), height=Cm(3.5))
            all_logs.append(f"[photo] 삽입: {photo.name}")
        else:
            all_logs.append("[photo] 사진 없음 (스킵)")

        # body의 맨 앞 자식 앞에 삽입 (테이블/단락 무관하게 최상단)
        first_child = body[0] if len(body) > 0 else None
        if first_child is not None:
            first_child.addprevious(tbl._element)
        else:
            body.append(tbl._element)

    return doc, all_logs


def _replace_with_bold_korea(para, cleaned_text: str):
    """South Korea를 볼드로 처리하여 단락에 삽입"""
    from docx.shared import Pt, RGBColor
    # 기존 runs의 서식 복사용 (첫 run의 font 정보 보존)
    base_font_size = None
    if para.runs:
        base_font_size = para.runs[0].font.size
    # 기존 runs 텍스트 비우기
    for run in para.runs:
        run.text = ""
    # South Korea 기준으로 분할하여 새 run 추가
    parts = cleaned_text.split("South Korea")
    for i, part in enumerate(parts):
        if part:
            run = para.add_run(part)
            if base_font_size:
                run.font.size = base_font_size
        if i < len(parts) - 1:
            kr_run = para.add_run("South Korea")
            kr_run.bold = True
            kr_run.font.size = base_font_size or Pt(11)
            kr_run.font.color.rgb = RGBColor(0, 0, 0)


# ══════════════════════════════════════════════════════
#  5. PDF 처리 (인-플레이스 redaction)
# ══════════════════════════════════════════════════════

def process_pdf(filepath: Path, brj_number: int, candidate: dict = None, dry: bool = False):
    """
    PDF 처리: PyMuPDF redaction으로 PII를 흰색 사각형으로 덮기.
    원본 서식/이미지/레이아웃 보존.
    Returns (output_path or None, log_entries)
    """
    import fitz

    doc = fitz.open(str(filepath))
    all_logs = []

    # 모든 PII 패턴을 수집
    pii_patterns = _build_search_patterns(candidate)

    # 파일명에서 이름 추출 (DB 불일치 대비)
    filename_names = _extract_names_from_filename(filepath)

    for page_num, page in enumerate(doc):
        text = page.get_text()

        # 줄 단위 PII 라벨 검사 → redact 대상 텍스트 수집
        redact_texts = set()

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue

            # PII 라벨 줄 → 전체 줄 redact
            if _should_skip_line(stripped.lower()):
                redact_texts.add(stripped)
                all_logs.append(f"[page{page_num}] LINE_DEL: {stripped[:60]}")
                continue

        # regex 패턴 매칭
        for pattern, tag in pii_patterns:
            for m in pattern.finditer(text):
                matched = m.group().strip()
                if matched and len(matched) > 1:
                    redact_texts.add(matched)
                    all_logs.append(f"[page{page_num}] {tag}: {matched[:60]}")

        # 후보자 이름 매칭
        if candidate and candidate.get("full_name"):
            for variant in _name_variants(candidate["full_name"]):
                if variant.lower() in text.lower():
                    redact_texts.add(variant)
                    all_logs.append(f"[page{page_num}] NAME: {variant}")

        # 파일명 기반 이름도 redact
        for fn_name in filename_names:
            if fn_name.lower() in text.lower():
                redact_texts.add(fn_name)
                all_logs.append(f"[page{page_num}] FILENAME_NAME: {fn_name}")

        # ── 한국 학원명/도시명 redact (한국 맥락 있을 때만) ──
        # 페이지 전체에 한국 관련 키워드가 있는지 먼저 확인
        page_lower = text.lower()
        page_has_korea = any(kw in page_lower for kw in
            ("korea", "한국", "seoul", "busan", "서울", "부산"))

        keep_keywords = {"korea", "south korea", "rok", "republic of korea", "한국"}
        # 한국 맥락이 없으면 학원명 redact 스킵 (미국 high school 등 오탐 방지)
        if page_has_korea:
            for line in text.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                s_lower = stripped.lower()
                has_kr = any(kw in s_lower for kw in KR_KEYWORDS)
                has_kr_work = any(kw in s_lower for kw in KR_WORKPLACE_KEYWORDS)

                # 같은 줄에 한국 키워드+학원명 → 학원명 redact
                if has_kr_work and has_kr:
                    for kw in KR_WORKPLACE_KEYWORDS:
                        kw_pat = re.compile(r"\b" + re.escape(kw) + r"\b", re.I)
                        for m in kw_pat.finditer(stripped):
                            redact_texts.add(m.group())
                            all_logs.append(f"[page{page_num}] KR_ACADEMY: {m.group()}")

                # 한국 도시명 redact (korea 자체는 유지)
                if has_kr:
                    for city in KR_KEYWORDS:
                        if len(city) <= 2 or city.lower() in keep_keywords:
                            continue
                        city_pat = re.compile(r"\b" + re.escape(city) + r"\b", re.I)
                        for m in city_pat.finditer(stripped):
                            redact_texts.add(m.group())
                            all_logs.append(f"[page{page_num}] KR_CITY: {m.group()}")

        # 위치 라벨 → 값만 redact (Korea 대체 텍스트 삽입)
        # 직장명 라벨 → 값만 redact
        replacement_redacts = []

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            s_lower = stripped.lower()

            # 위치: "Current Location: Seoul, South Korea" → redact → "Korea"
            for label in LOCATION_LABELS:
                pat = re.match(rf"({re.escape(label)}\s*:?\s*)(.+)", s_lower)
                if pat and _is_korea(pat.group(2)):
                    label_end = len(pat.group(1))
                    value_text = stripped[label_end:].strip()
                    if value_text:
                        replacement_redacts.append((value_text, "Korea"))
                        all_logs.append(f"[page{page_num}] LOC→Korea: {value_text[:40]}")

            # 직장명: "Current Employer: YBM Academy" → redact (빈 대체)
            for label in WORKPLACE_LABELS:
                pat = re.match(rf"({re.escape(label)}\s*:?\s*)(.+)", s_lower)
                if pat:
                    label_end = len(pat.group(1))
                    value_text = stripped[label_end:].strip()
                    if value_text:
                        redact_texts.add(value_text)
                        all_logs.append(f"[page{page_num}] WORK_REDACT: {value_text[:40]}")

        if dry:
            continue

        # Redact 적용 — 일반 (흰색 덮기)
        for target in redact_texts:
            instances = page.search_for(target)
            for rect in instances:
                page.add_redact_annot(rect, fill=(1, 1, 1))

        # Redact 적용 — 대체 텍스트 삽입 (위치→Korea)
        for target, replacement in replacement_redacts:
            instances = page.search_for(target)
            for rect in instances:
                page.add_redact_annot(
                    rect, text=replacement, fill=(1, 1, 1),
                    text_color=(0, 0, 0), fontsize=10,
                )

        if redact_texts or replacement_redacts:
            page.apply_redactions()

    # 번호 삽입 (첫 페이지 최상단)
    if not dry and len(doc) > 0:
        first_page = doc[0]
        rect = fitz.Rect(50, 15, 300, 45)
        first_page.draw_rect(rect, color=None, fill=(1, 1, 1))
        first_page.insert_text(
            fitz.Point(50, 38),
            str(brj_number),
            fontsize=20,
            fontname="helv",
            color=(0, 0, 0),
        )

    # PDF 메타데이터 클리어 (이름/제목 제거)
    if not dry:
        doc.set_metadata({
            "title": "", "author": "", "subject": "",
            "keywords": "", "creator": "", "producer": "",
        })

    return doc, all_logs


def _build_search_patterns(candidate: dict = None):
    """PDF redaction용 검색 패턴 목록 생성"""
    patterns = [
        (RE_EMAIL, "EMAIL"),
        (RE_LINKEDIN, "LINKEDIN"),
        (RE_KAKAO, "KAKAO"),
        (RE_SNS, "SNS"),
        (RE_URL, "URL"),
        (RE_PASSPORT, "PASSPORT"),
        (RE_KR_ADDRESS, "KR_ADDR"),
        (RE_EN_ADDRESS, "EN_ADDR"),
    ]

    # 전화번호는 별도 처리 (7자리+ 필터)
    re_phone_strict = re.compile(
        r"(?:\+?\d{1,3}[\s\-.]?)?\(?\d{2,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}"
    )
    patterns.append((re_phone_strict, "PHONE"))

    # 후보자 DB 정보
    if candidate:
        for field in ("email", "mobile_phone", "kakaotalk"):
            val = candidate.get(field, "")
            if val and len(val) > 3:
                patterns.append((re.compile(re.escape(val), re.I), f"DB_{field.upper()}"))

    return patterns


# ══════════════════════════════════════════════════════
#  6. 파일 저장 + 백업 + 로그
# ══════════════════════════════════════════════════════

def _convert_docx_to_pdf(docx_path: Path, pdf_path: Path) -> bool:
    """DOCX → PDF 변환 (Word COM 자동화). 성공 시 True."""
    try:
        import comtypes.client
        word = comtypes.client.CreateObject("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(docx_path.resolve()))
        doc.SaveAs(str(pdf_path.resolve()), FileFormat=17)  # 17 = wdFormatPDF
        doc.Close()
        word.Quit()
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"  [PDF WARN] COM 변환 실패: {e}")
    # fallback: docx2pdf
    try:
        from docx2pdf import convert
        convert(str(docx_path), str(pdf_path))
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"  [PDF WARN] docx2pdf 실패: {e}")
    # fallback: LibreOffice
    try:
        import subprocess
        lo_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        lo = next((p for p in lo_paths if Path(p).exists()), None)
        if lo:
            subprocess.run(
                [lo, "--headless", "--convert-to", "pdf",
                 "--outdir", str(pdf_path.parent), str(docx_path)],
                capture_output=True, timeout=60,
            )
            # LibreOffice는 원본 이름으로 저장하므로 rename
            lo_out = pdf_path.parent / (docx_path.stem + ".pdf")
            if lo_out.exists() and lo_out != pdf_path:
                lo_out.rename(pdf_path)
            return pdf_path.exists()
    except Exception as e:
        print(f"  [PDF WARN] LibreOffice 실패: {e}")
    print("  [PDF FAIL] PDF 변환 불가 — comtypes/docx2pdf/LibreOffice 모두 없음")
    print("             pip install comtypes 또는 pip install docx2pdf 로 설치")
    return False


def backup_original(filepath: Path):
    """원본 → originals/ 복사"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"{ts}_{filepath.name}"
    shutil.copy2(str(filepath), str(dest))
    return dest


def save_log(filepath, brj_number: int, logs: list[str]):
    """삭제 로그 저장"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stem = filepath.stem if isinstance(filepath, Path) else str(filepath).replace("#", "")
    log_path = LOG_DIR / f"BRJ{brj_number}_{stem}.json"
    data = {
        "source": str(filepath),
        "brj_number": brj_number,
        "processed_at": datetime.now().isoformat(),
        "removals": logs,
        "total_removals": len(logs),
    }
    log_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return log_path


def auto_detect_candidate(filepath: Path):
    """파일명에서 강사번호 자동 감지"""
    stem = filepath.stem
    # 파일명에서 3-5자리 숫자 추출
    numbers = re.findall(r"(\d{3,5})", stem)
    for num_str in numbers:
        candidate = get_candidate(int(num_str))
        if candidate:
            return candidate
    return None


# ══════════════════════════════════════════════════════
#  7. CLI 명령어
# ══════════════════════════════════════════════════════

def cmd_process(args):
    """process 명령"""
    input_path = Path(args.input)
    output_dir = Path(args.output) if args.output else DEFAULT_OUTPUT
    brj_number = args.number
    dry = args.dry

    if not input_path.exists():
        print(f"[ERROR] Path not found: {input_path}")
        sys.exit(1)

    # 파일 목록
    if input_path.is_file():
        files = [input_path]
    else:
        files = sorted(
            f for f in input_path.iterdir()
            if f.suffix.lower() in (".docx", ".pdf")
            and not f.name.startswith("~")
            and not f.name.startswith(".")
        )

    if not files:
        print(f"[INFO] No .docx/.pdf files in {input_path}")
        return

    mode = "DRY RUN" if dry else "PROCESS"
    print(f"\n{'=' * 60}")
    print(f"  BRIDGE Document Processor v2.0  [{mode}]")
    print(f"  Input:  {input_path}")
    print(f"  Output: {output_dir}")
    print(f"  Files:  {len(files)}")
    print(f"{'=' * 60}\n")

    for filepath in files:
        print(f"[{mode}] {filepath.name}")

        # 번호 결정
        current_number = brj_number
        candidate = None

        if current_number:
            candidate = get_candidate(current_number)
            if candidate:
                print(f"  #{current_number} {candidate['full_name']}")
            else:
                print(f"  #{current_number} (DB에 없음)")
        else:
            candidate = auto_detect_candidate(filepath)
            if candidate:
                current_number = candidate["sheet_number"]
                print(f"  Auto: #{current_number} {candidate['full_name']}")
            else:
                nums = re.findall(r"(\d{3,5})", filepath.stem)
                if nums:
                    current_number = int(nums[0])
                    print(f"  Filename: #{current_number}")
                else:
                    print(f"  [SKIP] 번호 없음. --number N 사용")
                    continue

        try:
            ext = filepath.suffix.lower()

            if ext == ".docx":
                doc, logs = process_docx(filepath, current_number, candidate, dry)
            elif ext == ".pdf":
                doc, logs = process_pdf(filepath, current_number, candidate, dry)
            else:
                print(f"  [SKIP] 미지원: {ext}")
                continue

            # 로그 출력
            if logs:
                print(f"  PII {len(logs)}건 {'발견' if dry else '삭제'}:")
                for l in logs[:10]:
                    print(f"    - {l}")
                if len(logs) > 10:
                    print(f"    ... +{len(logs)-10}건")

            if dry:
                if ext == ".pdf":
                    doc.close()
                print(f"  [DRY] 미리보기 완료\n")
                continue

            # 백업
            backup = backup_original(filepath)
            print(f"  Backup: {backup.name}")

            # 저장
            output_dir.mkdir(parents=True, exist_ok=True)
            out_name = _build_output_filename(current_number, candidate, ext)
            out_path = output_dir / out_name

            if ext == ".docx":
                doc.save(str(out_path))
            elif ext == ".pdf":
                doc.save(str(out_path), garbage=4, deflate=True)
                doc.close()

            print(f"  Output: {out_path.name}")

            # 삭제 로그 저장
            if logs:
                log_path = save_log(filepath, current_number, logs)
                print(f"  Log: {log_path.name}")

            print(f"  [OK]\n")

        except Exception as e:
            print(f"  [ERROR] {e}\n")
            import traceback
            traceback.print_exc()

    print(f"{'=' * 60}")
    print(f"  Done! {output_dir}")
    print(f"{'=' * 60}")


def cmd_lookup(args):
    """lookup 명령"""
    results = lookup_candidate(args.query)
    if not results:
        print(f"[INFO] No results for: {args.query}")
        return

    print(f"\n  {'#':>5}  {'Name':<35}  {'Nationality':<12}  Email")
    print(f"  {'─'*5}  {'─'*35}  {'─'*12}  {'─'*25}")
    for sn, name, nat, email in results:
        print(f"  {sn or '?':>5}  {(name or '')[:35]:<35}  {(nat or '')[:12]:<12}  {email or ''}")
    print()


def _resolve_candidate(filepath: Path) -> tuple[int | None, dict | None]:
    """파일에서 후보자 번호+정보 자동 탐지. Returns (number, candidate_dict)."""
    candidate = auto_detect_candidate(filepath)
    if candidate and candidate.get("sheet_number"):
        return candidate["sheet_number"], candidate

    nums = re.findall(r"(\d{3,5})", filepath.stem)
    if nums:
        num = int(nums[0])
        cand = get_candidate(num)
        return num, cand

    # DOCX → 이메일 기반 매칭
    if filepath.suffix.lower() == ".docx":
        try:
            for em in _extract_emails_from_docx(filepath):
                cand = find_candidate_by_email(em)
                if cand:
                    if cand.get("sheet_number"):
                        return cand["sheet_number"], cand
                    return None, cand  # 번호 없지만 후보자 정보 있음
        except Exception:
            pass
    return None, None


def cmd_batch(args):
    """batch 명령: incoming/ 폴더 전체 일괄 처리 (커버레터+이력서 자동 병합)"""
    dry = args.dry
    incoming = INCOMING_DIR
    if not incoming.exists() or not any(incoming.iterdir()):
        print(f"[INFO] incoming/ 폴더가 비어 있습니다: {incoming}")
        print(f"  파일을 여기에 넣으세요: {incoming}")
        return

    files = sorted(
        f for f in incoming.iterdir()
        if f.suffix.lower() in (".docx", ".pdf")
        and not f.name.startswith("~")
        and not f.name.startswith(".")
    )

    if not files:
        print(f"[INFO] .docx/.pdf 파일 없음: {incoming}")
        return

    mode = "DRY RUN" if dry else "BATCH"

    # ── 파일 분류: 커버레터 vs 이력서 ──
    cover_letters = []
    resumes = []
    for f in files:
        if _is_cover_letter(f):
            cover_letters.append(f)
        else:
            resumes.append(f)

    # ── 사진 맵 수집 ──
    photo_map = {}
    for f in incoming.iterdir():
        if f.suffix.lower() in (".jpg", ".jpeg", ".png") and not f.name.startswith(("~", ".")):
            nums = re.findall(r"(\d{3,5})", f.stem)
            for n in nums:
                photo_map[int(n)] = f

    # ── 후보자별 그룹핑 ──
    # key = candidate_number, value = {"resume": Path, "cover": Path, ...}
    groups = {}  # number → {resume, cover, candidate}

    for filepath in resumes:
        num, cand = _resolve_candidate(filepath)
        if not num:
            db = _get_db()
            max_num = db.execute("SELECT MAX(sheet_number) FROM candidates").fetchone()[0] or 3000
            num = max_num + 1
        groups[num] = {"resume": filepath, "cover": None, "candidate": cand}

    # 커버레터를 같은 번호 이력서에 매칭
    for filepath in cover_letters:
        num, cand = _resolve_candidate(filepath)
        if num and num in groups:
            groups[num]["cover"] = filepath
            if cand and not groups[num]["candidate"]:
                groups[num]["candidate"] = cand
        elif num:
            groups[num] = {"resume": None, "cover": filepath, "candidate": cand}
        else:
            # 번호 매칭 실패 → 이력서 1개만 있으면 그것에 붙임
            if len(resumes) == 1:
                only_num = next(iter(groups))
                groups[only_num]["cover"] = filepath
            else:
                db = _get_db()
                max_num = db.execute("SELECT MAX(sheet_number) FROM candidates").fetchone()[0] or 3000
                num = max_num + 1
                groups[num] = {"resume": None, "cover": filepath, "candidate": cand}

    total = len(groups)
    print(f"\n{'=' * 60}")
    print(f"  BRIDGE Document Processor v2.4  [{mode}]")
    print(f"  Incoming:  {incoming}")
    print(f"  Output:    {DEFAULT_OUTPUT}")
    print(f"  Resumes:   {len(resumes)} | Cover Letters: {len(cover_letters)}")
    print(f"  Groups:    {total}")
    print(f"{'=' * 60}\n")

    import tempfile

    for current_number, grp in groups.items():
        resume_path = grp["resume"]
        cover_path = grp["cover"]
        candidate = grp["candidate"]

        label = f"#{current_number}"
        if candidate:
            label += f" {candidate.get('full_name', '')}"
        print(f"[{mode}] {label}")
        if resume_path:
            print(f"  Resume: {resume_path.name}")
        if cover_path:
            print(f"  Cover:  {cover_path.name}")

        photo = photo_map.get(current_number)
        all_logs = []
        temp_pdfs = []  # (순서, pdf_path) — 최종 병합용

        try:
            # ── 커버레터 처리 ──
            if cover_path:
                ext = cover_path.suffix.lower()
                if ext == ".docx":
                    # 커버레터 DOCX: PII 제거 (번호/사진 삽입 안 함)
                    cl_doc, cl_logs = process_docx(
                        cover_path, current_number, candidate, dry, photo_path=None
                    )
                    all_logs.extend(cl_logs)
                    if not dry:
                        backup_original(cover_path)
                        # 임시 DOCX 저장 → PDF 변환
                        tmp_docx = Path(tempfile.mktemp(suffix=".docx"))
                        cl_doc.save(str(tmp_docx))
                        tmp_pdf = Path(tempfile.mktemp(suffix=".pdf"))
                        if _convert_docx_to_pdf(tmp_docx, tmp_pdf):
                            temp_pdfs.append(("cover", tmp_pdf))
                            tmp_docx.unlink()
                        else:
                            temp_pdfs.append(("cover_docx", tmp_docx))
                        cover_path.unlink()
                elif ext == ".pdf":
                    cl_doc, cl_logs = process_pdf(
                        cover_path, current_number, candidate, dry
                    )
                    all_logs.extend(cl_logs)
                    if not dry:
                        backup_original(cover_path)
                        tmp_pdf = Path(tempfile.mktemp(suffix=".pdf"))
                        cl_doc.save(str(tmp_pdf), garbage=4, deflate=True)
                        cl_doc.close()
                        temp_pdfs.append(("cover", tmp_pdf))
                        cover_path.unlink()

            # ── 이력서 처리 ──
            if resume_path:
                ext = resume_path.suffix.lower()
                if ext == ".docx":
                    doc, res_logs = process_docx(
                        resume_path, current_number, candidate, dry, photo_path=photo
                    )
                    all_logs.extend(res_logs)
                    if not dry:
                        backup_original(resume_path)
                        tmp_docx = Path(tempfile.mktemp(suffix=".docx"))
                        doc.save(str(tmp_docx))
                        tmp_pdf = Path(tempfile.mktemp(suffix=".pdf"))
                        if _convert_docx_to_pdf(tmp_docx, tmp_pdf):
                            temp_pdfs.append(("resume", tmp_pdf))
                            tmp_docx.unlink()
                        else:
                            temp_pdfs.append(("resume_docx", tmp_docx))
                        resume_path.unlink()
                elif ext == ".pdf":
                    doc, res_logs = process_pdf(
                        resume_path, current_number, candidate, dry
                    )
                    all_logs.extend(res_logs)
                    if not dry:
                        backup_original(resume_path)
                        tmp_pdf = Path(tempfile.mktemp(suffix=".pdf"))
                        doc.save(str(tmp_pdf), garbage=4, deflate=True)
                        doc.close()
                        temp_pdfs.append(("resume", tmp_pdf))
                        resume_path.unlink()

            # ── 로그 출력 ──
            if all_logs:
                print(f"  PII {len(all_logs)}건 {'발견' if dry else '삭제'}:")
                for l in all_logs[:10]:
                    print(f"    - {l}")
                if len(all_logs) > 10:
                    print(f"    ... +{len(all_logs)-10}건")

            if dry:
                print(f"  [DRY] 미리보기 완료\n")
                continue

            # ── 최종 PDF 병합/출력 ──
            DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
            final_name = _build_output_filename(current_number, candidate, ".pdf")
            final_path = DEFAULT_OUTPUT / final_name

            pdf_parts = [p for _, p in temp_pdfs if p.suffix == ".pdf"]
            if len(pdf_parts) >= 2:
                # 커버레터 + 이력서 PDF 병합
                cover_p = next((p for t, p in temp_pdfs if "cover" in t), None)
                resume_p = next((p for t, p in temp_pdfs if "resume" in t), None)
                _merge_pdfs(cover_p, resume_p, final_path)
                print(f"  Output: {final_name} (커버레터+이력서 병합 PDF)")
            elif len(pdf_parts) == 1:
                shutil.move(str(pdf_parts[0]), str(final_path))
                print(f"  Output: {final_name} (PDF)")
            else:
                # PDF 변환 실패 — DOCX 그대로 출력
                docx_parts = [p for _, p in temp_pdfs if p.suffix == ".docx"]
                if docx_parts:
                    final_path = DEFAULT_OUTPUT / _build_output_filename(
                        current_number, candidate, ".docx")
                    shutil.move(str(docx_parts[0]), str(final_path))
                    print(f"  Output: {final_path.name} (DOCX — PDF 변환 실패)")

            # 임시 파일 정리
            for _, tmp in temp_pdfs:
                if tmp.exists():
                    tmp.unlink()

            if all_logs:
                log_path = save_log(
                    resume_path or cover_path or Path(f"#{current_number}"),
                    current_number, all_logs,
                )
                print(f"  Log: {log_path.name}")

            # DB 기록
            try:
                file_size = final_path.stat().st_size if final_path.exists() else 0
                _record_file_upload(
                    entity_id=current_number,
                    file_type=final_path.suffix.lstrip("."),
                    file_url=str(final_path),
                    file_size=file_size,
                )
                print(f"  [DB] file_uploads 기록 완료")
            except Exception as db_err:
                print(f"  [DB WARN] 기록 실패 (무시): {db_err}")

            print(f"  [OK]\n")

        except Exception as e:
            print(f"  [ERROR] {e}\n")
            import traceback
            traceback.print_exc()

    print(f"{'=' * 60}")
    print(f"  Done! 결과: {DEFAULT_OUTPUT}")
    print(f"{'=' * 60}")


def cmd_download(args):
    """download 명령: S3에서 후보자 파일 다운로드"""
    number = args.number
    candidate = get_candidate(number)
    if not candidate:
        print(f"[ERROR] #{number} 후보자를 찾을 수 없습니다")
        return

    print(f"  #{number} {candidate['full_name']}")

    # bx.py로 AWS 자격증명 로드
    try:
        sys.path.insert(0, str(BASE_DIR / "tools"))
        from bx import load_to_env
        load_to_env()
    except Exception as e:
        print(f"[ERROR] AWS 자격증명 로드 실패: {e}")
        print(f"  bx.py set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_S3_BUCKET 필요")
        return

    import boto3

    bucket = os.environ.get("AWS_S3_BUCKET")
    region = os.environ.get("AWS_REGION", "ap-northeast-2")
    if not bucket:
        print("[ERROR] AWS_S3_BUCKET 환경변수 미설정")
        return

    s3 = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )

    # S3에서 후보자 관련 파일 검색 (prefix 패턴)
    prefixes_to_try = [
        f"candidates/cnd_{number}/",
        f"candidates/{number}/",
        f"resumes/{number}/",
    ]

    downloaded = []
    dest_dir = args.output or str(INCOMING_DIR)
    Path(dest_dir).mkdir(parents=True, exist_ok=True)

    for prefix in prefixes_to_try:
        try:
            response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            for obj in response.get("Contents", []):
                key = obj["Key"]
                ext = Path(key).suffix.lower()
                if ext not in (".pdf", ".docx", ".doc", ".hwp"):
                    continue

                filename = f"{number}_{Path(key).name}"
                dest = Path(dest_dir) / filename
                print(f"  Downloading: {key} -> {filename}")
                s3.download_file(bucket, key, str(dest))
                downloaded.append(dest)
        except Exception as e:
            # prefix가 없을 수 있음 → 조용히 넘김
            pass

    if downloaded:
        print(f"\n  {len(downloaded)}개 다운로드 완료 → {dest_dir}")
        if not args.no_process:
            print(f"\n  자동 처리 시작...")
            for f in downloaded:
                try:
                    ext = f.suffix.lower()
                    if ext == ".docx":
                        doc, logs = process_docx(f, number, candidate)
                    elif ext == ".pdf":
                        doc, logs = process_pdf(f, number, candidate)
                    else:
                        continue

                    backup_original(f)
                    DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
                    out_name = _build_output_filename(number, candidate, ext)
                    out_path = DEFAULT_OUTPUT / out_name

                    if ext == ".docx":
                        doc.save(str(out_path))
                    elif ext == ".pdf":
                        doc.save(str(out_path), garbage=4, deflate=True)
                        doc.close()

                    if logs:
                        save_log(f, number, logs)
                    print(f"  [OK] {out_path.name} (PII {len(logs)}건 삭제)")

                except Exception as e:
                    print(f"  [ERROR] {f.name}: {e}")
    else:
        print(f"  S3에서 파일을 찾을 수 없습니다")
        print(f"  수동으로 파일을 incoming/에 넣고 batch 명령 사용:")
        print(f"    python doc_processor.py batch")


def cmd_setup(_args=None):
    """setup 명령: 폴더 구조 생성 + 상태 확인"""
    dirs = [INCOMING_DIR, DEFAULT_OUTPUT, BACKUP_DIR, LOG_DIR]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    print(f"\n  BRIDGE Document Processor v2.3 — 폴더 구조")
    print(f"  {'─' * 50}")
    print(f"  incoming/   : {INCOMING_DIR}")
    print(f"  processed/  : {DEFAULT_OUTPUT}")
    print(f"  originals/  : {BACKUP_DIR}")
    print(f"  logs/       : {LOG_DIR}")
    print()

    # incoming 파일 수
    incoming_files = [f for f in INCOMING_DIR.iterdir()
                      if f.suffix.lower() in (".docx", ".pdf")] if INCOMING_DIR.exists() else []
    processed_files = list(DEFAULT_OUTPUT.iterdir()) if DEFAULT_OUTPUT.exists() else []

    print(f"  대기 중: {len(incoming_files)}개")
    print(f"  처리됨: {len(processed_files)}개")

    if incoming_files:
        print(f"\n  대기 파일:")
        for f in incoming_files[:10]:
            print(f"    - {f.name}")
    print()


def cmd_init_db(_args=None):
    """init-db 명령: file_uploads 테이블 생성"""
    _ensure_file_uploads_table()
    db = _get_db()
    count = db.execute("SELECT COUNT(*) FROM file_uploads").fetchone()[0]
    print(f"\n  [init-db] file_uploads 테이블 준비 완료")
    print(f"  DB: {DB_PATH}")
    print(f"  기존 레코드: {count}건\n")


def main():
    parser = argparse.ArgumentParser(
        description="BRIDGE Document Processor v2.3 — PII 삭제 + 강사번호"
    )
    sub = parser.add_subparsers(dest="command")

    p_proc = sub.add_parser("process", help="단일 파일/폴더 처리")
    p_proc.add_argument("input", help="파일 또는 폴더")
    p_proc.add_argument("--number", "-n", type=int, help="강사번호")
    p_proc.add_argument("--output", "-o", help="출력 폴더")
    p_proc.add_argument("--dry", action="store_true", help="미리보기 (수정 없음)")

    p_batch = sub.add_parser("batch", help="incoming/ 폴더 일괄 처리")
    p_batch.add_argument("--dry", action="store_true", help="미리보기 (수정 없음)")

    p_dl = sub.add_parser("download", help="S3에서 후보자 파일 다운로드 + 처리")
    p_dl.add_argument("number", type=int, help="강사번호")
    p_dl.add_argument("--output", "-o", help="다운로드 폴더 (기본: incoming/)")
    p_dl.add_argument("--no-process", action="store_true", help="다운로드만 (처리 안 함)")

    p_look = sub.add_parser("lookup", help="후보자 검색")
    p_look.add_argument("query", help="이름 또는 이메일")

    sub.add_parser("setup", help="폴더 구조 생성 + 상태 확인")
    sub.add_parser("init-db", help="file_uploads 테이블 생성 (IF NOT EXISTS)")

    args = parser.parse_args()
    if args.command == "process":
        cmd_process(args)
    elif args.command == "batch":
        cmd_batch(args)
    elif args.command == "download":
        cmd_download(args)
    elif args.command == "lookup":
        cmd_lookup(args)
    elif args.command == "setup":
        cmd_setup(args)
    elif args.command == "init-db":
        cmd_init_db(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
