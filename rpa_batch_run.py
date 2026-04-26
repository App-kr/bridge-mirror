"""
RPA 배치 실행 — 전 계정 순차 실행
라운드 1: 4개 계정 × 3건
5분 휴식
라운드 2: 4개 계정 × 2건
"""
import subprocess
import sys
import time
import threading
from pathlib import Path
from datetime import datetime

PYTHON   = r"Q:\Phtyon 3\python.exe"
SCRIPT   = str(Path(__file__).parent / "craigslist_auto_rpa.py")
ACCOUNTS = ["account4", "account1", "account3", "account2"]
TAGS     = {"account4": "GRAY", "account1": "GREEN", "account3": "BROWN", "account2": "PURPLE"}
LOG_FILE = Path(__file__).parent / "logs" / "rpa_batch.log"

ROUNDS = [
    {"limit": 3, "label": "라운드 1 (3건씩)"},
    {"limit": 2, "label": "라운드 2 (2건씩)"},
]
REST_BETWEEN_ROUNDS = 300   # 5분
REST_BETWEEN_ACCOUNTS = 10  # 계정 간 대기 (Chrome 정리 + DLL 초기화 시간)


def ts():
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str):
    line = f"[{ts()}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_account(account_id: str, limit: int):
    tag = TAGS.get(account_id, account_id)
    log(f"▶ {tag} ({account_id}) — {limit}건 시작")

    proc = subprocess.Popen(
        [PYTHON, "-X", "utf8", "-u", SCRIPT,
         "--headless", "--account", account_id,
         "--limit", str(limit), "--no-overlay"],
        cwd=str(Path(SCRIPT).parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        # CREATE_NO_WINDOW: 창 없이 실행. 단, Chrome DLL 초기화에 시간 필요 → 계정 간 딜레이 필수
        creationflags=subprocess.CREATE_NO_WINDOW,
        text=True, encoding="utf-8", errors="replace",
        bufsize=1,
    )

    for line in proc.stdout:
        line = line.rstrip("\r\n")
        if line:
            log(f"  [{tag}] {line}")

    proc.wait()
    rc = proc.returncode
    if rc != 0:
        # 0xC0000142 = DLL 초기화 실패 (Chrome 잔류 프로세스 충돌)
        # 0x40010004 = Ctrl+C / 비정상 종료
        hex_rc = f"0x{rc & 0xFFFFFFFF:08X}" if rc < 0 else f"0x{rc:08X}"
        log(f"■ {tag} 완료 (exit {rc} / {hex_rc}) ← 비정상 종료")
    else:
        log(f"■ {tag} 완료 (exit 0)")
    # Chrome cleanup 대기 — DLL 해제 후 다음 계정 안전 시작
    time.sleep(REST_BETWEEN_ACCOUNTS)


def countdown(seconds: int, label: str):
    for remaining in range(seconds, 0, -1):
        print(f"\r  [{ts()}] {label} — {remaining}초 남음   ", end="", flush=True)
        time.sleep(1)
    print()
    log(f"{label} 완료")


def main():
    LOG_FILE.parent.mkdir(exist_ok=True)
    log("=" * 50)
    log("BRIDGE RPA 배치 실행 시작")
    log("  라운드 1: 4계정 × 3건")
    log("  5분 휴식")
    log("  라운드 2: 4계정 × 2건")
    log("=" * 50)

    for r_idx, rnd in enumerate(ROUNDS):
        if r_idx > 0:
            log(f"\n--- 라운드 간 {REST_BETWEEN_ROUNDS//60}분 휴식 시작 ---")
            countdown(REST_BETWEEN_ROUNDS, "라운드 간 휴식")

        log(f"\n{'─'*40}")
        log(f"  {rnd['label']} 시작")
        log(f"{'─'*40}")

        for a_idx, acct in enumerate(ACCOUNTS):
            run_account(acct, rnd["limit"])
            # 마지막 계정은 불필요한 대기 생략
            if a_idx == len(ACCOUNTS) - 1:
                time.sleep(0)  # 루프 내 sleep은 run_account 끝에서 이미 처리됨

    log(f"\n{'='*50}")
    log("전체 완료")
    log(f"{'='*50}")


if __name__ == "__main__":
    main()
