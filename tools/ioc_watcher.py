r"""
ioc_watcher.py — Windows IOC (Indicators of Compromise) 감시
Quanta Spot 유형 악성코드 재감염 탐지

사용법:
  python tools/ioc_watcher.py baseline    # 현재 상태를 정상 기준선으로 저장
  python tools/ioc_watcher.py scan        # 기준선 대비 변경 탐지 → 텔레그램 알림
  python tools/ioc_watcher.py register    # Windows 작업 스케줄러에 등록 (1시간마다)

감시 대상:
  1. AppData\Roaming — 새로운 .exe 파일 (Quanta Spot 위장 경로)
  2. AppData\Local\Temp — 새 .exe (다운로더 드롭)
  3. schtasks /query — 새 예약 태스크
  4. Registry Run keys (HKCU + HKLM) — 새 자동시작 항목
  5. Windows Defender 제외 목록 — 수상한 추가
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BASELINE_FILE = BASE_DIR / ".ioc_baseline.json"
LOG_FILE = BASE_DIR / "logs" / "ioc_watcher.log"
LOG_FILE.parent.mkdir(exist_ok=True)

APPDATA_ROAMING = Path(os.environ.get("APPDATA", ""))
APPDATA_LOCAL = Path(os.environ.get("LOCALAPPDATA", ""))
TEMP_DIR = Path(os.environ.get("TEMP", ""))

# Quanta Spot 계열이 위장에 쓰는 벤더명 경로 패턴
SUSPICIOUS_PATHS_PATTERNS = [
    "NVIDIA", "Intel", "AMD", "Microsoft", "Windows",
    "Sync", "CloudAgent", "Update", "Service",
]


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _file_fingerprint(path: Path) -> dict:
    try:
        st = path.stat()
        # 빠른 지문: 크기 + mtime (SHA 생략 — 성능)
        return {
            "size": st.st_size,
            "mtime": int(st.st_mtime),
        }
    except Exception:
        return {}


def _scan_appdata_exes() -> dict[str, dict]:
    """AppData\\Roaming + Temp의 모든 .exe 파일 목록"""
    result = {}
    for root in (APPDATA_ROAMING, APPDATA_LOCAL, TEMP_DIR):
        if not root or not root.exists():
            continue
        try:
            for p in root.rglob("*.exe"):
                try:
                    key = str(p)
                    result[key] = _file_fingerprint(p)
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            continue
    return result


def _scan_schtasks() -> list[str]:
    """schtasks 전체 목록 (Name만). 한글 윈도우 CP949 처리."""
    try:
        r = subprocess.run(
            ["schtasks", "/query", "/fo", "CSV", "/nh"],
            capture_output=True, timeout=30,
            creationflags=0x08000000,
        )
        if r.returncode != 0 or not r.stdout:
            return []
        # CP949 → UTF-8 변환 (한글 윈도우 기본), 실패 시 무시
        raw = r.stdout
        for enc in ("cp949", "utf-8", "latin-1"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw.decode("utf-8", errors="ignore")

        tasks = []
        for line in text.splitlines():
            parts = [p.strip('"') for p in line.split('","')]
            if parts and parts[0]:
                tasks.append(parts[0].strip('"'))
        return sorted(set(tasks))
    except Exception as e:
        _log(f"schtasks 조회 실패: {e}")
        return []


def _scan_registry_run() -> dict[str, list[str]]:
    """HKCU + HKLM Run keys (자동시작)"""
    result = {"HKCU": [], "HKLM": []}
    keys = [
        ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run"),
        ("HKLM", r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ]
    for hive, path in keys:
        try:
            r = subprocess.run(
                ["reg", "query", f"{hive}\\{path}"],
                capture_output=True, text=True, timeout=15,
                creationflags=0x08000000,
            )
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    line = line.strip()
                    if line and not line.startswith("HKEY_") and line != "":
                        result[hive].append(line)
        except Exception:
            pass
    return result


def _scan_defender_exclusions() -> list[str]:
    """Windows Defender 제외 경로 목록"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-MpPreference).ExclusionPath -join '|'"],
            capture_output=True, text=True, timeout=15,
            creationflags=0x08000000,
        )
        if r.returncode == 0 and r.stdout.strip():
            return sorted(r.stdout.strip().split("|"))
    except Exception as e:
        _log(f"Defender 제외 목록 조회 실패: {e}")
    return []


def collect_state() -> dict:
    _log("IOC 스캔 시작...")
    state = {
        "timestamp": datetime.now().isoformat(),
        "appdata_exes": _scan_appdata_exes(),
        "schtasks": _scan_schtasks(),
        "registry_run": _scan_registry_run(),
        "defender_exclusions": _scan_defender_exclusions(),
    }
    _log(f"AppData .exe: {len(state['appdata_exes'])}개 / schtasks: {len(state['schtasks'])}개")
    return state


def save_baseline():
    state = collect_state()
    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    _log(f"기준선 저장됨: {BASELINE_FILE}")
    _log(f"  AppData .exe: {len(state['appdata_exes'])}")
    _log(f"  schtasks: {len(state['schtasks'])}")
    _log(f"  registry Run (HKCU): {len(state['registry_run']['HKCU'])}")
    _log(f"  registry Run (HKLM): {len(state['registry_run']['HKLM'])}")
    _log(f"  Defender 제외: {len(state['defender_exclusions'])}")


def _is_suspicious_path(path: str) -> bool:
    """위장 벤더명 패턴 포함 여부"""
    low = path.lower()
    hits = sum(1 for p in SUSPICIOUS_PATHS_PATTERNS if p.lower() in low)
    # AppData\Roaming 내부 + 벤더명 2개 이상 = 위장 의심
    return "appdata" in low and "roaming" in low and hits >= 1


def scan_diff():
    if not BASELINE_FILE.exists():
        _log("기준선 없음 — 먼저 `baseline` 실행 필요")
        sys.exit(1)
    with open(BASELINE_FILE, encoding="utf-8") as f:
        base = json.load(f)
    curr = collect_state()

    alerts = []

    # 1. 새 .exe (AppData)
    new_exes = set(curr["appdata_exes"]) - set(base["appdata_exes"])
    for exe in new_exes:
        suspicious = _is_suspicious_path(exe)
        tag = "[CRITICAL]" if suspicious else "[WARN]"
        alerts.append(f"{tag} 새 AppData .exe: {exe}")

    # 2. 새 schtasks
    new_tasks = set(curr["schtasks"]) - set(base["schtasks"])
    for t in new_tasks:
        if t and not t.startswith("\\Microsoft\\"):  # MS 시스템 태스크 제외
            alerts.append(f"[WARN] 새 schtasks: {t}")

    # 3. 새 Registry Run 항목
    for hive in ("HKCU", "HKLM"):
        new_runs = set(curr["registry_run"][hive]) - set(base["registry_run"][hive])
        for r in new_runs:
            alerts.append(f"[CRITICAL] 새 Registry Run ({hive}): {r}")

    # 4. 새 Defender 제외
    new_excl = set(curr["defender_exclusions"]) - set(base["defender_exclusions"])
    for e in new_excl:
        alerts.append(f"[CRITICAL] 새 Defender 제외 추가됨: {e}")

    if not alerts:
        _log("IOC 정상 — 기준선과 일치")
        return

    _log(f"IOC 이상 감지: {len(alerts)}건")
    for a in alerts:
        _log(f"  {a}")

    # 텔레그램 알림
    try:
        sys.path.insert(0, str(BASE_DIR / "tools"))
        from tg_notify import send_telegram  # type: ignore
        msg = f"🚨 BRIDGE IOC 이상 감지 ({len(alerts)}건)\n\n" + "\n".join(alerts[:20])
        send_telegram(msg)
    except Exception as e:
        _log(f"텔레그램 알림 실패: {e}")


def register_scheduled_task():
    """Windows 작업 스케줄러에 1시간 주기 등록"""
    python = sys.executable
    script = str(Path(__file__).resolve())
    cmd = [
        "schtasks", "/create",
        "/sc", "hourly",
        "/tn", "BRIDGE_IOC_Watcher",
        "/tr", f'"{python}" "{script}" scan',
        "/rl", "limited",
        "/f",  # force overwrite
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000)
    if r.returncode == 0:
        _log("Windows 작업 스케줄러 등록 완료 (1시간 주기)")
    else:
        _log(f"스케줄러 등록 실패: {r.stderr}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1].lower()
    if cmd == "baseline":
        save_baseline()
    elif cmd == "scan":
        scan_diff()
    elif cmd == "register":
        register_scheduled_task()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
