"""
BRIDGE RPA Overlay — Apple-inspired Desktop Notification
=========================================================
macOS 스타일 알림. 주 모니터 상단 중앙.
2모니터 환경 게임 방해 없음. 보안: 개인정보 미표시.
"""

import threading
import tkinter as tk
from tkinter import font as tkfont

# "5개 더 올리기" 콜백용
_post_more_event = threading.Event()


def wants_more() -> bool:
    """메인 스크립트에서 호출: 유저가 '더 올리기' 눌렀는지 확인."""
    result = _post_more_event.is_set()
    _post_more_event.clear()
    return result


class RPAOverlay:
    """Apple-inspired 오버레이 (frosted glass, rounded, macOS 닫기 버튼)."""

    # ── Apple 색상 팔레트 ──
    WHITE = "#ffffff"
    BG = "#f5f5f7"
    TEXT_PRIMARY = "#1d1d1f"
    TEXT_SECONDARY = "#86868b"
    ACCENT_BLUE = "#0071e3"
    ACCENT_GREEN = "#34c759"
    ACCENT_RED = "#ff3b30"
    ACCENT_ORANGE = "#ff9500"
    BORDER = "#d2d2d7"
    CARD_BG = "#ffffff"
    SHADOW = "#e0e0e0"

    def __init__(self):
        self._root = None
        self._thread = None
        self._ready = threading.Event()

    def show_working(self):
        """작업 시작 — macOS 알림 스타일."""
        self.close()
        self._thread = threading.Thread(target=self._build_working, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def show_complete(self, posted_count: int = 0):
        """작업 완료 — 확인 요청 + 더 올리기 버튼."""
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
    # Working Overlay
    # ──────────────────────────────────────────────────────────────
    def _build_working(self):
        root = self._create_root(720, 160)

        # 외곽 shadow + border 프레임
        outer = tk.Frame(root, bg=self.BORDER, padx=1, pady=1)
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        card = tk.Frame(outer, bg=self.CARD_BG, padx=28, pady=20)
        card.pack(fill="both", expand=True)

        # ── 상단 바: macOS 닫기 버튼 (빨간 원) ──
        top_bar = tk.Frame(card, bg=self.CARD_BG)
        top_bar.pack(fill="x", pady=(0, 12))

        close_circle = tk.Canvas(top_bar, width=14, height=14,
                                 bg=self.CARD_BG, highlightthickness=0)
        close_circle.pack(side="left")
        close_circle.create_oval(1, 1, 13, 13, fill=self.ACCENT_RED,
                                 outline="#e0352b", width=1)
        close_circle.bind("<Button-1>", lambda e: root.destroy())
        close_circle.bind("<Enter>", lambda e: close_circle.create_text(
            7, 7, text="×", fill="white", font=("Arial", 8, "bold")))
        close_circle.bind("<Leave>", lambda e: [
            close_circle.delete("all"),
            close_circle.create_oval(1, 1, 13, 13, fill=self.ACCENT_RED,
                                     outline="#e0352b", width=1)])

        # 우측 X 버튼
        x_btn = self._make_text_btn(top_bar, "✕", self.TEXT_SECONDARY,
                                    self.CARD_BG, 13, lambda: root.destroy())
        x_btn.pack(side="right")

        # ── 메인 콘텐츠 ──
        content = tk.Frame(card, bg=self.CARD_BG)
        content.pack(fill="both", expand=True)

        # 이모지
        emoji_lbl = tk.Label(content, text="👨‍💻", bg=self.CARD_BG,
                             font=self._emoji_font(42))
        emoji_lbl.pack(side="left", padx=(0, 20))

        # 텍스트
        text_area = tk.Frame(content, bg=self.CARD_BG)
        text_area.pack(side="left", fill="both", expand=True)

        tk.Label(text_area, text="크래이그 작업중",
                 font=self._font(20, "bold"), bg=self.CARD_BG,
                 fg=self.TEXT_PRIMARY, anchor="w").pack(anchor="w")

        tk.Label(text_area,
                 text="인터넷 창을 건들지 마세요! 🙏",
                 font=self._font(13), bg=self.CARD_BG,
                 fg=self.TEXT_SECONDARY, anchor="w").pack(anchor="w", pady=(4, 0))

        # ── 하단: 닫기 버튼 ──
        btn_frame = tk.Frame(card, bg=self.CARD_BG)
        btn_frame.pack(fill="x", pady=(12, 0))

        self._make_pill_btn(btn_frame, "닫기", self.BG, self.TEXT_PRIMARY,
                            lambda: root.destroy()).pack(side="right")

        # 드래그
        self._enable_drag(card, root)
        self._enable_drag(content, root)

        self._ready.set()
        try:
            root.mainloop()
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # Complete Overlay
    # ──────────────────────────────────────────────────────────────
    def _build_complete(self, posted_count: int):
        root = self._create_root(720, 220)

        outer = tk.Frame(root, bg=self.BORDER, padx=1, pady=1)
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        card = tk.Frame(outer, bg=self.CARD_BG, padx=28, pady=20)
        card.pack(fill="both", expand=True)

        # ── 상단 바 ──
        top_bar = tk.Frame(card, bg=self.CARD_BG)
        top_bar.pack(fill="x", pady=(0, 12))

        close_circle = tk.Canvas(top_bar, width=14, height=14,
                                 bg=self.CARD_BG, highlightthickness=0)
        close_circle.pack(side="left")
        close_circle.create_oval(1, 1, 13, 13, fill=self.ACCENT_RED,
                                 outline="#e0352b", width=1)
        close_circle.bind("<Button-1>", lambda e: root.destroy())
        close_circle.bind("<Enter>", lambda e: close_circle.create_text(
            7, 7, text="×", fill="white", font=("Arial", 8, "bold")))
        close_circle.bind("<Leave>", lambda e: [
            close_circle.delete("all"),
            close_circle.create_oval(1, 1, 13, 13, fill=self.ACCENT_RED,
                                     outline="#e0352b", width=1)])

        x_btn = self._make_text_btn(top_bar, "✕", self.TEXT_SECONDARY,
                                    self.CARD_BG, 13, lambda: root.destroy())
        x_btn.pack(side="right")

        # ── 메인 콘텐츠 ──
        content = tk.Frame(card, bg=self.CARD_BG)
        content.pack(fill="both", expand=True)

        emoji_lbl = tk.Label(content, text="🎉", bg=self.CARD_BG,
                             font=self._emoji_font(42))
        emoji_lbl.pack(side="left", padx=(0, 20))

        text_area = tk.Frame(content, bg=self.CARD_BG)
        text_area.pack(side="left", fill="both", expand=True)

        tk.Label(text_area, text=f"광고 {posted_count}건 완료!",
                 font=self._font(20, "bold"), bg=self.CARD_BG,
                 fg=self.ACCENT_GREEN, anchor="w").pack(anchor="w")

        tk.Label(text_area,
                 text="개인정보 노출이 없도록\n한번 더 직접 확인해주세요 🙏",
                 font=self._font(13), bg=self.CARD_BG,
                 fg=self.TEXT_SECONDARY, anchor="w",
                 justify="left").pack(anchor="w", pady=(6, 0))

        # ── 하단 버튼 ──
        btn_frame = tk.Frame(card, bg=self.CARD_BG)
        btn_frame.pack(fill="x", pady=(16, 0))

        def _on_post_more():
            _post_more_event.set()
            root.destroy()

        self._make_pill_btn(btn_frame, "5개 더 올리기 🚀",
                            self.ACCENT_BLUE, self.WHITE,
                            _on_post_more).pack(side="right", padx=(10, 0))

        self._make_pill_btn(btn_frame, "닫기",
                            self.BG, self.TEXT_PRIMARY,
                            lambda: root.destroy()).pack(side="right")

        # 드래그
        self._enable_drag(card, root)
        self._enable_drag(content, root)

        # 60초 후 자동 닫기
        root.after(60000, lambda: root.destroy() if root.winfo_exists() else None)

        self._ready.set()
        try:
            root.mainloop()
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # 헬퍼
    # ──────────────────────────────────────────────────────────────
    def _create_root(self, w, h):
        root = tk.Tk()
        self._root = root
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.96)
        root.configure(bg=self.SHADOW)

        screen_w = root.winfo_screenwidth()
        x = (screen_w - w) // 2
        root.geometry(f"{w}x{h}+{x}+24")
        return root

    def _font(self, size, weight="normal"):
        try:
            return tkfont.Font(family="Segoe UI", size=size, weight=weight)
        except Exception:
            return tkfont.Font(size=size, weight=weight)

    def _emoji_font(self, size):
        try:
            return tkfont.Font(family="Segoe UI Emoji", size=size)
        except Exception:
            return tkfont.Font(size=size)

    def _make_text_btn(self, parent, text, fg, bg, size, command):
        lbl = tk.Label(parent, text=text, fg=fg, bg=bg, cursor="hand2",
                       font=self._font(size))
        lbl.bind("<Button-1>", lambda e: command())
        lbl.bind("<Enter>", lambda e: lbl.configure(fg=self.ACCENT_RED))
        lbl.bind("<Leave>", lambda e: lbl.configure(fg=fg))
        return lbl

    def _make_pill_btn(self, parent, text, bg_color, fg_color, command):
        """Apple 스타일 pill 버튼 (rounded-full)."""
        btn = tk.Label(parent, text=f"  {text}  ", bg=bg_color, fg=fg_color,
                       cursor="hand2", font=self._font(12, "bold"),
                       padx=16, pady=6,
                       relief="flat", borderwidth=0)
        btn.bind("<Button-1>", lambda e: command())

        # hover 효과
        def _enter(e):
            if bg_color == self.ACCENT_BLUE:
                btn.configure(bg="#005ec4")
            elif bg_color == self.BG:
                btn.configure(bg="#e8e8ed")

        def _leave(e):
            btn.configure(bg=bg_color)

        btn.bind("<Enter>", _enter)
        btn.bind("<Leave>", _leave)
        return btn

    def _enable_drag(self, widget, root):
        def _start(event):
            root._drag_x = event.x
            root._drag_y = event.y

        def _drag(event):
            nx = root.winfo_x() + (event.x - root._drag_x)
            ny = root.winfo_y() + (event.y - root._drag_y)
            root.geometry(f"+{nx}+{ny}")

        widget.bind("<ButtonPress-1>", _start)
        widget.bind("<B1-Motion>", _drag)


# ── 싱글턴 ──
_overlay = RPAOverlay()


def show_working():
    _overlay.show_working()


def show_complete(posted_count: int = 0):
    _overlay.show_complete(posted_count)


def close():
    _overlay.close()
