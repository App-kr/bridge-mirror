"""
launcher.py — BRIDGE Converter 런처 v10
  - DPI Awareness (Tk 생성 전)
  - 콘솔 숨김
  - clam 테마 강제 (_build_ui 패치)
  - 단순 mainloop 진입 (withdraw/BringWindowToTop 없음)
"""
import sys
import ctypes
import traceback
from pathlib import Path

# ── DPI Awareness ──────────────────────────────────────────────────────────
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# ── 콘솔 숨김 ─────────────────────────────────────────────────────────────
try:
    _hw = ctypes.windll.kernel32.GetConsoleWindow()
    if _hw:
        ctypes.windll.user32.ShowWindow(_hw, 0)
except Exception:
    pass

# ── 로그 ──────────────────────────────────────────────────────────────────
_LOG = Path(__file__).parent / "logs" / "launcher.log"
_LOG.parent.mkdir(exist_ok=True)


def _log(msg):
    import datetime
    with open(_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%H:%M:%S} {msg}\n")


_log("=" * 40)
_log("v10 start")

# ── sys.path ──────────────────────────────────────────────────────────────
_TOOLS = str(Path(__file__).parent.parent)
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

try:
    import resume_converter.main_gui as _mg

    # clam 테마 강제 (_configure_styles 이전에도 동작하도록 패치)
    _original_build_ui = _mg.BridgeConverterApp._build_ui

    def _patched_build_ui(self):
        import tkinter.ttk as _ttk
        try:
            _ttk.Style(self.root).theme_use("clam")
            _log("테마: clam 적용")
        except Exception as e:
            _log(f"테마 설정 실패 (무시): {e}")
        _original_build_ui(self)

    _mg.BridgeConverterApp._build_ui = _patched_build_ui

    # TkinterDnD 비활성화
    _mg._DND_AVAILABLE = False
    _log("TkinterDnD 비활성화")

    from resume_converter.main_gui import BridgeConverterApp
    _log("import OK")

    app = BridgeConverterApp()
    _log("BridgeConverterApp() OK")

    root = app.root

    # 화면 정중앙
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    ww, wh = 1440, 900
    x = max(0, (sw - ww) // 2)
    y = max(0, (sh - wh) // 2)
    root.geometry(f"{ww}x{wh}+{x}+{y}")
    _log(f"screen={sw}x{sh} pos={x},{y}")

    _log("mainloop 시작")
    app.run()
    _log("종료")

except Exception:
    tb = traceback.format_exc()
    _log(f"FATAL:\n{tb}")
    try:
        ctypes.windll.user32.MessageBoxW(0, f"오류:\n{tb[:500]}", "BRIDGE 오류", 0x10)
    except Exception:
        pass
