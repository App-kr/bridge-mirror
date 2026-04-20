"""
Pipeline Failure Watcher (v2.1)
================================

로컬 PC 전용 데몬 — Render 파이프라인에서 DLQ 진입한 작업을 감지하여:
  1) S3 원본 파일을 Q:\Claudework\bridge base\failed_files\ 로 다운로드
  2) 실패 메타 JSON 생성 (candidate_id, error, 수동처리 지침)
  3) Windows 탐색기로 해당 폴더 자동 열기 (최초 1회)
  4) 텔레그램 알림 (옵션, Render 측에서도 이미 발송됨)

실행:
  python tools/pipeline_failure_watcher.py              # 1회 스캔
  python tools/pipeline_failure_watcher.py --daemon     # 60초 주기 상시 감시
  python tools/pipeline_failure_watcher.py --once       # 현재 DLQ 1회 처리 후 종료

저장 위치:
  Q:\Claudework\bridge base\failed_files\
    FAIL_{job_id}_{YYYYMMDD_HHMMSS}/
      metadata.json           ← 실패 상세
      {original_filename}      ← S3 원본 다운로드 (가능 시)
      ERROR.txt                ← 에러 메시지 요약
"""
from __future__ import annotations
import argparse
import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from bx import _read  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
_log = logging.getLogger("bridge.failure_watcher")

RENDER_URL = os.getenv("RENDER_API_URL", "https://bridge-n7hk.onrender.com")
FAILED_DIR = BASE / "failed_files"
PROCESSED_MARK = FAILED_DIR / ".processed_job_ids.txt"  # 중복 처리 방지


def _admin_get(path: str) -> dict:
    admin_key = _read("ADMIN_API_KEY")
    req = urllib.request.Request(
        f"{RENDER_URL}{path}",
        headers={"x-admin-key": admin_key},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _fetch_dlq_jobs() -> list[dict]:
    try:
        d = _admin_get("/api/admin/pipeline/dlq?limit=50")
        return d.get("data", {}).get("dlq_jobs", []) or []
    except Exception as e:
        _log.warning("fetch DLQ fail: %s", e)
        return []


def _fetch_presigned_url(s3_key: str) -> Optional[str]:
    """/api/admin/storage/sign 로 presigned URL 받기 (있으면)."""
    if not s3_key:
        return None
    try:
        admin_key = _read("ADMIN_API_KEY")
        import urllib.parse
        req = urllib.request.Request(
            f"{RENDER_URL}/api/admin/storage/sign?path={urllib.parse.quote(s3_key)}",
            headers={"x-admin-key": admin_key},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode())
            return d.get("data", {}).get("signed_url") or d.get("signed_url")
    except Exception as e:
        _log.debug("presign fail for %s: %s", s3_key[:60], e)
        return None


def _download_file(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
        return True
    except Exception as e:
        _log.warning("download fail %s: %s", url[:60], e)
        return False


def _load_processed_ids() -> set:
    if not PROCESSED_MARK.exists():
        return set()
    try:
        return {line.strip() for line in PROCESSED_MARK.read_text(encoding="utf-8").splitlines() if line.strip()}
    except Exception:
        return set()


def _mark_processed(job_id: int) -> None:
    try:
        FAILED_DIR.mkdir(parents=True, exist_ok=True)
        with open(PROCESSED_MARK, "a", encoding="utf-8") as f:
            f.write(f"{job_id}\n")
    except Exception as e:
        _log.warning("mark processed fail: %s", e)


def _open_explorer(path: Path) -> None:
    """Windows 탐색기에서 폴더 열기."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        _log.info("탐색기 열기: %s", path)
    except Exception as e:
        _log.warning("탐색기 열기 실패: %s", e)


def _windows_toast(title: str, body: str) -> None:
    """Windows 10+ 토스트 알림 (PowerShell 기반)."""
    if not sys.platform.startswith("win"):
        return
    try:
        ps = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "[System.Windows.Forms.MessageBox]::Show("
            f"'{body}', '{title}', 0, 48)"
        )
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
            creationflags=0x08000000 if sys.platform.startswith("win") else 0,
        )
    except Exception as e:
        _log.warning("toast 실패: %s", e)


def _save_failure_bundle(job: dict) -> Optional[Path]:
    """DLQ 작업 1건 → failed_files/FAIL_{id}_{ts}/ 디렉토리 생성."""
    job_id = job.get("id")
    if not job_id:
        return None
    try:
        payload = json.loads(job.get("payload_json") or "{}")
    except Exception:
        payload = {}

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_dir = FAILED_DIR / f"FAIL_{job_id}_{ts}"
    job_dir.mkdir(parents=True, exist_ok=True)

    # 1) metadata.json
    meta = {
        "job_id": job_id,
        "job_type": job.get("job_type"),
        "candidate_id": payload.get("candidate_id", ""),
        "file_type": payload.get("file_type", ""),
        "filename": payload.get("filename", ""),
        "s3_key": payload.get("s3_key", ""),
        "attempts": job.get("attempts"),
        "max_attempts": job.get("max_attempts"),
        "last_error": job.get("last_error"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "instructions": {
            "1_inspect": "이 폴더의 파일을 직접 열어보고 문제 확인",
            "2_manual_process": "tools/doc_processor.py 로 로컬에서 직접 처리 가능",
            "3_requeue_after_fix": "/admin/pipeline 대시보드 → 재큐잉 버튼",
            "4_skip": "처리 불가능한 파일이면 대시보드에서 삭제(스킵)",
        },
    }
    (job_dir / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 2) ERROR.txt
    err_txt = (
        f"Job ID: {job_id}\n"
        f"Job Type: {job.get('job_type')}\n"
        f"Candidate: {payload.get('candidate_id')}\n"
        f"File: {payload.get('filename')}\n"
        f"Attempts: {job.get('attempts')}/{job.get('max_attempts')}\n"
        f"\n--- Error ---\n{job.get('last_error') or '(no message)'}\n"
    )
    (job_dir / "ERROR.txt").write_text(err_txt, encoding="utf-8")

    # 3) S3 파일 다운로드 시도
    s3_key = payload.get("s3_key", "")
    if s3_key:
        signed = _fetch_presigned_url(s3_key)
        if signed:
            original_name = payload.get("filename") or s3_key.rsplit("/", 1)[-1] or "original_file"
            dest = job_dir / original_name
            if _download_file(signed, dest):
                _log.info("원본 다운로드 완료: %s", dest)
            else:
                # 실패 기록만 남기고 계속
                (job_dir / "DOWNLOAD_FAILED.txt").write_text(
                    f"presigned URL: {signed[:200]}\n다운로드 실패",
                    encoding="utf-8",
                )
        else:
            (job_dir / "DOWNLOAD_SKIP.txt").write_text(
                f"s3_key: {s3_key}\npresigned URL 획득 실패 — AWS 자격증명 또는 엔드포인트 문제",
                encoding="utf-8",
            )

    return job_dir


def run_once(open_folder: bool = True) -> int:
    """DLQ 1회 스캔. 신규 DLQ 진입한 것만 처리."""
    jobs = _fetch_dlq_jobs()
    if not jobs:
        _log.info("DLQ 비어있음")
        return 0

    processed = _load_processed_ids()
    new_jobs = [j for j in jobs if str(j.get("id")) not in processed]
    if not new_jobs:
        _log.info("신규 DLQ 없음 (기존 %d건 유지)", len(jobs))
        return 0

    _log.warning("신규 DLQ %d건 감지 — 처리 시작", len(new_jobs))

    first_dir: Optional[Path] = None
    for j in new_jobs:
        d = _save_failure_bundle(j)
        if d and first_dir is None:
            first_dir = d
        _mark_processed(j["id"])
        _log.warning("  FAIL #%s [%s] candidate=%s file=%s",
                     j.get("id"), j.get("job_type"),
                     (json.loads(j.get("payload_json") or "{}")).get("candidate_id", ""),
                     (json.loads(j.get("payload_json") or "{}")).get("filename", ""))

    # 4) Windows 팝업 + 탐색기 열기
    if first_dir and open_folder:
        _windows_toast(
            title="BRIDGE 파이프라인 실패",
            body=f"{len(new_jobs)}건 실패 — {first_dir.name} 확인 필요",
        )
        _open_explorer(first_dir if len(new_jobs) == 1 else FAILED_DIR)

    return len(new_jobs)


def daemon_loop(interval: int = 60) -> None:
    _log.info("daemon 시작 — %d초 주기", interval)
    while True:
        try:
            run_once(open_folder=True)
        except Exception as e:
            _log.error("cycle error: %s", e, exc_info=True)
        time.sleep(interval)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--daemon", action="store_true", help="60초 주기 상시 감시")
    p.add_argument("--once", action="store_true", help="1회 실행 후 종료 (default)")
    p.add_argument("--interval", type=int, default=60)
    p.add_argument("--no-open", action="store_true", help="탐색기/토스트 자동 열기 비활성")
    args = p.parse_args()

    FAILED_DIR.mkdir(parents=True, exist_ok=True)

    if args.daemon:
        daemon_loop(args.interval)
        return 0
    else:
        return run_once(open_folder=not args.no_open)


if __name__ == "__main__":
    sys.exit(main())
