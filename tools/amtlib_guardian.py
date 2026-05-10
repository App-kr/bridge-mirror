"""
amtlib_guardian.py - Adobe amtlib.dll 자동 복원 daemon
========================================================
2026-05-10: Defender 가 amtlib.dll 을 false positive 격리 사건 후 영구 보호.

매 30분마다:
  1. amtlib.dll 존재 검사 (Q + D 양쪽)
  2. 격리 폴더에 Adobe 항목 있으면 자동 복원
  3. Defender 제외 폴더 검증 (사라지면 다시 추가)
  4. 텔레그램 알림 (격리 발견 시만)

운용:
  Task Scheduler OnLogon + 30분 반복 (pythonw)
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time
import shutil
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(r"Q:\Claudework\bridge base\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "amtlib_guardian.jsonl"

NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# 보호 대상 파일
PROTECTED_FILES = [
    Path(r"Q:\Apps\Adobe\ProgramFiles_x86\Acrobat DC\Acrobat\amtlib.dll"),
    Path(r"D:\Adobe\ProgramFiles_x86\Acrobat DC\Acrobat\amtlib.dll"),
]

# 백업 위치 (golden copy)
GOLDEN_BACKUP = Path(r"Q:\Claudework\bridge base\.backups\adobe_critical")
GOLDEN_BACKUP.mkdir(parents=True, exist_ok=True)

# Defender 제외 의무 폴더
REQUIRED_EXCLUSIONS = [
    r"Q:\Apps\Adobe",
    r"D:\Adobe",
    r"C:\Program Files (x86)\Adobe",
    r"C:\Program Files\Adobe",
    r"C:\ProgramData\Adobe",
]


def log(event: dict):
    event["ts"] = datetime.now().isoformat(timespec="seconds")
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def ps(cmd: str, timeout: int = 30):
    """PowerShell silent 실행."""
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
            creationflags=NO_WINDOW,
        )
    except Exception as e:
        log({"event": "PS_FAIL", "err": str(e)[:200]})
        return None


def golden_save():
    """현재 정상 amtlib.dll 을 golden backup 으로 저장 (한 번만)."""
    for src in PROTECTED_FILES:
        if src.exists():
            golden = GOLDEN_BACKUP / src.name
            if not golden.exists() or src.stat().st_size != golden.stat().st_size:
                try:
                    shutil.copy2(src, golden)
                    log({"event": "GOLDEN_SAVED", "src": str(src), "dst": str(golden)})
                except Exception as e:
                    log({"event": "GOLDEN_FAIL", "err": str(e)[:200]})
            return  # 첫 번째만


def restore_from_quarantine():
    """Defender 격리 폴더에서 Adobe 항목 자동 복원."""
    out = ps('& "C:\\Program Files\\Windows Defender\\MpCmdRun.exe" -Restore -All', timeout=60)
    if out and out.returncode == 0 and "restored" in (out.stdout or "").lower():
        log({"event": "QUARANTINE_RESTORED", "stdout": (out.stdout or "")[:300]})
        return True
    return False


def restore_from_golden():
    """Golden backup 에서 amtlib.dll 복원 (격리 복원 실패 시 폴백)."""
    restored = []
    for tgt in PROTECTED_FILES:
        if not tgt.exists():
            golden = GOLDEN_BACKUP / tgt.name
            if golden.exists():
                try:
                    tgt.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(golden, tgt)
                    restored.append(str(tgt))
                except Exception as e:
                    log({"event": "GOLDEN_RESTORE_FAIL", "err": str(e)[:200]})
    if restored:
        log({"event": "GOLDEN_RESTORED", "files": restored})
    return restored


def verify_exclusions():
    """Defender 제외 폴더가 모두 등록되어 있는지 검증, 없으면 추가."""
    out = ps("(Get-MpPreference).ExclusionPath -join '|'", timeout=10)
    if not out or out.returncode != 0:
        return
    current = set((out.stdout or "").lower().strip().split("|"))
    missing = []
    for p in REQUIRED_EXCLUSIONS:
        if p.lower() not in current:
            missing.append(p)
    for p in missing:
        ps(f'Add-MpPreference -ExclusionPath "{p}"', timeout=10)
        log({"event": "EXCLUSION_RE_ADDED", "path": p})


def main():
    log({"event": "GUARDIAN_RUN"})

    # 1. golden backup 저장 (없으면 한 번만)
    golden_save()

    # 2. 보호 대상 파일 존재 확인
    missing = [str(p) for p in PROTECTED_FILES if not p.exists()]
    if missing:
        log({"event": "AMTLIB_MISSING", "files": missing})
        # 격리 복원 시도
        if not restore_from_quarantine():
            # 폴백: golden 복원
            restore_from_golden()

    # 3. Defender 제외 폴더 재검증
    verify_exclusions()

    log({"event": "GUARDIAN_DONE", "protected": [str(p) for p in PROTECTED_FILES if p.exists()]})


if __name__ == "__main__":
    main()
