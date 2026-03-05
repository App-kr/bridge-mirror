"""
BRIDGE RPA Overlay — Apple-inspired Desktop Notification
=========================================================
Canvas 직접 렌더링 (Windows 이모지 미사용).
주 모니터 상단 중앙. 2모니터 게임 방해 없음.
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

    # Apple 팔레트
    WHITE = "#ffffff"
    BG = "#f5f5f7"
    TEXT1 = "#1d1d1f"
    TEXT2 = "#86868b"
    TEXT3 = "#aeaeb2"
    BLUE = "#0071e3"
    BLUE_HOVER = "#0062c4"
    GREEN = "#34c759"
    RED = "#ff3b30"
    ORANGE = "#ff9500"
    BORDER = "#d2d2d7"
    CARD = "#ffffff"
    HOVER_BG = "#e8e8ed"

    def __init__(self):
        self._root = None
        self._thread = None
        self._ready = threading.Event()
        self._anim_id = None

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
        root = self._make_root(660, 150)
        card = self._make_card(root)

        # 왼쪽: 애니메이션 아이콘 (파란 펄스 원 + 모니터 아이콘)
        icon_canvas = tk.Canvas(card, width=72, height=72,
                                bg=self.CARD, highlightthickness=0)
        icon_canvas.pack(side="left", padx=(0, 24))
        self._draw_working_icon(icon_canvas, root)

        # 중앙: 텍스트
        mid = tk.Frame(card, bg=self.CARD)
        mid.pack(side="left", fill="both", expand=True)

        tk.Label(mid, text="크래이그 작업중",
                 font=self._fn(22, "bold"), bg=self.CARD,
                 fg=self.TEXT1).pack(anchor="w")
        tk.Label(mid, text="인터넷 창을 건들지 마세요",
                 font=self._fn(14), bg=self.CARD,
                 fg=self.TEXT2).pack(anchor="w", pady=(6, 0))

        # 우측: 닫기 영역
        right = tk.Frame(card, bg=self.CARD)
        right.pack(side="right", padx=(16, 0))

        self._mac_close_btn(right, root)
        self._pill_btn(right, "닫기", self.BG, self.TEXT1,
                       lambda: root.destroy(), side="bottom")

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
        root = self._make_root(660, 210)
        card = self._make_card(root)

        # 왼쪽: 체크마크 아이콘
        icon_canvas = tk.Canvas(card, width=72, height=72,
                                bg=self.CARD, highlightthickness=0)
        icon_canvas.pack(side="left", padx=(0, 24))
        self._draw_check_icon(icon_canvas)

        # 중앙+하단 묶음
        body = tk.Frame(card, bg=self.CARD)
        body.pack(side="left", fill="both", expand=True)

        # 텍스트
        tk.Label(body, text=f"광고 {count}건 완료",
                 font=self._fn(22, "bold"), bg=self.CARD,
                 fg=self.GREEN).pack(anchor="w")
        tk.Label(body, text="개인정보 노출이 없도록\n한번 더 직접 확인해주세요",
                 font=self._fn(14), bg=self.CARD, fg=self.TEXT2,
                 justify="left").pack(anchor="w", pady=(8, 0))

        # 버튼 행
        btn_row = tk.Frame(body, bg=self.CARD)
        btn_row.pack(anchor="w", pady=(16, 0))

        def _on_more():
            _post_more_event.set()
            root.destroy()

        self._pill_btn(btn_row, "5개 더 올리기", self.BLUE, self.WHITE,
                       _on_more, side="left", padx=(0, 10))
        self._pill_btn(btn_row, "닫기", self.BG, self.TEXT1,
                       lambda: root.destroy(), side="left")

        # 우측: 닫기
        right = tk.Frame(card, bg=self.CARD)
        right.pack(side="right", anchor="n", padx=(16, 0))
        self._mac_close_btn(right, root)

        self._draggable(card, root)
        root.after(60000, lambda: root.destroy() if root.winfo_exists() else None)

        self._ready.set()
        try:
            root.mainloop()
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # 커스텀 아이콘 (Canvas 렌더링, 이모지 미사용)
    # ──────────────────────────────────────────────────────────────
    def _draw_working_icon(self, c: tk.Canvas, root: tk.Tk):
        """파란 원 + 모니터 아이콘 + 펄스 애니메이션."""
        cx, cy, r = 36, 36, 30

        # 배경 원
        c.create_oval(cx - r, cy - r, cx + r, cy + r,
                      fill="#e8f4fd", outline="#b3d9f7", width=1.5)

        # 모니터 본체
        c.create_rectangle(20, 20, 52, 44, fill=self.BLUE,
                           outline="", width=0)
        # 모니터 화면 (밝은 부분)
        c.create_rectangle(23, 23, 49, 41, fill="#4da3ef", outline="")
        # 화면 위 커서 라인들
        c.create_line(26, 28, 38, 28, fill=self.WHITE, width=1.5)
        c.create_line(26, 32, 42, 32, fill="#a8d4f5", width=1.5)
        c.create_line(26, 36, 35, 36, fill="#a8d4f5", width=1.5)
        # 모니터 받침
        c.create_line(36, 44, 36, 50, fill=self.BLUE, width=2.5)
        c.create_line(28, 50, 44, 50, fill=self.BLUE, width=2.5)

        # 펄스 애니메이션 (바깥 원 확대/축소)
        self._pulse_ring = None
        self._pulse_step = 0

        def _pulse():
            if not root.winfo_exists():
                return
            if self._pulse_ring:
                c.delete(self._pulse_ring)
            s = self._pulse_step % 40
            scale = 1.0 + 0.15 * math.sin(s * math.pi / 20)
            pr = r * scale
            alpha_hex = format(int(80 * (1 - abs(math.sin(s * math.pi / 20)))), '02x')
            self._pulse_ring = c.create_oval(
                cx - pr, cy - pr, cx + pr, cy + pr,
                outline=self.BLUE, width=2, dash=(4, 3))
            self._pulse_step += 1
            self._anim_id = root.after(80, _pulse)

        _pulse()

    def _draw_check_icon(self, c: tk.Canvas):
        """초록 원 + 체크마크."""
        cx, cy, r = 36, 36, 30

        # 배경 원
        c.create_oval(cx - r, cy - r, cx + r, cy + r,
                      fill="#e8f8ed", outline="#a3e4b8", width=1.5)

        # 안쪽 원
        c.create_oval(cx - 20, cy - 20, cx + 20, cy + 20,
                      fill=self.GREEN, outline="")

        # 체크마크 (두꺼운 흰 선)
        c.create_line(26, 36, 33, 44, fill=self.WHITE, width=3.5,
                      capstyle="round", joinstyle="round")
        c.create_line(33, 44, 47, 28, fill=self.WHITE, width=3.5,
                      capstyle="round", joinstyle="round")

    # ──────────────────────────────────────────────────────────────
    # UI 컴포넌트
    # ──────────────────────────────────────────────────────────────
    def _make_root(self, w, h):
        root = tk.Tk()
        self._root = root
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.97)
        root.configure(bg=self.BORDER)

        screen_w = root.winfo_screenwidth()
        x = (screen_w - w) // 2
        root.geometry(f"{w}x{h}+{x}+28")
        return root

    def _make_card(self, root):
        """흰 카드 + 미세 border (Apple 스타일)."""
        # border 역할
        outer = tk.Frame(root, bg=self.BORDER, padx=1, pady=1)
        outer.pack(fill="both", expand=True)

        card = tk.Frame(outer, bg=self.CARD, padx=28, pady=24)
        card.pack(fill="both", expand=True)
        return card

    def _mac_close_btn(self, parent, root):
        """macOS 빨간 원 닫기 버튼."""
        c = tk.Canvas(parent, width=16, height=16,
                      bg=self.CARD, highlightthickness=0, cursor="hand2")
        c.pack(anchor="ne", pady=(0, 8))

        circle_id = c.create_oval(2, 2, 14, 14, fill=self.RED, outline="#e0352b")
        x_items = []

        def _enter(e):
            x_items.append(c.create_line(5, 5, 11, 11, fill=self.WHITE, width=1.5))
            x_items.append(c.create_line(11, 5, 5, 11, fill=self.WHITE, width=1.5))

        def _leave(e):
            for item in x_items:
                c.delete(item)
            x_items.clear()

        c.bind("<Enter>", _enter)
        c.bind("<Leave>", _leave)
        c.bind("<Button-1>", lambda e: root.destroy())
        return c

    def _pill_btn(self, parent, text, bg, fg, cmd, side="top", padx=0):
        """Apple pill 버튼."""
        btn = tk.Frame(parent, bg=bg, padx=1, pady=1, cursor="hand2")
        btn.pack(side=side, padx=padx)

        inner = tk.Label(btn, text=f"   {text}   ", bg=bg, fg=fg,
                         font=self._fn(13, "bold"), padx=14, pady=7)
        inner.pack()

        def _enter(e):
            if bg == self.BLUE:
                inner.configure(bg=self.BLUE_HOVER)
                btn.configure(bg=self.BLUE_HOVER)
            else:
                inner.configure(bg=self.HOVER_BG)
                btn.configure(bg=self.HOVER_BG)

        def _leave(e):
            inner.configure(bg=bg)
            btn.configure(bg=bg)

        for w in (btn, inner):
            w.bind("<Button-1>", lambda e: cmd())
            w.bind("<Enter>", _enter)
            w.bind("<Leave>", _leave)

        return btn

    def _fn(self, size, weight="normal"):
        for family in ("SF Pro Display", "Segoe UI", "Malgun Gothic"):
            try:
                return tkfont.Font(family=family, size=size, weight=weight)
            except Exception:
                continue
        return tkfont.Font(size=size, weight=weight)

    def _draggable(self, widget, root):
        def _start(e):
            root._dx, root._dy = e.x, e.y

        def _move(e):
            root.geometry(f"+{root.winfo_x() + e.x - root._dx}+{root.winfo_y() + e.y - root._dy}")

        widget.bind("<ButtonPress-1>", _start)
        widget.bind("<B1-Motion>", _move)


# ── API ──
_overlay = RPAOverlay()
show_working = _overlay.show_working
show_complete = _overlay.show_complete
close = _overlay.close
