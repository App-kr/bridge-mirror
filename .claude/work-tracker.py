"""
Bridge Work Tracker - 5min interval auto work logging (Python edition)
=======================================================================
2026-05-01: PowerShell version was spawning git+conhost (27 per run)
            even with Process.Start CreateNoWindow=true.
            Python subprocess + creationflags=CREATE_NO_WINDOW fully works.

Same logic as work-tracker.ps1 but zero conhost flicker.
"""
from __future__ import annotations
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(r"Q:\Claudework\bridge base")
LOG_FILE = REPO / ".claude" / "work-log.txt"
MAX_LOG_LINES = 500

NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def git(args: list[str]) -> str:
    try:
        r = subprocess.run(
            ["git"] + args,
            cwd=str(REPO),
            capture_output=True, text=True, timeout=5,
            encoding="utf-8", errors="replace",
            creationflags=NO_WINDOW,
        )
        return (r.stdout or "").strip()
    except Exception:
        return ""


def main():
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    last_commit = git(["log", "-1", "--format=%s"])
    last_commit_time = git(["log", "-1", "--format=%ar"])
    modified = [l for l in git(["diff", "--name-only"]).splitlines() if l]
    untracked = [l for l in git(["ls-files", "--others", "--exclude-standard"]).splitlines() if l]
    staged = [l for l in git(["diff", "--cached", "--name-only"]).splitlines() if l]

    total_changed = len(modified) + len(untracked) + len(staged)

    last_commit_epoch = git(["log", "-1", "--format=%ct"])
    now_epoch = int(time.time())
    if last_commit_epoch and last_commit_epoch.isdigit():
        minutes_ago = round((now_epoch - int(last_commit_epoch)) / 60)
    else:
        minutes_ago = 9999

    # 1시간 이내 커밋이 있거나 수정 파일이 있으면 기록
    if minutes_ago > 60 and total_changed == 0:
        return

    # 작업명 추정
    if total_changed > 0:
        all_files = modified + untracked + staged
        top_file = all_files[0] if all_files else ""
        others = total_changed - 1
        work_name = f"editing: {top_file} (+{others} files)"
    elif last_commit:
        work_name = f"last: {last_commit}"
    else:
        work_name = "idle"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"[{timestamp}] Branch:{branch} | {work_name} | "
        f"commit:{last_commit_time} | changed:{total_changed}"
    )

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(entry + "\n")

    # 로그 크기 제한
    try:
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_LOG_LINES:
            LOG_FILE.write_text(
                "\n".join(lines[-MAX_LOG_LINES:]) + "\n",
                encoding="utf-8",
            )
    except Exception:
        pass


if __name__ == "__main__":
    main()
