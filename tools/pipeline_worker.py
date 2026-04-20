"""
Resume Pipeline Worker (v2.0)
===============================

백그라운드 worker 스레드 — job_queue 에서 작업 꺼내서 실제 처리.

실행 방법:
  1) api_server.py startup hook에서 자동 시작 (기본 3 worker)
  2) 로컬 PC에서 독립 실행: python tools/pipeline_worker.py

보호:
  - 각 작업 120초 타임아웃 (스레드 내부에서)
  - 예외 반드시 mark_job_failed 로 기록
  - 중복 실행 방지: mark_job_running atomic UPDATE
"""
from __future__ import annotations
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional

_log = logging.getLogger("bridge.pipeline.worker")

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

_STOP = threading.Event()
_WORKER_THREADS: list[threading.Thread] = []

POLL_INTERVAL = 5  # 빈 큐일 때 대기 (초)
JOB_TIMEOUT = 120  # 개별 작업 타임아웃 (초)


def _process_resume_job(job: dict) -> tuple[bool, str]:
    """resume_process 작업 — CV/DOCX PDF 변환 + PII 제거."""
    payload = json.loads(job["payload_json"])
    candidate_id = payload.get("candidate_id", "")
    cv_s3_key = payload.get("cv_s3_key") or payload.get("s3_key", "")
    try:
        import api_server
        api_server._auto_process_resume(candidate_id, cv_s3_key)
        return True, ""
    except Exception as e:
        return False, str(e)[:500]


def _process_image_job(job: dict) -> tuple[bool, str]:
    """image_process 작업 — SHA-256 해시 + photo_s3_key 갱신.
    사진은 PII 불필요. 무결성 해시만 기록.
    """
    import hashlib
    import sqlite3 as _sql

    payload = json.loads(job["payload_json"])
    candidate_id = payload.get("candidate_id", "")
    s3_key = payload.get("s3_key", "")

    try:
        import api_server
        # S3 다운로드
        data = api_server.s3_download_bytes(s3_key)
        if not data:
            return False, f"S3 다운로드 실패: {s3_key}"
        sha = hashlib.sha256(data).hexdigest()

        # candidates.photo_s3_key / photo_sha256 갱신
        conn = _sql.connect(str(api_server._ADMIN_DB_PATH))
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            conn.execute(
                "UPDATE candidates SET photo_s3_key = ?, photo_sha256 = ? WHERE candidate_id = ?",
                (s3_key, sha, candidate_id),
            )
            conn.commit()
        finally:
            conn.close()

        from pipeline_v2 import log_event
        log_event("image_processed", candidate_id=candidate_id,
                  job_id=job["id"], details={"sha256": sha[:16], "size": len(data)})
        return True, ""
    except Exception as e:
        return False, str(e)[:500]


def _process_video_job(job: dict) -> tuple[bool, str]:
    """video_process 작업 — SHA-256 해시만. 영상 PII 제거는 미구현."""
    import hashlib
    payload = json.loads(job["payload_json"])
    candidate_id = payload.get("candidate_id", "")
    s3_key = payload.get("s3_key", "")
    try:
        import api_server
        data = api_server.s3_download_bytes(s3_key)
        if not data:
            return False, f"S3 다운로드 실패: {s3_key}"
        sha = hashlib.sha256(data).hexdigest()
        from pipeline_v2 import log_event
        log_event("video_processed", candidate_id=candidate_id,
                  job_id=job["id"], details={"sha256": sha[:16], "size": len(data)})
        return True, ""
    except Exception as e:
        return False, str(e)[:500]


def _process_attachment_job(job: dict) -> tuple[bool, str]:
    """attachment_store 작업 — 해시만 기록 (reference, certificate, 기타)."""
    import hashlib
    payload = json.loads(job["payload_json"])
    candidate_id = payload.get("candidate_id", "")
    s3_key = payload.get("s3_key", "")
    file_type = payload.get("file_type", "attachment")
    try:
        import api_server
        data = api_server.s3_download_bytes(s3_key)
        if not data:
            return False, f"S3 다운로드 실패: {s3_key}"
        sha = hashlib.sha256(data).hexdigest()
        from pipeline_v2 import log_event
        log_event("attachment_stored", candidate_id=candidate_id,
                  job_id=job["id"],
                  details={"sha256": sha[:16], "size": len(data), "file_type": file_type})
        return True, ""
    except Exception as e:
        return False, str(e)[:500]


# Job type dispatcher
_JOB_HANDLERS = {
    "resume_process":   _process_resume_job,
    "image_process":    _process_image_job,
    "video_process":    _process_video_job,
    "attachment_store": _process_attachment_job,
}

# 워커가 처리할 job_type 목록 (전체)
_ALL_JOB_TYPES = list(_JOB_HANDLERS.keys())


def _run_one_job() -> bool:
    """큐에서 1건 가져와 실행. 작업이 있으면 True, 없으면 False.
    모든 job_type 중에서 가장 오래된 queued 작업 처리.
    """
    from pipeline_v2 import (
        get_next_job_any, mark_job_running, mark_job_done, mark_job_failed,
    )

    job = get_next_job_any(_ALL_JOB_TYPES)
    if not job:
        return False

    job_id = job["id"]
    job_type = job["job_type"]
    if not mark_job_running(job_id):
        return True

    payload = json.loads(job["payload_json"])
    candidate_id = payload.get("candidate_id", "")

    _log.info("[WORKER] start job_id=%s type=%s cid=%s", job_id, job_type, candidate_id)

    handler = _JOB_HANDLERS.get(job_type)
    if not handler:
        mark_job_failed(job_id, f"unknown job_type: {job_type}", candidate_id=candidate_id)
        return True

    result = {"ok": False, "err": "timeout"}

    def _target():
        ok, err = handler(dict(job))
        result["ok"] = ok
        result["err"] = err

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(JOB_TIMEOUT)

    if t.is_alive():
        mark_job_failed(job_id, f"timeout after {JOB_TIMEOUT}s", candidate_id=candidate_id)
        _log.warning("[WORKER] timeout job_id=%s type=%s", job_id, job_type)
        return True

    if result["ok"]:
        mark_job_done(job_id, candidate_id=candidate_id)
        _log.info("[WORKER] done job_id=%s type=%s cid=%s", job_id, job_type, candidate_id)
    else:
        outcome = mark_job_failed(job_id, result["err"], candidate_id=candidate_id)
        _log.warning("[WORKER] fail job_id=%s type=%s → %s err=%s",
                     job_id, job_type, outcome, result["err"][:100])
    return True


def _worker_loop(worker_id: int) -> None:
    _log.info("[WORKER %d] started", worker_id)
    while not _STOP.is_set():
        try:
            had_work = _run_one_job()
            if not had_work:
                _STOP.wait(POLL_INTERVAL)
        except Exception as e:
            _log.error("[WORKER %d] loop error: %s", worker_id, e, exc_info=True)
            _STOP.wait(POLL_INTERVAL)
    _log.info("[WORKER %d] stopped", worker_id)


def start_workers(n: int = 3) -> None:
    """api_server.py startup hook 에서 호출."""
    global _WORKER_THREADS
    if _WORKER_THREADS:
        _log.warning("start_workers: already started")
        return
    for i in range(n):
        t = threading.Thread(target=_worker_loop, args=(i,), daemon=True, name=f"pipeline-worker-{i}")
        t.start()
        _WORKER_THREADS.append(t)
    _log.info("start_workers: %d threads launched", n)


def stop_workers() -> None:
    _STOP.set()
    _log.info("stop_workers: stop signal sent")


# ── CLI: python tools/pipeline_worker.py ────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    n = int(os.getenv("WORKER_COUNT", "3"))
    start_workers(n)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        stop_workers()
        for t in _WORKER_THREADS:
            t.join(timeout=2)
        print("Worker 종료")
