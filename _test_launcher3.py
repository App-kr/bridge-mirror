"""
테스트 3 런처: VBS 역할을 Python으로 대체
1. pythonw.exe로 워커 실행 (숨김 창)
2. CMD 모니터 창 실행 (보임)
"""
import subprocess, sys, os
from pathlib import Path

pythonw  = r"C:\Python314\pythonw.exe"
python   = r"C:\Python314\python.exe"
worker   = r"Q:\Claudework\bridge base\_test_worker3.py"
monitor  = r"Q:\Claudework\bridge base\rpa_console_monitor.py"

# 1) 워커: 숨김 창으로 실행 (DETACHED_PROCESS + CREATE_NO_WINDOW)
DETACHED = 0x00000008
NO_WIN   = 0x08000000

worker_proc = subprocess.Popen(
    [pythonw, worker],
    creationflags=DETACHED | NO_WIN,
    close_fds=True,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)
print(f"Worker PID: {worker_proc.pid} (pythonw, 창 없음)")

# 2) 모니터 콘솔: CMD 창으로 실행 (사용자가 볼 수 있는 창)
monitor_proc = subprocess.Popen(
    ["cmd.exe", "/K", python, "-X", "utf8", monitor],
    creationflags=subprocess.CREATE_NEW_CONSOLE,
)
print(f"Monitor PID: {monitor_proc.pid} (cmd 창)")
print("런처 종료 — 워커와 모니터는 독립 실행 중")

# 런처 즉시 종료 (이게 핵심: 런처가 죽어도 워커는 살아있어야 함)
os._exit(0)
