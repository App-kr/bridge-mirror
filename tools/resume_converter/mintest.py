"""tkinterdnd2 import + tk.Tk() 충돌 테스트"""
import sys
import tkinter as tk
from tkinter import ttk
import ctypes, threading, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

LOG = Path(__file__).parent / "logs" / "mintest.log"
LOG.parent.mkdir(exist_ok=True)

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg, flush=True)

log("=== mintest3 start ===")

# main_gui.py 상단 임포트 재현
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _DND_AVAILABLE = True
    log("tkinterdnd2 imported OK")
except ImportError:
    _DND_AVAILABLE = False
    TkinterDnD = tk.Tk
    log("tkinterdnd2 not found")

# launcher.py가 하는 것처럼 강제 비활성화
_DND_AVAILABLE = False
log(f"_DND_AVAILABLE forced False")

ctypes.windll.shcore.SetProcessDpiAwareness(1)

# launcher.py와 동일하게 tk.Tk() 사용
if _DND_AVAILABLE:
    root = TkinterDnD.Tk()
    log("TkinterDnD.Tk() used")
else:
    root = tk.Tk()
    log("tk.Tk() used")

root.title("BRIDGE Converter")
root.geometry("1440x900")
ttk.Style(root).theme_use("clam")
ttk.Style(root).configure("Treeview", font=("Malgun Gothic", 12), rowheight=28)
log("setup OK")

# Treeview 여러 개 (main_gui는 3개 이상)
for i in range(3):
    tv = ttk.Treeview(root, columns=("a", "b", "c"), show="headings", height=5)
    tv.pack()
log("3x Treeview created")

paned = ttk.PanedWindow(root, orient="horizontal")
paned.pack(fill="both", expand=True)
f1 = tk.Frame(paned, bg="#FFFFFF")
f2 = tk.Frame(paned, bg="#F8F9FA")
paned.add(f1, weight=3)
paned.add(f2, weight=1)
log("PanedWindow+panels OK")

# 5초 후 자동 종료
def _close():
    time.sleep(5)
    root.after(0, root.destroy)
threading.Thread(target=_close, daemon=True).start()

log("before mainloop")
root.mainloop()
log("after mainloop - SUCCESS")
