"""
parse_jobs.py — Bridge Base: raw job text → JSON / master.db

Wrapper around tools/legacy/load_jobs.py parser with simplified CLI.

Usage:
  # 1. Dry-run: parse and show JSON preview
  python parse_jobs.py --input raw_jobs.txt --output test_parsed.json --dry-run

  # 2. Save to DB
  python parse_jobs.py --input raw_jobs.txt --db master.db --source manual

  # 3. Migrate legacy data
  python parse_jobs.py --input all_legacy_jobs.txt --db master.db --source manual

  # 4. Use original file (default)
  python parse_jobs.py --dry-run
  python parse_jobs.py --db master.db
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Reuse parser logic from load_jobs.py
sys.path.insert(0, str(Path(__file__).parent / "tools" / "legacy"))
from load_jobs import (
    parse_jobs_txt,
    parse_salary,
    parse_daily_hours,
    split_location,
    JOB_COLS,
    upsert_jobs,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent
DEFAULT_INPUT = BASE_DIR / "original_jobs" / "BRIDGE_clients_jobs.txt"
DEFAULT_DB = BASE_DIR / "master.db"
NOW_ISO = datetime.now(timezone.utc).isoformat()


def main():
    ap = argparse.ArgumentParser(description="Parse raw job text files → JSON / DB")
    ap.add_argument("--input", "-i", type=str, default=str(DEFAULT_INPUT),
                    help="Input text file (default: original_jobs/BRIDGE_clients_jobs.txt)")
    ap.add_argument("--output", "-o", type=str, default="",
                    help="Output JSON file (dry-run mode)")
    ap.add_argument("--db", type=str, default="",
                    help="SQLite DB path to save parsed jobs")
    ap.add_argument("--source", type=str, default="manual",
                    help="source_file tag for DB records (default: manual)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Parse only, don't write to DB")
    args = ap.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    print(f"Parsing: {input_path.name}")
    records = parse_jobs_txt(input_path)

    # Override source_file
    for r in records:
        r["source_file"] = args.source if args.source != "manual" else input_path.name

    unique_codes = len({r["job_code"] for r in records})
    dup_codes = len({r["job_code"] for r in records if r["seq"] > 1})
    print(f"  Records: {len(records)}  |  Unique codes: {unique_codes}  |  Duplicates: {dup_codes}")

    # Dry-run: show preview
    if args.dry_run:
        print(f"\n--- Preview (first 10) ---")
        for j in records[:10]:
            dup = f" seq={j['seq']}" if j["seq"] > 1 else ""
            loc = j.get("location", "")[:25]
            sal = f"{j.get('salary_min', '?')}~{j.get('salary_max', '?')}M"
            print(f"  {j['job_code']:12s}{dup:8s} | {loc:25s} | {sal}")

        # Write JSON if output specified
        if args.output:
            out_path = Path(args.output)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2, default=str)
            print(f"\nJSON saved: {out_path} ({len(records)} records)")
        else:
            print("\n[DRY-RUN] No output file specified. Use --output to save JSON.")
        return

    # DB save
    db_path = Path(args.db) if args.db else DEFAULT_DB
    if not db_path.exists() and not args.db:
        print(f"ERROR: DB not found: {db_path}")
        sys.exit(1)

    print(f"\nSaving to DB: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        upsert_jobs(conn, records)
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        new_source = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE source_file = ?",
            (records[0]["source_file"],)
        ).fetchone()[0]
        print(f"  DB total jobs: {total:,}")
        print(f"  From this source: {new_source:,}")
        print(f"  Done.")
    finally:
        conn.close()

    # Also save JSON if output specified
    if args.output:
        out_path = Path(args.output)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2, default=str)
        print(f"  JSON also saved: {out_path}")


if __name__ == "__main__":
    main()
