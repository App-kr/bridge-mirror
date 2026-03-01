"""
BRIDGE Supabase 이관 스크립트
================================
bridge base master.db (SQLite) → Supabase PostgreSQL 전량 이관

실행 전 준비:
  1. Supabase 프로젝트에서 supabase_schema.sql 실행 완료
  2. .env 에 SUPABASE_URL + SUPABASE_SERVICE_KEY 입력
  3. pip install supabase python-dotenv

실행:
  python migrate_to_supabase.py            # 전체 이관
  python migrate_to_supabase.py --dry-run  # 건수만 확인 (실제 업로드 안 함)
  python migrate_to_supabase.py --table candidates  # 특정 테이블만
"""
import io
import os
import sys
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── dotenv 로드 ──────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path("Q:/Claudework/bridge base/.env"))
except ImportError:
    pass

try:
    from supabase import create_client, Client
except ImportError:
    print("[ERROR] supabase 패키지 없음: pip install supabase")
    sys.exit(1)

# ── 설정 ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path("Q:/Claudework/bridge base")
DB_PATH  = BASE_DIR / "master.db"

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")  # service role key (RLS 우회)

BATCH_SIZE = 100   # 한 번에 upsert 할 레코드 수

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────
def clean(val):
    """None / 빈 문자열 정리"""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def batch_upsert(client: "Client", table: str, rows: list[dict], on_conflict: str):
    """배치 upsert. 실패 시 오류 출력 후 계속."""
    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        chunk = rows[i:i + BATCH_SIZE]
        try:
            client.table(table).upsert(chunk, on_conflict=on_conflict).execute()
            total += len(chunk)
            print(f"  [{table}] {total}/{len(rows)} 완료", end="\r")
        except Exception as e:
            print(f"\n  [WARN] 배치 오류 (row {i}~{i+len(chunk)}): {e}")
    print()
    return total


# ── 테이블별 이관 함수 ─────────────────────────────────────────────────────────
def migrate_candidates(conn: sqlite3.Connection, client: "Client", dry_run: bool) -> int:
    rows_db = conn.execute("""
        SELECT candidate_id, email, full_name, nationality, ancestry, dob, gender,
               current_location, start_date, target, area_prefs, experience, employment,
               current_salary, desired_salary, certification, e_visa, mobile_phone,
               kakaotalk, criminal_record, passport, housing, arc_holders, job_prefs,
               reference, documents, status, source_file, created_at, updated_at
        FROM candidates
    """).fetchall()

    cols = [
        "legacy_id","email","full_name","nationality","ancestry","dob","gender",
        "current_location","start_date","target_age","area_prefs","experience","employment",
        "current_salary","desired_salary","certification","e_visa","mobile_phone",
        "kakaotalk","criminal_record","passport","housing","arc_holders","job_prefs",
        "reference","documents","status","source_file","created_at","updated_at"
    ]

    records = []
    for row in rows_db:
        rec = dict(zip(cols, [clean(v) for v in row]))
        # status 검증
        if rec["status"] not in ("Active","Inactive","Placed","Blacklist"):
            rec["status"] = "Active"
        # source 필드 (Supabase 스키마 필수)
        rec["source"] = "import"
        records.append(rec)

    print(f"  candidates: {len(records):,}건 준비")
    if dry_run:
        return len(records)

    return batch_upsert(client, "candidates", records, "legacy_id")


def migrate_jobs(conn: sqlite3.Connection, client: "Client", dry_run: bool) -> int:
    rows_db = conn.execute("""
        SELECT id, job_code, seq, location, city, district,
               start_date, teaching_age, class_size, working_hours,
               daily_hours, teach_hrs_week,
               salary_min, salary_max, salary_raw,
               vacation, housing, native_count, benefits,
               is_hot, is_part_time, status, internal_notes, source_file,
               created_at, updated_at
        FROM jobs
    """).fetchall()

    cols = [
        "legacy_id","job_code","seq","location","city","district",
        "start_date","teaching_age","class_size","working_hours",
        "daily_hours","teach_hrs_week",
        "salary_min","salary_max","salary_raw",
        "vacation","housing","native_count","benefits",
        "is_hot","is_part_time","status","internal_notes","source_file",
        "created_at","updated_at"
    ]

    records = []
    for row in rows_db:
        rec = dict(zip(cols, [clean(v) for v in row]))
        # Boolean 변환
        rec["is_hot"]      = bool(rec.get("is_hot"))
        rec["is_part_time"]= bool(rec.get("is_part_time"))
        # Numeric
        for col in ("daily_hours","salary_min","salary_max"):
            try:
                rec[col] = float(rec[col]) if rec[col] else None
            except (TypeError, ValueError):
                rec[col] = None
        # legacy_id 는 integer
        try:
            rec["legacy_id"] = int(rec["legacy_id"]) if rec["legacy_id"] else None
        except (TypeError, ValueError):
            rec["legacy_id"] = None
        # status 검증
        if rec["status"] not in ("open","filled","hold","cancelled"):
            rec["status"] = "open"
        records.append(rec)

    print(f"  jobs: {len(records):,}건 준비")
    if dry_run:
        return len(records)

    return batch_upsert(client, "jobs", records, "legacy_id")


def migrate_client_inquiries(conn: sqlite3.Connection, client: "Client", dry_run: bool) -> int:
    # 실제 컬럼 확인
    try:
        cols_info = conn.execute("PRAGMA table_info(client_inquiries)").fetchall()
        db_cols = [c[1] for c in cols_info]
    except Exception:
        print("  [SKIP] client_inquiries 테이블 없음")
        return 0

    rows_db = conn.execute("SELECT * FROM client_inquiries").fetchall()

    # SQLite → Supabase 컬럼 매핑
    mapping = {
        "id":             "legacy_id",
        "submitted_at":   "submitted_at",
        "email":          "email",
        "school_name":    "school_name",
        "location":       "location",
        "contact_name":   "contact_name",
        "phone":          "phone",
        "start_date":     "start_date",
        "vacancies":      "vacancies",
        "teaching_age":   "teaching_age",
        "schedule":       "schedule",
        "working_hours":  "working_hours",
        "salary_raw":     "salary_raw",
        "housing_type":   "housing_type",
        "housing_detail": "housing_detail",
        "travel_support": "travel_support",
        "benefits":       "benefits",
        "vacation":       "vacation",
        "sick_leave":     "sick_leave",
        "meal":           "meal",
        "memo":           "memo",
        "status":         "status",
        "source":         "source",
        "source_file":    "source_file",
        "created_at":     "created_at",
        "updated_at":     "updated_at",
    }

    records = []
    for row in rows_db:
        row_dict = dict(zip(db_cols, row))
        rec = {}
        for src_col, dst_col in mapping.items():
            if src_col in row_dict:
                rec[dst_col] = clean(row_dict[src_col])
        # legacy_id 는 integer
        try:
            rec["legacy_id"] = int(rec["legacy_id"]) if rec.get("legacy_id") else None
        except (TypeError, ValueError):
            rec["legacy_id"] = None
        # status 검증
        if rec.get("status") not in ("pending","matched","filled","cancelled"):
            rec["status"] = "pending"
        if not rec.get("source"):
            rec["source"] = "import"
        records.append(rec)

    print(f"  client_inquiries: {len(records):,}건 준비")
    if dry_run:
        return len(records)

    return batch_upsert(client, "client_inquiries", records, "legacy_id")


def migrate_ad_posts(conn: sqlite3.Connection, client: "Client", dry_run: bool) -> int:
    try:
        rows_db = conn.execute("""
            SELECT id, job_code, seq, platform, status,
                   ad_title, ad_body, posted_url, posted_at, expires_at,
                   created_at, updated_at
            FROM ad_posts
        """).fetchall()
    except Exception:
        print("  [SKIP] ad_posts 테이블 없음")
        return 0

    if not rows_db:
        print("  ad_posts: 0건 (스킵)")
        return 0

    cols = [
        "legacy_id","job_code","seq","platform","status",
        "ad_title","ad_body","posted_url","posted_at","expires_at",
        "created_at","updated_at"
    ]

    records = []
    for row in rows_db:
        rec = dict(zip(cols, [clean(v) for v in row]))
        try:
            rec["legacy_id"] = int(rec["legacy_id"]) if rec["legacy_id"] else None
        except (TypeError, ValueError):
            rec["legacy_id"] = None
        records.append(rec)

    print(f"  ad_posts: {len(records):,}건 준비")
    if dry_run:
        return len(records)

    return batch_upsert(client, "ad_posts", records, "legacy_id")


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="BRIDGE Supabase 이관")
    parser.add_argument("--dry-run", action="store_true", help="건수 확인만 (업로드 안 함)")
    parser.add_argument("--table",   default="all",
                        choices=["all","candidates","jobs","client_inquiries","ad_posts"],
                        help="특정 테이블만 이관")
    args = parser.parse_args()

    # 자격증명 확인
    if not args.dry_run:
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("[ERROR] .env 에 SUPABASE_URL 과 SUPABASE_SERVICE_KEY 를 입력하세요.")
            print("  Supabase 대시보드 → Settings → API → service_role key")
            sys.exit(1)

    print("=" * 55)
    print("  BRIDGE → Supabase 이관 스크립트")
    print(f"  DB   : {DB_PATH}")
    print(f"  모드  : {'DRY-RUN (건수 확인만)' if args.dry_run else '실제 이관'}")
    print(f"  대상  : {args.table}")
    print("=" * 55)

    conn = sqlite3.connect(str(DB_PATH))

    sb_client = None
    if not args.dry_run:
        sb_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"  Supabase 연결: {SUPABASE_URL[:40]}...")
    print()

    total = 0
    run_all = args.table == "all"

    if run_all or args.table == "candidates":
        total += migrate_candidates(conn, sb_client, args.dry_run)

    if run_all or args.table == "jobs":
        total += migrate_jobs(conn, sb_client, args.dry_run)

    if run_all or args.table == "client_inquiries":
        total += migrate_client_inquiries(conn, sb_client, args.dry_run)

    if run_all or args.table == "ad_posts":
        total += migrate_ad_posts(conn, sb_client, args.dry_run)

    conn.close()

    print()
    print("=" * 55)
    if args.dry_run:
        print(f"  [DRY-RUN] 이관 예정: {total:,}건")
        print("  --dry-run 없이 재실행하면 실제 업로드됩니다.")
    else:
        print(f"  완료: 총 {total:,}건 Supabase 업로드")
    print("=" * 55)


if __name__ == "__main__":
    main()
