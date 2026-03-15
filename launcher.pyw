"""
BRIDGE RPA Launcher
===================
전역 중복 실행 방지: 어떤 계정이든 이미 실행 중이면 기존 창 복원 후 종료.
CMD 창 없이 계정 선택 팝업 표시 → 백엔드 독립 실행.
실행: pythonw.exe launcher.pyw  (콘솔 없음)
"""
import ctypes
import os
import sys
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

# ── 전역 중복 실행 체크 ────────────────────────────────────────────────────
# 어떤 계정이든 실행 중인 lock 파일이 있으면 → 기존 창 복원 후 즉시 종료
_lock_dir = BASE / "logs"
_lock_dir.mkdir(parents=True, exist_ok=True)

_STILL_ACTIVE = 259  # Windows STILL_ACTIVE 상수

def _is_pid_alive(pid: int) -> bool:
    """GetExitCodeProcess로 프로세스가 실제로 살아있는지 확인."""
    try:
        import ctypes as _ct
        PROCESS_QUERY_LIMITED = 0x1000
        _h = _ct.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid)
        if not _h:
            return False
        _code = _ct.c_ulong(0)
        _ct.windll.kernel32.GetExitCodeProcess(_h, _ct.byref(_code))
        _ct.windll.kernel32.CloseHandle(_h)
        return _code.value == _STILL_ACTIVE
    except Exception:
        return False

_running_acct = None
for _lf in _lock_dir.glob(".rpa_*.lock"):
    try:
        _pid = int(_lf.read_text(encoding="utf-8").strip())
        if _is_pid_alive(_pid):
            _running_acct = _lf.stem.replace(".rpa_", "")
            break
        else:
            _lf.unlink(missing_ok=True)  # 좀비 lock 파일 정리
    except Exception:
        try:
            _lf.unlink(missing_ok=True)
        except Exception:
            pass

if _running_acct:
    # 이미 실행 중 → restore flag 생성 (craigslist_auto_rpa.py가 감지하여 창 복원)
    _restore_flag = _lock_dir / ".overlay_restore.flag"
    try:
        _restore_flag.write_text(_running_acct, encoding="utf-8")
    except Exception:
        pass
    # 안내 팝업
    from rpa_overlay import ask_already_running
    ask_already_running(_running_acct)
    sys.exit(0)

# ── 계정 선택 팝업 ────────────────────────────────────────────────────────
from rpa_overlay import ask_account_selection

result = ask_account_selection()

# ("account1", 10) 형태 또는 ("CANCEL", 0)
if (
    isinstance(result, tuple)
    and len(result) == 2
    and result[0] not in ("CANCEL", None, "")
):
    acct_id, limit = result

    # pythonw → python.exe (백엔드는 콘솔 없이 실행, overlay가 UI 담당)
    py = Path(sys.executable)
    py_exe = py.with_name("python.exe") if py.stem.lower() == "pythonw" else py

    subprocess.Popen(
        [
            str(py_exe),
            str(BASE / "craigslist_auto_rpa.py"),
            "--headless",
            f"--limit={limit}",
            "--account", acct_id,
        ],
        creationflags=0x00000008 | 0x08000000,  # DETACHED_PROCESS | CREATE_NO_WINDOW
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        cwd=str(BASE),
    )
