"""
BRIDGE RPA Overlay — iOS Dark v3 (Apple Aesthetic)
===================================================
두-톤 헤더(CARD #252527) + BG 바디(#1c1c1e).
귀여운 로봇 캐릭터 애니메이션 (눈 글로우 · 안테나 흔들림 · LED 깜박임).
Pill 프로그레스 바. 상태 블링크.
"""

import json
import math
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import font as tkfont
import winsound

try:
    from screeninfo import get_monitors
    _HAS_SCREENINFO = True
except ImportError:
    _HAS_SCREENINFO = False

_post_more_event = threading.Event()
_stop_event = threading.Event()


def wants_more() -> bool:
    result = _post_more_event.is_set()
    _post_more_event.clear()
    return result


def stop_requested() -> bool:
    return _stop_event.is_set()


class RPAOverlay:

    BG     = "#1c1c1e"
    CARD   = "#252527"      # header default
    TEXT1  = "#ffffff"
    TEXT2  = "#aeaeb2"
    BLUE   = "#0a84ff"
    RED    = "#ff453a"
    GREEN  = "#30d158"
    SEP    = "#38383a"
    HOVER  = "#3a3a3c"
    X_GRAY = "#636366"
    BAR_BG = "#3a3a3c"
    GOLD   = "#ffd60a"

    # 계정별 헤더 색상 (뚜렷하게 구별되는 4가지)
    _HEADER_COLORS = {
        "coreabridge@gmail.com":    "#163520",   # 짙은 숲초록
        "airelair00@gmail.com":     "#220f3c",   # 짙은 보라
        "ferrari812fast@gmail.com": "#351c04",   # 짙은 호박색
        "bridgejobkr@gmail.com":    "#0c2044",   # 짙은 네이비
    }

    _STATUS_CYCLE = [
        "작업준비중", "로그인중", "카테고리선택중",
        "제목작성중", "폼입력중", "이미지업로드중", "게시중",
    ]

    def __init__(self):
        self._root             = None
        self._thread           = None
        self._ready            = threading.Event()
        self._progress_var     = [0, 0]
        self._prog_bar_canvas  = None
        self._prog_pct_label   = None
        self._prog_count_label = None
        self._status_label     = None
        self._status_text      = ""
        self._is_working       = False
        self._remind_timer     = None
        self._email            = ""
        self._bot_t            = 0.0
        self._card_color       = "#252527"

    # ── Public API ────────────────────────────
    def show_working(self, current: int = 0, total: int = 0, email: str = ""):
        self.close()
        self._is_working   = True
        self._progress_var = [current, total]
        self._email        = email
        self._bot_t        = 0.0
        self._card_color   = self._HEADER_COLORS.get(email.lower(), self.CARD)
        self._thread = threading.Thread(target=self._build_working, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def update_progress(self, current: int, total: int):
        self._progress_var = [current, total]
        if self._root:
            try:
                self._root.after(0, lambda: self._refresh_progress(current, total))
            except Exception:
                pass

    def update_status(self, text: str):
        """외부에서 상태 텍스트 직접 설정."""
        self._status_text = text
        if self._root and self._status_label:
            try:
                self._root.after(0, lambda: self._set_status_text(text))
            except Exception:
                pass

    def _set_status_text(self, text: str):
        try:
            if self._status_label and self._status_label.winfo_exists():
                self._status_label.configure(text=text, fg=self.BLUE)
        except Exception:
            pass

    def show_complete(self, posted_count: int = 0):
        self._is_working = False
        self.close()
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._build_complete, args=(posted_count,), daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)
        threading.Thread(target=self._play_complete_sound, daemon=True).start()

    @staticmethod
    def _play_complete_sound():
        try:
            for freq, dur in [(523, 120), (659, 120), (784, 120), (1047, 200)]:
                winsound.Beep(freq, dur)
        except Exception:
            pass

    def close(self):
        self._is_working = False
        self._stop_remind()
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass
            self._root = None
        self._ready.clear()

    def _dismiss_and_remind(self):
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None
        self._ready.clear()
        if self._is_working:
            self._remind_timer = threading.Timer(30.0, self._re_show_working)
            self._remind_timer.daemon = True
            self._remind_timer.start()

    def _re_show_working(self):
        if not self._is_working:
            return
        self._thread = threading.Thread(target=self._build_working, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def _stop_remind(self):
        if self._remind_timer:
            self._remind_timer.cancel()
            self._remind_timer = None

    # ── WORKING window ────────────────────────
    def _build_working(self):
        _stop_event.clear()
        CC = self._card_color          # 계정별 헤더 색
        root, card = self._make_window(520, 360)

        # ══ HEADER (계정 색 배경) ═══════════════
        header = tk.Frame(card, bg=CC)
        header.pack(fill="x")

        # 닫기 버튼 (헤더 우상단)
        bar = tk.Frame(header, bg=CC, height=26)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        xb = tk.Label(bar, text="\u2715", font=self._fn(10),
                      bg=CC, fg=self.X_GRAY, cursor="hand2")
        xb.pack(side="right", padx=(0, 10), pady=(4, 0))
        xb.bind("<Enter>", lambda e: xb.configure(fg=self.TEXT1))
        xb.bind("<Leave>", lambda e: xb.configure(fg=self.X_GRAY))
        xb.bind("<Button-1>", lambda e: self._dismiss_and_remind())

        # 봇 + 타이틀
        bot_row = tk.Frame(header, bg=CC)
        bot_row.pack(padx=20, pady=(4, 16), anchor="w")

        bot_c = tk.Canvas(bot_row, width=64, height=80,
                          bg=CC, highlightthickness=0)
        bot_c.pack(side="left", padx=(0, 16))
        self._draw_bot(bot_c, root)

        info_col = tk.Frame(bot_row, bg=CC)
        info_col.pack(side="left", anchor="w")

        tk.Label(info_col, text="Craig RPA",
                 font=self._fn(17, "bold"),
                 bg=CC, fg=self.TEXT1, anchor="w").pack(anchor="w")

        if self._email:
            tk.Label(info_col, text=self._email,
                     font=self._fn(11),
                     bg=CC, fg=self.TEXT1, anchor="w").pack(anchor="w", pady=(6, 0))

        # ══ SEPARATOR ══════════════════════════
        tk.Frame(card, bg=self.SEP, height=1).pack(fill="x")

        # ══ BODY (BG 배경) ══════════════════════
        cur, tot = self._progress_var or [0, 0]
        body = tk.Frame(card, bg=self.BG)
        body.pack(fill="x", padx=20, pady=(12, 8))

        # % · 상태 · 카운트 행
        pct_row = tk.Frame(body, bg=self.BG)
        pct_row.pack(fill="x", pady=(0, 8))

        self._prog_pct_label = tk.Label(
            pct_row, text=self._pct_text(cur, tot),
            font=self._fn(15, "bold"), bg=self.BG, fg=self.TEXT1)
        self._prog_pct_label.pack(side="left")

        tk.Label(pct_row, text="  ·  ",
                 font=self._fn(10), bg=self.BG, fg=self.TEXT2).pack(side="left")

        self._status_label = tk.Label(
            pct_row, text=self._STATUS_CYCLE[0],
            font=self._fn(10), bg=self.BG, fg=self.BLUE)
        self._status_label.pack(side="left")

        self._prog_count_label = tk.Label(
            pct_row, text=self._prog_text(cur, tot),
            font=self._fn(10), bg=self.BG, fg=self.TEXT2)
        self._prog_count_label.pack(side="right")

        # Pill 프로그레스 바 (520 - 2border - 40pad = 478)
        BAR_W, BAR_H = 478, 10
        self._prog_bar_canvas = tk.Canvas(
            body, width=BAR_W, height=BAR_H,
            bg=self.BG, highlightthickness=0)
        self._prog_bar_canvas.pack()
        self._draw_pill_bar(BAR_W, BAR_H, cur, tot)

        # 개인정보 경고
        warn_row = tk.Frame(card, bg=self.BG)
        warn_row.pack(pady=(10, 0), padx=20, anchor="w")
        tk.Label(warn_row, text="\u26a0",
                 font=self._fn(12), bg=self.BG, fg=self.GOLD).pack(side="left", padx=(0, 6))
        tk.Label(warn_row, text="개인정보 확인 필수",
                 font=self._fn(12, "bold"), bg=self.BG, fg=self.TEXT1).pack(side="left")

        # 스페이서
        tk.Frame(card, bg=self.BG).pack(fill="both", expand=True)

        # ══ BUTTONS ════════════════════════════
        tk.Frame(card, bg=self.SEP, height=1).pack(fill="x")
        btn_row = tk.Frame(card, bg=self.BG)
        btn_row.pack(fill="x")
        self._action_inline(btn_row, "닫기", "normal", self.BLUE,
                            lambda: self._dismiss_and_remind(), "left")
        tk.Frame(btn_row, bg=self.SEP, width=1).pack(side="left", fill="y")
        self._action_inline(btn_row, "중단하기", "normal", self.RED,
                            lambda: self._confirm_stop_popup(root), "left")

        # 애니메이션
        self._start_status_blink(root)
        self._start_pulse_bar(root)

        self._drag(root, header, bar, bot_row, bot_c, info_col, warn_row)
        self._ready.set()
        try:
            root.mainloop()
        except Exception:
            pass

    # ── Cute Robot animation ──────────────────
    def _draw_bot(self, c, root):
        """64×80 귀여운 로봇. 눈 글로우, 안테나 흔들림, 가슴 LED."""
        # Bot drawing runs on the tkinter thread — safe to access self._bot_t
        def _tick():
            if not root.winfo_exists():
                return
            c.delete("bot")
            t = self._bot_t

            # ── Antenna oscillation ──
            ant_off = int(2.2 * math.sin(t * 1.5))

            # ── Eye glow (0.55 → 1.0) ──
            glow   = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(t * 2.4))
            e_fill = self._lerp_color("#003478", "#0a84ff", glow)
            e_hi   = self._lerp_color("#1a4a88", "#5ab8ff", glow)

            # ── Head shadow ──
            c.create_oval(8, 13, 58, 53,
                          fill="#0e0e10", outline="", tags="bot")

            # ── Head ──
            c.create_oval(6, 10, 58, 52,
                          fill="#2c2c2e", outline="#48484a", width=1.5, tags="bot")

            # ── Left eye ──
            c.create_oval(14, 22, 28, 36, fill=e_fill,  outline="", tags="bot")
            c.create_oval(15, 23, 24, 31, fill=e_hi,    outline="", tags="bot")
            c.create_oval(15, 23, 19, 27, fill="#c8e8ff", outline="", tags="bot")  # shine

            # ── Right eye ──
            c.create_oval(36, 22, 50, 36, fill=e_fill,  outline="", tags="bot")
            c.create_oval(37, 23, 46, 31, fill=e_hi,    outline="", tags="bot")
            c.create_oval(37, 23, 41, 27, fill="#c8e8ff", outline="", tags="bot")

            # ── Smile ──
            c.create_arc(18, 34, 46, 52, start=210, extent=120,
                         style="arc", outline=self.GREEN, width=2.5, tags="bot")

            # ── Cheeks (cute blush) ──
            c.create_oval( 7, 33, 15, 39, fill="#ff6b8a", outline="", stipple="gray50", tags="bot")
            c.create_oval(49, 33, 57, 39, fill="#ff6b8a", outline="", stipple="gray50", tags="bot")

            # ── Antenna pole ──
            c.create_line(32, 10, 32, 3 + ant_off,
                          fill="#636366", width=2, tags="bot")
            # Antenna ball
            c.create_oval(27, -2 + ant_off, 37, 8 + ant_off,
                          fill=self.GOLD, outline="", tags="bot")
            c.create_oval(28, -1 + ant_off, 32, 3 + ant_off,
                          fill="#ffe880", outline="", tags="bot")  # shine

            # ── Torso ──
            c.create_rectangle(18, 53, 46, 66,
                               fill="#2c2c2e", outline="#48484a", width=1, tags="bot")
            # Chest LED
            led_bright = 0.5 + 0.5 * math.sin(t * 3.6)
            led_col    = self._lerp_color("#1a5e2a", self.GREEN, led_bright)
            c.create_oval(28, 56, 36, 63, fill=led_col,  outline="", tags="bot")
            if led_bright > 0.7:
                c.create_oval(29, 57, 33, 60, fill="#90ffa0", outline="", tags="bot")

            self._bot_t += 0.08
            root.after(80, _tick)

        _tick()

    @staticmethod
    def _lerp_color(c1: str, c2: str, t: float) -> str:
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        t = max(0.0, min(1.0, t))
        return "#{:02x}{:02x}{:02x}".format(
            int(r1 + (r2 - r1) * t),
            int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t))

    # ── Pill progress bar ──────────────────────
    def _draw_pill_bar(self, bar_w, bar_h, cur, tot):
        c = self._prog_bar_canvas
        if not c:
            return
        try:
            if not c.winfo_exists():
                return
        except Exception:
            return
        c.delete("all")
        r = bar_h

        c.create_rectangle(r // 2, 0, bar_w - r // 2, bar_h,
                           fill=self.BAR_BG, outline="")
        c.create_oval(0, 0, r, bar_h, fill=self.BAR_BG, outline="")
        c.create_oval(bar_w - r, 0, bar_w, bar_h, fill=self.BAR_BG, outline="")

        pct     = 0.0 if tot <= 0 else min(1.0, cur / tot)
        fill_px = int(pct * bar_w)

        if fill_px > 0:
            c.create_oval(0, 0, r, bar_h, fill=self.GREEN, outline="")
            right_x = min(fill_px, bar_w - r // 2)
            if right_x > r // 2:
                c.create_rectangle(r // 2, 0, right_x, bar_h,
                                   fill=self.GREEN, outline="")
            if fill_px >= bar_w - r // 2:
                c.create_oval(bar_w - r, 0, bar_w, bar_h,
                              fill=self.GREEN, outline="")

    # ── Status blink ──────────────────────────
    def _start_status_blink(self, root):
        tick    = [0]
        visible = [True]

        def _blink():
            if not root.winfo_exists():
                return
            visible[0] = not visible[0]
            try:
                if self._status_label and self._status_label.winfo_exists():
                    if visible[0]:
                        tick[0] += 1
                        txt = (self._status_text if self._status_text
                               else self._STATUS_CYCLE[(tick[0] // 2) % len(self._STATUS_CYCLE)])
                        self._status_label.configure(text=txt, fg=self.BLUE)
                    else:
                        self._status_label.configure(fg="#1e3a5a")
            except Exception:
                pass
            root.after(700, _blink)

        _blink()

    def _start_pulse_bar(self, root):
        def _pulse():
            if not root.winfo_exists():
                return
            cur, tot = self._progress_var or [0, 0]
            self._refresh_progress(cur, tot)
            root.after(500, _pulse)
        _pulse()

    def _refresh_progress(self, cur, tot):
        try:
            if self._prog_pct_label and self._prog_pct_label.winfo_exists():
                self._prog_pct_label.configure(text=self._pct_text(cur, tot))
            if self._prog_count_label and self._prog_count_label.winfo_exists():
                self._prog_count_label.configure(text=self._prog_text(cur, tot))
            self._draw_pill_bar(478, 10, cur, tot)
        except Exception:
            pass

    # ── Stop confirmation popup ───────────────
    def _confirm_stop_popup(self, parent_root):
        popup = tk.Toplevel(parent_root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg=self.BG)

        pw, ph = 380, 250
        px = parent_root.winfo_x() + (580 - pw) // 2
        py = parent_root.winfo_y() + (390 - ph) // 2
        popup.geometry(f"{pw}x{ph}+{px}+{py}")
        popup.attributes("-alpha", 0.0)

        def _fade(a=0.0):
            if popup.winfo_exists():
                if a < 1.0:
                    popup.attributes("-alpha", a)
                    popup.after(16, lambda: _fade(a + 0.12))
                else:
                    popup.attributes("-alpha", 1.0)
        popup.after(10, _fade)

        border = tk.Frame(popup, bg=self.SEP, padx=1, pady=1)
        border.pack(fill="both", expand=True)
        inner = tk.Frame(border, bg=self.BG)
        inner.pack(fill="both", expand=True)

        tk.Label(inner, text="\U0001f916",
                 font=tkfont.Font(family="Segoe UI Emoji", size=30),
                 bg=self.BG).pack(pady=(18, 6))
        tk.Label(inner, text="Claude가 중단을 요청합니다",
                 font=self._fn(13, "bold"),
                 bg=self.BG, fg=self.TEXT1).pack()
        tk.Label(inner, text="현재 건 완료 후 자동으로 중단됩니다.",
                 font=self._fn(10),
                 bg=self.BG, fg=self.TEXT2).pack(pady=(4, 0))

        tk.Frame(inner, bg=self.BG).pack(fill="both", expand=True)
        tk.Frame(inner, bg=self.SEP, height=1).pack(fill="x")

        btn_row = tk.Frame(inner, bg=self.BG)
        btn_row.pack(fill="x")

        def _do_stop():
            _stop_event.set()
            self._stop_remind()
            try: popup.destroy()
            except Exception: pass
            try: parent_root.destroy()
            except Exception: pass

        def _cancel():
            try: popup.destroy()
            except Exception: pass

        cont_btn = tk.Label(btn_row, text="계속하기",
                            font=self._fn(13, "bold"),
                            bg=self.BG, fg=self.BLUE, pady=14, cursor="hand2")
        cont_btn.pack(side="left", expand=True, fill="both")
        cont_btn.bind("<Button-1>", lambda e: _cancel())
        cont_btn.bind("<Enter>", lambda e: cont_btn.configure(bg=self.HOVER))
        cont_btn.bind("<Leave>", lambda e: cont_btn.configure(bg=self.BG))

        tk.Frame(btn_row, bg=self.SEP, width=1).pack(side="left", fill="y")

        stop_btn = tk.Label(btn_row, text="중단하기",
                            font=self._fn(13, "bold"),
                            bg=self.BG, fg=self.RED, pady=14, cursor="hand2")
        stop_btn.pack(side="left", expand=True, fill="both")
        stop_btn.bind("<Button-1>", lambda e: _do_stop())
        stop_btn.bind("<Enter>", lambda e: stop_btn.configure(bg=self.HOVER))
        stop_btn.bind("<Leave>", lambda e: stop_btn.configure(bg=self.BG))

    # ── COMPLETE window ───────────────────────
    def _build_complete(self, count: int):
        root, card = self._make_window(420, 300)

        bar = self._top_bar(card, root)

        chk = tk.Canvas(card, width=60, height=50,
                        bg=self.BG, highlightthickness=0)
        chk.pack(pady=(4, 8))
        self._draw_check_animated(chk, root)

        title = tk.Label(card, text=f"\u2728 광고 {count}건 완료",
                         font=self._fn(17, "bold"),
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

    # ── Progress helpers ──────────────────────
    @staticmethod
    def _prog_text(cur, tot):
        if tot <= 0:
            return "준비 중…"
        return f"{cur} / {tot} 완료"

    @staticmethod
    def _pct_text(cur, tot):
        if tot <= 0:
            return "0%"
        return f"{int(cur / tot * 100)}%"

    # ── Drawing ──────────────────────────────
    def _draw_check_animated(self, c, root):
        p1 = (10, 22); p2 = (24, 40); p3 = (52, 8)
        s1, s2 = 8, 10

        def _anim(step=0):
            if not root.winfo_exists():
                return
            if step <= s1:
                t = step / s1
                c.delete("v1")
                c.create_line(p1[0], p1[1],
                              p1[0] + (p2[0]-p1[0])*t, p1[1] + (p2[1]-p1[1])*t,
                              fill=self.GREEN, width=4, capstyle="round", tags="v1")
            elif step <= s1 + s2:
                t = (step - s1) / s2
                c.delete("v2")
                c.create_line(p2[0], p2[1],
                              p2[0] + (p3[0]-p2[0])*t, p2[1] + (p3[1]-p2[1])*t,
                              fill=self.GREEN, width=4, capstyle="round", tags="v2")
            else:
                return
            root.after(30, lambda: _anim(step + 1))

        root.after(300, _anim)

    # ── UI Components ────────────────────────
    def _top_bar(self, parent, root):
        bar = tk.Frame(parent, bg=self.BG, height=28)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        xb = tk.Label(bar, text="\u2715", font=self._fn(10),
                      bg=self.BG, fg=self.X_GRAY, cursor="hand2")
        xb.pack(side="right", padx=(0, 6), pady=(4, 0))
        xb.bind("<Enter>", lambda e: xb.configure(fg=self.TEXT1))
        xb.bind("<Leave>", lambda e: xb.configure(fg=self.X_GRAY))
        xb.bind("<Button-1>", lambda e: self._dismiss_and_remind())
        return bar

    def _sep(self, parent):
        tk.Frame(parent, bg=self.SEP, height=1).pack(fill="x")

    def _action(self, parent, text, weight, cmd):
        btn = tk.Label(parent, text=text,
                       font=self._fn(15, weight),
                       bg=self.BG, fg=self.BLUE, pady=12, cursor="hand2")
        btn.pack(fill="x")
        btn.bind("<Enter>", lambda e: btn.configure(bg=self.HOVER))
        btn.bind("<Leave>", lambda e: btn.configure(bg=self.BG))
        btn.bind("<Button-1>", lambda e: cmd())

    def _action_inline(self, parent, text, weight, color, cmd, side):
        btn = tk.Label(parent, text=text,
                       font=tkfont.Font(family="Malgun Gothic", size=15, weight=weight),
                       bg=self.BG, fg=color, pady=18, padx=24, cursor="hand2")
        btn.pack(side=side, expand=True, fill="both")
        btn.bind("<Enter>", lambda e: btn.configure(bg=self.HOVER))
        btn.bind("<Leave>", lambda e: btn.configure(bg=self.BG))
        btn.bind("<Button-1>", lambda e: cmd())

    # ── Window ───────────────────────────────
    def _make_window(self, w, h):
        root = tk.Tk()
        self._root = root
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.0)
        root.configure(bg=self.BG)

        mx, my, mw, mh = 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()
        if _HAS_SCREENINFO:
            try:
                mons = get_monitors()
                m    = mons[1] if len(mons) >= 2 else mons[0]
                mx, my, mw, mh = m.x, m.y, m.width, m.height
            except Exception:
                pass
        root.geometry(f"{w}x{h}+{mx + (mw - w) // 2}+{my + (mh - h) // 2}")

        border = tk.Frame(root, bg=self.SEP, padx=1, pady=1)
        border.pack(fill="both", expand=True)
        card = tk.Frame(border, bg=self.BG)
        card.pack(fill="both", expand=True)

        def _fade(a=0.0):
            if not root.winfo_exists():
                return
            if a < 1.0:
                root.attributes("-alpha", a)
                root.after(16, lambda: _fade(a + 0.07))
            else:
                root.attributes("-alpha", 1.0)

        root.after(10, _fade)
        return root, card

    def _fn(self, size, weight="normal"):
        return tkfont.Font(family="Malgun Gothic",
                           size=int(size * 1.2), weight=weight)

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


# ── Integrity check popup ─────────────────────────────────────────────────────
def ask_integrity_password() -> bool:
    """변조 감지 시 비밀번호 입력 팝업. 1234 입력 시 True 반환. 메인 스레드에서 실행."""
    result = [False]

    root = tk.Tk()
    root.title("보안 확인")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#2a2a2a")
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    w, h = 360, 200
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    border = tk.Frame(root, bg="#333344", padx=1, pady=1)
    border.pack(fill="both", expand=True)
    card = tk.Frame(border, bg="#2a2a2a")
    card.pack(fill="both", expand=True)

    tk.Label(card, text="파일 변조 감지",
             font=tkfont.Font(size=16, weight="bold"),
             bg="#2a2a2a", fg="#f47174").pack(pady=(20, 6))
    tk.Label(card, text="리셋 비밀번호를 입력하세요",
             font=tkfont.Font(size=11),
             bg="#2a2a2a", fg="#b8b8cc").pack(pady=(0, 10))

    entry = tk.Entry(card, show="*", font=tkfont.Font(size=14),
                     justify="center", width=15)
    entry.pack(pady=(0, 10))
    entry.focus_set()

    msg = tk.Label(card, text="", font=tkfont.Font(size=10),
                   bg="#2a2a2a", fg="#f47174")
    msg.pack()

    def _submit(event=None):
        if entry.get().strip() == "1234":
            result[0] = True
            root.destroy()
        else:
            msg.configure(text="비밀번호가 틀렸습니다")
            entry.delete(0, "end")

    def _cancel():
        root.destroy()

    entry.bind("<Return>", _submit)

    tk.Frame(card, bg="#333344", height=1).pack(fill="x", pady=(10, 0))
    btn_row = tk.Frame(card, bg="#2a2a2a")
    btn_row.pack(fill="x")
    ok_lbl = tk.Label(btn_row, text="확인", font=tkfont.Font(size=13),
                      bg="#2a2a2a", fg="#6cb4ee", pady=10, cursor="hand2")
    ok_lbl.pack(side="left", expand=True, fill="both")
    ok_lbl.bind("<Button-1>", lambda e: _submit())
    tk.Frame(btn_row, bg="#333344", width=1).pack(side="left", fill="y")
    cancel_lbl = tk.Label(btn_row, text="취소", font=tkfont.Font(size=13),
                          bg="#2a2a2a", fg="#f47174", pady=10, cursor="hand2")
    cancel_lbl.pack(side="left", expand=True, fill="both")
    cancel_lbl.bind("<Button-1>", lambda e: _cancel())

    def _press(e):
        root._dx, root._dy = e.x_root, e.y_root
    def _move(e):
        x = root.winfo_x() + e.x_root - root._dx
        y = root.winfo_y() + e.y_root - root._dy
        root._dx, root._dy = e.x_root, e.y_root
        root.geometry(f"+{x}+{y}")
    for w in (card, border):
        w.bind("<ButtonPress-1>", _press)
        w.bind("<B1-Motion>", _move)

    root.mainloop()
    return result[0]


# ── Account list ──────────────────────────────────────────────────────────────
_ACCOUNT_LIST = [
    ("account1", "coreabridge@gmail.com",    "#1e2e1e"),
    ("account2", "airelair00@gmail.com",      "#251e2e"),
    ("account3", "ferrari812fast@gmail.com",  "#2e2518"),
    ("account4", "bridgejobkr@gmail.com",     "#2a2a2a"),
]

_LAST_RUN_FILE = Path(__file__).resolve().parent / "logs" / ".last_run.json"


def _mask_email(email: str) -> str:
    try:
        local, domain = email.split("@", 1)
        if len(local) <= 3:
            masked = local[0] + "*" * (len(local) - 1)
        else:
            masked = local[:2] + "*" * (len(local) - 4) + local[-2:]
        return f"{masked}@{domain}"
    except Exception:
        return "****@****"


def _load_last_runs() -> dict:
    try:
        return json.loads(_LAST_RUN_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_last_run(email: str):
    data = _load_last_runs()
    data[email] = datetime.now().isoformat()
    _LAST_RUN_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LAST_RUN_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _time_ago(iso_str: str) -> str:
    try:
        last  = datetime.fromisoformat(iso_str)
        diff  = datetime.now() - last
        hours = int(diff.total_seconds() // 3600)
        mins  = int((diff.total_seconds() % 3600) // 60)
        return f"{hours}시간 {mins}분 전" if hours > 0 else f"{mins}분 전"
    except Exception:
        return "기록 없음"


# ── Account selection popup ───────────────────────────────────────────────────
def ask_account_selection():
    """계정 선택 팝업.  Returns: (account_id, limit) or ("CANCEL", 0)."""
    result = [("CANCEL", 0)]

    def _build():
        root = tk.Tk()
        root.title("BRIDGE Craig")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg="#2a2a2a")

        w, h = 440, 540
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        if _HAS_SCREENINFO:
            try:
                mons = get_monitors()
                m    = mons[1] if len(mons) >= 2 else mons[0]
                sw, sh = m.width, m.height
                ox, oy = m.x, m.y
            except Exception:
                ox, oy = 0, 0
        else:
            ox, oy = 0, 0
        root.geometry(f"{w}x{h}+{ox + (sw - w) // 2}+{oy + (sh - h) // 2}")
        root.lift()
        root.focus_force()

        border = tk.Frame(root, bg="#333344", padx=1, pady=1)
        border.pack(fill="both", expand=True)
        card = tk.Frame(border, bg="#2a2a2a")
        card.pack(fill="both", expand=True)

        tk.Label(card, text="BRIDGE Craig RPA",
                 font=tkfont.Font(family="Segoe UI", size=18, weight="bold"),
                 bg="#2a2a2a", fg="#f0f0f5").pack(pady=(20, 2))
        tk.Label(card, text="작업할 계정을 선택하세요",
                 font=tkfont.Font(family="Segoe UI", size=10),
                 bg="#2a2a2a", fg="#b8b8cc").pack(pady=(0, 10))

        last_runs = _load_last_runs()
        cnt_var   = tk.IntVar(value=10)

        for acct_id, email, color in _ACCOUNT_LIST:
            ago = (_time_ago(last_runs[email]) if email in last_runs
                   else "아직 사용 안 함")

            border_frame = tk.Frame(card, bg="#444455", padx=1, pady=1)
            border_frame.pack(fill="x", padx=16, pady=3)

            btn_frame = tk.Frame(border_frame, bg=color, padx=14, pady=10, cursor="hand2")
            btn_frame.pack(fill="both")

            lbl_email = tk.Label(btn_frame, text=_mask_email(email),
                                 font=tkfont.Font(family="Segoe UI", size=12, weight="bold"),
                                 bg=color, fg="#f0f0f5", anchor="w")
            lbl_email.pack(fill="x")

            lbl_ago = tk.Label(btn_frame, text=ago,
                               font=tkfont.Font(family="Segoe UI", size=9),
                               bg=color, fg="#aaaaaa", anchor="w")
            lbl_ago.pack(fill="x", pady=(2, 0))

            def _select(aid=acct_id, em=email):
                result[0] = (aid, cnt_var.get())
                _save_last_run(em)
                root.destroy()

            hover_color = "#3a3a4a"
            for widget in (btn_frame, lbl_email, lbl_ago):
                widget.bind("<Button-1>", lambda e, f=_select: f())
                widget.bind("<Enter>",
                            lambda e, bf=btn_frame, hc=hover_color: bf.configure(bg=hc))
                widget.bind("<Leave>",
                            lambda e, bf=btn_frame, c=color: bf.configure(bg=c))

        tk.Frame(card, bg="#333344", height=1).pack(fill="x", padx=16, pady=(12, 0))
        cnt_row = tk.Frame(card, bg="#2a2a2a")
        cnt_row.pack(fill="x", padx=16, pady=6)
        tk.Label(cnt_row, text="게시 수:",
                 font=tkfont.Font(family="Segoe UI", size=10),
                 bg="#2a2a2a", fg="#b8b8cc").pack(side="left")

        cnt_btns = []

        def _pick(v):
            cnt_var.set(v)
            for b, bv in cnt_btns:
                b.configure(bg="#6cb4ee" if bv == v else "#3a3a4a",
                            fg="#ffffff" if bv == v else "#b8b8cc")

        for lbl, val in [("1(테스트)", 1), ("5", 5), ("10", 10), ("20", 20)]:
            b = tk.Button(cnt_row, text=lbl, bg="#3a3a4a", fg="#b8b8cc",
                          font=tkfont.Font(family="Segoe UI", size=9),
                          relief="flat", bd=0, cursor="hand2", padx=8, pady=4,
                          command=lambda v=val: _pick(v))
            b.pack(side="left", padx=3)
            cnt_btns.append((b, val))

        for b, bv in cnt_btns:
            if bv == 10:
                b.configure(bg="#6cb4ee", fg="#ffffff")

        tk.Frame(card, bg="#333344", height=1).pack(fill="x")
        cancel_lbl = tk.Label(card, text="나중에 하기 (종료)",
                              font=tkfont.Font(family="Segoe UI", size=12),
                              bg="#2a2a2a", fg="#f47174", cursor="hand2", pady=10)
        cancel_lbl.pack(fill="x")
        cancel_lbl.bind("<Button-1>", lambda e: root.destroy())
        cancel_lbl.bind("<Enter>", lambda e: cancel_lbl.configure(bg="#333344"))
        cancel_lbl.bind("<Leave>", lambda e: cancel_lbl.configure(bg="#2a2a2a"))

        def _press(e):
            root._dx, root._dy = e.x_root, e.y_root
        def _move(e):
            x = root.winfo_x() + e.x_root - root._dx
            y = root.winfo_y() + e.y_root - root._dy
            root._dx, root._dy = e.x_root, e.y_root
            root.geometry(f"+{x}+{y}")
        for dw in (card, border):
            dw.bind("<ButtonPress-1>", _press)
            dw.bind("<B1-Motion>", _move)

        root.mainloop()

    import threading as _threading
    if _threading.current_thread() is _threading.main_thread():
        _build()
    else:
        t = threading.Thread(target=_build, daemon=True)
        t.start()
        t.join(timeout=300)
    return result[0]


# ── Module-level exports ──────────────────────────────────────────────────────
_overlay       = RPAOverlay()
show_working   = _overlay.show_working
show_complete  = _overlay.show_complete
update_progress = _overlay.update_progress
update_status  = _overlay.update_status
close          = _overlay.close
