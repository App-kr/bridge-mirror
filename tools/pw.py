"""
pw.py — BX Credential Manager GUI  v2.0
범용 비밀번호/API키 관리 + 서버 블랙리스트 리셋
설치 필요 없음 (tkinter = Python 기본 내장)
독립 실행 가능 — Claude 없이도 바로가기로 실행
"""
import hashlib
import hmac
import secrets
import subprocess
import sys
import os
import json
from pathlib import Path
from urllib.request import Request as UrlRequest, urlopen
from urllib.error import URLError

BASE_DIR = Path(__file__).resolve().parent.parent
ITERATIONS = 260000
RENDER_API = "https://bridge-n7hk.onrender.com"

# ── 프리셋: (표시명, BX키, 해시여부) ────────────────────────────────────────
PRESETS = [
    ("BRIDGE Admin (bridgejob.co.kr)",  "ADMIN_PASSWORD",        True),
    ("Gmail App Password",              "GMAIL_APP_PASSWORD",     False),
    ("Naver App Password",              "NAVER_APP_PASSWORD",     False),
    ("Naver SMTP Password",             "NAVER_SMTP_PASS",       False),
    ("Telegram Bot Token",              "TELEGRAM_BOT_TOKEN",     False),
    ("Anthropic API Key",               "ANTHROPIC_API_KEY",      False),
    ("Bridge SMTP Password",            "BRIDGE_SMTP_PASS",       False),
    ("Craigslist Password",             "CRAIGSLIST_PASSWORD",    False),
    ("Admin API Key",                   "ADMIN_API_KEY",          False),
    ("JWT Secret",                      "JWT_SECRET",             False),
    ("Webhook Secret",                  "WEBHOOK_SECRET",         False),
    ("Bridge Webhook Secret",           "BRIDGE_WEBHOOK_SECRET",  False),
    ("Upload Sign Key",                 "UPLOAD_SIGN_KEY",        False),
    ("PII Encryption Key",              "BRIDGE_FIELD_KEY",       False),
    ("\uc9c1\uc811 \uc785\ub825",       "",                       False),
]


def pbkdf2_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS)
    return f"pbkdf2:sha256:{ITERATIONS}:{salt}:{dk.hex()}"


def verify(password: str, stored: str) -> bool:
    if not stored.startswith("pbkdf2:sha256:"):
        return hmac.compare_digest(password, stored)
    try:
        _, _, iters, salt, dk_hex = stored.split(":", 4)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def save_to_bx(key: str, value: str) -> bool:
    sys.path.insert(0, str(BASE_DIR))
    try:
        from tools.bx import _store
        _store(key, value)
        return True
    except Exception:
        return False


def read_from_bx(key: str) -> str:
    sys.path.insert(0, str(BASE_DIR))
    try:
        from tools.bx import _read
        return _read(key) or ""
    except Exception:
        return ""


def copy_to_clipboard(text: str):
    try:
        subprocess.run(["clip"], input=text.encode(), check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass


def reset_blacklist() -> tuple[bool, str]:
    """Render 서버 IP 블랙리스트 초기화. (성공여부, 메시지) 반환."""
    api_key = read_from_bx("ADMIN_API_KEY")
    if not api_key:
        return False, "ADMIN_API_KEY\uac00 BX\uc5d0 \uc5c6\uc2b5\ub2c8\ub2e4.\npw.py\uc5d0\uc11c Admin API Key\ub97c \uba3c\uc800 \uc800\uc7a5\ud558\uc138\uc694."
    try:
        req = UrlRequest(
            f"{RENDER_API}/api/admin/reset-blacklist",
            data=b"{}",
            headers={
                "Content-Type": "application/json",
                "X-Admin-Key": api_key,
            },
            method="POST",
        )
        with urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
            return True, body.get("message", "\ucd08\uae30\ud654 \uc644\ub8cc")
    except URLError as e:
        reason = str(getattr(e, "reason", e))
        if hasattr(e, "code") and e.code == 403:
            return False, "API \ud0a4 \uac80\uc99d \uc2e4\ud328 (403)\nAdmin API Key\uac00 \uc11c\ubc84\uc640 \uc77c\uce58\ud558\ub294\uc9c0 \ud655\uc778\ud558\uc138\uc694."
        return False, f"\uc11c\ubc84 \uc5f0\uacb0 \uc2e4\ud328:\n{reason}"
    except Exception as e:
        return False, f"\uc624\ub958: {e}"


def main():
    import tkinter as tk
    from tkinter import ttk, messagebox

    root = tk.Tk()
    root.title("BX Credential Manager")
    root.geometry("440x520")
    root.resizable(False, False)
    root.configure(bg="#1a1a2e")
    root.attributes("-topmost", True)

    # ── 아이콘 설정 (ICO 파일 있으면 사용) ─────────────────────
    ico_path = Path(__file__).resolve().parent / "bx_icon.ico"
    if ico_path.exists():
        try:
            root.iconbitmap(str(ico_path))
        except Exception:
            pass

    # ── 타이틀 ─────────────────────────────────────────────────
    tk.Label(root, text="\U0001f510 BX Credential Manager",
             font=("Segoe UI", 13, "bold"), fg="#e0e0e0", bg="#1a1a2e"
             ).pack(pady=(12, 8))

    frame = tk.Frame(root, bg="#1a1a2e")
    frame.pack(padx=30, fill="x")

    # ── 서비스 선택 ────────────────────────────────────────────
    tk.Label(frame, text="\uc11c\ube44\uc2a4 \uc120\ud0dd", font=("Segoe UI", 10),
             fg="#aaaaaa", bg="#1a1a2e", anchor="w").pack(fill="x")

    preset_names = [p[0] for p in PRESETS]
    combo = ttk.Combobox(frame, values=preset_names, state="readonly",
                         font=("Segoe UI", 10), width=36)
    combo.set(preset_names[0])
    combo.pack(pady=(2, 8), fill="x")

    # 직접 입력용 키 이름
    custom_frame = tk.Frame(frame, bg="#1a1a2e")
    custom_lbl = tk.Label(custom_frame, text="BX \ud0a4 \uc774\ub984", font=("Segoe UI", 10),
                          fg="#aaaaaa", bg="#1a1a2e", anchor="w")
    custom_entry = tk.Entry(custom_frame, width=36, font=("Segoe UI", 10),
                            bg="#16213e", fg="white", insertbackground="white",
                            relief="flat", highlightthickness=1, highlightcolor="#0f3460")

    def on_combo_change(event=None):
        idx = combo.current()
        if PRESETS[idx][1] == "":
            custom_frame.pack(fill="x", pady=(0, 5))
            custom_lbl.pack(fill="x")
            custom_entry.pack(fill="x", ipady=3)
        else:
            custom_frame.pack_forget()

    combo.bind("<<ComboboxSelected>>", on_combo_change)

    # ── 해시 체크박스 ──────────────────────────────────────────
    hash_var = tk.BooleanVar(value=True)
    hash_chk = tk.Checkbutton(frame, text="pbkdf2 \ud574\uc2dc \uc800\uc7a5 (\ube44\ubc00\ubc88\ud638\uc6a9)",
                               variable=hash_var, font=("Segoe UI", 9),
                               fg="#888888", bg="#1a1a2e", selectcolor="#16213e",
                               activebackground="#1a1a2e", activeforeground="#cccccc")
    hash_chk.pack(anchor="w", pady=(5, 5))

    def sync_hash_check(event=None):
        idx = combo.current()
        hash_var.set(PRESETS[idx][2])

    combo.bind("<<ComboboxSelected>>", lambda e: (on_combo_change(e), sync_hash_check(e)))

    # ── 비밀번호 입력 ──────────────────────────────────────────
    tk.Label(frame, text="\uc0c8 \uac12", font=("Segoe UI", 10),
             fg="#cccccc", bg="#1a1a2e", anchor="w").pack(fill="x", pady=(5, 0))
    pw1 = tk.Entry(frame, show="\u25cf", width=36, font=("Segoe UI", 11),
                   bg="#16213e", fg="white", insertbackground="white",
                   relief="flat", highlightthickness=1, highlightcolor="#0f3460")
    pw1.pack(fill="x", ipady=4, pady=(2, 5))

    tk.Label(frame, text="\ud655\uc778", font=("Segoe UI", 10),
             fg="#cccccc", bg="#1a1a2e", anchor="w").pack(fill="x")
    pw2 = tk.Entry(frame, show="\u25cf", width=36, font=("Segoe UI", 11),
                   bg="#16213e", fg="white", insertbackground="white",
                   relief="flat", highlightthickness=1, highlightcolor="#0f3460")
    pw2.pack(fill="x", ipady=4, pady=(2, 10))

    # ── 저장 버튼 ──────────────────────────────────────────────
    def on_save():
        idx = combo.current()
        preset = PRESETS[idx]
        bx_key = preset[1] if preset[1] else custom_entry.get().strip()

        if not bx_key:
            messagebox.showwarning("\uc785\ub825 \uc624\ub958", "BX \ud0a4 \uc774\ub984\uc744 \uc785\ub825\ud558\uc138\uc694.")
            return

        p1 = pw1.get().strip()
        p2 = pw2.get().strip()

        if not p1:
            messagebox.showwarning("\uc785\ub825 \uc624\ub958", "\uac12\uc744 \uc785\ub825\ud558\uc138\uc694.")
            return
        if p1 != p2:
            messagebox.showwarning("\uc785\ub825 \uc624\ub958", "\uac12\uc774 \uc77c\uce58\ud558\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4.")
            return

        # 해시 또는 평문
        if hash_var.get():
            store_val = pbkdf2_hash(p1)
            assert verify(p1, store_val)
        else:
            store_val = p1

        if save_to_bx(bx_key, store_val):
            copy_to_clipboard(store_val)
            svc_name = preset[0] if preset[1] else bx_key
            messagebox.showinfo(
                "\uc800\uc7a5 \uc644\ub8cc",
                f"{svc_name}\n\n"
                f"BX \uc800\uc7a5 \uc644\ub8cc (DPAPI \uc554\ud638\ud654)\n"
                f"\ud074\ub9bd\ubcf4\ub4dc\uc5d0 \ubcf5\uc0ac\ub428 (\ud544\uc694 \uc2dc Ctrl+V)"
            )
            pw1.delete(0, "end")
            pw2.delete(0, "end")
        else:
            messagebox.showerror("\uc624\ub958", "BX \uc800\uc7a5 \uc2e4\ud328")

    btn_save = tk.Button(frame, text="\uc800\uc7a5", command=on_save,
                         font=("Segoe UI", 11, "bold"), width=36,
                         bg="#0f3460", fg="white", activebackground="#1a5276",
                         activeforeground="white", relief="flat", cursor="hand2")
    btn_save.pack(ipady=4)

    # ── 구분선 ─────────────────────────────────────────────────
    sep = tk.Frame(frame, bg="#333355", height=1)
    sep.pack(fill="x", pady=(15, 10))

    # ── 서버 관리 섹션 ─────────────────────────────────────────
    tk.Label(frame, text="\U0001f6e1\ufe0f \uc11c\ubc84 \ubcf4\uc548 \uad00\ub9ac",
             font=("Segoe UI", 11, "bold"), fg="#e0e0e0", bg="#1a1a2e",
             anchor="w").pack(fill="x", pady=(0, 5))

    status_var = tk.StringVar(value="")
    status_lbl = tk.Label(frame, textvariable=status_var,
                          font=("Segoe UI", 9), fg="#66bb6a", bg="#1a1a2e",
                          anchor="w", wraplength=360)
    status_lbl.pack(fill="x")

    def on_reset_blacklist():
        btn_reset.config(state="disabled", text="\ucc98\ub9ac \uc911...")
        root.update_idletasks()
        ok, msg = reset_blacklist()
        if ok:
            status_var.set(f"\u2705 {msg}")
            status_lbl.config(fg="#66bb6a")
        else:
            status_var.set(f"\u274c {msg}")
            status_lbl.config(fg="#ef5350")
        btn_reset.config(state="normal", text="\U0001f512 \uc811\uc18d\ucc28\ub2e8 \ucd08\uae30\ud654 (IP Blacklist Reset)")

    btn_reset = tk.Button(frame,
                          text="\U0001f512 \uc811\uc18d\ucc28\ub2e8 \ucd08\uae30\ud654 (IP Blacklist Reset)",
                          command=on_reset_blacklist,
                          font=("Segoe UI", 10), width=36,
                          bg="#4a1942", fg="white", activebackground="#6a2462",
                          activeforeground="white", relief="flat", cursor="hand2")
    btn_reset.pack(ipady=3, pady=(5, 0))

    tk.Label(frame, text="* \ubc18\ubcf5 \ub85c\uadf8\uc778 \uc2e4\ud328\ub85c \ucc28\ub2e8\ub41c IP\ub97c \ud574\uc81c\ud569\ub2c8\ub2e4",
             font=("Segoe UI", 8), fg="#666666", bg="#1a1a2e",
             anchor="w").pack(fill="x", pady=(3, 0))

    root.bind("<Return>", lambda e: on_save())
    pw1.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()
