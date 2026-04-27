"""
BRIDGE RPA Admin Board  v6
============================
- 숨겨진 Tk 펌프 + Toplevel 창 (작업표시줄 "tk" 방지)
- 계정 카드: Canvas 체크박스 (선택) + 수정 버튼 (편집)
- 헤더 오른쪽 숨기기 버튼
- 하단: [시작하기] [즉시중단] 나란히
- 이모지 전면 금지 (GDI deadlock 방지)
"""

import ctypes
import hashlib
import hmac as _hmac_mod
import json
import os
import queue
import re as _re
import subprocess
import sys
import threading
import time as _time
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox

# ── 경로 ─────────────────────────────────────────────────────────────────────
_DIR            = Path(__file__).resolve().parent
LOGS_DIR        = _DIR / "logs"
HWND_FILE       = LOGS_DIR / ".overlay_hwnd.txt"
PID_FILE        = LOGS_DIR / ".rpa_pid.txt"
ADMIN_HWND_FILE = LOGS_DIR / ".admin_hwnd.txt"
PYTHONW         = str(Path(sys.executable).parent / "pythonw.exe")
if not Path(PYTHONW).exists():
    PYTHONW = sys.executable
SCRIPT = str(_DIR / "craigslist_auto_rpa.py")

# ── 계정 정의 (Gray → Green → Brown → Purple 순) ─────────────────────────────
_ACCOUNT_DEFS = [
    {"file": "account4.env", "color": "#9ca3af", "tag": "GRAY",   "fallback": "bridgejobkr"},
    {"file": "account1.env", "color": "#22c55e", "tag": "GREEN",  "fallback": "Coreabridge"},
    {"file": "account3.env", "color": "#e67e22", "tag": "BROWN",  "fallback": "Ferrari812"},
    {"file": "account2.env", "color": "#a855f7", "tag": "PURPLE", "fallback": "airelair"},
]

# ── 팔레트 (목업 모던 다크) ──────────────────────────────────────────────────
BG      = "#0d1017"   # 메인 배경 (가장 어두움)
SURFACE = "#161a23"   # 헤더/패널 배경
CARD    = "#1e2230"   # 카드 배경
CARD_HI = "#252a3a"   # 카드 호버
BORDER  = "#2a2f3d"   # 외곽선
BORDER_LI = "#3a4055" # 강조 외곽선
TEXT1   = "#f1f5f9"   # 제1 텍스트
TEXT2   = "#94a3b8"   # 제2 텍스트
TEXT3   = "#64748b"   # 제3 텍스트 (placeholder)
GREEN   = "#22c55e"   # 단일계정 액션
GREEN_D = "#15803d"
BLUE    = "#3b82f6"   # 배치 액션
BLUE_D  = "#1e40af"
RED     = "#ef4444"   # 위험/중단
RED_D   = "#991b1b"
RED_BG  = "#2d0a0a"
RED_FG  = "#f87171"
HIDE_BG = "#1e2230"
HIDE_FG = "#94a3b8"
DIM     = "#1a1e2a"
ACCENT  = "#6366f1"   # 브랜드 인디고

# ── 폰트 (+2pt, 자간 넓힘) ───────────────────────────────────────────────────
FN_HEAD = ("Malgun Gothic", 15, "bold")
FN_MID  = ("Malgun Gothic", 12, "bold")
FN_SM   = ("Malgun Gothic", 11)
FN_TAG  = ("Consolas",      10, "bold")
FN_MONO = ("Consolas",      11)
FN_BTN  = ("Malgun Gothic", 12, "bold")

# ── 게이지 액션 키워드 매핑 ──────────────────────────────────────────────────
_ACTION_KEYWORDS = [
    ("publish",             "게시 완료"),
    ("[POST]",              "게시글 제출 중"),
    ("[LOGIN] 성공",         "로그인 성공"),
    ("[LOGIN]",             "Craigslist 로그인 중"),
    ("[DRIVER]",            "Chrome 실행 중"),
    ("copyfromAnother",     "게시물 복사 중"),
    ("?s=area",             "지역 선택 중"),
    ("?s=type",             "분류 입력 중"),
    ("?s=cat",              "카테고리 선택 중"),
    ("[DRAFT]",             "초안 준비 중"),
    ("Chrome 시작",          "Chrome 실행 중"),
    ("로그인",               "Craigslist 로그인 중"),
    ("제목",                 "제목 작성 중"),
    ("본문",                 "본문 작성 중"),
    ("대상 포지션",           "대상 포지션 확인 중"),
]


# ══════════════════════════════════════════ .env 유틸 ══════════════════════════

def _parse_env(path: Path) -> dict:
    result = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def _write_env(path: Path, updates: dict):
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    written = set()
    out = []
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k = s.split("=", 1)[0].strip()
            if k in updates:
                out.append(f"{k}={updates[k]}")
                written.add(k)
                continue
        out.append(line)
    for k, v in updates.items():
        if k not in written:
            out.append(f"{k}={v}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


# ── 파일 무결성 (HMAC-SHA256) ────────────────────────────────────────────────
_HASH_FILE = _DIR / ".account_hashes.json"


def _integrity_key() -> bytes:
    """무결성 검사 키 — .bridge.key 파생."""
    kp = _DIR / ".bridge.key"
    raw = kp.read_bytes().strip() if kp.exists() else b"BRIDGE_RPA_DEFAULT_INTEGRITY_2026"
    return hashlib.sha256(raw + b"ACCOUNT_INTEGRITY_V1").digest()


def _env_hmac(path: Path) -> str:
    content = path.read_bytes() if path.exists() else b""
    return _hmac_mod.new(_integrity_key(), content, hashlib.sha256).hexdigest()


def _save_integrity():
    hashes = {d["file"]: _env_hmac(_DIR / d["file"]) for d in _ACCOUNT_DEFS}
    _HASH_FILE.write_text(json.dumps(hashes, indent=2), encoding="utf-8")


def _check_integrity() -> list[str]:
    """변조된 계정 파일 이름 목록 반환. 최초 실행 시 해시 기록 후 빈 목록."""
    if not _HASH_FILE.exists():
        _save_integrity()
        return []
    try:
        saved = json.loads(_HASH_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [
        d["file"]
        for d in _ACCOUNT_DEFS
        if d["file"] in saved and _env_hmac(_DIR / d["file"]) != saved[d["file"]]
    ]


def _encrypt_password(plain: str) -> str:
    """암호화 실패 시 평문 저장 금지 — 예외를 호출자에게 전달."""
    sys.path.insert(0, str(_DIR))
    from crypto_util import encrypt_value      # 실패 시 ImportError → 호출자가 처리
    return encrypt_value(plain)


def _decrypt_password(enc: str) -> str:
    if not enc.startswith("ENC:"):
        return enc
    try:
        from crypto_util import decrypt_value
        return decrypt_value(enc)
    except Exception:
        return ""


# ── PID / HWND 범위 검증 ──────────────────────────────────────────────────────
_PID_MAX  = 4_194_304   # Windows 최대 PID
_HWND_MAX = 0xFFFF_FFFF


def _safe_pid(raw: str) -> int | None:
    try:
        pid = int(raw.strip())
        return pid if 1 <= pid <= _PID_MAX else None
    except (ValueError, OverflowError):
        return None


def _safe_hwnd(raw: str) -> int | None:
    try:
        hwnd = int(raw.strip())
        return hwnd if 1 <= hwnd <= _HWND_MAX else None
    except (ValueError, OverflowError):
        return None


def _load_accounts() -> list[dict]:
    result = []
    for d in _ACCOUNT_DEFS:
        env_path = _DIR / d["file"]
        data     = _parse_env(env_path)
        email    = data.get("CRAIGSLIST_EMAIL", "")
        label    = email.split("@")[0] if email else d["fallback"]
        result.append({
            "file": d["file"], "id": Path(d["file"]).stem,
            "color": d["color"], "tag": d["tag"],
            "label": label, "email": email,
        })
    return result


# ══════════════════════════════════════════ ctypes 유틸 ═══════════════════════

def _bring_hwnd_to_front(hwnd: int) -> bool:
    # 2026-04-26 정책: 사용자 작업창 위로 강제 띄우기 금지 (BRIDGE_FORCE_FOREGROUND=1 만 예외)
    if os.getenv("BRIDGE_FORCE_FOREGROUND", "0") != "1":
        # 보이긴 하되 포커스/topmost 강탈 안 함 (ShowWindow=SW_SHOWNOACTIVATE만)
        try:
            ctypes.windll.user32.ShowWindow(hwnd, 4)  # SW_SHOWNOACTIVATE
            return True
        except Exception:
            return False
    try:
        u = ctypes.windll.user32
        fg    = u.GetForegroundWindow()
        fg_t  = u.GetWindowThreadProcessId(fg,   None)
        tgt_t = u.GetWindowThreadProcessId(hwnd, None)
        if fg_t and tgt_t and fg_t != tgt_t:
            u.AttachThreadInput(fg_t, tgt_t, True)
        u.ShowWindow(hwnd, 9)
        u.BringWindowToTop(hwnd)
        u.SetForegroundWindow(hwnd)
        if fg_t and tgt_t and fg_t != tgt_t:
            u.AttachThreadInput(fg_t, tgt_t, False)
        return True
    except Exception:
        return False


def _check_running_overlay() -> int | None:
    if not HWND_FILE.exists():
        return None
    try:
        hwnd = _safe_hwnd(HWND_FILE.read_text(encoding="utf-8"))
        if hwnd and ctypes.windll.user32.IsWindow(hwnd):
            return hwnd
        HWND_FILE.unlink(missing_ok=True)
    except Exception:
        pass
    return None


def _kill_rpa():
    if not PID_FILE.exists():
        return
    try:
        pid = _safe_pid(PID_FILE.read_text(encoding="utf-8"))
        if pid is None:
            PID_FILE.unlink(missing_ok=True)
            return
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                       capture_output=True, timeout=5)
        PID_FILE.unlink(missing_ok=True)
        HWND_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ══════════════════════════════════════════ 공통 위젯 ════════════════════════

def _div(parent, bg=BORDER, padx=20, pady=0):
    tk.Frame(parent, bg=bg, height=1).pack(fill="x", padx=padx, pady=pady)


class RoundCanvas(tk.Canvas):
    """Canvas 기반 라운드 버튼."""
    R = 12

    def __init__(self, parent, h, fill, text, text_color,
                 command=None, sub_text="", font=None, **kw):
        super().__init__(parent, height=h, bg=BG,
                         highlightthickness=0, bd=0, **kw)
        self._fill    = fill
        self._text    = text
        self._sub     = sub_text
        self._tc      = text_color
        self._cmd     = command
        self._font    = font or FN_BTN
        self._hover   = False
        self._enabled = True
        self.bind("<Configure>", self._draw)
        self.bind("<Button-1>",  self._click)
        self.bind("<Enter>",     self._enter)
        self.bind("<Leave>",     self._leave)

    def _draw(self, _=None):
        self.delete("all")
        w, h, r = self.winfo_width(), self.winfo_height(), self.R
        if w < 4:
            return
        f = self._fill if self._enabled else DIM
        if self._hover and self._enabled:
            f = self._lighten(f, 20)
        self._rr(0, 0, w, h, r, f)
        cy = h // 2
        if self._sub:
            self.create_text(w // 2, cy - 8, text=self._text,
                             fill=self._tc, font=self._font, anchor="center")
            self.create_text(w // 2, cy + 9, text=self._sub,
                             fill=self._tc, font=FN_SM, anchor="center")
        else:
            self.create_text(w // 2, cy, text=self._text,
                             fill=self._tc, font=self._font, anchor="center")

    def _rr(self, x1, y1, x2, y2, r, fill):
        for args in [
            (x1, y1, x1+2*r, y1+2*r, 90,  90),
            (x2-2*r, y1, x2, y1+2*r, 0,   90),
            (x1, y2-2*r, x1+2*r, y2, 180, 90),
            (x2-2*r, y2-2*r, x2, y2, 270, 90),
        ]:
            self.create_arc(*args[:4], start=args[4], extent=args[5],
                            fill=fill, outline=fill)
        self.create_rectangle(x1+r, y1, x2-r, y2, fill=fill, outline=fill)
        self.create_rectangle(x1, y1+r, x2, y2-r, fill=fill, outline=fill)

    @staticmethod
    def _lighten(h, amt=20):
        r = min(255, int(h[1:3], 16) + amt)
        g = min(255, int(h[3:5], 16) + amt)
        b = min(255, int(h[5:7], 16) + amt)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _enter(self, _):
        self._hover = True
        self.configure(cursor="hand2" if self._enabled else "")
        self._draw()

    def _leave(self, _):
        self._hover = False
        self._draw()

    def _click(self, _):
        if self._cmd and self._enabled:
            self._cmd()

    def update_text(self, text):
        self._text = text
        self._draw()

    def update_fill(self, fill, tc=None):
        self._fill = fill
        if tc:
            self._tc = tc
        self._draw()

    def set_enabled(self, v: bool):
        self._enabled = v
        self._draw()


class AccountCard(tk.Canvas):
    """계정 카드 — 우측 체크박스(선택) + 수정 버튼(편집)."""
    H  = 66
    R  = 10
    CB = 22   # 체크박스 크기

    def __init__(self, parent, acct: dict, on_edit, **kw):
        super().__init__(parent, height=self.H, bg=BG,
                         highlightthickness=0, bd=0, **kw)
        self.acct      = acct
        self._on_edit  = on_edit
        self._selected = True
        self._edit_box = None   # (x1, x2)
        self._cb_box   = None   # (x1, x2)

        self.bind("<Configure>", self._draw)
        self.bind("<Button-1>",  self._click)
        self.bind("<Motion>",    self._motion)
        self.bind("<Leave>",     lambda _: self.configure(cursor=""))

    # ── 퍼블릭 ──────────────────────────────────────────
    @property
    def selected(self):
        return self._selected

    def select(self):
        self._selected = True
        self._draw()

    def deselect(self):
        self._selected = False
        self._draw()

    def update_label(self, label: str):
        self.acct["label"] = label
        self._draw()

    # ── 그리기 ──────────────────────────────────────────
    def _draw(self, _=None):
        self.delete("all")
        w, h, r = self.winfo_width(), self.winfo_height(), self.R
        if w < 4:
            return

        color = self.acct["color"]

        # 카드 배경
        if self._selected:
            bg = self._tint(color, 0.12)
            self._rr(0, 0, w, h, r, bg)
            self._rr(0, 0, 5, h, 0, color)
        else:
            self._rr(0, 0, w, h, r, DIM)
            self._rr(0, 0, 5, h, 0, BORDER)

        PAD_R = 14

        # ── 체크박스 (우측 끝) ──────────────────────────
        CB = self.CB
        cb_x2 = w - PAD_R
        cb_x1 = cb_x2 - CB
        cb_y1 = h // 2 - CB // 2
        cb_y2 = h // 2 + CB // 2
        self._cb_box = (cb_x1, cb_x2)

        if self._selected:
            self._rr(cb_x1, cb_y1, cb_x2, cb_y2, 5, color)
            # 체크마크
            tx1 = cb_x1 + 4
            ty1 = cb_y1 + CB // 2
            tmx = cb_x1 + CB // 3 + 1
            tmy = cb_y2 - 4
            tx2 = cb_x2 - 3
            ty2 = cb_y1 + 4
            self.create_line(tx1, ty1, tmx, tmy,
                             fill=BG, width=2.5, capstyle="round")
            self.create_line(tmx, tmy, tx2, ty2,
                             fill=BG, width=2.5, capstyle="round")
        else:
            # 빈 체크박스 (테두리)
            self._rr(cb_x1, cb_y1, cb_x2, cb_y2, 5, TEXT3)
            self._rr(cb_x1 + 1, cb_y1 + 1, cb_x2 - 1, cb_y2 - 1, 4, DIM)

        # ── 수정 버튼 (체크박스 왼쪽) ───────────────────
        EDIT_W = 38
        ex2 = cb_x1 - 8
        ex1 = ex2 - EDIT_W
        ey1, ey2 = h // 2 - 12, h // 2 + 12
        self._edit_box = (ex1, ex2)
        edit_bg = SURFACE if self._selected else BORDER
        self._rr(ex1, ey1, ex2, ey2, 6, edit_bg)
        self.create_text((ex1 + ex2) // 2, h // 2, text="수정",
                         fill=TEXT2, font=("Malgun Gothic", 10), anchor="center")

        # ── 태그 뱃지 ────────────────────────────────────
        TAG_X, TAG_Y = 16, h // 2 - 10
        tag = self.acct["tag"]
        tw = max(40, len(tag) * 8 + 12)
        self._rr(TAG_X, TAG_Y, TAG_X + tw, TAG_Y + 20, 5,
                 color if self._selected else TEXT3)
        self.create_text(TAG_X + tw // 2, TAG_Y + 10, text=tag,
                         fill=BG, font=FN_TAG, anchor="center")

        # ── 계정명 + 이메일 ──────────────────────────────
        LBL_X = TAG_X + tw + 12
        tc = TEXT1 if self._selected else TEXT3
        self.create_text(LBL_X, h // 2 - 8, text=self.acct["label"],
                         fill=tc, font=FN_MID, anchor="w")
        self.create_text(LBL_X, h // 2 + 10, text=self.acct["email"],
                         fill=TEXT3 if self._selected else BORDER,
                         font=("Consolas", 9), anchor="w")

    def _rr(self, x1, y1, x2, y2, r, fill):
        if r == 0:
            self.create_rectangle(x1, y1, x2, y2, fill=fill, outline=fill)
            return
        for args in [
            (x1, y1, x1+2*r, y1+2*r, 90,  90),
            (x2-2*r, y1, x2, y1+2*r, 0,   90),
            (x1, y2-2*r, x1+2*r, y2, 180, 90),
            (x2-2*r, y2-2*r, x2, y2, 270, 90),
        ]:
            self.create_arc(*args[:4], start=args[4], extent=args[5],
                            fill=fill, outline=fill)
        self.create_rectangle(x1+r, y1, x2-r, y2, fill=fill, outline=fill)
        self.create_rectangle(x1, y1+r, x2, y2-r, fill=fill, outline=fill)

    @staticmethod
    def _tint(hex_color, factor=0.12):
        r = min(255, int(int(hex_color[1:3], 16) * factor + 18))
        g = min(255, int(int(hex_color[3:5], 16) * factor + 18))
        b = min(255, int(int(hex_color[5:7], 16) * factor + 18))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _click(self, e):
        # 수정 버튼 영역
        if self._edit_box and self._edit_box[0] <= e.x <= self._edit_box[1]:
            self._on_edit()
            return
        # 체크박스 또는 카드 본문 → 선택 토글
        self._selected = not self._selected
        self._draw()

    def _motion(self, e):
        self.configure(cursor="hand2")


# ══════════════════════════════════════════ 진행률 게이지 ════════════════════

class _ProgressGauge(tk.Canvas):
    """배치 실행 진행률 게이지 — 배치 버튼 대체."""
    H = 66
    R = 10

    def __init__(self, parent, **kw):
        super().__init__(parent, height=self.H, bg=BG,
                         highlightthickness=0, bd=0, **kw)
        self._pct    = 0.0
        self._action = "준비 중..."
        self._done   = 0
        self._total  = 0
        self._eta    = "예상 소요시간 계산 중..."
        self._blink  = False
        self.bind("<Configure>", self._draw)

    def refresh(self, pct: float, action: str, done: int, total: int,
                eta: str, blink: bool):
        self._pct    = max(0.0, min(1.0, pct))
        self._action = action
        self._done   = done
        self._total  = total
        self._eta    = eta
        self._blink  = blink
        self._draw()

    def _draw(self, _=None):
        self.delete("all")
        w, h, r = self.winfo_width(), self.winfo_height(), self.R
        if w < 4:
            return

        # 배경
        self._rr(0, 0, w, h, r, "#0a1628")

        # 진행률 채움 (왼쪽 라운드, 오른쪽 flat)
        fw = max(0, int(w * self._pct))
        if fw > 0:
            fc = "#1d4ed8" if self._blink else "#163179"
            if fw >= w:
                self._rr(0, 0, w, h, r, fc)
            else:
                self._rr_left(0, 0, fw, h, r, fc)

        # 깜박 점
        dot_c = "#22c55e" if self._blink else "#166534"
        self.create_oval(12, h//2-5, 22, h//2+5,
                         fill=dot_c, outline=dot_c)

        # 라인 1: 현재 작업 + 카운트
        if self._total > 0:
            cnt = f"    {self._done:02d}/{self._total:02d} 건...총"
        else:
            cnt = ""
        self.create_text(30, h//2 - 10,
                         text=f"{self._action}{cnt}",
                         fill=TEXT1,
                         font=("Malgun Gothic", 11, "bold"),
                         anchor="w")

        # 라인 2: 예상 소요시간
        self.create_text(30, h//2 + 11,
                         text=self._eta,
                         fill=TEXT3,
                         font=("Malgun Gothic", 9),
                         anchor="w")

        # 퍼센트 (우측)
        pct_c = "#60a5fa" if self._blink else "#2563eb"
        self.create_text(w - 12, h//2,
                         text=f"{int(self._pct * 100)}%",
                         fill=pct_c,
                         font=("Consolas", 10, "bold"),
                         anchor="e")

    def _rr(self, x1, y1, x2, y2, r, fill):
        if x2 <= x1 or y2 <= y1:
            return
        rr = min(r, (x2-x1)//2, (y2-y1)//2)
        for args in [
            (x1, y1, x1+2*rr, y1+2*rr, 90,  90),
            (x2-2*rr, y1, x2, y1+2*rr, 0,   90),
            (x1, y2-2*rr, x1+2*rr, y2, 180, 90),
            (x2-2*rr, y2-2*rr, x2, y2, 270, 90),
        ]:
            self.create_arc(*args[:4], start=args[4], extent=args[5],
                            fill=fill, outline=fill)
        self.create_rectangle(x1+rr, y1, x2-rr, y2, fill=fill, outline=fill)
        self.create_rectangle(x1, y1+rr, x2, y2-rr, fill=fill, outline=fill)

    def _rr_left(self, x1, y1, x2, y2, r, fill):
        """왼쪽만 라운드, 오른쪽 flat."""
        if x2 <= x1 or y2 <= y1:
            return
        rr = min(r, (x2-x1)//2, (y2-y1)//2)
        self.create_arc(x1, y1, x1+2*rr, y1+2*rr,
                        start=90, extent=90, fill=fill, outline=fill)
        self.create_arc(x1, y2-2*rr, x1+2*rr, y2,
                        start=180, extent=90, fill=fill, outline=fill)
        self.create_rectangle(x1+rr, y1, x2, y2, fill=fill, outline=fill)
        self.create_rectangle(x1, y1+rr, x1+rr, y2-rr, fill=fill, outline=fill)


# ══════════════════════════════════════════ 다이얼로그 ═══════════════════════

class _BaseDialog(tk.Toplevel):
    def __init__(self, parent, title, w=380, h=280):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=SURFACE)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2 - w // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - h // 2
        self.geometry(f"{w}x{h}+{px}+{py}")

    def _lbl(self, parent, text, size=11, weight="normal", color=TEXT2):
        return tk.Label(parent, text=text,
                        font=("Malgun Gothic", size, weight),
                        bg=SURFACE, fg=color)

    def _entry(self, parent, show=""):
        return tk.Entry(parent, show=show,
                        font=("Malgun Gothic", 12),
                        bg=CARD, fg=TEXT1, insertbackground=TEXT1,
                        relief="flat",
                        highlightthickness=1,
                        highlightbackground=BORDER,
                        highlightcolor=GREEN)

    def _btn(self, parent, text, bg, fg, cmd):
        return tk.Button(parent, text=text, command=cmd,
                         bg=bg, fg=fg,
                         font=("Malgun Gothic", 11, "bold"),
                         relief="flat", cursor="hand2",
                         padx=18, pady=9,
                         activebackground=bg, activeforeground=fg)


class EditAccountDialog(_BaseDialog):
    def __init__(self, parent, acct, on_save):
        super().__init__(parent, f"{acct['tag']}  {acct['label']}  수정",
                         w=390, h=300)
        self._acct    = acct
        self._on_save = on_save
        self._pw_vis  = False
        self._build()

    def _build(self):
        tk.Frame(self, bg=self._acct["color"], width=4).place(
            x=0, y=0, relheight=1)
        f = tk.Frame(self, bg=SURFACE)
        f.pack(fill="both", expand=True, padx=26, pady=22)

        self._lbl(f, "이메일", weight="bold", color=TEXT1).pack(anchor="w")
        self._em = self._entry(f)
        self._em.insert(0, self._acct["email"])
        self._em.pack(fill="x", pady=(4, 14))

        h = tk.Frame(f, bg=SURFACE)
        h.pack(fill="x")
        self._lbl(h, "비밀번호", weight="bold", color=TEXT1).pack(side="left")
        self._sw = tk.Label(h, text="[표시]", cursor="hand2",
                            font=("Consolas", 10), bg=SURFACE, fg=TEXT3)
        self._sw.pack(side="right")
        self._sw.bind("<Button-1>", self._tog)

        self._pw = self._entry(f, show="*")
        env_data = _parse_env(_DIR / self._acct["file"])
        self._pw.insert(0, _decrypt_password(
            env_data.get("CRAIGSLIST_PASSWORD", "")))
        self._pw.pack(fill="x", pady=(4, 18))

        r = tk.Frame(f, bg=SURFACE)
        r.pack(fill="x")
        self._btn(r, "저장", GREEN, BG, self._save).pack(side="left", padx=(0, 10))
        self._btn(r, "취소", CARD,  TEXT2, self.destroy).pack(side="left")

    def _tog(self, _=None):
        self._pw_vis = not self._pw_vis
        self._pw.configure(show="" if self._pw_vis else "*")
        self._sw.configure(text="[숨김]" if self._pw_vis else "[표시]")

    def _save(self):
        email = self._em.get().strip()
        plain = self._pw.get()
        if not email:
            messagebox.showwarning("입력 오류", "이메일을 입력하세요.", parent=self)
            return
        updates = {"CRAIGSLIST_EMAIL": email}
        if plain:
            try:
                updates["CRAIGSLIST_PASSWORD"] = _encrypt_password(plain)
            except Exception as e:
                messagebox.showerror("암호화 오류",
                    f"비밀번호를 암호화할 수 없어 저장을 중단합니다.\n\n{e}", parent=self)
                return
        _write_env(_DIR / self._acct["file"], updates)
        _save_integrity()   # 변경 후 해시 갱신
        self._on_save(email)
        self.destroy()


class AddAccountDialog(_BaseDialog):
    def __init__(self, parent, on_added):
        super().__init__(parent, "계정 추가", w=390, h=310)
        self._on_added = on_added
        self._pw_vis   = False
        self._build()

    def _build(self):
        f = tk.Frame(self, bg=SURFACE)
        f.pack(fill="both", expand=True, padx=26, pady=22)
        self._lbl(f, "새 계정 추가", size=13, weight="bold",
                  color=TEXT1).pack(anchor="w", pady=(0, 14))
        self._lbl(f, "이메일", weight="bold", color=TEXT1).pack(anchor="w")
        self._em = self._entry(f)
        self._em.pack(fill="x", pady=(4, 12))

        h = tk.Frame(f, bg=SURFACE)
        h.pack(fill="x")
        self._lbl(h, "비밀번호", weight="bold", color=TEXT1).pack(side="left")
        self._sw = tk.Label(h, text="[표시]", cursor="hand2",
                            font=("Consolas", 10), bg=SURFACE, fg=TEXT3)
        self._sw.pack(side="right")
        self._sw.bind("<Button-1>", self._tog)

        self._pw = self._entry(f, show="*")
        self._pw.pack(fill="x", pady=(4, 16))

        r = tk.Frame(f, bg=SURFACE)
        r.pack(fill="x")
        self._btn(r, "추가", GREEN, BG, self._add).pack(side="left", padx=(0, 10))
        self._btn(r, "취소", CARD,  TEXT2, self.destroy).pack(side="left")

    def _tog(self, _=None):
        self._pw_vis = not self._pw_vis
        self._pw.configure(show="" if self._pw_vis else "*")
        self._sw.configure(text="[숨김]" if self._pw_vis else "[표시]")

    def _add(self):
        email = self._em.get().strip()
        plain = self._pw.get()
        if not email or not plain:
            messagebox.showwarning("입력 오류", "이메일과 비밀번호를 모두 입력하세요.",
                                   parent=self)
            return
        try:
            enc_pw = _encrypt_password(plain)
        except Exception as e:
            messagebox.showerror("암호화 오류",
                f"비밀번호를 암호화할 수 없어 추가를 중단합니다.\n\n{e}", parent=self)
            return
        idx = 1
        while (_DIR / f"account{idx}.env").exists():
            idx += 1
            if idx > 20:
                messagebox.showerror("오류", "슬롯이 가득 찼습니다.", parent=self)
                return
        env_path = _DIR / f"account{idx}.env"
        env_path.write_text(
            f"# Account {idx} — {email.split('@')[0]}\n"
            f"CRAIGSLIST_EMAIL={email}\n"
            f"CRAIGSLIST_PASSWORD={enc_pw}\n"
            f"CRAIGSLIST_CITY=Seoul\nACCOUNT_ID=account{idx}\n",
            encoding="utf-8")
        _save_integrity()
        self._on_added(f"account{idx}", email)
        self.destroy()


class ManageAccountsDialog(_BaseDialog):
    def __init__(self, parent, accounts, on_changed):
        super().__init__(parent, "계정 관리", w=430, h=380)
        self._accounts   = accounts
        self._on_changed = on_changed
        self._build()

    def _build(self):
        p = 18
        tk.Label(self, text="등록된 계정 목록",
                 font=("Malgun Gothic", 13, "bold"),
                 bg=SURFACE, fg=TEXT1).pack(anchor="w", padx=p, pady=(p, 10))
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=p)

        lf = tk.Frame(self, bg=SURFACE)
        lf.pack(fill="both", expand=True, padx=p, pady=10)

        for acct in self._accounts:
            row = tk.Frame(lf, bg=CARD, pady=8)
            row.pack(fill="x", pady=4)
            tk.Label(row, text="  o  ", font=("Consolas", 13),
                     bg=CARD, fg=acct["color"]).pack(side="left")
            info = tk.Frame(row, bg=CARD)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=acct["label"],
                     font=("Malgun Gothic", 11, "bold"),
                     bg=CARD, fg=TEXT1, anchor="w").pack(anchor="w")
            tk.Label(info, text=acct["email"] or "(이메일 없음)",
                     font=("Consolas", 10), bg=CARD, fg=TEXT3,
                     anchor="w").pack(anchor="w")

            def _del(a=acct):
                if messagebox.askyesno("삭제", f"{a['label']} 계정을 삭제할까요?",
                                       parent=self):
                    ep = _DIR / a["file"]
                    if ep.exists():
                        ep.rename(ep.with_suffix(".env.bak"))
                    self._on_changed()
                    self.destroy()
            tk.Button(row, text="삭제", command=_del,
                      bg=RED_BG, fg=RED_FG,
                      font=("Malgun Gothic", 10),
                      relief="flat", cursor="hand2", padx=10,
                      ).pack(side="right", padx=12)

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=p)
        self._btn(self, "닫기", CARD, TEXT2, self.destroy).pack(
            anchor="e", padx=p, pady=p)


# ══════════════════════════════════════════ 메인 보드 ════════════════════════

# python.exe 경로 (stdout PIPE 캡처용 — pythonw는 stdout 버림)
_PYTHON_EXE = str(Path(sys.executable).parent / "python.exe")
if not Path(_PYTHON_EXE).exists():
    _PYTHON_EXE = sys.executable


class AdminBoard:
    LW  = 420   # 왼쪽 패널 고정 폭
    RW  = 380   # 오른쪽 로그 패널 폭
    PAD = 20

    @property
    def W(self):
        return self.LW + 1 + self.RW   # 801

    def __init__(self):
        # 숨겨진 펌프 (작업표시줄 "tk" 방지)
        self._pump = tk.Tk()
        self._pump.withdraw()
        self._pump.wm_attributes("-toolwindow", True)

        self.root = tk.Toplevel(self._pump)
        self.root.title("Bridge RPA Admin")
        self.root.configure(bg=BG)
        self.root.geometry(f"{self.W}x760")
        self.root.resizable(True, True)
        self.root.minsize(300, 60)
        self.root.wm_attributes("-toolwindow", True)

        _ico = _DIR / "rpa_icon.ico"
        if _ico.exists():
            try: self.root.iconbitmap(str(_ico))
            except Exception: pass

        self._accounts    = _load_accounts()
        self._cards: list[AccountCard] = []
        self._proc        = None
        self._running     = False
        self._blink       = False
        self._log_widget  = None
        self._batch_running = False
        self._log_queue   = queue.Queue()   # 워커→메인 로그 큐 (응답없음 방지)

        # ── 게이지 상태 ─────────────────────────────────────────────────────
        self._gauge_done    = 0
        self._gauge_total   = 0
        self._gauge_action  = "준비 중..."
        self._gauge_start   = 0.0
        self._gauge_blink   = False
        self._gauge: "_ProgressGauge | None" = None
        self._compact_mode  = False
        self._idle_drawn    = False

        self._build()
        self.root.bind("<Configure>", self._on_resize)
        self.root.after(200, self._tick)
        self.root.after(100, self._flush_log_queue)   # 로그 배치 처리 시작
        self.root.after(400, self._save_hwnd)
        self.root.after(800, self._integrity_check_startup)
        self.root.protocol("WM_DELETE_WINDOW", self._on_exit)

    # ── 빌드 ─────────────────────────────────────────────────────────────────

    def _build(self):
        p = self.PAD

        # ── 최소화 컴팩트 바 (기본 숨김) ─────────────────
        self._compact_bar = tk.Frame(self.root, bg=SURFACE, height=44)
        self._cb_dot = tk.Label(self._compact_bar, text="●",
                                font=("Consolas", 12), bg=SURFACE, fg=TEXT3)
        self._cb_dot.pack(side="left", padx=(16, 8))
        self._cb_lbl = tk.Label(self._compact_bar,
                                text="대기 중",
                                font=("Malgun Gothic", 10), bg=SURFACE, fg=TEXT2,
                                anchor="w")
        self._cb_lbl.pack(side="left", fill="x", expand=True)
        RoundCanvas(self._compact_bar, h=30, width=92, fill=RED_D,
                    text="즉시 중단", text_color="#ffffff",
                    command=self._on_stop,
                    font=("Malgun Gothic", 10, "bold"),
                    ).pack(side="right", padx=10, pady=7)

        # ─────────────────────────────────────────────────────────────
        # ❶  헤더 (슬림 + 타이틀 + 상태 칩 + 도구 버튼)
        # ─────────────────────────────────────────────────────────────
        self._hdr_frame = tk.Frame(self.root, bg=SURFACE, height=58)
        self._hdr_frame.pack(fill="x")
        self._hdr_frame.pack_propagate(False)
        hdr = self._hdr_frame

        # 좌측: 브랜드 마크 + 타이틀
        brand = tk.Frame(hdr, bg=SURFACE)
        brand.pack(side="left", padx=(p, 0), pady=12)
        tk.Label(brand, text="◆", font=("Consolas", 16, "bold"),
                 bg=SURFACE, fg=ACCENT).pack(side="left", padx=(0, 8))
        tk.Label(brand, text="BRIDGE", font=("Malgun Gothic", 14, "bold"),
                 bg=SURFACE, fg=TEXT1).pack(side="left")
        tk.Label(brand, text="RPA Admin", font=("Malgun Gothic", 11),
                 bg=SURFACE, fg=TEXT3).pack(side="left", padx=(8, 0))

        # 우측: 도구 버튼 그룹
        tools = tk.Frame(hdr, bg=SURFACE)
        tools.pack(side="right", padx=(0, p), pady=10)

        def _tool_btn(parent, text, cmd, fg=TEXT2, hover_bg=CARD_HI):
            b = tk.Label(parent, text=text, bg=SURFACE, fg=fg,
                         font=("Malgun Gothic", 10),
                         padx=12, pady=8, cursor="hand2")
            b.bind("<Button-1>", lambda e: cmd())
            b.bind("<Enter>", lambda e: b.configure(bg=hover_bg, fg=TEXT1))
            b.bind("<Leave>", lambda e: b.configure(bg=SURFACE, fg=fg))
            return b

        _tool_btn(tools, "✕  종료", self._on_exit, fg=RED_FG, hover_bg=RED_BG).pack(side="right", padx=(2, 0))
        _tool_btn(tools, "▼  숨기기", self._on_hide, fg=HIDE_FG).pack(side="right", padx=(2, 0))

        # ─────────────────────────────────────────────────────────────
        # ❷  서브 헤더: 상태 칩(좌) + 투명도 슬라이더(우)
        # ─────────────────────────────────────────────────────────────
        sub = tk.Frame(self.root, bg=BG, height=44)
        sub.pack(fill="x")
        sub.pack_propagate(False)
        # 헤더-서브 사이 미세 라인
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # 상태 칩 (둥근 박스 형태)
        chip = tk.Frame(sub, bg=CARD, highlightbackground=BORDER,
                        highlightthickness=1)
        chip.pack(side="left", padx=p, pady=8)
        self._dot = tk.Label(chip, text="●", font=("Consolas", 11),
                             bg=CARD, fg=TEXT3)
        self._dot.pack(side="left", padx=(10, 6), pady=4)
        self._st_lbl = tk.Label(chip, text="대기 중 — 작업이 없습니다",
                                font=("Malgun Gothic", 10),
                                bg=CARD, fg=TEXT2)
        self._st_lbl.pack(side="left", padx=(0, 12), pady=4)

        # 투명도 — 숨기기 아래 (서브 헤더 우측)
        _alpha_prefs_file = LOGS_DIR / ".admin_prefs.json"
        def _load_alpha():
            try:
                import json as _j
                return float(_j.loads(_alpha_prefs_file.read_text()).get("alpha", 1.0))
            except Exception:
                return 1.0
        def _save_alpha(v):
            try:
                import json as _j
                _alpha_prefs_file.parent.mkdir(exist_ok=True)
                _alpha_prefs_file.write_text(_j.dumps({"alpha": float(v)}))
            except Exception:
                pass

        _av = tk.DoubleVar(value=_load_alpha())
        self.root.attributes("-alpha", _av.get())

        def _on_alpha_change(val):
            try:
                self.root.attributes("-alpha", float(val))
                _save_alpha(val)
            except Exception:
                pass

        alpha_box = tk.Frame(sub, bg=BG)
        alpha_box.pack(side="right", padx=p, pady=8)
        tk.Label(alpha_box, text="투명도", font=("Malgun Gothic", 9),
                 bg=BG, fg=TEXT3).pack(side="left", padx=(0, 6))
        tk.Scale(alpha_box, from_=0.3, to=1.0, resolution=0.05,
                 orient="horizontal", variable=_av, command=_on_alpha_change,
                 length=120, bg=BG, fg=TEXT2, highlightthickness=0,
                 sliderrelief="flat", bd=0, troughcolor=BORDER, showvalue=False,
                 ).pack(side="left")

        # ─────────────────────────────────────────────────────────────
        # ❸  본문: 좌측 작업 패널 + 우측 로그 패널
        # ─────────────────────────────────────────────────────────────
        self._body_frame = tk.Frame(self.root, bg=BG)
        self._body_frame.pack(fill="both", expand=True)
        body = self._body_frame

        left = tk.Frame(body, bg=BG, width=self.LW)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self._left_panel = left

        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        right = tk.Frame(body, bg="#0a0d13")
        right.pack(side="left", fill="both", expand=True)
        self._build_log_panel(right)

        # ─────────────────────────────────────────────────────────────
        # ❹  계정 선택 섹션
        # ─────────────────────────────────────────────────────────────
        sh = tk.Frame(left, bg=BG)
        sh.pack(fill="x", padx=p, pady=(14, 8))
        tk.Label(sh, text="계정 선택",
                 font=("Malgun Gothic", 11, "bold"),
                 bg=BG, fg=TEXT1).pack(side="left")
        tk.Label(sh, text=f"{len(self._accounts)}개",
                 font=("Malgun Gothic", 9),
                 bg=BG, fg=TEXT3).pack(side="left", padx=(8, 0))

        tf = tk.Frame(sh, bg=BG)
        tf.pack(side="right")

        def _ghost_btn(parent, text, cmd):
            b = tk.Label(parent, text=text, bg=BG, fg=TEXT2,
                         font=("Malgun Gothic", 9),
                         padx=10, pady=4, cursor="hand2",
                         highlightbackground=BORDER, highlightthickness=1)
            b.bind("<Button-1>", lambda e: cmd())
            b.bind("<Enter>", lambda e: b.configure(bg=CARD, fg=TEXT1))
            b.bind("<Leave>", lambda e: b.configure(bg=BG, fg=TEXT2))
            return b

        _ghost_btn(tf, "전체 선택", self._sel_all).pack(side="left", padx=(0, 4))
        _ghost_btn(tf, "전체 해제", self._desel_all).pack(side="left")

        # 계정 카드 리스트
        cf = tk.Frame(left, bg=BG)
        cf.pack(fill="x", padx=p)
        for i, acct in enumerate(self._accounts):
            card = AccountCard(cf, acct, on_edit=lambda i=i: self._edit(i))
            card.pack(fill="x", pady=3)
            self._cards.append(card)

        # ─────────────────────────────────────────────────────────────
        # ❺  계정 관리 + 카운트 (한 줄)
        # ─────────────────────────────────────────────────────────────
        mf = tk.Frame(left, bg=BG)
        mf.pack(fill="x", padx=p, pady=(10, 6))
        _ghost_btn(mf, "+ 계정 추가", self._on_add).pack(side="left", padx=(0, 6))
        _ghost_btn(mf, "계정 관리", self._on_manage).pack(side="left")

        self._cnt = tk.IntVar(value=10)
        tk.Label(mf, text="건",  font=("Malgun Gothic", 10), bg=BG, fg=TEXT2).pack(side="right")
        tk.Spinbox(mf, from_=1, to=30, textvariable=self._cnt,
                   width=4, font=("Malgun Gothic", 11, "bold"),
                   bg=CARD, fg=TEXT1, buttonbackground=BORDER,
                   relief="flat", highlightthickness=1,
                   highlightbackground=BORDER,
                   ).pack(side="right", padx=(6, 8))
        tk.Label(mf, text="계정당", font=("Malgun Gothic", 10), bg=BG, fg=TEXT2).pack(side="right", padx=(0, 2))

        # 메시지
        self._msg_lbl = tk.Label(left, text="", font=("Malgun Gothic", 9),
                                 bg=BG, fg=TEXT3)
        self._msg_lbl.pack(pady=(0, 4))

        GAP = 8
        SBW = (self.LW - p * 2 - 24 - GAP) // 2

        # ─────────────────────────────────────────────────────────────
        # ❻  ① 단일계정 모드 카드
        # ─────────────────────────────────────────────────────────────
        single_card = tk.Frame(left, bg=CARD, highlightbackground=BORDER,
                               highlightthickness=1)
        single_card.pack(fill="x", padx=p, pady=(8, 6))
        self._single_card = single_card

        # 카드 헤더
        sh1 = tk.Frame(single_card, bg=CARD)
        sh1.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(sh1, text="●", font=("Consolas", 10),
                 bg=CARD, fg=GREEN).pack(side="left", padx=(0, 6))
        tk.Label(sh1, text="단일계정 모드",
                 font=("Malgun Gothic", 10, "bold"),
                 bg=CARD, fg=TEXT1).pack(side="left")
        tk.Label(sh1, text="선택 계정으로 즉시 게시",
                 font=("Malgun Gothic", 9),
                 bg=CARD, fg=TEXT3).pack(side="left", padx=(8, 0))

        # 액션 버튼 행
        single_btn_row = tk.Frame(single_card, bg=CARD)
        single_btn_row.pack(fill="x", padx=12, pady=(2, 12))
        self._single_btn_row = single_btn_row

        self._start_btn = RoundCanvas(
            single_btn_row, h=46, width=SBW, fill=GREEN,
            text="단일계정 포스팅하기", text_color="#ffffff",
            command=self._on_start,
            font=("Malgun Gothic", 11, "bold"),
        )
        self._start_btn.pack(side="left", padx=(0, GAP))

        self._stop_btn = RoundCanvas(
            single_btn_row, h=46, width=SBW, fill=RED_D,
            text="즉시 중단", text_color="#ffffff",
            command=self._on_stop,
            font=("Malgun Gothic", 11, "bold"),
        )
        self._stop_btn.pack(side="left")

        # 단일계정 게이지 (실행 중에만 표시)
        self._start_gauge = _ProgressGauge(single_card)

        # ─────────────────────────────────────────────────────────────
        # ❼  ② 계정스와이프 모드 카드
        # ─────────────────────────────────────────────────────────────
        batch_card = tk.Frame(left, bg=CARD, highlightbackground=BORDER,
                              highlightthickness=1)
        batch_card.pack(fill="x", padx=p, pady=(2, 8))
        self._batch_card = batch_card

        # 카드 헤더
        bh1 = tk.Frame(batch_card, bg=CARD)
        bh1.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(bh1, text="●", font=("Consolas", 10),
                 bg=CARD, fg=BLUE).pack(side="left", padx=(0, 6))
        tk.Label(bh1, text="계정스와이프 모드",
                 font=("Malgun Gothic", 10, "bold"),
                 bg=CARD, fg=TEXT1).pack(side="left")
        tk.Label(bh1, text="배치 — 계정 순환 + 휴식",
                 font=("Malgun Gothic", 9),
                 bg=CARD, fg=TEXT3).pack(side="left", padx=(8, 0))

        # 스피너 행
        sf = tk.Frame(batch_card, bg=CARD)
        sf.pack(fill="x", padx=12, pady=(4, 8))

        def _spin(parent, var, lo=1, hi=30, w=3):
            return tk.Spinbox(parent, from_=lo, to=hi, textvariable=var,
                              width=w, font=("Malgun Gothic", 10, "bold"),
                              bg=DIM, fg=TEXT1, buttonbackground=BORDER,
                              relief="flat", highlightthickness=1,
                              highlightbackground=BORDER)

        def _lbl(parent, text):
            tk.Label(parent, text=text, font=("Malgun Gothic", 9),
                     bg=CARD, fg=TEXT2).pack(side="left", padx=(3, 3))

        self._b_cnt1  = tk.IntVar(value=3)
        self._b_rest  = tk.IntVar(value=5)
        self._b_cnt2  = tk.IntVar(value=2)
        self._b_reps  = tk.IntVar(value=2)

        _spin(sf, self._b_cnt1).pack(side="left")
        _lbl(sf, "개 →")
        _spin(sf, self._b_rest, lo=1, hi=60).pack(side="left")
        _lbl(sf, "분 휴식 →")
        _spin(sf, self._b_cnt2).pack(side="left")
        _lbl(sf, "개  ×")
        _spin(sf, self._b_reps, lo=1, hi=20, w=2).pack(side="left")
        _lbl(sf, "회")

        # 계정스와이프 액션 버튼
        batch_btn_row = tk.Frame(batch_card, bg=CARD)
        batch_btn_row.pack(fill="x", padx=12, pady=(0, 12))
        self._batch_btn_row = batch_btn_row

        BBW = (self.LW - p * 2 - 24 - GAP) // 2

        self._batch_btn = RoundCanvas(
            batch_btn_row, h=42, width=BBW, fill=BLUE,
            text="계정스와이프 포스팅시작", text_color="#ffffff",
            command=self._on_batch_start,
            font=("Malgun Gothic", 10, "bold"),
        )
        self._batch_btn.pack(side="left", padx=(0, GAP))

        self._batch_stop_btn = RoundCanvas(
            batch_btn_row, h=42, width=BBW, fill=RED_D,
            text="즉시 중단", text_color="#ffffff",
            command=self._on_stop,
            font=("Malgun Gothic", 10, "bold"),
        )
        self._batch_stop_btn.pack(side="left")

        # 배치 게이지 (실행 중에만 표시)
        self._gauge = _ProgressGauge(batch_card)

    def _build_log_panel(self, parent):
        """오른쪽 실시간 로그 패널 (모던 다크)."""
        LOG_BG = "#0a0d13"

        # 로그 헤더 (서브헤더와 동일 높이 정렬)
        lh = tk.Frame(parent, bg=SURFACE, height=58)
        lh.pack(fill="x")
        lh.pack_propagate(False)
        # 헤더 좌측 라벨
        lhead = tk.Frame(lh, bg=SURFACE)
        lhead.pack(side="left", padx=16, pady=14)
        tk.Label(lhead, text="▤", font=("Consolas", 12),
                 bg=SURFACE, fg=ACCENT).pack(side="left", padx=(0, 8))
        tk.Label(lhead, text="실시간 로그",
                 font=("Malgun Gothic", 11, "bold"),
                 bg=SURFACE, fg=TEXT1).pack(side="left")

        # 우측 지우기 버튼 (고스트 스타일)
        clear_btn = tk.Label(lh, text="지우기", bg=SURFACE, fg=TEXT2,
                             font=("Malgun Gothic", 9),
                             padx=10, pady=4, cursor="hand2",
                             highlightbackground=BORDER, highlightthickness=1)
        clear_btn.pack(side="right", padx=14, pady=14)
        clear_btn.bind("<Button-1>", lambda e: self._clear_log())
        clear_btn.bind("<Enter>", lambda e: clear_btn.configure(bg=CARD, fg=TEXT1))
        clear_btn.bind("<Leave>", lambda e: clear_btn.configure(bg=SURFACE, fg=TEXT2))

        # 헤더 아래 미세 라인
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")

        # 로그 텍스트 + 스크롤바
        frame = tk.Frame(parent, bg=LOG_BG)
        frame.pack(fill="both", expand=True, padx=0, pady=0)

        sb = tk.Scrollbar(frame, bg=BORDER, troughcolor=LOG_BG,
                          relief="flat", width=8)
        sb.pack(side="right", fill="y")

        self._log_widget = tk.Text(
            frame,
            bg=LOG_BG, fg="#cccccc",
            font=("Consolas", 9),
            relief="flat",
            bd=0,
            padx=10, pady=8,
            wrap="word",
            state="disabled",
            yscrollcommand=sb.set,
            selectbackground="#333355",
            insertbackground=LOG_BG,
            spacing1=2,
        )
        self._log_widget.pack(side="left", fill="both", expand=True)
        sb.config(command=self._log_widget.yview)

        # 색상 태그
        self._log_widget.tag_config("success", foreground="#22c55e")
        self._log_widget.tag_config("error",   foreground="#f87171")
        self._log_widget.tag_config("warn",    foreground="#fbbf24")
        self._log_widget.tag_config("info",    foreground="#60a5fa")
        self._log_widget.tag_config("dim",     foreground="#555566")
        self._log_widget.tag_config("normal",  foreground="#cccccc")
        self._log_widget.tag_config("ts",      foreground="#444455")

        self._append_log("--- BRIDGE RPA 로그 시작 ---", "dim")

    # ── 내부 유틸 ─────────────────────────────────────────────────────────────

    def _append_log(self, line: str, force_tag: str = ""):
        """로그 한 줄 추가 (메인 스레드에서 호출)."""
        if not self._log_widget:
            return
        from datetime import datetime as _dt
        ts  = _dt.now().strftime("%H:%M:%S")

        # 자동 색상 분류
        if force_tag:
            tag = force_tag
        elif any(k in line for k in ("완료", "성공", "✅", "Publish")):
            tag = "success"
        elif any(k in line for k in ("ERROR", "오류", "실패", "Exception", "Traceback")):
            tag = "error"
        elif any(k in line for k in ("WARNING", "주의", "skip", "SKIP")):
            tag = "warn"
        elif line.startswith("  [") or line.startswith("["):
            tag = "info"
        elif line.startswith("=") or line.startswith("-"):
            tag = "dim"
        else:
            tag = "normal"

        self._log_widget.configure(state="normal")
        self._log_widget.insert("end", f"[{ts}] ", "ts")
        self._log_widget.insert("end", line + "\n", tag)
        self._log_widget.see("end")
        self._log_widget.configure(state="disabled")

    def _clear_log(self):
        if not self._log_widget:
            return
        self._log_widget.configure(state="normal")
        self._log_widget.delete("1.0", "end")
        self._log_widget.configure(state="disabled")
        self._append_log("--- 로그 지움 ---", "dim")

    def _save_hwnd(self):
        try:
            LOGS_DIR.mkdir(exist_ok=True)
            # HWND + PID 함께 저장 (재사용 HWND 오인 방지)
            ADMIN_HWND_FILE.write_text(
                f"{self.root.winfo_id()}:{os.getpid()}", encoding="utf-8")
        except Exception:
            pass

    def _integrity_check_startup(self):
        """시작 시 계정 파일 변조 검사."""
        tampered = _check_integrity()
        if tampered:
            names = "\n".join(f"  - {f}" for f in tampered)
            messagebox.showwarning(
                "파일 변조 감지",
                f"아래 계정 파일이 외부에서 변경된 것으로 감지되었습니다:\n\n{names}\n\n"
                "계속 진행하려면 확인을 누르세요. 변경 내용을 직접 검토하는 것을 권장합니다.",
                parent=self.root,
            )
            self._append_log(
                f"[SECURITY] 계정 파일 변조 감지: {', '.join(tampered)}", "error")
            _save_integrity()  # 경고 후 현재 상태로 해시 갱신

    def _on_close(self):
        ADMIN_HWND_FILE.unlink(missing_ok=True)
        self._pump.destroy()

    def _msg(self, text: str, color=TEXT3):
        self._msg_lbl.configure(text=text, fg=color)

    # ── 상태 깜박임 ───────────────────────────────────────────────────────────

    _flush_count = 0  # see("end") / 줄수 체크 빈도 조절용

    def _flush_log_queue(self):
        """200ms마다 로그 큐 드레인 — 배치 25줄로 메인스레드 부하 최소화."""
        batch: list[tuple[str, str]] = []
        try:
            while len(batch) < 25:
                batch.append(self._log_queue.get_nowait())
        except queue.Empty:
            pass

        if batch and self._log_widget:
            from datetime import datetime as _dt
            ts = _dt.now().strftime("%H:%M:%S")
            self._log_widget.configure(state="normal")
            for line, force_tag in batch:
                if force_tag:
                    tag = force_tag
                elif any(k in line for k in ("완료", "성공", "Publish")):
                    tag = "success"
                elif any(k in line for k in ("ERROR", "오류", "실패", "Exception", "Traceback")):
                    tag = "error"
                elif any(k in line for k in ("WARNING", "주의", "skip", "SKIP")):
                    tag = "warn"
                elif line.startswith("  [") or line.startswith("["):
                    tag = "info"
                elif line.startswith("=") or line.startswith("-"):
                    tag = "dim"
                else:
                    tag = "normal"
                self._log_widget.insert("end", f"[{ts}] ", "ts")
                self._log_widget.insert("end", line + "\n", tag)

            self.__class__._flush_count += 1

            # 10번째 flush마다 줄수 초과 정리 (index() 호출 빈도 줄임)
            if self._flush_count % 10 == 0:
                try:
                    total_lines = int(self._log_widget.index("end-1c").split(".")[0])
                    if total_lines > 1500:
                        self._log_widget.delete("1.0", f"{total_lines - 1000}.0")
                except Exception:
                    pass

            self._log_widget.see("end")
            self._log_widget.configure(state="disabled")

        self.root.after(200, self._flush_log_queue)

    def _tick(self):
        # 단일/배치 어느 쪽이든 실행 중이면 busy
        busy = self._running or self._batch_running
        if busy:
            self._idle_drawn = False
            self._blink = not self._blink
            # 모드별 색상: 배치=BLUE, 단일=GREEN
            on_color  = BLUE  if self._batch_running else GREEN
            off_color = BLUE_D if self._batch_running else GREEN_D
            dot_fg = on_color if self._blink else off_color
            action = self._gauge_action if self._gauge_action and self._gauge_action != "준비 중..." else "작업 진행 중"
            done, total = self._gauge_done, self._gauge_total
            # 게이지 막대 (12칸 유니코드 블록)
            BARS = 12
            if total > 0:
                filled = max(0, min(BARS, int(BARS * done / total + 0.5)))
                pct    = int(done / total * 100)
                gauge  = "▰" * filled + "▱" * (BARS - filled)
                meter  = f"  {gauge}  {done}/{total} ({pct}%)"
            else:
                # total 미정 — 바운싱 점 표시 (살아있음 표시)
                pos = int(_time.time() * 2) % BARS
                gauge = "▱" * pos + "▰" + "▱" * (BARS - pos - 1)
                meter = f"  {gauge}"
            text = f"{action}{meter}"
            self._dot.configure(fg=dot_fg)
            self._st_lbl.configure(text=text, fg=TEXT1)
            # 컴팩트 바 동기화
            self._cb_dot.configure(fg=dot_fg)
            self._cb_lbl.configure(text=text, fg=TEXT1)
        else:
            if not self._idle_drawn:
                self._dot.configure(fg=TEXT3)
                self._st_lbl.configure(text="대기 중 — 작업이 없습니다", fg=TEXT2)
                self._start_btn.update_text("단일계정 포스팅하기")
                self._start_btn.update_fill(GREEN, "#ffffff")
                self._cb_dot.configure(fg=TEXT3)
                self._cb_lbl.configure(text="대기 중", fg=TEXT2)
                self._idle_drawn = True
        # 깜박임 부드럽게 — 600ms
        self.root.after(600, self._tick)

    # ── 일반 실행 게이지 제어 ────────────────────────────────────────────────

    def _show_start_gauge(self):
        """단일계정 카드 내부에 게이지 표시 (시작/즉시중단 버튼은 유지)."""
        if self._start_gauge:
            self._start_gauge.pack(in_=self._single_card, fill="x",
                                   padx=12, pady=(0, 12))
        # 시작 버튼만 비활성화, 라벨로 진행 표시
        try:
            self._start_btn.set_enabled(False)
            self._start_btn.update_text("실행 중...")
        except Exception:
            pass
        self._start_gauge_tick()

    def _hide_start_gauge(self):
        """일반 실행 게이지 숨김 + 시작 버튼 복원."""
        if self._start_gauge:
            self._start_gauge.pack_forget()
        try:
            self._start_btn.set_enabled(True)
            self._start_btn.update_text("단일계정 포스팅하기")
        except Exception:
            pass

    def _start_gauge_tick(self):
        """600ms마다 일반 실행 게이지 갱신."""
        if not self._running or not self._start_gauge:
            return
        self._gauge_blink = not self._gauge_blink

        done    = self._gauge_done
        total   = self._gauge_total
        elapsed = _time.time() - self._gauge_start if self._gauge_start else 0

        if done > 0 and elapsed > 0 and total > done:
            rate_sec = elapsed / done
            rem = rate_sec * (total - done)
            if rem >= 3600:
                eta = f"예상 소요 약 {int(rem/3600)}시간 {int((rem%3600)/60)}분 남음"
            elif rem >= 60:
                eta = f"예상 소요 약 {int(rem/60)}분 남음"
            else:
                eta = f"예상 소요 약 {int(rem)}초 남음"
        elif done == 0:
            eta = "예상 소요시간 계산 중..."
        else:
            eta = "거의 완료 중..."

        pct = done / total if total > 0 else 0.0
        self._start_gauge.refresh(
            pct, self._gauge_action, done, total, eta, self._gauge_blink)
        self.root.after(1500, self._start_gauge_tick)

    # ── 배치 게이지 제어 ──────────────────────────────────────────────────────

    def _show_gauge(self):
        """배치 카드 내부에 게이지 바 표시 (액션버튼 행은 그대로 유지 — 즉시중단 보존)."""
        if self._gauge:
            self._gauge.pack(in_=self._batch_card, fill="x",
                             padx=12, pady=(0, 12))
        # 시작 버튼만 비활성화 (실행 중 표시) — 즉시중단은 그대로 활성
        try:
            self._batch_btn.set_enabled(False)
            self._batch_btn.update_text("실행 중...")
        except Exception:
            pass
        self._gauge_tick()

    def _hide_gauge(self):
        """게이지 숨기고 시작 버튼 라벨/활성 복원."""
        if self._gauge:
            self._gauge.pack_forget()
        try:
            self._batch_btn.set_enabled(True)
            self._batch_btn.update_text("계정스와이프 포스팅시작")
        except Exception:
            pass

    def _gauge_tick(self):
        """600ms마다 게이지 갱신 (깜박 + ETA)."""
        if not self._batch_running or not self._gauge:
            return
        self._gauge_blink = not self._gauge_blink

        done  = self._gauge_done
        total = self._gauge_total
        elapsed = _time.time() - self._gauge_start if self._gauge_start else 0

        if done > 0 and elapsed > 0 and total > done:
            rate_sec = elapsed / done
            rem = rate_sec * (total - done)
            if rem >= 3600:
                eta = f"예상 소요시간 약 {int(rem/3600)}시간 {int((rem%3600)/60)}분 남음"
            elif rem >= 60:
                eta = f"예상 소요시간 약 {int(rem/60)}분 남음"
            else:
                eta = f"예상 소요시간 약 {int(rem)}초 남음"
        elif done == 0:
            eta = "예상 소요시간 계산 중..."
        else:
            eta = "거의 완료 중..."

        pct = done / total if total > 0 else 0.0
        self._gauge.refresh(
            pct, self._gauge_action, done, total, eta, self._gauge_blink)
        self.root.after(1500, self._gauge_tick)

    def _set_gauge_action(self, action: str):
        """메인 스레드에서 게이지 액션 텍스트 갱신."""
        self._gauge_action = action

    def _inc_gauge_done(self, n: int):
        """게이지 완료 카운트 증가 (메인 스레드)."""
        self._gauge_done = min(self._gauge_done + n, self._gauge_total)

    def _detect_action(self, line: str) -> str | None:
        """로그 줄에서 현재 액션 감지."""
        # [N/M] Job. 패턴 — 가장 구체적
        m = _re.search(r'\[(\d+)/(\d+)\]\s+Job\.', line)
        if m:
            return f"Job {m.group(1)}/{m.group(2)} 처리 중"
        for kw, action in _ACTION_KEYWORDS:
            if kw in line:
                return action
        return None

    # ── 계정 이벤트 ──────────────────────────────────────────────────────────

    def _sel_all(self):
        for c in self._cards: c.select()

    def _desel_all(self):
        for c in self._cards: c.deselect()

    def _edit(self, idx: int):
        acct = self._accounts[idx]
        def _saved(email: str):
            label = email.split("@")[0]
            self._accounts[idx]["email"] = email
            self._accounts[idx]["label"] = label
            self._cards[idx].update_label(label)
        EditAccountDialog(self.root, acct, on_save=_saved)

    def _on_add(self):
        def _added(acct_id, email):
            messagebox.showinfo("완료", f"계정 추가 완료\n{email}", parent=self.root)
        AddAccountDialog(self.root, on_added=_added)

    def _on_manage(self):
        ManageAccountsDialog(self.root, self._accounts, on_changed=lambda: None)

    # ── 실행 이벤트 ──────────────────────────────────────────────────────────

    def _on_start(self):
        if self._running:
            return

        selected = [self._accounts[i] for i, c in enumerate(self._cards) if c.selected]
        if not selected:
            self._msg("체크박스로 계정을 하나 이상 선택하세요.", RED_FG)
            return

        count = self._cnt.get()
        self._running = True
        self._start_btn.update_text("실행 중 ...")
        self._start_btn.update_fill("#4b5563", TEXT2)   # 회색으로 변경
        self._start_btn.set_enabled(False)

        # 게이지 초기화 + 표시
        self._gauge_done   = 0
        self._gauge_total  = len(selected) * count
        self._gauge_action = "시작 중..."
        self._gauge_start  = _time.time()
        self._show_start_gauge()

        def worker():
            total = len(selected)
            for i, acct in enumerate(selected, 1):
                self.root.after(0, self._msg,
                                f"[{i}/{total}]  {acct['label']} 실행 중...",
                                acct["color"])
                self.root.after(0, self._append_log,
                                f"=== [{i}/{total}] {acct['label']} ({acct['email']}) 시작 ===",
                                "info")
                try:
                    self._proc = subprocess.Popen(
                        [_PYTHON_EXE, "-X", "utf8", "-u", SCRIPT,
                         "--account", acct["id"],
                         "--limit", str(count), "--no-overlay", "--manual"],
                        cwd=str(_DIR),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        text=True, encoding="utf-8", errors="replace",
                        bufsize=1,
                    )
                except Exception as e:
                    self.root.after(0, self._append_log, f"실행 오류: {e}", "error")
                    continue

                if self._proc.pid:
                    LOGS_DIR.mkdir(exist_ok=True)
                    PID_FILE.write_text(str(self._proc.pid))

                # stdout 실시간 읽기 + 액션 감지 + 완료 건수 추적
                _last_action = ""
                for line in self._proc.stdout:
                    line = line.rstrip("\r\n")
                    if not line:
                        continue
                    self._log_queue.put((line, ""))
                    action = self._detect_action(line)
                    # 액션이 바뀔 때만 after() 호출 — 매 줄 호출 시 Tk 큐 과적으로 응답없음 발생
                    if action and action != _last_action:
                        _last_action = action
                        self.root.after(0, self._set_gauge_action, action)
                    # 게시 완료 1건 감지
                    if ("[OK] 게시 완료" in line or "게시 완료" in line or
                            '"posted"' in line or "Post successful" in line):
                        self.root.after(0, self._inc_gauge_done, 1)

                self._proc.wait()
                rc = self._proc.returncode
                self.root.after(0, self._append_log,
                                f"=== {acct['label']} 종료 (exit {rc}) ===",
                                "success" if rc == 0 else "error")
                # 비정상 종료 시 Chrome 좀비 정리
                if rc != 0:
                    self.root.after(0, self._append_log,
                                    f"  [CLEANUP] Chrome 좀비 정리 중...", "warn")
                    self._kill_chrome_orphans()
                else:
                    _time.sleep(2)

            PID_FILE.unlink(missing_ok=True)
            self._running = False
            self._proc    = None
            self.root.after(0, self._hide_start_gauge)
            self.root.after(0, self._msg, f"완료  ({total}개 계정)", GREEN)
            self.root.after(0, self._append_log,
                            f"--- 전체 완료: {total}개 계정 ---", "success")
            self.root.after(0, self._start_btn.update_text, "단일계정 포스팅하기")
            self.root.after(0, self._start_btn.update_fill, GREEN, "#ffffff")
            self.root.after(0, self._start_btn.set_enabled, True)
            self.root.after(0, self._show_post_run_dialog, total)

        threading.Thread(target=worker, daemon=True).start()

    def _on_stop(self):
        # 배치 + 일반 모두 중단
        self._batch_running = False
        self._running = False
        self._hide_gauge()
        self._hide_start_gauge()
        if self._proc:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self._proc.pid)],
                    capture_output=True, timeout=5)
            except Exception:
                pass
            self._proc = None
        _kill_rpa()
        self._running = False
        self._start_btn.update_text("단일계정 포스팅하기")
        self._start_btn.update_fill(GREEN, BG)
        self._start_btn.set_enabled(True)
        self._batch_btn.update_text("계정스와이프 포스팅시작")
        self._batch_btn.set_enabled(True)
        self._msg("중단되었습니다.", RED_FG)

    def _on_batch_start(self):
        if self._running or self._batch_running:
            return

        selected = [self._accounts[i] for i, c in enumerate(self._cards) if c.selected]
        if not selected:
            self._msg("체크박스로 계정을 하나 이상 선택하세요.", RED_FG)
            return

        cnt1  = self._b_cnt1.get()
        rest  = self._b_rest.get()
        cnt2  = self._b_cnt2.get()
        reps  = self._b_reps.get()

        self._batch_running = True
        self._batch_btn.set_enabled(False)
        self._start_btn.set_enabled(False)

        # 게이지 초기화 + 표시
        self._gauge_done   = 0
        self._gauge_total  = (cnt1 + cnt2) * reps * len(selected)
        self._gauge_action = "배치 시작 중..."
        self._gauge_start  = _time.time()
        self._show_gauge()

        self._append_log(
            f"=== 배치 시작: {len(selected)}계정 × [{cnt1}건 → {rest}분 → {cnt2}건] × {reps}회 ===",
            "info")

        def _batch_worker():
            total_accts = len(selected)
            for rep in range(1, reps + 1):
                if not self._batch_running:
                    break
                # ── 라운드 A ──────────────────────────────
                self.root.after(0, self._append_log,
                                f"--- [{rep}/{reps}회] 라운드A ({cnt1}건/계정) 시작 ---", "info")
                self.root.after(0, self._msg,
                                f"배치 {rep}/{reps}회 — 라운드A", "#60a5fa")
                self.root.after(0, self._set_gauge_action,
                                f"{rep}/{reps}회 라운드A 시작")
                for i, acct in enumerate(selected, 1):
                    if not self._batch_running:
                        break
                    self.root.after(0, self._append_log,
                                    f"=== A [{i}/{total_accts}] {acct['label']} ({cnt1}건) ===", "info")
                    self._run_single(acct, cnt1)
                if not self._batch_running:
                    break

                # ── 라운드 간 휴식 ────────────────────────
                self.root.after(0, self._append_log,
                                f"--- [{rep}/{reps}회] {rest}분 휴식 시작 ---", "dim")
                rest_sec = rest * 60
                for s in range(rest_sec, 0, -1):
                    if not self._batch_running:
                        break
                    if s % 30 == 0 or s <= 10:
                        self.root.after(0, self._msg,
                                        f"배치 {rep}/{reps}회 — 휴식 {s}초 남음", TEXT3)
                    if s % 5 == 0 or s <= 10:
                        self.root.after(0, self._set_gauge_action,
                                        f"라운드 휴식 중  {s}초 남음")
                    _time.sleep(1)
                if not self._batch_running:
                    break

                # ── 라운드 B ──────────────────────────────
                self.root.after(0, self._append_log,
                                f"--- [{rep}/{reps}회] 라운드B ({cnt2}건/계정) 시작 ---", "info")
                self.root.after(0, self._msg,
                                f"배치 {rep}/{reps}회 — 라운드B", "#60a5fa")
                self.root.after(0, self._set_gauge_action,
                                f"{rep}/{reps}회 라운드B 시작")
                for i, acct in enumerate(selected, 1):
                    if not self._batch_running:
                        break
                    self.root.after(0, self._append_log,
                                    f"=== B [{i}/{total_accts}] {acct['label']} ({cnt2}건) ===", "info")
                    self._run_single(acct, cnt2)

            # ── 완료 ──────────────────────────────────────
            self._batch_running = False
            self.root.after(0, self._hide_gauge)
            self.root.after(0, self._batch_btn.set_enabled, True)
            self.root.after(0, self._start_btn.set_enabled, True)
            self.root.after(0, self._batch_btn.update_text, "계정스와이프 포스팅시작")
            self.root.after(0, self._msg, f"배치 완료 ({reps}회)", GREEN)
            self.root.after(0, self._append_log,
                            f"=== 배치 전체 완료: {reps}회 ===", "success")

        threading.Thread(target=_batch_worker, daemon=True).start()

    # ── Chrome 좀비 프로세스 강제 정리 ─────────────────────────────────────────
    @staticmethod
    def _kill_chrome_orphans():
        """chromedriver.exe + 우리 RPA가 남긴 chrome.exe 정리.

        chrome.exe 전체를 죽이면 사용자 Chrome도 죽으므로
        chromedriver.exe 만 종료 (Chrome은 driver.quit()로 정리됨).
        """
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", "chromedriver.exe"],
                capture_output=True, timeout=5,
            )
        except Exception:
            pass
        # 혹시 ChromeDriver 종료 후 Chrome이 부모 없이 떠도는 경우는
        # 드물지만 --headless 모드에서 발생할 수 있음 —
        # headless chrome은 사용자 창이 아니므로 강제 종료 가능.
        # 단, 안전을 위해 5초 대기 후 체크.
        _time.sleep(3)

    def _run_single(self, acct: dict, count: int):
        """단일 계정 RPA 실행 (배치용 — 동기, 워커 스레드에서 호출)."""
        try:
            self._proc = subprocess.Popen(
                [_PYTHON_EXE, "-X", "utf8", "-u", SCRIPT,
                 "--account", acct["id"],
                 "--limit", str(count), "--no-overlay", "--manual"],
                cwd=str(_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True, encoding="utf-8", errors="replace",
                bufsize=1,
            )
        except Exception as e:
            self.root.after(0, self._append_log, f"실행 오류: {e}", "error")
            return

        if self._proc.pid:
            LOGS_DIR.mkdir(exist_ok=True)
            PID_FILE.write_text(str(self._proc.pid))

        _last_action = ""
        for line in self._proc.stdout:
            line = line.rstrip("\r\n")
            if line:
                self._log_queue.put((line, ""))
                action = self._detect_action(line)
                # 액션 변경 시만 after() 호출
                if action and action != _last_action:
                    _last_action = action
                    self.root.after(0, self._set_gauge_action, action)

        self._proc.wait()
        rc = self._proc.returncode
        tag = "success" if rc == 0 else "error"
        self.root.after(0, self._append_log,
                        f"  {acct['label']} 완료 (exit {rc})",
                        tag)
        if rc == 0:
            self.root.after(0, self._inc_gauge_done, count)
        self._proc = None
        PID_FILE.unlink(missing_ok=True)

        # ── Chrome/ChromeDriver 좀비 정리 (다음 계정 DLL_INIT_FAILED 방지) ──
        if rc != 0:
            self.root.after(0, self._append_log,
                            f"  [CLEANUP] 비정상 종료 감지 — Chrome 좀비 프로세스 정리 중...",
                            "warn")
            self._kill_chrome_orphans()
            self.root.after(0, self._append_log,
                            "  [CLEANUP] Chrome 정리 완료", "dim")
        else:
            # 정상 종료도 2초 대기 (DLL 해제 시간 확보)
            _time.sleep(2)

    # ── 반응형 리사이즈 ──────────────────────────────────────────────────────────

    _COMPACT_H = 140   # 이 높이 미만이면 컴팩트 모드

    def _on_resize(self, event):
        if event.widget is not self.root:
            return
        if event.height < self._COMPACT_H and not self._compact_mode:
            self._enter_compact()
        elif event.height >= self._COMPACT_H and self._compact_mode:
            self._exit_compact()

    def _enter_compact(self):
        self._compact_mode = True
        self._hdr_frame.pack_forget()
        self._body_frame.pack_forget()
        self._compact_bar.pack(fill="both", expand=True)

    def _exit_compact(self):
        self._compact_mode = False
        self._compact_bar.pack_forget()
        self._hdr_frame.pack(fill="x")
        self._body_frame.pack(fill="both", expand=True)

    def _show_post_run_dialog(self, total: int):
        """RPA 완료 후 추가 작업 여부 묻는 팝업."""
        dlg = tk.Toplevel(self.root)
        dlg.title("RPA 완료")
        dlg.configure(bg=SURFACE)
        # 2026-04-26 정책: 사용자 작업창 위로 강제 띄우지 않음
        if os.getenv("BRIDGE_FORCE_FOREGROUND", "0") == "1":
            dlg.attributes("-topmost", True)
        dlg.resizable(False, False)
        dlg.grab_set()

        # 창 중앙 배치
        dlg.update_idletasks()
        w, h = 300, 160
        rx = self.root.winfo_x() + (self.root.winfo_width()  - w) // 2
        ry = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{rx}+{ry}")

        tk.Label(dlg, text=f"완료  ({total}개 계정)",
                 font=("Malgun Gothic", 13, "bold"),
                 bg=SURFACE, fg=GREEN).pack(pady=(18, 6))
        tk.Label(dlg, text="추가 작업을 하시겠습니까?",
                 font=("Malgun Gothic", 11),
                 bg=SURFACE, fg=TEXT2).pack()

        btn_row = tk.Frame(dlg, bg=SURFACE)
        btn_row.pack(pady=16, fill="x", padx=20)

        def _do_more():
            dlg.destroy()
            # 선택된 계정으로 바로 재실행
            self._on_start()

        def _do_exit():
            dlg.destroy()
            self._on_exit()

        def _do_close():
            dlg.destroy()

        tk.Button(btn_row, text="추가 작업하기",
                  command=_do_more,
                  bg="#0a2a1a", fg=GREEN,
                  font=("Malgun Gothic", 11, "bold"),
                  relief="flat", cursor="hand2",
                  padx=10, pady=7,
                  activebackground="#0d3a20", activeforeground=GREEN,
                  ).pack(side="left", expand=True, fill="x", padx=(0, 4))

        tk.Button(btn_row, text="종료하기",
                  command=_do_exit,
                  bg="#3a0a0a", fg="#f87171",
                  font=("Malgun Gothic", 11, "bold"),
                  relief="flat", cursor="hand2",
                  padx=10, pady=7,
                  activebackground="#5a1010", activeforeground="#ffffff",
                  ).pack(side="left", expand=True, fill="x", padx=(4, 0))

        # 닫기(X) → 그냥 닫기만 (창 유지)
        dlg.protocol("WM_DELETE_WINDOW", _do_close)

    def _on_hide(self):
        self.root.withdraw()

    def _on_exit(self, _=None):
        """X 버튼 — 실행 중 작업 종료 후 창 닫기."""
        self._on_stop()
        self._on_close()

    def run(self):
        self._pump.mainloop()


# ══════════════════════════════════════════ 진입점 ═══════════════════════════

if __name__ == "__main__":
    import os
    import traceback

    # python.exe → pythonw.exe 재시작
    if sys.executable.lower().endswith("python.exe") and "--no-relaunch" not in sys.argv:
        pw = str(Path(sys.executable).parent / "pythonw.exe")
        if Path(pw).exists():
            subprocess.Popen(
                [pw, os.path.abspath(__file__), "--no-relaunch"] + sys.argv[1:],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            )
            sys.exit(0)

    # 단일 인스턴스 — 이미 실행 중이면 창 복원
    # ⚠️ 좀비 pythonw 가 hidden 상태로 살아있으면 ShowWindow 가 화면에 안 뜨고
    #    sys.exit(0) 만 호출되어 사용자에게 "반응 없음" 으로 보임 → 재발 방지 가드
    LOGS_DIR.mkdir(exist_ok=True)
    if ADMIN_HWND_FILE.exists():
        try:
            raw = ADMIN_HWND_FILE.read_text(encoding="utf-8").strip()
            # 구형 포맷(숫자만) / 신형 포맷(hwnd:pid) 모두 지원
            if ":" in raw:
                hwnd_str, pid_str = raw.split(":", 1)
                hwnd = _safe_hwnd(hwnd_str)
                pid  = _safe_pid(pid_str)
            else:
                hwnd = _safe_hwnd(raw)
                pid  = None

            # PID가 기록됐으면 프로세스 생존 여부로 먼저 확인
            pid_alive = False
            if pid is not None:
                try:
                    import psutil as _psu
                    pid_alive = _psu.pid_exists(pid)
                except ImportError:
                    # psutil 없으면 os.kill(pid, 0) 으로 확인
                    try:
                        import signal as _sig
                        os.kill(pid, 0)
                        pid_alive = True
                    except OSError:
                        pid_alive = False

            # PID 가 살아있어도 그 프로세스가 실제 launcher 창을 띄우고 있는지 검증
            # (좀비 pythonw 또는 다른 무관한 pythonw 가 PID 재사용한 경우 감지)
            proc_is_launcher = False
            if pid_alive and pid is not None:
                try:
                    import psutil as _psu
                    _proc = _psu.Process(pid)
                    _cmdline = " ".join(_proc.cmdline()).lower()
                    proc_is_launcher = "rpa_select_launcher" in _cmdline
                except Exception:
                    proc_is_launcher = True   # psutil 실패 시 보수적으로 신뢰

            if (hwnd and ctypes.windll.user32.IsWindow(hwnd)
                    and pid_alive and proc_is_launcher):
                ctypes.windll.user32.ShowWindow(hwnd, 5)
                _bring_hwnd_to_front(hwnd)
                # 창이 실제 visible 상태가 됐는지 확인 (hidden/minimized 잔존 방지)
                try:
                    import time as _t
                    _t.sleep(0.3)
                    if ctypes.windll.user32.IsWindowVisible(hwnd):
                        sys.exit(0)
                    # visible 안 됨 → 좀비로 간주, kill 후 새 인스턴스
                    print(f"[stale] hwnd {hwnd} not visible → killing PID {pid}")
                    try:
                        import psutil as _psu
                        _psu.Process(pid).terminate()
                        _psu.Process(pid).wait(timeout=2)
                    except Exception:
                        try:
                            os.kill(pid, 9)
                        except Exception:
                            pass
                except Exception:
                    sys.exit(0)
            else:
                # stale: PID/HWND 죽었거나 다른 프로세스가 PID 재사용
                if pid_alive and not proc_is_launcher:
                    print(f"[stale] PID {pid} alive but not launcher → ignoring")
        except Exception:
            pass
        ADMIN_HWND_FILE.unlink(missing_ok=True)

    try:
        AdminBoard().run()
    except Exception:
        err = traceback.format_exc()
        crash_log = LOGS_DIR / "_crash.log"
        crash_log.write_text(err, encoding="utf-8")
        # 긴급 에러창 (tkinter가 살아있을 때만)
        try:
            import tkinter.messagebox as _mb
            _mb.showerror("RPA 실행 오류", err[:500])
        except Exception:
            pass
