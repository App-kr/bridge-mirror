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
import subprocess
import sys
import threading
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

# ── 팔레트 ───────────────────────────────────────────────────────────────────
BG      = "#111111"
SURFACE = "#1c1c1e"
CARD    = "#242426"
BORDER  = "#2c2c2e"
TEXT1   = "#f5f5f7"
TEXT2   = "#aeaeb2"
TEXT3   = "#636366"
GREEN   = "#22c55e"
GREEN_D = "#166534"
RED_BG  = "#2d0a0a"
RED_FG  = "#f87171"
HIDE_BG = "#0a1f12"
HIDE_FG = "#6ee7b7"
DIM     = "#1e1e20"

# ── 폰트 (+2pt, 자간 넓힘) ───────────────────────────────────────────────────
FN_HEAD = ("Malgun Gothic", 15, "bold")
FN_MID  = ("Malgun Gothic", 12, "bold")
FN_SM   = ("Malgun Gothic", 11)
FN_TAG  = ("Consolas",      10, "bold")
FN_MONO = ("Consolas",      11)
FN_BTN  = ("Malgun Gothic", 12, "bold")


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
        self.root.resizable(False, False)
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

        self._build()
        self.root.after(200, self._tick)
        self.root.after(400, self._save_hwnd)
        self.root.after(800, self._integrity_check_startup)
        self.root.protocol("WM_DELETE_WINDOW", self._on_exit)

    # ── 빌드 ─────────────────────────────────────────────────────────────────

    def _build(self):
        p = self.PAD

        # ── 전체 폭 헤더 ─────────────────────────────────
        hdr = tk.Frame(self.root, bg=SURFACE)
        hdr.pack(fill="x")
        tk.Label(hdr, text="BRIDGE  RPA Admin",
                 font=("Malgun Gothic", 15, "bold"),
                 bg=SURFACE, fg=TEXT1).pack(side="left", padx=p, pady=14)
        tk.Button(hdr, text="숨기기",
                  command=self._on_hide,
                  bg=HIDE_BG, fg="#ffffff",
                  font=("Malgun Gothic", 10),
                  relief="flat", cursor="hand2",
                  padx=12, pady=6,
                  activebackground=HIDE_BG, activeforeground="#ffffff",
                  ).pack(side="right", padx=(0, 8))

        # ── 좌우 분할 영역 ────────────────────────────────
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)

        # ── 왼쪽 패널 (고정 420px) ────────────────────────
        left = tk.Frame(body, bg=BG, width=self.LW)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        # 수직 구분선
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        # ── 오른쪽 로그 패널 ──────────────────────────────
        right = tk.Frame(body, bg="#0d0d0f")
        right.pack(side="left", fill="both", expand=True)
        self._build_log_panel(right)

        # ── 왼쪽: 상태 표시줄 ────────────────────────────
        st = tk.Frame(left, bg=BG)
        st.pack(fill="x", padx=p, pady=(12, 6))
        self._dot = tk.Label(st, text="●", font=("Consolas", 13), bg=BG, fg=TEXT3)
        self._dot.pack(side="left", padx=(0, 8))
        self._st_lbl = tk.Label(st, text="진행 중인 작업이 없습니다.",
                                font=("Malgun Gothic", 11), bg=BG, fg=TEXT3)
        self._st_lbl.pack(side="left")

        _div(left, padx=p, pady=3)

        # ── 왼쪽: 계정 섹션 헤더 ─────────────────────────
        sh = tk.Frame(left, bg=BG)
        sh.pack(fill="x", padx=p, pady=(10, 6))
        tk.Label(sh, text="계정 선택",
                 font=("Malgun Gothic", 12, "bold"),
                 bg=BG, fg=TEXT1).pack(side="left")
        tf = tk.Frame(sh, bg=BG)
        tf.pack(side="right")
        for txt, fn in [("전체 선택", self._sel_all), ("전체 해제", self._desel_all)]:
            tk.Button(tf, text=txt, command=fn,
                      bg=CARD, fg=TEXT2,
                      font=("Malgun Gothic", 10),
                      relief="flat", cursor="hand2",
                      padx=10, pady=3).pack(side="left", padx=(0, 4))

        # ── 왼쪽: 계정 카드 ──────────────────────────────
        cf = tk.Frame(left, bg=BG)
        cf.pack(fill="x", padx=p)
        for i, acct in enumerate(self._accounts):
            card = AccountCard(cf, acct, on_edit=lambda i=i: self._edit(i))
            card.pack(fill="x", pady=3)
            self._cards.append(card)

        # ── 왼쪽: 계정 관리 + 건수 ───────────────────────
        mf = tk.Frame(left, bg=BG)
        mf.pack(fill="x", padx=p, pady=(8, 8))
        for txt, fn in [("+ 계정 추가", self._on_add), ("계정 관리", self._on_manage)]:
            tk.Button(mf, text=txt, command=fn,
                      bg=CARD, fg="#ffffff",
                      font=("Malgun Gothic", 10),
                      relief="flat", cursor="hand2",
                      padx=12, pady=5).pack(side="left", padx=(0, 8))

        self._cnt = tk.IntVar(value=10)
        tk.Label(mf, text="건",  font=("Malgun Gothic", 11), bg=BG, fg="#ffffff").pack(side="right")
        tk.Spinbox(mf, from_=1, to=30, textvariable=self._cnt,
                   width=4, font=("Malgun Gothic", 12),
                   bg=CARD, fg=TEXT1, buttonbackground=BORDER,
                   relief="flat", highlightthickness=1,
                   highlightbackground=BORDER,
                   ).pack(side="right", padx=(4, 6))
        tk.Label(mf, text="계정당", font=("Malgun Gothic", 11), bg=BG, fg="#ffffff").pack(side="right", padx=(0, 2))

        _div(left, padx=p, pady=2)

        # ── 왼쪽: 메시지 + 버튼 ──────────────────────────
        self._msg_lbl = tk.Label(left, text="", font=("Malgun Gothic", 10), bg=BG, fg=TEXT3)
        self._msg_lbl.pack(pady=(2, 2))

        GAP = 8
        BW  = (self.LW - p * 2 - GAP) // 2

        btn_row = tk.Frame(left, bg=BG)
        btn_row.pack(fill="x", padx=p, pady=(0, 0))

        self._start_btn = RoundCanvas(
            btn_row, h=54, width=BW, fill=GREEN,
            text="시작하기", text_color="#ffffff",
            command=self._on_start,
            font=("Malgun Gothic", 14, "bold"),
        )
        self._start_btn.pack(side="left", padx=(0, GAP))

        self._stop_btn = RoundCanvas(
            btn_row, h=54, width=BW, fill="#991b1b",
            text="즉시 중단", text_color="#ffffff",
            command=self._on_stop,
            font=("Malgun Gothic", 13, "bold"),
        )
        self._stop_btn.pack(side="left")

        # ── 왼쪽: 배치 모드 ──────────────────────────────
        _div(left, padx=p, pady=(8, 0))

        bh = tk.Frame(left, bg=BG)
        bh.pack(fill="x", padx=p, pady=(6, 4))
        tk.Label(bh, text="배치 모드",
                 font=("Malgun Gothic", 10, "bold"),
                 bg=BG, fg=TEXT2).pack(side="left")

        # 스핀박스 행
        sf = tk.Frame(left, bg=BG)
        sf.pack(fill="x", padx=p, pady=(0, 6))

        def _spin(parent, var, lo=1, hi=30, w=3):
            return tk.Spinbox(parent, from_=lo, to=hi, textvariable=var,
                              width=w, font=("Malgun Gothic", 11),
                              bg=CARD, fg=TEXT1, buttonbackground=BORDER,
                              relief="flat", highlightthickness=1,
                              highlightbackground=BORDER)

        def _lbl(parent, text):
            tk.Label(parent, text=text,
                     font=("Malgun Gothic", 10), bg=BG, fg=TEXT2).pack(side="left", padx=(2, 2))

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

        # 배치 시작 버튼 (전체 폭)
        BATCH_C = "#1e3a5f"
        self._batch_btn = RoundCanvas(
            left, h=44, fill=BATCH_C,
            text="배치 시작", text_color="#ffffff",
            command=self._on_batch_start,
            font=("Malgun Gothic", 12, "bold"),
        )
        self._batch_btn.pack(fill="x", padx=p, pady=(0, 6))

    def _build_log_panel(self, parent):
        """오른쪽 실시간 로그 패널."""
        LOG_BG = "#0d0d0f"

        # 로그 헤더
        lh = tk.Frame(parent, bg=SURFACE)
        lh.pack(fill="x")
        tk.Label(lh, text="실시간 로그",
                 font=("Malgun Gothic", 11, "bold"),
                 bg=SURFACE, fg=TEXT1).pack(side="left", padx=14, pady=10)
        tk.Button(lh, text="지우기",
                  command=self._clear_log,
                  bg=CARD, fg=TEXT2,
                  font=("Malgun Gothic", 9),
                  relief="flat", cursor="hand2",
                  padx=8, pady=4,
                  activebackground=CARD, activeforeground=TEXT1,
                  ).pack(side="right", padx=10, pady=8)

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
            ADMIN_HWND_FILE.write_text(str(self.root.winfo_id()), encoding="utf-8")
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

    def _tick(self):
        if self._running:
            self._blink = not self._blink
            # 점 깜박 (초록 ↔ 어두운 초록)
            self._dot.configure(fg=GREEN if self._blink else GREEN_D)
            # 텍스트도 깜박 (밝은 초록 ↔ 살짝 어두운 초록)
            lbl_fg = "#22c55e" if self._blink else "#15803d"
            self._st_lbl.configure(text="작업이 진행 중입니다.", fg=lbl_fg)
        else:
            self._dot.configure(fg=TEXT3)
            self._st_lbl.configure(text="진행 중인 작업이 없습니다.", fg=TEXT3)
            self._start_btn.update_text("시작하기")
            self._start_btn.update_fill(GREEN, "#ffffff")
        self.root.after(600, self._tick)

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
        self._start_btn.update_fill("#0d2e14", TEXT1)
        self._start_btn.set_enabled(False)

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
                         "--headless", "--account", acct["id"],
                         "--limit", str(count), "--no-overlay"],
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

                # stdout 실시간 읽기
                for line in self._proc.stdout:
                    line = line.rstrip("\r\n")
                    if line:
                        self.root.after(0, self._append_log, line)

                self._proc.wait()
                rc = self._proc.returncode
                self.root.after(0, self._append_log,
                                f"=== {acct['label']} 종료 (exit {rc}) ===",
                                "success" if rc == 0 else "error")

            PID_FILE.unlink(missing_ok=True)
            self.root.after(0, self._msg, f"완료  ({total}개 계정)", GREEN)
            self.root.after(0, self._append_log,
                            f"--- 전체 완료: {total}개 계정 ---", "success")
            self.root.after(0, self._start_btn.update_text, "시작하기")
            self.root.after(0, self._start_btn.update_fill, GREEN, "#ffffff")
            self.root.after(0, self._start_btn.set_enabled, True)
            self._running = False
            self._proc    = None

        threading.Thread(target=worker, daemon=True).start()

    def _on_stop(self):
        # 배치 + 일반 모두 중단
        self._batch_running = False
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
        self._start_btn.update_text("시작하기")
        self._start_btn.update_fill(GREEN, BG)
        self._start_btn.set_enabled(True)
        self._batch_btn.update_text("배치 시작")
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
        self._batch_btn.update_text("배치 실행 중...")
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
                    import time as _t; _t.sleep(1)
                if not self._batch_running:
                    break

                # ── 라운드 B ──────────────────────────────
                self.root.after(0, self._append_log,
                                f"--- [{rep}/{reps}회] 라운드B ({cnt2}건/계정) 시작 ---", "info")
                self.root.after(0, self._msg,
                                f"배치 {rep}/{reps}회 — 라운드B", "#60a5fa")
                for i, acct in enumerate(selected, 1):
                    if not self._batch_running:
                        break
                    self.root.after(0, self._append_log,
                                    f"=== B [{i}/{total_accts}] {acct['label']} ({cnt2}건) ===", "info")
                    self._run_single(acct, cnt2)

            # ── 완료 ──────────────────────────────────────
            self._batch_running = False
            self.root.after(0, self._batch_btn.set_enabled, True)
            self.root.after(0, self._start_btn.set_enabled, True)
            self.root.after(0, self._batch_btn.update_text, "배치 시작")
            self.root.after(0, self._msg, f"배치 완료 ({reps}회)", GREEN)
            self.root.after(0, self._append_log,
                            f"=== 배치 전체 완료: {reps}회 ===", "success")

        threading.Thread(target=_batch_worker, daemon=True).start()

    def _run_single(self, acct: dict, count: int):
        """단일 계정 RPA 실행 (배치용 — 동기, 워커 스레드에서 호출)."""
        try:
            self._proc = subprocess.Popen(
                [_PYTHON_EXE, "-X", "utf8", "-u", SCRIPT,
                 "--headless", "--account", acct["id"],
                 "--limit", str(count), "--no-overlay"],
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

        for line in self._proc.stdout:
            line = line.rstrip("\r\n")
            if line:
                self.root.after(0, self._append_log, line)

        self._proc.wait()
        rc = self._proc.returncode
        self.root.after(0, self._append_log,
                        f"  {acct['label']} 완료 (exit {rc})",
                        "success" if rc == 0 else "error")
        self._proc = None
        PID_FILE.unlink(missing_ok=True)

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
    LOGS_DIR.mkdir(exist_ok=True)
    if ADMIN_HWND_FILE.exists():
        try:
            hwnd = _safe_hwnd(ADMIN_HWND_FILE.read_text(encoding="utf-8"))
            if hwnd and ctypes.windll.user32.IsWindow(hwnd):
                ctypes.windll.user32.ShowWindow(hwnd, 5)
                _bring_hwnd_to_front(hwnd)
                sys.exit(0)
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
