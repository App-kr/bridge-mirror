"""
BRIDGE RPA Overlay — iOS Alert Style
=====================================
Apple HIG 기반. 보더 없는 플로팅 카드 + 드롭 섀도.
애니메이션 V 체크마크. iOS 텍스트 액션 버튼.
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

    BG = "#2a2a2a"
    TEXT1 = "#f0f0f5"
    TEXT2 = "#b8b8cc"
    BLUE = "#6cb4ee"
    RED = "#f47174"
    GREEN = "#78dba0"
    SEP = "#333344"
    HOVER = "#2a2a3c"
    X_GRAY = "#66667a"
    BORDER = "#888899"
    BAR_BG = "#333344"
    _TRANS = "#010203"

    def __init__(self):
        self._root = None
        self._thread = None
        self._ready = threading.Event()
        self._progress_var = None   # (current, total) 표시용
        self._prog_bar = None
        self._prog_label = None
        self._prog_pct = None
        self._is_working = False
        self._remind_timer = None

    ACCOUNT_COLORS = {
        "coreabridge@gmail.com":  "#0d3d0d",   # 선명한 녹색
        "ferrari812fast@gmail.com": "#3a2810",  # 진한 갈색
        "airelair00@gmail.com":   "#2a1a3a",    # 진한 보라색
        "bridgejobkr@gmail.com":  "#3a3a3a",    # 회색
    }

    def show_working(self, current: int = 0, total: int = 0, email: str = ""):
        self.close()
        self._is_working = True
        self._progress_var = [current, total]
        self._email = email
        if email.lower() in self.ACCOUNT_COLORS:
            self.BG = self.ACCOUNT_COLORS[email.lower()]
        self._thread = threading.Thread(target=self._build_working, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def update_progress(self, current: int, total: int):
        self._progress_var = [current, total]
        if self._root and self._prog_bar and self._prog_label:
            try:
                self._root.after(0, lambda: self._refresh_bar(current, total))
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
        """닫기 누르면 창만 닫고, 30초 후 다시 팝업."""
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

    # ── WORKING ──────────────────────────────
    def _build_working(self):
        _stop_event.clear()
        root, card = self._make_window(480, 370)

        bar = self._top_bar(card, root)

        spinner = tk.Canvas(card, width=44, height=44,
                            bg=self.BG, highlightthickness=0)
        spinner.pack(pady=(4, 10))
        self._draw_spinner(spinner, root)

        title = tk.Label(card, text="Craig 작업중",
                         font=self._fn(18, "bold"),
                         bg=self.BG, fg=self.TEXT1)
        title.pack()

        if self._email:
            acct_lbl = tk.Label(card, text=self._email,
                                font=self._fn(9), bg=self.BG, fg=self.TEXT2)
            acct_lbl.pack(pady=(2, 0))

        # ── 진행률 바 ──
        cur, tot = self._progress_var or [0, 0]

        self._prog_label = tk.Label(
            card, text=self._prog_text(cur, tot),
            font=self._fn(11), bg=self.BG, fg=self.TEXT2)
        self._prog_label.pack(pady=(6, 4))

        bar_frame = tk.Frame(card, bg=self.BAR_BG, height=6, width=340)
        bar_frame.pack(pady=(0, 2))
        bar_frame.pack_propagate(False)

        self._prog_bar = tk.Frame(bar_frame, bg=self.GREEN, height=6,
                                  width=self._bar_width(cur, tot, 340))
        self._prog_bar.place(x=0, y=0, height=6)

        # 펄스 글로우 (게이지 끝부분 빛남)
        self._pulse_canvas = tk.Canvas(bar_frame, width=12, height=6,
                                       bg=self.BAR_BG, highlightthickness=0)
        self._pulse_dir = 1
        self._pulse_alpha = 0.0
        self._start_pulse(root)

        self._prog_pct = tk.Label(
            card, text=self._pct_text(cur, tot),
            font=self._fn(10), bg=self.BG, fg=self.TEXT2)
        self._prog_pct.pack(pady=(0, 4))

        sub = tk.Label(card, text="인터넷 창을 건들지 마세요",
                       font=self._fn(13, "bold"), bg=self.BG, fg="#ffffff")
        sub.pack(pady=(2, 6))

        # 게임 OK 라인
        game_row = tk.Frame(card, bg=self.BG)
        game_row.pack(pady=(0, 8))
        gun = tk.Canvas(game_row, width=24, height=18,
                        bg=self.BG, highlightthickness=0)
        gun.pack(side="left", padx=(0, 4))
        self._draw_gun(gun)
        game_lbl = tk.Label(game_row, text="게임은 해도 됩니다!",
                            font=self._fn(11), bg=self.BG, fg=self.GREEN)
        game_lbl.pack(side="left")

        tk.Frame(card, bg=self.BG, height=16).pack()
        self._sep(card)
        btn_row = tk.Frame(card, bg=self.BG)
        btn_row.pack(fill="x")
        self._action_inline(btn_row, "닫기", "normal", self.BLUE,
                            lambda: self._dismiss_and_remind(), "left")
        tk.Frame(btn_row, bg=self.SEP, width=1).pack(side="left", fill="y")
        self._action_inline(btn_row, "중단하기", "normal", self.RED,
                            lambda: [_stop_event.set(), self._stop_remind(), root.destroy()], "left")

        self._drag(root, bar, spinner, title, sub, game_row, game_lbl)
        self._ready.set()
        try:
            root.mainloop()
        except Exception:
            pass

    # ── COMPLETE ─────────────────────────────
    def _build_complete(self, count: int):
        root, card = self._make_window(420, 300)

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

    @staticmethod
    def _bar_width(cur, tot, max_w):
        if tot <= 0:
            return 0
        return max(0, min(max_w, int(cur / tot * max_w)))

    def _refresh_bar(self, cur, tot):
        try:
            if self._prog_label and self._prog_label.winfo_exists():
                self._prog_label.configure(text=self._prog_text(cur, tot))
            w = self._bar_width(cur, tot, 340)
            if self._prog_bar and self._prog_bar.winfo_exists():
                self._prog_bar.place(x=0, y=0, height=6, width=w)
            if self._prog_pct and self._prog_pct.winfo_exists():
                self._prog_pct.configure(text=self._pct_text(cur, tot))
            if self._pulse_canvas and self._pulse_canvas.winfo_exists():
                self._pulse_canvas.place(x=max(0, w - 12), y=0, height=6)
        except Exception:
            pass

    def _start_pulse(self, root):
        """게이지 끝부분 글로우 펄스 애니메이션."""
        def _pulse():
            if not root.winfo_exists():
                return
            self._pulse_alpha += 0.08 * self._pulse_dir
            if self._pulse_alpha >= 1.0:
                self._pulse_alpha = 1.0
                self._pulse_dir = -1
            elif self._pulse_alpha <= 0.0:
                self._pulse_alpha = 0.0
                self._pulse_dir = 1
            # 밝기 보간: BAR_BG → 밝은 녹색
            bg_r, bg_g, bg_b = 0x33, 0x33, 0x44
            hi_r, hi_g, hi_b = 0x90, 0xf0, 0xb8
            a = self._pulse_alpha
            r = int(bg_r + (hi_r - bg_r) * a)
            g = int(bg_g + (hi_g - bg_g) * a)
            b = int(bg_b + (hi_b - bg_b) * a)
            color = f"#{r:02x}{g:02x}{b:02x}"
            try:
                self._pulse_canvas.configure(bg=color)
                cur, tot = self._progress_var or [0, 0]
                w = self._bar_width(cur, tot, 340)
                if w > 0:
                    self._pulse_canvas.place(x=max(0, w - 12), y=0, height=6)
                else:
                    self._pulse_canvas.place_forget()
            except Exception:
                pass
            root.after(50, _pulse)
        _pulse()

    # ── Drawing ──────────────────────────────
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
        g = "#78dba0"
        # Barrel
        c.create_rectangle(10, 4, 23, 8, fill=g, outline="")
        # Body
        c.create_rectangle(3, 4, 14, 12, fill=g, outline="")
        # Handle
        c.create_polygon(5, 12, 9, 12, 10, 17, 4, 17,
                         fill=g, outline="")
        # Trigger guard
        c.create_line(9, 12, 12, 12, 12, 14, 9, 14,
                      fill=g, width=1.5)

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
                       bg=self.BG, fg=self.BLUE,
                       pady=12, cursor="hand2")
        btn.pack(fill="x")
        btn.bind("<Enter>", lambda e: btn.configure(bg=self.HOVER))
        btn.bind("<Leave>", lambda e: btn.configure(bg=self.BG))
        btn.bind("<Button-1>", lambda e: cmd())

    def _action_inline(self, parent, text, weight, color, cmd, side):
        btn = tk.Label(parent, text=text,
                       font=tkfont.Font(family="Malgun Gothic", size=15, weight=weight),
                       bg=self.BG, fg=color,
                       pady=18, padx=24, cursor="hand2")
        btn.pack(side=side, expand=True, fill="both")
        btn.bind("<Enter>", lambda e: btn.configure(bg=self.HOVER))
        btn.bind("<Leave>", lambda e: btn.configure(bg=self.BG))
        btn.bind("<Button-1>", lambda e: cmd())

    # ── Window ───────────────────────────────
    def _make_window(self, w, h):
        """Clean white floating card."""
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
                m = mons[1] if len(mons) >= 2 else mons[0]
                mx, my, mw, mh = m.x, m.y, m.width, m.height
            except Exception:
                pass
        root.geometry(f"{w}x{h}+{mx + (mw - w) // 2}+{my + (mh - h) // 2}")

        border = tk.Frame(root, bg=self.BORDER, padx=1, pady=1)
        border.pack(fill="both", expand=True)
        card = tk.Frame(border, bg=self.BG)
        card.pack(fill="both", expand=True)

        # Fade in
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
        scaled = int(size * 1.2)
        return tkfont.Font(size=scaled, weight=weight)

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

    # 드래그 이동
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


_ACCOUNT_LIST = [
    ("account1", "coreabridge@gmail.com",   "#1e2e1e"),  # 옅은 녹색
    ("account3", "ferrari812fast@gmail.com", "#2e2518"),  # 옅은 갈색
    ("account2", "airelair00@gmail.com",     "#251e2e"),  # 옅은 보라색
    ("account4", "bridgejobkr@gmail.com",    "#2a2a2a"),  # 옅은 블랙
]

_LAST_RUN_FILE = Path(__file__).resolve().parent / "logs" / ".last_run.json"


def _load_last_runs() -> dict:
    try:
        return json.loads(_LAST_RUN_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_last_run(email: str):
    data = _load_last_runs()
    data[email] = datetime.now().isoformat()
    _LAST_RUN_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LAST_RUN_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _time_ago(iso_str: str) -> str:
    try:
        last = datetime.fromisoformat(iso_str)
        diff = datetime.now() - last
        hours = int(diff.total_seconds() // 3600)
        mins = int((diff.total_seconds() % 3600) // 60)
        if hours > 0:
            return f"{hours}시간 {mins}분 전"
        return f"{mins}분 전"
    except Exception:
        return "기록 없음"


def ask_account_selection():
    """계정 선택 팝업. 선택된 account_id 반환 (None이면 기본 .env, 'CANCEL'이면 취소)."""
    result = ["CANCEL"]

    def _build():
        root = tk.Tk()
        root.title("BRIDGE Craig")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg="#2a2a2a")

        w, h = 440, 480
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        if _HAS_SCREENINFO:
            try:
                mons = get_monitors()
                m = mons[1] if len(mons) >= 2 else mons[0]
                sw, sh = m.width, m.height
                ox, oy = m.x, m.y
            except Exception:
                ox, oy = 0, 0
        else:
            ox, oy = 0, 0
        root.geometry(f"{w}x{h}+{ox + (sw - w) // 2}+{oy + (sh - h) // 2}")

        border = tk.Frame(root, bg="#333344", padx=1, pady=1)
        border.pack(fill="both", expand=True)
        card = tk.Frame(border, bg="#2a2a2a")
        card.pack(fill="both", expand=True)

        tk.Label(card, text="BRIDGE Craig RPA",
                 font=tkfont.Font(size=18, weight="bold"),
                 bg="#2a2a2a", fg="#f0f0f5").pack(pady=(20, 4))
        tk.Label(card, text="작업할 계정을 선택하세요",
                 font=tkfont.Font(size=11),
                 bg="#2a2a2a", fg="#b8b8cc").pack(pady=(0, 12))

        last_runs = _load_last_runs()

        for acct_id, email, color in _ACCOUNT_LIST:
            ago = _time_ago(last_runs.get(email, ""))
            if email in last_runs:
                sub_text = f"{ago}"
            else:
                sub_text = "아직 사용 안 함"

            border_frame = tk.Frame(card, bg="#555566", padx=1, pady=1)
            border_frame.pack(fill="x", padx=16, pady=4)

            btn_frame = tk.Frame(border_frame, bg=color, padx=14, pady=10, cursor="hand2")
            btn_frame.pack(fill="both")

            lbl_email = tk.Label(btn_frame, text=email,
                                 font=tkfont.Font(size=12, weight="bold"),
                                 bg=color, fg="#f0f0f5", anchor="w")
            lbl_email.pack(fill="x")

            lbl_ago = tk.Label(btn_frame, text=sub_text,
                               font=tkfont.Font(size=9),
                               bg=color, fg="#aaaaaa", anchor="w")
            lbl_ago.pack(fill="x", pady=(2, 0))

            def _select(aid=acct_id, em=email):
                result[0] = aid
                _save_last_run(em)
                root.destroy()

            for widget in (btn_frame, lbl_email, lbl_ago):
                widget.bind("<Button-1>", lambda e, f=_select: f())
                widget.bind("<Enter>", lambda e, bf=btn_frame: bf.configure(bg="#444455"))
                widget.bind("<Leave>", lambda e, bf=btn_frame, c=color: bf.configure(bg=c))

        tk.Frame(card, bg="#2a2a2a", height=20).pack()
        tk.Frame(card, bg="#333344", height=1).pack(fill="x")
        tk.Frame(card, bg="#2a2a2a", height=6).pack()
        cancel_lbl = tk.Label(card, text="나중에 하기(종료)",
                              font=tkfont.Font(family="Segoe UI", size=12),
                              bg="#2a2a2a", fg="#f47174", cursor="hand2", pady=10)
        cancel_lbl.pack(fill="x")
        cancel_lbl.bind("<Button-1>", lambda e: root.destroy())
        cancel_lbl.bind("<Enter>", lambda e: cancel_lbl.configure(bg="#333344"))
        cancel_lbl.bind("<Leave>", lambda e: cancel_lbl.configure(bg="#2a2a2a"))

        # 드래그 이동
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

    t = threading.Thread(target=_build, daemon=True)
    t.start()
    t.join(timeout=300)
    return result[0]


_overlay = RPAOverlay()
show_working = _overlay.show_working
show_complete = _overlay.show_complete
update_progress = _overlay.update_progress
close = _overlay.close
