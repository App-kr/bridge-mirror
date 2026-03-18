"""
PreCompact 훅 — /compact 실행 전 work_state.md에 현재 상태 저장
Claude Code가 컨텍스트를 압축하기 전에 진행상황을 기록합니다.
"""
import sys, os, json, io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

WORK_STATE = os.path.join(os.path.dirname(__file__), "..", ".claude", "work_state.md")

def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    session_id = data.get("session_id", "unknown")

    # 기존 work_state.md 읽기
    try:
        with open(WORK_STATE, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        content = ""

    # 최근 업데이트 날짜 갱신
    lines = content.splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("최근 업데이트:"):
            new_lines.append(f"최근 업데이트: {now} (PreCompact 자동저장)")
        else:
            new_lines.append(line)

    # PreCompact 기록 추가 (맨 끝에)
    compact_note = f"\n## /compact 실행 기록\n- {now} — 컨텍스트 압축됨 (session: {session_id[:8]})\n"
    updated = "\n".join(new_lines) + compact_note

    with open(WORK_STATE, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"[save_work_state] work_state.md 업데이트: {now}")

if __name__ == "__main__":
    main()
