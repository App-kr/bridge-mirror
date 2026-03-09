#!/usr/bin/env python3
"""
auto_backup.py — Bridge DB 5분 주기 자동 백업
  - 영구보존 (삭제 없음)
  - 폴더 구조: .backups/auto/YYYY-MM-DD_AM|PM/master_HHMMSS.db
    - AM: 00:00 ~ 11:59
    - PM: 12:00 ~ 23:59
  - 로그: .logs/auto_backup.log
"""
import os
import shutil
import datetime

BASE        = r"Q:\Claudework\bridge base"
DB_PATH     = os.path.join(BASE, "master.db")
BACKUP_ROOT = os.path.join(BASE, ".backups", "auto")
LOG_PATH    = os.path.join(BASE, ".logs", "auto_backup.log")

def main():
    if not os.path.exists(DB_PATH):
        return  # DB 없으면 조용히 종료

    now  = datetime.datetime.now()
    half = "AM" if now.hour < 12 else "PM"
    date_str = now.strftime("%Y-%m-%d")
    folder   = f"{date_str}_{half}"

    dst_dir = os.path.join(BACKUP_ROOT, folder)
    os.makedirs(dst_dir, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    ts  = now.strftime("%H%M%S")
    dst = os.path.join(dst_dir, f"master_{ts}.db")

    shutil.copy2(DB_PATH, dst)
    size_kb = os.path.getsize(dst) // 1024

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{now.strftime('%Y-%m-%d %H:%M:%S')} | {folder}/master_{ts}.db | {size_kb}KB\n")

if __name__ == "__main__":
    main()
