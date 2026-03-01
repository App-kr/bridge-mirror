"""
load_jobs.py — Bridge Base: original_jobs → master.db + Obsidian 마크다운 생성

★ 정책: 삭제 없음. 중복 Job 코드는 seq(순번)로 구분하여 전부 보존.
         Obsidian 파일에서 중복 항목은 색상 callout으로 묶어서 표시.

파싱 대상:
  1. original_jobs/BRIDGE_clients_jobs.txt   → jobs 테이블
  2. original_jobs/BRIDGE_clients_data.csv   → client_inquiries 테이블 (구형식)
  3. original_jobs/BRIDGE_clients_data_New.csv → client_inquiries 테이블 (신형식)

실행:
  python load_jobs.py               # DB 적재 + Obsidian 생성
  python load_jobs.py --dry-run     # 파싱 결과만 확인, 쓰기 없음
  python load_jobs.py --db-only     # DB 적재만 (Obsidian 생략)
  python load_jobs.py --md-only     # Obsidian 생성만 (DB 이미 있을 때)
"""

import argparse
import csv
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR    = Path(__file__).parent
JOBS_TXT    = BASE_DIR / "original_jobs" / "BRIDGE_clients_jobs.txt"
CSV_OLD     = BASE_DIR / "original_jobs" / "BRIDGE_clients_data.csv"
CSV_NEW     = BASE_DIR / "original_jobs" / "BRIDGE_clients_data_New.csv"
DB_PATH     = BASE_DIR / "master.db"
OBSIDIAN_DIR = Path("Q:/Obsidian/Scarlett/Bridge_Vault/Jobs")

NOW_ISO  = datetime.now(timezone.utc).isoformat()
NOW_DISP = datetime.now().strftime("%Y-%m-%d %H:%M")

# ── 색상 callout 정의 (Obsidian 지원 타입) ──────────────────────────────────
# seq 순번 → callout 타입 & 한글 레이블
CALLOUT_COLORS = {
    1: ("success", "🟢 Primary 등록"),    # 초록
    2: ("warning", "🟡 2nd 등록"),        # 노랑
    3: ("caution", "🟠 3rd 등록"),        # 주황
    4: ("danger",  "🔴 4th 등록"),        # 빨강
}
PT_CALLOUT = ("tip", "🔵 Part-Time")     # 파트타임은 파랑

# ─────────────────────────────────────────────────────────────────────────────
# DDL
# ─────────────────────────────────────────────────────────────────────────────

DDL_JOBS = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_code        TEXT    NOT NULL,
    seq             INTEGER NOT NULL DEFAULT 1,
    location        TEXT,
    city            TEXT,
    district        TEXT,
    start_date      TEXT,
    teaching_age    TEXT,
    class_size      TEXT,
    working_hours   TEXT,
    daily_hours     REAL,
    salary_min      REAL,
    salary_max      REAL,
    salary_raw      TEXT,
    teach_hrs_week  TEXT,
    vacation        TEXT,
    housing         TEXT,
    native_count    TEXT,
    benefits        TEXT,
    internal_notes  TEXT,
    is_part_time    INTEGER DEFAULT 0,
    source_file     TEXT    DEFAULT 'BRIDGE_clients_jobs.txt',
    loaded_at       TEXT,
    UNIQUE(job_code, seq)
)
"""

DDL_CLIENTS = """
CREATE TABLE IF NOT EXISTS client_inquiries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    submitted_at    TEXT,
    email           TEXT,
    school_name     TEXT,
    location        TEXT,
    contact_name    TEXT,
    phone           TEXT,
    start_date      TEXT,
    vacancies       TEXT,
    teaching_age    TEXT,
    schedule        TEXT,
    working_hours   TEXT,
    salary_raw      TEXT,
    housing_type    TEXT,
    housing_detail  TEXT,
    travel_support  TEXT,
    benefits        TEXT,
    vacation        TEXT,
    sick_leave      TEXT,
    meal            TEXT,
    memo            TEXT,
    source_file     TEXT,
    loaded_at       TEXT
)
"""

# ─────────────────────────────────────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────────────────────────────────────

def parse_salary(raw: str):
    if not raw:
        return None, None
    raw2 = raw.upper().replace(",", "").replace(" ", "")
    nums = re.findall(r"(\d+(?:\.\d+)?)\s*(?:M(?:AN(?:WON)?)?|KRW|만원)?", raw2)
    floats = []
    for n in nums:
        v = float(n)
        if v >= 100:
            v = v / 100
        if 1.0 <= v <= 10.0:      # 합리적 급여 범위만
            floats.append(round(v, 2))
    if not floats:
        return None, None
    return min(floats), max(floats)

def parse_daily_hours(wh: str):
    if not wh:
        return None
    m = re.search(r"(\d{1,2}):(\d{2})\s*[~\-]+\s*(\d{1,2}):(\d{2})", wh)
    if m:
        sh, sm, eh, em = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        total = (eh * 60 + em) - (sh * 60 + sm)
        return round(total / 60, 2) if total > 0 else None
    return None

def split_location(loc: str):
    parts = loc.strip().split(None, 1)
    city = parts[0].capitalize() if parts else loc
    district = parts[1].strip() if len(parts) > 1 else ""
    return city, district

def city_tag(city: str) -> str:
    return re.sub(r"[^a-z]", "", city.lower()) if city else "korea"

# ─────────────────────────────────────────────────────────────────────────────
# BRIDGE_clients_jobs.txt 파싱
# ─────────────────────────────────────────────────────────────────────────────

JOB_CODE_RE = re.compile(
    r"^`?JOBS?(?:GGP|SP|PT|P|_PT)?\.\s*(\w+)", re.IGNORECASE
)
FIELD_RE = re.compile(r"^`?\s*(.+?)\s*:\s*(.+)", re.IGNORECASE)

def parse_jobs_txt(path: Path) -> list[dict]:
    """TXT → 레코드 목록. 중복 코드는 seq 부여하여 전부 보존."""
    raw_records: list[dict] = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    job: dict | None = None
    pending_location = ""
    pending_notes = ""

    def flush(j):
        if j and j.get("job_code"):
            smin, smax = parse_salary(j.get("salary_raw", ""))
            j["salary_min"]  = smin
            j["salary_max"]  = smax
            j["daily_hours"] = parse_daily_hours(j.get("working_hours", ""))
            j.setdefault("location", "")
            j["city"], j["district"] = split_location(j["location"])
            j.setdefault("is_part_time", 0)
            j["loaded_at"] = NOW_ISO
            raw_records.append(j)

    for line in lines:
        stripped = line.strip()

        is_pt = bool(re.search(r"PART\s*TIME", stripped, re.IGNORECASE))

        # 내부 한국어 메모
        if stripped.startswith("(") and stripped.endswith(")"):
            pending_notes = stripped
            continue

        if stripped.startswith("🔥"):
            continue

        # Job 코드
        m = JOB_CODE_RE.match(stripped)
        if m:
            flush(job)
            job = {
                "job_code":       "Job." + m.group(1),
                "location":       pending_location.strip(),
                "internal_notes": pending_notes,
                "is_part_time":   1 if is_pt else 0,
                "source_file":    "BRIDGE_clients_jobs.txt",
            }
            pending_notes = ""
            pending_location = ""
            continue

        # 위치 후보 라인 — job 유무 무관하게 캡처 (다음 Job. 코드에 사용)
        # 조건: 짧고 알파벳/한글만, 콜론 없음, 특수 키워드 아님
        if (
            2 <= len(stripped) <= 45
            and re.match(r"^[A-Za-z가-힣\s\-/()\u4e00-\u9fff]+$", stripped)
            and ":" not in stripped
            and not re.search(r"PART|REQUIRE|BENEFIT|ONLY|FULL|AVAIL|FLUENT", stripped, re.IGNORECASE)
        ):
            pending_location = stripped
            if job is None:
                continue
            # job이 진행 중이면 필드 처리로 넘어가지 않고 pending만 갱신
            continue

        if job is None:
            continue

        if is_pt:
            job["is_part_time"] = 1

        fm = FIELD_RE.match(stripped)
        if fm:
            key_raw = fm.group(1).strip().lower()
            val     = fm.group(2).strip()
            if re.search(r"start", key_raw):
                job.setdefault("start_date", val)
            elif re.search(r"teach.*age|age.*group", key_raw):
                job.setdefault("teaching_age", val)
            elif re.search(r"class\s*size", key_raw):
                job.setdefault("class_size", val)
            elif re.search(r"working\s*hour", key_raw):
                job.setdefault("working_hours", val)
            elif re.search(r"salary|pay", key_raw):
                job.setdefault("salary_raw", val)
            elif re.search(r"teach.*week|average.*teach", key_raw):
                job.setdefault("teach_hrs_week", val)
            elif re.search(r"vacation", key_raw):
                job.setdefault("vacation", val)
            elif re.search(r"housing", key_raw):
                job.setdefault("housing", val)
            elif re.search(r"native|available\s*position", key_raw):
                job.setdefault("native_count", val)
            elif re.search(r"benefit|employee\s*benefit", key_raw):
                job.setdefault("benefits", val)
            continue

        # 위치가 job 안에서 늦게 오는 경우
        if (
            2 <= len(stripped) <= 45
            and re.match(r"^[A-Za-z\s]+$", stripped)
            and not job.get("location")
            and not re.search(r"PART|REQUIRE|ONLY|FULL|AVAIL", stripped, re.IGNORECASE)
        ):
            job["location"] = stripped

    flush(job)

    # ── seq 부여: 같은 job_code 순서대로 1, 2, 3 … ───────────────────────────
    seq_counter: dict[str, int] = {}
    for rec in raw_records:
        code = rec["job_code"]
        seq_counter[code] = seq_counter.get(code, 0) + 1
        rec["seq"] = seq_counter[code]

    return raw_records

# ─────────────────────────────────────────────────────────────────────────────
# CSV 파싱
# ─────────────────────────────────────────────────────────────────────────────

def _find_val(row: dict, *keywords) -> str:
    for k, v in row.items():
        kl = k.strip().lower()
        if any(kw.lower() in kl for kw in keywords):
            return v.strip()
    return ""

def map_row_old(row: dict) -> dict:
    return {
        "submitted_at":  _find_val(row, "타임스탬프"),
        "email":         _find_val(row, "이메일"),
        "school_name":   _find_val(row, "업체명", "학원명", "학교"),
        "location":      _find_val(row, "소재지", "location"),
        "contact_name":  _find_val(row, "성함", "직책"),
        "phone":         _find_val(row, "연락처", "폰번호"),
        "start_date":    _find_val(row, "희망 시작일", "starting date"),
        "vacancies":     _find_val(row, "채용인원", "vacancies"),
        "teaching_age":  _find_val(row, "강의대상", "teaching age"),
        "schedule":      _find_val(row, "근무요일", "schedule"),
        "working_hours": _find_val(row, "근로계약시간", "working hour"),
        "salary_raw":    _find_val(row, "급여", "salary"),
        "housing_type":  _find_val(row, "기숙사", "housing"),
        "travel_support":_find_val(row, "이동비용"),
        "benefits":      _find_val(row, "복지", "benefit"),
        "vacation":      _find_val(row, "휴가"),
        "sick_leave":    _find_val(row, "보건휴가", "sick"),
        "meal":          _find_val(row, "식사", "meal"),
        "memo":          _find_val(row, "메모", "memo"),
        "source_file":   "BRIDGE_clients_data.csv",
        "loaded_at":     NOW_ISO,
    }

def map_row_new(row: dict) -> dict:
    return {
        "submitted_at":   _find_val(row, "타임스탬프"),
        "email":          _find_val(row, "이메일"),
        "school_name":    _find_val(row, "학교이름", "name"),
        "location":       _find_val(row, "근무처소재지"),
        "contact_name":   _find_val(row, "성함직책"),
        "phone":          _find_val(row, "휴대전화"),
        "start_date":     _find_val(row, "희망시작일"),
        "vacancies":      _find_val(row, "채용인원"),
        "teaching_age":   _find_val(row, "수업대상"),
        "schedule":       _find_val(row, "근무요일"),
        "working_hours":  _find_val(row, "근무일정"),
        "salary_raw":     _find_val(row, "급여조건"),
        "housing_type":   _find_val(row, "숙소제공"),
        "housing_detail": _find_val(row, "숙소관련"),
        "travel_support": _find_val(row, "이동지원"),
        "benefits":       _find_val(row, "복지"),
        "vacation":       _find_val(row, "유급휴일"),
        "sick_leave":     _find_val(row, "보건휴가"),
        "meal":           _find_val(row, "식사식대"),
        "memo":           _find_val(row, "메모"),
        "source_file":    "BRIDGE_clients_data_New.csv",
        "loaded_at":      NOW_ISO,
    }

def parse_csv(path: Path, mapper) -> list[dict]:
    records = []
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            r = mapper(row)
            if any(r.get(k) for k in ("submitted_at", "email", "school_name")):
                records.append(r)
    return records

# ─────────────────────────────────────────────────────────────────────────────
# DB 적재
# ─────────────────────────────────────────────────────────────────────────────

JOB_COLS = [
    "job_code","seq","location","city","district","start_date","teaching_age",
    "class_size","working_hours","daily_hours","salary_min","salary_max",
    "salary_raw","teach_hrs_week","vacation","housing","native_count",
    "benefits","internal_notes","is_part_time","source_file","loaded_at",
]
CLIENT_COLS = [
    "submitted_at","email","school_name","location","contact_name","phone",
    "start_date","vacancies","teaching_age","schedule","working_hours",
    "salary_raw","housing_type","housing_detail","travel_support","benefits",
    "vacation","sick_leave","meal","memo","source_file","loaded_at",
]

def upsert_jobs(conn: sqlite3.Connection, records: list[dict]):
    ph  = ", ".join("?" * len(JOB_COLS))
    cs  = ", ".join(JOB_COLS)
    upd = ", ".join(f"{c}=excluded.{c}" for c in JOB_COLS if c not in ("job_code","seq"))
    sql = (f"INSERT INTO jobs ({cs}) VALUES ({ph}) "
           f"ON CONFLICT(job_code, seq) DO UPDATE SET {upd}")
    rows = [[r.get(c) for c in JOB_COLS] for r in records]
    conn.executemany(sql, rows)

def insert_clients(conn: sqlite3.Connection, records: list[dict], source: str):
    conn.execute("DELETE FROM client_inquiries WHERE source_file = ?", (source,))
    ph  = ", ".join("?" * len(CLIENT_COLS))
    cs  = ", ".join(CLIENT_COLS)
    sql = f"INSERT INTO client_inquiries ({cs}) VALUES ({ph})"
    rows = [[r.get(c) for c in CLIENT_COLS] for r in records]
    conn.executemany(sql, rows)

# ─────────────────────────────────────────────────────────────────────────────
# Obsidian 마크다운 생성
# ─────────────────────────────────────────────────────────────────────────────

def salary_str(smin, smax) -> str:
    if smin and smax:
        if abs(smin - smax) < 0.01:
            return f"{smin:.2f}m KRW"
        return f"{smin:.2f}m ~ {smax:.2f}m KRW"
    if smin:
        return f"{smin:.2f}m KRW~"
    return "협의"

def build_callout_block(rec: dict, seq: int, total: int) -> str:
    """단일 레코드를 색상 callout 블록으로 변환"""
    is_pt = rec.get("is_part_time", 0)

    if is_pt:
        ct, label = PT_CALLOUT
    else:
        ct, label = CALLOUT_COLORS.get(seq, ("note", f"#{seq} 등록"))

    loc    = rec.get("location", "")
    sd     = rec.get("start_date", "협의")
    age    = rec.get("teaching_age", "")
    cls    = rec.get("class_size", "")
    wh     = rec.get("working_hours", "")
    dh     = rec.get("daily_hours")
    sraw   = rec.get("salary_raw", "")
    smin   = rec.get("salary_min")
    smax   = rec.get("salary_max")
    sal_s  = salary_str(smin, smax)
    vac    = rec.get("vacation", "협의")
    house  = rec.get("housing", "")
    nat    = rec.get("native_count", "")
    ben    = rec.get("benefits", "")
    notes  = rec.get("internal_notes", "")

    wh_disp = f"{wh}  ({dh:.1f}h/day)" if dh else wh

    part_tag = " `PART-TIME`" if is_pt else ""
    title = f"{label}{part_tag}" if total > 1 else "📋 Job Details"

    lines = [
        f"> [!{ct}]+ {title}",
        f"> | 항목 | 내용 |",
        f"> |------|------|",
        f"> | 📍 Location | {loc} |",
        f"> | 📅 시작일 | {sd} |",
        f"> | 👶 수업대상 | {age} |",
    ]
    if cls:
        lines.append(f"> | 🏫 학급규모 | {cls} |")
    if wh_disp:
        lines.append(f"> | ⏰ 근무시간 | {wh_disp} |")
    lines.append(f"> | 💰 급여 | {sal_s} |")
    if vac:
        lines.append(f"> | 🌴 방학 | {vac} |")
    if house:
        lines.append(f"> | 🏠 숙소 | {house} |")
    if nat:
        lines.append(f"> | 👨‍🏫 원어민 수 | {nat} |")
    if ben:
        lines.append(f"> | 🎁 복지 | {ben} |")
    if notes:
        lines.append(f"> ")
        lines.append(f"> **내부 메모**: {notes}")

    return "\n".join(lines)

def build_ad_section(code: str, loc: str, rec: dict) -> str:
    sd   = rec.get("start_date", "ASAP")
    age  = rec.get("teaching_age", "")
    cls  = rec.get("class_size", "")
    wh   = rec.get("working_hours", "")
    dh   = rec.get("daily_hours")
    smin = rec.get("salary_min")
    smax = rec.get("salary_max")
    sal_s = salary_str(smin, smax)
    vac  = rec.get("vacation", "협의")
    house= rec.get("housing", "")
    nat  = rec.get("native_count", "")
    ben  = rec.get("benefits", "")
    wh_disp = f"{wh}  ({dh:.1f}h/day)" if dh else wh

    craigslist = f"""### 📢 Craigslist Ad

**English Teaching Position in {loc}**

We are currently seeking a qualified Native English Teacher for our school.

- 📍 **Location**: {loc}
- 📅 **Start Date**: {sd}
- 👶 **Teaching Age**: {age}
- 🏫 **Class Size**: {cls}
- ⏰ **Working Hours**: {wh_disp}
- 💰 **Monthly Salary**: {sal_s}
- 🌴 **Vacation**: {vac}
- 🏠 **Housing**: {house}
- 🎁 **Benefits**: {ben}

**Requirements:**
- Native English speaker from USA, UK, Canada, Australia, NZ, South Africa, or Ireland
- Bachelor's degree or higher (any field)
- TEFL/TESOL/CELTA certification preferred
- Clean criminal background check

To apply, please send your CV, photo, and cover letter to: bridge.recruiting@email.com
Reference Code: **{code}**
"""

    esl_cafe = f"""### 🌐 ESL Cafe Ad

**[{code}] {loc} | {age} | {sal_s} | {sd}**

---
Hello ESL Cafe community!

We have an exciting opening at a school in **{loc}**.

| Field | Details |
|-------|---------|
| Job Code | {code} |
| Location | {loc} |
| Start Date | {sd} |
| Teaching Age | {age} |
| Class Size | {cls} |
| Working Hours | {wh_disp} |
| Monthly Salary | {sal_s} |
| Vacation | {vac} |
| Housing | {house} |
| Native Teachers | {nat} |

**Benefits included:** {ben}

Interested? Contact us with your resume and photo.
✉️ bridge.recruiting@email.com | Reference: **{code}**
"""
    return craigslist + "\n\n---\n\n" + esl_cafe

def make_md(code: str, group: list[dict]) -> str:
    """동일 job_code 그룹 → 마크다운 문자열"""
    # 대표 레코드(seq=1)로 frontmatter 구성
    primary = group[0]
    loc     = primary.get("location", "")
    city    = primary.get("city", "")
    sd      = primary.get("start_date", "")
    age     = primary.get("teaching_age", "")
    dh      = primary.get("daily_hours")
    smin    = primary.get("salary_min")
    smax    = primary.get("salary_max")
    tag     = city_tag(city)
    is_dup  = len(group) > 1

    fm_lines = [
        "---",
        f"job_code: {code}",
        f"location: {loc}",
        f"city: {city}",
        f"is_hot: False",
        f"start_date: {sd}",
        f"teaching_age: {age}",
        f"daily_hours: {dh if dh else ''}",
        f"salary_min: {smin if smin else ''}",
        f"salary_max: {smax if smax else ''}",
        f"duplicate_entries: {len(group)}",
        f"updated: {NOW_ISO}",
        f"tags: [bridge, job, {tag}]",
        "---",
    ]

    header = f"# {code} — {loc}\n\n> **마지막 업데이트**: {NOW_ISO}\n"
    if is_dup:
        header += f"\n> ⚠️ 동일 코드 **{len(group)}개** 항목 존재 — 아래 색상 구분 참조\n"

    # 각 항목 callout
    callout_blocks = []
    for rec in group:
        seq = rec.get("seq", 1)
        block = build_callout_block(rec, seq, len(group))
        callout_blocks.append(block)

    # 광고 템플릿은 primary(seq=1) 기준으로 1개만 생성
    ad_section = build_ad_section(code, loc, primary)

    footer = f"\n---\n\n*Generated by BRIDGE Automation · {NOW_DISP}*\n"

    parts = [
        "\n".join(fm_lines),
        "",
        header,
        "",
        "\n\n---\n\n".join(callout_blocks),
        "",
        "---",
        "",
        ad_section,
        footer,
    ]
    return "\n".join(parts)

def generate_obsidian(records: list[dict], obsidian_dir: Path, overwrite: bool = False):
    """레코드 → 옵시디언 .md 파일 생성. 신규만 생성 (기존 파일 삭제 없음)."""
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    # job_code별 그룹화
    groups: dict[str, list[dict]] = {}
    for r in records:
        code = r["job_code"]
        groups.setdefault(code, []).append(r)

    created = 0
    skipped = 0
    updated = 0

    for code, group in groups.items():
        # 파일명: Job.XXXX.md
        fname = code + ".md"
        fpath = obsidian_dir / fname

        is_dup = len(group) > 1

        if fpath.exists() and not overwrite:
            # 중복 항목이 있는 경우는 덮어쓰기 (색상 구분 추가)
            if is_dup:
                md = make_md(code, group)
                fpath.write_text(md, encoding="utf-8")
                updated += 1
            else:
                skipped += 1
            continue

        md = make_md(code, group)
        fpath.write_text(md, encoding="utf-8")
        created += 1

    return created, updated, skipped

# ─────────────────────────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Bridge Base load_jobs")
    ap.add_argument("--dry-run",  action="store_true", help="파싱 미리보기만 (쓰기 없음)")
    ap.add_argument("--db-only",  action="store_true", help="DB 적재만 (Obsidian 생략)")
    ap.add_argument("--md-only",  action="store_true", help="Obsidian 생성만")
    ap.add_argument("--overwrite",action="store_true", help="기존 Obsidian 파일도 덮어쓰기")
    args = ap.parse_args()

    print("=" * 65)
    print("  BRIDGE load_jobs.py  —  데이터 적재 시작")
    print(f"  실행: {NOW_DISP}")
    print("=" * 65)

    # ── 1. TXT 파싱 ──────────────────────────────────────────────────────────
    print(f"\n[1/3] TXT 파싱: {JOBS_TXT.name}")
    jobs = parse_jobs_txt(JOBS_TXT)
    dup_codes = {r["job_code"] for r in jobs if r["seq"] > 1}
    print(f"      → 전체 레코드: {len(jobs)}건  |  고유 코드: {len({r['job_code'] for r in jobs})}개")
    print(f"      → 중복 코드:   {len(dup_codes)}개  (삭제 없이 seq 구분 보존)")

    # ── 2. CSV 구형식 ─────────────────────────────────────────────────────────
    print(f"\n[2/3] CSV(구) 파싱: {CSV_OLD.name}")
    clients_old = parse_csv(CSV_OLD, map_row_old)
    print(f"      → {len(clients_old)}건")

    # ── 3. CSV 신형식 ─────────────────────────────────────────────────────────
    print(f"\n[3/3] CSV(신) 파싱: {CSV_NEW.name}")
    clients_new = parse_csv(CSV_NEW, map_row_new)
    print(f"      → {len(clients_new)}건")

    # ── Dry-run ───────────────────────────────────────────────────────────────
    if args.dry_run:
        print("\n── DRY-RUN 미리보기 ─────────────────────────────────────────")
        for j in jobs[:5]:
            dup = f" (seq={j['seq']})" if j["seq"] > 1 else ""
            print(f"  {j['job_code']:12s}{dup:10s} | {j.get('location',''):25s} | "
                  f"{j.get('salary_min','-')}~{j.get('salary_max','-')}M")
        print(f"\n  중복 코드 예시: {sorted(dup_codes)[:10]}")
        print("\n[DRY-RUN] 쓰기를 건너뜁니다.")
        return

    # ── DB 적재 ───────────────────────────────────────────────────────────────
    if not args.md_only:
        print(f"\n[DB] master.db 생성/갱신: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(DDL_JOBS)
        conn.execute(DDL_CLIENTS)

        upsert_jobs(conn, jobs)
        insert_clients(conn, clients_old, "BRIDGE_clients_data.csv")
        insert_clients(conn, clients_new,  "BRIDGE_clients_data_New.csv")
        conn.commit()

        j_cnt = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        c_cnt = conn.execute("SELECT COUNT(*) FROM client_inquiries").fetchone()[0]
        dup_cnt = conn.execute("SELECT COUNT(*) FROM jobs WHERE seq > 1").fetchone()[0]
        conn.close()

        print(f"      ✅ jobs            : {j_cnt:,}건 (중복 seq>1: {dup_cnt}건)")
        print(f"      ✅ client_inquiries: {c_cnt:,}건")

    # ── Obsidian 생성 ─────────────────────────────────────────────────────────
    if not args.db_only:
        print(f"\n[MD] Obsidian 마크다운 생성: {OBSIDIAN_DIR}")
        created, updated, skipped = generate_obsidian(
            jobs, OBSIDIAN_DIR, overwrite=args.overwrite
        )
        print(f"      ✅ 신규 생성: {created}건")
        print(f"      🔄 중복 업데이트: {updated}건  (색상 callout 적용)")
        print(f"      ⏭  기존 유지: {skipped}건  (삭제 없음)")

    print("\n" + "=" * 65)
    print("  ✅ 모든 작업 완료")
    print("=" * 65)

if __name__ == "__main__":
    main()
