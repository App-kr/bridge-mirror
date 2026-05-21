"""
BRIDGE Candidates DB Builder
==============================
original_candidates/*.csv + intake/candidates/*.csv
→ bridge base master.db 의 candidates 테이블에 전량 적재

헤더 기반으로 OLD(52열) / NEW(50열) 자동 판별.
14개 확장 필드 포함 전체 매핑.

실행: python build_candidates_db.py
경로: Q:/Claudework/bridge base/
"""
import csv
import hashlib
import io
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR      = Path("Q:/Claudework/bridge base")
DB_PATH       = BASE_DIR / "master.db"
ORIG_DIR      = BASE_DIR / "original_candidates"
INTAKE_DIR    = BASE_DIR / "intake" / "candidates"
PROCESSED_DIR = BASE_DIR / "intake" / "processed_candidates"

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

# ── DB 테이블 생성 ────────────────────────────────────────────────────────────
CREATE_SQL = """
CREATE TABLE IF NOT EXISTS candidates (
    candidate_id    TEXT PRIMARY KEY,
    email           TEXT,
    full_name       TEXT,
    nationality     TEXT,
    ancestry        TEXT,
    dob             TEXT,
    gender          TEXT,
    current_location TEXT,
    start_date      TEXT,
    target          TEXT,
    area_prefs      TEXT,
    experience      TEXT,
    employment      TEXT,
    current_salary  TEXT,
    desired_salary  TEXT,
    certification   TEXT,
    e_visa          TEXT,
    mobile_phone    TEXT,
    kakaotalk       TEXT,
    criminal_record TEXT,
    passport        TEXT,
    housing         TEXT,
    arc_holders     TEXT,
    job_prefs       TEXT,
    reference       TEXT,
    documents       TEXT,
    status          TEXT DEFAULT 'Active',
    source_file     TEXT,
    source_row      TEXT,
    created_at      TEXT,
    updated_at      TEXT
)
"""

# ── 컬럼 인덱스 매핑: OLD(52열) vs NEW(50열) ─────────────────────────────────
# OLD CSV: bridge_candidates_data.csv (52 columns)
#   [4]=빈열, [17]=Apply, [18]=빈열, [22]=빈열, [26]=Basic health,
#   [27]=Situation, [28]=Pet, [29]=Tattoos, [30]=Piercings, [31]=Marital,
#   [32]=Housing, [33]=Religion, [34]=E visa, [35]=KakaoTalk,
#   [36]=Mobile Phone, [37]=Criminal Record, [38]=빈열, [39]=Passport
#
# NEW CSV: bridge_candidates_data new.csv / intake CSVs (50 columns)
#   [4]=ARC holders, [17]=Interview, [18]=Apply, [22]=Degree,
#   [26]=Health Information, [27]=Personal Considerations, [28]=piercings,
#   [29]=Dependents Pets, [30]=Marital Status, [31]=Housing, [32]=Religion,
#   [33]=E visa, [34]=KakaoTalk, [35]=Mobile Phone, [36]=Criminal Record,
#   [37]=Criminal Record in Korea, [38]=Agreement, [39]=Facts

OLD_MAP = {
    "email":                  0,
    "full_name":              1,
    # 2=Photo, 3=No, 4=빈열
    "nationality":            5,
    "ancestry":               6,
    "dob":                    7,
    "gender":                 8,
    "current_location":       9,
    "start_date":            10,
    "target":                11,
    "area_prefs":            12,
    "reference":             13,
    "experience":            14,
    "employment":            15,
    "job_prefs":             16,
    # 17=Apply, 18=빈열
    "current_salary":        19,
    "desired_salary":        20,
    "interview_time":        21,
    # 22=빈열
    "major":                 23,
    "certification":         24,
    "documents":             25,
    "health_info":           26,
    "personal_consideration":27,
    # 28=Pet, 29=Tattoos, 30=Piercings — OLD 포맷은 다른 필드
    "piercings":             30,
    "married":               31,
    "housing":               32,
    "religion":              33,
    "e_visa":                34,
    "kakaotalk":             35,
    "mobile_phone":          36,
    "criminal_record":       37,
    # 38=빈열
    "passport":              39,
    "consent":               40,
    "fact_check":            41,
    "arc_holders":            4,
}

NEW_MAP = {
    "email":                  0,
    "full_name":              1,
    # 2=Photo, 3=No
    "arc_holders":            4,
    "nationality":            5,
    "ancestry":               6,
    "dob":                    7,
    "gender":                 8,
    "current_location":       9,
    "start_date":            10,
    "target":                11,
    "area_prefs":            12,
    "reference":             13,
    "experience":            14,
    "employment":            15,
    "job_prefs":             16,
    # 17=Interview, 18=Apply
    "current_salary":        19,
    "desired_salary":        20,
    "interview_time":        21,
    "education_level":       22,
    "major":                 23,
    "certification":         24,
    "documents":             25,
    "health_info":           26,
    "personal_consideration":27,
    "piercings":             28,
    "dependents":            29,
    "married":               30,
    "housing":               31,
    "religion":              32,
    "e_visa":                33,
    "kakaotalk":             34,
    "mobile_phone":          35,
    "criminal_record":       36,
    "korean_criminal_record":37,
    "consent":               38,
    "fact_check":            39,
}

# 전체 INSERT 대상 컬럼 (OLD/NEW 합집합)
ALL_DB_COLS = [
    "candidate_id", "email", "full_name", "nationality", "ancestry", "dob",
    "gender", "current_location", "start_date", "target", "area_prefs",
    "experience", "employment", "current_salary", "desired_salary",
    "certification", "e_visa", "mobile_phone", "kakaotalk", "criminal_record",
    "passport", "housing", "arc_holders", "job_prefs", "reference", "documents",
    "status", "source_file", "source_row", "created_at", "updated_at",
    # 확장 필드
    "interview_time", "education_level", "major", "health_info",
    "personal_consideration", "piercings", "dependents", "married",
    "religion", "korean_criminal_record", "consent", "fact_check",
]


def stable_id(email: str, name: str, row_num: int, fname: str) -> str:
    raw = f"{fname}||{row_num}||{email}||{name}"
    return "cnd_" + hashlib.sha1(raw.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]


def is_memo_row(row: list) -> bool:
    """메모/내부노트 행 감지"""
    joined = " ".join(str(c) for c in row[:6])
    keywords = ["인터뷰🔥", "제안📢", "체결:", "이름", "메일", "name", "email"]
    return any(kw.lower() in joined.lower() for kw in keywords) and not any(
        "@" in c for c in row[:3]
    )


def get_val(row: list, idx: int) -> str:
    if idx < len(row):
        return row[idx].strip()
    return ""


def detect_format(header: list) -> str:
    """헤더 기반 OLD(52열) vs NEW(50열) 자동 판별"""
    header_lower = [h.strip().lower() for h in header]
    # NEW 포맷 특징: [4]='arc holders', [22]='degree', [37]='criminal record in korea'
    if "arc holders" in header_lower:
        return "NEW"
    if len(header) >= 52:
        return "OLD"
    # 안전장치: 50열이면 NEW, 52열이면 OLD
    if len(header) <= 50:
        return "NEW"
    return "OLD"


def load_csv(fpath: Path, status: str = "Active") -> list[dict]:
    """CSV → 레코드 리스트 반환. 헤더 기반 자동 판별."""
    records = []
    rows: list = []
    for enc in ["utf-8-sig", "utf-8", "cp949"]:
        try:
            with open(fpath, encoding=enc, errors="replace") as f:
                rows = list(csv.reader(f))
            break
        except Exception:
            rows = []

    if not rows:
        print(f"  [SKIP] 읽기 실패: {fpath.name}")
        return []

    # 헤더 행 찾기
    header_idx = 0
    for i, row in enumerate(rows):
        joined = " ".join(row)
        if "Full name" in joined or "이메일 주소" in joined:
            header_idx = i
            break

    header = rows[header_idx]
    fmt = detect_format(header)
    mapping = NEW_MAP if fmt == "NEW" else OLD_MAP
    print(f"  Format: {fmt} ({len(header)} columns)")

    data_rows = rows[header_idx + 1:]

    for row_num, row in enumerate(data_rows, start=header_idx + 2):
        if not any(c.strip() for c in row):
            continue
        if is_memo_row(row):
            continue

        email = get_val(row, 0)
        name  = get_val(row, 1)

        if not email and not name:
            continue

        cid = stable_id(email, name, row_num, fpath.name)

        rec: dict = {
            "candidate_id": cid,
            "status":       status,
            "source_file":  fpath.name,
            "source_row":   str(row_num),
            "created_at":   NOW,
            "updated_at":   NOW,
        }

        # 매핑 적용
        for db_col, csv_idx in mapping.items():
            rec[db_col] = get_val(row, csv_idx)

        # 누락 필드 빈문자열 보장
        for col in ALL_DB_COLS:
            rec.setdefault(col, "")

        records.append(rec)

    return records


def upsert_records(conn: sqlite3.Connection, records: list[dict]) -> tuple[int, int]:
    inserted = skipped = 0
    cols_str = ", ".join(ALL_DB_COLS)
    placeholders = ", ".join(f":{c}" for c in ALL_DB_COLS)
    insert_sql = f"INSERT INTO candidates ({cols_str}) VALUES ({placeholders})"

    for rec in records:
        existing = conn.execute(
            "SELECT candidate_id FROM candidates WHERE candidate_id=?",
            (rec["candidate_id"],)
        ).fetchone()
        if existing:
            skipped += 1
            continue
        conn.execute(insert_sql, rec)
        inserted += 1
    return inserted, skipped


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute(CREATE_SQL)
    conn.commit()

    before = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    print(f"시작 전 candidates: {before:,}건")
    print()

    total_inserted = 0
    total_skipped  = 0

    # 1. 원본 마스터 CSV
    sources = [
        (ORIG_DIR / "bridge_candidates_data.csv",     "Inactive"),
        (ORIG_DIR / "bridge_candidates_data new.csv", "Active"),
    ]

    for fpath, status in sources:
        if not fpath.exists():
            print(f"  [SKIP] 없음: {fpath.name}")
            continue
        print(f"[{status}] {fpath.name} 파싱 중...")
        records = load_csv(fpath, status)
        ins, skp = upsert_records(conn, records)
        conn.commit()
        print(f"  -> 파싱: {len(records)}건  적재: {ins}건  중복: {skp}건")
        total_inserted += ins
        total_skipped  += skp
        print()

    # 2. intake CSV (Google Sheets Pull 결과 — Active)
    intake_csvs = sorted(INTAKE_DIR.glob("sheets_candidates_*.csv"))
    for fpath in intake_csvs:
        print(f"[Intake] {fpath.name} 파싱 중...")
        records = load_csv(fpath, "Active")
        ins, skp = upsert_records(conn, records)
        conn.commit()
        print(f"  -> 파싱: {len(records)}건  적재: {ins}건  중복: {skp}건")
        total_inserted += ins
        total_skipped  += skp
        print()

    after = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    conn.close()

    print("=" * 50)
    print(f"완료: {before:,} -> {after:,}명  (+{total_inserted}건 신규 / {total_skipped}건 중복 스킵)")
    print(f"DB: {DB_PATH}")


if __name__ == "__main__":
    main()
