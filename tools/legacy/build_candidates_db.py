"""
BRIDGE Candidates DB Builder
==============================
original_candidates/*.csv + intake/candidates/*.csv
→ bridge base master.db 의 candidates 테이블에 전량 적재

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

def stable_id(email: str, name: str, row_num: int, fname: str) -> str:
    raw = f"{fname}||{row_num}||{email}||{name}"
    return "cnd_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

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

def load_csv(fpath: Path, status: str = "Active") -> list[dict]:
    """CSV → 레코드 리스트 반환. 헤더 자동 감지."""
    records = []
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
        if "Full name" in " ".join(row) or "이메일 주소" in " ".join(row):
            header_idx = i
            break

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

        # 컬럼 인덱스 (bridge_candidates_data.csv 기준 52컬럼)
        # bridge_candidates_data new.csv 는 50컬럼 (col04=ARC holders 있음)
        # 두 포맷 모두 지원: col04가 비어있으면 구형식
        arc_col = 4 if get_val(row, 4) != "" or len(row) <= 50 else None
        offset  = 0  # 두 포맷이 거의 동일하므로 offset 없이 처리

        records.append({
            "candidate_id":    cid,
            "email":           email,
            "full_name":       name,
            "nationality":     get_val(row, 5),
            "ancestry":        get_val(row, 6),
            "dob":             get_val(row, 7),
            "gender":          get_val(row, 8),
            "current_location":get_val(row, 9),
            "start_date":      get_val(row, 10),
            "target":          get_val(row, 11),
            "area_prefs":      get_val(row, 12),
            "reference":       get_val(row, 13),
            "experience":      get_val(row, 14),
            "employment":      get_val(row, 15),
            "job_prefs":       get_val(row, 16),
            "current_salary":  get_val(row, 19),
            "desired_salary":  get_val(row, 20),
            "certification":   get_val(row, 24),
            "documents":       get_val(row, 25),
            "e_visa":          get_val(row, 34),
            "kakaotalk":       get_val(row, 35),
            "mobile_phone":    get_val(row, 36),
            "criminal_record": get_val(row, 37),
            "passport":        get_val(row, 39),
            "housing":         get_val(row, 32),
            "arc_holders":     get_val(row, 4),
            "status":          status,
            "source_file":     fpath.name,
            "source_row":      str(row_num),
            "created_at":      NOW,
            "updated_at":      NOW,
        })

    return records


def upsert_records(conn: sqlite3.Connection, records: list[dict]) -> tuple[int, int]:
    inserted = skipped = 0
    for rec in records:
        existing = conn.execute(
            "SELECT candidate_id FROM candidates WHERE candidate_id=?",
            (rec["candidate_id"],)
        ).fetchone()
        if existing:
            skipped += 1
            continue
        conn.execute("""
            INSERT INTO candidates (
                candidate_id, email, full_name, nationality, ancestry, dob, gender,
                current_location, start_date, target, area_prefs, experience, employment,
                current_salary, desired_salary, certification, e_visa, mobile_phone,
                kakaotalk, criminal_record, passport, housing, arc_holders, job_prefs,
                reference, documents, status, source_file, source_row, created_at, updated_at
            ) VALUES (
                :candidate_id,:email,:full_name,:nationality,:ancestry,:dob,:gender,
                :current_location,:start_date,:target,:area_prefs,:experience,:employment,
                :current_salary,:desired_salary,:certification,:e_visa,:mobile_phone,
                :kakaotalk,:criminal_record,:passport,:housing,:arc_holders,:job_prefs,
                :reference,:documents,:status,:source_file,:source_row,:created_at,:updated_at
            )
        """, rec)
        inserted += 1
    return inserted, skipped


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(CREATE_SQL)
    conn.commit()

    before = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    print(f"시작 전 candidates: {before:,}건")
    print()

    total_inserted = 0
    total_skipped  = 0

    # 1. 원본 마스터 CSV (Inactive — 기존 데이터)
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
