#!/usr/bin/env python3
"""
session_resume.py — SessionStart Hook
SESSION_STATE.json 읽어서 이전 세션 컨텍스트를 Claude stdout으로 주입.
기존 security_check.py / model_advisor.py와 별도 파일 유지.
"""
import json
from pathlib import Path

STATE_FILE = Path(r"Q:\Claudework\bridge base\.claude\SESSION_STATE.json")


def main():
    if not STATE_FILE.exists():
        print("=== 세션 시작 (이전 상태 없음) ===")
        return

    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        print("=== 세션 시작 (상태 파일 읽기 실패) ===")
        return

    last_updated  = state.get("last_updated", "알 수 없음")
    last_cmd      = state.get("last_command", "")
    git_head      = state.get("git_head", "")
    files         = state.get("modified_files", [])
    task          = state.get("current_task", "")
    git_changed   = state.get("git_changed", [])

    lines = [
        "=" * 50,
        f"이전 세션 마지막 작업: {last_updated}",
    ]
    if task:
        lines.append(f"현재 태스크: {task}")
    if git_head:
        lines.append(f"git HEAD: {git_head}")
    if last_cmd:
        lines.append(f"마지막 명령: {last_cmd}")
    if files:
        lines.append(f"수정된 파일 ({len(files)}개): {', '.join(files[-5:])}")
    if git_changed:
        lines.append(f"커밋 안된 변경: {', '.join(git_changed[:5])}")
    lines.append("=" * 50)

    print("\n".join(lines))


if __name__ == "__main__":
    main()
