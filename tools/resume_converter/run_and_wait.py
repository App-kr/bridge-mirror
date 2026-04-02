"""launcher를 8초간 실행하고 결과 확인"""
import subprocess
import time
from pathlib import Path

LOG = Path(r"Q:\Claudework\bridge base\tools\resume_converter\logs\diag.log")

# 실행 전 마지막 라인 수 기록
before_lines = len(LOG.read_text(encoding="utf-8").splitlines()) if LOG.exists() else 0

proc = subprocess.Popen([
    r"Q:\Phtyon 3\python.exe",
    r"Q:\Claudework\bridge base\tools\resume_converter\launcher.py"
])
print(f"PID={proc.pid}")

time.sleep(30)

# 결과 확인
if LOG.exists():
    lines = LOG.read_text(encoding="utf-8").splitlines()
    new_lines = lines[before_lines:]
    print("--- new diag.log entries ---")
    for l in new_lines:
        print(l)
else:
    print("diag.log not found")

# 프로세스 종료
proc.terminate()
print("process terminated")
