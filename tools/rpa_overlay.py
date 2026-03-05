"""
BRIDGE RPA Overlay — Apple-inspired Desktop Notification
=========================================================
Canvas 직접 렌더링 (Windows 이모지 미사용).
화면 정중앙. 2모니터 게임 방해 없음 (주 모니터만).
보안: 개인정보 미표시.
"""

import math
import threading
import tkinter as tk
from tkinter import font as tkfont

_post_more_event = threading.Event()


def wants_more() -> bool:
    result = _post_more_event.is_set()
    _post_more_event.clear()
    return result


class RPAOverlay:

    WHITE = "#ffffff"
    BG = "#f5f5f7"
    TEXT1 = "#1d1d1f"
    TEXT2 = "#6e6e73"
    BLUE = "#0071e3"
    BLUE_HOVER = "#0062c4"
    GREEN = "#34c759"
    RED = "#ff3b30"
    BORDER = "#d2d2d7"
    CARD = "#ffffff"
    HOVER_BG = "#e8e8ed"

    def __init__(self):
        self._root = None
        self._thread = None
        self._ready = threading.Event()

    def show_working(self):
        self.close()
        self._thread = threading.Thread(target=self._build_working, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def show_complete(self, posted_count: int = 0):
        self.close()
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._build_complete, args=(posted_count,), daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def close(self):
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass
            self._root = None
        self._ready.clear()

    # ──────────────────────────────────────────────────────────────
    # WORKING
    # ──────────────────────────────────────────────────────────────
    def _build_working(self):
        root = self._make_root(520, 340)
        card = self._make_card(root)

        # macOS 닫기 (좌상단)
        self._mac_close_btn(card, root)

        # 아이콘 (중앙)
        icon = tk.Canvas(card, width=90, height=90,
                         bg=self.CARD, highlightthickness=0)
        icon.pack(pady=(16, 20))
        self._draw_working_icon(icon, root)

        # 제목
        tk.Label(card, text="크래이그 작업중",
                 font=self._fn(28, "bold"), bg=self.CARD,
                 fg=self.TEXT1).pack()

        # 부제
        tk.Label(card, text="인터넷 창을 건들지 마세요",
                 font=self._fn(16), bg=self.CARD,
                 fg=self.TEXT2).pack(pady=(8, 0))

        # 하단 버튼
        btn_area = tk.Frame(card, bg=self.CARD)
        btn_area.pack(side="bottom", fill="x", pady=(24, 4))

        self._big_pill(btn_area, "닫기", self.BG, self.TEXT1,
                       lambda: root.destroy())

        self._draggable(card, root)
        self._ready.set()
        try:
            root.mainloop()
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # COMPLETE
    # ──────────────────────────────────────────────────────────────
    def _build_complete(self, count: int):
        root = self._make_root(520, 400)
        card = self._make_card(root)

        self._mac_close_btn(card, root)

        # 아이콘
        icon = tk.Canvas(card, width=90, height=90,
                         bg=self.CARD, highlightthickness=0)
        icon.pack(pady=(16, 20))
        self._draw_check_icon(icon)

        # 제목
        tk.Label(card, text=f"광고 {count}건 완료!",
                 font=self._fn(28, "bold"), bg=self.CARD,
                 fg=self.GREEN).pack()

        # 부제
        tk.Label(card, text="개인정보 노출이 없도록\n한번 더 직접 확인해주세요",
                 font=self._fn(16), bg=self.CARD, fg=self.TEXT2,
                 justify="center").pack(pady=(10, 0))

        # 하단 버튼 (크게, 세로 배치)
        btn_area = tk.Frame(card, bg=self.CARD)
        btn_area.pack(side="bottom", fill="x", pady=(20, 4))

        def _on_more():
            _post_more_event.set()
            root.destroy()

        self._big_pill(btn_area, "5개 더 올리기", self.BLUE, self.WHITE, _on_more)
        self._big_pill(btn_area, "닫기", self.BG, self.TEXT1,
                       lambda: root.destroy(), pady=(10, 0))

        self._draggable(card, root)
        root.after(60000, lambda: root.destroy() if root.winfo_exists() else None)

        self._ready.set()
        try:
            root.mainloop()
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # Canvas 아이콘
    # ──────────────────────────────────────────────────────────────
    def _draw_working_icon(self, c: tk.Canvas, root: tk.Tk):
        cx, cy, r = 45, 45, 38

        c.create_oval(cx - r, cy - r, cx + r, cy + r,
                      fill="#e8f4fd", outline="#b3d9f7", width=2)

        # 모니터
        c.create_rectangle(25, 24, 65, 52, fill=self.BLUE, outline="")
        c.create_rectangle(28, 27, 62, 49, fill="#4da3ef", outline="")
        c.create_line(31, 33, 46, 33, fill=self.WHITE, width=2)
        c.create_line(31, 38, 52, 38, fill="#a8d4f5", width=2)
        c.create_line(31, 43, 40, 43, fill="#a8d4f5", width=2)
        c.create_line(45, 52, 45, 60, fill=self.BLUE, width=3)
        c.create_line(35, 60, 55, 60, fill=self.BLUE, width=3)

        # 펄스
        self._pulse_step = 0

        def _pulse():
            if not root.winfo_exists():
                return
            c.delete("pulse")
            s = self._pulse_step % 40
            scale = 1.0 + 0.12 * math.sin(s * math.pi / 20)
            pr = r * scale
            c.create_oval(cx - pr, cy - pr, cx + pr, cy + pr,
                          outline=self.BLUE, width=2, dash=(5, 3), tags="pulse")
            self._pulse_step += 1
            root.after(80, _pulse)

        _pulse()

    def _draw_check_icon(self, c: tk.Canvas):
        cx, cy, r = 45, 45, 38

        c.create_oval(cx - r, cy - r, cx + r, cy + r,
                      fill="#e8f8ed", outline="#a3e4b8", width=2)
        c.create_oval(cx - 26, cy - 26, cx + 26, cy + 26,
                      fill=self.GREEN, outline="")
        c.create_line(31, 45, 40, 55, fill=self.WHITE, width=4.5,
                      capstyle="round", joinstyle="round")
        c.create_line(40, 55, 60, 33, fill=self.WHITE, width=4.5,
                      capstyle="round", joinstyle="round")

    # ──────────────────────────────────────────────────────────────
    # UI 헬퍼
    # ──────────────────────────────────────────────────────────────
    def _make_root(self, w, h):
        root = tk.Tk()
        self._root = root
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.97)
        root.configure(bg=self.BORDER)

        # 화면 정중앙
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        root.geometry(f"{w}x{h}+{x}+{y}")
        return root

    def _make_card(self, root):
        outer = tk.Frame(root, bg=self.BORDER, padx=1, pady=1)
        outer.pack(fill="both", expand=True)
        card = tk.Frame(outer, bg=self.CARD, padx=36, pady=28)
        card.pack(fill="both", expand=True)
        return card

    def _mac_close_btn(self, parent, root):
        row = tk.Frame(parent, bg=self.CARD)
        row.pack(fill="x")

        c = tk.Canvas(row, width=16, height=16,
                      bg=self.CARD, highlightthickness=0, cursor="hand2")
        c.pack(side="left")
        c.create_oval(2, 2, 14, 14, fill=self.RED, outline="#e0352b")
        x_items = []

        def _enter(e):
            x_items.append(c.create_line(5, 5, 11, 11, fill=self.WHITE, width=1.5))
            x_items.append(c.create_line(11, 5, 5, 11, fill=self.WHITE, width=1.5))

        def _leave(e):
            for i in x_items:
                c.delete(i)
            x_items.clear()

        c.bind("<Enter>", _enter)
        c.bind("<Leave>", _leave)
        c.bind("<Button-1>", lambda e: root.destroy())

    def _big_pill(self, parent, text, bg, fg, cmd, pady=(0, 0)):
        """큰 pill 버튼 (full-width)."""
        wrap = tk.Frame(parent, bg=self.CARD)
        wrap.pack(fill="x", padx=20, pady=pady)

        btn = tk.Label(wrap, text=text, bg=bg, fg=fg,
                       font=self._fn(16, "bold"),
                       padx=20, pady=14, cursor="hand2")
        btn.pack(fill="x")

        hover_bg = self.BLUE_HOVER if bg == self.BLUE else self.HOVER_BG

        btn.bind("<Button-1>", lambda e: cmd())
        btn.bind("<Enter>", lambda e: btn.configure(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg))

    def _fn(self, size, weight="normal"):
        for fam in ("SF Pro Display", "Segoe UI", "Malgun Gothic"):
            try:
                return tkfont.Font(family=fam, size=size, weight=weight)
            except Exception:
                continue
        return tkfont.Font(size=size, weight=weight)

    def _draggable(self, widget, root):
        def _s(e):
            root._dx, root._dy = e.x, e.y

        def _m(e):
            root.geometry(f"+{root.winfo_x() + e.x - root._dx}+{root.winfo_y() + e.y - root._dy}")

        widget.bind("<ButtonPress-1>", _s)
        widget.bind("<B1-Motion>", _m)


_overlay = RPAOverlay()
show_working = _overlay.show_working
show_complete = _overlay.show_complete
close = _overlay.close
