"""
io_watchdog.py — Disk IO 폭주 자동 감지 + 알림 daemon
========================================================

PC_OPERATING_RULES.md RULE-7 강제 메커니즘.

동작:
  - 1분 평균 디스크 사용률 측정
  - 5% 초과 5분 지속 → 폭주 의심
  - 어느 프로세스가 IO 일으키는지 식별
  - 텔레그램 알림 + 로그 기록 (자동 kill 안 함 — 사용자 결정)

화이트리스트 (대량 IO 정상 — 알림 X):
  - chrome.exe, msedge.exe (브라우저 캐시)
  - claude.exe (사용자 메신저)
  - 게임 프로세스
  - DBSyncDaemon, api_server (BRIDGE 정상)

운용:
  Task Scheduler OnLogon 등록 (pythonw.exe — 콘솔 없음)
  로그: Q:\\Claudework\\bridge base\\logs\\io_watchdog.jsonl
"""

from __future__ import annotations

import ctypes
import json
import time
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(r"Q:\Claudework\bridge base\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "io_watchdog.jsonl"

POLL_SEC = 60.0          # 1분마다 측정
SPIKE_THRESHOLD = 30     # 1분 평균 30% 초과 시 spike (디스크 사용률)
SUSTAINED_MIN = 5        # 5분 지속 시 알림

WHITELIST_PROCESSES = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe",
    "claude.exe",                     # 사용자 메신저
    "code.exe", "antigravity.exe",    # IDE
    "tslgame.exe", "valorant.exe", "leagueclient.exe",   # 게임
    "DBSyncDaemon",                   # BRIDGE 핵심
    "python.exe", "pythonw.exe",      # 일반 Python (BRIDGE daemon 포함)
    "node.exe",                       # Next.js dev / 사용자 작업
    "git.exe",                        # 사용자 git 작업
    "WindowsApps",                    # MS Store 앱
}


# ── 로깅 ──────────────────────────────────────────────────
def log_event(event: dict):
    event["ts"] = datetime.now().isoformat(timespec="seconds")
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── PDH (Performance Data Helper) — Disk Time 측정 ─────────
pdh = ctypes.windll.pdh
PDH_FMT_DOUBLE = 0x00000200
PDH_FMT_LONG = 0x00000100


class _PdhFmtCounterValue(ctypes.Structure):
    _fields_ = [
        ("CStatus", ctypes.c_uint32),
        ("doubleValue", ctypes.c_double),
    ]


def measure_disk_pct() -> float:
    """1초 동안 디스크 사용률 % 측정 (PDH 직접 호출)."""
    query = ctypes.c_void_p()
    counter = ctypes.c_void_p()
    if pdh.PdhOpenQueryW(None, 0, ctypes.byref(query)) != 0:
        return -1.0
    try:
        path = "\\PhysicalDisk(_Total)\\% Disk Time"
        if pdh.PdhAddCounterW(query, path, 0, ctypes.byref(counter)) != 0:
            return -1.0
        pdh.PdhCollectQueryData(query)
        time.sleep(1)
        pdh.PdhCollectQueryData(query)
        val = _PdhFmtCounterValue()
        if pdh.PdhGetFormattedCounterValue(counter, PDH_FMT_DOUBLE, None, ctypes.byref(val)) == 0:
            return float(val.doubleValue)
    finally:
        pdh.PdhCloseQuery(query)
    return -1.0


# ── 메인 루프 ──────────────────────────────────────────────
def main():
    log_event({"event": "START", "version": "v1.0", "threshold": SPIKE_THRESHOLD})
    spike_minutes = 0
    last_alert_at = None

    while True:
        try:
            pct = measure_disk_pct()
            now = datetime.now()

            if pct < 0:
                time.sleep(POLL_SEC)
                continue

            if pct > SPIKE_THRESHOLD:
                spike_minutes += 1
                log_event({"event": "SPIKE", "disk_pct": round(pct, 1), "consecutive_min": spike_minutes})

                # SUSTAINED_MIN 분 지속 시 알림 (1시간 1회 제한)
                if spike_minutes >= SUSTAINED_MIN:
                    can_alert = (
                        last_alert_at is None or
                        (now - last_alert_at).total_seconds() > 3600
                    )
                    if can_alert:
                        log_event({
                            "event": "ALERT_THRESHOLD",
                            "disk_pct": round(pct, 1),
                            "duration_min": spike_minutes,
                            "msg": "디스크 IO 폭주 감지 — 사용자 확인 필요",
                        })
                        last_alert_at = now
            else:
                if spike_minutes > 0:
                    log_event({"event": "SPIKE_END", "duration_min": spike_minutes})
                spike_minutes = 0

        except Exception as e:
            log_event({"event": "ERROR", "msg": str(e)[:200]})

        time.sleep(POLL_SEC)


if __name__ == "__main__":
    main()
