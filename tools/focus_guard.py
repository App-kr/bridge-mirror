"""
focus_guard.py — CMD/PowerShell popup auto-hider (event-driven + focus restore)
================================================================================

v3 (2026-04-28 긴급):
  - SetWinEventHook EVENT_OBJECT_SHOW 이벤트로 새 창 spawn 즉시 감지 (~10ms)
  - 숨김 직후 사용자 활성창에 포커스 복원 (SetForegroundWindow)
  - 100ms 폴링 fallback (이벤트 누락 대비)
  - 사용자 입력(키보드/마우스) 빼앗김 차단

목적:
  Antigravity / VS Code / git polling / ccusage 등이 1~5초마다 spawn 하는
  자식 cmd/powershell 창이 사용자 입력 focus를 가로채는 문제 해결.

동작:
  - EVENT_OBJECT_SHOW: 새 창 가시화 즉시 콜백
  - 게임 모드: 모든 콘솔 창 숨김 (화이트리스트 제외)
  - 일반 모드 (ALWAYS_ON_MODE): transient spawn 패턴만 숨김 + 포커스 복원

운용:
  Task Scheduler 등록 (OnLogon, pythonw.exe)
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
    "antigravity",          # Antigravity terminal panel
)

# 강제 숨김 대상 — 어떤 모드에서도 항상 숨김 (transient spawn)
ALWAYS_HIDE_TITLE_KEYWORDS = (
    "ccusage statusline",
    "npm exec ccusage",
    "git.exe",              # 백업/hook용 git 호출
    "npm run dev",          # 누군가 spawn한 npm dev (사용자가 띄운 건 wt에서)
    "next dev",
    "npx ccusage",
    "subprocess",           # python -c 호출 식별자
)

# 2026-04-28 긴급: 게임 아니어도 항상 동작 (사용자 호소 — 1~5초 깜빡임)
ALWAYS_ON_MODE = True

# 로그
LOG_DIR = Path(r"Q:\Claudework\bridge base\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "focus_guard.jsonl"

POLL_SEC = 0.001            # 1ms (was 5ms) — 사용자 추가 호소
                            # 1000회/초 polling, CPU 1-2%. visible 시간 1ms 이하 (사람 눈에 거의 안 보임)
MAX_LOG_PER_HOUR = 2000


# ── Win32 ──────────────────────────────────────────────────
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
SW_HIDE = 0

# WinEvent constants
EVENT_OBJECT_SHOW = 0x8002
EVENT_OBJECT_CREATE = 0x8000
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002
OBJID_WINDOW = 0

# WinEventProc signature
WinEventProcType = ctypes.WINFUNCTYPE(
    None,
    wt.HANDLE,  # hWinEventHook
    wt.DWORD,   # event
    wt.HWND,    # hwnd
    wt.LONG,    # idObject
    wt.LONG,    # idChild
    wt.DWORD,   # idEventThread
    wt.DWORD,   # dwmsEventTime
)


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


SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_HIDEWINDOW = 0x0080
SWP_NOREDRAW = 0x0008
SWP_NOSENDCHANGING = 0x0400
SWP_FLAGS_HIDE_NO_FOCUS = SWP_NOZORDER | SWP_NOACTIVATE | SWP_HIDEWINDOW | SWP_NOSENDCHANGING

# 게임 창 강제 topmost
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
LSFW_LOCK = 1
LSFW_UNLOCK = 2

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000   # 창이 활성화 자체 안 됨
WS_EX_TOOLWINDOW = 0x00000080   # 작업 표시줄 미표시
WS_EX_LAYERED = 0x00080000      # 투명도 적용 가능
LWA_ALPHA = 0x00000002          # alpha 값 적용

# 화면 밖 좌표 (사용자 눈에 절대 안 보임)
OFFSCREEN_X = -32000
OFFSCREEN_Y = -32000

# Win32 API signatures (LongPtr 호환)
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_ssize_t]


def _force_no_activate(hwnd):
    """창 스타일에 WS_EX_NOACTIVATE + LAYERED 적용 — 활성화 차단 + 투명화 가능."""
    try:
        ex = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        new_ex = ex | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_LAYERED
        user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, new_ex)
        # alpha=0 으로 완전 투명 (시각적으로 0% 가시화)
        user32.SetLayeredWindowAttributes(hwnd, 0, 0, LWA_ALPHA)
    except Exception:
        pass


def hide_window(hwnd):
    """창 숨김 — v3.3 5중 방어 (시각적으로 절대 안 보임 + 활성화 절대 안 됨).

    1. WS_EX_NOACTIVATE + LAYERED 스타일 강제 적용
    2. SetLayeredWindowAttributes alpha=0 (완전 투명, 픽셀 0%)
    3. SetWindowPos with OFFSCREEN 좌표 (-32000, -32000) — 화면 밖
    4. SetWindowPos with SWP_HIDEWINDOW (Z-order 변경 없이 숨김)
    5. ShowWindow(SW_HIDE) — 최종 fallback

    이 5중 방어로 새 창이 spawn되어도 사용자 눈에 절대 안 보이고
    포커스도 절대 안 빼앗김.
    """
    _force_no_activate(hwnd)
    # 화면 밖으로 이동 (활성화 없이)
    try:
        user32.SetWindowPos(hwnd, 0, OFFSCREEN_X, OFFSCREEN_Y, 1, 1,
                            SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOSENDCHANGING)
    except Exception:
        pass
    # 숨김 (활성화 없이)
    try:
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_FLAGS_HIDE_NO_FOCUS)
    except Exception:
        pass
    user32.ShowWindow(hwnd, SW_HIDE)


def get_foreground():
    return user32.GetForegroundWindow()


def restore_focus(prev_hwnd):
    """이전 활성창에 포커스 복원 (사용자 입력 빼앗김 방지)."""
    if prev_hwnd:
        try:
            user32.SetForegroundWindow(prev_hwnd)
        except Exception:
            pass


def should_hide(hwnd, always_on: bool):
    """창이 숨김 대상인지 판정 (이벤트 hook + 폴링 공통 로직)."""
    try:
        if not is_visible(hwnd):
            return False
        cls = get_window_class(hwnd)
        if cls not in TARGET_CLASSES:
            return False
        title_raw = get_window_title(hwnd)
        title = title_raw.lower()

        # 부모가 사용자 작업 도구 (Antigravity / VSCode / Cursor / Terminal / Explorer)
        # 면 절대 hide 안 함 — 사용자가 띄운 콘솔 보호
        try:
            wpid = get_window_pid(hwnd)
            if wpid and _is_user_tool_child(wpid):
                return False
        except Exception:
            pass

        # 화이트리스트
        for kw in WHITELIST_TITLE_KEYWORDS:
            if kw in title:
                return False

        if always_on:
            for kw in ALWAYS_HIDE_TITLE_KEYWORDS:
                if kw in title:
                    return True
            # 빈 제목 또는 "관리자: ..." 패턴 (transient spawn signature)
            if not title.strip():
                return True
            if "관리자:" in title_raw or "administrator:" in title:
                return True
            if title in ("c:\\windows\\system32\\cmd.exe",
                         "c:\\windows\\system32\\windowspowershell\\v1.0\\powershell.exe"):
                return True
            return False
        # 게임 모드: 화이트리스트 외 모든 콘솔 숨김
        return True
    except Exception:
        return False


# ── 게임 감지 (ctypes 직접 — subprocess spawn 없음) ────────
# 2026-04-28 핵심 수정: tasklist subprocess가 conhost 깜빡임을 만들어
# 자기 자신이 만든 conhost를 hide하려는 무한 루프 발생 → ctypes 로 교체
_psapi = ctypes.windll.psapi


# 사용자 작업 도구 (IDE/Terminal 본체) — 부모 프로세스가 이 목록에 있으면 자식 콘솔 보호
# 2026-04-30 정리: IDE/Terminal 본체만 보호. Claude/node/bash 등은 부모 추적 (3대) 으로 IDE 자식 자동 보호
# (claude.exe 자식 conhost가 IDE 안 작업이면 부모 따라가서 Antigravity 발견 → 보호)
# (claude.exe가 자체적으로 spawn하는 단명 conhost는 hide → 사용자 시야 깜빡임 차단)
USER_TOOL_PARENTS = {
    "antigravity.exe",          # Antigravity IDE
    "code.exe",                 # VS Code
    "code - insiders.exe",
    "cursor.exe",
    "windsurf.exe",
    "windowsterminal.exe",      # Windows Terminal
    "wt.exe",
    "openconsole.exe",
    "explorer.exe",             # 사용자가 직접 cmd 더블클릭한 경우
}


def _get_parent_pid(pid: int) -> int:
    """Win32 NtQueryInformationProcess 대신 toolhelp32 활용."""
    try:
        # CreateToolhelp32Snapshot
        TH32CS_SNAPPROCESS = 0x00000002
        snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snapshot == -1 or snapshot == 0:
            return 0

        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize", ctypes.c_ulong),
                ("cntUsage", ctypes.c_ulong),
                ("th32ProcessID", ctypes.c_ulong),
                ("th32DefaultHeapID", ctypes.c_void_p),
                ("th32ModuleID", ctypes.c_ulong),
                ("cntThreads", ctypes.c_ulong),
                ("th32ParentProcessID", ctypes.c_ulong),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", ctypes.c_ulong),
                ("szExeFile", ctypes.c_char * 260),
            ]

        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        try:
            if kernel32.Process32First(snapshot, ctypes.byref(entry)):
                while True:
                    if entry.th32ProcessID == pid:
                        return entry.th32ParentProcessID
                    if not kernel32.Process32Next(snapshot, ctypes.byref(entry)):
                        break
        finally:
            kernel32.CloseHandle(snapshot)
    except Exception:
        pass
    return 0


def _get_process_name(pid: int) -> str:
    """프로세스 이름 (소문자)."""
    if pid <= 0:
        return ""
    try:
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(260)
            n = _psapi.GetModuleBaseNameW(h, None, buf, 260)
            if n > 0:
                return buf.value.lower()
        finally:
            kernel32.CloseHandle(h)
    except Exception:
        pass
    return ""


def _is_user_tool_child(pid: int) -> bool:
    """창의 프로세스가 사용자 작업 도구 자식인지 확인 (최대 3대 거슬러 올라감)."""
    cur = pid
    for _ in range(3):
        parent = _get_parent_pid(cur)
        if parent <= 0:
            return False
        pname = _get_process_name(parent)
        if pname in USER_TOOL_PARENTS:
            return True
        cur = parent
    return False


def _list_process_names_via_ctypes() -> set[str]:
    """EnumProcesses + GetModuleBaseNameW — 외부 프로세스 spawn 없음.

    tasklist.exe 호출보다 훨씬 빠르고 conhost 깜빡임 자체를 만들지 않음.
    """
    arr = (ctypes.c_ulong * 4096)()
    cb_needed = ctypes.c_ulong()
    if not _psapi.EnumProcesses(arr, ctypes.sizeof(arr), ctypes.byref(cb_needed)):
        return set()
    count = cb_needed.value // ctypes.sizeof(ctypes.c_ulong)

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000  # Win Vista+, 안전한 권한
    names = set()
    for i in range(count):
        pid = arr[i]
        if pid == 0:
            continue
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            continue
        try:
            buf = ctypes.create_unicode_buffer(260)
            n = _psapi.GetModuleBaseNameW(h, None, buf, 260)
            if n > 0:
                names.add(buf.value.lower())
        finally:
            kernel32.CloseHandle(h)
    return names


_game_check_cache = {"names": set(), "ts": 0.0}
_GAME_CACHE_TTL = 4.0  # 4초 동안 결과 재사용 (CPU 부하 감소)


def is_game_running():
    """게임 프로세스 검사 — ctypes 기반 (subprocess spawn 없음 + 4초 캐시)."""
    now = time.time()
    if now - _game_check_cache["ts"] < _GAME_CACHE_TTL:
        names = _game_check_cache["names"]
    else:
        names = _list_process_names_via_ctypes()
        _game_check_cache["names"] = names
        _game_check_cache["ts"] = now

    for g in GAME_PROCESS_NAMES:
        if g in names:
            return g
    return None


# ── 콘솔창 enumerate + 숨김 ─────────────────────────────────
def find_target_windows(always_on: bool = False):
    """대상 콘솔 창 식별.

    always_on=True (게임 외 모드): ALWAYS_HIDE_TITLE_KEYWORDS 매칭만 숨김
                                   (사용자가 띄운 일반 cmd/powershell은 보호)
    always_on=False (게임 모드): 화이트리스트 외 모든 콘솔 숨김
    """
    targets = []

    def cb(hwnd, _):
        try:
            if not is_visible(hwnd):
                return True
            cls = get_window_class(hwnd)
            if cls not in TARGET_CLASSES:
                return True
            title_raw = get_window_title(hwnd)
            title = title_raw.lower()

            # 화이트리스트 — 사용자가 직접 띄운 것은 절대 안 숨김
            for kw in WHITELIST_TITLE_KEYWORDS:
                if kw in title:
                    return True

            # always_on (게임 외 모드): 알려진 spawn 패턴만 숨김
            if always_on:
                for kw in ALWAYS_HIDE_TITLE_KEYWORDS:
                    if kw in title:
                        targets.append((hwnd, cls, title_raw, get_window_pid(hwnd)))
                        return True
                # 빈 제목 + 짧은 시간 cmd/powershell.exe → 자식 spawn 강력 의심
                if not title.strip() or title in ("c:\\windows\\system32\\cmd.exe",
                                                   "c:\\windows\\system32\\windowspowershell\\v1.0\\powershell.exe",
                                                   "관리자: c:\\windows\\system32\\cmd.exe",
                                                   "관리자: c:\\windows\\system32\\windowspowershell\\v1.0\\powershell.exe"):
                    targets.append((hwnd, cls, title_raw, get_window_pid(hwnd)))
                return True

            # 게임 모드: 모든 콘솔 숨김 (화이트리스트 외)
            targets.append((hwnd, cls, title_raw, get_window_pid(hwnd)))
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


# ── 글로벌 상태 (이벤트 콜백에서 접근) ────────────────────
_state = {
    "game_active": False,
    "log_count": 0,
    "log_hour": datetime.now().hour,
    "last_user_focus": 0,    # 마지막으로 본 사용자 활성창 hwnd
}


def _maybe_log(event):
    """rate-limited 로그."""
    cur_hour = datetime.now().hour
    if cur_hour != _state["log_hour"]:
        _state["log_hour"] = cur_hour
        _state["log_count"] = 0
    if _state["log_count"] < MAX_LOG_PER_HOUR:
        log_event(event)
        _state["log_count"] += 1


def _track_user_focus():
    """현재 활성창이 콘솔이 아니면 사용자 활성창으로 기록."""
    fg = get_foreground()
    if not fg:
        return
    cls = get_window_class(fg)
    if cls not in TARGET_CLASSES:  # 사용자 작업창 (브라우저, IDE, 게임 등)
        _state["last_user_focus"] = fg


# ── 이벤트 콜백 (새 창 가시화 즉시 호출) ────────────────────
def _on_window_event(hWinEventHook, event, hwnd, idObject, idChild,
                     dwEventThread, dwmsEventTime):
    if idObject != OBJID_WINDOW or hwnd == 0:
        return
    try:
        always_on = ALWAYS_ON_MODE and not _state["game_active"]
        if not (_state["game_active"] or always_on):
            return

        # ── v3.5: 게임 모드면 EVENT_OBJECT_CREATE에서 visible 검사 SKIP ──
        # 새 콘솔이 visible 되기 전 미리 차단 (가장 강력한 방어)
        cls = get_window_class(hwnd)
        if cls not in TARGET_CLASSES:
            return

        # 사용자 작업 도구 보호
        try:
            wpid = get_window_pid(hwnd)
            if wpid and _is_user_tool_child(wpid):
                return
        except Exception:
            pass

        title_raw = get_window_title(hwnd)
        title = title_raw.lower()

        # 화이트리스트
        for kw in WHITELIST_TITLE_KEYWORDS:
            if kw in title:
                return

        # 게임 모드: 화이트리스트 외 모든 콘솔 차단 (visible 여부 무관)
        # 일반 모드: 패턴 매칭만
        if not _state["game_active"]:
            # always_on - 패턴 매치만
            matched = False
            for kw in ALWAYS_HIDE_TITLE_KEYWORDS:
                if kw in title:
                    matched = True
                    break
            if not matched:
                if not title.strip():
                    matched = True
                elif "관리자:" in title_raw or "administrator:" in title:
                    matched = True
            if not matched:
                return

        prev_focus = _state["last_user_focus"]
        pid = get_window_pid(hwnd)

        hide_window(hwnd)
        # 포커스 즉시 복원 — 사용자 키보드/마우스 입력 보호
        restore_focus(prev_focus)

        # 게임 모드: 게임 창을 강제로 TOPMOST 로 (다른 창이 게임 위 못 올림)
        if _state["game_active"] and prev_focus:
            try:
                user32.SetWindowPos(prev_focus, HWND_TOPMOST, 0, 0, 0, 0,
                                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
            except Exception:
                pass

        _maybe_log({
            "event": "HIDDEN_EVT",
            "class": cls,
            "title": title_raw[:60],
            "pid": pid,
            "mode": "game" if _state["game_active"] else "always-on",
            "focus_restored": bool(prev_focus),
        })
    except Exception as e:
        _maybe_log({"event": "EVT_ERR", "msg": str(e)[:200]})


# ── 메시지 루프 ────────────────────────────────────────────
def _message_loop_thread():
    """Win32 메시지 루프 (이벤트 hook 콜백 dispatch 위해 필수)."""
    msg = wt.MSG()
    while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


# ── 폴링 fallback (이벤트 누락 대비) ────────────────────────
def _polling_thread():
    last_state = None
    # v3.6: 시작 즉시 ForegroundLock 활성 (게임 여부 무관)
    try:
        user32.LockSetForegroundWindow(LSFW_LOCK)
        log_event({"event": "FOREGROUND_LOCKED_ALWAYS_ON"})
    except Exception:
        pass

    while True:
        try:
            game = is_game_running()
            _state["game_active"] = bool(game)
            if game and last_state != "game":
                log_event({"event": "GAME_DETECTED", "name": game})
                last_state = "game"
            elif not game and last_state == "game":
                log_event({"event": "GAME_GONE"})
                last_state = "idle"

            _track_user_focus()
            # v3.6.1: 매 30ms z-order 호출이 오히려 redraw 깜빡임 유발
            # -> 비활성화. ForegroundLock 만으로 충분.

            if game or ALWAYS_ON_MODE:
                always_on = not game
                # 폴백 검사 — 이벤트 누락된 창 청소
                wins = find_target_windows(always_on=always_on)
                for hwnd, cls, title, pid in wins:
                    prev_focus = _state["last_user_focus"]
                    hide_window(hwnd)
                    restore_focus(prev_focus)
                    _maybe_log({
                        "event": "HIDDEN_POLL",
                        "class": cls,
                        "title": title[:60],
                        "pid": pid,
                        "mode": "game" if game else "always-on",
                    })
        except Exception as e:
            _maybe_log({"event": "POLL_ERR", "msg": str(e)[:200]})
        time.sleep(POLL_SEC)


# ── 메인 ──────────────────────────────────────────────────
def main():
    import threading

    log_event({"event": "START", "pid": _self_pid(), "version": "v3-event-hook"})

    # WinEvent hook 등록 (EVENT_OBJECT_SHOW + EVENT_OBJECT_CREATE)
    proc = WinEventProcType(_on_window_event)
    # ref 유지 — GC 방지
    globals()["_evt_proc_ref"] = proc

    hook1 = user32.SetWinEventHook(
        EVENT_OBJECT_SHOW, EVENT_OBJECT_SHOW,
        0, proc, 0, 0,
        WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
    )
    hook2 = user32.SetWinEventHook(
        EVENT_OBJECT_CREATE, EVENT_OBJECT_CREATE,
        0, proc, 0, 0,
        WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
    )

    if not hook1 and not hook2:
        log_event({"event": "HOOK_FAIL", "msg": "SetWinEventHook returned 0"})

    # 폴링 fallback 스레드
    t = threading.Thread(target=_polling_thread, daemon=True)
    t.start()

    # 메시지 루프 (메인 스레드 — 이벤트 콜백 dispatch)
    try:
        _message_loop_thread()
    finally:
        if hook1:
            user32.UnhookWinEvent(hook1)
        if hook2:
            user32.UnhookWinEvent(hook2)


def _self_pid():
    return kernel32.GetCurrentProcessId()


if __name__ == "__main__":
    main()
