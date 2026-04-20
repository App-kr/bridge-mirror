"""
Resume Pipeline v2.0 — Durable Queue + Worker + Event Log
======================================================

100% 성공 보장 아키텍처:
  - 영속 큐(SQLite) → 서버 재시작 생존
  - 멱등 enqueue → 중복 호출 무해 (idempotency_key UNIQUE)
  - Exponential retry (2^attempts 분, max 10회) → DLQ 진입
  - Verify-after-write (S3 HEAD + SHA-256 재검증)
  - pipeline_events 감사 로그 (append-only)

공개 API:
  enqueue_resume_process(candidate_id, cv_s3_key, trigger) -> job_id
  log_event(event_type, candidate_id, details, severity) -> None
  get_next_job(job_type) -> job or None
  mark_job_running(job_id) -> bool
  mark_job_done(job_id) -> None
  mark_job_failed(job_id, error) -> None (자동 DLQ 승격)
"""
from __future__ import annotations
import hashlib
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

_log = logging.getLogger("bridge.pipeline")


# ── DB 경로 ──────────────────────────────────────────────────────────────
def _db_path() -> str:
    p = os.getenv("BRIDGE_DB_PATH") or os.getenv("DB_PATH") or "master.db"
    return p


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_db_path())
    c.execute("PRAGMA busy_timeout = 5000")
    c.row_factory = sqlite3.Row
    return c


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ── Idempotency key ─────────────────────────────────────────────────────
def _make_idempotency_key(job_type: str, payload: dict) -> str:
    """같은 작업 중복 호출을 감지하기 위한 결정적 해시."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{job_type}|{canonical}".encode()).hexdigest()


# ── 이벤트 로그 (append-only) ────────────────────────────────────────────
def log_event(
    event_type: str,
    candidate_id: Optional[str] = None,
    job_id: Optional[int] = None,
    details: Optional[dict] = None,
    severity: str = "info",
) -> None:
    """pipeline_events 에 1줄 추가. 예외는 silent (로그 실패가 파이프라인 중단시키지 않음)."""
    try:
        conn = _conn()
        try:
            conn.execute(
                """INSERT INTO pipeline_events
                   (event_type, candidate_id, job_id, details_json, severity)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    event_type,
                    candidate_id,
                    job_id,
                    json.dumps(details or {}, ensure_ascii=False, default=str)[:2000],
                    severity,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        _log.warning("log_event fail type=%s err=%s", event_type, e)


# ── 큐 등록 (멱등) ───────────────────────────────────────────────────────
def enqueue_resume_process(
    candidate_id: str,
    cv_s3_key: str,
    trigger: str = "unknown",
    max_attempts: int = 10,
) -> int:
    """
    이력서 처리 작업 큐 등록. 멱등성 보장: 동일 (candidate_id, cv_s3_key) 중복 호출 시 기존 job_id 반환.
    trigger 는 메타데이터(payload)에 포함하되 idempotency_key 계산에서는 제외.
    """
    payload = {
        "candidate_id": str(candidate_id),
        "cv_s3_key": str(cv_s3_key),
        "trigger": str(trigger),
    }
    # idempotency 는 후보자 + 파일 key 만 고려 — trigger 변경으로 중복 허용되지 않음
    idempotency_key = _make_idempotency_key(
        "resume_process",
        {"candidate_id": str(candidate_id), "cv_s3_key": str(cv_s3_key)},
    )

    conn = _conn()
    try:
        # 기존 확인
        existing = conn.execute(
            "SELECT id, status FROM job_queue WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing:
            existing_id = existing["id"]
            # DLQ/failed 상태면 재큐잉 허용
            if existing["status"] in ("dlq", "failed"):
                conn.execute(
                    "UPDATE job_queue SET status='queued', attempts=0, next_run_at=NULL, "
                    "last_error=NULL, updated_at=? WHERE id=?",
                    (_now(), existing_id),
                )
                conn.commit()
                log_event(
                    "job_requeued",
                    candidate_id=candidate_id,
                    job_id=existing_id,
                    details={"trigger": trigger, "reason": "retry_from_failed"},
                )
            return existing_id

        cur = conn.execute(
            """INSERT INTO job_queue
               (job_type, payload_json, idempotency_key, status, max_attempts, next_run_at)
               VALUES ('resume_process', ?, ?, 'queued', ?, datetime('now'))""",
            (
                json.dumps(payload, ensure_ascii=False),
                idempotency_key,
                max_attempts,
            ),
        )
        conn.commit()
        job_id = cur.lastrowid or 0
    finally:
        conn.close()

    log_event(
        "job_enqueued",
        candidate_id=candidate_id,
        job_id=job_id,
        details={"trigger": trigger, "cv_s3_key": cv_s3_key},
    )
    return job_id


# ── v2.0 확장: 전 파일타입 큐 등록 ───────────────────────────────────────
_FILE_CATEGORY_TO_JOB_TYPE = {
    "document": "resume_process",
    "image":    "image_process",
    "video":    "video_process",
    "other":    "attachment_store",
}


def enqueue_file_process(
    candidate_id: str,
    s3_key: str,
    file_type: str = "",             # 'cv'/'cover_letter'/'photo'/'video'/...
    filename: str = "",
    trigger: str = "unknown",
    max_attempts: int = 10,
) -> int:
    """
    v2.0 Universal file enqueue — CV/DOCX/이미지/영상/기타 모두 처리.
    파일 확장자 또는 file_type 으로 job_type 자동 결정.
    """
    # 카테고리 결정: 확장자 우선 → file_type 폴백
    ext = ""
    if filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if not ext and s3_key:
        ext = "." + s3_key.rsplit(".", 1)[-1].lower() if "." in s3_key else ""

    # 확장자 → category
    doc_exts = {".pdf", ".docx", ".doc", ".rtf", ".odt", ".hwp"}
    img_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}
    vid_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv"}

    if ext in doc_exts:
        category = "document"
    elif ext in img_exts:
        category = "image"
    elif ext in vid_exts:
        category = "video"
    elif file_type in ("cv", "cover_letter", "certificate", "reference"):
        category = "document"
    elif file_type in ("photo", "community_image"):
        category = "image"
    elif file_type == "video":
        category = "video"
    else:
        category = "other"

    job_type = _FILE_CATEGORY_TO_JOB_TYPE.get(category, "attachment_store")

    payload = {
        "candidate_id": str(candidate_id),
        "s3_key": str(s3_key),
        "file_type": str(file_type),
        "filename": str(filename),
        "category": category,
        "trigger": str(trigger),
    }
    # 멱등 key: job_type + candidate_id + s3_key (trigger 제외)
    idempotency_key = _make_idempotency_key(
        job_type,
        {"candidate_id": str(candidate_id), "s3_key": str(s3_key)},
    )

    conn = _conn()
    try:
        existing = conn.execute(
            "SELECT id, status FROM job_queue WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if existing:
            existing_id = existing["id"]
            if existing["status"] in ("dlq", "failed"):
                conn.execute(
                    "UPDATE job_queue SET status='queued', attempts=0, next_run_at=NULL, "
                    "last_error=NULL, updated_at=? WHERE id=?",
                    (_now(), existing_id),
                )
                conn.commit()
                log_event(
                    "job_requeued",
                    candidate_id=candidate_id,
                    job_id=existing_id,
                    details={"trigger": trigger, "category": category},
                )
            return existing_id

        cur = conn.execute(
            """INSERT INTO job_queue
               (job_type, payload_json, idempotency_key, status, max_attempts, next_run_at)
               VALUES (?, ?, ?, 'queued', ?, datetime('now'))""",
            (
                job_type,
                json.dumps(payload, ensure_ascii=False),
                idempotency_key,
                max_attempts,
            ),
        )
        conn.commit()
        job_id = cur.lastrowid or 0
    finally:
        conn.close()

    log_event(
        "job_enqueued",
        candidate_id=candidate_id,
        job_id=job_id,
        details={"trigger": trigger, "job_type": job_type, "category": category,
                 "s3_key": s3_key[:80], "file_type": file_type},
    )
    return job_id


# ── 워커용 큐 조회 ───────────────────────────────────────────────────────
def get_next_job(job_type: str = "resume_process") -> Optional[sqlite3.Row]:
    """실행 대기 작업 1건 반환 (next_run_at <= 현재)."""
    conn = _conn()
    try:
        row = conn.execute(
            """SELECT * FROM job_queue
               WHERE job_type = ? AND status = 'queued'
                 AND (next_run_at IS NULL OR next_run_at <= datetime('now'))
               ORDER BY id LIMIT 1""",
            (job_type,),
        ).fetchone()
        return row
    finally:
        conn.close()


def get_next_job_any(job_types: list = None) -> Optional[sqlite3.Row]:
    """여러 job_type 중 가장 오래된 queued 작업 1건.
    job_types=None 이면 전 타입. 빈 리스트는 빈 결과."""
    conn = _conn()
    try:
        if job_types is None:
            row = conn.execute(
                """SELECT * FROM job_queue
                   WHERE status = 'queued'
                     AND (next_run_at IS NULL OR next_run_at <= datetime('now'))
                   ORDER BY id LIMIT 1"""
            ).fetchone()
        elif job_types:
            placeholders = ",".join("?" * len(job_types))
            row = conn.execute(
                f"""SELECT * FROM job_queue
                    WHERE job_type IN ({placeholders}) AND status = 'queued'
                      AND (next_run_at IS NULL OR next_run_at <= datetime('now'))
                    ORDER BY id LIMIT 1""",
                job_types,
            ).fetchone()
        else:
            return None
        return row
    finally:
        conn.close()


def mark_job_running(job_id: int) -> bool:
    """queued → running 원자적 전이. 이미 다른 워커가 잡았으면 False."""
    conn = _conn()
    try:
        cur = conn.execute(
            """UPDATE job_queue
               SET status='running', started_at=?, updated_at=?,
                   attempts = attempts + 1
               WHERE id = ? AND status = 'queued'""",
            (_now(), _now(), job_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def mark_job_done(job_id: int, candidate_id: Optional[str] = None) -> None:
    conn = _conn()
    try:
        conn.execute(
            "UPDATE job_queue SET status='done', finished_at=?, updated_at=?, last_error=NULL WHERE id=?",
            (_now(), _now(), job_id),
        )
        conn.commit()
    finally:
        conn.close()
    log_event("job_done", candidate_id=candidate_id, job_id=job_id)


def mark_job_failed(
    job_id: int,
    error: str,
    candidate_id: Optional[str] = None,
) -> str:
    """
    실패 처리 — attempts/max_attempts 비교하여:
      - 재시도 가능 → status='queued', next_run_at = now + 2^attempts 분
      - 최대 도달  → status='dlq' (Dead Letter Queue)
    Returns: 'queued' or 'dlq'
    """
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT attempts, max_attempts FROM job_queue WHERE id=?",
            (job_id,),
        ).fetchone()
        if not row:
            return "unknown"
        attempts = int(row["attempts"])
        max_attempts = int(row["max_attempts"])

        if attempts >= max_attempts:
            conn.execute(
                "UPDATE job_queue SET status='dlq', last_error=?, finished_at=?, updated_at=? WHERE id=?",
                (str(error)[:500], _now(), _now(), job_id),
            )
            conn.commit()
            log_event(
                "job_dlq",
                candidate_id=candidate_id,
                job_id=job_id,
                details={"error": str(error)[:300], "attempts": attempts},
                severity="critical",
            )
            return "dlq"

        # Exponential backoff: 2^attempts 분 (1,2,4,8,16,32... 분)
        backoff_min = min(2 ** attempts, 60)
        next_at = (datetime.now(tz=timezone.utc) + timedelta(minutes=backoff_min)).isoformat()
        conn.execute(
            """UPDATE job_queue
               SET status='queued', last_error=?, next_run_at=?, updated_at=?
               WHERE id=?""",
            (str(error)[:500], next_at, _now(), job_id),
        )
        conn.commit()
        log_event(
            "job_retry",
            candidate_id=candidate_id,
            job_id=job_id,
            details={"error": str(error)[:300], "attempts": attempts, "next_run_at": next_at},
            severity="warn",
        )
        return "queued"
    finally:
        conn.close()


# ── 후보자 상태 업데이트 (candidates.cv_processed_*) ────────────────────
def update_candidate_status(
    candidate_id: str,
    status: str,
    s3_key: Optional[str] = None,
    sha256: Optional[str] = None,
    last_error: Optional[str] = None,
) -> None:
    """candidates.cv_processed_* 컬럼 갱신."""
    conn = _conn()
    try:
        sets = ["cv_processed_status = ?", "cv_processed_attempts = cv_processed_attempts + 1"]
        params = [status]
        if s3_key is not None:
            sets.append("cv_processed_s3_key = ?")
            params.append(s3_key)
        if sha256 is not None:
            sets.append("cv_processed_sha256 = ?")
            params.append(sha256)
        if status == "done":
            sets.append("cv_processed_at = ?")
            params.append(_now())
            sets.append("cv_processed_last_error = NULL")
        elif last_error is not None:
            sets.append("cv_processed_last_error = ?")
            params.append(str(last_error)[:300])
        params.append(str(candidate_id))

        conn.execute(
            f"UPDATE candidates SET {', '.join(sets)} WHERE candidate_id = ?",
            params,
        )
        conn.commit()
    finally:
        conn.close()


# ── DLQ 조회 (관리자 UI용) ────────────────────────────────────────────────
def list_dlq_jobs(limit: int = 50) -> list:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM job_queue WHERE status='dlq' ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def requeue_dlq_job(job_id: int) -> bool:
    """DLQ 작업 수동 재큐잉."""
    conn = _conn()
    try:
        cur = conn.execute(
            """UPDATE job_queue
               SET status='queued', attempts=0, last_error=NULL, next_run_at=NULL, updated_at=?
               WHERE id=? AND status='dlq'""",
            (_now(), job_id),
        )
        conn.commit()
        ok = cur.rowcount > 0
    finally:
        conn.close()
    if ok:
        log_event("job_dlq_requeued", job_id=job_id, severity="info")
    return ok


def get_queue_stats() -> dict:
    """큐 현황 (대시보드용)."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT job_type, status, COUNT(*) as c FROM job_queue GROUP BY job_type, status"
        ).fetchall()
        stats: dict = {}
        for r in rows:
            stats.setdefault(r["job_type"], {})[r["status"]] = r["c"]
        return stats
    finally:
        conn.close()
