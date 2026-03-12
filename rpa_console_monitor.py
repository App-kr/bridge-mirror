import json, time, sys
from pathlib import Path

STATE = Path(r"Q:\Claudework\bridge base\overlay_state.json")

print("=" * 50)
print("  BRIDGE RPA Running (background)")
print("  Close this window anytime - RPA continues")
print("=" * 50)

while True:
    try:
        s = json.loads(STATE.read_text(encoding="utf-8"))
        status = s.get("status", "")
        done   = s.get("done", 0)
        total  = s.get("total", 0)
        cur    = s.get("current", "")[:40]
        print(f"\r  [{done}/{total}] {cur}          ", end="", flush=True)
        if status == "done":
            print(f"\n  완료! {s.get('success',0)}건 게시")
            break
    except Exception:
        pass
    time.sleep(1)

input("\nPress Enter to close...")
