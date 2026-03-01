"""
community_posts 테이블 보드 카테고리 확장
==========================================
SQLite는 ALTER TABLE로 CHECK 제약조건 변경이 불가하므로
테이블을 재생성하여 6개 보드를 지원합니다.

보드 목록:
  visa        — 비자 정보
  support_kr  — 공지 및 서류 안내 (한국어)
  support_en  — Information & Documents (English)
  about       — BRIDGE 소개
  korea       — 한국 생활 정보
  tips        — 교사 팁

실행:
  python migrations/alter_community_boards.py
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger("migrate_boards")

DB_PATH = os.getenv("BRIDGE_DB_PATH", str(Path(__file__).resolve().parent.parent / "master.db"))

NEW_BOARDS = ('visa', 'support_kr', 'support', 'about', 'korea', 'tips', 'testimonials')
BOARD_CHECK = ", ".join(f"'{b}'" for b in NEW_BOARDS)

CREATE_NEW = f"""
CREATE TABLE community_posts_new (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    board       TEXT    NOT NULL DEFAULT 'support'
                        CHECK (board IN ({BOARD_CHECK})),
    title       TEXT    NOT NULL,
    body        TEXT    NOT NULL,
    author_hash TEXT,
    image_paths TEXT    DEFAULT '[]',
    pinned      INTEGER DEFAULT 0,
    views       INTEGER DEFAULT 0,
    created_at  TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at  TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    is_deleted  INTEGER DEFAULT 0
)
"""

# 보드명 매핑 (기존 → 신규)
BOARD_MAP = {
    'general': 'tips',
    'support_en': 'support',
}


def migrate(db_path: str) -> None:
    if not Path(db_path).exists():
        log.error("DB not found: %s", db_path)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = OFF")

    # 기존 테이블 존재 확인
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='community_posts'"
    ).fetchone()

    if not exists:
        log.info("community_posts 테이블 없음 — 새로 생성")
        conn.execute(CREATE_NEW.replace("community_posts_new", "community_posts"))
        conn.commit()
        conn.close()
        log.info("완료: community_posts 생성 (6개 보드)")
        return

    # 현재 보드 목록 확인
    rows = conn.execute(
        "SELECT DISTINCT board FROM community_posts WHERE is_deleted=0"
    ).fetchall()
    current_boards = {r[0] for r in rows}
    log.info("현재 보드: %s", current_boards)

    # 이미 새 보드가 포함되어 있으면 스킵
    if current_boards <= set(NEW_BOARDS):
        # CHECK 제약조건만 확인 — 이미 맞으면 스킵
        schema = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='community_posts'"
        ).fetchone()[0]
        if all(b in schema for b in NEW_BOARDS):
            log.info("이미 6개 보드 스키마 — 스킵")
            conn.close()
            return

    # 1) 새 테이블 생성
    conn.execute("DROP TABLE IF EXISTS community_posts_new")
    conn.execute(CREATE_NEW)

    # 2) 데이터 복사 (board 매핑 적용)
    case_parts = " ".join(
        f"WHEN '{old}' THEN '{new}'" for old, new in BOARD_MAP.items()
    )
    board_expr = f"CASE board {case_parts} ELSE board END" if case_parts else "board"

    conn.execute(f"""
        INSERT INTO community_posts_new
            (id, board, title, body, author_hash, image_paths,
             pinned, views, created_at, updated_at, is_deleted)
        SELECT id, {board_expr}, title, body, author_hash, image_paths,
               pinned, views, created_at, updated_at, is_deleted
        FROM community_posts
    """)

    count = conn.execute("SELECT COUNT(*) FROM community_posts_new").fetchone()[0]
    log.info("복사 완료: %d rows", count)

    # 3) 테이블 교체
    conn.execute("DROP TABLE community_posts")
    conn.execute("ALTER TABLE community_posts_new RENAME TO community_posts")
    conn.commit()

    # 4) 검증
    boards_after = conn.execute(
        "SELECT DISTINCT board FROM community_posts WHERE is_deleted=0"
    ).fetchall()
    log.info("마이그레이션 완료 — 보드: %s", [r[0] for r in boards_after])

    conn.close()


if __name__ == "__main__":
    log.info("DB: %s", DB_PATH)
    migrate(DB_PATH)
    log.info("Done.")
