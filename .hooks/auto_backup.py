#!/usr/bin/env python3
"""
auto_backup.py — Bridge DB 5분 주기 자동 백업
  - 보존 정책: 최근 48시간 전체 + 48시간 이전 날짜별 최신 1개
  - 폴더 구조: .backups/auto/YYYY-MM-DD_AM|PM/master_HHMMSS.db
    - AM: 00:00 ~ 11:59
    - PM: 12:00 ~ 23:59
  - 로그: .logs/auto_backup.log
"""
import os
import shutil
import datetime
from collections import defaultdict

BASE        = r"Q:\Claudework\bridge base"
DB_PATH     = os.path.join(BASE, "master.db")
BACKUP_ROOT = os.path.join(BASE, ".backups", "auto")
LOG_PATH    = os.path.join(BASE, ".logs", "auto_backup.log")

RETAIN_HOURS = 48  # 이 시간 이내는 전체 보존


def prune_old_backups():
    """
    보존 정책:
    - 최근 48시간: 전체 보존
    - 48시간 이전: 날짜별 최신 1개만 보존, 나머지 삭제
    """
    if not os.path.isdir(BACKUP_ROOT):
        return 0

    cutoff = datetime.datetime.now() - datetime.timedelta(hours=RETAIN_HOURS)
    daily = defaultdict(list)

    for root, dirs, files in os.walk(BACKUP_ROOT):
        for fname in files:
            if not fname.endswith(".db"):
                continue
            fpath = os.path.join(root, fname)
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fpath))
            if mtime < cutoff:
                date_key = mtime.strftime("%Y-%m-%d")
                daily[date_key].append((mtime, fpath))

    deleted = 0
    for date_key, files in daily.items():
        files.sort(key=lambda x: x[0])  # 오래된 순 정렬
        for _, fpath in files[:-1]:      # 최신 1개 제외하고 삭제
            os.remove(fpath)
            deleted += 1

    # 빈 폴더 제거
    for root, dirs, files in os.walk(BACKUP_ROOT, topdown=False):
        if root != BACKUP_ROOT and not os.listdir(root):
            os.rmdir(root)

    return deleted


def main():
    if not os.path.exists(DB_PATH):
        return

    os.makedirs(BACKUP_ROOT, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    # 백업 생성
    now     = datetime.datetime.now()
    half    = "AM" if now.hour < 12 else "PM"
    folder  = now.strftime("%Y-%m-%d") + "_" + half
    dst_dir = os.path.join(BACKUP_ROOT, folder)
    os.makedirs(dst_dir, exist_ok=True)

    ts  = now.strftime("%H%M%S")
    dst = os.path.join(dst_dir, f"master_{ts}.db")
    shutil.copy2(DB_PATH, dst)
    size_kb = os.path.getsize(dst) // 1024

    # 보존 정책 적용
    deleted = prune_old_backups()

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        line = f"{now.strftime('%Y-%m-%d %H:%M:%S')} | {folder}/master_{ts}.db | {size_kb}KB"
        if deleted:
            line += f" | pruned={deleted}"
        f.write(line + "\n")


if __name__ == "__main__":
    main()
