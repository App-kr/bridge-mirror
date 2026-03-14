"""
BRIDGE RPA Launcher
===================
CMD 창 없이 계정 선택 팝업 표시 → 백엔드 독립 실행.
실행: pythonw.exe launcher.pyw  (콘솔 없음)
"""
import os
import sys
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

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
