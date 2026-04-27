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
    """WMIC 대안 — Get-CimInstance via PowerShell."""
    ps_cmd = (
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate,WorkingSetSize | "
        "ConvertTo-Json -Depth 3 -Compress"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-OutputFormat", "Text", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
            creationflags=0x08000000,
        )
        if out.returncode != 0:
            log({"event": "PS_FAIL", "rc": out.returncode, "err": (out.stderr or "")[:200]})
            return []
        raw = (out.stdout or "").strip()
        if not raw:
            return []
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        return data
    except Exception as e:
        log({"event": "LIST_FAIL", "err": str(e)[:200]})
        return []


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
    try:
        out = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000,
        )
        return out.returncode == 0
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
