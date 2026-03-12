import subprocess, sys, os, time, json
from pathlib import Path

pythonw = str(Path(sys.executable).with_name("pythonw.exe"))
worker  = str(Path(r"Q:\Claudework\bridge base\_test_worker.py"))
state   = Path(r"Q:\Claudework\bridge base\_test_state.json")

# 이전 상태 파일 초기화
if state.exists():
    state.unlink()

task_name = "BridgeDetachTest001"
cmd_tr    = f'"{pythonw}" "{worker}"'

# 기존 태스크 삭제 후 재생성
subprocess.run(
    ['schtasks', '/delete', '/f', '/tn', task_name],
    creationflags=subprocess.CREATE_NO_WINDOW,
    capture_output=True
)
result_create = subprocess.run(
    ['schtasks', '/create', '/f',
     '/tn', task_name,
     '/tr', cmd_tr,
     '/sc', 'once',
     '/st', '00:00'],
    creationflags=subprocess.CREATE_NO_WINDOW,
    capture_output=True, text=True
)
result_run = subprocess.run(
    ['schtasks', '/run', '/tn', task_name],
    creationflags=subprocess.CREATE_NO_WINDOW,
    capture_output=True, text=True
)

print(f"CREATE: {result_create.returncode} | {result_create.stdout.strip()} {result_create.stderr.strip()}")
print(f"RUN:    {result_run.returncode}    | {result_run.stdout.strip()} {result_run.stderr.strip()}")
print("Launcher exiting in 2s...")
time.sleep(2)
os._exit(0)
