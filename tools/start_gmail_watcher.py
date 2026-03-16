"""
Gmail 에러 워처 백그라운드 실행 스크립트
사용: python tools/start_gmail_watcher.py

창 없이 백그라운드에서 실행됨.
로그: logs/gmail_error_watcher.log
"""
import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 이미 실행 중인지 확인
pid_file = PROJECT_ROOT / "logs" / "gmail_watcher.pid"

def is_running(pid: int) -> bool:
    try:
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
    except Exception:
        pass
    return False

if pid_file.exists():
    try:
        old_pid = int(pid_file.read_text().strip())
        if is_running(old_pid):
            print(f"이미 실행 중 (PID: {old_pid})")
            print(f"로그: logs/gmail_error_watcher.log")
            sys.exit(0)
    except Exception:
        pass

# pythonw.exe로 창 없이 실행
pythonw = Path(sys.executable).parent / "pythonw.exe"
if not pythonw.exists():
    pythonw = sys.executable  # fallback

log_file = PROJECT_ROOT / "logs" / "gmail_error_watcher.log"
(PROJECT_ROOT / "logs").mkdir(exist_ok=True)

proc = subprocess.Popen(
    [str(pythonw), str(PROJECT_ROOT / "tools" / "gmail_error_watcher.py")],
    stdout=open(str(log_file), "a", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    cwd=str(PROJECT_ROOT),
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
)

pid_file.write_text(str(proc.pid))
print(f"Gmail 에러 워처 시작 (PID: {proc.pid})")
print(f"로그: {log_file}")
print(f"중지: python tools/stop_gmail_watcher.py")
