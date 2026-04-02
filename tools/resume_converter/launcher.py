"""
launcher.py — BRIDGE Converter 안전 런처 v3
콘솔 창 숨김 + 에러 로그 기록
"""
import sys
import os
import ctypes
import traceback
from pathlib import Path

# ── 1. 콘솔 창 즉시 숨김 (python.exe 실행 시 나타나는 검은 창) ────────────
try:
    _hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if _hwnd:
        ctypes.windll.user32.ShowWindow(_hwnd, 0)  # SW_HIDE
except Exception:
    pass

# ── 2. 로그 파일 설정 ─────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_LOG_FILE = _LOG_DIR / "launcher.log"

def _log(msg: str):
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            import datetime
            f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
            f.flush()
    except Exception:
        pass

# stderr/stdout 리다이렉트 (pythonw 환경 대비)
class _FileWriter:
    def write(self, s):
        if s and s.strip():
            _log(f"STDERR: {s.rstrip()}")
    def flush(self):
        pass

if sys.stderr is None:
    sys.stderr = _FileWriter()
if sys.stdout is None:
    sys.stdout = _FileWriter()

_log("=" * 50)
_log("BRIDGE Converter 시작")
_log(f"Python: {sys.version[:40]}")
_log(f"실행 경로: {__file__}")
_log(f"작업 디렉토리: {os.getcwd()}")

# ── 3. sys.path 설정 ──────────────────────────────────────────────────────
_TOOLS_DIR = str(Path(__file__).parent.parent)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)
_log(f"sys.path[0]: {sys.path[0]}")

# ── 4. 앱 실행 ────────────────────────────────────────────────────────────
try:
    _log("main_gui 임포트 중...")
    from resume_converter.main_gui import BridgeConverterApp
    _log("임포트 완료. 앱 생성...")
    app = BridgeConverterApp()
    _log("앱 초기화 완료. 창 표시...")

    # 창 강제 표시
    app.root.deiconify()
    app.root.state("normal")
    app.root.lift()
    app.root.focus_force()
    app.root.attributes("-topmost", True)
    app.root.after(1500, lambda: app.root.attributes("-topmost", False))

    # Tk 콜백 에러도 로그에 기록
    def _report_cb_exception(exc, val, tb):
        _log(f"TK CALLBACK ERROR: {exc.__name__}: {val}")
        _log(traceback.format_exc())
    app.root.report_callback_exception = _report_cb_exception

    _log("mainloop() 진입")
    app.run()
    _log("정상 종료")

except Exception:
    tb = traceback.format_exc()
    _log(f"ERROR:\n{tb}")
    try:
        ctypes.windll.user32.MessageBoxW(
            0,
            f"BRIDGE Converter 오류:\n\n{tb[:500]}\n\n로그: {_LOG_FILE}",
            "BRIDGE Converter 오류",
            0x10
        )
    except Exception:
        pass
