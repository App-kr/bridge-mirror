"""
migration.py — Bridge Base: CSV → Supabase Migration Tool

Reads legacy candidate and client data from CSV exports,
maps columns to the Supabase schema, encrypts sensitive fields,
and inserts records in batches.

Usage:
    python migration.py                           # live migration (all tables)
    python migration.py --dry-run                 # validate & preview, no DB writes
    python migration.py --table candidates        # migrate only candidates
    python migration.py --table clients           # migrate only clients
    python migration.py --delete-source           # remove CSVs after success (IRREVERSIBLE)
    python migration.py --dry-run --table clients # dry-run single table

Dependencies:
    pip install supabase python-dotenv cryptography
"""

import argparse
import csv
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 output so Korean/Unicode data prints correctly on Windows (CP949 terminal)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Environment ───────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# ── Dependency Checks ─────────────────────────────────────────────────────────

try:
    from security_vault import encrypt_field, is_encrypted
except ImportError:
    print("[ERROR] security_vault.py not found in the same directory.")
    sys.exit(1)

# supabase is imported lazily in get_supabase_client() so that
# --dry-run works even if httpcore/supabase has a Python version conflict.

# ── File Paths ────────────────────────────────────────────────────────────────

CANDIDATES_CSV = BASE_DIR / "candidates_old.csv.csv"
CLIENTS_CSV    = BASE_DIR / "clients_old.csv.csv"

# ── Column Mappings: CSV header → Supabase column name ───────────────────────
# Keys are stripped of whitespace when reading, so trailing spaces are safe.

CANDIDATES_COLUMN_MAP = {
    "타임스탬프":                 "submitted_at",
    "이메일 주소":                "email",
    "How to":                     "source",
    "Attach your files":          "document_links",
    "Full name":                  "full_name",
    "Nationality":                "nationality",
    "Family Ancestry Background": "ethnicity",
    "Date of Birth":              "date_of_birth",
    "Gender":                     "gender",
    "Current Location":           "current_location",
    "Educational Background":     "education",
    "Major":                      "major",
    "Certification":              "certification",
    "E visa":                     "e_visa_status",
    "ARC holders":                "arc_status",
    "Passport":                   "passport_status",       # SENSITIVE
    "Criminal Record":            "criminal_record",       # SENSITIVE
    "Document Status":            "document_status",
    "Start date":                 "available_from",
    "Target":                     "target_students",
    "Area prefs":                 "area_preferences",
    "Job prefs (Notes)":          "job_preferences",
    "Experience":                 "experience",
    "Employment":                 "current_employer",
    "Reference":                  "reference_contact",
    "Current salary":             "current_salary",
    "Desired salary":             "desired_salary",
    "Marital Status":             "marital_status",
    "Dependents Pets":            "dependents",
    "Housing":                    "housing_preference",
    "Personal Considerations":    "personal_considerations",
    "Religion":                   "religion",
    "Health Information":         "health_info",           # SENSITIVE
    "Criminal Record Check":      "criminal_record_check", # SENSITIVE
    "Interview time":             "interview_availability",
    "KakaoTalk":                  "kakaotalk",
    "Mobile Phone":               "mobile_phone",
    "Agreement":                  "agreement",
    "Facts":                      "facts_verified",
    "메모":                       "memo",
}

CLIENTS_COLUMN_MAP = {
    "타임스탬프":       "submitted_at",
    "이메일 주소":      "email",
    "채용인원":         "recruitment_count",
    "성함직책":         "contact_name",
    "휴대전화":         "phone",
    "사업자":           "business_registration",  # SENSITIVE
    "학교이름Name":     "school_name",
    "채용이력":         "hiring_history",
    "근무처소재지":     "location",
    "원어민강사":       "native_teacher_count",
    "희망시작일":       "desired_start_date",
    "수업대상":         "class_target",
    "근무요일":         "work_days",
    "근무일정":         "work_schedule",
    "거주지":           "residence",
    "학생수":           "student_count",
    "평균강의":         "teaching_hours",
    "프렙타임":         "prep_time",
    "선호대상":         "preferred_candidates",
    "급여조건":         "salary_conditions",
    "숙소제공":         "housing_provided",
    "숙소관련":         "housing_details",
    "이동지원":         "transport_support",
    "복지":             "benefits",
    "유급휴일":         "paid_holidays",
    "휴일 포함여부":    "holiday_inclusion",
    "메모Memo":         "memo",
    "개인정보처리방침": "privacy_agreement",
    "계약구분":         "contract_type",
    "휴게시간":         "break_time",
    "업무책임":         "responsibilities",
    "보건휴가":         "health_leave",
    "식사식대":         "meal_allowance",
}

# Sensitive DB column names that must be encrypted before storage
CANDIDATES_SENSITIVE = {
    "passport_status",
    "criminal_record",
    "health_info",
    "criminal_record_check",
}

CLIENTS_SENSITIVE = {
    "business_registration",
}


# ── CSV Reading ───────────────────────────────────────────────────────────────

def read_csv(filepath: Path) -> list:
    """
    Read a CSV file and return a list of row dicts.
    Column names are stripped of leading/trailing whitespace.
    Tries UTF-8-BOM, UTF-8, then CP949 (for Korean Excel exports).
    """
    encodings = ["utf-8-sig", "utf-8", "cp949"]
    for enc in encodings:
        try:
            rows = []
            with open(filepath, encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Strip whitespace from all keys to normalise headers
                    rows.append({k.strip(): (v or "").strip() for k, v in row.items()})
            return rows
        except UnicodeDecodeError:
            continue
        except Exception as exc:
            raise IOError(f"Failed to read {filepath}: {exc}") from exc

    raise IOError(
        f"Could not decode {filepath.name} with any of {encodings}. "
        "Please check the file encoding."
    )


# ── Row Mapping & Encryption ──────────────────────────────────────────────────

def map_row(
    raw: dict,
    column_map: dict,
    sensitive_fields: set,
    dry_run: bool,
) -> dict:
    """
    Map a raw CSV row dict to a Supabase-schema dict.
    Encrypts sensitive fields (or shows a preview marker in dry-run mode).
    Unmapped CSV columns are silently ignored.
    Empty strings are stored as None (NULL in Supabase).
    """
    record = {}
    for csv_col, db_col in column_map.items():
        value = raw.get(csv_col, "") or ""

        if db_col in sensitive_fields:
            if dry_run:
                preview = value[:25] + "..." if len(value) > 25 else value
                value = f"[WILL ENCRYPT → '{preview}']" if value else None
            else:
                value = encrypt_field(value) if value else None
        else:
            value = value if value else None

        record[db_col] = value

    return record


# ── Validation ────────────────────────────────────────────────────────────────

def validate_candidate(record: dict) -> list:
    """Return a list of validation warning strings for a candidate record."""
    warnings = []
    if not record.get("email"):
        warnings.append("missing email")
    if not record.get("full_name"):
        warnings.append("missing full_name")
    if not record.get("nationality"):
        warnings.append("missing nationality")
    return warnings


def validate_client(record: dict) -> list:
    """Return a list of validation warning strings for a client record."""
    warnings = []
    if not record.get("email"):
        warnings.append("missing email")
    if not record.get("school_name"):
        warnings.append("missing school_name")
    if not record.get("contact_name"):
        warnings.append("missing contact_name")
    return warnings


# ── Dry-Run Report ────────────────────────────────────────────────────────────

def print_dry_run_report(records: list, table: str, sensitive: set, validator) -> bool:
    """
    Print a dry-run validation report.
    Returns True if there are no validation errors (warnings are non-blocking).
    """
    SEP = "=" * 72
    print(f"\n{SEP}")
    print(f"  DRY RUN │ TABLE: {table.upper()} │ {len(records)} rows")
    print(SEP)

    rows_with_warnings = []
    preview_limit = 3

    for i, rec in enumerate(records):
        warnings = validator(rec)
        if warnings:
            rows_with_warnings.append((i + 1, warnings))

        if i < preview_limit:
            identifier = rec.get("email") or rec.get("school_name") or f"row {i+1}"
            print(f"\n  +-- Row {i+1}: {identifier}")
            for col, val in rec.items():
                display = str(val) if val is not None else "(null)"
                if len(display) > 65:
                    display = display[:62] + "..."
                marker = " [ENCRYPTED]" if col in sensitive else ""
                print(f"  |  {col:<32} {display}{marker}")
            if warnings:
                print(f"  |  [!] Warnings: {', '.join(warnings)}")
            print(f"  +{'-'*60}")

    if len(records) > preview_limit:
        print(f"\n  ... {len(records) - preview_limit} more rows not shown in preview.")

    print(f"\n  -- Validation Summary ------------------------------------------")
    print(f"     Total rows        : {len(records)}")
    print(f"     Rows with warnings: {len(rows_with_warnings)}")
    print(f"     Sensitive fields  : {sorted(sensitive)}")

    if rows_with_warnings:
        print(f"\n  -- Warning Details ---------------------------------------------")
        for row_num, warns in rows_with_warnings[:10]:
            print(f"     Row {row_num:3d}: {', '.join(warns)}")
        if len(rows_with_warnings) > 10:
            print(f"     ... and {len(rows_with_warnings) - 10} more")

    print(f"\n{SEP}\n")
    return True  # warnings are non-blocking


# ── Supabase Client ───────────────────────────────────────────────────────────

def get_supabase_client():
    """Create and return an authenticated Supabase client (lazy import)."""
    try:
        from supabase import create_client
    except ImportError as exc:
        raise ImportError(
            "supabase-py is not installed or incompatible with this Python version.\n"
            "Run: pip install supabase\n"
            f"Original error: {exc}"
        ) from exc

    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not url:
        raise EnvironmentError("SUPABASE_URL is not set in .env")
    if not key:
        raise EnvironmentError("SUPABASE_SERVICE_ROLE_KEY is not set in .env")

    return create_client(url, key)


# ── Batch Insert ──────────────────────────────────────────────────────────────

BATCH_SIZE = 100

def insert_records(client, table: str, records: list) -> int:
    """
    Insert records into a Supabase table in batches of BATCH_SIZE.
    Returns the total number of successfully inserted rows.
    """
    total_inserted = 0
    total_batches = (len(records) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num, start in enumerate(range(0, len(records), BATCH_SIZE), 1):
        batch = records[start : start + BATCH_SIZE]
        try:
            response = client.table(table).insert(batch).execute()
            inserted = len(response.data) if response.data else len(batch)
            total_inserted += inserted
            print(
                f"  Batch {batch_num}/{total_batches}: "
                f"inserted {inserted} rows → {table}"
            )
        except Exception as exc:
            print(f"  [ERROR] Batch {batch_num} failed: {exc}")
            raise

    return total_inserted


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Bridge Base — CSV to Supabase Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and preview data without writing to Supabase.",
    )
    parser.add_argument(
        "--table",
        choices=["candidates", "clients", "all"],
        default="all",
        help="Which table to migrate (default: all).",
    )
    parser.add_argument(
        "--delete-source",
        action="store_true",
        help="IRREVERSIBLE: Delete source CSV files after successful migration.",
    )
    args = parser.parse_args()

    # ── Header ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  Bridge Base - Migration Tool")
    print("=" * 72)
    print(f"  Mode         : {'DRY RUN (read-only)' if args.dry_run else 'LIVE MIGRATION'}")
    print(f"  Target table : {args.table}")
    print(f"  Delete source: {'YES - CSVs will be deleted after success' if args.delete_source else 'No'}")
    if args.dry_run:
        print("  NOTE: No data will be written to Supabase in dry-run mode.")
    print()

    # ── Supabase Connection (skip in dry-run) ─────────────────────────────────
    supabase = None
    if not args.dry_run:
        print("Connecting to Supabase...")
        try:
            supabase = get_supabase_client()
            print("  Connection OK.\n")
        except Exception as exc:
            print(f"[ERROR] Supabase connection failed: {exc}")
            sys.exit(1)

    migration_success = True
    migrated_files = []

    # ── Candidates ────────────────────────────────────────────────────────────
    if args.table in ("candidates", "all"):
        step = "1/2" if args.table == "all" else "1/1"
        print(f"[{step}] Candidates  ← {CANDIDATES_CSV.name}")

        if not CANDIDATES_CSV.exists():
            print(f"  [ERROR] File not found: {CANDIDATES_CSV}")
            migration_success = False
        else:
            try:
                raw_rows = read_csv(CANDIDATES_CSV)
                print(f"  Read {len(raw_rows)} rows.")

                records = [
                    map_row(r, CANDIDATES_COLUMN_MAP, CANDIDATES_SENSITIVE, args.dry_run)
                    for r in raw_rows
                ]

                if args.dry_run:
                    print_dry_run_report(records, "candidates", CANDIDATES_SENSITIVE, validate_candidate)
                else:
                    count = insert_records(supabase, "candidates", records)
                    print(f"  Inserted {count}/{len(records)} candidates.\n")
                    migrated_files.append(CANDIDATES_CSV)

            except Exception as exc:
                print(f"  [ERROR] {exc}")
                migration_success = False

    # ── Clients ───────────────────────────────────────────────────────────────
    if args.table in ("clients", "all"):
        step = "2/2" if args.table == "all" else "1/1"
        print(f"[{step}] Clients     ← {CLIENTS_CSV.name}")

        if not CLIENTS_CSV.exists():
            print(f"  [ERROR] File not found: {CLIENTS_CSV}")
            migration_success = False
        else:
            try:
                raw_rows = read_csv(CLIENTS_CSV)
                print(f"  Read {len(raw_rows)} rows.")

                records = [
                    map_row(r, CLIENTS_COLUMN_MAP, CLIENTS_SENSITIVE, args.dry_run)
                    for r in raw_rows
                ]

                if args.dry_run:
                    print_dry_run_report(records, "clients", CLIENTS_SENSITIVE, validate_client)
                else:
                    count = insert_records(supabase, "clients", records)
                    print(f"  Inserted {count}/{len(records)} clients.\n")
                    migrated_files.append(CLIENTS_CSV)

            except Exception as exc:
                print(f"  [ERROR] {exc}")
                migration_success = False

    # ── Post-migration: Delete Source CSVs ────────────────────────────────────
    if not args.dry_run and args.delete_source and migration_success and migrated_files:
        print("\n[Cleanup] Deleting source CSV files...")
        for filepath in migrated_files:
            try:
                os.remove(filepath)
                print(f"  Deleted: {filepath.name}")
            except OSError as exc:
                print(f"  [WARNING] Could not delete {filepath.name}: {exc}")

    # ── Final Summary ─────────────────────────────────────────────────────────
    print("=" * 72)
    if args.dry_run:
        print("  DRY RUN complete.")
        print("  If the output looks correct, run without --dry-run to migrate.")
    elif migration_success:
        print("  Migration completed successfully.")
        if args.delete_source:
            print("  Source CSV files have been deleted.")
    else:
        print("  Migration completed with errors. Review output above.")
        sys.exit(1)
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()
