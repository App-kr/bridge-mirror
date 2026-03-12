# -*- coding: utf-8 -*-
"""
BRIDGE Craigslist RPA — 콘솔 모니터
Worker(pythonw.exe)와 완전히 분리된 별도 프로세스.
이 창을 닫아도 실제 RPA는 계속 실행됩니다.
"""
import json, time, sys
from pathlib import Path

STATE = Path(r"Q:\Claudework\bridge base\overlay_state.json")

print("=" * 55)
print("  BRIDGE Craigslist RPA Running...")
print("  Close this window anytime - RPA continues")
print("=" * 55)

# 상태 파일이 생성될 때까지 대기
for _ in range(10):
    if STATE.exists():
        break
    print("  대기 중...", end="\r", flush=True)
    time.sleep(1)

started = None
while True:
    try:
        s = json.loads(STATE.read_text(encoding="utf-8"))
        status  = s.get("status", "")
        done    = s.get("done", 0)
        total   = s.get("total", 0)
        success = s.get("success", 0)
        cur     = s.get("current", "")[:45]
        acct    = s.get("account", "")

        if started is None and s.get("started"):
            started = s["started"]
            print(f"\n  Started : {started}")
            print(f"  Account : {acct}")
            print(f"  Limit   : {total} posts")
            print("-" * 55)

        bar_fill = int(30 * done / total) if total > 0 else 0
        bar = "#" * bar_fill + "-" * (30 - bar_fill)
        print(f"\r  [{bar}] {done}/{total}  OK={success}  {cur}  ", end="", flush=True)

        if status == "done":
            print(f"\n{'=' * 55}")
            print(f"  완료: {success}/{total}건 게시 성공")
            print(f"{'=' * 55}")
            break
    except Exception:
        pass
    time.sleep(1)

input("\n  Press Enter to close...")
