"""Start telegram bot as a detached subprocess."""
import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

proc = subprocess.Popen(
    [sys.executable, "-m", "telegram_agent"],
    stdout=open("telegram_bot.log", "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
)
print(f"Bot started with PID {proc.pid}")
