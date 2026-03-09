"""
BRIDGE uploads/ → S3 일괄 마이그레이션 스크립트
=================================================
기존 로컬 uploads/ 디렉토리의 파일을 AWS S3로 이관합니다.
이관 후 로컬 파일은 삭제하지 않습니다 (롤백 대비).

실행 방법:
    cd "Q:/Claudework/bridge base"
    python backend/scripts/migrate_uploads_to_s3.py

필수 환경변수 (.env 또는 shell export):
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    AWS_S3_BUCKET
    AWS_REGION (선택, 기본 ap-northeast-2)

출력:
    - 콘솔: 진행 상황 실시간 출력
    - 파일: backend/scripts/migration_report_{timestamp}.txt
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 환경변수 로드 (.env 파일)
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    print("[INFO] .env 로드 완료")
except ImportError:
    print("[WARN] python-dotenv 없음 — 환경변수를 직접 설정하세요.")

# AWS 환경변수 확인 (Fail-Closed)
_REQUIRED = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_BUCKET"]
_MISSING = [k for k in _REQUIRED if not os.environ.get(k)]
if _MISSING:
    print(f"[ERROR] 필수 환경변수 미설정: {_MISSING}")
    print("  .env 파일에 AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET 를 설정하세요.")
    sys.exit(1)

import boto3
from botocore.exceptions import ClientError

AWS_ACCESS_KEY_ID     = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_S3_BUCKET         = os.environ["AWS_S3_BUCKET"]
AWS_REGION            = os.environ.get("AWS_REGION", "ap-northeast-2")

UPLOADS_DIR = PROJECT_ROOT / "uploads"
REPORT_DIR  = Path(__file__).parent

# 마이그레이션 시 S3 키 접두사 (기존 파일 구분용)
S3_LEGACY_PREFIX = "legacy"


def _get_content_type(ext: str) -> str:
    _MAP = {
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
    }
    return _MAP.get(ext.lower(), "application/octet-stream")


def migrate(dry_run: bool = False) -> None:
    """
    uploads/ → S3 마이그레이션 실행.

    Args:
        dry_run: True이면 실제 업로드 없이 대상 파일 목록만 출력
    """
    if not UPLOADS_DIR.exists():
        print(f"[INFO] uploads/ 디렉토리 없음: {UPLOADS_DIR}")
        return

    # 대상 파일 수집
    all_files = [f for f in UPLOADS_DIR.rglob("*") if f.is_file()]

    if not all_files:
        print("[INFO] uploads/ 비어있음 — 마이그레이션 불필요")
        return

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}마이그레이션 대상: {len(all_files)}개 파일")
    print(f"  로컬 경로: {UPLOADS_DIR}")
    print(f"  S3 버킷  : s3://{AWS_S3_BUCKET}/{S3_LEGACY_PREFIX}/")
    print(f"  리전     : {AWS_REGION}")
    print()

    if dry_run:
        for f in all_files:
            rel = f.relative_to(UPLOADS_DIR)
            s3_key = f"{S3_LEGACY_PREFIX}/{rel.as_posix()}"
            size_kb = f.stat().st_size // 1024
            print(f"  [{size_kb:>6}KB] {f.name}  →  {s3_key}")
        print("\n[DRY-RUN] 실제 업로드 없이 종료합니다. --upload 플래그로 실행하세요.")
        return

    # S3 클라이언트
    s3 = boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    # 연결 확인
    try:
        s3.head_bucket(Bucket=AWS_S3_BUCKET)
        print(f"[OK] S3 연결 확인: {AWS_S3_BUCKET}")
    except ClientError as e:
        print(f"[ERROR] S3 연결 실패: {e}")
        sys.exit(1)

    success_count = 0
    fail_count = 0
    log_entries: list[dict] = []
    start_time = time.time()

    for idx, f in enumerate(all_files, 1):
        rel = f.relative_to(UPLOADS_DIR)
        s3_key = f"{S3_LEGACY_PREFIX}/{rel.as_posix()}"
        ext = f.suffix.lower()
        content_type = _get_content_type(ext)
        file_size = f.stat().st_size

        try:
            s3.upload_file(
                Filename=str(f),
                Bucket=AWS_S3_BUCKET,
                Key=s3_key,
                ExtraArgs={"ContentType": content_type},
            )
            status = "ok"
            success_count += 1
            print(f"  [{idx:>3}/{len(all_files)}] OK   {s3_key} ({file_size // 1024}KB)")
        except Exception as e:
            status = f"fail:{e}"
            fail_count += 1
            print(f"  [{idx:>3}/{len(all_files)}] FAIL {f.name} — {e}")

        log_entries.append({
            "local":   str(f),
            "s3_key":  s3_key,
            "size":    file_size,
            "status":  status,
        })

    elapsed = time.time() - start_time

    # 리포트 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"migration_report_{timestamp}.txt"
    with open(report_path, "w", encoding="utf-8") as r:
        r.write(f"BRIDGE uploads/ → S3 마이그레이션 리포트\n")
        r.write(f"실행 시각: {datetime.now().isoformat()}\n")
        r.write(f"버킷     : {AWS_S3_BUCKET} ({AWS_REGION})\n")
        r.write(f"결과     : 성공 {success_count}개 / 실패 {fail_count}개 / 총 {len(all_files)}개\n")
        r.write(f"소요시간  : {elapsed:.1f}초\n")
        r.write("─" * 80 + "\n")
        for entry in log_entries:
            r.write(f"{entry['status']}\t{entry['local']}\t{entry['s3_key']}\t{entry['size']}B\n")

    print(f"\n{'─' * 60}")
    print(f"완료: {success_count}개 성공 / {fail_count}개 실패 ({elapsed:.1f}초)")
    print(f"리포트: {report_path}")

    if fail_count > 0:
        print(f"\n[WARNING] {fail_count}개 파일 마이그레이션 실패. 리포트를 확인하세요.")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="BRIDGE uploads/ → S3 마이그레이션"
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="실제 업로드 실행 (미지정 시 dry-run)",
    )
    args = parser.parse_args()

    migrate(dry_run=not args.upload)
