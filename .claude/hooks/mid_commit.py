#!/usr/bin/env python3
"""
mid_commit.py — PostToolUse Hook
Write/Edit/Bash 도구 5회마다 자동 git add -A && commit "auto: mid-session [timestamp]"
카운터: Q:\Claudework\bridge base\.claude\hook_counter.json
세션 상태: Q:\Claudework\bridge base\.claude\SESSION_STATE.json
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

COUNTER_FILE = Path(r"Q:\Claudework\bridge base\.claude\hook_counter.json")
STATE_FILE   = Path(r"Q:\Claudework\bridge base\.claude\SESSION_STATE.json")
REPO_DIR     = Path(r"Q:\Claudework")
THRESHOLD    = 5
TRACKED      = {"Write", "Edit", "MultiEdit", "Bash"}


# ── helpers ───────────────────────────────────────────────────

def _load(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def _save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _git_head() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(REPO_DIR), timeout=5
        )
        return r.stdout.strip()
    except Exception:
        return ""


def _git_changed_files() -> list[str]:
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=str(REPO_DIR), timeout=5
        )
        return [l for l in r.stdout.strip().splitlines() if l]
    except Exception:
        return []


def _workstate_task() -> str:
    """work_state.md 에서 현재 태스크 첫 줄 읽기."""
    ws = Path(r"Q:\Claudework\bridge base\.claude\work_state.md")
    if not ws.exists():
        return ""
    try:
        text = ws.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("##") and "완료" not in line and "이전" not in line:
                return line.lstrip("#").strip()
    except Exception:
        pass
    return ""


# ── session state update ──────────────────────────────────────

def update_state(tool_name: str, tool_input: dict):
    state = _load(STATE_FILE, {})

    last_cmd = ""
    if tool_name == "Bash" and isinstance(tool_input, dict):
        last_cmd = tool_input.get("command", "")[:200]
    elif tool_name in ("Write", "Edit", "MultiEdit") and isinstance(tool_input, dict):
        last_cmd = f"{tool_name}: {tool_input.get('file_path', '')}"

    # 수정된 파일 누적 (최대 20개)
    files: list = state.get("modified_files", [])
    if tool_name in ("Write", "Edit", "MultiEdit") and isinstance(tool_input, dict):
        fp = tool_input.get("file_path", "")
        if fp and fp not in files:
            files = (files + [fp])[-20:]

    state.update({
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_tool": tool_name,
        "last_command": last_cmd,
        "git_head": _git_head(),
        "modified_files": files,
        "current_task": _workstate_task(),
        "git_changed": _git_changed_files(),
    })
    _save(STATE_FILE, state)


# ── auto commit ───────────────────────────────────────────────

def auto_commit():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        subprocess.run(["git", "add", "-A"], cwd=str(REPO_DIR), timeout=15, capture_output=True)
        r = subprocess.run(
            ["git", "commit", "-m", f"auto: mid-session {ts}"],
            cwd=str(REPO_DIR), timeout=15, capture_output=True, text=True
        )
        if r.returncode == 0:
            print(f"[mid_commit] 자동 커밋: mid-session {ts}", file=sys.stderr)
    except Exception as e:
        print(f"[mid_commit] 오류: {e}", file=sys.stderr)


# ── main ──────────────────────────────────────────────────────

def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    tool_name  = data.get("tool_name", data.get("tool", ""))
    tool_input = data.get("tool_input", {})

    # 세션 상태 항상 업데이트
    update_state(tool_name, tool_input)

    # 카운터는 추적 도구만
    if tool_name not in TRACKED:
        return

    counter = _load(COUNTER_FILE, {"count": 0})
    counter["count"] = counter.get("count", 0) + 1

    if counter["count"] >= THRESHOLD:
        auto_commit()
        counter["count"] = 0

    _save(COUNTER_FILE, counter)


if __name__ == "__main__":
    main()
