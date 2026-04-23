"""
배포 게이트 — git push 전 승인 대기
========================================
- 터미널 + 텔레그램 동시 대기 (먼저 응답한 쪽 채택)
- 터미널 응답 없어도 텔레그램 yes/no 로 원격 승인 가능

사용법:
  python tools/deploy_gate.py          ← pre-push 훅 자동 호출
  python tools/deploy_gate.py --force  ← 승인 없이 즉시 통과
"""

import json
import os
import sys
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

DB_PATH          = PROJECT_ROOT / "master.db"
SKIP_FILE        = PROJECT_ROOT / "deploy_skip.json"
TERMINAL_TIMEOUT = int(os.getenv("DEPLOY_TERMINAL_TIMEOUT", "180"))
TG_TIMEOUT       = int(os.getenv("DEPLOY_TG_TIMEOUT", "600"))
TERMINAL_NAME    = os.getenv("TERMINAL_NAME", "Claude Code")

(PROJECT_ROOT / "logs").mkdir(exist_ok=True)


# ── Token (BX vault 우선, .env 폴백) ─────────────────────────────────────────

def get_token() -> str:
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "tools"))
        from bx import _read as bx_read
        t = bx_read("TELEGRAM_BOT_TOKEN")
        if t:
            return t
    except Exception:
        pass
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


# ── Session-skip helper ────────────────────────────────────────────────────

def is_skip_active() -> bool:
    try:
        data = json.loads(SKIP_FILE.read_text(encoding="utf-8"))
        return time.time() < data.get("expire", 0)
    except Exception:
        return False


def set_skip():
    SKIP_FILE.write_text(
        json.dumps({"expire": time.time() + 8 * 3600, "set_at": datetime.now().isoformat()}),
        encoding="utf-8"
    )


# ── Telegram ───────────────────────────────────────────────────────────────

def tg_send(chat_id: int, text: str, token: str) -> bool:
    if not token:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
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


GATE_IPC_FILE = PROJECT_ROOT / ".claude" / "tg_gate_response.json"


def tg_poll_response(token: str, subs: list[int], since_ts: float, deadline: float) -> str | None:
    """
    tg_commander.py가 IPC 파일에 기록한 yes/no 응답을 폴링.
    (직접 getUpdates 대신 파일 기반 IPC — 409 Conflict 방지)
    """
    # 기존 파일 삭제 (이전 응답 오인 방지)
    try:
        if GATE_IPC_FILE.exists():
            data = json.loads(GATE_IPC_FILE.read_text(encoding="utf-8"))
            if data.get("ts", 0) < since_ts:
                GATE_IPC_FILE.unlink()
    except Exception:
        pass

    while time.time() < deadline:
        try:
            if GATE_IPC_FILE.exists():
                data = json.loads(GATE_IPC_FILE.read_text(encoding="utf-8"))
                answer = data.get("answer", "")
                ts = data.get("ts", 0)
                if ts >= since_ts and answer in ("yes", "no"):
                    GATE_IPC_FILE.unlink(missing_ok=True)
                    return answer
        except Exception:
            pass
        time.sleep(2)

    return None


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


# ── Interactive arrow-key menu (Windows) ───────────────────────────────────

_ANSI_UP    = "\033[A"
_ANSI_CLEAR = "\033[J"
_GREEN      = "\033[32m"
_RESET      = "\033[0m"


def _render(option_lines: list[list[str]], selected: int, redraw: bool):
    total_lines = sum(len(ls) for ls in option_lines)
    if redraw:
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
    """화살표 키 선택 메뉴. 반환: 'yes' | 'yes_always' | 'no' | None(타임아웃)"""
    try:
        import msvcrt
    except ImportError:
        return _plain_input(timeout)

    proj_short = str(PROJECT_ROOT).replace("\\", "/")
    option_lines = [
        ["Yes"],
        ["Yes, and don't ask again for", f"python commands in", f"{proj_short}"],
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
            if ch in ('\x00', '\xe0'):
                ch2 = msvcrt.getwch()
                if ch2 == 'H':
                    selected = (selected - 1) % len(choices)
                    _render(option_lines, selected, redraw=True)
                elif ch2 == 'P':
                    selected = (selected + 1) % len(choices)
                    _render(option_lines, selected, redraw=True)
            elif ch == '\r':
                sys.stdout.write("\n")
                return choices[selected]
            elif ch in ('1', '2', '3'):
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
    return None


def _plain_input(timeout: int) -> str | None:
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
        f"✅ <b>yes</b> — 배포 진행\n"
        f"❌ <b>no</b> — 취소"
    )


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    if "--force" in sys.argv:
        print("[deploy_gate] --force 통과")
        sys.exit(0)

    if is_skip_active():
        print("[deploy_gate] ✅ 세션 스킵 활성 — 묻지 않고 push 진행")
        sys.exit(0)

    info = get_commit_info()
    if info["commit_count"] == 0:
        print("[deploy_gate] push할 커밋 없음 — 통과")
        sys.exit(0)

    token       = get_token()
    subscribers = get_subscribers()

    # ── 텔레그램 즉시 발송 ─────────────────────────────────
    tg_sent    = False
    request_ts = time.time()

    if token and subscribers:
        msg  = build_tg_msg(info)
        sent = sum(1 for cid in subscribers if tg_send(cid, msg, token))
        tg_sent = sent > 0
        if tg_sent:
            print(f"[deploy_gate] 📱 텔레그램 알림 발송 완료 — yes/no 로 응답하세요")
        else:
            print("[deploy_gate] 텔레그램 전송 실패")
    else:
        print("[deploy_gate] 텔레그램 미설정 (토큰 또는 구독자 없음)")

    # ── 터미널 + 텔레그램 동시 대기 ───────────────────────
    answer: list[tuple[str, str] | None] = [None]
    lock   = threading.Lock()

    def _terminal():
        a = interactive_menu(TERMINAL_TIMEOUT, info)
        if a is not None:
            with lock:
                if answer[0] is None:
                    answer[0] = ("terminal", a)

    def _telegram():
        if not tg_sent:
            return
        total = TERMINAL_TIMEOUT + TG_TIMEOUT
        a = tg_poll_response(token, subscribers, request_ts, time.time() + total)
        if a is not None:
            with lock:
                if answer[0] is None:
                    answer[0] = ("telegram", a)

    t1 = threading.Thread(target=_terminal, daemon=True)
    t2 = threading.Thread(target=_telegram, daemon=True)
    t1.start()
    t2.start()

    total_deadline = time.time() + TERMINAL_TIMEOUT + TG_TIMEOUT
    while time.time() < total_deadline:
        with lock:
            if answer[0] is not None:
                break
        time.sleep(1)

    # 타임아웃
    if answer[0] is None:
        print("[deploy_gate] ⏰ 타임아웃 — push 차단")
        if tg_sent:
            for cid in subscribers:
                tg_send(cid, "⏰ 응답 없음 — 배포 자동 취소됨\n다시 push하면 새로 물어봅니다.", token)
        sys.exit(1)

    source, choice = answer[0]
    print(f"[deploy_gate] {source} 응답: {choice}")

    if choice == "yes":
        if tg_sent and source == "telegram":
            for cid in subscribers:
                tg_send(cid, f"✅ 배포 시작!\n\"{info['latest_msg'][:80]}\"", token)
        print("[deploy_gate] ✅ 승인 — push 진행")
        sys.exit(0)

    elif choice == "yes_always":
        set_skip()
        print("[deploy_gate] ✅ 승인 (8시간 스킵 설정) — push 진행")
        sys.exit(0)

    elif choice == "no":
        if tg_sent and source == "telegram":
            for cid in subscribers:
                tg_send(cid, f"❌ 배포 취소됨", token)
        print("[deploy_gate] ❌ 거부 — push 취소")
        sys.exit(1)

    # 예외: 알 수 없는 응답
    sys.exit(1)


if __name__ == "__main__":
    main()
