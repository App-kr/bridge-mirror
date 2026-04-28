"""
game_mode_guardian.py — Game Mode 자동 토글 daemon
=====================================================

PC_OPERATING_RULES.md RULE-3 강제 메커니즘.

동작:
  - 5초 간격 게임 프로세스 감지
  - 게임 시작 → 비필수 BRIDGE Task 자동 Disable + lingering kill
  - 게임 종료 → 5분 grace 후 자동 Enable

활성/복구 대상 Task (Disable / Enable):
  Tier-1 (CPU 부하 큰 polling) — 즉시 정지:
    BridgeWorkTracker (5분 git polling)
    BRIDGE_GDrive_Backup_Frequent
    BRIDGE_EmailAutoresponder
    BRIDGE_EmailAutoresponder_Night
    ClaudeBlog_AutoBackup
    BRIDGE_IOC_Watcher
    BRIDGE_Render_Keepalive

  Tier-2 (백업/감시) — 게임 중 정지:
    BRIDGE_DB_Backup
    BRIDGE_GDrive_Backup
    Bridge\\AutoBackup5min
    BRIDGE_Behavior_Check
    BRIDGE_Auto_Security_Patch

절대 정지 안 함 (Always-on):
  api_server, db_sync_daemon, tg_approval, rdp_keepalive,
  focus_guard, ram_watchdog, game_mode_guardian (self),
  Tailscale, MSDefender, Windows core

운용:
  Task Scheduler OnLogon 등록, pythonw.exe (콘솔 없음)
  로그: Q:\\Claudework\\bridge base\\logs\\game_mode.jsonl
"""

from __future__ import annotations

import ctypes
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(r"Q:\Claudework\bridge base\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "game_mode.jsonl"
STATE_PATH = LOG_DIR / "game_mode_state.json"

# ── 게임 프로세스 (확장 가능) ──────────────────────────────
GAME_PROCESS_NAMES = {
    "tslgame.exe", "overwatch.exe", "leagueclient.exe", "leagueoflegends.exe",
    "valorant.exe", "valorant-win64-shipping.exe", "rl.exe",
    "csgo.exe", "cs2.exe", "destiny2.exe",
    "starcraft.exe", "starcraft2.exe", "lostarkclient.exe",
    "blackdesert64.exe", "wow.exe", "genshinimpact.exe",
    "client-win64-shipping.exe",  # GTA / Rockstar
    "fortnite.exe", "fortniteclient-win64-shipping.exe",
    "minecraft.exe", "javaw.exe",  # Minecraft (조심: javaw은 다른 용도도)
    "rocksmith2014.exe",
}

# ── 게임 중 일시정지할 Task ─────────────────────────────────
SUSPEND_TASKS_TIER1 = [
    "BridgeWorkTracker",
    "BRIDGE_GDrive_Backup_Frequent",
    "BRIDGE_EmailAutoresponder",
    "BRIDGE_EmailAutoresponder_Night",
    "ClaudeBlog_AutoBackup",
    "BRIDGE_IOC_Watcher",
    "BRIDGE_Render_Keepalive",
]

SUSPEND_TASKS_TIER2 = [
    "BRIDGE_DB_Backup",
    "BRIDGE_GDrive_Backup",
    r"\Bridge\AutoBackup5min",
    "BRIDGE_Behavior_Check",
    "BRIDGE_Auto_Security_Patch",
    "BRIDGE_ThreatFeed_Sync",
]

ALL_SUSPEND_TASKS = SUSPEND_TASKS_TIER1 + SUSPEND_TASKS_TIER2

# 게임 종료 후 grace period (sec) — 즉시 게임 재시작 대비
RESUME_GRACE_SEC = 300

POLL_SEC = 5.0
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


# ── 로그 ──────────────────────────────────────────────────
def log_event(event: dict):
    event["ts"] = datetime.now().isoformat(timespec="seconds")
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── 상태 ──────────────────────────────────────────────────
def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"mode": "normal", "suspended_tasks": [], "game_gone_at": None}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"mode": "normal", "suspended_tasks": [], "game_gone_at": None}


def save_state(state: dict):
    try:
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    except Exception:
        pass


# ── 게임 감지 (ctypes 직접 — subprocess spawn 없음) ────────
# 2026-04-28 핵심 수정: tasklist subprocess가 conhost 깜빡임을 만들어
# 사용자 입력을 가로채는 문제 발생 → ctypes EnumProcesses 로 교체
_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32
_psapi = ctypes.windll.psapi


def _list_process_names() -> set[str]:
    """EnumProcesses + GetModuleBaseNameW — 외부 프로세스 spawn 없음."""
    arr = (ctypes.c_ulong * 4096)()
    cb_needed = ctypes.c_ulong()
    if not _psapi.EnumProcesses(arr, ctypes.sizeof(arr), ctypes.byref(cb_needed)):
        return set()
    count = cb_needed.value // ctypes.sizeof(ctypes.c_ulong)
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    names = set()
    for i in range(count):
        pid = arr[i]
        if pid == 0:
            continue
        h = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            continue
        try:
            buf = ctypes.create_unicode_buffer(260)
            n = _psapi.GetModuleBaseNameW(h, None, buf, 260)
            if n > 0:
                names.add(buf.value.lower())
        finally:
            _kernel32.CloseHandle(h)
    return names


def is_game_running() -> str | None:
    names = _list_process_names()
    for g in GAME_PROCESS_NAMES:
        if g in names:
            return g
    return None


# ── Task Scheduler 제어 ─────────────────────────────────────
def disable_task(name: str) -> bool:
    try:
        out = subprocess.run(
            ["schtasks", "/Change", "/TN", name, "/DISABLE"],
            capture_output=True, text=True, timeout=10,
            creationflags=NO_WINDOW,
        )
        return out.returncode == 0
    except Exception:
        return False


def enable_task(name: str) -> bool:
    try:
        out = subprocess.run(
            ["schtasks", "/Change", "/TN", name, "/ENABLE"],
            capture_output=True, text=True, timeout=10,
            creationflags=NO_WINDOW,
        )
        return out.returncode == 0
    except Exception:
        return False


# ── 게임 모드 진입 ─────────────────────────────────────────
def enter_game_mode(state: dict, game_name: str):
    log_event({"event": "GAME_DETECTED", "game": game_name})
    suspended = []
    for tname in ALL_SUSPEND_TASKS:
        if disable_task(tname):
            suspended.append(tname)
    state["mode"] = "game"
    state["suspended_tasks"] = suspended
    state["game_gone_at"] = None
    save_state(state)
    log_event({
        "event": "GAME_MODE_ENTER",
        "game": game_name,
        "suspended_count": len(suspended),
        "suspended": suspended,
    })


def exit_game_mode(state: dict, reason: str = "game_gone_grace_passed"):
    suspended = state.get("suspended_tasks", [])
    resumed = []
    for tname in suspended:
        if enable_task(tname):
            resumed.append(tname)
    state["mode"] = "normal"
    state["suspended_tasks"] = []
    state["game_gone_at"] = None
    save_state(state)
    log_event({
        "event": "GAME_MODE_EXIT",
        "reason": reason,
        "resumed_count": len(resumed),
        "resumed": resumed,
    })


# ── 메인 루프 ──────────────────────────────────────────────
def main():
    log_event({"event": "START", "version": "v1.0"})
    state = load_state()
    last_game_name = None

    while True:
        try:
            game = is_game_running()
            mode = state.get("mode", "normal")

            if game and mode != "game":
                # 게임 시작
                enter_game_mode(state, game)
                last_game_name = game

            elif not game and mode == "game":
                # 게임 사라짐 → grace timer 시작
                if state.get("game_gone_at") is None:
                    state["game_gone_at"] = datetime.now().isoformat()
                    save_state(state)
                    log_event({
                        "event": "GAME_GONE_GRACE_START",
                        "grace_sec": RESUME_GRACE_SEC,
                        "last_game": last_game_name,
                    })
                else:
                    # grace 경과 체크
                    try:
                        gone_at = datetime.fromisoformat(state["game_gone_at"])
                        elapsed = (datetime.now() - gone_at).total_seconds()
                        if elapsed >= RESUME_GRACE_SEC:
                            exit_game_mode(state, reason="grace_passed")
                    except Exception:
                        pass

            elif game and mode == "game":
                # 게임 계속 — grace timer 리셋
                if state.get("game_gone_at"):
                    state["game_gone_at"] = None
                    save_state(state)

            # else: 일반 (게임 없음 + 정상 모드) — nothing to do

        except Exception as e:
            log_event({"event": "ERROR", "msg": str(e)[:200]})

        time.sleep(POLL_SEC)


if __name__ == "__main__":
    main()
