"""
backend/migrate_bbs.py — Legacy BBS → master.db Migration
==========================================================

legacy_posts.csv → community_posts (master.db)

CSV columns recognised (any order, case-insensitive headers):
    id, title, content | body, author, created_at | date,
    is_deleted | deleted | status,   board (optional, default='general')

Features
--------
- Chunk-based insert (default 500 rows / batch) — zero memory growth
- PII detection (KR phone, intl phone, email, biz_reg) in body
  → AES-256-GCM encrypt entire body via security_vault.encrypt_field()
- Author field → SHA-256 hash (first 24 hex chars) → author_hash
- Soft delete enforcement: legacy-deleted rows → is_deleted=1, never physical DELETE
- Dedup on composite key (title, created_at) — INSERT WHERE NOT EXISTS
- Full audit log written to logs/migrate_bbs.log

Usage
-----
  python backend/migrate_bbs.py                          # default: ./legacy_posts.csv
  python backend/migrate_bbs.py --csv path/to/file.csv  # custom CSV
  python backend/migrate_bbs.py --dry-run               # parse only, no DB writes
  python backend/migrate_bbs.py --chunk-size 1000       # larger batches
  python backend/migrate_bbs.py --board visa            # force target board

Zero-Tolerance Rules
--------------------
  ✅  Zero physical DELETE — is_deleted = 1 for soft-deleted records
  ✅  AES-256-GCM encryption for any body containing PII
  ✅  Author PII never stored — SHA-256 hash only
"""

import sys
import re
import csv
import hashlib
import logging
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Iterator

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent   # Q:/Claudework/bridge base/
DB_PATH    = BASE_DIR / "master.db"
LOG_DIR    = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# security_vault.py lives in BASE_DIR (project root)
sys.path.insert(0, str(BASE_DIR))
try:
    from security_vault import encrypt_field, is_encrypted  # noqa: E402
except ImportError as exc:
    sys.exit(f"[FATAL] Cannot import security_vault from {BASE_DIR}: {exc}")

# ── Logging ───────────────────────────────────────────────────────────────────
_fmt = "%(asctime)s  %(levelname)-8s  %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=_fmt,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "migrate_bbs.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("migrate_bbs")

# ── Constants ─────────────────────────────────────────────────────────────────
CHUNK_SIZE   = 500
VALID_BOARDS = {"general", "visa"}

# ── PII Pattern Registry ──────────────────────────────────────────────────────
_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'010[-\s]?\d{3,4}[-\s]?\d{4}'),                            "KR_phone"),
    (re.compile(r'\+\d{1,3}[\s\-]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{4}'),    "intl_phone"),
    (re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'),      "email"),
    (re.compile(r'\b\d{3}-\d{2}-\d{5}\b'),                                  "biz_reg"),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_pii(text: str) -> list[str]:
    """Return list of PII type labels found in text."""
    return [label for pat, label in _PII_PATTERNS if pat.search(text)]


def _hash_author(raw: str) -> str:
    """SHA-256 hash of author string → first 24 hex chars (no raw PII stored)."""
    s = (raw or "").strip()
    if not s:
        return ""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:24]


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_TS_FORMATS = (
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
)

def _normalise_ts(raw: str) -> str:
    """Normalise various timestamp strings to ISO-8601 UTC. Falls back to now()."""
    s = (raw or "").strip()
    if not s:
        return _iso_now()
    for fmt in _TS_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    log.warning("Unrecognised timestamp %r → using now()", s[:30])
    return _iso_now()


# ── CSV helpers ───────────────────────────────────────────────────────────────

def _norm_header(h: str) -> str:
    """Lowercase + strip header for case-insensitive matching."""
    return h.strip().lower().lstrip("\ufeff")  # strip BOM if present


def csv_chunks(csv_path: Path, chunk_size: int) -> Iterator[list[dict]]:
    """
    Yield successive row-chunk lists from a CSV file.
    Headers are normalised (lowercase, stripped) for flexible matching.
    Memory is bounded to chunk_size rows at any time.
    """
    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        # normalise headers in-place
        reader.fieldnames = [_norm_header(h) for h in (reader.fieldnames or [])]
        chunk: list[dict] = []
        for row in reader:
            # re-key with normalised headers
            norm_row = {_norm_header(k): v for k, v in row.items()}
            chunk.append(norm_row)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk


# ── Row processor ─────────────────────────────────────────────────────────────

def process_row(row: dict, forced_board: str | None) -> dict | None:
    """
    Map one CSV row → community_posts insert dict.
    Returns None if the row is invalid (empty title → skip).

    Security:
      - body PII detected → AES-256-GCM encrypt entire body field
      - author → SHA-256 hash (raw author never stored)
    """
    # ── title (required) ──────────────────────────────────────────────────────
    title = (row.get("title") or "").strip()
    if not title:
        return None

    # ── body / content ────────────────────────────────────────────────────────
    body_raw = (row.get("content") or row.get("body") or "").strip()

    # PII guard: detect → AES-256-GCM encrypt whole field
    pii_hits = _detect_pii(body_raw) if body_raw else []
    if pii_hits and not is_encrypted(body_raw):
        body = encrypt_field(body_raw)
        log.info("  [PII→ENC] title=%.40r  pii=%s", title, pii_hits)
    else:
        body = body_raw

    # ── author → hash (Zero-PII storage) ─────────────────────────────────────
    author_hash = _hash_author(row.get("author") or row.get("author_name") or "")

    # ── board ─────────────────────────────────────────────────────────────────
    if forced_board:
        board = forced_board
    else:
        board = (row.get("board") or "general").strip().lower()
        if board not in VALID_BOARDS:
            board = "general"

    # ── timestamps ────────────────────────────────────────────────────────────
    created_at = _normalise_ts(row.get("created_at") or row.get("date") or "")
    updated_at = _iso_now()

    # ── is_deleted: soft-delete enforcement — 물리 DELETE 절대 금지 ──────────
    deleted_raw = (
        row.get("is_deleted") or row.get("deleted") or row.get("status") or "0"
    ).strip().lower()
    is_deleted = 1 if deleted_raw in ("1", "true", "yes", "deleted", "삭제", "d") else 0

    return {
        "board":       board,
        "title":       title,
        "body":        body,
        "author_hash": author_hash,
        "created_at":  created_at,
        "updated_at":  updated_at,
        "is_deleted":  is_deleted,
    }


# ── DB helpers ────────────────────────────────────────────────────────────────

def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create community_posts if not present. Never alters existing schema."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS community_posts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            board       TEXT    NOT NULL DEFAULT 'general'
                                CHECK (board IN ('general','visa')),
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
    """)
    conn.commit()
    log.info("Schema verified — community_posts OK")


_INSERT_SQL = """
    INSERT INTO community_posts
        (board, title, body, author_hash, image_paths,
         pinned, views, created_at, updated_at, is_deleted)
    SELECT ?, ?, ?, ?, '[]', 0, 0, ?, ?, ?
    WHERE NOT EXISTS (
        SELECT 1 FROM community_posts
        WHERE title = ? AND created_at = ?
    )
"""


def insert_chunk(
    conn: sqlite3.Connection,
    records: list[dict],
) -> tuple[int, int, int]:
    """
    Insert one batch of pre-processed records.
    Dedup: INSERT WHERE NOT EXISTS (title, created_at composite key).
    Returns (inserted, skipped, errors).
    """
    inserted = skipped = errors = 0
    for rec in records:
        try:
            cur = conn.execute(
                _INSERT_SQL,
                (
                    rec["board"],
                    rec["title"],
                    rec["body"],
                    rec["author_hash"],
                    rec["created_at"],
                    rec["updated_at"],
                    rec["is_deleted"],
                    # WHERE NOT EXISTS params
                    rec["title"],
                    rec["created_at"],
                ),
            )
            if cur.rowcount == 1:
                inserted += 1
            else:
                skipped += 1
        except sqlite3.Error as exc:
            log.error("  [DB ERR] title=%.40r → %s", rec.get("title", ""), exc)
            errors += 1
    conn.commit()
    return inserted, skipped, errors


# ── Main migration ────────────────────────────────────────────────────────────

def migrate(
    csv_path: Path,
    db_path: Path,
    chunk_size: int,
    dry_run: bool,
    forced_board: str | None,
) -> None:
    log.info("=" * 62)
    log.info("migrate_bbs  START  %s", _iso_now())
    log.info("  CSV        : %s", csv_path)
    log.info("  DB         : %s", db_path)
    log.info("  chunk_size : %d", chunk_size)
    log.info("  board      : %s", forced_board or "(from CSV / default=general)")
    log.info("  mode       : %s", "DRY-RUN (no writes)" if dry_run else "LIVE")
    log.info("=" * 62)

    if not csv_path.exists():
        raise SystemExit(f"[FATAL] CSV not found: {csv_path}")

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")

    if not dry_run:
        ensure_schema(conn)

    total_read = total_processed = total_inserted = total_skipped = total_errors = 0

    for chunk_idx, raw_chunk in enumerate(csv_chunks(csv_path, chunk_size), start=1):
        total_read += len(raw_chunk)

        # Map CSV rows → insert records (invalid rows silently skipped)
        records: list[dict] = []
        for raw_row in raw_chunk:
            rec = process_row(raw_row, forced_board)
            if rec is None:
                total_skipped += 1  # empty title → skip
            else:
                records.append(rec)
        total_processed += len(records)

        if dry_run:
            # Print sample rows, count only
            for rec in records[:5]:
                log.info(
                    "  [DRY] board=%-8s  del=%d  pii_enc=%s  title=%.50r",
                    rec["board"],
                    rec["is_deleted"],
                    is_encrypted(rec["body"]),
                    rec["title"],
                )
            if len(records) > 5:
                log.info("  [DRY]   … %d more rows in chunk %d", len(records) - 5, chunk_idx)
            total_inserted += len(records)  # dry-run: count as "would insert"
        else:
            ins, skp, err = insert_chunk(conn, records)
            total_inserted += ins
            total_skipped  += skp
            total_errors   += err
            log.info(
                "  Chunk %4d  read=%-5d  processed=%-5d  "
                "inserted=%-5d  skipped(dup)=%-5d  errors=%d",
                chunk_idx, len(raw_chunk), len(records), ins, skp, err,
            )

    conn.close()

    log.info("=" * 62)
    log.info("SUMMARY")
    log.info("  total_read      : %d", total_read)
    log.info("  total_processed : %d", total_processed)
    log.info("  inserted        : %d%s", total_inserted, "  (dry-run estimate)" if dry_run else "")
    log.info("  skipped (dup)   : %d", total_skipped)
    log.info("  errors          : %d", total_errors)
    log.info("")
    log.info("  ✅  Zero physical DELETE enforced (is_deleted flag only)")
    log.info("  ✅  PII-containing bodies AES-256-GCM encrypted")
    log.info("  ✅  Author PII hashed — raw value never stored")
    log.info("=" * 62)

    if total_errors:
        log.warning("Migration completed WITH %d errors. Check logs/migrate_bbs.log", total_errors)
        sys.exit(1)
    log.info("Migration completed successfully.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate legacy BBS CSV → master.db community_posts"
    )
    parser.add_argument(
        "--csv",
        default="legacy_posts.csv",
        metavar="PATH",
        help="Input CSV file (default: ./legacy_posts.csv)",
    )
    parser.add_argument(
        "--db",
        default=str(DB_PATH),
        metavar="PATH",
        help=f"master.db path (default: {DB_PATH})",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=CHUNK_SIZE,
        metavar="N",
        help=f"Rows per DB transaction batch (default: {CHUNK_SIZE})",
    )
    parser.add_argument(
        "--board",
        choices=list(VALID_BOARDS),
        default=None,
        metavar="BOARD",
        help="Force all rows into this board (general|visa). "
             "If omitted, reads 'board' column from CSV or defaults to 'general'.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and log without writing to DB",
    )
    args = parser.parse_args()

    migrate(
        csv_path=Path(args.csv).resolve(),
        db_path=Path(args.db).resolve(),
        chunk_size=args.chunk_size,
        dry_run=args.dry_run,
        forced_board=args.board,
    )


if __name__ == "__main__":
    main()
