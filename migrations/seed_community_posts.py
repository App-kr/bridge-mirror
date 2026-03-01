"""
community_posts 시드 데이터 삽입
================================
migrations/post_content/ 폴더의 JSON 파일들을 master.db에 삽입합니다.
중복 방지: 동일 title + board 조합이 이미 있으면 스킵.

실행:
  python migrations/seed_community_posts.py
"""

import os
import sys
import json
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger("seed_posts")

DB_PATH = os.getenv("BRIDGE_DB_PATH", str(Path(__file__).resolve().parent.parent / "master.db"))
CONTENT_DIR = Path(__file__).resolve().parent / "post_content"

# JSON 파일명 → board 매핑
FILE_BOARD_MAP = {
    "visa_posts.json": "visa",
    "support_kr_posts.json": "support_kr",
    "support_posts.json": "support",
    "support_en_posts.json": "support",
    "about_posts.json": "about",
    "about_posts_extra.json": "about",
    "korea_posts.json": "korea",
    "korea_posts_extra.json": "korea",
    "tips_posts.json": "tips",
    "testimonials_posts.json": "testimonials",
    "testimonials_posts_extra.json": "testimonials",
}

INSERT_SQL = """
    INSERT INTO community_posts (board, title, body, author_hash, pinned)
    SELECT ?, ?, ?, 'bridge_admin', ?
    WHERE NOT EXISTS (
        SELECT 1 FROM community_posts WHERE title = ? AND board = ? AND is_deleted = 0
    )
"""


def seed(db_path: str) -> None:
    if not Path(db_path).exists():
        log.error("DB not found: %s", db_path)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 5000")

    total_inserted = 0

    for filename, board in FILE_BOARD_MAP.items():
        filepath = CONTENT_DIR / filename
        if not filepath.exists():
            log.warning("파일 없음 — 스킵: %s", filepath)
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            posts = json.load(f)

        inserted = 0
        for post in posts:
            title = post["title"].strip()
            body = post["body"].strip()
            pinned = post.get("pinned", 0)

            cur = conn.execute(INSERT_SQL, (board, title, body, pinned, title, board))
            if cur.rowcount > 0:
                inserted += 1

        conn.commit()
        log.info("[%s] %d/%d posts inserted", board, inserted, len(posts))
        total_inserted += inserted

    conn.close()
    log.info("시드 완료: 총 %d posts 삽입", total_inserted)


if __name__ == "__main__":
    log.info("DB: %s", DB_PATH)
    seed(DB_PATH)
