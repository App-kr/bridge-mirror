"""
setup_scheduler.py — Windows 작업 스케줄러 자동 등록
=======================================================
BRIDGE 유지보수 작업을 Windows 작업 스케줄러에 등록.

실행:
  python tools/setup_scheduler.py          -- 등록
  python tools/setup_scheduler.py --list   -- 등록된 BRIDGE 작업 확인
  python tools/setup_scheduler.py --delete -- 전체 삭제

등록 작업:
  BRIDGE-daily-backup    매일 03:00  로컬 DB 스냅샷 백업
  BRIDGE-render-db-dump  매주 월 04:00  Render /data/master.db SQL 덤프
"""
import subprocess
import sys
from pathlib import Path

PYTHON  = r"Q:\Phtyon 3\python.exe"
BASE    = r"Q:\Claudework\bridge base"
TOOLS   = BASE + r"\tools"
LOG_DIR = BASE + r"\logs\scheduler"

TASKS = [
    {
        "name":     "BRIDGE-daily-backup",
        "desc":     "BRIDGE 로컬 DB 일일 자동 백업 (03:00)",
        "cmd":      f'"{PYTHON}" "{TOOLS}\\bridge_backup.py" backup "자동백업" --type scheduled',
        "schedule": ["/SC", "DAILY", "/ST", "03:00"],
    },
    {
        "name":     "BRIDGE-render-db-dump",
        "desc":     "Render DB SQL 주간 백업 (월 04:00)",
        "cmd":      f'"{PYTHON}" -X utf8 "{TOOLS}\\render_db_backup.py"',
        "schedule": ["/SC", "WEEKLY", "/D", "MON", "/ST", "04:00"],
    },
]


def _schtasks(*args) -> tuple[int, str]:
    r = subprocess.run(
        ["schtasks"] + list(args),
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return r.returncode, (r.stdout + r.stderr).strip()


def register():
    print("[BRIDGE 작업 스케줄러 등록]")
    print(f"  Python  : {PYTHON}")
    print(f"  Base    : {BASE}")
    print()

    # 로그 디렉토리 생성
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

    ok = 0
    for t in TASKS:
        # 기존 작업 삭제 (오류 무시)
        _schtasks("/Delete", "/TN", t["name"], "/F")

        # 등록 (/RL HIGHEST = 현재 사용자 최고 권한)
        code, out = _schtasks(
            "/Create",
            "/TN", t["name"],
            "/TR", t["cmd"],
            "/RL", "HIGHEST",
            *t["schedule"],
            "/F",
        )
        if code == 0:
            print(f"  [OK]   {t['name']}")
            print(f"         {t['desc']}")
            ok += 1
        else:
            print(f"  [FAIL] {t['name']}")
            print(f"         {out[:200]}")
            print("         관리자 권한으로 실행하면 해결될 수 있습니다.")
        print()

    print(f"완료: {ok}/{len(TASKS)} 작업 등록됨")
    if ok < len(TASKS):
        print("\n권고: '관리자로 실행' → python tools/setup_scheduler.py 재시도")


def list_tasks():
    print("[등록된 BRIDGE 작업 스케줄러 목록]")
    for t in TASKS:
        code, out = _schtasks("/Query", "/TN", t["name"], "/FO", "LIST")
        if code == 0:
            # 필요한 줄만 필터링
            for line in out.splitlines():
                if any(k in line for k in ("작업 이름", "TaskName", "상태", "Status",
                                            "다음 실행", "Next Run", "마지막 실행", "Last Run")):
                    print(f"  {line.strip()}")
            print()
        else:
            print(f"  {t['name']}: 미등록")
            print()


def delete_tasks():
    print("[BRIDGE 작업 스케줄러 삭제]")
    for t in TASKS:
        code, out = _schtasks("/Delete", "/TN", t["name"], "/F")
        if code == 0:
            print(f"  [삭제됨] {t['name']}")
        else:
            print(f"  [없음]   {t['name']}")


def main():
    if "--list" in sys.argv:
        list_tasks()
    elif "--delete" in sys.argv:
        delete_tasks()
    else:
        register()


if __name__ == "__main__":
    main()
