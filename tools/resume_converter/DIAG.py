"""
DIAG.py - 순수 진단 스크립트
창이 뜨는지 여부만 테스트. tkinter 최소 코드.
"""
import ctypes
import tkinter as tk
from pathlib import Path

LOG = Path(__file__).parent / "logs" / "DIAG.log"
LOG.parent.mkdir(exist_ok=True)

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        import datetime
        f.write(f"{datetime.datetime.now():%H:%M:%S} {msg}\n")

# 콘솔 숨김
try:
    hw = ctypes.windll.kernel32.GetConsoleWindow()
    if hw:
        ctypes.windll.user32.ShowWindow(hw, 0)
except:
    pass

log("=== START ===")
log(f"Python: {__import__('sys').version[:30]}")

# 1. 창 생성
root = tk.Tk()
log("Tk() 완료")

# 2. 위치 명시: 화면 정중앙
sw = root.winfo_screenwidth()
sh = root.winfo_screenheight()
w, h = 500, 300
x = (sw - w) // 2
y = (sh - h) // 2
root.geometry(f"{w}x{h}+{x}+{y}")
root.title("BRIDGE 진단")
root.configure(bg="#1D9E75")

tk.Label(root,
    text="✓ BRIDGE 창 정상\n이 창이 보이면 성공!",
    bg="#1D9E75", fg="white",
    font=("맑은 고딕", 18, "bold"),
    justify="center"
).pack(expand=True)

tk.Button(root, text="닫기", command=root.destroy,
    font=("맑은 고딕", 12),
    bg="white", fg="#1D9E75",
    relief="flat", padx=20, pady=6
).pack(pady=20)

log(f"화면: {sw}x{sh}, 창 위치: {x},{y}")

# 3. 창 강제 표시
root.deiconify()
root.lift()
root.focus_force()
root.attributes("-topmost", True)
root.update()

log("update() 완료 - mainloop 진입")

# 4. Win32 직접 강제 표시
try:
    import ctypes
    HWND = root.winfo_id()
    ctypes.windll.user32.SetForegroundWindow(HWND)
    ctypes.windll.user32.ShowWindow(HWND, 9)   # SW_RESTORE
    ctypes.windll.user32.BringWindowToTop(HWND)
except Exception as e:
    log(f"Win32 경고: {e}")

log("mainloop 시작")
root.mainloop()
log("mainloop 종료 - 창 닫힘")
