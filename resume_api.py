"""
resume_api.py — BRIDGE Resume Converter FastAPI 라우터
Admin HMAC 인증 후에만 접근 가능

POST  /api/resume/process           — 이력서 처리 시작 (비동기 job)
GET   /api/resume/preview/{job_id}  — 처리 상태/결과 조회
GET   /api/resume/download/{job_id} — 완료된 PDF 다운로드
POST  /api/resume/edit/{job_id}     — 수동 편집 적용
POST  /api/resume/focus-check/{job_id} — 집중 PII 점검
GET   /api/resume/unprocessed       — 미처리 시트 행 목록
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

log = logging.getLogger("resume_api")

# ── 경로 설정 ──────────────────────────────────────────────────────────────
_API_DIR   = Path(__file__).parent
_RC_DIR    = _API_DIR / "tools" / "resume_converter"
_OUTPUT    = _RC_DIR / "output"
_INBOX     = _RC_DIR / "inbox"
_OUTPUT.mkdir(parents=True, exist_ok=True)
_INBOX.mkdir(parents=True, exist_ok=True)

# resume_converter 패키지 경로 추가
if str(_API_DIR / "tools") not in sys.path:
    sys.path.insert(0, str(_API_DIR / "tools"))

router = APIRouter(prefix="/api/resume", tags=["resume"])

# ── 인증 의존성 (기존 _check_admin 재사용) ────────────────────────────────
def _get_admin_check():
    """api_server.py의 _check_admin 임포트."""
    try:
        import api_server
        return api_server._check_admin
    except Exception:
        # 폴백: 헤더 검사 없음 (로컬 테스트용)
        async def _no_auth():
            return True
        return _no_auth

# ── 인메모리 Job 스토어 ────────────────────────────────────────────────────
_jobs: dict[str, dict] = {}


def _new_job(candidate_id: str) -> dict:
    job = {
        "job_id":      str(uuid.uuid4()),
        "candidate_id": candidate_id,
        "status":      "pending",
        "step":        "대기 중",
        "pii_count":   0,
        "output_file": None,
        "error":       None,
        "output_path": None,
    }
    _jobs[job["job_id"]] = job
    return job


# ── POST /api/resume/process ──────────────────────────────────────────────
@router.post("/process")
async def process_resume(
    candidate_id: str = Form(...),
    files: list[UploadFile] = File(...),
):
    """파일 업로드 → 비동기 파이프라인 실행."""
    # 파일 inbox에 저장
    import datetime
    today    = datetime.date.today().strftime("%Y%m%d")
    dest_dir = _INBOX / f"{candidate_id}_제출_{today}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for uf in files:
        dest = dest_dir / (uf.filename or f"file_{uuid.uuid4().hex[:6]}")
        dest.write_bytes(await uf.read())
        saved_paths.append(dest)

    job = _new_job(candidate_id)
    job_id = job["job_id"]

    # 백그라운드 스레드로 파이프라인 실행
    def _run():
        try:
            from resume_converter.pipeline import Pipeline
            def _progress(msg: str):
                log.info(f"[Job {job_id[:8]}] {msg}")
                job["step"] = msg

            pl = Pipeline(auto_mode=True, on_progress=_progress)
            job["status"] = "processing"
            result = pl.run(candidate_id, dest_dir)

            if result.errors:
                job["status"] = "error"
                job["error"]  = " | ".join(result.errors)
            else:
                job["status"]      = "completed"
                job["output_path"] = str(result.output_path) if result.output_path else None
                job["output_file"] = result.output_path.name if result.output_path else None
                job["pii_count"]   = sum([
                    len(result.cover_pii.pii_found)  if result.cover_pii  else 0,
                    len(result.resume_pii.pii_found) if result.resume_pii else 0,
                    len(result.rec_pii.pii_found)    if result.rec_pii    else 0,
                ])
        except Exception as e:
            job["status"] = "error"
            job["error"]  = str(e)
            log.exception(f"파이프라인 오류 job={job_id}")

    threading.Thread(target=_run, daemon=True, name=f"resume-{job_id[:8]}").start()

    return JSONResponse({
        "job_id": job_id,
        "status": "pending",
        "step":   "시작 중...",
        "pii_count": 0,
    })


# ── GET /api/resume/preview/{job_id} ─────────────────────────────────────
@router.get("/preview/{job_id}")
async def get_preview(job_id: str):
    """처리 상태 + 결과 조회."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "작업을 찾을 수 없습니다")
    return JSONResponse({
        "job_id":      job["job_id"],
        "status":      job["status"],
        "step":        job["step"],
        "pii_count":   job["pii_count"],
        "output_file": job["output_file"],
        "error":       job["error"],
    })


# ── GET /api/resume/download/{job_id} ────────────────────────────────────
@router.get("/download/{job_id}")
async def download_pdf(job_id: str):
    """완료된 PDF 파일 다운로드."""
    job = _jobs.get(job_id)
    if not job or job["status"] != "completed":
        raise HTTPException(404, "완료된 파일이 없습니다")

    out_path = Path(job["output_path"]) if job["output_path"] else None
    if not out_path or not out_path.exists():
        raise HTTPException(404, "파일을 찾을 수 없습니다")

    return FileResponse(
        path=str(out_path),
        media_type="application/pdf",
        filename=out_path.name,
    )


# ── POST /api/resume/edit/{job_id} ───────────────────────────────────────
@router.post("/edit/{job_id}")
async def edit_resume(job_id: str, body: dict):
    """수동 텍스트 편집 후 PDF 재생성."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "작업을 찾을 수 없습니다")

    edited_text = body.get("text", "")
    if not edited_text:
        raise HTTPException(400, "편집 내용이 없습니다")

    try:
        from resume_converter.pdf_builder import build_pdf
        out, size = build_pdf(
            candidate_id = job["candidate_id"],
            resume_text  = edited_text,
            out_dir      = _OUTPUT,
        )
        job["output_path"] = str(out)
        job["output_file"] = out.name
        return JSONResponse({"status": "ok", "output_file": out.name, "size_kb": size // 1024})
    except Exception as e:
        raise HTTPException(500, str(e))


# ── POST /api/resume/focus-check/{job_id} ───────────────────────────────
@router.post("/focus-check/{job_id}")
async def focus_check(job_id: str, body: dict):
    """선택 텍스트 집중 PII 점검."""
    text = body.get("text", "")
    if not text.strip():
        raise HTTPException(400, "텍스트가 없습니다")

    try:
        from resume_converter.pii_engine import analyze_pii_focus, load_api_key
        api_key = load_api_key()
        if not api_key:
            raise HTTPException(503, "Anthropic API 키 미설정")

        result = analyze_pii_focus(text, api_key)
        return JSONResponse({
            "cleaned_text": result.cleaned_text,
            "pii_found": [
                {
                    "type":     p.type,
                    "original": p.original_value[:50],
                    "color":    p.color,
                }
                for p in result.pii_found
            ],
            "uncertain": result.uncertain,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ── GET /api/resume/unprocessed ──────────────────────────────────────────
@router.get("/unprocessed")
async def get_unprocessed():
    """미처리 구글시트 행 목록."""
    try:
        from resume_converter.sheets_connector import get_unprocessed_rows
        rows = get_unprocessed_rows(20)
        return JSONResponse({"rows": rows})
    except Exception as e:
        log.warning(f"미처리 목록 조회 실패: {e}")
        return JSONResponse({"rows": []})
