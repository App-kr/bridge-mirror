#!/usr/bin/env python3
"""
Bridge 실시간 상태 기록기
- PreToolUse/PostToolUse/Stop 훅에서 호출
- live_status.txt에 현재 Claude 행동 기록
- 별도 터미널에서 Get-Content -Wait로 실시간 감시 가능
"""

import os
import json
import sys
import datetime

STATUS_FILE   = r"Q:\Claudework\bridge base\tasks\live_status.txt"
CURRENT_FILE  = r"Q:\Claudework\bridge base\tasks\current_action.txt"

TOOL_ICONS = {
    "Write":       "✏️  WRITE",
    "Edit":        "🔧 EDIT ",
    "Read":        "📖 READ ",
    "Bash":        "⚙️  BASH ",
    "Grep":        "🔍 GREP ",
    "Glob":        "📂 GLOB ",
    "Task":        "🤖 TASK ",
    "WebFetch":    "🌐 WEB  ",
    "WebSearch":   "🌐 SRCH ",
    "TodoWrite":   "📋 TODO ",
    "TaskCreate":  "📋 TASK+",
    "TaskUpdate":  "📋 TASK~",
}

def get_detail(tool: str, raw_input: str) -> str:
    try:
        inp = json.loads(raw_input)
    except Exception:
        return raw_input[:80]

    if tool in ("Write", "Edit", "Read", "NotebookEdit"):
        path = inp.get("file_path") or inp.get("notebook_path", "")
        return os.path.basename(path) or path

    if tool == "Bash":
        cmd = inp.get("command", "")
        desc = inp.get("description", "")
        if desc:
            return desc[:80]
        return cmd[:80] + ("..." if len(cmd) > 80 else "")

    if tool == "Grep":
        pat  = inp.get("pattern", "")
        path = inp.get("path", ".")
        return f'"{pat}" in {os.path.basename(path) or path}'

    if tool == "Glob":
        return inp.get("pattern", "")

    if tool in ("Task", "TaskCreate", "TaskUpdate"):
        return (inp.get("subject") or inp.get("description") or "")[:80]

    if tool == "WebFetch":
        url = inp.get("url", "")
        return url[:80]

    if tool == "WebSearch":
        return inp.get("query", "")[:80]

    # 기타: 첫 번째 값
    vals = list(inp.values())
    return str(vals[0])[:80] if vals else ""


def write_status(phase: str):
    tool      = os.environ.get("CLAUDE_TOOL_NAME", "")
    raw_input = os.environ.get("CLAUDE_TOOL_INPUT", "{}")
    task_title= os.environ.get("CLAUDE_TASK_TITLE", "")

    ts = datetime.datetime.now().strftime("%H:%M:%S")

    if phase == "STOP":
        icon   = "✅ DONE"
        detail = task_title or "작업 완료"
    elif phase == "START":
        icon   = "🚀 START"
        detail = ""
    else:
        icon   = TOOL_ICONS.get(tool, f"   {tool[:5]}")
        detail = get_detail(tool, raw_input)

    line = f"[{ts}] {icon} | {detail}"

    # 1) 누적 로그 (append)
    try:
        with open(STATUS_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

    # 2) 현재 상태 (overwrite — 가장 최근 1줄만)
    try:
        with open(CURRENT_FILE, "w", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    phase = sys.argv[1].upper() if len(sys.argv) > 1 else "PRE"
    write_status(phase)
