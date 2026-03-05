"""
Craig RPA — 다른 PC 작업 기록 가져오기 (메인 PC에서 실행)
=========================================================
사용법: python import_craig_records.py craig_records.json
"""

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "master.db"


def main():
    if len(sys.argv) < 2:
        print("사용법: python import_craig_records.py <craig_records.json>")
        sys.exit(1)

    json_file = Path(sys.argv[1])
    if not json_file.exists():
        print(f"[ERROR] 파일 없음: {json_file}")
        sys.exit(1)

    with open(json_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"  가져올 기록: {len(records)}건")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout=5000")

    imported, skipped = 0, 0
    for r in records:
        # 중복 체크: job_code + seq + posted_at
        exists = conn.execute(
            "SELECT 1 FROM ad_posts WHERE job_code=? AND seq=? AND posted_at=?",
            (r.get("job_code"), r.get("seq"), r.get("posted_at"))
        ).fetchone()

        if exists:
            skipped += 1
            continue

        conn.execute(
            """INSERT INTO ad_posts
               (job_code, seq, platform, status, ad_title, ad_body,
                draft_at, posted_at, screenshot_path, error_msg, posted_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (r.get("job_code"), r.get("seq"), r.get("platform", "craigslist"),
             r.get("status", "posted"), r.get("ad_title"), r.get("ad_body"),
             r.get("draft_at"), r.get("posted_at"),
             r.get("screenshot_path"), r.get("error_msg"), r.get("posted_url"))
        )
        imported += 1

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM ad_posts").fetchone()[0]
    conn.close()

    print(f"  [OK] {imported}건 가져오기 완료 (중복 {skipped}건 건너뜀)")
    print(f"  현재 총 기록: {total}건")


if __name__ == "__main__":
    main()
