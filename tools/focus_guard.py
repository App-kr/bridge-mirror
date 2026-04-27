"""
focus_guard.py — Game-time CMD/PowerShell popup auto-hider
==========================================================

목적:
  게임/풀스크린 앱 실행 중에 부모 모르게 뜨는 cmd/powershell 창을
  포커스 빼앗기 전에 자동 숨김 (SW_HIDE).

동작:
  - 1초 간격으로 가시 윈도우 enumerate
  - 게임 프로세스 (TslGame, Overwatch, LeagueClient 등) 실행 중일 때만 활성
  - 대상: ConsoleWindowClass (cmd/powershell/conhost) + Python console
  - 보호 화이트리스트: 사용자가 직접 띄운 터미널 (Windows Terminal, Anthropic Claude 등)

운용:
  Task Scheduler에 등록 (OnLogon 트리거, pythonw.exe로 실행 — 자기 자신 콘솔 없음)
  로그: Q:\\Claudework\\bridge base\\logs\\focus_guard.jsonl
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────────
GAME_PROCESS_NAMES = {
    "tslgame.exe",          # PUBG
    "overwatch.exe",
    "leagueclient.exe",
    "leagueoflegends.exe",
    "valorant.exe",
    "valorant-win64-shipping.exe",
    "rl.exe",               # Rocket League
    "csgo.exe",
    "cs2.exe",
    "destiny2.exe",
    "starcraft.exe",
    "starcraft2.exe",
    "lostarkclient.exe",
    "blackdesert64.exe",
    "wow.exe",              # WoW
}

# 숨길 대상 윈도우 클래스
TARGET_CLASSES = {
    "ConsoleWindowClass",   # cmd, powershell, conhost
    "PowerShell",
    "PSReadLine",
}

# 숨기지 않을 콘솔 (사용자가 직접 띄운 것)
WHITELIST_TITLE_KEYWORDS = (
    "windows terminal",
    "wt.exe",
    "claude code",          # Claude Code CLI 본체
    "anthropic",
    "chocolatey",           # 사용자 패키지 매니저
    "nodejs cli",
)

# 로그
LOG_DIR = Path(r"Q:\Claudework\bridge base\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "focus_guard.jsonl"

POLL_SEC = 1.0
MAX_LOG_PER_HOUR = 200      # rate-limit 로그 (디스크 보호)


# ── Win32 ──────────────────────────────────────────────────
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
SW_HIDE = 0


def get_window_class(hwnd):
    buf = ctypes.create_unicode_buffer(128)
    user32.GetClassNameW(hwnd, buf, 128)
    return buf.value


def get_window_title(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    if n == 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def get_window_pid(hwnd):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def is_visible(hwnd):
    return bool(user32.IsWindowVisible(hwnd))


def hide_window(hwnd):
    user32.ShowWindow(hwnd, SW_HIDE)


# ── 게임 감지 ──────────────────────────────────────────────
def is_game_running():
    """tasklist 로 게임 프로세스 검사 (CREATE_NO_WINDOW=0x08000000)."""
    import subprocess
    try:
        out = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=4,
            creationflags=0x08000000,
        )
        names_lower = out.stdout.lower()
        for g in GAME_PROCESS_NAMES:
            if g in names_lower:
                return g
    except Exception:
        pass
    return None


# ── 콘솔창 enumerate + 숨김 ─────────────────────────────────
def find_target_windows():
    targets = []

    def cb(hwnd, _):
        try:
            if not is_visible(hwnd):
                return True
            cls = get_window_class(hwnd)
            if cls not in TARGET_CLASSES:
                return True
            title = get_window_title(hwnd).lower()
            for kw in WHITELIST_TITLE_KEYWORDS:
                if kw in title:
                    return True
            targets.append((hwnd, cls, get_window_title(hwnd), get_window_pid(hwnd)))
        except Exception:
            pass
        return True

    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return targets


def log_event(event: dict):
    event["ts"] = datetime.now().isoformat(timespec="seconds")
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── 메인 루프 ──────────────────────────────────────────────
def main():
    log_event({"event": "START", "pid": _self_pid()})
    last_hour = datetime.now().hour
    log_count = 0
    last_state = None

    while True:
        try:
            game = is_game_running()
            if game and last_state != "game":
                log_event({"event": "GAME_DETECTED", "name": game})
                last_state = "game"
            elif not game and last_state == "game":
                log_event({"event": "GAME_GONE"})
                last_state = "idle"

            if game:
                wins = find_target_windows()
                for hwnd, cls, title, pid in wins:
                    hide_window(hwnd)
                    if log_count < MAX_LOG_PER_HOUR:
                        log_event({
                            "event": "HIDDEN",
                            "class": cls,
                            "title": title[:60],
                            "pid": pid,
                            "game": game,
                        })
                        log_count += 1

            # 시간마다 log_count reset
            cur_hour = datetime.now().hour
            if cur_hour != last_hour:
                last_hour = cur_hour
                log_count = 0

        except Exception as e:
            log_event({"event": "ERROR", "msg": str(e)[:200]})

        time.sleep(POLL_SEC)


def _self_pid():
    return kernel32.GetCurrentProcessId()


if __name__ == "__main__":
    main()
