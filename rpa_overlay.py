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

# ── 백그라운드 모드 (True일 때 어떤 창도 포커스를 뺏지 않음) ──
_BACKGROUND_MODE = False

def set_background_mode(enabled: bool = True):
    """전역 백그라운드 모드 설정. True면 topmost/focus_force/BringWindowToTop 전부 비활성."""
    global _BACKGROUND_MODE
    _BACKGROUND_MODE = enabled


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
_post_more_count = [0]   # +5/10/20개 추가 게시 수
_stop_event = threading.Event()
_logout_event = threading.Event()   # 로그아웃 요청 플래그
_complete_result_val = [None]   # "MORE" / "CHANGE" / "EXIT"
_complete_done_event = threading.Event()

_PREFS_FILE = Path(__file__).resolve().parent / "logs" / ".rpa_prefs.json"


def _load_prefs() -> dict:
    try:
        if _PREFS_FILE.exists():
            return json.loads(_PREFS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_prefs(prefs: dict):
    try:
        _PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PREFS_FILE.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
    except Exception:
        pass


def is_logout_requested() -> bool:
    """RPA 메인 루프에서 로그아웃 버튼 눌렸는지 체크."""
    return _logout_event.is_set()


def clear_logout_event():
    _logout_event.clear()


def get_auto_login_pref() -> bool:
    """자동로그인 유지 설정 반환 (기본 True)."""
    return _load_prefs().get("auto_login", True)


def _make_rpa_photoimage(root, size=32):
    """파란 원형 배경 + 흰색 R — tkinter 아이콘용 PhotoImage 생성."""
    import math as _math
    _R = [
        [1,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,1,1,1,0],
        [1,0,1,0,0],
        [1,0,0,1,0],
        [1,0,0,0,1],
    ]
    cx, cy = size / 2 - 0.5, size / 2 - 0.5
    radius = size / 2 - 1.5
    ox, oy, scale = 8, 5, 3
    r_pix = set()
    for ry, row in enumerate(_R):
        for rx, p in enumerate(row):
            if p:
                for dy in range(scale):
                    for dx in range(scale):
                        r_pix.add((ox + rx*scale + dx, oy + ry*scale + dy))
    BLUE = "#0071e3"
    WHITE = "#ffffff"
    BG = "#00000000"  # transparent (tkinter uses empty string for transparent in row data)
    rows = []
    for y in range(size):
        row_parts = []
        for x in range(size):
            dist = _math.sqrt((x - cx)**2 + (y - cy)**2)
            if dist > radius:
                row_parts.append(WHITE)   # 투명 대신 흰색 테두리
            elif (x, y) in r_pix:
                row_parts.append(WHITE)
            else:
                row_parts.append(BLUE)
        rows.append("{" + " ".join(row_parts) + "}")
    img = tk.PhotoImage(width=size, height=size)
    img.put(" ".join(rows))
    return img


def wants_more() -> bool:
    result = _post_more_event.is_set()
    _post_more_event.clear()
    return result


def wants_more_count() -> int:
    """wants_more() 가 True 반환한 후 호출 — 추가 게시 수 반환 (기본 5)"""
    return _post_more_count[0] if _post_more_count[0] > 0 else 5


def stop_requested() -> bool:
    return _stop_event.is_set()


class RPAOverlay:

    BG     = "#f5f5f7"
    CARD   = "#ffffff"      # header default
    TEXT1  = "#1d1d1f"
    TEXT2  = "#6e6e73"
    # ── 2026 Dark Mode Palette ──
    BLUE   = "#60a5fa"  # 밝은 파랑
    RED    = "#ff6b6b"  # 밝은 빨강
    GREEN  = "#22c55e"  # 밝은 초록
    SEP    = "#404040"  # 어두운 분리선
    HOVER  = "#333333"  # 호버 배경
    X_GRAY = "#999999"  # 밝은 회색
    BAR_BG = "#2a2a2a"  # 진행바 배경
    GOLD   = "#fbbf24"  # 밝은 황색
    TEXT1  = "#ffffff"  # 기본 텍스트
    TEXT2  = "#cccccc"  # 보조 텍스트

    # 계정별 색상 (가로선) — Dark Mode
    ACCOUNT_COLORS = {
        "coreabridge@gmail.com":    "#22c55e",  # Green
        "airelair00@gmail.com":     "#a855f7",  # Purple
        "ferrari812fast@gmail.com": "#92400e",  # Brown
        "bridgejobkr@gmail.com":    "#808080",  # Gray
    }

    # Dark Mode 배경색 (BG, CARD)
    _WINDOW_COLORS = {
        "coreabridge@gmail.com":    ("#1a1a1a", "#252525"),
        "airelair00@gmail.com":     ("#1a1a1a", "#252525"),
        "ferrari812fast@gmail.com": ("#1a1a1a", "#252525"),
        "bridgejobkr@gmail.com":    ("#1a1a1a", "#252525"),
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
        self._status_dot_label = None   # ● 점 블링크용
        self._status_text      = ""
        self._is_working       = False
        self._remind_timer     = None
        self._email            = ""
        self._bot_t            = 0.0
        self._bear_t           = 0.0
        self._restore_monitor  = None
        self._account_color    = self.GREEN  # 계정별 색상

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
        """tkinter 스레드에서 창 앞으로 (AttachThreadInput 강제 포커스).
        _BACKGROUND_MODE=True일 때 전부 스킵 — 사용자 작업 방해 방지."""
        if _BACKGROUND_MODE:
            return
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
        # 계정별 다리 색상 설정
        self._account_color = self.ACCOUNT_COLORS.get(email.lower(), self.GREEN)

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

    def show_complete(self, posted_count: int = 0) -> str:
        self._is_working = False
        self.close()
        _complete_result_val[0] = None
        _complete_done_event.clear()
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._build_complete, args=(posted_count,), daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)
        threading.Thread(target=self._play_complete_sound, daemon=True).start()
        _complete_done_event.wait(timeout=90)
        return _complete_result_val[0] or "EXIT"

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
        """닫기/X 버튼 — withdraw로 숨김 (overrideredirect 창은 iconify 불가)."""
        _log_overlay("_dismiss_and_remind: withdraw 호출")
        try:
            if self._root and self._root.winfo_exists():
                self._root.withdraw()          # 완전 숨김 (overrideredirect와 호환)
                _log_overlay(f"_dismiss_and_remind: withdraw 완료 state={self._root.state()}")
        except Exception as _e:
            _log_overlay(f"_dismiss_and_remind ERROR: {_e}")
        self._ready.clear()

    def _deiconify_working(self):
        """숨겨진 작업창 복원 — tkinter 이벤트 루프 내부에서 호출됨.
        _BACKGROUND_MODE=True일 때 포커스 강탈 없이 조용히 복원만."""
        if not self._is_working:
            return
        try:
            if self._root and self._root.winfo_exists():
                self._root.deiconify()
                if not _BACKGROUND_MODE:
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
        root, card = self._make_window(360, 388)
        _log_overlay(f"_build_working: 창 생성 완료 winfo_id={root.winfo_id()}")

        try:
            root.title("Craig RPA — 작업중")
        except Exception:
            pass

        # ══ HEADER ════════════════════════════════
        header = tk.Frame(card, bg=CC)
        header.pack(fill="x")

        # X 닫기 — 우상단
        bar = tk.Frame(header, bg=CC, height=24)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        xb = tk.Label(bar, text="\u2715", font=self._fn(10),
                      bg=CC, fg=self.X_GRAY, cursor="hand2")
        xb.pack(side="right", padx=(0, 12), pady=(5, 0))
        xb.bind("<Enter>", lambda e: xb.configure(fg=self.TEXT1))
        xb.bind("<Leave>", lambda e: xb.configure(fg=self.X_GRAY))
        xb.bind("<Button-1>", lambda e: self._dismiss_and_remind())

        # 스피너(32px) + 타이틀 + 계정명 — 2026 style
        bot_row = tk.Frame(header, bg=CC)
        bot_row.pack(padx=20, pady=(2, 8), anchor="w")

        spin_c = tk.Canvas(bot_row, width=32, height=32,
                           bg=CC, highlightthickness=0)
        spin_c.pack(side="left", padx=(0, 13))
        self._draw_spinner(spin_c, root, size=32)

        info_col = tk.Frame(bot_row, bg=CC)
        info_col.pack(side="left", anchor="w")

        tk.Label(info_col, text="RPA",
                 font=self._fn(16, "bold"),
                 bg=CC, fg=self.TEXT1, anchor="w").pack(anchor="w")

        if self._email:
            _display_email = self._email.split("@")[0] if "@" in self._email else self._email
            tk.Label(info_col, text=_display_email,
                     font=tkfont.Font(family="Malgun Gothic", size=13, weight="bold"),
                     bg=CC, fg=self._account_color, anchor="w").pack(anchor="w", pady=(3, 0))

        # ══ SEPARATOR ══════════════════════════
        tk.Frame(card, bg=self.SEP, height=1).pack(fill="x")

        # ══ BODY ═══════════════════════════════
        cur, tot = self._progress_var or [0, 0]
        body = tk.Frame(card, bg=self.BG)
        body.pack(fill="x", padx=20, pady=(6, 0))

        # 상단 행: 큰 % (좌) + 카운트 (우) — 2026: 더 큰 숫자
        pct_row = tk.Frame(body, bg=self.BG)
        pct_row.pack(fill="x", pady=(0, 6))

        self._prog_pct_label = tk.Label(
            pct_row, text=self._pct_text(cur, tot),
            font=tkfont.Font(family="Malgun Gothic", size=24, weight="bold"),
            bg=self.BG, fg=self.TEXT1)
        self._prog_pct_label.pack(side="left")

        self._prog_count_label = tk.Label(
            pct_row, text=self._prog_text(cur, tot),
            font=tkfont.Font(family="Malgun Gothic", size=11),
            bg=self.BG, fg=self.TEXT2)
        self._prog_count_label.pack(side="right", anchor="s", pady=(0, 6))

        # 곰 삽질 + 진행바 캔버스 — 360-2border-40pad = 318
        BAR_W, BAR_H = 318, 72
        self._prog_bar_canvas = tk.Canvas(
            body, width=BAR_W, height=BAR_H,
            bg=self.BG, highlightthickness=0)
        self._prog_bar_canvas.pack()
        self._draw_bear_bar(BAR_W, BAR_H, cur, tot, self._account_color)

        # 상태 행: ● dot + 텍스트 (바 아래)
        status_row = tk.Frame(body, bg=self.BG)
        status_row.pack(fill="x", pady=(5, 0))

        self._status_dot_label = tk.Label(
            status_row, text="●",
            font=tkfont.Font(family="Malgun Gothic", size=9),
            bg=self.BG, fg=self.BLUE)
        self._status_dot_label.pack(side="left", padx=(0, 6))

        self._status_label = tk.Label(
            status_row, text=self._STATUS_CYCLE[0],
            font=tkfont.Font(family="Malgun Gothic", size=11),
            bg=self.BG, fg=self.BLUE)
        self._status_label.pack(side="left")

        # ══ 개인정보 경고 (2026 inline minimal) ══════
        warn_row = tk.Frame(card, bg=self.BG)
        warn_row.pack(fill="x", padx=20, pady=(6, 2))
        warn_icon = tk.Label(warn_row, text="\u26a0",
                             font=tkfont.Font(family="Segoe UI Emoji", size=11),
                             bg=self.BG, fg=self.GOLD)
        warn_icon.pack(side="left", padx=(0, 7))
        warn_lbl = tk.Label(warn_row, text="개인정보 확인 필수",
                            font=tkfont.Font(family="Malgun Gothic", size=10, weight="bold"),
                            bg=self.BG, fg="#8a6200")
        warn_lbl.pack(side="left")

        # ══ BUTTONS (하단 고정) ═══════════════════
        btn_outer = tk.Frame(card, bg=self.BG)
        btn_outer.pack(fill="x", side="bottom")
        tk.Frame(card, bg=self.SEP, height=1).pack(fill="x", side="bottom")

        # ── +추가 게시 버튼 행 (ghost style) ─────────────
        more_row = tk.Frame(btn_outer, bg=self.BG)
        more_row.pack(fill="x")
        _MORE_HOV = "#172817"   # 연한 초록 tint
        for _i, _n in enumerate([5, 10, 20]):
            def _post_more(count=_n):
                _post_more_count[0] = count
                _post_more_event.set()
                self._dismiss_and_remind()
            _mb = tk.Label(more_row,
                           text=f"＋{_n}개",
                           font=tkfont.Font(family="Malgun Gothic", size=10),
                           bg=self.BG, fg=self.GREEN, cursor="hand2")
            _mb.pack(side="left", expand=True, fill="both", ipady=6)
            _mb.bind("<Button-1>", lambda e, f=_post_more: f())
            _mb.bind("<Enter>",    lambda e, b=_mb: b.configure(bg=_MORE_HOV))
            _mb.bind("<Leave>",    lambda e, b=_mb: b.configure(bg=self.BG))
            if _i < 2:
                tk.Frame(more_row, bg=self.SEP, width=1).pack(side="left", fill="y")

        tk.Frame(btn_outer, bg=self.SEP, height=1).pack(fill="x")

        # ── 숨기기 / 즉시중단 (ghost style, 깔끔) ──────────
        main_row = tk.Frame(btn_outer, bg=self.BG)
        main_row.pack(fill="x")

        # 숨기기: 차분한 파랑 텍스트
        _HIDE_HOV = "#0e1828"
        hide_btn = tk.Label(main_row, text="숨기기",
                            font=tkfont.Font(family="Malgun Gothic", size=13),
                            bg=self.BG, fg="#7aaad8", cursor="hand2")
        hide_btn.pack(side="left", expand=True, fill="both", ipady=10)
        hide_btn.bind("<Button-1>", lambda e: self._dismiss_and_remind())
        hide_btn.bind("<Enter>", lambda e: hide_btn.configure(bg=_HIDE_HOV))
        hide_btn.bind("<Leave>", lambda e: hide_btn.configure(bg=self.BG))

        tk.Frame(main_row, bg=self.SEP, width=1).pack(side="left", fill="y")

        # 로그아웃: 주황 텍스트
        _LOGOUT_HOV = "#1e1000"
        logout_btn = tk.Label(main_row, text="로그아웃",
                              font=tkfont.Font(family="Malgun Gothic", size=13),
                              bg=self.BG, fg="#ff9500", cursor="hand2")
        logout_btn.pack(side="left", expand=True, fill="both", ipady=10)
        def _do_logout():
            _logout_event.set()
            _stop_event.set()
            self._do_direct_stop(root)
        logout_btn.bind("<Button-1>", lambda e: _do_logout())
        logout_btn.bind("<Enter>", lambda e: logout_btn.configure(bg=_LOGOUT_HOV))
        logout_btn.bind("<Leave>", lambda e: logout_btn.configure(bg=self.BG))

        tk.Frame(main_row, bg=self.SEP, width=1).pack(side="left", fill="y")

        # 즉시중단: 붉은 텍스트, 호버만 어두운 red tint
        _KILL_HOV = "#1e0808"
        stop_btn = tk.Label(main_row, text="즉시중단",
                            font=tkfont.Font(family="Malgun Gothic", size=13, weight="bold"),
                            bg=self.BG, fg=self.RED, cursor="hand2")
        stop_btn.pack(side="left", expand=True, fill="both", ipady=10)
        stop_btn.bind("<Button-1>", lambda e: self._do_direct_stop(root))
        stop_btn.bind("<Enter>", lambda e: stop_btn.configure(bg=_KILL_HOV))
        stop_btn.bind("<Leave>", lambda e: stop_btn.configure(bg=self.BG))

        # 애니메이션
        self._start_status_blink(root)
        self._start_pulse_bar(root)
        self._start_bear_anim(root)

        self._drag(root, header, bar, bot_row, spin_c, info_col, warn_row, warn_icon, warn_lbl)
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
                    w, h = 360, 378
                    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
                    if not _BACKGROUND_MODE:
                        root.attributes("-topmost", True)
                        root.lift()
                        root.focus_force()
                        root.after(2000, lambda: root.attributes("-topmost", False)
                                   if root.winfo_exists() else None)
                    _log_overlay("_check_restore: deiconify 완료")
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

    # ── Bridge progress bar (다리 모양) ──────────────────────
    def _draw_bridge_bar(self, bar_w, bar_h, cur, tot, account_color="#22c55e"):
        """다리 모양 진행바 — 가로선들로 다리를 짓는 모양"""
        c = self._prog_bar_canvas
        if not c:
            return
        try:
            if not c.winfo_exists():
                return
        except Exception:
            return
        c.delete("all")

        # 최대 10개 줄 (포스팅)
        max_lines = 10
        line_h = 3
        line_spacing = 4
        total_h = max_lines * (line_h + line_spacing)

        for i in range(max_lines):
            y = i * line_spacing

            if i < cur:
                # 완료된 줄 — 밝은 색상
                c.create_rectangle(0, y, bar_w, y + line_h,
                                 fill=account_color, outline="")
            elif i == cur:
                # 진행 중인 줄 — 계정 색상 (깜박임은 _blink에서 처리)
                c.create_rectangle(0, y, bar_w, y + line_h,
                                 fill=account_color, outline="")
            else:
                # 아직 안 한 줄 — 어두운 색상
                c.create_rectangle(0, y, bar_w, y + line_h,
                                 fill="#3a3a3a", outline="")

    # ── Bear digging animation bar ────────────
    def _draw_bear_bar(self, bar_w, bar_h, cur, tot, account_color="#22c55e"):
        """곰 삽질 애니메이션 프로그레스 바 (canvas 318×72)"""
        c = self._prog_bar_canvas
        if not c:
            return
        try:
            if not c.winfo_exists():
                return
        except Exception:
            return
        c.delete("all")

        pct    = (cur / tot) if tot > 0 else 0.0
        pct    = max(0.0, min(1.0, pct))
        fill_x = int(pct * bar_w)

        # ── Pill 게이지 바 (하단 14px) ─────────
        by1 = bar_h - 14   # 58
        by2 = bar_h - 2    # 70
        r   = 6
        # 배경
        c.create_rectangle(r, by1, bar_w - r, by2, fill="#2a2a2a", outline="")
        c.create_oval(0, by1, r * 2, by2,           fill="#2a2a2a", outline="")
        c.create_oval(bar_w - r * 2, by1, bar_w, by2, fill="#2a2a2a", outline="")
        # 진행 채우기
        if fill_x > r:
            rx2 = min(fill_x, bar_w - r)
            c.create_rectangle(r, by1, rx2, by2, fill=account_color, outline="")
            c.create_oval(0, by1, r * 2, by2, fill=account_color, outline="")
            if fill_x < bar_w - r:
                c.create_oval(fill_x - r * 2, by1, fill_x, by2,
                              fill=account_color, outline="")
            else:
                c.create_oval(bar_w - r * 2, by1, bar_w, by2,
                              fill=account_color, outline="")

        # ── 곰 위치 (바 위 중앙) ───────────────
        bx  = max(20, min(fill_x, bar_w - 20))
        bfy = by1           # 발 바닥 = 바 표면
        t   = self._bear_t
        dig = math.sin(t * 3.5)          # -1 ~ +1

        sway = int(math.sin(t * 3.5) * 1.2)
        land = int(abs(math.sin(t * 3.5)) * 1.5)
        bxs  = bx + sway
        bys  = bfy - land

        # 색
        B  = "#7a5010";  BL = "#b87828";  BD = "#4a2e08"
        BP = "#ffaac0";  BK = "#111111"
        SM = "#c0c8d0";  SH = "#7a5010"

        # 그림자
        c.create_oval(bx - 13, bys + 2, bx + 13, bys + 6,
                      fill="#111111", outline="", stipple="gray25")

        # 오른팔 (뒤, 고정)
        c.create_line(bxs - 6, bys - 18, bxs - 15, bys - 8,
                      fill=BD, width=4, capstyle="round")

        # 왼팔 + 삽 (앞, 애니메이션)
        raise_f  = max(0.0, dig)
        dig_f    = max(0.0, -dig)
        arm_dx   = int(11 + 4 * raise_f)
        arm_dy   = int(-8 - 10 * raise_f + 8 * dig_f)
        ax = bxs + arm_dx;  ay = bys + arm_dy
        c.create_line(bxs + 5, bys - 18, ax, ay,
                      fill=BD, width=4, capstyle="round")
        # 삽 손잡이
        h_dx = int(2 * dig_f)
        c.create_line(ax, ay, ax + h_dx, ay + 12,
                      fill=SH, width=3, capstyle="round")
        # 삽 날
        sx, sy = ax + h_dx, ay + 12
        c.create_polygon(sx - 6, sy, sx + 6, sy,
                         sx + 7, sy + 9, sx - 7, sy + 9,
                         fill=SM, outline="#8a9098", width=1)
        # 흙 튀김
        if dig_f > 0.5 and tot > 0:
            for i in range(4):
                off  = (dig_f - 0.5) * 2
                dx2  = sx + (-6 + i * 4)
                dy2  = sy + 9 - int(off * 8) + int(math.sin(t * 8 + i * 1.5) * 3)
                cr   = 2
                c.create_oval(dx2 - cr, dy2 - cr, dx2 + cr, dy2 + cr,
                              fill=BD, outline="")

        # 다리
        leg_l = int(land)
        c.create_oval(bxs - 10, bys - 3, bxs -  3, bys + 8 - leg_l,
                      fill=B, outline=BD, width=1)
        c.create_oval(bxs +  3, bys - 3, bxs + 10, bys + 8 + leg_l,
                      fill=B, outline=BD, width=1)

        # 몸통
        c.create_oval(bxs - 12, bys - 22, bxs + 12, bys + 1,
                      fill=B, outline=BD, width=1)
        c.create_oval(bxs - 7, bys - 18, bxs + 7, bys + 0,
                      fill=BL, outline="")

        # 머리
        c.create_oval(bxs - 11, bys - 38, bxs + 11, bys - 18,
                      fill=B, outline=BD, width=1)
        # 귀 좌
        c.create_oval(bxs - 14, bys - 42, bxs -  6, bys - 34,
                      fill=B, outline=BD, width=1)
        c.create_oval(bxs - 13, bys - 41, bxs -  8, bys - 36,
                      fill=BP, outline="")
        # 귀 우
        c.create_oval(bxs +  6, bys - 42, bxs + 14, bys - 34,
                      fill=B, outline=BD, width=1)
        c.create_oval(bxs +  8, bys - 41, bxs + 13, bys - 36,
                      fill=BP, outline="")

        # 주둥이 + 코
        c.create_oval(bxs - 6, bys - 28, bxs + 6, bys - 22, fill=BL, outline="")
        c.create_oval(bxs - 3, bys - 29, bxs + 3, bys - 25, fill=BK, outline="")

        # 눈 (깜박임)
        blink = 0.5 + 0.5 * math.sin(t * 1.4)
        ey_h  = max(1, int(4 * blink))
        ey_y  = bys - 35
        c.create_oval(bxs - 8, ey_y, bxs - 4, ey_y + ey_h, fill=BK, outline="")
        if blink > 0.7:
            c.create_oval(bxs - 8, ey_y, bxs - 6, ey_y + 2, fill="#ffffff", outline="")
        c.create_oval(bxs + 4, ey_y, bxs + 8, ey_y + ey_h, fill=BK, outline="")
        if blink > 0.7:
            c.create_oval(bxs + 4, ey_y, bxs + 6, ey_y + 2, fill="#ffffff", outline="")

        # 볼 홍조
        c.create_oval(bxs - 11, bys - 27, bxs -  7, bys - 24,
                      fill=BP, outline="", stipple="gray50")
        c.create_oval(bxs +  7, bys - 27, bxs + 11, bys - 24,
                      fill=BP, outline="", stipple="gray50")

        # 땀방울 (작업 중)
        if tot > 0:
            sw_t = (t * 1.5) % (2 * math.pi)
            sw_y = ey_y - 6 - int(abs(math.sin(sw_t)) * 5)
            sw_x = bxs + 13
            c.create_oval(sw_x, sw_y, sw_x + 4, sw_y + 6,
                          fill="#60a5fa", outline="")
            c.create_oval(sw_x + 1, sw_y - 1, sw_x + 3, sw_y + 1,
                          fill="#93c5fd", outline="")

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
                        if self._status_dot_label and self._status_dot_label.winfo_exists():
                            self._status_dot_label.configure(fg=self.BLUE)
                    else:
                        self._status_label.configure(fg=self.BG)
                        if self._status_dot_label and self._status_dot_label.winfo_exists():
                            self._status_dot_label.configure(fg=self.BG)
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

    def _start_bear_anim(self, root):
        """곰 삽질 애니메이션 루프 — 50ms"""
        def _tick():
            if not root.winfo_exists():
                return
            self._bear_t += 0.05
            cur, tot = self._progress_var or [0, 0]
            self._draw_bear_bar(318, 72, cur, tot, self._account_color)
            root.after(50, _tick)
        _tick()

    def _refresh_progress(self, cur, tot):
        try:
            if self._prog_pct_label and self._prog_pct_label.winfo_exists():
                self._prog_pct_label.configure(text=self._pct_text(cur, tot))
            if self._prog_count_label and self._prog_count_label.winfo_exists():
                self._prog_count_label.configure(text=self._prog_text(cur, tot))
            # 바 캔버스는 _start_bear_anim이 담당 — 레이블만 갱신
        except Exception:
            pass

    # ── Direct stop (그만하기 버튼 직접 호출) ─────
    def _do_direct_stop(self, root):
        """그만하기 버튼 직접 클릭 — stop_event 설정 + graceful flag 파일 + 창 닫기."""
        # 1. 같은 프로세스 내 RPA 루프에 중단 신호
        _stop_event.set()
        # 2. 크로스 프로세스 대비 graceful flag 파일 기록
        try:
            _sflag = Path(__file__).resolve().parent / "logs" / ".rpa_stop_graceful.flag"
            _sflag.parent.mkdir(parents=True, exist_ok=True)
            _sflag.write_text("stop", encoding="utf-8")
        except Exception:
            pass
        self._stop_remind()
        self._is_working = False
        try:
            root.destroy()
        except Exception:
            pass
        self._root = None

    # ── Stop confirmation popup ───────────────
    def _confirm_stop_popup(self, parent_root):
        popup = tk.Toplevel(parent_root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg=self.BG)

        pw, ph = 300, 220
        px = parent_root.winfo_x() + (340 - pw) // 2
        py = parent_root.winfo_y() + (262 - ph) // 2
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
        # ── Apple Light 팔레트 (apply 페이지 동일 스타일) — self.* 색상 미사용 ──
        _BG    = "#f5f5f7"   # Apple 밝은 배경
        _CARD  = "#ffffff"   # 카드 흰색
        _T1    = "#1d1d1f"   # 기본 텍스트 (거의 검정)
        _T2    = "#6e6e73"   # 보조 텍스트 (회색)
        _SEP   = "#d2d2d7"   # 구분선 (밝은 회색)
        _GREEN = "#1d9e75"   # BRIDGE 브랜드 초록
        _BLUE  = "#0071e3"   # Apple 파랑
        _RED   = "#ff3b30"   # Apple 빨강 (종료)
        _HOV_G = "#e8f8f3"   # 초록 버튼 호버
        _HOV_B = "#e8f1fd"   # 파랑 버튼 호버
        _HOV_R = "#fff0ef"   # 빨강 버튼 호버
        _XGRAY = "#c7c7cc"   # X 버튼 색상

        root = tk.Tk()
        root.withdraw()  # tk. 흰 창 즉시 숨김
        self._root = root
        _ico = Path(__file__).resolve().parent / "images" / "craig_icon.ico"
        if _ico.exists():
            try:
                root.iconbitmap(str(_ico))
            except Exception:
                pass
        try:
            _img = _make_rpa_photoimage(root)
            root.iconphoto(True, _img)
            root._rpa_icon = _img
        except Exception:
            pass
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.0)
        root.configure(bg=_SEP)

        w, h = 380, 360
        mx, my, mw, mh = 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()
        if _HAS_SCREENINFO:
            try:
                mons = get_monitors()
                m    = mons[0]
                mx, my, mw, mh = m.x, m.y, m.width, m.height
            except Exception:
                pass
        root.geometry(f"{w}x{h}+{mx + (mw - w) // 2}+{my + (mh - h) // 2}")

        # 외곽 테두리 (1px, 밝은 회색)
        border = tk.Frame(root, bg=_SEP, padx=1, pady=1)
        border.pack(fill="both", expand=True)
        card = tk.Frame(border, bg=_CARD)
        card.pack(fill="both", expand=True)

        _countdown = [12]

        def _set_result(res: str):
            _complete_result_val[0] = res
            if res == "MORE":
                _post_more_event.set()
            _complete_done_event.set()
            try:
                root.destroy()
            except Exception:
                pass

        # fade-in 애니메이션
        def _fade(a=0.0):
            if not root.winfo_exists():
                return
            if a < 1.0:
                root.attributes("-alpha", a)
                root.after(16, lambda: _fade(round(a + 0.08, 2)))
            else:
                root.attributes("-alpha", 1.0)
                root.after(2000, lambda: root.attributes("-topmost", False)
                           if root.winfo_exists() else None)
        root.deiconify()  # withdraw 후 복원 (alpha=0.0이라 흰 창 없음)
        root.after(10, _fade)

        # ── 상단 바 (X 버튼) ──────────────────────────────────
        bar = tk.Frame(card, bg=_CARD, height=32)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        xb = tk.Label(bar, text="\u2715", font=self._fn(11),
                      bg=_CARD, fg=_XGRAY, cursor="hand2")
        xb.pack(side="right", padx=10, pady=6)
        xb.bind("<Enter>", lambda e: xb.configure(fg=_T1))
        xb.bind("<Leave>", lambda e: xb.configure(fg=_XGRAY))
        xb.bind("<Button-1>", lambda e: _set_result("EXIT"))

        # ── 체크 애니메이션 ────────────────────────────────────
        chk = tk.Canvas(card, width=56, height=48,
                        bg=_CARD, highlightthickness=0)
        chk.pack(pady=(0, 4))
        # 체크 배경 원 (초록)
        chk.create_oval(4, 4, 52, 48, fill="#e8f8f3", outline=_GREEN, width=2)
        self._draw_check_animated(chk, root)

        # ── 타이틀 ────────────────────────────────────────────
        title_lbl = tk.Label(card, text="작업완료!",
                             font=self._fn(17, "bold"),
                             bg=_CARD, fg=_T1)
        title_lbl.pack()

        sub_lbl = tk.Label(card, text=f"{count}건 게시 완료",
                           font=self._fn(10), bg=_CARD, fg=_T2)
        sub_lbl.pack(pady=(3, 12))

        # ── 구분선 ─────────────────────────────────────────────
        tk.Frame(card, bg=_SEP, height=1).pack(fill="x")

        # ── 추가 게시 버튼 행: 5개 더 | 10개 더 | 20개 더 ──────
        more_row = tk.Frame(card, bg=_CARD)
        more_row.pack(fill="x")

        for i, (label, cnt) in enumerate([("5개 더", 5), ("10개 더", 10), ("20개 더", 20)]):
            def _click_more(n=cnt):
                _post_more_count[0] = n
                _set_result("MORE")
            btn = tk.Label(more_row, text=label,
                           font=self._fn(13),
                           bg=_CARD, fg=_GREEN, cursor="hand2", pady=12)
            btn.pack(side="left", expand=True, fill="both")
            btn.bind("<Button-1>", lambda e, f=_click_more: f())
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=_HOV_G))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=_CARD))
            if i < 2:
                tk.Frame(more_row, bg=_SEP, width=1).pack(side="left", fill="y")

        # ── 구분선 ─────────────────────────────────────────────
        tk.Frame(card, bg=_SEP, height=1).pack(fill="x")

        # ── 계정변경 버튼 ──────────────────────────────────────
        acct_content = tk.Frame(card, bg=_CARD)
        acct_content.pack(fill="x")

        main_acct_row = tk.Frame(acct_content, bg=_CARD)
        main_acct_row.pack(fill="x")

        def _show_accounts():
            main_acct_row.pack_forget()
            acct_picker.pack(fill="x")
            _countdown[0] = 30

        chg_btn = tk.Label(main_acct_row, text="계정변경",
                           font=self._fn(11),
                           bg=_CARD, fg=_BLUE, cursor="hand2", pady=9)
        chg_btn.pack(fill="x")
        chg_btn.bind("<Button-1>", lambda e: _show_accounts())
        chg_btn.bind("<Enter>", lambda e: chg_btn.configure(bg=_HOV_B))
        chg_btn.bind("<Leave>", lambda e: chg_btn.configure(bg=_CARD))

        # 계정 선택 패널 (숨겨진 상태)
        acct_picker = tk.Frame(acct_content, bg=_CARD)

        def _darken(hc, factor=0.88):
            r = int(int(hc[1:3], 16) * factor)
            g = int(int(hc[3:5], 16) * factor)
            b = int(int(hc[5:7], 16) * factor)
            return "#{:02x}{:02x}{:02x}".format(min(r, 255), min(g, 255), min(b, 255))

        current_email = (self._email or "").lower()
        for acct_id, email, color in _ACCOUNT_LIST:
            if email.lower() == current_email:
                continue
            name = email.split("@")[0]
            hov_c = _darken(color)
            wrap = tk.Frame(acct_picker, bg=_SEP, padx=1, pady=1)
            wrap.pack(fill="x", padx=10, pady=2)
            inner = tk.Label(wrap, text=f"  {name}",
                             font=self._fn(11),
                             bg=color, fg="#1d1d1f", cursor="hand2",
                             pady=7, padx=6, anchor="w")
            inner.pack(fill="both")
            def _click_acct(aid=acct_id):
                _set_result(f"CHANGE_{aid}")
            inner.bind("<Button-1>", lambda e, f=_click_acct: f())
            inner.bind("<Enter>", lambda e, b=inner, h=hov_c: b.configure(bg=h))
            inner.bind("<Leave>", lambda e, b=inner, c=color: b.configure(bg=c))

        def _back_to_main():
            acct_picker.pack_forget()
            main_acct_row.pack(fill="x")
            _countdown[0] = 12

        back_lbl = tk.Label(acct_picker, text="< 돌아가기",
                            font=self._fn(10),
                            bg=_CARD, fg=_XGRAY, cursor="hand2", pady=5)
        back_lbl.pack()
        back_lbl.bind("<Button-1>", lambda e: _back_to_main())
        back_lbl.bind("<Enter>", lambda e: back_lbl.configure(fg=_T1))
        back_lbl.bind("<Leave>", lambda e: back_lbl.configure(fg=_XGRAY))

        # ── 구분선 ─────────────────────────────────────────────
        tk.Frame(card, bg=_SEP, height=1).pack(fill="x")

        # ── 종료하기 버튼 ──────────────────────────────────────
        exit_btn = tk.Label(card, text="종료하기",
                            font=self._fn(13, "bold"),
                            bg=_CARD, fg=_RED, cursor="hand2", pady=11)
        exit_btn.pack(fill="x")
        exit_btn.bind("<Button-1>", lambda e: _set_result("EXIT"))
        exit_btn.bind("<Enter>", lambda e: exit_btn.configure(bg=_HOV_R))
        exit_btn.bind("<Leave>", lambda e: exit_btn.configure(bg=_CARD))

        # ── 구분선 + 카운트다운 ────────────────────────────────
        tk.Frame(card, bg=_SEP, height=1).pack(fill="x")
        countdown_lbl = tk.Label(card, text=f"{_countdown[0]}초 후 자동 종료",
                                 font=self._fn(9),
                                 bg=_BG, fg=_T2, pady=7)
        countdown_lbl.pack(fill="x")

        def _tick():
            if not root.winfo_exists():
                return
            _countdown[0] -= 1
            if _countdown[0] <= 0:
                _set_result("EXIT")
                return
            countdown_lbl.configure(text=f"{_countdown[0]}초 후 자동 종료")
            root.after(1000, _tick)

        root.after(1000, _tick)

        self._drag(root, bar, chk, title_lbl, sub_lbl)
        self._ready.set()
        try:
            root.mainloop()
        except Exception:
            pass
        _complete_done_event.set()   # fallback if window closed externally

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
        root.withdraw()  # tk. 흰 창 즉시 숨김
        self._root = root
        _ico = Path(__file__).resolve().parent / "images" / "craig_icon.ico"
        if _ico.exists():
            try:
                root.iconbitmap(str(_ico))
            except Exception:
                pass
        try:
            _img = _make_rpa_photoimage(root)
            root.iconphoto(True, _img)
            root._rpa_icon = _img   # GC 방지
        except Exception:
            pass
        root.overrideredirect(True)
        if not _BACKGROUND_MODE:
            root.attributes("-topmost", True)   # 처음 표시 시에만 앞으로
        else:
            root.attributes("-topmost", False)
        root.attributes("-alpha", 0.0)
        root.configure(bg=self.BG)

        # 항상 주 모니터(mons[0]) 사용 — 2번 모니터에 창이 생기는 버그 방지
        mx, my, mw, mh = 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()
        if _HAS_SCREENINFO:
            try:
                mons = get_monitors()
                m    = mons[0]   # 항상 주 모니터
                mx, my, mw, mh = m.x, m.y, m.width, m.height
            except Exception:
                pass
        root.geometry(f"{w}x{h}+{mx + (mw - w) // 2}+{my + (mh - h) // 2}")

        border = tk.Frame(root, bg=self.SEP, padx=1, pady=0)
        border.pack(fill="both", expand=True)
        card = tk.Frame(border, bg=self.BG)
        card.pack(fill="both", expand=True)

        def _add_taskbar_button():
            """overrideredirect 창을 작업표시줄에 표시 (WS_EX_APPWINDOW)."""
            try:
                import ctypes as _ct
                GWL_EXSTYLE      = -20
                WS_EX_APPWINDOW  = 0x00040000
                WS_EX_TOOLWINDOW = 0x00000080
                hwnd = root.winfo_id()
                style = _ct.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                style = (style | WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW
                _ct.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                # 스타일 변경을 작업표시줄이 인식하도록 잠깐 숨겼다 복원
                root.withdraw()
                root.after(50, root.deiconify)
            except Exception:
                pass

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
        root.after(200, _add_taskbar_button)   # 창 렌더 후 작업표시줄 등록
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
    root.withdraw()  # tk. 흰 창 즉시 숨김
    _ico = Path(__file__).resolve().parent / "images" / "craig_icon.ico"
    if _ico.exists():
        try:
            root.iconbitmap(str(_ico))
        except Exception:
            pass
    root.title("Craig RPA — 보안 확인")
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

    root.deiconify()  # withdraw 후 복원
    root.mainloop()
    return result[0]


# ── Account list ──────────────────────────────────────────────────────────────
_ACCOUNT_LIST = [
    ("green", "Coreabridge@gmail.com",        "#c8dcc8"),  # 옅은 초록
    ("purple", "airelair00@gmail.com",        "#d8d0e8"),  # 옅은 보라
    ("brown", "ferrari812fast@gmail.com",     "#e8d8c0"),  # 옅은 갈색
    ("gray", "bridgejobkr@gmail.com",         "#d4d4d4"),  # 옅은 회색
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
        root.withdraw()  # tk. 흰 창 즉시 숨김
        _ico = Path(__file__).resolve().parent / "images" / "craig_icon.ico"
        if _ico.exists():
            try:
                root.iconbitmap(str(_ico))
            except Exception:
                pass
        root.title("Craig RPA — 계정 선택")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=_BG)

        w, h = 340, 510
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        if _HAS_SCREENINFO:
            try:
                mons = get_monitors()
                m    = mons[0]   # 항상 주 모니터
                sw, sh = m.width, m.height
                ox, oy = m.x, m.y
            except Exception:
                ox, oy = 0, 0
        else:
            ox, oy = 0, 0
        root.geometry(f"{w}x{h}+{ox + (sw - w) // 2}+{oy + (sh - h) // 2}")
        root.lift()
        root.focus_force()

        # ── Windows 포커스 강화 (cmd 창 뒤로 안 가게) ──
        try:
            import ctypes as _ct3
            _hwnd = root.winfo_id()
            _ct3.windll.user32.SetForegroundWindow(_hwnd)
        except Exception:
            pass

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

        last_runs    = _load_last_runs()
        cnt_var      = tk.IntVar(value=10)
        auto_login_v = tk.BooleanVar(value=_load_prefs().get("auto_login", True))

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
                _save_prefs({"auto_login": auto_login_v.get()})
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

        # ── 자동로그인 체크박스 ──────────────────────────────────
        auto_row = tk.Frame(card, bg=_CARD)
        auto_row.pack(fill="x", padx=16, pady=(2, 6))
        auto_chk = tk.Checkbutton(
            auto_row,
            text="자동로그인 유지  (세션 쿠키 재사용)",
            variable=auto_login_v,
            font=tkfont.Font(family="Malgun Gothic", size=9),
            bg=_CARD, fg=_T2, activebackground=_CARD,
            selectcolor=_CARD, cursor="hand2",
        )
        auto_chk.pack(side="left")

        # ── 마스터 수정 버튼 + 취소 (같은 행) ──────────────────────────────
        tk.Frame(card, bg=_SEP, height=1).pack(fill="x")
        bot_row = tk.Frame(card, bg=_CARD)
        bot_row.pack(fill="x")

        mk_lbl = tk.Label(bot_row, text="🔑 마스터 수정",
                          font=tkfont.Font(family="Malgun Gothic", size=9),
                          bg=_CARD, fg=_T2, cursor="hand2", pady=10, padx=14)
        mk_lbl.pack(side="left")
        mk_lbl.bind("<Enter>", lambda e: mk_lbl.configure(fg=_BLUE))
        mk_lbl.bind("<Leave>", lambda e: mk_lbl.configure(fg=_T2))

        def _open_mk_edit():
            """마스터 키 저장/변경 Toplevel 다이얼로그."""
            try:
                import sys as _sys3
                _sys3.path.insert(0, str(Path(__file__).resolve().parent))
                from tools.rpa_credential_vault import CredentialVault, _save_mk_cache, _load_mk_cache
            except ImportError as _ie:
                return

            top = tk.Toplevel(root)
            top.overrideredirect(True)
            top.attributes("-topmost", True)
            top.configure(bg=_BG)
            top.grab_set()

            tw, th = 320, 290
            top.geometry(f"{tw}x{th}+{ox + (sw - tw) // 2}+{oy + (sh - th) // 2}")

            bt = tk.Frame(top, bg=_SEP, padx=1, pady=1)
            bt.pack(fill="both", expand=True)
            ct = tk.Frame(bt, bg=_CARD)
            ct.pack(fill="both", expand=True)

            _fnt_mk  = tkfont.Font(family="Malgun Gothic", size=10)
            _fnt_mks = tkfont.Font(family="Malgun Gothic", size=9)

            tk.Label(ct, text="🔑  마스터 키 관리",
                     font=tkfont.Font(family="Malgun Gothic", size=13, weight="bold"),
                     bg=_CARD, fg=_T1).pack(pady=(14, 2))
            tk.Label(ct, text="현재 키만 입력 → 저장   |   새 키도 입력 → 키 변경",
                     font=_fnt_mks, bg=_CARD, fg=_T2).pack(pady=(0, 6))
            tk.Frame(ct, bg=_SEP, height=1).pack(fill="x", padx=12)

            def _row(lbl_text):
                fr = tk.Frame(ct, bg=_CARD); fr.pack(fill="x", padx=16, pady=(6, 0))
                tk.Label(fr, text=lbl_text, font=_fnt_mks,
                         bg=_CARD, fg=_T2, anchor="w").pack(fill="x")
                ent = tk.Entry(fr, show="●", font=_fnt_mk, relief="flat", bd=1,
                               highlightthickness=1, highlightbackground=_SEP,
                               highlightcolor=_BLUE)
                ent.pack(fill="x", ipady=5)
                return ent

            e_cur = _row("현재 마스터 키")
            e_new = _row("새 마스터 키  (변경 시만 입력)")
            e_cfm = _row("새 마스터 키 확인")

            err_mk = tk.Label(ct, text="", font=_fnt_mks, bg=_CARD, fg=_RED)
            err_mk.pack(pady=(4, 0))

            def _do_save():
                cur = e_cur.get().strip()
                nw  = e_new.get()
                cfm = e_cfm.get()
                if not cur:
                    err_mk.configure(text="현재 마스터 키를 입력하세요"); return
                # 현재 키 검증 (vault 복호화 시도)
                try:
                    v = CredentialVault()
                    v._master_key = cur.encode("utf-8")
                    test = v.get_decrypted("gray_email")
                    if not test:
                        err_mk.configure(text="현재 마스터 키가 올바르지 않습니다"); return
                except Exception:
                    err_mk.configure(text="현재 마스터 키가 올바르지 않습니다"); return

                if nw:  # 새 키 입력 있으면 → rekey
                    if nw != cfm:
                        err_mk.configure(text="새 마스터 키가 일치하지 않습니다"); return
                    if nw == cur:
                        err_mk.configure(text="현재 키와 동일합니다"); return
                    v2 = CredentialVault()
                    if v2.rekey(cur, nw):
                        err_mk.configure(text="✅ 마스터 키 변경 완료", fg=_BLUE)
                        top.after(1200, lambda: [top.grab_release(), top.destroy()])
                    else:
                        err_mk.configure(text="변경 실패 — 다시 시도하세요")
                else:   # 새 키 없음 → 현재 키 저장만
                    _save_mk_cache(cur.encode("utf-8"))
                    err_mk.configure(text="✅ 마스터 키 저장 완료", fg=_BLUE)
                    top.after(900, lambda: [top.grab_release(), top.destroy()])

            tk.Frame(ct, bg=_SEP, height=1).pack(fill="x", pady=(6, 0))
            br = tk.Frame(ct, bg=_CARD); br.pack(fill="x")

            ok3 = tk.Label(br, text="저장 / 변경",
                           font=tkfont.Font(family="Malgun Gothic", size=12, weight="bold"),
                           bg=_CARD, fg=_BLUE, pady=9, cursor="hand2")
            ok3.pack(side="left", expand=True, fill="both")
            ok3.bind("<Button-1>", lambda e: _do_save())
            ok3.bind("<Enter>", lambda e: ok3.configure(bg=_HOV))
            ok3.bind("<Leave>", lambda e: ok3.configure(bg=_CARD))

            tk.Frame(br, bg=_SEP, width=1).pack(side="left", fill="y")

            cx3 = tk.Label(br, text="취소",
                           font=tkfont.Font(family="Malgun Gothic", size=12),
                           bg=_CARD, fg=_RED, pady=9, cursor="hand2")
            cx3.pack(side="left", expand=True, fill="both")
            cx3.bind("<Button-1>", lambda e: [top.grab_release(), top.destroy()])
            cx3.bind("<Enter>", lambda e: cx3.configure(bg=_HOV))
            cx3.bind("<Leave>", lambda e: cx3.configure(bg=_CARD))

            e_cur.focus_set()
            top.bind("<Return>", lambda e: _do_save())

        mk_lbl.bind("<Button-1>", lambda e: _open_mk_edit())

        tk.Frame(bot_row, bg=_SEP, width=1).pack(side="left", fill="y")

        cancel_lbl = tk.Label(bot_row, text="나중에 하기 (종료)",
                              font=tkfont.Font(family="Malgun Gothic", size=12),
                              bg=_CARD, fg=_RED, cursor="hand2", pady=10)
        cancel_lbl.pack(side="left", expand=True, fill="both")
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

        root.deiconify()  # withdraw 후 복원
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
    root.withdraw()  # tk. 흰 창 즉시 숨김
    root.attributes("-alpha", 0.0)   # flash 방지
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
            m = mons[0]   # 항상 주 모니터
            sw, sh = m.width, m.height
            ox, oy = m.x, m.y
        except Exception:
            pass
    w, h = 300, 205
    root.geometry(f"{w}x{h}+{ox + (sw - w) // 2}+{oy + (sh - h) // 2 - 80}")
    root.attributes("-alpha", 0.0)

    def _fade(a=0.0):
        if root.winfo_exists():
            if a < 1.0:
                root.attributes("-alpha", a)
                root.after(16, lambda: _fade(a + 0.1))
            else:
                root.attributes("-alpha", 1.0)
    root.deiconify()  # withdraw 후 복원 (alpha=0.0이라 흰 창 없음)
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

    def _do_graceful_stop():
        """현재 작업 완료 후 중단 — flag 파일 방식 (크로스 프로세스)"""
        try:
            _sflag = Path(__file__).resolve().parent / "logs" / ".rpa_stop_graceful.flag"
            _sflag.parent.mkdir(parents=True, exist_ok=True)
            _sflag.write_text("stop", encoding="utf-8")
        except Exception:
            pass
        _stop_event.set()
        try:
            root.destroy()
        except Exception:
            pass

    def _do_force_stop():
        """즉시 강제 종료 — lock 파일 PID taskkill (크로스 프로세스)"""
        import subprocess as _sp2
        try:
            lock_dir = Path(__file__).resolve().parent / "logs"
            for _lf in lock_dir.glob(".rpa_*.lock"):
                try:
                    _pid = int(_lf.read_text(encoding="utf-8").strip())
                    _sp2.call(
                        ["taskkill", "/F", "/PID", str(_pid)],
                        creationflags=0x08000000,
                        stdout=_sp2.DEVNULL, stderr=_sp2.DEVNULL,
                    )
                    _lf.unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception:
            pass
        _stop_event.set()
        try:
            root.destroy()
        except Exception:
            pass

    # ── hover 색 (acct_color보다 살짝 어둡게) ──────────────────────────────
    _hov_c = "#{:02x}{:02x}{:02x}".format(
        max(0, int(int(acct_color[1:3], 16) * 0.88)),
        max(0, int(int(acct_color[3:5], 16) * 0.88)),
        max(0, int(int(acct_color[5:7], 16) * 0.88)))

    # ── 중단 버튼 행 (작업 후 중단 | 그만하기) ─────────────────────────────
    stop_row = tk.Frame(card, bg=acct_color)
    stop_row.pack(fill="x")

    after_btn = tk.Label(stop_row, text="작업 후 중단",
                         font=tkfont.Font(family="Malgun Gothic", size=11),
                         bg=acct_color, fg="#0071e3", pady=8, cursor="hand2")
    after_btn.pack(side="left", expand=True, fill="both")
    after_btn.bind("<Button-1>", lambda e: _do_graceful_stop())
    after_btn.bind("<Enter>", lambda e: after_btn.configure(bg=_hov_c))
    after_btn.bind("<Leave>", lambda e: after_btn.configure(bg=acct_color))

    tk.Frame(stop_row, bg=_sc, width=1).pack(side="left", fill="y")

    force_btn = tk.Label(stop_row, text="그만하기",
                         font=tkfont.Font(family="Malgun Gothic", size=11, weight="bold"),
                         bg=acct_color, fg="#ff3b30", pady=8, cursor="hand2")
    force_btn.pack(side="left", expand=True, fill="both")
    force_btn.bind("<Button-1>", lambda e: _do_force_stop())
    force_btn.bind("<Enter>", lambda e: force_btn.configure(bg=_hov_c))
    force_btn.bind("<Leave>", lambda e: force_btn.configure(bg=acct_color))

    # ── 확인 (계속) ─────────────────────────────────────────────────────────
    tk.Frame(card, bg=_sc, height=1).pack(fill="x")

    ok_btn = tk.Label(card, text="확인 (계속)",
                      font=tkfont.Font(family="Malgun Gothic", size=11),
                      bg=acct_color, fg="#6e6e73", pady=7, cursor="hand2")
    ok_btn.pack(fill="x")
    ok_btn.bind("<Button-1>", lambda e: _close())
    ok_btn.bind("<Enter>", lambda e: ok_btn.configure(bg=_hov_c))
    ok_btn.bind("<Leave>", lambda e: ok_btn.configure(bg=acct_color))

    def _press(e): root._dx, root._dy = e.x_root, e.y_root
    def _move(e):
        x = root.winfo_x() + e.x_root - root._dx
        y = root.winfo_y() + e.y_root - root._dy
        root._dx, root._dy = e.x_root, e.y_root
        root.geometry(f"+{x}+{y}")
    for dw in (card, border):
        dw.bind("<ButtonPress-1>", _press)
        dw.bind("<B1-Motion>", _move)

    root.after(8000, lambda: _close() if root.winfo_exists() else None)
    root.mainloop()


def ask_vault_setup() -> bool:
    """Vault 파일 없을 때 비밀번호 입력 팝업.
    마스터 키 + 4개 계정 비밀번호 입력 → .rpa_vault.enc.json 생성.
    Returns True if setup completed, False if cancelled."""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from tools.rpa_credential_vault import CredentialVault, ACCOUNTS
    except ImportError:
        return False

    result = [False]
    _BG   = "#f5f5f7"; _CARD = "#ffffff"; _SEP = "#d2d2d7"
    _T1   = "#1d1d1f"; _T2   = "#6e6e73"; _BLUE = "#0071e3"
    _RED  = "#ff3b30"; _HOV  = "#e8e8ed"

    _ACCT_ORDER = ["gray", "green", "brown", "purple"]
    _ACCT_LABEL = {"gray": "회색 (bridgejobkr)", "green": "초록 (Coreabridge)",
                   "brown": "갈색 (ferrari812fast)", "purple": "보라 (airelair00)"}

    def _build():
        root = tk.Tk()
        root.withdraw()  # tk. 흰 창 즉시 숨김
        _ico = Path(__file__).resolve().parent / "images" / "craig_icon.ico"
        if _ico.exists():
            try: root.iconbitmap(str(_ico))
            except Exception: pass
        root.title("Craig RPA — 비밀번호 설정")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=_BG)

        w, h = 360, 500
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        root.lift(); root.focus_force()

        border = tk.Frame(root, bg=_SEP, padx=1, pady=1)
        border.pack(fill="both", expand=True)
        card = tk.Frame(border, bg=_CARD)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="🔐  비밀번호 설정",
                 font=tkfont.Font(family="Malgun Gothic", size=15, weight="bold"),
                 bg=_CARD, fg=_T1).pack(pady=(16, 2))
        tk.Label(card, text="마스터 키와 4개 계정 비밀번호를 입력하세요\n(입력 내용은 화면에 표시되지 않습니다)",
                 font=tkfont.Font(family="Malgun Gothic", size=9),
                 bg=_CARD, fg=_T2, justify="center").pack(pady=(0, 8))
        tk.Frame(card, bg=_SEP, height=1).pack(fill="x", padx=12)

        entries = {}
        _fnt = tkfont.Font(family="Malgun Gothic", size=10)
        _fnt_sm = tkfont.Font(family="Malgun Gothic", size=9)

        # 마스터 키
        f = tk.Frame(card, bg=_CARD); f.pack(fill="x", padx=16, pady=(10, 2))
        tk.Label(f, text="마스터 키 (기억할 암호)", font=_fnt_sm, bg=_CARD, fg=_T2, anchor="w").pack(fill="x")
        e = tk.Entry(f, show="●", font=_fnt, relief="flat", bd=1,
                     highlightthickness=1, highlightbackground=_SEP, highlightcolor=_BLUE)
        e.pack(fill="x", ipady=5); entries["master"] = e

        tk.Frame(card, bg=_SEP, height=1).pack(fill="x", padx=12, pady=(8, 0))

        # 4개 계정 비밀번호
        for ak in _ACCT_ORDER:
            f = tk.Frame(card, bg=_CARD); f.pack(fill="x", padx=16, pady=(6, 0))
            tk.Label(f, text=_ACCT_LABEL[ak], font=_fnt_sm, bg=_CARD, fg=_T2, anchor="w").pack(fill="x")
            e = tk.Entry(f, show="●", font=_fnt, relief="flat", bd=1,
                         highlightthickness=1, highlightbackground=_SEP, highlightcolor=_BLUE)
            e.pack(fill="x", ipady=5); entries[ak] = e

        err_lbl = tk.Label(card, text="", font=_fnt_sm, bg=_CARD, fg=_RED)
        err_lbl.pack(pady=(6, 0))

        def _submit():
            mk = entries["master"].get().strip()
            if not mk:
                err_lbl.configure(text="마스터 키를 입력하세요"); return
            pws = {}
            for ak in _ACCT_ORDER:
                pw = entries[ak].get()
                if not pw:
                    err_lbl.configure(text=f"{_ACCT_LABEL[ak]} 비밀번호를 입력하세요"); return
                pws[ak] = pw
            vault = CredentialVault()
            ok = vault.setup_from_gui(mk, pws)
            if ok:
                result[0] = True
                root.destroy()
            else:
                err_lbl.configure(text="저장 실패 — 다시 시도하세요")

        tk.Frame(card, bg=_SEP, height=1).pack(fill="x", pady=(8, 0))
        btn_row = tk.Frame(card, bg=_CARD); btn_row.pack(fill="x")

        ok_lbl = tk.Label(btn_row, text="저장",
                          font=tkfont.Font(family="Malgun Gothic", size=13, weight="bold"),
                          bg=_CARD, fg=_BLUE, pady=10, cursor="hand2")
        ok_lbl.pack(side="left", expand=True, fill="both")
        ok_lbl.bind("<Button-1>", lambda e: _submit())
        ok_lbl.bind("<Enter>", lambda e: ok_lbl.configure(bg=_HOV))
        ok_lbl.bind("<Leave>", lambda e: ok_lbl.configure(bg=_CARD))

        tk.Frame(btn_row, bg=_SEP, width=1).pack(side="left", fill="y")

        cancel_lbl = tk.Label(btn_row, text="취소",
                              font=tkfont.Font(family="Malgun Gothic", size=13),
                              bg=_CARD, fg=_RED, pady=10, cursor="hand2")
        cancel_lbl.pack(side="left", expand=True, fill="both")
        cancel_lbl.bind("<Button-1>", lambda e: root.destroy())
        cancel_lbl.bind("<Enter>", lambda e: cancel_lbl.configure(bg=_HOV))
        cancel_lbl.bind("<Leave>", lambda e: cancel_lbl.configure(bg=_CARD))

        entries["master"].focus_set()
        root.bind("<Return>", lambda e: _submit())

        def _press(e): root._dx, root._dy = e.x_root, e.y_root
        def _move(e):
            x = root.winfo_x() + e.x_root - root._dx
            y = root.winfo_y() + e.y_root - root._dy
            root._dx, root._dy = e.x_root, e.y_root
            root.geometry(f"+{x}+{y}")
        for dw in (card, border):
            dw.bind("<ButtonPress-1>", _press)
            dw.bind("<B1-Motion>", _move)

        root.deiconify()  # withdraw 후 복원
        root.mainloop()

    import threading as _threading
    if _threading.current_thread() is _threading.main_thread():
        _build()
    else:
        t = _threading.Thread(target=_build, daemon=True)
        t.start(); t.join(timeout=300)
    return result[0]


def ask_master_key_gui() -> str:
    """마스터 키 GUI 입력 팝업 — getpass 대체 (비인터랙티브 환경 대응).
    Returns 입력된 문자열, 취소 시 ""."""
    result = [""]
    _BG = "#f5f5f7"; _CARD = "#ffffff"; _SEP = "#d2d2d7"
    _T1 = "#1d1d1f"; _T2 = "#6e6e73"; _BLUE = "#0071e3"
    _RED = "#ff3b30"; _HOV = "#e8e8ed"

    def _build():
        root = tk.Tk()
        root.withdraw()  # tk. 흰 창 즉시 숨김
        root.title("Craig RPA — 마스터 키 입력")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=_BG)

        w, h = 320, 230
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        root.lift(); root.focus_force()

        border = tk.Frame(root, bg=_SEP, padx=1, pady=1)
        border.pack(fill="both", expand=True)
        card = tk.Frame(border, bg=_CARD)
        card.pack(fill="both", expand=True)

        _fnt = tkfont.Font(family="Malgun Gothic", size=10)
        _fnt_sm = tkfont.Font(family="Malgun Gothic", size=9)

        tk.Label(card, text="🔑  마스터 키 입력",
                 font=tkfont.Font(family="Malgun Gothic", size=13, weight="bold"),
                 bg=_CARD, fg=_T1).pack(pady=(16, 2))
        tk.Label(card, text="저장된 자격증명을 복호화하려면\n마스터 키를 입력하세요",
                 font=_fnt_sm, bg=_CARD, fg=_T2, justify="center").pack(pady=(0, 8))
        tk.Frame(card, bg=_SEP, height=1).pack(fill="x", padx=12)

        f = tk.Frame(card, bg=_CARD); f.pack(fill="x", padx=16, pady=(10, 0))
        e = tk.Entry(f, show="●", font=_fnt, relief="flat", bd=1,
                     highlightthickness=1, highlightbackground=_SEP, highlightcolor=_BLUE)
        e.pack(fill="x", ipady=6)

        err_lbl = tk.Label(card, text="", font=_fnt_sm, bg=_CARD, fg=_RED)
        err_lbl.pack(pady=(4, 0))

        def _submit():
            val = e.get().strip()
            if not val:
                err_lbl.configure(text="마스터 키를 입력하세요"); return
            result[0] = val
            root.destroy()

        tk.Frame(card, bg=_SEP, height=1).pack(fill="x", pady=(8, 0))
        btn_row = tk.Frame(card, bg=_CARD); btn_row.pack(fill="x")

        ok_lbl = tk.Label(btn_row, text="확인",
                          font=tkfont.Font(family="Malgun Gothic", size=12, weight="bold"),
                          bg=_CARD, fg=_BLUE, pady=9, cursor="hand2")
        ok_lbl.pack(side="left", expand=True, fill="both")
        ok_lbl.bind("<Button-1>", lambda ev: _submit())
        ok_lbl.bind("<Enter>", lambda ev: ok_lbl.configure(bg=_HOV))
        ok_lbl.bind("<Leave>", lambda ev: ok_lbl.configure(bg=_CARD))

        tk.Frame(btn_row, bg=_SEP, width=1).pack(side="left", fill="y")

        cancel_lbl = tk.Label(btn_row, text="취소",
                              font=tkfont.Font(family="Malgun Gothic", size=12),
                              bg=_CARD, fg=_RED, pady=9, cursor="hand2")
        cancel_lbl.pack(side="left", expand=True, fill="both")
        cancel_lbl.bind("<Button-1>", lambda ev: root.destroy())
        cancel_lbl.bind("<Enter>", lambda ev: cancel_lbl.configure(bg=_HOV))
        cancel_lbl.bind("<Leave>", lambda ev: cancel_lbl.configure(bg=_CARD))

        # ── 마스터 키 변경 링크 ────────────────────────────────────────────
        change_lbl = tk.Label(card, text="마스터 키 변경 ›",
                              font=_fnt_sm, bg=_CARD, fg=_T2, cursor="hand2")
        change_lbl.pack(pady=(2, 6))

        def _open_change():
            """마스터 키 변경 Toplevel 다이얼로그."""
            try:
                import sys as _sys2
                _sys2.path.insert(0, str(Path(__file__).resolve().parent))
                from tools.rpa_credential_vault import CredentialVault
            except ImportError:
                err_lbl.configure(text="vault 모듈 임포트 실패"); return

            top = tk.Toplevel(root)
            top.overrideredirect(True)
            top.attributes("-topmost", True)
            top.configure(bg=_BG)
            top.grab_set()

            tw, th = 320, 280
            top.geometry(f"{tw}x{th}+{(sw - tw) // 2}+{(sh - th) // 2}")

            bt = tk.Frame(top, bg=_SEP, padx=1, pady=1)
            bt.pack(fill="both", expand=True)
            ct = tk.Frame(bt, bg=_CARD)
            ct.pack(fill="both", expand=True)

            tk.Label(ct, text="🔑  마스터 키 변경",
                     font=tkfont.Font(family="Malgun Gothic", size=13, weight="bold"),
                     bg=_CARD, fg=_T1).pack(pady=(14, 2))
            tk.Label(ct, text="현재 키와 새 키를 입력하세요",
                     font=_fnt_sm, bg=_CARD, fg=_T2).pack(pady=(0, 6))
            tk.Frame(ct, bg=_SEP, height=1).pack(fill="x", padx=12)

            def _field(parent, label):
                f2 = tk.Frame(parent, bg=_CARD); f2.pack(fill="x", padx=16, pady=(6, 0))
                tk.Label(f2, text=label, font=_fnt_sm, bg=_CARD, fg=_T2, anchor="w").pack(fill="x")
                ent = tk.Entry(f2, show="●", font=_fnt, relief="flat", bd=1,
                               highlightthickness=1, highlightbackground=_SEP, highlightcolor=_BLUE)
                ent.pack(fill="x", ipady=5)
                return ent

            e_old = _field(ct, "현재 마스터 키")
            e_new = _field(ct, "새 마스터 키")
            e_cfm = _field(ct, "새 마스터 키 확인")

            err_t = tk.Label(ct, text="", font=_fnt_sm, bg=_CARD, fg=_RED)
            err_t.pack(pady=(4, 0))

            def _do_rekey():
                old_k = e_old.get().strip()
                new_k = e_new.get()
                cfm_k = e_cfm.get()
                if not old_k:
                    err_t.configure(text="현재 마스터 키를 입력하세요"); return
                if not new_k:
                    err_t.configure(text="새 마스터 키를 입력하세요"); return
                if new_k != cfm_k:
                    err_t.configure(text="새 마스터 키가 일치하지 않습니다"); return
                if new_k == old_k:
                    err_t.configure(text="현재 키와 동일합니다"); return
                vault_obj = CredentialVault()
                if vault_obj.rekey(old_k, new_k):
                    # 성공: 메인 입력창에 새 키 자동 입력 + 성공 메시지
                    e.delete(0, "end")
                    e.insert(0, new_k)
                    err_lbl.configure(text="✅ 마스터 키 변경 완료 — 확인을 누르세요", fg=_BLUE)
                    top.grab_release()
                    top.destroy()
                else:
                    err_t.configure(text="변경 실패 — 현재 마스터 키를 확인하세요")

            tk.Frame(ct, bg=_SEP, height=1).pack(fill="x", pady=(6, 0))
            br2 = tk.Frame(ct, bg=_CARD); br2.pack(fill="x")

            ok2 = tk.Label(br2, text="변경",
                           font=tkfont.Font(family="Malgun Gothic", size=12, weight="bold"),
                           bg=_CARD, fg=_BLUE, pady=9, cursor="hand2")
            ok2.pack(side="left", expand=True, fill="both")
            ok2.bind("<Button-1>", lambda ev: _do_rekey())
            ok2.bind("<Enter>", lambda ev: ok2.configure(bg=_HOV))
            ok2.bind("<Leave>", lambda ev: ok2.configure(bg=_CARD))

            tk.Frame(br2, bg=_SEP, width=1).pack(side="left", fill="y")

            cx2 = tk.Label(br2, text="취소",
                           font=tkfont.Font(family="Malgun Gothic", size=12),
                           bg=_CARD, fg=_RED, pady=9, cursor="hand2")
            cx2.pack(side="left", expand=True, fill="both")
            cx2.bind("<Button-1>", lambda ev: [top.grab_release(), top.destroy()])
            cx2.bind("<Enter>", lambda ev: cx2.configure(bg=_HOV))
            cx2.bind("<Leave>", lambda ev: cx2.configure(bg=_CARD))

            e_old.focus_set()
            top.bind("<Return>", lambda ev: _do_rekey())

        change_lbl.bind("<Button-1>", lambda ev: _open_change())
        change_lbl.bind("<Enter>", lambda ev: change_lbl.configure(fg=_BLUE))
        change_lbl.bind("<Leave>", lambda ev: change_lbl.configure(fg=_T2))

        e.focus_set()
        root.bind("<Return>", lambda ev: _submit())

        def _press(ev): root._dx, root._dy = ev.x_root, ev.y_root
        def _move(ev):
            x = root.winfo_x() + ev.x_root - root._dx
            y = root.winfo_y() + ev.y_root - root._dy
            root._dx, root._dy = ev.x_root, ev.y_root
            root.geometry(f"+{x}+{y}")
        for dw in (card, border):
            dw.bind("<ButtonPress-1>", _press)
            dw.bind("<B1-Motion>", _move)

        root.deiconify()  # withdraw 후 복원
        root.mainloop()

    import threading as _threading
    if _threading.current_thread() is _threading.main_thread():
        _build()
    else:
        t = _threading.Thread(target=_build, daemon=True)
        t.start(); t.join(timeout=120)
    return result[0]


# ── Module-level exports ──────────────────────────────────────────────────────
_overlay        = RPAOverlay()
show_working    = _overlay.show_working
show_complete   = _overlay.show_complete
update_progress = _overlay.update_progress
update_status   = _overlay.update_status
close           = _overlay.close
# wants_more / wants_more_count 는 모듈 상단에 이미 정의됨
# set_background_mode는 모듈 상단에 정의됨
