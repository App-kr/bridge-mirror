"""
테스트 3용 워커: pythonw.exe로 실행 (창 없음)
overlay_state.json에 상태를 기록
"""
import time, json, os
from pathlib import Path

STATE = Path(r"Q:\Claudework\bridge base\overlay_state.json")
TOTAL = 10
pid   = os.getpid()

for i in range(1, TOTAL + 1):
    STATE.write_text(json.dumps({
        "status":  "running",
        "done":    i,
        "total":   TOTAL,
        "current": f"항목{i} 처리중",
        "success": i - 1,
        "pid":     pid
    }), encoding="utf-8")
    time.sleep(1)

STATE.write_text(json.dumps({
    "status":  "done",
    "done":    TOTAL,
    "total":   TOTAL,
    "current": "완료",
    "success": TOTAL,
    "pid":     pid
}), encoding="utf-8")
