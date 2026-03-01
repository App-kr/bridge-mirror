"""
통합 수신함용 DB 마이그레이션
- master.db (SQLite): candidates 테이블에 inbox 컬럼 추가
- Supabase: ALTER TABLE (수동 실행 SQL 출력)

실행: python migrations/db_migration_inbox.py
"""
import os
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(os.getenv("BRIDGE_DB_PATH", "./master.db"))

# ── SQLite 마이그레이션 ────────────────────────────────────────────────────────
SQLITE_COLUMNS = [
    ("source",           "TEXT DEFAULT 'website'"),
    ("inbox_status",     "TEXT DEFAULT 'new'"),
    ("gmail_message_id", "TEXT"),
    ("raw_email_body",   "TEXT"),
    ("parsed_data",      "TEXT"),      # JSON string
    ("notes",            "TEXT"),
    ("assigned_to",      "TEXT"),
    ("last_activity",    "TEXT"),
]

# client_inquiries에도 동일 컬럼 추가
INQUIRY_COLUMNS = [
    ("source",           "TEXT DEFAULT 'website'"),
    ("inbox_status",     "TEXT DEFAULT 'new'"),
    ("gmail_message_id", "TEXT"),
    ("raw_email_body",   "TEXT"),
    ("parsed_data",      "TEXT"),
    ("notes",            "TEXT"),
    ("assigned_to",      "TEXT"),
    ("last_activity",    "TEXT"),
]


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """테이블에 컬럼이 존재하는지 확인."""
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def migrate_sqlite():
    """master.db에 inbox 컬럼 추가 (IF NOT EXISTS 방식)."""
    if not DB_PATH.exists():
        print(f"[WARN] {DB_PATH} not found — skip SQLite migration")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")

    # candidates 테이블
    added = 0
    for col_name, col_def in SQLITE_COLUMNS:
        if not _column_exists(conn, "candidates", col_name):
            conn.execute(f"ALTER TABLE candidates ADD COLUMN {col_name} {col_def}")
            added += 1
            print(f"  [OK] candidates.{col_name} added")
        else:
            print(f"  [SKIP] candidates.{col_name} already exists")

    # client_inquiries 테이블
    for col_name, col_def in INQUIRY_COLUMNS:
        if not _column_exists(conn, "client_inquiries", col_name):
            conn.execute(f"ALTER TABLE client_inquiries ADD COLUMN {col_name} {col_def}")
            added += 1
            print(f"  [OK] client_inquiries.{col_name} added")
        else:
            print(f"  [SKIP] client_inquiries.{col_name} already exists")

    # gmail_message_id 인덱스
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_candidates_gmail_msg_id
        ON candidates(gmail_message_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_inquiries_gmail_msg_id
        ON client_inquiries(gmail_message_id)
    """)
    # inbox_status 인덱스
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_candidates_inbox_status
        ON candidates(inbox_status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_inquiries_inbox_status
        ON client_inquiries(inbox_status)
    """)

    conn.commit()
    conn.close()
    print(f"\n[DONE] SQLite migration: {added} columns added")


# ── Supabase 마이그레이션 SQL (수동 실행) ───────────────────────────────────────
SUPABASE_SQL = """
-- Supabase 관리 콘솔 SQL Editor에서 실행:

-- candidates 테이블
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS inbox_status TEXT DEFAULT 'new';
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS gmail_message_id TEXT;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS raw_email_body TEXT;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS parsed_data JSONB;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS assigned_to TEXT;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS last_activity TIMESTAMPTZ DEFAULT now();

-- client_inquiries 테이블
ALTER TABLE client_inquiries ADD COLUMN IF NOT EXISTS inbox_status TEXT DEFAULT 'new';
ALTER TABLE client_inquiries ADD COLUMN IF NOT EXISTS gmail_message_id TEXT;
ALTER TABLE client_inquiries ADD COLUMN IF NOT EXISTS raw_email_body TEXT;
ALTER TABLE client_inquiries ADD COLUMN IF NOT EXISTS parsed_data JSONB;
ALTER TABLE client_inquiries ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE client_inquiries ADD COLUMN IF NOT EXISTS assigned_to TEXT;
ALTER TABLE client_inquiries ADD COLUMN IF NOT EXISTS last_activity TIMESTAMPTZ DEFAULT now();

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_candidates_gmail_msg ON candidates(gmail_message_id);
CREATE INDEX IF NOT EXISTS idx_candidates_inbox_status ON candidates(inbox_status);
CREATE INDEX IF NOT EXISTS idx_inquiries_gmail_msg ON client_inquiries(gmail_message_id);
CREATE INDEX IF NOT EXISTS idx_inquiries_inbox_status ON client_inquiries(inbox_status);
"""


def main():
    print("=" * 60)
    print("BRIDGE 통합 수신함 — DB 마이그레이션")
    print("=" * 60)

    print("\n[1/2] SQLite (master.db) 마이그레이션...")
    migrate_sqlite()

    print("\n[2/2] Supabase SQL (수동 실행 필요):")
    print(SUPABASE_SQL)

    print("=" * 60)
    print("완료. Supabase SQL은 관리 콘솔에서 직접 실행하세요.")


if __name__ == "__main__":
    main()
