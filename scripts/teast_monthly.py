"""
teast_monthly.py — Teast 구인공고 월간 자동 재게시 스케줄러
============================================================

매월 특정 날짜(기본: 1일 09:00)에 teast_repost.py 를 자동 실행.

실행:
  python teast_monthly.py              # 무한 루프 (매시 정각 체크)
  python teast_monthly.py --once       # 즉시 1회 실행 (날짜 무관)
  python teast_monthly.py --day 15     # 매월 15일 실행 (기본: 1일)
  python teast_monthly.py --hour 10    # 오전 10시 실행 (기본: 9시)
  python teast_monthly.py --once --live  # 즉시 실제 게시

Windows 작업 스케줄러 등록 (1회성 실행용):
  schtasks /create /tn "TeastMonthly" /tr "python scripts\\teast_monthly.py --once --live" /sc monthly /d 1 /st 09:00 /f
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR  = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR.parent / "tools"
# _teast_build_post.py: 실제 작동 확인된 포스팅 스크립트
SCRIPT    = TOOLS_DIR / "_teast_build_post.py"

LOGS_DIR  = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE  = LOGS_DIR / "teast_scheduler.log"


def _log(msg: str):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_repost(live: bool = False, extra_args: list = None) -> int:
    """teast_repost.py 실행."""
    cmd = [sys.executable, str(SCRIPT)]
    if live:
        cmd.append("--live")
    if extra_args:
        cmd.extend(extra_args)

    _log(f"실행: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, timeout=300)
        _log(f"완료 (returncode={result.returncode})")
        return result.returncode
    except subprocess.TimeoutExpired:
        _log("타임아웃 (5분 초과) — 강제 종료")
        return 1
    except Exception as e:
        _log(f"실행 오류: {e}")
        return 1


def main():
    ap = argparse.ArgumentParser(description="Teast 월간 재게시 스케줄러")
    ap.add_argument("--once",  action="store_true",
                    help="즉시 1회 실행 (날짜/시각 무관)")
    ap.add_argument("--day",   type=int, default=1,
                    help="매월 실행 날짜 (기본: 1일)")
    ap.add_argument("--hour",  type=int, default=9,
                    help="실행 시각 (기본: 9시)")
    ap.add_argument("--live",  action="store_true",
                    help="실제 게시 모드 (미설정 시 Draft)")
    ap.add_argument("--headless", action="store_true",
                    help="헤드리스 Chrome 사용")
    args = ap.parse_args()

    extra = []
    if args.headless:
        extra.append("--headless")

    if args.once:
        _log("--once 모드: 즉시 실행")
        rc = run_repost(live=args.live, extra_args=extra)
        sys.exit(rc)

    # ── 무한 루프 스케줄 ──────────────────────────────────────────────────────
    _log(f"월간 스케줄러 시작 — 매월 {args.day}일 {args.hour:02d}:00 실행")
    _log(f"모드: {'LIVE (실제 게시)' if args.live else 'DRAFT'}")
    _log("Ctrl+C 로 종료")

    last_run_month = -1

    while True:
        now = datetime.now()
        if (now.day == args.day
                and now.hour == args.hour
                and now.month != last_run_month):
            _log(f"스케줄 트리거: {now.strftime('%Y-%m-%d %H:%M')}")
            run_repost(live=args.live, extra_args=extra)
            last_run_month = now.month

        # 1분마다 체크
        time.sleep(60)


if __name__ == "__main__":
    main()
