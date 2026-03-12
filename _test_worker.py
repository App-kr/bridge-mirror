import time, json, os
from pathlib import Path

state = Path(r"Q:\Claudework\bridge base\_test_state.json")
pid = os.getpid()

for i in range(20):
    state.write_text(json.dumps({"tick": i, "pid": pid}), encoding="utf-8")
    time.sleep(1)

state.write_text(json.dumps({"tick": "DONE", "pid": pid}), encoding="utf-8")
