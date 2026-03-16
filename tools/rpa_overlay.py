"""
BRIDGE RPA Overlay — iOS Alert Style
=====================================
Apple HIG 기반. 보더 없는 플로팅 카드 + 드롭 섀도.
애니메이션 V 체크마크. iOS 텍스트 액션 버튼.
"""

import math
import threading
import tkinter as tk
from tkinter import font as tkfont

_post_more_event = threading.Event()
_stop_event      = threading.Event()


def wants_more() -> bool:
    result = _post_more_event.is_set()
    _post_more_event.clear()
    return result


def stop_requested() -> bool:
    """RPA 루프가 호출 — 그만하기/X 버튼 눌리면 True 반환 후 플래그 초기화."""
    result = _stop_event.is_set()
    _stop_event.clear()
    return result


class RPAOverlay:

    BG    = "#ffffff"
    TEXT1 = "#1d1d1f"
    TEXT2 = "#86868b"
    BLUE  = "#007aff"
    GREEN = "#34c759"
    RED   = "#ff3b30"
    SEP   = "#e5e5ea"
    HOVER = "#f2f2f7"
    HOVER_RED = "#fff1f0"
    X_GRAY = "#c7c7cc"
    _TRANS = "#010203"

    def __init__(self):
        self._root           = None
        self._thread         = None
        self._ready          = threading.Event()
        self._progress_label = None   # update_progress() 가 업데이트할 라벨

    def show_working(self, current: int = 0, total: int = 0, email: str = ""):
        self.close()
        _stop_event.clear()
        self._thread = threading.Thread(
            target=self._build_working,
            args=(current, total, email),
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(timeout=3)

    def show_complete(self, posted_count: int = 0):
        self.close()
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._build_complete, args=(posted_count,), daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def update_progress(self, current: int, total: int):
        """RPA 루프가 게시 완료마다 호출 — 진행 라벨 갱신."""
        if self._root and self._progress_label:
            try:
                self._root.after(
                    0,
                    lambda: self._progress_label.configure(
                        text=f"{current} / {total} 완료"
                    ) if self._progress_label.winfo_exists() else None
                )
            except Exception:
                pass

    def close(self):
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass
            self._root = None
        self._progress_label = None
        self._ready.clear()

    # ── 그만하기 공통 액션 (작업중 창 전용) ──────────────────────────────
    def _do_stop(self, root):
        """그만하기/X 클릭 → RPA 중단 신호 + 창 닫기."""
        _stop_event.set()
        try:
            root.destroy()
        except Exception:
            pass

    # ── WORKING ──────────────────────────────────────────────────────────
    def _build_working(self, current: int, total: int, email: str):
        root, card = self._make_window(340, 290)

        bar = self._top_bar_stop(card, root)   # X → 그만하기

        spinner = tk.Canvas(card, width=44, height=44,
                            bg=self.BG, highlightthickness=0)
        spinner.pack(pady=(4, 10))
        self._draw_spinner(spinner, root)

        title = tk.Label(card, text="Craig 작업중",
                         font=self._fn(18, "bold"),
                         bg=self.BG, fg=self.TEXT1)
        title.pack()

        sub = tk.Label(card, text="인터넷 창을 건들지 마세요",
                       font=self._fn(12), bg=self.BG, fg=self.TEXT2)
        sub.pack(pady=(4, 4))

        # 진행 카운터
        prog_text = f"{current} / {total} 완료" if total else "준비 중..."
        prog = tk.Label(card, text=prog_text,
                        font=self._fn(11), bg=self.BG, fg=self.TEXT2)
        prog.pack(pady=(0, 4))
        self._progress_label = prog

        # 이메일 표시 (있을 때만)
        if email:
            acct = tk.Label(card, text=email,
                            font=self._fn(10), bg=self.BG, fg=self.X_GRAY)
            acct.pack(pady=(0, 6))

        # 게임 OK 라인
        game_row = tk.Frame(card, bg=self.BG)
        game_row.pack(pady=(0, 10))
        gun = tk.Canvas(game_row, width=24, height=18,
                        bg=self.BG, highlightthickness=0)
        gun.pack(side="left", padx=(0, 4))
        self._draw_gun(gun)
        game_lbl = tk.Label(game_row, text="게임은 해도 됩니다!",
                            font=self._fn(11), bg=self.BG, fg=self.GREEN)
        game_lbl.pack(side="left")

        self._sep(card)
        self._action_stop(card, "그만하기", lambda: self._do_stop(root))

        self._drag(root, bar, spinner, title, sub, prog, game_row, game_lbl)
        self._ready.set()
        try:
            root.mainloop()
        except Exception:
            pass

    # ── COMPLETE ─────────────────────────────────────────────────────────
    def _build_complete(self, count: int):
        root, card = self._make_window(340, 300)

        bar = self._top_bar(card, root)

        chk = tk.Canvas(card, width=60, height=50,
                        bg=self.BG, highlightthickness=0)
        chk.pack(pady=(4, 8))
        self._draw_check_animated(chk, root)

        title = tk.Label(card, text=f"광고 {count}건 완료",
                         font=self._fn(18, "bold"),
                         bg=self.BG, fg=self.TEXT1)
        title.pack()

        sub = tk.Label(card, text="개인정보 노출이 없는지 확인해 주세요",
                       font=self._fn(12), bg=self.BG, fg=self.TEXT2)
        sub.pack(pady=(4, 16))

        self._sep(card)

        def _more():
            _post_more_event.set()
            root.destroy()

        self._action(card, "5개 더 올리기", "bold", _more)
        self._sep(card)
        self._action(card, "닫기", "normal", lambda: root.destroy())

        self._drag(root, bar, chk, title, sub)
        root.after(60000,
                   lambda: root.destroy() if root.winfo_exists() else None)
        self._ready.set()
        try:
            root.mainloop()
        except Exception:
            pass

    # ── Drawing ──────────────────────────────────────────────────────────
    def _draw_spinner(self, c, root):
        """Apple activity indicator (rotating bars)."""
        cx, cy = 22, 22
        r_in, r_out = 7, 15
        n = 12
        self._si = 0

        def _tick():
            if not root.winfo_exists():
                return
            c.delete("sp")
            for i in range(n):
                a = 2 * math.pi * i / n - math.pi / 2
                x1 = cx + r_in * math.cos(a)
                y1 = cy + r_in * math.sin(a)
                x2 = cx + r_out * math.cos(a)
                y2 = cy + r_out * math.sin(a)
                d = (i - self._si) % n
                g = 80 + int(d * 140 / n)
                c.create_line(x1, y1, x2, y2,
                              fill=f"#{g:02x}{g:02x}{g:02x}",
                              width=2.5, capstyle="round", tags="sp")
            self._si = (self._si + 1) % n
            root.after(80, _tick)

        _tick()

    def _draw_check_animated(self, c, root):
        """Animated V checkmark — two-stroke draw."""
        p1 = (10, 22)
        p2 = (24, 40)
        p3 = (52, 8)
        s1, s2 = 8, 10

        def _anim(step=0):
            if not root.winfo_exists():
                return
            if step <= s1:
                t = step / s1
                c.delete("v1")
                c.create_line(p1[0], p1[1],
                              p1[0] + (p2[0] - p1[0]) * t,
                              p1[1] + (p2[1] - p1[1]) * t,
                              fill=self.GREEN, width=4,
                              capstyle="round", tags="v1")
            elif step <= s1 + s2:
                t = (step - s1) / s2
                c.delete("v2")
                c.create_line(p2[0], p2[1],
                              p2[0] + (p3[0] - p2[0]) * t,
                              p2[1] + (p3[1] - p2[1]) * t,
                              fill=self.GREEN, width=4,
                              capstyle="round", tags="v2")
            else:
                return
            root.after(30, lambda: _anim(step + 1))

        root.after(300, _anim)

    def _draw_gun(self, c):
        """Small pistol icon."""
        g = "#34c759"
        c.create_rectangle(10, 4, 23, 8, fill=g, outline="")
        c.create_rectangle(3, 4, 14, 12, fill=g, outline="")
        c.create_polygon(5, 12, 9, 12, 10, 17, 4, 17, fill=g, outline="")
        c.create_line(9, 12, 12, 12, 12, 14, 9, 14, fill=g, width=1.5)

    # ── UI Components ─────────────────────────────────────────────────────
    def _top_bar(self, parent, root):
        """완료 창용 X — 창만 닫음."""
        bar = tk.Frame(parent, bg=self.BG, height=28)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        xb = tk.Label(bar, text="\u2715", font=self._fn(10),
                      bg=self.BG, fg=self.X_GRAY, cursor="hand2")
        xb.pack(side="right", padx=(0, 6), pady=(4, 0))
        xb.bind("<Enter>", lambda e: xb.configure(fg=self.TEXT1))
        xb.bind("<Leave>", lambda e: xb.configure(fg=self.X_GRAY))
        xb.bind("<Button-1>", lambda e: root.destroy())
        return bar

    def _top_bar_stop(self, parent, root):
        """작업중 창용 X — RPA 중단 + 창 닫기."""
        bar = tk.Frame(parent, bg=self.BG, height=28)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        xb = tk.Label(bar, text="\u2715", font=self._fn(10),
                      bg=self.BG, fg=self.X_GRAY, cursor="hand2")
        xb.pack(side="right", padx=(0, 6), pady=(4, 0))
        xb.bind("<Enter>", lambda e: xb.configure(fg=self.RED))
        xb.bind("<Leave>", lambda e: xb.configure(fg=self.X_GRAY))
        xb.bind("<Button-1>", lambda e: self._do_stop(root))
        return bar

    def _sep(self, parent):
        tk.Frame(parent, bg=self.SEP, height=1).pack(fill="x")

    def _action(self, parent, text, weight, cmd):
        """일반 파란색 버튼."""
        btn = tk.Label(parent, text=text,
                       font=self._fn(15, weight),
                       bg=self.BG, fg=self.BLUE,
                       pady=12, cursor="hand2")
        btn.pack(fill="x")
        btn.bind("<Enter>", lambda e: btn.configure(bg=self.HOVER))
        btn.bind("<Leave>", lambda e: btn.configure(bg=self.BG))
        btn.bind("<Button-1>", lambda e: cmd())

    def _action_stop(self, parent, text, cmd):
        """그만하기 — 빨간색 버튼."""
        btn = tk.Label(parent, text=text,
                       font=self._fn(15, "bold"),
                       bg=self.BG, fg=self.RED,
                       pady=12, cursor="hand2")
        btn.pack(fill="x")
        btn.bind("<Enter>", lambda e: btn.configure(bg=self.HOVER_RED))
        btn.bind("<Leave>", lambda e: btn.configure(bg=self.BG))
        btn.bind("<Button-1>", lambda e: cmd())

    # ── Window ────────────────────────────────────────────────────────────
    def _make_window(self, w, h):
        """Clean white floating card."""
        root = tk.Tk()
        self._root = root
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.0)
        root.configure(bg=self.BG)

        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        card = tk.Frame(root, bg=self.BG)
        card.pack(fill="both", expand=True)

        def _fade(a=0.0):
            if not root.winfo_exists():
                return
            if a < 0.98:
                root.attributes("-alpha", a)
                root.after(16, lambda: _fade(a + 0.07))
            else:
                root.attributes("-alpha", 0.98)

        root.after(10, _fade)
        return root, card

    def _fn(self, size, weight="normal"):
        fam = "Pretendard"
        if weight == "bold":
            fam = "Pretendard Medium"
        return tkfont.Font(family=fam, size=size, weight=weight)

    def _drag(self, root, *widgets):
        def _press(e):
            root._dx, root._dy = e.x_root, e.y_root

        def _move(e):
            x = root.winfo_x() + e.x_root - root._dx
            y = root.winfo_y() + e.y_root - root._dy
            root._dx, root._dy = e.x_root, e.y_root
            root.geometry(f"+{x}+{y}")

        for w in widgets:
            w.bind("<ButtonPress-1>", _press)
            w.bind("<B1-Motion>", _move)


_overlay = RPAOverlay()
show_working     = _overlay.show_working
show_complete    = _overlay.show_complete
update_progress  = _overlay.update_progress
close            = _overlay.close
