"""
launcher.py — BRIDGE Converter 런처 v9
  1) DPI Awareness
  2) ttk 'clam' 테마 강제
  3) withdraw() 후 mainloop 진입 → after(0)에서 deiconify() (pre-mainloop 페인트 차단)
  4) Win32 BringWindowToTop 제거 (cascade repaint 원인)
"""
import sys
import ctypes
import traceback
from pathlib import Path

# ── [1] DPI Awareness ─────────────────────────────────────────────────────
# 반드시 Tk 생성 전에 호출해야 효과 있음
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # SYSTEM_DPI_AWARE
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


def log(msg):
    with open(_LOG, "a", encoding="utf-8") as f:
        import datetime
        f.write(f"{datetime.datetime.now():%H:%M:%S} {msg}\n")
        f.flush()


log("=" * 40)
log("v9 start")

# ── sys.path ──────────────────────────────────────────────────────────────
_TOOLS = str(Path(__file__).parent.parent)
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

try:
    import resume_converter.main_gui as _mg

    # ── [2] ttk 테마 'clam' 강제 ────────────────────────────────────────
    # Vista/XP 네이티브 Win32 테마는 Windows 10 DWM과 충돌 → 첫 페인트 시 응답없음
    # clam 테마는 순수 Tk 렌더링 → Win32 의존 없음
    _original_build_ui = _mg.BridgeConverterApp._build_ui

    def _patched_build_ui(self):
        import tkinter.ttk as _ttk
        try:
            _ttk.Style(self.root).theme_use("clam")
            log("테마: clam 강제 적용")
        except Exception as e:
            log(f"테마 설정 실패 (무시): {e}")
        _original_build_ui(self)

    _mg.BridgeConverterApp._build_ui = _patched_build_ui

    # TkinterDnD2 비활성화
    _mg._DND_AVAILABLE = False
    log("TkinterDnD 비활성화")

    from resume_converter.main_gui import BridgeConverterApp
    log("import OK")

    app = BridgeConverterApp()
    log("BridgeConverterApp() OK")

    root = app.root

    # 화면 정중앙
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    ww, wh = 1440, 900
    x = max(0, (sw - ww) // 2)
    y = max(0, (sh - wh) // 2)
    root.geometry(f"{ww}x{wh}+{x}+{y}")
    log(f"screen={sw}x{sh} pos={x},{y}")

    # mainloop 전 페인트 메시지 차단 (pre-paint cascade 방지)
    root.withdraw()

    def _on_tk_error(exc, val, tb):
        log(f"TK ERROR: {exc}: {val}")
    root.report_callback_exception = _on_tk_error

    # ── mainloop 내부에서 창 표시 ─────────────────────────────────────────
    # BringWindowToTop 제거: WM_WINDOWPOSCHANGED → clam repaint cascade 원인
    def _show_window():
        root.deiconify()
        root.lift()
        root.focus_force()
        log("_show_window OK")

    def _heartbeat():
        log("heartbeat OK - mainloop 정상 동작")

    root.after(0,    _show_window)
    root.after(300,  _heartbeat)
    root.after(1500, lambda: root.attributes("-topmost", False))

    log("mainloop 시작")
    app.run()
    log("종료")

except Exception:
    tb = traceback.format_exc()
    log(f"FATAL:\n{tb}")
    try:
        ctypes.windll.user32.MessageBoxW(0, f"오류:\n{tb[:500]}", "BRIDGE 오류", 0x10)
    except Exception:
        pass
