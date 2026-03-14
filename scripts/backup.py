"""
BRIDGE Backup Utility
======================
백업 저장: BridgeCraig/backups/YYYYMMDD_HHMMSS/
보관 정책: 최대 3일치 유지, 초과분 자동 삭제.

실행:
  python backup.py           # 백업 생성 + 오래된 백업 정리
  python backup.py --list    # 현재 백업 목록 출력
"""

import argparse
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKUP_ROOT = BASE_DIR / "backups"
MAX_AGE_DAYS = 3

# 백업 대상 (소스 코드 + 설정만, DB/이미지/로그 제외)
BACKUP_TARGETS = [
    "craigslist_auto_rpa.py",
    "rpa_overlay.py",
    "scheduler.py",
    "launch_now.ps1",
    "launch_scheduler.ps1",
    "run_rpa.ps1",
    ".gitignore",
    ".env",
    "account1.env",
    "account2.env",
    "account3.env",
]


def create_backup() -> Path:
    """타임스탬프 백업 폴더 생성."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_ROOT / ts
    dest.mkdir(parents=True, exist_ok=True)

    copied = 0
    for name in BACKUP_TARGETS:
        src = BASE_DIR / name
        if src.exists():
            shutil.copy2(src, dest / name)
            copied += 1

    print(f"  [BACKUP] {dest.name}/ — {copied}개 파일 백업 완료")
    return dest


def cleanup_old():
    """3일 초과 백업 폴더 자동 삭제."""
    if not BACKUP_ROOT.exists():
        return

    cutoff = datetime.now() - timedelta(days=MAX_AGE_DAYS)
    removed = 0

    for d in sorted(BACKUP_ROOT.iterdir()):
        if not d.is_dir():
            continue
        try:
            # 폴더명 형식: YYYYMMDD_HHMMSS
            folder_time = datetime.strptime(d.name, "%Y%m%d_%H%M%S")
            if folder_time < cutoff:
                shutil.rmtree(d)
                print(f"  [CLEANUP] {d.name}/ 삭제 (3일 초과)")
                removed += 1
        except ValueError:
            continue

    if removed:
        print(f"  [CLEANUP] {removed}개 오래된 백업 삭제")
    else:
        print(f"  [CLEANUP] 삭제 대상 없음")


def list_backups():
    """현재 백업 목록 출력."""
    if not BACKUP_ROOT.exists():
        print("  백업 없음")
        return

    dirs = sorted(BACKUP_ROOT.iterdir())
    dirs = [d for d in dirs if d.is_dir()]
    if not dirs:
        print("  백업 없음")
        return

    print(f"  백업 위치: {BACKUP_ROOT}")
    print(f"  보관 정책: 최대 {MAX_AGE_DAYS}일")
    print(f"  {'─'*40}")
    for d in dirs:
        files = list(d.iterdir())
        print(f"  {d.name}/  ({len(files)}개 파일)")
    print(f"  {'─'*40}")
    print(f"  총 {len(dirs)}개 백업")


def main():
    parser = argparse.ArgumentParser(description="BRIDGE Backup Utility")
    parser.add_argument("--list", action="store_true", help="백업 목록 출력")
    args = parser.parse_args()

    if args.list:
        list_backups()
        return

    create_backup()
    cleanup_old()


if __name__ == "__main__":
    main()
