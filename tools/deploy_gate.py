"""
배포 게이트 — git push 전 승인 대기
========================================
1단계: 터미널에서 3분(180초) 대기 (화살표 키 선택 메뉴)
2단계: 응답 없으면 텔레그램으로 알림 후 대기

사용법:
  python tools/deploy_gate.py          ← pre-push 훅 자동 호출
  python tools/deploy_gate.py --force  ← 승인 없이 즉시 통과
"""

import json
import os
import sys
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

TG_TOKEN         = os.getenv("TELEGRAM_BOT_TOKEN", "")
DB_PATH          = PROJECT_ROOT / "master.db"
STATE_FILE       = PROJECT_ROOT / "logs" / "deploy_request.json"
SKIP_FILE        = PROJECT_ROOT / "logs" / "deploy_skip.json"   # "이번 세션 묻지마" 플래그
TERMINAL_TIMEOUT = int(os.getenv("DEPLOY_TERMINAL_TIMEOUT", "180"))  # 터미널 대기 (초, 기본 3분)
TG_TIMEOUT       = int(os.getenv("DEPLOY_TG_TIMEOUT", "600"))         # 텔레 대기 (초)
TERMINAL_NAME    = os.getenv("TERMINAL_NAME", "Claude Code")

(PROJECT_ROOT / "logs").mkdir(exist_ok=True)


# ── Session-skip helper ────────────────────────────────────────────────────

def is_skip_active() -> bool:
    """'이번 세션 묻지마' 플래그가 유효한지 확인 (8시간 유효)."""
    try:
        data = json.loads(SKIP_FILE.read_text(encoding="utf-8"))
        expire = data.get("expire", 0)
        return time.time() < expire
    except Exception:
        return False


def set_skip():
    """'이번 세션 묻지마' 플래그 저장 (8시간)."""
    SKIP_FILE.write_text(
        json.dumps({"expire": time.time() + 8 * 3600, "set_at": datetime.now().isoformat()}),
        encoding="utf-8"
    )


# ── Telegram ───────────────────────────────────────────────────────────────

def tg_send(chat_id: int, text: str) -> bool:
    if not TG_TOKEN:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4000], "parse_mode": "HTML"},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def get_subscribers() -> list[int]:
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute(
            "SELECT chat_id FROM tg_alert_subscribers WHERE active=1"
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


# ── Git info ───────────────────────────────────────────────────────────────

def get_commit_info() -> dict:
    def run(cmd):
        return subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT), encoding="utf-8"
        ).stdout.strip()

    commits = run(["git", "log", "origin/main..HEAD", "--oneline"]).splitlines()
    files   = run(["git", "diff", "origin/main..HEAD", "--name-only"]).splitlines()
    latest  = run(["git", "log", "-1", "--pretty=%s"])
    branch  = run(["git", "branch", "--show-current"]) or "main"

    return {
        "commits":      commits[:5],
        "files":        files[:8],
        "latest_msg":   latest or "변경사항",
        "branch":       branch,
        "commit_count": len(commits),
        "file_count":   len(files),
    }


# ── State ──────────────────────────────────────────────────────────────────

def write_state(request_id: str, info: dict):
    STATE_FILE.write_text(
        json.dumps({
            "request_id": request_id,
            "status":     "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "info":       info,
        }, ensure_ascii=False),
        encoding="utf-8"
    )


def read_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def clear_state():
    try:
        STATE_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ── Interactive arrow-key menu (Windows) ───────────────────────────────────

_ANSI_UP    = "\033[A"
_ANSI_CLEAR = "\033[J"
_GREEN      = "\033[32m"
_RESET      = "\033[0m"


def _render(option_lines: list[list[str]], selected: int, redraw: bool):
    """
    option_lines: list of [line1, line2, ...] per option
    각 옵션은 여러 줄일 수 있음.
    """
    # 총 출력 줄 수 계산
    total_lines = sum(len(ls) for ls in option_lines)

    if redraw:
        # 커서를 total_lines 위로 올리고 이후 지우기
        sys.stdout.write(f"\033[{total_lines}A{_ANSI_CLEAR}")

    for i, lines in enumerate(option_lines):
        for j, line in enumerate(lines):
            if j == 0:
                prefix = f" {_GREEN}❯{_RESET}" if i == selected else "  "
                sys.stdout.write(f"{prefix} {i+1}. {line}\n")
            else:
                sys.stdout.write(f"      {line}\n")

    sys.stdout.flush()


def interactive_menu(timeout: int, info: dict) -> str | None:
    """
    화살표 키 선택 메뉴.
    반환값: 'yes' | 'yes_always' | 'no' | None(타임아웃)
    """
    try:
        import msvcrt
    except ImportError:
        return _plain_input(timeout)

    proj_short = str(PROJECT_ROOT).replace("\\", "/")
    option_lines = [
        ["Yes"],
        [
            "Yes, and don't ask again for",
            f"python commands in",
            f"{proj_short}",
        ],
        ["No"],
    ]
    choices = ["yes", "yes_always", "no"]

    selected = 0

    sys.stdout.write(f"\nDo you want to proceed?\n")
    _render(option_lines, selected, redraw=False)

    deadline = time.time() + timeout

    while time.time() < deadline:
        if msvcrt.kbhit():
            ch = msvcrt.getwch()

            if ch in ('\x00', '\xe0'):          # 확장키 (화살표)
                ch2 = msvcrt.getwch()
                if ch2 == 'H':                  # 위 화살표
                    selected = (selected - 1) % len(choices)
                    _render(option_lines, selected, redraw=True)
                elif ch2 == 'P':                # 아래 화살표
                    selected = (selected + 1) % len(choices)
                    _render(option_lines, selected, redraw=True)

            elif ch == '\r':                    # Enter
                sys.stdout.write("\n")
                return choices[selected]

            elif ch in ('1', '2', '3'):         # 숫자 직접 입력
                idx = int(ch) - 1
                if 0 <= idx < len(choices):
                    selected = idx
                    _render(option_lines, selected, redraw=True)
                    sys.stdout.write("\n")
                    return choices[selected]

            elif ch.lower() == 'y':
                sys.stdout.write("\n")
                return "yes"

            elif ch.lower() == 'n':
                sys.stdout.write("\n")
                return "no"

        time.sleep(0.05)

    sys.stdout.write("\n")
    return None  # 타임아웃


def _plain_input(timeout: int) -> str | None:
    """비-Windows 폴백: 텍스트 입력."""
    import threading
    result = [None]

    def _read():
        try:
            ans = input("yes/no: ").strip().lower()
            result[0] = "yes" if ans in ("yes", "y") else "no" if ans in ("no", "n") else None
        except Exception:
            pass

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    t.join(timeout)
    return result[0]


# ── Telegram message ───────────────────────────────────────────────────────

def build_tg_msg(info: dict) -> str:
    files_str = "\n".join(f"  • {f}" for f in info["files"]) or "  (없음)"
    time_str  = datetime.now().strftime("%H:%M")
    return (
        f"🟡 [중요] 💬 <b>{TERMINAL_NAME}에서 배포 승인 요청</b> ({time_str})\n\n"
        f"📝 \"{info['latest_msg']}\"\n\n"
        f"📁 변경 파일 {info['file_count']}개:\n{files_str}\n\n"
        f"배포할까요?\n"
        f"✅ <b>yes</b> 또는 <b>/yes</b> — 배포 진행\n"
        f"❌ <b>no</b> 또는 <b>/no</b>   — 취소"
    )


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    if "--force" in sys.argv:
        print("[deploy_gate] --force 통과")
        sys.exit(0)

    # "이번 세션 묻지마" 플래그 확인
    if is_skip_active():
        print("[deploy_gate] ✅ 세션 스킵 활성 — 묻지 않고 push 진행")
        sys.exit(0)

    info = get_commit_info()
    if info["commit_count"] == 0:
        print("[deploy_gate] push할 커밋 없음 — 통과")
        sys.exit(0)

    # ── 1단계: 터미널 대기 ────────────────────────────────
    terminal_ans = interactive_menu(TERMINAL_TIMEOUT, info)

    if terminal_ans == "yes":
        print("[deploy_gate] ✅ 터미널 승인 — push 진행")
        sys.exit(0)

    elif terminal_ans == "yes_always":
        set_skip()
        print("[deploy_gate] ✅ 터미널 승인 (8시간 스킵 설정) — push 진행")
        sys.exit(0)

    elif terminal_ans == "no":
        print("[deploy_gate] ❌ 터미널 거부 — push 취소")
        sys.exit(1)

    # ── 2단계: 텔레그램 알림 ─────────────────────────────
    print(f"\n[deploy_gate] 터미널 응답 없음 → 텔레그램으로 전송 중...")

    subscribers = get_subscribers()
    if not subscribers or not TG_TOKEN:
        print("[deploy_gate] 텔레그램 미설정 — 자동 통과")
        sys.exit(0)

    request_id = str(uuid.uuid4())
    clear_state()
    write_state(request_id, info)

    msg = build_tg_msg(info)
    sent = sum(1 for cid in subscribers if tg_send(cid, msg))

    if sent == 0:
        print("[deploy_gate] 텔레그램 전송 실패 — 자동 통과")
        clear_state()
        sys.exit(0)

    print(f"[deploy_gate] 텔레그램 승인 대기 중 (최대 {TG_TIMEOUT}초) — yes/no 로 응답하세요")

    deadline = time.time() + TG_TIMEOUT
    while time.time() < deadline:
        time.sleep(2)
        status = read_state().get("status", "pending")

        if status == "approved":
            print("[deploy_gate] ✅ 텔레그램 승인 — push 진행")
            for cid in subscribers:
                tg_send(cid, f"✅ 배포 시작!\n\"{info['latest_msg'][:80]}\"")
            clear_state()
            sys.exit(0)

        elif status == "rejected":
            print("[deploy_gate] ❌ 텔레그램 거부 — push 취소")
            clear_state()
            sys.exit(1)

        remaining = int(deadline - time.time())
        if remaining % 120 == 0 and remaining > 0:
            print(f"[deploy_gate] 대기 중... {remaining}초 남음")

    print("[deploy_gate] ⏰ 타임아웃 — push 차단")
    for cid in subscribers:
        tg_send(cid, "⏰ 응답 없음 — 배포 자동 취소됨\n다시 push하면 새로 물어봅니다.")
    clear_state()
    sys.exit(1)


if __name__ == "__main__":
    main()
