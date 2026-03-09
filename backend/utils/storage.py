"""
BRIDGE Storage Utility
======================
로컬 uploads/ → AWS S3 대체.

- Fail-Closed: 환경변수 미설정 시 즉시 RuntimeError (로컬 fallback 없음)
- Zero-Leak: presigned URL 방식, S3 버킷 public 차단 권장
- 프로덕션 데이터 소실 방지: Render 재시작 시 파일 유지

환경변수 (하드코딩 절대 금지):
    AWS_ACCESS_KEY_ID     : AWS 액세스 키
    AWS_SECRET_ACCESS_KEY : AWS 시크릿 키
    AWS_S3_BUCKET         : S3 버킷 이름
    AWS_REGION            : AWS 리전 (기본 ap-northeast-2)
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import UploadFile

log = logging.getLogger(__name__)

# ── 환경변수 (하드코딩 절대 금지) ────────────────────────────────────────────
AWS_ACCESS_KEY_ID     = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET         = os.environ.get("AWS_S3_BUCKET")
AWS_REGION            = os.environ.get("AWS_REGION", "ap-northeast-2")

# ── 허용 파일 타입 (Whitelist) ────────────────────────────────────────────────
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

# 기본 최대 파일 크기 (upload_file 경로 독립 제한)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Content-Type 매핑
_CONTENT_TYPE_MAP: dict[str, str] = {
    ".pdf":  "application/pdf",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".webp": "image/webp",
    ".gif":  "image/gif",
    ".doc":  "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".hwp":  "application/x-hwp",
    ".mp4":  "video/mp4",
    ".mov":  "video/quicktime",
    ".webm": "video/webm",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".zip":  "application/zip",
    ".txt":  "text/plain",
}


class StorageError(Exception):
    """S3 스토리지 작업 중 발생하는 예외."""


# ──────────────────────────────────────────────────────────────────────────────
# 내부 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _get_s3_client():
    """
    S3 클라이언트 생성 — 환경변수 미설정 시 Fail-Closed (RuntimeError).
    로컬 fallback 없음: 잘못된 설정으로 파일이 로컬에 저장되면
    Render 재배포 시 소실되므로 즉시 실패 처리.
    """
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET]):
        raise RuntimeError(
            "S3 환경변수 미설정 — .env에 다음 변수를 설정하세요: "
            "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET"
        )
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )


def _validate_file_ext(filename: str, file_size: int, allowed_category: str) -> str:
    """
    파일 유효성 검증 — 확장자 whitelist + 크기 제한.
    반환: 소문자 확장자 (예: '.pdf')
    """
    ext = os.path.splitext(filename)[1].lower()
    allowed = ALLOWED_EXTENSIONS.get(allowed_category, set())
    if ext not in allowed:
        raise StorageError(
            f"허용되지 않는 파일 형식: '{ext}'. "
            f"허용 목록 ({allowed_category}): {sorted(allowed)}"
        )
    if file_size > MAX_FILE_SIZE:
        raise StorageError(
            f"파일 크기 초과: {file_size / 1024 / 1024:.1f}MB "
            f"(최대 {MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
        )
    return ext


def _generate_s3_key(folder: str, original_filename: str, ext: str) -> str:
    """
    S3 키 생성 — UUID 기반, 원본 파일명 노출 방지.
    형식: {folder}/{YYYY/MM/DD}/{uuid}{ext}
    예:  candidates/cnd_xxx/2026/03/09/a1b2c3d4.pdf
    """
    date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
    unique_id = uuid.uuid4().hex
    return f"{folder}/{date_prefix}/{unique_id}{ext}"


# ──────────────────────────────────────────────────────────────────────────────
# 공개 API
# ──────────────────────────────────────────────────────────────────────────────

async def upload_file(
    file: UploadFile,
    folder: str = "uploads",
    allowed_category: str = "document",
) -> dict:
    """
    파일 S3 업로드.

    Args:
        file            : FastAPI UploadFile 객체
        folder          : S3 키 접두사 (예: 'candidates/cnd_xxx')
        allowed_category: 허용 파일 카테고리 ('image' | 'document' | 'resume' | 'any')

    Returns:
        {
            "s3_key"  : str,  # DB 저장용 키 (전체 URL 아님)
            "s3_url"  : str,  # https://{bucket}.s3.{region}.amazonaws.com/{key}
            "filename": str,  # 원본 파일명
            "size"    : int,  # 바이트
        }

    Raises:
        RuntimeError  : 환경변수 미설정 (Fail-Closed)
        StorageError  : 파일 유효성 오류 또는 S3 오류
    """
    s3 = _get_s3_client()

    content = await file.read()
    file_size = len(content)
    if file_size == 0:
        raise StorageError("빈 파일은 업로드할 수 없습니다.")

    original_name = file.filename or "unnamed"
    ext = _validate_file_ext(original_name, file_size, allowed_category)
    s3_key = _generate_s3_key(folder, original_name, ext)
    content_type = _CONTENT_TYPE_MAP.get(ext, "application/octet-stream")

    try:
        s3.put_object(
            Bucket=AWS_S3_BUCKET,
            Key=s3_key,
            Body=content,
            ContentType=content_type,
            # public-read 미설정 — presigned URL로만 접근 (Zero-Leak)
        )
    except NoCredentialsError:
        raise RuntimeError("AWS 인증 실패 — AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY 확인")
    except ClientError as e:
        raise StorageError(f"S3 업로드 실패: {e.response['Error']['Message']}")

    s3_url = f"https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
    log.info("[S3] 업로드 완료: key=%s size=%d", s3_key, file_size)

    return {
        "s3_key":   s3_key,
        "s3_url":   s3_url,
        "filename": original_name,
        "size":     file_size,
    }


async def upload_bytes(
    data: bytes,
    folder: str,
    filename: str,
    allowed_category: str = "document",
) -> dict:
    """
    이미 읽은 bytes를 S3에 업로드.

    api_server.py에서 data = await file.read() 처리 후 파일 포인터가
    소진된 경우 이 함수를 사용하세요.

    Args:
        data            : 파일 바이트
        folder          : S3 키 접두사
        filename        : 원본 파일명 (확장자 판별용)
        allowed_category: 허용 카테고리

    Returns:
        upload_file과 동일한 dict
    """
    s3 = _get_s3_client()

    file_size = len(data)
    if file_size == 0:
        raise StorageError("빈 파일은 업로드할 수 없습니다.")

    ext = _validate_file_ext(filename, file_size, allowed_category)
    s3_key = _generate_s3_key(folder, filename, ext)
    content_type = _CONTENT_TYPE_MAP.get(ext, "application/octet-stream")

    try:
        s3.put_object(
            Bucket=AWS_S3_BUCKET,
            Key=s3_key,
            Body=data,
            ContentType=content_type,
        )
    except NoCredentialsError:
        raise RuntimeError("AWS 인증 실패 — AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY 확인")
    except ClientError as e:
        raise StorageError(f"S3 업로드 실패: {e.response['Error']['Message']}")

    s3_url = f"https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
    log.info("[S3] 업로드 완료: key=%s size=%d", s3_key, file_size)

    return {
        "s3_key":   s3_key,
        "s3_url":   s3_url,
        "filename": filename,
        "size":     file_size,
    }


def get_presigned_url(s3_key: str, expires: int = 3600) -> str:
    """
    Presigned URL 생성 — 임시 접근 권한 (기본 1시간).

    S3 버킷 public 차단 상태에서 안전하게 파일을 전달합니다.
    URL은 expires 초 후 자동 만료됩니다.

    Args:
        s3_key : upload_file / upload_bytes 반환값의 's3_key'
        expires: URL 유효 시간 (초, 기본 3600)

    Returns:
        서명된 임시 다운로드 URL

    Raises:
        RuntimeError : 환경변수 미설정
        StorageError : S3 오류
    """
    s3 = _get_s3_client()
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": AWS_S3_BUCKET, "Key": s3_key},
            ExpiresIn=expires,
        )
        return url
    except ClientError as e:
        raise StorageError(f"Presigned URL 생성 실패: {e}")


def delete_file(s3_key: str) -> bool:
    """
    S3 파일 삭제.

    논리삭제(is_deleted=1) 처리 후 실제 S3 파일을 제거할 때 호출합니다.

    Args:
        s3_key: 삭제할 S3 키

    Returns:
        True — 삭제 성공

    Raises:
        RuntimeError : 환경변수 미설정
        StorageError : S3 오류
    """
    s3 = _get_s3_client()
    try:
        s3.delete_object(Bucket=AWS_S3_BUCKET, Key=s3_key)
        log.info("[S3] 파일 삭제: key=%s", s3_key)
        return True
    except ClientError as e:
        raise StorageError(f"S3 삭제 실패: {e.response['Error']['Message']}")


def check_s3_connection() -> bool:
    """
    S3 연결 상태 확인 — 헬스체크 / 서버 시작 시 사용.

    Returns:
        True  — 연결 정상
        False — 환경변수 미설정 또는 연결 실패
    """
    try:
        s3 = _get_s3_client()
        s3.head_bucket(Bucket=AWS_S3_BUCKET)
        log.info("[S3] 연결 정상: bucket=%s region=%s", AWS_S3_BUCKET, AWS_REGION)
        return True
    except Exception as e:
        log.warning("[S3] 연결 실패: %s", e)
        return False
