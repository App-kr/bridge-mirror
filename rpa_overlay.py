"""
BRIDGE RPA Overlay — Apple Light v4
=====================================
두-톤 헤더(CARD #ffffff) + BG 바디(#f5f5f7).
귀여운 로봇 캐릭터 애니메이션 (눈 글로우 · 안테나 흔들림 · LED 깜박임).
Pill 프로그레스 바. 상태 블링크.
"""

import json
import math
import threading
import tkinter as tk
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import font as tkfont
import winsound


def _log_overlay(msg: str):
    """크래쉬/이벤트 진단 로그 → logs/overlay_debug.log"""
    try:
        import time as _t
        _p = Path(__file__).resolve().parent / "logs" / "overlay_debug.log"
        _p.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%H:%M:%S")
        with _p.open("a", encoding="utf-8") as _f:
            _f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

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

    BG     = "#f5f5f7"
    CARD   = "#ffffff"      # header default
    TEXT1  = "#1d1d1f"
    TEXT2  = "#6e6e73"
    BLUE   = "#0071e3"
    RED    = "#ff3b30"
    GREEN  = "#34c759"
    SEP    = "#d2d2d7"
    HOVER  = "#e8e8ed"
    X_GRAY = "#86868b"
    BAR_BG = "#e5e5ea"
    GOLD   = "#ff9500"

    # 계정별 전체 창 색상 (BG, CARD)
    _WINDOW_COLORS = {
        "coreabridge@gmail.com":    ("#c8dcc8", "#e0ede0"),  # 옅은 초록
        "airelair00@gmail.com":     ("#d8d0e8", "#ece8f5"),  # 옅은 보라
        "ferrari812fast@gmail.com": ("#e8d8c0", "#f5ece0"),  # 옅은 갈색
        "bridgejobkr@gmail.com":    ("#d4d4d4", "#e8e8e8"),  # 옅은 회색
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
        self._restore_monitor  = None

    # ── Restore flag monitor (안전망) ──────────
    def _start_restore_monitor(self):
        """안전망 모니터 — withdraw 방식에서 _check_restore()가 주 담당.
        self._root가 None인 비정상 케이스만 여기서 처리."""
        import time as _time

        _flag = Path(__file__).resolve().parent / "logs" / ".overlay_restore.flag"

        def _watch():
            while self._is_working:
                try:
                    if _flag.exists() and self._root is None:
                        _flag.unlink(missing_ok=True)
                        self._re_show_working()
                except Exception:
                    pass
                _time.sleep(1.0)

        self._restore_monitor = threading.Thread(target=_watch, daemon=True)
        self._restore_monitor.start()

    def _bring_to_front(self):
        """tkinter 스레드에서 창 앞으로 (AttachThreadInput 강제 포커스)."""
        try:
            if self._root and self._root.winfo_exists():
                import ctypes as _ct2
                _hwnd = self._root.winfo_id()
                _fg   = _ct2.windll.user32.GetForegroundWindow()
                _fg_tid  = _ct2.windll.user32.GetWindowThreadProcessId(_fg, None)
                _tgt_tid = _ct2.windll.user32.GetWindowThreadProcessId(_hwnd, None)
                if _fg_tid and _tgt_tid and _fg_tid != _tgt_tid:
                    _ct2.windll.user32.AttachThreadInput(_fg_tid, _tgt_tid, True)
                self._root.attributes("-topmost", True)
                self._root.lift()
                self._root.focus_force()
                _ct2.windll.user32.ShowWindow(_hwnd, 9)
                _ct2.windll.user32.BringWindowToTop(_hwnd)
                _ct2.windll.user32.SetForegroundWindow(_hwnd)
                if _fg_tid and _tgt_tid and _fg_tid != _tgt_tid:
                    _ct2.windll.user32.AttachThreadInput(_fg_tid, _tgt_tid, False)
                self._root.after(
                    1200,
                    lambda: self._root.attributes("-topmost", False)
                    if self._root and self._root.winfo_exists() else None
                )
        except Exception:
            pass

    # ── Public API ────────────────────────────
    def show_working(self, current: int = 0, total: int = 0, email: str = ""):
        _log_overlay(f"show_working called email={email} total={total}")
        self.close()
        self._is_working   = True
        self._progress_var = [current, total]
        self._email   = email
        self._bot_t   = 0.0
        bg_c, card_c  = self._WINDOW_COLORS.get(email.lower(),
                            (self.__class__.BG, self.__class__.CARD))
        self.BG   = bg_c
        self.CARD = card_c

        def _safe_build():
            try:
                self._build_working()
            except Exception as _exc:
                _log_overlay(f"_build_working CRASH: {_exc}\n{traceback.format_exc()}")
                try:
                    self._ready.set()
                except Exception:
                    pass

        self._thread = threading.Thread(target=_safe_build, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)
        _log_overlay(f"show_working ready wait done, is_working={self._is_working}")
        self._start_restore_monitor()  # restore flag 감시 시작

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
        # HWND 파일 정리 (중복실행 포커스용)
        try:
            (Path(__file__).resolve().parent / "logs" / ".overlay_hwnd.txt").unlink(missing_ok=True)
        except Exception:
            pass

    def _dismiss_and_remind(self):
        """닫기/X 버튼 — destroy 없이 withdraw(숨기기). tkinter 인터프리터 유지.
        _check_restore()가 400ms마다 flag 감시 → deiconify()로 즉시 복원 가능."""
        _log_overlay("_dismiss_and_remind: withdraw 호출")
        try:
            if self._root and self._root.winfo_exists():
                self._root.withdraw()          # 숨기기 (destroy 아님)
                _log_overlay(f"_dismiss_and_remind: withdraw 완료 state={self._root.state()}")
                if self._is_working:
                    # 30초 후 tkinter 이벤트 루프에서 자동 복원 (크로스스레드 없음)
                    self._root.after(30000, self._deiconify_working)
        except Exception as _e:
            _log_overlay(f"_dismiss_and_remind ERROR: {_e}")
        self._ready.clear()

    def _deiconify_working(self):
        """숨겨진 작업창 복원 — tkinter 이벤트 루프 내부에서 호출됨."""
        if not self._is_working:
            return
        try:
            if self._root and self._root.winfo_exists():
                self._root.deiconify()
                self._root.attributes("-topmost", True)
                self._root.lift()
                self._root.focus_force()
                self._root.after(
                    1500,
                    lambda: self._root.attributes("-topmost", False)
                    if self._root and self._root.winfo_exists() else None,
                )
        except Exception:
            pass

    def _re_show_working(self):
        """안전망: self._root가 None인 비정상 케이스 전용 (withdraw 방식 이후 거의 미사용)."""
        if not self._is_working:
            return
        # withdraw된 경우 — deiconify로 복원
        if self._root and self._root.winfo_exists():
            try:
                self._root.after(0, self._deiconify_working)
            except Exception:
                pass
            return
        # root가 완전히 없는 경우만 새 Tk() 생성
        self._thread = threading.Thread(target=self._build_working, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)

    def _stop_remind(self):
        if self._remind_timer:
            self._remind_timer.cancel()
            self._remind_timer = None

    # ── WORKING window ────────────────────────
    def _build_working(self):
        _log_overlay("_build_working: Tk() 생성 시작")
        _stop_event.clear()
        CC = self.CARD                 # 계정별 헤더 색
        root, card = self._make_window(320, 210)
        _log_overlay(f"_build_working: 창 생성 완료 winfo_id={root.winfo_id()}")

        # 숨겨진 title 설정 — FindWindowW로 HWND 직접 검색용
        try:
            root.title("CraigRPA_Working")
        except Exception:
            pass

        # ══ HEADER (계정 색 배경) ═══════════════
        header = tk.Frame(card, bg=CC)
        header.pack(fill="x")

        # 닫기 버튼 (헤더 우상단)
        bar = tk.Frame(header, bg=CC, height=24)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        xb = tk.Label(bar, text="\u2715", font=self._fn(10),
                      bg=CC, fg=self.X_GRAY, cursor="hand2")
        xb.pack(side="right", padx=(0, 10), pady=(4, 0))
        xb.bind("<Enter>", lambda e: xb.configure(fg=self.TEXT1))
        xb.bind("<Leave>", lambda e: xb.configure(fg=self.X_GRAY))
        xb.bind("<Button-1>", lambda e: self._dismiss_and_remind())

        # 스피너 + 타이틀
        bot_row = tk.Frame(header, bg=CC)
        bot_row.pack(padx=20, pady=(2, 10), anchor="w")

        spin_c = tk.Canvas(bot_row, width=44, height=44,
                           bg=CC, highlightthickness=0)
        spin_c.pack(side="left", padx=(0, 14))
        self._draw_spinner(spin_c, root)

        info_col = tk.Frame(bot_row, bg=CC)
        info_col.pack(side="left", anchor="w")

        tk.Label(info_col, text="Craig RPA",
                 font=self._fn(16, "bold"),
                 bg=CC, fg=self.TEXT1, anchor="w").pack(anchor="w")

        if self._email:
            _display_email = self._email.split("@")[0] if "@" in self._email else self._email
            tk.Label(info_col, text=_display_email,
                     font=self._fn(10),
                     bg=CC, fg=self.TEXT1, anchor="w").pack(anchor="w", pady=(4, 0))

        # ══ SEPARATOR ══════════════════════════
        tk.Frame(card, bg=self.SEP, height=1).pack(fill="x")

        # ══ BODY (BG 배경) ══════════════════════
        cur, tot = self._progress_var or [0, 0]
        body = tk.Frame(card, bg=self.BG)
        body.pack(fill="x", padx=20, pady=(8, 4))

        # % · 상태 · 카운트 행
        pct_row = tk.Frame(body, bg=self.BG)
        pct_row.pack(fill="x", pady=(0, 6))

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

        # Pill 프로그레스 바 (320 - 2border - 40pad = 278)
        BAR_W, BAR_H = 278, 10
        self._prog_bar_canvas = tk.Canvas(
            body, width=BAR_W, height=BAR_H,
            bg=self.BG, highlightthickness=0)
        self._prog_bar_canvas.pack()
        self._draw_pill_bar(BAR_W, BAR_H, cur, tot)

        # 개인정보 경고
        warn_row = tk.Frame(card, bg=self.BG)
        warn_row.pack(pady=(6, 0), padx=20, anchor="w")
        tk.Label(warn_row, text="\u26a0",
                 font=self._fn(11), bg=self.BG, fg=self.GOLD).pack(side="left", padx=(0, 6))
        tk.Label(warn_row, text="개인정보 확인 필수",
                 font=self._fn(11, "bold"), bg=self.BG, fg=self.TEXT1).pack(side="left")

        # ══ BUTTONS (하단 고정) ═══════════════════
        btn_row = tk.Frame(card, bg=self.BG)
        btn_row.pack(fill="x", side="bottom")
        tk.Frame(card, bg="#9a9aaa", height=2).pack(fill="x", side="bottom")

        # 닫기 버튼 (파란 배경)
        _CLOSE_BG  = "#e4eef8"
        _CLOSE_HOV = "#ccdcf0"
        close_btn = tk.Label(btn_row, text="닫기",
                             font=tkfont.Font(family="Malgun Gothic", size=14),
                             bg=_CLOSE_BG, fg=self.BLUE, cursor="hand2")
        close_btn.pack(side="left", expand=True, fill="both", ipady=6)
        close_btn.bind("<Button-1>", lambda e: self._dismiss_and_remind())
        close_btn.bind("<Enter>", lambda e: close_btn.configure(bg=_CLOSE_HOV))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(bg=_CLOSE_BG))

        # 버튼 구분선 (짙게)
        tk.Frame(btn_row, bg="#9a9aaa", width=2).pack(side="left", fill="y")

        # 중단하기 버튼 (빨간 배경)
        _STOP_BG  = "#fde8e8"
        _STOP_HOV = "#f8cece"
        stop_btn = tk.Label(btn_row, text="중단하기",
                            font=tkfont.Font(family="Malgun Gothic", size=14),
                            bg=_STOP_BG, fg=self.RED, cursor="hand2")
        stop_btn.pack(side="left", expand=True, fill="both", ipady=6)
        stop_btn.bind("<Button-1>", lambda e: self._confirm_stop_popup(root))
        stop_btn.bind("<Enter>", lambda e: stop_btn.configure(bg=_STOP_HOV))
        stop_btn.bind("<Leave>", lambda e: stop_btn.configure(bg=_STOP_BG))

        # 애니메이션
        self._start_status_blink(root)
        self._start_pulse_bar(root)

        self._drag(root, header, bar, bot_row, spin_c, info_col, warn_row)
        _log_overlay("_build_working: ready.set() 직전 — UI 완성")
        self._ready.set()

        # HWND 파일 저장 — launcher 직접 포커스용
        def _save_hwnd():
            try:
                _hwnd = root.winfo_id()
                _hwnd_file = Path(__file__).resolve().parent / "logs" / ".overlay_hwnd.txt"
                _hwnd_file.parent.mkdir(parents=True, exist_ok=True)
                _hwnd_file.write_text(str(_hwnd), encoding="utf-8")
            except Exception:
                pass
        root.after(200, _save_hwnd)

        # ── 복원 플래그 감시 (tkinter 이벤트 루프 내부 — 크로스스레드 없음) ──
        # attributes("-topmost", True)는 Win32 WM이 강제 적용 → SetForegroundWindow
        # 권한 문제 완전 회피. 이것이 작업창 복원의 확실한 경로.
        _restore_flag = Path(__file__).resolve().parent / "logs" / ".overlay_restore.flag"

        def _check_restore():
            if not root.winfo_exists():
                _log_overlay("_check_restore: root 소멸 — 감시 종료")
                return
            try:
                if _restore_flag.exists():
                    _restore_flag.unlink(missing_ok=True)
                    _log_overlay(f"_check_restore: flag 감지! state={root.state()}")
                    root.deiconify()                    # withdraw 상태면 재표시
                    # 화면 밖 방지: 주 모니터 중앙으로 재배치
                    sw = root.winfo_screenwidth()
                    sh = root.winfo_screenheight()
                    w, h = 320, 210
                    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
                    root.attributes("-topmost", True)   # Win32 WM 강제 최상위
                    root.lift()
                    root.focus_force()
                    _log_overlay("_check_restore: deiconify+topmost 완료")
                    root.after(2000, lambda: root.attributes("-topmost", False)
                               if root.winfo_exists() else None)
            except Exception as _e:
                _log_overlay(f"_check_restore ERROR: {_e}")
            root.after(400, _check_restore)

        root.after(400, _check_restore)

        try:
            root.mainloop()
        except Exception:
            pass

    # ── Cute Robot animation ──────────────────
    def _draw_spinner(self, c, root, size=44):
        """원형 스피너 — 회전하는 호."""
        cx = cy = size // 2
        r = size // 2 - 5

        def _tick(angle=0):
            if not root.winfo_exists():
                return
            c.delete("spin")
            c.create_oval(cx - r, cy - r, cx + r, cy + r,
                          outline=self.BAR_BG, width=5, tags="spin")
            c.create_arc(cx - r, cy - r, cx + r, cy + r,
                         start=angle, extent=130,
                         outline=self.BLUE, width=5,
                         style="arc", tags="spin")
            root.after(25, lambda: _tick((angle + 9) % 360))

        _tick()

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
            e_fill = self._lerp_color("#1a60b8", "#0071e3", glow)
            e_hi   = self._lerp_color("#4a90d8", "#64b5ff", glow)

            # ── Head shadow ──
            c.create_oval(8, 13, 58, 53,
                          fill="#d8d8dc", outline="", tags="bot")

            # ── Head ──
            c.create_oval(6, 10, 58, 52,
                          fill="#e8e8ed", outline="#c7c7cc", width=1.5, tags="bot")

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
                          fill="#8e8e93", width=2, tags="bot")
            # Antenna ball
            c.create_oval(27, -2 + ant_off, 37, 8 + ant_off,
                          fill=self.GOLD, outline="", tags="bot")
            c.create_oval(28, -1 + ant_off, 32, 3 + ant_off,
                          fill="#ffe880", outline="", tags="bot")  # shine

            # ── Torso ──
            c.create_rectangle(18, 53, 46, 66,
                               fill="#e8e8ed", outline="#c7c7cc", width=1, tags="bot")
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
                        self._status_label.configure(fg=self.BG)
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
            self._draw_pill_bar(278, 10, cur, tot)
        except Exception:
            pass

    # ── Stop confirmation popup ───────────────
    def _confirm_stop_popup(self, parent_root):
        popup = tk.Toplevel(parent_root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg=self.BG)

        pw, ph = 300, 220
        px = parent_root.winfo_x() + (320 - pw) // 2
        py = parent_root.winfo_y() + (210 - ph) // 2
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

        tk.Label(inner, text="\u26d4",
                 font=tkfont.Font(family="Segoe UI Emoji", size=28),
                 bg=self.BG, fg=self.RED).pack(pady=(16, 4))
        tk.Label(inner, text="Boss요청으로 작업 중단",
                 font=self._fn(13, "bold"),
                 bg=self.BG, fg=self.TEXT1).pack()
        tk.Label(inner, text="작업중인 경우 완료 후 중단됩니다",
                 font=self._fn(10),
                 bg=self.BG, fg=self.TEXT2).pack(pady=(4, 0))

        tk.Frame(inner, bg=self.BG).pack(fill="both", expand=True)
        tk.Frame(inner, bg=self.SEP, height=1).pack(fill="x")

        btn_row = tk.Frame(inner, bg=self.BG)
        btn_row.pack(fill="x")

        def _do_force_stop():
            """즉시 강제 종료 — lock 파일에서 PID 읽어서 프로세스 kill."""
            import subprocess as _sp
            try:
                lock_dir = Path(__file__).resolve().parent / "logs"
                for _lf in lock_dir.glob(".rpa_*.lock"):
                    try:
                        _pid = int(_lf.read_text(encoding="utf-8").strip())
                        _sp.call(
                            ["taskkill", "/F", "/PID", str(_pid)],
                            creationflags=0x08000000,
                            stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
                        )
                        _lf.unlink(missing_ok=True)
                    except Exception:
                        pass
            except Exception:
                pass
            _stop_event.set()
            self._stop_remind()
            try: popup.destroy()
            except Exception: pass
            try: parent_root.destroy()
            except Exception: pass

        def _do_stop_after():
            """현재 작업 완료 후 중단 — 실행창 닫고 stop_event set. 완료 후 show_complete 호출됨."""
            _stop_event.set()
            self._stop_remind()
            try: popup.destroy()
            except Exception: pass
            try: parent_root.destroy()
            except Exception: pass
            self._root = None

        force_btn = tk.Label(btn_row, text="그만하기",
                             font=self._fn(13, "bold"),
                             bg=self.BG, fg=self.RED, pady=14, cursor="hand2")
        force_btn.pack(side="left", expand=True, fill="both")
        force_btn.bind("<Button-1>", lambda e: _do_force_stop())
        force_btn.bind("<Enter>", lambda e: force_btn.configure(bg=self.HOVER))
        force_btn.bind("<Leave>", lambda e: force_btn.configure(bg=self.BG))

        tk.Frame(btn_row, bg=self.SEP, width=1).pack(side="left", fill="y")

        after_btn = tk.Label(btn_row, text="작업 후 중단",
                             font=self._fn(13, "bold"),
                             bg=self.BG, fg=self.BLUE, pady=14, cursor="hand2")
        after_btn.pack(side="left", expand=True, fill="both")
        after_btn.bind("<Button-1>", lambda e: _do_stop_after())
        after_btn.bind("<Enter>", lambda e: after_btn.configure(bg=self.HOVER))
        after_btn.bind("<Leave>", lambda e: after_btn.configure(bg=self.BG))

    # ── COMPLETE window ───────────────────────
    def _build_complete(self, count: int):
        root, card = self._make_window(320, 250)

        bar = self._top_bar(card, root)

        chk = tk.Canvas(card, width=54, height=46,
                        bg=self.BG, highlightthickness=0)
        chk.pack(pady=(2, 6))
        self._draw_check_animated(chk, root)

        title = tk.Label(card, text=f"✓  {count}건 완료!",
                         font=self._fn(16, "bold"),
                         bg=self.BG, fg=self.TEXT1)
        title.pack()

        sub = tk.Label(card, text="개인정보 노출이 없는지 확인해 주세요 ⚠",
                       font=self._fn(10), bg=self.BG, fg=self.TEXT2)
        sub.pack(pady=(3, 12))

        self._sep(card)

        def _more():
            _post_more_event.set()
            root.destroy()

        self._action(card, "5개 더 올리기  ›", "bold", _more)
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
        _ico = Path(__file__).resolve().parent / "images" / "craig_icon.ico"
        if _ico.exists():
            try:
                root.iconbitmap(str(_ico))
            except Exception:
                pass
        root.overrideredirect(True)
        root.attributes("-topmost", True)   # 처음 표시 시에만 앞으로
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

        border = tk.Frame(root, bg=self.SEP, padx=1, pady=0)
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
                # 페이드 완료 후 topmost 해제 — 이후 뒤에서 작업 가능
                root.after(100, lambda: root.attributes("-topmost", False)
                           if root.winfo_exists() else None)

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
    _ico = Path(__file__).resolve().parent / "images" / "craig_icon.ico"
    if _ico.exists():
        try:
            root.iconbitmap(str(_ico))
        except Exception:
            pass
    root.title("보안 확인")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#f5f5f7")
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    w, h = 300, 185
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    border = tk.Frame(root, bg="#d2d2d7", padx=1, pady=1)
    border.pack(fill="both", expand=True)
    card = tk.Frame(border, bg="#ffffff")
    card.pack(fill="both", expand=True)

    tk.Label(card, text="🔒  파일 변조 감지",
             font=tkfont.Font(family="Malgun Gothic", size=14, weight="bold"),
             bg="#ffffff", fg="#ff3b30").pack(pady=(16, 4))
    tk.Label(card, text="리셋 비밀번호를 입력하세요",
             font=tkfont.Font(family="Malgun Gothic", size=10),
             bg="#ffffff", fg="#6e6e73").pack(pady=(0, 8))

    entry = tk.Entry(card, show="*", font=tkfont.Font(family="Malgun Gothic", size=13),
                     justify="center", width=13,
                     relief="flat", bd=1, highlightthickness=1,
                     highlightbackground="#d2d2d7", highlightcolor="#0071e3")
    entry.pack(pady=(0, 10))
    entry.focus_set()

    msg = tk.Label(card, text="", font=tkfont.Font(family="Malgun Gothic", size=10),
                   bg="#ffffff", fg="#ff3b30")
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

    tk.Frame(card, bg="#d2d2d7", height=1).pack(fill="x", pady=(10, 0))
    btn_row = tk.Frame(card, bg="#ffffff")
    btn_row.pack(fill="x")
    ok_lbl = tk.Label(btn_row, text="확인", font=tkfont.Font(family="Malgun Gothic", size=13),
                      bg="#ffffff", fg="#0071e3", pady=10, cursor="hand2")
    ok_lbl.pack(side="left", expand=True, fill="both")
    ok_lbl.bind("<Button-1>", lambda e: _submit())
    ok_lbl.bind("<Enter>", lambda e: ok_lbl.configure(bg="#e8e8ed"))
    ok_lbl.bind("<Leave>", lambda e: ok_lbl.configure(bg="#ffffff"))
    tk.Frame(btn_row, bg="#d2d2d7", width=1).pack(side="left", fill="y")
    cancel_lbl = tk.Label(btn_row, text="취소", font=tkfont.Font(family="Malgun Gothic", size=13),
                          bg="#ffffff", fg="#ff3b30", pady=10, cursor="hand2")
    cancel_lbl.pack(side="left", expand=True, fill="both")
    cancel_lbl.bind("<Button-1>", lambda e: _cancel())
    cancel_lbl.bind("<Enter>", lambda e: cancel_lbl.configure(bg="#e8e8ed"))
    cancel_lbl.bind("<Leave>", lambda e: cancel_lbl.configure(bg="#ffffff"))

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
    ("account1", "coreabridge@gmail.com",    "#c8dcc8"),  # 옅은 초록
    ("account2", "airelair00@gmail.com",      "#d8d0e8"),  # 옅은 보라
    ("account3", "ferrari812fast@gmail.com",  "#e8d8c0"),  # 옅은 갈색
    ("account4", "bridgejobkr@gmail.com",     "#d4d4d4"),  # 옅은 회색
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
        _BG   = "#f5f5f7"
        _CARD = "#ffffff"
        _SEP  = "#d2d2d7"
        _T1   = "#1d1d1f"
        _T2   = "#6e6e73"
        _BLUE = "#0071e3"
        _RED  = "#ff3b30"
        _HOV  = "#e8e8ed"

        root = tk.Tk()
        _ico = Path(__file__).resolve().parent / "images" / "craig_icon.ico"
        if _ico.exists():
            try:
                root.iconbitmap(str(_ico))
            except Exception:
                pass
        root.title("BRIDGE Craig")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=_BG)

        w, h = 340, 510
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

        border = tk.Frame(root, bg=_SEP, padx=1, pady=1)
        border.pack(fill="both", expand=True)
        card = tk.Frame(border, bg=_CARD)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="✦  BRIDGE Craig RPA",
                 font=tkfont.Font(family="Malgun Gothic", size=16, weight="bold"),
                 bg=_CARD, fg=_T1).pack(pady=(18, 2))
        tk.Label(card, text="계정을 선택해 주세요",
                 font=tkfont.Font(family="Malgun Gothic", size=10),
                 bg=_CARD, fg=_T2).pack(pady=(0, 10))
        tk.Frame(card, bg=_SEP, height=1).pack(fill="x", padx=12, pady=(0, 3))

        last_runs = _load_last_runs()
        cnt_var   = tk.IntVar(value=10)

        def _darken(hex_color, factor=0.82):
            """hex 색상을 factor 비율로 어둡게."""
            r = int(int(hex_color[1:3], 16) * factor)
            g = int(int(hex_color[3:5], 16) * factor)
            b = int(int(hex_color[5:7], 16) * factor)
            return "#{:02x}{:02x}{:02x}".format(
                min(r, 255), min(g, 255), min(b, 255))

        for idx, (acct_id, email, color) in enumerate(_ACCOUNT_LIST, 1):
            ago       = (_time_ago(last_runs[email]) if email in last_runs
                         else "아직 사용 안 함")
            name      = email.split("@")[0]          # @gmail.com 제거
            hover_c   = _darken(color)               # 호버시 선명한 어두운 버전
            accent_c  = _darken(color, 0.68)         # 왼쪽 악센트 바 색

            # ── 카드 래퍼 (테두리) ────────────────────
            wrap = tk.Frame(card, bg=_SEP, padx=1, pady=1)
            wrap.pack(fill="x", padx=12, pady=3)

            # ── 버튼 본체 ─────────────────────────────
            btn = tk.Frame(wrap, bg=color, cursor="hand2")
            btn.pack(fill="both")

            # 왼쪽 악센트 바
            accent = tk.Frame(btn, bg=accent_c, width=5)
            accent.pack(side="left", fill="y")
            accent.pack_propagate(False)

            # 콘텐츠 영역
            body = tk.Frame(btn, bg=color, padx=12, pady=11)
            body.pack(side="left", fill="both", expand=True)

            lbl_name = tk.Label(body,
                                text=name,
                                font=tkfont.Font(family="Malgun Gothic", size=13, weight="bold"),
                                bg=color, fg=_T1, anchor="w")
            lbl_name.pack(fill="x")

            lbl_ago = tk.Label(body,
                               text=ago,
                               font=tkfont.Font(family="Malgun Gothic", size=9),
                               bg=color, fg="#555560", anchor="w")
            lbl_ago.pack(fill="x", pady=(2, 0))

            # 오른쪽 화살표
            arrow = tk.Label(btn, text="›",
                             font=tkfont.Font(family="Malgun Gothic", size=20),
                             bg=color, fg=accent_c, padx=14, cursor="hand2")
            arrow.pack(side="right", fill="y")

            def _select(aid=acct_id, em=email):
                result[0] = (aid, cnt_var.get())
                _save_last_run(em)
                root.destroy()

            # 호버 대상 위젯 (악센트 바 제외 — 악센트는 고정색 유지)
            _bg_widgets = (btn, body, lbl_name, lbl_ago, arrow)
            for w in _bg_widgets + (accent,):
                w.bind("<Button-1>", lambda e, f=_select: f())
            for w in _bg_widgets:
                w.bind("<Enter>",
                       lambda e, ws=_bg_widgets, hc=hover_c: [x.configure(bg=hc) for x in ws])
                w.bind("<Leave>",
                       lambda e, ws=_bg_widgets, c=color: [x.configure(bg=c) for x in ws])
            accent.bind("<Enter>",
                        lambda e, ws=_bg_widgets, hc=hover_c: [x.configure(bg=hc) for x in ws])
            accent.bind("<Leave>",
                        lambda e, ws=_bg_widgets, c=color: [x.configure(bg=c) for x in ws])

        tk.Frame(card, bg=_SEP, height=1).pack(fill="x", padx=12, pady=(10, 0))
        cnt_row = tk.Frame(card, bg=_CARD)
        cnt_row.pack(fill="x", padx=12, pady=5)
        tk.Label(cnt_row, text="게시 수:",
                 font=tkfont.Font(family="Malgun Gothic", size=10),
                 bg=_CARD, fg=_T2).pack(side="left")

        cnt_btns = []

        def _pick(v):
            cnt_var.set(v)
            for b, bv in cnt_btns:
                b.configure(bg=_BLUE if bv == v else _HOV,
                            fg="#ffffff" if bv == v else _T2)

        for lbl, val in [("1(테스트)", 1), ("5", 5), ("10", 10), ("20", 20)]:
            b = tk.Button(cnt_row, text=lbl, bg=_HOV, fg=_T2,
                          font=tkfont.Font(family="Malgun Gothic", size=9),
                          relief="flat", bd=0, cursor="hand2", padx=8, pady=4,
                          command=lambda v=val: _pick(v))
            b.pack(side="left", padx=3)
            cnt_btns.append((b, val))

        for b, bv in cnt_btns:
            if bv == 10:
                b.configure(bg=_BLUE, fg="#ffffff")

        tk.Frame(card, bg=_SEP, height=1).pack(fill="x")
        cancel_lbl = tk.Label(card, text="나중에 하기 (종료)",
                              font=tkfont.Font(family="Malgun Gothic", size=12),
                              bg=_CARD, fg=_RED, cursor="hand2", pady=10)
        cancel_lbl.pack(fill="x")
        cancel_lbl.bind("<Button-1>", lambda e: root.destroy())
        cancel_lbl.bind("<Enter>", lambda e: cancel_lbl.configure(bg=_HOV))
        cancel_lbl.bind("<Leave>", lambda e: cancel_lbl.configure(bg=_CARD))

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


# ── Win32 직접 창 포커스 헬퍼 ────────────────────────────────────────────────
def _win32_focus_working():
    """lock 파일의 PID → HWND 파일 or EnumWindows로 실제 창을 찾아 앞으로 가져온다.
    창이 없으면(dismiss 상태) restore flag로 monitor 스레드에 복원 요청."""
    import ctypes as _ct
    from ctypes.wintypes import HWND, DWORD, BOOL, LPARAM

    # ── lock 파일에서 살아있는 PID 수집 ────────────────────────────────
    _STILL_ACTIVE = 259
    _lock_dir = Path(__file__).resolve().parent / "logs"
    _pids = []
    for _lf in _lock_dir.glob(".rpa_*.lock"):
        try:
            _pid = int(_lf.read_text(encoding="utf-8").strip())
            _h = _ct.windll.kernel32.OpenProcess(0x1000, False, _pid)
            if _h:
                _code = _ct.c_ulong(0)
                _ct.windll.kernel32.GetExitCodeProcess(_h, _ct.byref(_code))
                _ct.windll.kernel32.CloseHandle(_h)
                if _code.value == _STILL_ACTIVE:
                    _pids.append(_pid)
                else:
                    _lf.unlink(missing_ok=True)
            else:
                _lf.unlink(missing_ok=True)
        except Exception:
            pass

    if not _pids:
        return False

    def _bring_hwnd(hwnd):
        """AttachThreadInput 방식으로 교차-프로세스 창 활성화 (가장 신뢰할 수 있음)."""
        try:
            _fg = _ct.windll.user32.GetForegroundWindow()
            _fg_tid = _ct.windll.user32.GetWindowThreadProcessId(_fg, None)
            _tgt_tid = _ct.windll.user32.GetWindowThreadProcessId(hwnd, None)
            if _fg_tid and _tgt_tid and _fg_tid != _tgt_tid:
                _ct.windll.user32.AttachThreadInput(_fg_tid, _tgt_tid, True)
            _ct.windll.user32.ShowWindow(hwnd, 9)        # SW_RESTORE
            _ct.windll.user32.BringWindowToTop(hwnd)
            _ct.windll.user32.SetForegroundWindow(hwnd)
            if _fg_tid and _tgt_tid and _fg_tid != _tgt_tid:
                _ct.windll.user32.AttachThreadInput(_fg_tid, _tgt_tid, False)
        except Exception:
            pass

    # ── 항상 restore flag 기록 (tkinter _check_restore()가 가장 확실) ──
    # _check_restore()는 tkinter 이벤트 루프 내부에서 attributes(-topmost, True) 사용
    # Win32 SetForegroundWindow 권한 제한 없이 무조건 동작
    _rf = _lock_dir / ".overlay_restore.flag"
    try:
        _rf.write_text("restore", encoding="utf-8")
    except Exception:
        pass

    # ── 방법1: HWND 파일 직접 읽기 (즉각 Win32 응답 시도) ──────────────
    _hwnd_file = _lock_dir / ".overlay_hwnd.txt"
    if _hwnd_file.exists():
        try:
            _saved_hwnd = int(_hwnd_file.read_text(encoding="utf-8").strip())
            if (_ct.windll.user32.IsWindow(_saved_hwnd)
                    and _ct.windll.user32.IsWindowVisible(_saved_hwnd)):
                _bring_hwnd(_saved_hwnd)
                return True
        except Exception:
            pass

    # ── 방법2: EnumWindows 폴백 ────────────────────────────────────────
    _found_hwnds = []
    _EnumProc = _ct.WINFUNCTYPE(BOOL, HWND, LPARAM)

    def _cb(hwnd, _):
        _pid_out = DWORD()
        _ct.windll.user32.GetWindowThreadProcessId(hwnd, _ct.byref(_pid_out))
        if _pid_out.value in _pids and _ct.windll.user32.IsWindowVisible(hwnd):
            _found_hwnds.append(hwnd)
        return True

    _ct.windll.user32.EnumWindows(_EnumProc(_cb), 0)

    if _found_hwnds:
        for _hwnd in _found_hwnds:
            _bring_hwnd(_hwnd)
        return True

    # 창이 없음(dismiss) → restore flag로 monitor 스레드가 _re_show_working() 호출
    return False


# ── Already-running popup ─────────────────────────────────────────────────────
def ask_already_running(acct_key: str = ""):
    """같은 계정 RPA 중복 실행 감지 시 알림 팝업 + 기존 작업창 앞으로 포커스."""

    # ── 작업창 즉시 가져오기 (팝업 표시 전) ──────────────────────────────
    _found = _win32_focus_working()

    # ── 안내 팝업 ────────────────────────────────────────────────────────────
    acct_color = "#f5f5f7"
    for _aid, _em, _c in _ACCOUNT_LIST:
        if _aid == acct_key or _em.split("@")[0] == acct_key:
            acct_color = _c
            break

    root = tk.Tk()
    _ico = Path(__file__).resolve().parent / "images" / "craig_icon.ico"
    if _ico.exists():
        try:
            root.iconbitmap(str(_ico))
        except Exception:
            pass
    root.overrideredirect(True)
    root.attributes("-topmost", False)   # 팝업이 작업창을 덮지 않도록
    root.configure(bg=acct_color)

    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    ox, oy = 0, 0
    if _HAS_SCREENINFO:
        try:
            mons = get_monitors()
            m = mons[1] if len(mons) >= 2 else mons[0]
            sw, sh = m.width, m.height
            ox, oy = m.x, m.y
        except Exception:
            pass
    w, h = 300, 148
    root.geometry(f"{w}x{h}+{ox + (sw - w) // 2}+{oy + (sh - h) // 2 - 80}")
    root.attributes("-alpha", 0.0)

    def _fade(a=0.0):
        if root.winfo_exists():
            if a < 1.0:
                root.attributes("-alpha", a)
                root.after(16, lambda: _fade(a + 0.1))
            else:
                root.attributes("-alpha", 1.0)
    root.after(10, _fade)

    _bc = "#{:02x}{:02x}{:02x}".format(
        max(0, int(int(acct_color[1:3], 16) * 0.80)),
        max(0, int(int(acct_color[3:5], 16) * 0.80)),
        max(0, int(int(acct_color[5:7], 16) * 0.80)))
    border = tk.Frame(root, bg=_bc, padx=1, pady=1)
    border.pack(fill="both", expand=True)
    card = tk.Frame(border, bg=acct_color)
    card.pack(fill="both", expand=True)

    name_part = acct_key.replace("account", "") if acct_key.startswith("account") else acct_key
    for _aid, _em, _c in _ACCOUNT_LIST:
        if _aid == acct_key:
            name_part = _em.split("@")[0]
            break

    _msg = "작업 창을 앞으로 가져왔습니다." if _found else "잠시 후 작업 창이 복원됩니다."
    tk.Label(card, text="이미 작업 중 ✦",
             font=tkfont.Font(family="Malgun Gothic", size=13, weight="bold"),
             bg=acct_color, fg="#1d1d1f").pack(pady=(13, 3))
    tk.Label(card, text=f"[ {name_part} ] 작업이 진행 중입니다.",
             font=tkfont.Font(family="Malgun Gothic", size=10),
             bg=acct_color, fg="#444450").pack()
    tk.Label(card, text=_msg,
             font=tkfont.Font(family="Malgun Gothic", size=9),
             bg=acct_color, fg="#666670").pack(pady=(2, 0))

    _sc = "#{:02x}{:02x}{:02x}".format(
        max(0, int(int(acct_color[1:3], 16) * 0.75)),
        max(0, int(int(acct_color[3:5], 16) * 0.75)),
        max(0, int(int(acct_color[5:7], 16) * 0.75)))
    tk.Frame(card, bg=_sc, height=1).pack(fill="x", pady=(12, 0))

    def _close():
        try:
            root.destroy()
        except Exception:
            pass
        # 팝업 닫힌 후 작업창 다시 앞으로
        _win32_focus_working()

    ok_btn = tk.Label(card, text="확인",
                      font=tkfont.Font(family="Malgun Gothic", size=12),
                      bg=acct_color, fg="#0071e3", pady=8, cursor="hand2")
    ok_btn.pack(fill="x")
    ok_btn.bind("<Button-1>", lambda e: _close())

    def _press(e): root._dx, root._dy = e.x_root, e.y_root
    def _move(e):
        x = root.winfo_x() + e.x_root - root._dx
        y = root.winfo_y() + e.y_root - root._dy
        root._dx, root._dy = e.x_root, e.y_root
        root.geometry(f"+{x}+{y}")
    for dw in (card, border):
        dw.bind("<ButtonPress-1>", _press)
        dw.bind("<B1-Motion>", _move)

    root.after(4000, lambda: _close() if root.winfo_exists() else None)
    root.mainloop()


# ── Module-level exports ──────────────────────────────────────────────────────
_overlay       = RPAOverlay()
show_working   = _overlay.show_working
show_complete  = _overlay.show_complete
update_progress = _overlay.update_progress
update_status  = _overlay.update_status
close          = _overlay.close
