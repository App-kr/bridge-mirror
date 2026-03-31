"""
Stop Hook — Claude Code Stop event logger
stop_hook.bat 교체 — Python3 직접 실행 (bash 오류 없음)
"""
import datetime
from pathlib import Path

LOG_FILE = Path(r"Q:\Claudework\bridge base\logs\stop_hook.log")
LOG_FILE.parent.mkdir(exist_ok=True)

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
with open(LOG_FILE, "a", encoding="utf-8") as f:
    f.write(f"[STOP] {now}\n")
