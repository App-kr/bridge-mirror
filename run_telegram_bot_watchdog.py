"""
텔레그램 봇 워치독 — 봇이 죽으면 자동 재시작
실행: python run_telegram_bot_watchdog.py
"""
import subprocess
import time
import logging
from pathlib import Path

BASE = Path(__file__).resolve().parent
PY   = str(BASE.parent.parent / "Phtyon 3" / "python.exe")
BOT  = str(BASE / "tools" / "tg_commander.py")
LOG  = BASE / "logs" / "watchdog.log"

logging.basicConfig(
    filename=str(LOG),
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

RESTART_DELAY = 10   # 재시작 전 대기(초)
MAX_FAST_CRASH = 5   # 연속 빠른 충돌 감지 횟수
FAST_CRASH_SEC = 30  # 이 시간 내에 종료되면 빠른 충돌

def run():
    consecutive_fast = 0
    while True:
        logging.info("봇 시작")
        start = time.time()
        proc = subprocess.Popen(
            [PY, str(BOT)],
            cwd=str(BASE),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        proc.wait()
        elapsed = time.time() - start
        rc = proc.returncode

        if elapsed < FAST_CRASH_SEC:
            consecutive_fast += 1
            logging.warning(f"빠른 종료 (rc={rc}, {elapsed:.0f}초) — 연속 {consecutive_fast}회")
        else:
            consecutive_fast = 0

        if consecutive_fast >= MAX_FAST_CRASH:
            logging.error(f"연속 {consecutive_fast}회 빠른 충돌 — 60초 대기 후 재시도")
            consecutive_fast = 0
            time.sleep(60)
        else:
            logging.info(f"봇 종료 (rc={rc}) — {RESTART_DELAY}초 후 재시작")
            time.sleep(RESTART_DELAY)

if __name__ == "__main__":
    run()
