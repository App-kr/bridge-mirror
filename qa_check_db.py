#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QA DB Check Script"""
import sqlite3
import json
from pathlib import Path

db_path = Path(__file__).parent / "master.db"

if not db_path.exists():
    print(f"ERROR: DB not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Table list
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    print(f"[DB] Total tables: {len(tables)}")

    # Key metrics
    cursor.execute("SELECT COUNT(*) FROM candidates")
    candidates = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM candidates WHERE is_deleted=1")
    deleted = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM client_inquiries")
    inquiries = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs")
    jobs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM file_uploads")
    files = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ad_posts")
    ad_posts = cursor.fetchone()[0]

    print(f"\n[RECORDS]")
    print(f"  candidates: {candidates} (deleted: {deleted}, active: {candidates - deleted})")
    print(f"  client_inquiries: {inquiries}")
    print(f"  jobs: {jobs}")
    print(f"  file_uploads: {files}")
    print(f"  ad_posts: {ad_posts}")

    # Check key columns
    cursor.execute("PRAGMA table_info(candidates)")
    cols = [row[1] for row in cursor.fetchall()]
    print(f"\n[COLUMNS] candidates has {len(cols)} columns")

    if 'is_deleted' in cols:
        print(f"  ✅ is_deleted column exists")
    else:
        print(f"  ❌ is_deleted column MISSING")

    if 'email' in cols:
        cursor.execute("SELECT COUNT(*) FROM candidates WHERE email IS NULL OR email=''")
        null_emails = cursor.fetchone()[0]
        print(f"  email: {null_emails} NULL/empty out of {candidates}")

    # Check ad_posts table structure
    cursor.execute("PRAGMA table_info(ad_posts)")
    ad_cols = [row[1] for row in cursor.fetchall()]
    if ad_cols:
        print(f"\n[AD_POSTS] has {len(ad_cols)} columns: {', '.join(ad_cols[:5])}...")

    # Recent ad posts
    cursor.execute("SELECT COUNT(*) FROM ad_posts WHERE posted=1")
    posted = cursor.fetchone()[0]
    print(f"  posted ads: {posted}")

    conn.close()

except Exception as e:
    print(f"ERROR: {e}")
    exit(1)
