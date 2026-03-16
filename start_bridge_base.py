"""
Bridge Base 전체 시작 스크립트
================================
텔레그램 봇 + Gmail 워처 백그라운드 동시 실행

사용: python start_bridge_base.py
     pythonw.exe start_bridge_base.py  ← 창 없이
"""
import subprocess
import sys
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON    = str(Path(sys.executable).parent / "pythonw.exe")
PYTHONW   = PYTHON if Path(PYTHON).exists() else sys.executable
LOGS      = PROJECT_ROOT / "logs"
LOGS.mkdir(exist_ok=True)

FLAGS = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS


def is_running(pid_file: Path) -> bool:
    if not pid_file.exists():
        return False
    try:
        import ctypes
        pid = int(pid_file.read_text().strip())
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
            return True
    except Exception:
        pass
    return False


def start_process(name: str, cmd: list, log_name: str, pid_file: Path) -> int:
    log_path = LOGS / log_name
    proc = subprocess.Popen(
        cmd,
        stdout=open(str(log_path), "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        cwd=str(PROJECT_ROOT),
        creationflags=FLAGS,
    )
    pid_file.write_text(str(proc.pid))
    print(f"[{name}] 시작 PID={proc.pid} | 로그: logs/{log_name}")
    return proc.pid


def main():
    print("=" * 50)
    print("Bridge Base 시작")
    print("=" * 50)

    # 1. 텔레그램 봇
    bot_pid = LOGS / "telegram_bot.pid"
    if is_running(bot_pid):
        print(f"[Bot] 이미 실행 중 (PID: {bot_pid.read_text().strip()})")
    else:
        start_process(
            "Telegram Bot",
            [PYTHONW, "-X", "utf8", "-m", "telegram_agent"],
            "telegram_bot.log",
            bot_pid,
        )

    # 2. Gmail 워처
    watcher_pid = LOGS / "gmail_watcher.pid"
    if is_running(watcher_pid):
        print(f"[Watcher] 이미 실행 중 (PID: {watcher_pid.read_text().strip()})")
    else:
        start_process(
            "Gmail Watcher",
            [PYTHONW, "-X", "utf8", str(PROJECT_ROOT / "tools" / "gmail_error_watcher.py")],
            "gmail_watcher.log",
            watcher_pid,
        )

    print()
    print("모두 시작됨. 로그 위치: logs/")
    print("  telegram_bot.log  — 봇 로그")
    print("  gmail_watcher.log — Gmail 모니터 로그")
    print()
    print("중지: python stop_bridge_base.py")


if __name__ == "__main__":
    main()
