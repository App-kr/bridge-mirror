# -*- coding: utf-8 -*-
"""
chrome_clean_search_engines.py
Chrome Web Data에서 Google 외 검색엔진 자동 삭제
시작프로그램에 등록하여 매 부팅 시 실행
"""
import sqlite3
import shutil
import sys
import os
import time
from pathlib import Path

WEB_DATA = Path(os.environ["LOCALAPPDATA"]) / "Google/Chrome/User Data/Default/Web Data"
BACKUP   = Path(os.environ["LOCALAPPDATA"]) / "Google/Chrome/User Data/Default/Web Data.bak"

GOOGLE_KEYWORDS = {"google.com", "google", "google.co.kr"}


def chrome_running():
    import subprocess
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return "chrome.exe" in r.stdout


def clean():
    if not WEB_DATA.exists():
        print("[Chrome] Web Data 없음 — 스킵")
        return

    if chrome_running():
        print("[Chrome] Chrome 실행 중 — 스킵 (재부팅 후 적용)")
        return

    # 백업
    shutil.copy2(WEB_DATA, BACKUP)

    conn = sqlite3.connect(str(WEB_DATA))
    try:
        # 현재 검색엔진 목록
        rows = conn.execute("SELECT id, short_name, keyword FROM keywords").fetchall()
        to_delete = [r[0] for r in rows if r[2].lower() not in GOOGLE_KEYWORDS]

        if not to_delete:
            print(f"[Chrome] Google만 있음 — 변경 없음 ({len(rows)}개)")
            return

        placeholders = ",".join("?" * len(to_delete))
        conn.execute(f"DELETE FROM keywords WHERE id IN ({placeholders})", to_delete)
        conn.commit()
        print(f"[Chrome] 검색엔진 {len(to_delete)}개 삭제 완료 (Google 유지)")
        for r in rows:
            if r[0] in to_delete:
                print(f"  삭제: {r[1]} ({r[2]})")
    finally:
        conn.close()


if __name__ == "__main__":
    clean()
