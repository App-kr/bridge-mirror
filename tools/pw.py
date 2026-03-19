"""
pw.py — BX Credential Manager GUI
범용 비밀번호/API키 관리 — 어떤 서비스든 사용 가능
설치 필요 없음 (tkinter = Python 기본 내장)
"""
import hashlib
import hmac
import secrets
import subprocess
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ITERATIONS = 260000

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
    ("직접 입력",                        "",                       False),
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


def copy_to_clipboard(text: str):
    try:
        subprocess.run(["clip"], input=text.encode(), check=True)
    except Exception:
        pass


def main():
    import tkinter as tk
    from tkinter import ttk, messagebox

    root = tk.Tk()
    root.title("BX Credential Manager")
    root.geometry("420x380")
    root.resizable(False, False)
    root.configure(bg="#1a1a2e")
    root.attributes("-topmost", True)

    # ── 서비스 선택 ─────────────────────────────────────────────
    tk.Label(root, text="BX Credential Manager",
             font=("Segoe UI", 13, "bold"), fg="#e0e0e0", bg="#1a1a2e"
             ).pack(pady=(15, 10))

    frame = tk.Frame(root, bg="#1a1a2e")
    frame.pack(padx=30, fill="x")

    tk.Label(frame, text="서비스 선택", font=("Segoe UI", 10),
             fg="#aaaaaa", bg="#1a1a2e", anchor="w").pack(fill="x")

    preset_names = [p[0] for p in PRESETS]
    combo = ttk.Combobox(frame, values=preset_names, state="readonly",
                         font=("Segoe UI", 10), width=36)
    combo.set(preset_names[0])
    combo.pack(pady=(2, 8), fill="x")

    # 직접 입력용 키 이름
    custom_frame = tk.Frame(frame, bg="#1a1a2e")
    custom_lbl = tk.Label(custom_frame, text="BX 키 이름", font=("Segoe UI", 10),
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

    # ── 해시 체크박스 ───────────────────────────────────────────
    hash_var = tk.BooleanVar(value=True)
    hash_chk = tk.Checkbutton(frame, text="pbkdf2 해시 저장 (비밀번호용)",
                               variable=hash_var, font=("Segoe UI", 9),
                               fg="#888888", bg="#1a1a2e", selectcolor="#16213e",
                               activebackground="#1a1a2e", activeforeground="#cccccc")
    hash_chk.pack(anchor="w", pady=(5, 5))

    def sync_hash_check(event=None):
        idx = combo.current()
        hash_var.set(PRESETS[idx][2])

    combo.bind("<<ComboboxSelected>>", lambda e: (on_combo_change(e), sync_hash_check(e)))

    # ── 비밀번호 입력 ───────────────────────────────────────────
    tk.Label(frame, text="새 값", font=("Segoe UI", 10),
             fg="#cccccc", bg="#1a1a2e", anchor="w").pack(fill="x", pady=(5, 0))
    pw1 = tk.Entry(frame, show="●", width=36, font=("Segoe UI", 11),
                   bg="#16213e", fg="white", insertbackground="white",
                   relief="flat", highlightthickness=1, highlightcolor="#0f3460")
    pw1.pack(fill="x", ipady=4, pady=(2, 5))

    tk.Label(frame, text="확인", font=("Segoe UI", 10),
             fg="#cccccc", bg="#1a1a2e", anchor="w").pack(fill="x")
    pw2 = tk.Entry(frame, show="●", width=36, font=("Segoe UI", 11),
                   bg="#16213e", fg="white", insertbackground="white",
                   relief="flat", highlightthickness=1, highlightcolor="#0f3460")
    pw2.pack(fill="x", ipady=4, pady=(2, 10))

    # ── 저장 ────────────────────────────────────────────────────
    def on_save():
        idx = combo.current()
        preset = PRESETS[idx]
        bx_key = preset[1] if preset[1] else custom_entry.get().strip()

        if not bx_key:
            messagebox.showwarning("입력 오류", "BX 키 이름을 입력하세요.")
            return

        p1 = pw1.get().strip()
        p2 = pw2.get().strip()

        if not p1:
            messagebox.showwarning("입력 오류", "값을 입력하세요.")
            return
        if p1 != p2:
            messagebox.showwarning("입력 오류", "값이 일치하지 않습니다.")
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
                "저장 완료",
                f"{svc_name}\n\n"
                f"BX 저장 완료 (DPAPI 암호화)\n"
                f"클립보드에 복사됨 (필요 시 Ctrl+V)"
            )
            pw1.delete(0, "end")
            pw2.delete(0, "end")
        else:
            messagebox.showerror("오류", "BX 저장 실패")

    btn = tk.Button(frame, text="저장", command=on_save,
                    font=("Segoe UI", 11, "bold"), width=36,
                    bg="#0f3460", fg="white", activebackground="#1a5276",
                    activeforeground="white", relief="flat", cursor="hand2")
    btn.pack(ipady=4)

    root.bind("<Return>", lambda e: on_save())
    pw1.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()
