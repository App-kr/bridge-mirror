"""Gmail 에러 워처 중지."""
import os
import sys
from pathlib import Path
import ctypes

PROJECT_ROOT = Path(__file__).resolve().parent.parent
pid_file = PROJECT_ROOT / "logs" / "gmail_watcher.pid"

if not pid_file.exists():
    print("실행 중인 워처 없음 (PID 파일 없음)")
    sys.exit(0)

try:
    pid = int(pid_file.read_text().strip())
    handle = ctypes.windll.kernel32.OpenProcess(0x0001, False, pid)
    if handle:
        ctypes.windll.kernel32.TerminateProcess(handle, 0)
        ctypes.windll.kernel32.CloseHandle(handle)
        pid_file.unlink(missing_ok=True)
        print(f"워처 중지 완료 (PID: {pid})")
    else:
        print(f"프로세스 {pid} 없음 (이미 중지됨)")
        pid_file.unlink(missing_ok=True)
except Exception as e:
    print(f"에러: {e}")
    pid_file.unlink(missing_ok=True)
