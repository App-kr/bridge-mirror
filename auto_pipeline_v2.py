"""
auto_pipeline_v2.py — Bridge Base Multicore Batch Pipeline
===========================================================
Pipeline:  master.db  ──►  [PII Encrypt]  ──►  Supabase
           ────────────────────────────────────────────────
  Stage 1  EXTRACT   : SQLite → chunked generator (no full-RAM load)
  Stage 2  TRANSFORM : ProcessPoolExecutor — CPU-bound PII encryption
  Stage 3  LOAD      : ThreadPoolExecutor  — I/O-bound Supabase upsert

Auto-recovery : 3 retries + exponential back-off per chunk
No prompts    : all progress/errors go to logs/pipeline.log + stdout
"""

import os
import sys
import time
import json
import logging
import sqlite3
import multiprocessing
import concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

# ── Bootstrap ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
LOG_DIR  = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

import io as _io
sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("pipeline_v2")

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    log.warning("python-dotenv not installed — using system env vars only.")

try:
    from supabase import create_client
    _SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    _SUPABASE_SVC = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if _SUPABASE_URL and _SUPABASE_SVC:
        try:
            _sb = create_client(_SUPABASE_URL, _SUPABASE_SVC)
        except Exception as _e:
            log.warning(f"Supabase init failed ({_e}) -- LOAD stage disabled")
            _sb = None
    else:
        _sb = None
        log.warning("Supabase not configured — LOAD stage disabled (set SUPABASE_URL + SUPABASE_SERVICE_KEY in .env)")
except ImportError:
    log.warning("supabase SDK not installed — LOAD stage disabled.")
    _sb = None

# ── Configuration ──────────────────────────────────────────────────────────────
CHUNK_SIZE  = 100                                    # rows per processing batch
MAX_WORKERS = max(2, multiprocessing.cpu_count() - 1)  # leave 1 core for OS
MAX_RETRIES = 3
RETRY_BASE  = 2.0   # seconds; doubles on each retry

DB_PATH = BASE_DIR / "master.db"

# Fields that must be AES-256-GCM encrypted before upload
ENCRYPT_FIELDS: dict[str, set[str]] = {
    "candidates": {"passport_status", "criminal_record", "health_info", "criminal_record_check"},
    "clients":    {"business_registration"},
    "jobs":       set(),   # no PII fields in jobs
}

# ── Stage 1 — EXTRACT ──────────────────────────────────────────────────────────

def extract_table(table: str, chunk_size: int = CHUNK_SIZE) -> Generator[list[dict], None, None]:
    """
    Yield rows from master.db in fixed-size chunks.
    Generator pattern — never loads the full table into RAM.
    """
    if not DB_PATH.exists():
        log.warning(f"[EXTRACT] master.db not found at {DB_PATH}. Skipping '{table}'.")
        return

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        try:
            cur.execute(f"SELECT COUNT(*) FROM [{table}]")
            total = cur.fetchone()[0]
        except sqlite3.OperationalError as exc:
            log.error(f"[EXTRACT] Table '{table}' not accessible: {exc}")
            return

        log.info(f"[EXTRACT] '{table}' — {total:,} rows found, chunking by {chunk_size}")
        offset = 0
        while True:
            cur.execute(f"SELECT * FROM [{table}] LIMIT ? OFFSET ?", (chunk_size, offset))
            rows = [dict(r) for r in cur.fetchall()]
            if not rows:
                break
            yield rows
            offset += chunk_size


# ── Stage 2 — TRANSFORM (ProcessPoolExecutor) ──────────────────────────────────

def _encrypt_row_worker(args: tuple) -> tuple[dict, str | None]:
    """
    Top-level function required for ProcessPoolExecutor pickling on Windows.
    Encrypts designated PII fields in one row. Environment vars are inherited.
    """
    row, encrypt_fields = args
    try:
        from security_vault import encrypt_field, is_encrypted   # noqa: PLC0415
        out = dict(row)
        for field in encrypt_fields:
            val = out.get(field)
            if val and isinstance(val, str) and not is_encrypted(val):
                out[field] = encrypt_field(val)
        return out, None
    except Exception as exc:
        return row, str(exc)   # return original row + error — never drop data


def transform_chunk(rows: list[dict], encrypt_fields: set[str]) -> list[dict]:
    """
    Encrypt PII fields across all rows in parallel.
    Errors are logged per-row; original row is preserved to prevent data loss.
    """
    if not encrypt_fields:
        return rows   # fast path for tables with no PII fields

    args = [(row, encrypt_fields) for row in rows]
    results: list[dict] = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for transformed, err in pool.map(_encrypt_row_worker, args, chunksize=10):
            if err:
                log.warning(f"[TRANSFORM] Encryption error (row preserved): {err}")
            results.append(transformed)

    return results


# ── Stage 3 — LOAD (ThreadPoolExecutor) ────────────────────────────────────────

def _upsert_single_chunk(args: tuple) -> tuple[int, int]:
    """
    Upsert one chunk to Supabase with exponential-backoff retry.
    Returns (rows_ok, rows_failed).
    """
    table, rows = args
    if _sb is None:
        return 0, 0   # LOAD stage disabled — counted separately

    delay = RETRY_BASE
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = _sb.table(table).upsert(rows, on_conflict="id").execute()
            n_ok = len(res.data) if res.data else len(rows)
            return n_ok, 0
        except Exception as exc:
            if attempt == MAX_RETRIES:
                log.error(f"[LOAD] '{table}' chunk failed after {MAX_RETRIES} attempts: {exc}")
                return 0, len(rows)
            log.warning(f"[LOAD] '{table}' retry {attempt}/{MAX_RETRIES} in {delay:.0f}s — {exc}")
            time.sleep(delay)
            delay *= 2

    return 0, len(rows)   # unreachable but satisfies type checker


def load_chunks(table: str, chunks: list[list[dict]]) -> tuple[int, int]:
    """Upsert all chunks concurrently. Returns (total_ok, total_failed)."""
    args = [(table, chunk) for chunk in chunks]
    total_ok = total_err = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for ok, err in pool.map(_upsert_single_chunk, args):
            total_ok  += ok
            total_err += err

    return total_ok, total_err


# ── Diagnostics ────────────────────────────────────────────────────────────────

def run_diagnostics() -> None:
    """Detect cores and benchmark encryption throughput. No user input required."""
    cores = multiprocessing.cpu_count()
    log.info("=" * 62)
    log.info("  auto_pipeline_v2  --  MULTICORE DIAGNOSTICS")
    log.info("=" * 62)
    log.info(f"  Platform          : {sys.platform}")
    log.info(f"  Python            : {sys.version.split()[0]}")
    log.info(f"  CPU cores (total) : {cores}")
    log.info(f"  Worker processes  : {MAX_WORKERS}  (total - 1)")
    log.info(f"  Chunk size        : {CHUNK_SIZE} rows/batch")
    log.info(f"  Supabase ready    : {'YES' if _sb else 'NO — LOAD stage skipped'}")
    log.info(f"  DB path           : {DB_PATH}  ({'found' if DB_PATH.exists() else 'NOT FOUND'})")

    # Encryption benchmark
    try:
        from security_vault import encrypt_field   # noqa: PLC0415
        sample = ["BenchmarkPII_Value_Test_123"] * 500
        t0 = time.perf_counter()
        with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as pool:
            list(pool.map(encrypt_field, sample))
        elapsed = time.perf_counter() - t0
        rate = len(sample) / max(elapsed, 0.001)
        log.info(f"  Encrypt benchmark : {len(sample)} fields in {elapsed:.2f}s = {rate:,.0f} fields/sec")
        log.info(f"  Est. 20-min cap   : ~{rate * 1200:,.0f} field-encryptions")
    except Exception as exc:
        log.warning(f"  Encrypt benchmark : skipped ({exc})")

    log.info("=" * 62)


# ── Full Table Pipeline ────────────────────────────────────────────────────────

def run_table(table: str, encrypt_fields: set[str]) -> dict:
    """
    Execute Extract → Transform → Load for one table.
    Returns stats dict. Never raises — errors are logged and counted.
    """
    t_start = time.perf_counter()
    stats: dict = {
        "table":      table,
        "extracted":  0,
        "loaded_ok":  0,
        "errors":     0,
        "elapsed_s":  0.0,
    }

    log.info(f"\n[PIPELINE] ─── Starting: {table} ───")

    all_chunks: list[list[dict]] = []
    try:
        for chunk in extract_table(table):
            stats["extracted"] += len(chunk)
            chunk = transform_chunk(chunk, encrypt_fields)
            all_chunks.append(chunk)
    except Exception as exc:
        log.error(f"[PIPELINE] '{table}' extract/transform error: {exc}")
        stats["errors"] += 1

    if all_chunks:
        if _sb:
            ok, err = load_chunks(table, all_chunks)
            stats["loaded_ok"] = ok
            stats["errors"]   += err
        else:
            log.info(f"[PIPELINE] '{table}': {stats['extracted']} rows transformed — LOAD skipped (no Supabase)")
    else:
        log.info(f"[PIPELINE] '{table}': no rows to process.")

    stats["elapsed_s"] = round(time.perf_counter() - t_start, 1)
    rate_s = stats["extracted"] / max(stats["elapsed_s"], 0.1)
    log.info(
        f"[PIPELINE] '{table}' complete — "
        f"extracted={stats['extracted']:,}  loaded={stats['loaded_ok']:,}  "
        f"errors={stats['errors']}  time={stats['elapsed_s']}s  ({rate_s:.0f} rows/s)"
    )
    return stats


# ── Entry Point ────────────────────────────────────────────────────────────────

def main() -> None:
    t_global = time.perf_counter()
    run_diagnostics()

    pipelines = [
        ("candidates", ENCRYPT_FIELDS["candidates"]),
        ("clients",    ENCRYPT_FIELDS["clients"]),
        ("jobs",       ENCRYPT_FIELDS["jobs"]),
    ]

    all_stats: list[dict] = []
    for table, enc_fields in pipelines:
        stats = run_table(table, enc_fields)
        all_stats.append(stats)

    # ── Final Summary ──────────────────────────────────────────────────────────
    total_elapsed = time.perf_counter() - t_global
    total_rows    = sum(s["extracted"] for s in all_stats)
    total_errors  = sum(s["errors"]    for s in all_stats)

    log.info("\n" + "=" * 62)
    log.info("  PIPELINE SUMMARY")
    log.info("=" * 62)
    for s in all_stats:
        log.info(
            f"  {s['table']:15s}  extracted={s['extracted']:5,}  "
            f"loaded={str(s.get('loaded_ok', '—')):5}  "
            f"errors={s.get('errors', 0):3d}  "
            f"{s.get('elapsed_s', 0):.1f}s"
        )
    log.info(f"  {'─' * 54}")
    log.info(f"  TOTAL            {total_rows:6,} rows   {total_errors} errors   {total_elapsed:.1f}s")
    log.info("=" * 62)

    if total_errors > 0:
        log.warning(f"  {total_errors} errors recorded — check logs/pipeline.log for details.")
        sys.exit(1)
    else:
        log.info("  All stages completed with zero errors.")


if __name__ == "__main__":
    multiprocessing.freeze_support()   # Windows multiprocessing safety
    main()
