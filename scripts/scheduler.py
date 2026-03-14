"""
BRIDGE Multi-Account Scheduler
================================
계정별 시간대에 따라 craigslist_auto_rpa.py 를 자동 실행.
4시간 쿨다운: 수동 실행 후 4시간 내 자동 실행 건너뜀.

  account1: Coreabridge@gmail.com   → 01, 07, 13, 19시
  account2: airelair00@gmail.com    → 03, 09, 15, 21시
  account3: ferrari812fast@gmail.com → 05, 11, 17, 23시

실행:
  python scheduler.py              # 무한 루프 — 매시 정각 체크
  python scheduler.py --once       # 현재 시간에 해당하는 계정 1회만 실행
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
COOLDOWN_FILE = BASE_DIR / "logs" / ".last_run.json"
LOCK_FILE = BASE_DIR / "logs" / ".rpa_running.lock"
COOLDOWN_HOURS = 4

ACCOUNTS = {
    "account1": [1, 7, 13, 19],
    "account2": [3, 9, 15, 21],
    "account3": [5, 11, 17, 23],
}


def _load_last_run() -> dict:
    if COOLDOWN_FILE.exists():
        try:
            return json.loads(COOLDOWN_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def stamp_run(account_id: str):
    """계정 실행 타임스탬프 기록 (수동/자동 공통)."""
    data = _load_last_run()
    data[account_id] = datetime.now().isoformat()
    COOLDOWN_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOLDOWN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_cooldown(account_id: str) -> bool:
    """4시간 내 실행 이력이 있으면 True."""
    data = _load_last_run()
    last = data.get(account_id)
    if not last:
        return False
    try:
        last_dt = datetime.fromisoformat(last)
        return datetime.now() - last_dt < timedelta(hours=COOLDOWN_HOURS)
    except Exception:
        return False


def is_rpa_running() -> bool:
    """다른 RPA 프로세스가 이미 실행 중인지 확인."""
    if not LOCK_FILE.exists():
        return False
    try:
        import ctypes
        pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            LOCK_FILE.unlink(missing_ok=True)
            return False
        exit_code = ctypes.c_ulong()
        kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
        kernel32.CloseHandle(handle)
        if exit_code.value == STILL_ACTIVE:
            return True
        LOCK_FILE.unlink(missing_ok=True)
        return False
    except Exception:
        LOCK_FILE.unlink(missing_ok=True)
        return False


def get_due_accounts(hour: int) -> list[str]:
    """현재 시(hour)에 실행해야 할 계정 목록."""
    return [acct for acct, hours in ACCOUNTS.items() if hour in hours]


def run_account(account_id: str, limit: int = 10):
    """계정별 RPA 실행."""
    if is_rpa_running():
        print(f"[SCHEDULER] RPA 이미 실행 중 — {account_id} 건너뜀")
        return 0

    cmd = [
        sys.executable, str(BASE_DIR / "craigslist_auto_rpa.py"),
        "--account", account_id,
        "--headless",
        "--limit", str(limit),
    ]
    print(f"\n{'='*55}")
    print(f"[SCHEDULER] {account_id} 실행: {' '.join(cmd)}")
    print(f"{'='*55}")

    result = subprocess.run(cmd, cwd=str(BASE_DIR), timeout=1800)
    stamp_run(account_id)
    return result.returncode


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BRIDGE Multi-Account Scheduler")
    parser.add_argument("--once", action="store_true", help="현재 시간 기준 1회만 실행")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    if args.once:
        hour = datetime.now().hour
        due = get_due_accounts(hour)
        if not due:
            print(f"[SCHEDULER] {hour}시 — 실행 대상 계정 없음")
            return
        for acct in due:
            if is_cooldown(acct):
                print(f"[SCHEDULER] {acct} — 4시간 쿨다운 중 (건너뜀)")
                continue
            run_account(acct, args.limit)
        return

    # 무한 루프 — 매시 정각 체크
    print("[SCHEDULER] 다중 계정 스케줄러 시작 (Ctrl+C 로 종료)")
    print(f"  account1: 01,07,13,19시")
    print(f"  account2: 03,09,15,21시")
    print(f"  account3: 05,11,17,23시")
    print(f"  쿨다운  : 4시간 (수동 실행 후 자동 건너뜀)")

    last_run_hour = -1
    while True:
        now = datetime.now()
        hour = now.hour

        if hour != last_run_hour:
            due = get_due_accounts(hour)
            if due:
                for acct in due:
                    if is_cooldown(acct):
                        print(f"[SCHEDULER] {acct} — 4시간 쿨다운 중 (건너뜀)")
                        continue
                    try:
                        run_account(acct, args.limit)
                    except Exception as e:
                        print(f"[SCHEDULER ERROR] {acct}: {e}")
                last_run_hour = hour
            else:
                last_run_hour = hour

        # 60초마다 체크
        time.sleep(60)


if __name__ == "__main__":
    main()
