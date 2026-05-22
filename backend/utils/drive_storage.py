"""
BRIDGE Drive Storage Utility
============================
Google Drive 기반 영구 파일 저장소 (S3 대체).

사용 이유:
- Render free plan 의 ephemeral disk 에 사진 저장 시 재시작마다 휘발
- S3 AWS 계정/카드 없는 경우 무료 대안 (Google Drive 15GB 무료)
- 이미 db_persist.py 가 같은 Drive OAuth 사용 → 추가 자격증명 불필요

저장 구조:
  BRIDGE_UPLOADS/
    candidates/{cid}/photos/{uuid}_filename.jpg
    candidates/{cid}/cv/{uuid}_resume.pdf
    candidates/{cid}/certificates/{uuid}_cert.pdf
    community/{board}/{post_id}/{uuid}_image.png

서빙 방식:
- 업로드 후 s3_key 형식: "drive://{file_id}"  (S3 인터페이스 호환)
- s3_url 형식: "/api/drive-file/{file_id}"  (api_server 가 프록시 서빙)

환경변수 (db_persist.py 와 공유):
  DRIVE_OAUTH_TOKEN_JSON : Drive OAuth 토큰 (Render env 에 이미 설정됨)
"""
from __future__ import annotations
import io
import os
import sys
import uuid
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("bridge.drive_storage")

# ── 허용 확장자 (S3 storage 와 동일) ─────────────────────────────────────
ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    "image":    {".jpg", ".jpeg", ".png", ".webp", ".gif"},
    "document": {".pdf", ".doc", ".docx"},
    "resume":   {".pdf", ".doc", ".docx", ".hwp"},
    "video":    {".mp4", ".mov", ".webm"},
    "any":      {
        ".jpg", ".jpeg", ".png", ".webp", ".gif",
        ".pdf", ".doc", ".docx", ".hwp",
        ".mp4", ".mov", ".webm",
        ".xlsx", ".ppt", ".pptx", ".txt", ".zip",
    },
}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
UPLOADS_FOLDER_NAME = os.getenv("DRIVE_UPLOADS_FOLDER", "BRIDGE_UPLOADS")


class StorageError(Exception):
    pass


def _drive():
    """Reuse db_persist OAuth Drive client (DRIVE_OAUTH_TOKEN_JSON env var)."""
    _tools = Path(__file__).resolve().parent.parent.parent / "tools"
    if str(_tools) not in sys.path:
        sys.path.insert(0, str(_tools))
    from db_persist import _drive as _get_drive  # type: ignore
    return _get_drive()


# 폴더 ID 캐시 (메모리, 재시작 시 리셋)
_folder_cache: dict[str, str] = {}


def _get_or_create_folder(drive, name: str, parent_id: Optional[str] = None) -> str:
    """Drive 폴더 ID 조회 또는 생성 (중첩 가능)."""
    cache_key = f"{parent_id or 'root'}/{name}"
    if cache_key in _folder_cache:
        return _folder_cache[cache_key]
    safe_name = name.replace("'", "\\'")
    q = f"name='{safe_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    res = drive.files().list(q=q, fields='files(id,name)', pageSize=10).execute()
    files = res.get('files', [])
    if files:
        _folder_cache[cache_key] = files[0]['id']
        return files[0]['id']
    meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
    if parent_id:
        meta['parents'] = [parent_id]
    folder = drive.files().create(body=meta, fields='id').execute()
    _folder_cache[cache_key] = folder['id']
    return folder['id']


def _validate_extension(filename: str, category: str) -> str:
    """확장자 검증 후 정규화된 확장자 반환."""
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    allowed = ALLOWED_EXTENSIONS.get(category, ALLOWED_EXTENSIONS["any"])
    if ext not in allowed:
        raise StorageError(
            f"허용되지 않는 파일 형식: '{ext}' (category={category}, allowed={sorted(allowed)})"
        )
    return ext


def _safe_filename(original: str) -> str:
    """업로드 파일명에 uuid prefix 추가 (충돌 방지)."""
    base = os.path.basename(original).replace("/", "_").replace("\\", "_")
    return f"{uuid.uuid4().hex[:12]}_{base}"[:200]


def upload_bytes_sync(
    data: bytes,
    folder: str,
    filename: str,
    allowed_category: str = "any",
    content_type: Optional[str] = None,
) -> dict:
    """동기 Drive 업로드. S3 storage의 upload_bytes_sync 와 인터페이스 호환.

    Args:
        data: 파일 바이트
        folder: 가상 경로 (예: 'candidates/cnd_xxx/photos')
        filename: 원본 파일명
        allowed_category: 허용 카테고리 ('image'|'resume'|'video'|'any'|...)
        content_type: MIME type (선택)

    Returns:
        {'s3_key': 'drive://{file_id}', 's3_url': '/api/drive-file/{file_id}',
         'filename': safe_name, 'size': len, 'file_id': file_id}
    """
    if len(data) > MAX_FILE_SIZE:
        raise StorageError(f"파일 크기 초과: {len(data)} > {MAX_FILE_SIZE}")
    if not data:
        raise StorageError("빈 파일")

    _validate_extension(filename, allowed_category)
    safe_name = _safe_filename(filename)

    try:
        drive = _drive()
    except Exception as e:
        raise StorageError(f"Drive 인증 실패: {e}")

    # 폴더 계층 생성 (BRIDGE_UPLOADS / candidates / {cid} / photos)
    try:
        parent_id = _get_or_create_folder(drive, UPLOADS_FOLDER_NAME)
        for part in folder.split("/"):
            if part.strip():
                parent_id = _get_or_create_folder(drive, part.strip(), parent_id=parent_id)
    except Exception as e:
        raise StorageError(f"Drive 폴더 생성 실패: {e}")

    # 업로드
    try:
        from googleapiclient.http import MediaIoBaseUpload
        media = MediaIoBaseUpload(
            io.BytesIO(data),
            mimetype=content_type or "application/octet-stream",
            resumable=False,
        )
        file = drive.files().create(
            body={"name": safe_name, "parents": [parent_id]},
            media_body=media,
            fields="id,name,size,mimeType",
        ).execute()
        file_id = file["id"]
    except Exception as e:
        raise StorageError(f"Drive 업로드 실패: {e}")

    # 누구나 링크로 보기 가능하게 (선택 — 프록시 서빙해도 OK)
    try:
        drive.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute()
    except Exception as e:
        log.warning("Drive permission anyone:reader 설정 실패 (계속): %s", e)

    return {
        "s3_key": f"drive://{file_id}",
        "s3_url": f"/api/drive-file/{file_id}",
        "filename": safe_name,
        "size": len(data),
        "file_id": file_id,
    }


async def upload_bytes(*args, **kwargs):
    """비동기 wrapper — 내부는 동기 (Drive SDK 가 동기 only)."""
    import asyncio
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: upload_bytes_sync(*args, **kwargs))


def download_bytes(s3_key: str) -> bytes:
    """Drive 파일 다운로드 (s3_key 형식: 'drive://{file_id}')."""
    if not s3_key.startswith("drive://"):
        raise StorageError(f"Drive storage 가 아닌 s3_key: {s3_key}")
    file_id = s3_key[len("drive://"):]
    try:
        drive = _drive()
        from googleapiclient.http import MediaIoBaseDownload
        req = drive.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buf.seek(0)
        return buf.read()
    except Exception as e:
        raise StorageError(f"Drive 다운로드 실패 ({file_id}): {e}")


def get_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    """Drive 는 presigned URL 개념이 없음 — 프록시 endpoint 반환."""
    if s3_key.startswith("drive://"):
        return f"/api/drive-file/{s3_key[len('drive://'):]}"
    raise StorageError(f"지원되지 않는 s3_key: {s3_key}")


def delete_file(s3_key: str) -> bool:
    """Drive 파일 삭제 (논리적 삭제는 trashed=true)."""
    if not s3_key.startswith("drive://"):
        return False
    file_id = s3_key[len("drive://"):]
    try:
        drive = _drive()
        drive.files().update(fileId=file_id, body={"trashed": True}).execute()
        return True
    except Exception as e:
        log.warning("Drive 파일 삭제 실패 (%s): %s", file_id, e)
        return False


def check_drive_connection() -> bool:
    """헬스체크 — Drive 인증/연결 검증."""
    try:
        drive = _drive()
        drive.files().list(pageSize=1, fields='files(id)').execute()
        return True
    except Exception as e:
        log.warning("Drive 연결 실패: %s", e)
        return False


# S3 인터페이스 호환 alias
upload_file = upload_bytes
