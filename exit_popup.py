"""종료 알림 팝업 — 별도 프로세스로 실행됨.

사용법:
  python exit_popup.py --watch <PID>   → PID 감시 후 종료되면 팝업
  python exit_popup.py                 → 즉시 팝업 (테스트용)
"""
import ctypes
import sys
import time
import tkinter as tk
import tkinter.font as tkfont


def _is_pid_alive(pid):
    """Windows에서 프로세스 존재 여부 확인."""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    exit_code = ctypes.c_ulong()
    kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
    kernel32.CloseHandle(handle)
    return exit_code.value == STILL_ACTIVE


def _wait_for_pid(pid):
    """주어진 PID가 종료될 때까지 대기."""
    while _is_pid_alive(pid):
        time.sleep(1)


def show_exit_popup():
    root = tk.Tk()
    root.withdraw()
    root.overrideredirect(True)
    root.attributes("-topmost", True)

    W, H = 500, 320
    sx = root.winfo_screenwidth()
    sy = root.winfo_screenheight()
    root.geometry(f"{W}x{H}+{(sx - W) // 2}+{(sy - H) // 2}")

    # 드래그 이동
    def _press(e):
        root._dx, root._dy = e.x_root, e.y_root

    def _move(e):
        x = root.winfo_x() + e.x_root - root._dx
        y = root.winfo_y() + e.y_root - root._dy
        root.geometry(f"+{x}+{y}")
        root._dx, root._dy = e.x_root, e.y_root

    # 외곽 테두리 (부드러운 그레이)
    border = tk.Frame(root, bg="#d0d0d0")
    border.pack(fill="both", expand=True)

    card = tk.Frame(border, bg="#fafafa")
    card.pack(fill="both", expand=True, padx=1, pady=1)

    card.bind("<ButtonPress-1>", _press)
    card.bind("<B1-Motion>", _move)

    tk.Frame(card, bg="#fafafa", height=32).pack()

    # 작업 알림 (소제목 + 종 이모지)
    title_lbl = tk.Label(card, text="\U0001F514 작업 알림",
                         font=tkfont.Font(family="Malgun Gothic", size=13),
                         bg="#fafafa", fg="#999999")
    title_lbl.pack()
    title_lbl.bind("<ButtonPress-1>", _press)
    title_lbl.bind("<B1-Motion>", _move)

    tk.Frame(card, bg="#fafafa", height=16).pack()

    # 메인 메시지
    msg_lbl = tk.Label(card, text="Craig광고 작업이 요청으로 종료되었어요 !",
                       font=tkfont.Font(family="Malgun Gothic", size=16),
                       bg="#fafafa", fg="#333333")
    msg_lbl.pack()
    msg_lbl.bind("<ButtonPress-1>", _press)
    msg_lbl.bind("<B1-Motion>", _move)

    tk.Frame(card, bg="#fafafa", height=28).pack()

    # 확인 버튼 (둥근 느낌, 부드러운 파란색)
    btn = tk.Label(card, text="확인",
                   font=tkfont.Font(family="Malgun Gothic", size=15),
                   bg="#5b9bd5", fg="#ffffff", cursor="hand2",
                   padx=48, pady=10, relief="flat")
    btn.pack()
    btn.bind("<Button-1>", lambda e: root.destroy())
    btn.bind("<Enter>", lambda e: btn.configure(bg="#4a8ac4"))
    btn.bind("<Leave>", lambda e: btn.configure(bg="#5b9bd5"))

    tk.Frame(card, bg="#fafafa", height=14).pack()

    hint_lbl = tk.Label(card, text="다시 작업을 하려면 처음부터 시작해주세요",
                        font=tkfont.Font(family="Malgun Gothic", size=13),
                        bg="#fafafa", fg="#333333")
    hint_lbl.pack()
    hint_lbl.bind("<ButtonPress-1>", _press)
    hint_lbl.bind("<B1-Motion>", _move)

    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--watch":
        pid = int(sys.argv[2])
        _wait_for_pid(pid)
    show_exit_popup()
