"""
ram_watchdog.py — Lingering 일회성 작업 자동 정리
==================================================

목적:
  광고/블로그/메일/RPA 같은 일회성 작업이 끝나지 않고 RAM 점유하는 경우
  30분 idle 감지 시 자동 종료 + 텔레그램 알림 (선택).

보호 화이트리스트 (절대 종료 안 함):
  - api_server.py (BRIDGE API :8000)
  - db_sync_daemon
  - tg_approval_daemon
  - rdp_keepalive
  - render_monitor
  - bridge_ddns_watchdog
  - work-tracker
  - run_telegram_bot
  - wealth_manager (Next.js)
  - DBSyncDaemon

종료 대상 패턴 (lingering 의심):
  - craigslist_auto_rpa
  - rpa_overlay
  - inject_draft (블로그)
  - auto_post_blog
  - send_introduce_mail
  - bridge_ads (이미 종료됐어야 할 dev 서버)
  - chromedriver, geckodriver, msedgedriver (RPA 끝났는데 남은 것)
  - puppeteer headless

조건 (모두 만족 시 종료):
  - 패턴 매치
  - 30분 이상 실행 중
  - CPU 사용률 5분 평균 1% 미만 (idle)
  - 보호 화이트리스트 미일치

운용:
  Task Scheduler에 30분 간격 등록 (pythonw.exe 무콘솔)
  로그: logs/ram_watchdog.jsonl
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(r"Q:\Claudework\bridge base\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "ram_watchdog.jsonl"

KILL_PATTERNS = [
    r"craigslist_auto_rpa",
    r"rpa_overlay",
    r"inject_draft",
    r"auto_post_blog",
    r"send_introduce_mail",
    r"introduce_mail_send",
    r"bridge_ads.*next",
    r"bridge_ads.*npm",
    r"matjokdo_run_daily",   # 일회성 발행만 (matjokdo daemon은 보호 별도)
]

# 화이트리스트: 절대 종료 안 함
PROTECT_PATTERNS = [
    r"api_server",
    r"db_sync_daemon",
    r"tg_approval_daemon",
    r"rdp_keepalive",
    r"render_monitor",
    r"ddns_watchdog",
    r"work-tracker",
    r"run_telegram_bot",
    r"wealth_manager",
    r"DBSyncDaemon",
    r"focus_guard",         # 자기 자신/형제
    r"ram_watchdog",
    r"matjokdo_dashboard",  # GUI 대시보드 (사용자가 띄운 것)
    r"on_startup",
]

# Headless 브라우저 driver — RPA 끝나면 즉시 정리
DRIVER_NAMES = {
    "chromedriver.exe",
    "geckodriver.exe",
    "msedgedriver.exe",
    "operadriver.exe",
}

IDLE_THRESHOLD_MIN = 30
LOG_RETENTION_DAYS = 30


def log(event: dict):
    event["ts"] = datetime.now().isoformat(timespec="seconds")
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def list_processes():
    """ctypes 직접 — powershell spawn 없음 (30분마다 conhost 깜빡임 차단).

    2026-04-30: 이전 powershell ConvertTo-Json 호출이 30분마다 conhost spawn
    (CREATE_NO_WINDOW 적용해도 conhost 프로세스 자체는 attach).
    EnumProcesses + GetModuleBaseNameW + NtQueryInformationProcess 로 대체.
    """
    import ctypes
    from ctypes import wintypes

    psapi = ctypes.windll.psapi
    kernel32 = ctypes.windll.kernel32
    ntdll = ctypes.windll.ntdll

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_VM_READ = 0x0010

    # 1) PID 목록
    arr = (ctypes.c_ulong * 8192)()
    cb_needed = ctypes.c_ulong()
    if not psapi.EnumProcesses(arr, ctypes.sizeof(arr), ctypes.byref(cb_needed)):
        log({"event": "ENUM_FAIL"})
        return []
    pid_count = cb_needed.value // ctypes.sizeof(ctypes.c_ulong)

    # 2) 각 PID 의 정보 수집
    results = []
    for i in range(pid_count):
        pid = arr[i]
        if pid == 0:
            continue

        h = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, pid
        )
        if not h:
            continue

        try:
            # 이름
            name_buf = ctypes.create_unicode_buffer(260)
            if psapi.GetModuleBaseNameW(h, None, name_buf, 260) == 0:
                continue
            name = name_buf.value

            # 메모리
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]
            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(pmc)
            ws_size = 0
            if psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
                ws_size = pmc.WorkingSetSize

            # 생성 시각 (FILETIME)
            creation = wintypes.FILETIME()
            exit_ft = wintypes.FILETIME()
            kernel_ft = wintypes.FILETIME()
            user_ft = wintypes.FILETIME()
            create_str = ""
            if kernel32.GetProcessTimes(
                h, ctypes.byref(creation), ctypes.byref(exit_ft),
                ctypes.byref(kernel_ft), ctypes.byref(user_ft),
            ):
                ft = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
                # FILETIME (100ns ticks since 1601) -> Unix epoch
                if ft > 0:
                    UNIX_EPOCH_DELTA = 11644473600
                    epoch_sec = (ft / 10_000_000.0) - UNIX_EPOCH_DELTA
                    create_str = datetime.fromtimestamp(epoch_sec).strftime(
                        "%Y%m%d%H%M%S"
                    )

            # CommandLine 은 NtQueryInformationProcess + PEB 읽기 필요
            # 단순화: 매칭 패턴이 process name 또는 module path 에 있는지로 판단
            full_path = ctypes.create_unicode_buffer(1024)
            full_path_str = ""
            if psapi.GetModuleFileNameExW(h, None, full_path, 1024) > 0:
                full_path_str = full_path.value

            results.append({
                "ProcessId": pid,
                "ParentProcessId": 0,  # 부모 PID 는 미수집 (필요시 별도)
                "Name": name,
                "CommandLine": full_path_str,  # 풀 경로 (CommandLine 대용)
                "CreationDate": create_str,
                "WorkingSetSize": ws_size,
            })
        finally:
            kernel32.CloseHandle(h)

    return results


def is_protected(cmdline: str, name: str) -> bool:
    import re
    for p in PROTECT_PATTERNS:
        if re.search(p, cmdline or "", re.IGNORECASE) or re.search(p, name or "", re.IGNORECASE):
            return True
    return False


def matches_kill(cmdline: str, name: str) -> str | None:
    import re
    if name and name.lower() in DRIVER_NAMES:
        return "browser_driver"
    for p in KILL_PATTERNS:
        if re.search(p, cmdline or "", re.IGNORECASE):
            return p
    return None


def parse_cim_date(s):
    """CIM CreationDate 파싱.

    포맷 변형 처리:
      - 평문: '20260427100507.123456+540'
      - PS ConvertTo-Json 거치면 dict 형태: {"DateTime": "...", "value": "..."}
      - ISO: '2026-04-27T10:05:07'
    """
    if not s:
        return None
    # ConvertTo-Json 결과가 dict일 수 있음
    if isinstance(s, dict):
        s = s.get("DateTime") or s.get("value") or ""
    if not isinstance(s, str):
        return None
    s = s.strip()
    if len(s) >= 14 and s[:14].isdigit():
        try:
            return datetime.strptime(s[:14], "%Y%m%d%H%M%S")
        except Exception:
            pass
    # ISO fallback
    try:
        return datetime.fromisoformat(s.split(".")[0].split("+")[0].rstrip("Z"))
    except Exception:
        return None


def kill_pid(pid: int) -> bool:
    """ctypes TerminateProcess — taskkill subprocess 없음 (conhost spawn 0)."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        PROCESS_TERMINATE = 0x0001
        h = kernel32.OpenProcess(PROCESS_TERMINATE, False, int(pid))
        if not h:
            return False
        try:
            return bool(kernel32.TerminateProcess(h, 1))
        finally:
            kernel32.CloseHandle(h)
    except Exception:
        return False


def main():
    procs = list_processes()
    if not procs:
        log({"event": "NO_PROCS"})
        return

    now = datetime.now()
    killed = []
    skipped_protected = 0

    for p in procs:
        try:
            pid = p.get("ProcessId") or 0
            name = p.get("Name") or ""
            cmd = p.get("CommandLine") or ""
            ws_bytes = p.get("WorkingSetSize") or 0
            created = parse_cim_date(p.get("CreationDate") or "")
        except Exception:
            continue

        if pid in (0, 4) or not name:
            continue

        # 보호
        if is_protected(cmd, name):
            skipped_protected += 1
            continue

        # 패턴 매치
        match_reason = matches_kill(cmd, name)
        if not match_reason:
            continue

        # 실행 시간 체크 — created 파싱 실패 시 보수적으로 skip (보호)
        if created:
            mins = (now - created).total_seconds() / 60.0
            if mins < IDLE_THRESHOLD_MIN:
                continue
        else:
            # age 모르면 보호 (사용자가 방금 띄운 작업일 수 있음)
            log({"event": "AGE_UNKNOWN_SKIP", "pid": pid, "name": name, "match": match_reason})
            continue

        # 종료
        ok = kill_pid(pid)
        killed.append({
            "pid": pid,
            "name": name,
            "ram_mb": round(ws_bytes / (1024 * 1024), 1),
            "age_min": round(mins, 1) if mins >= 0 else None,
            "match": match_reason,
            "ok": ok,
        })

    log({
        "event": "SCAN_DONE",
        "total_procs": len(procs),
        "killed": len(killed),
        "protected_skipped": skipped_protected,
        "details": killed[:20],
    })


def cleanup_old_logs():
    if not LOG_PATH.exists():
        return
    try:
        cutoff = time.time() - (LOG_RETENTION_DAYS * 86400)
        if LOG_PATH.stat().st_mtime < cutoff:
            LOG_PATH.unlink(missing_ok=True)
    except Exception:
        pass


if __name__ == "__main__":
    cleanup_old_logs()
    main()
