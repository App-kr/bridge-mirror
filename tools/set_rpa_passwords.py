"""4개 계정 Craigslist 비밀번호 재설정 GUI"""
import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from crypto_util import encrypt_value, _load_or_create_key  # noqa: F401 (key init)

ACCOUNTS = [
    ("account1", "Coreabridge@gmail.com"),
    ("account2", "airelair00@gmail.com"),
    ("account3", "ferrari812fast@gmail.com"),
    ("account4", "bridgejobkr@gmail.com"),
]

def ask_password(account_id, email):
    result = {}
    win = tk.Tk()
    win.title(f"비밀번호 입력 — {account_id}")
    win.geometry("380x160")
    win.resizable(False, False)
    win.lift()
    win.attributes("-topmost", True)

    tk.Label(win, text=f"계정: {email}", font=("Segoe UI", 10, "bold"),
             fg="#333").pack(pady=(18, 4))
    tk.Label(win, text="Craigslist 비밀번호:", font=("Segoe UI", 10)).pack()

    pw_var = tk.StringVar()
    entry = tk.Entry(win, textvariable=pw_var, show="●",
                     font=("Segoe UI", 12), width=28)
    entry.pack(pady=6)
    entry.focus_set()

    def on_save():
        pw = pw_var.get().strip()
        if not pw:
            messagebox.showwarning("입력 필요", "비밀번호를 입력하세요.", parent=win)
            return
        result["pw"] = pw
        win.destroy()

    def on_skip():
        result["skip"] = True
        win.destroy()

    btn_frame = tk.Frame(win)
    btn_frame.pack()
    tk.Button(btn_frame, text="저장", width=10, bg="#1a6bbf", fg="white",
              font=("Segoe UI", 10, "bold"), command=on_save).pack(side="left", padx=6)
    tk.Button(btn_frame, text="건너뛰기", width=10,
              font=("Segoe UI", 10), command=on_skip).pack(side="left", padx=6)

    win.bind("<Return>", lambda e: on_save())
    win.mainloop()
    return result

def save_password(account_id, password):
    env_path = BASE_DIR / f"{account_id}.env"
    if not env_path.exists():
        print(f"  [ERROR] {env_path} 없음")
        return False

    enc = encrypt_value(password)

    lines = env_path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    replaced = False
    for line in lines:
        if line.startswith("CRAIGSLIST_PASSWORD="):
            new_lines.append(f"CRAIGSLIST_PASSWORD=ENC:{enc}")
            replaced = True
        else:
            new_lines.append(line)

    if not replaced:
        new_lines.append(f"CRAIGSLIST_PASSWORD=ENC:{enc}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"  [{account_id}] 비밀번호 저장 완료")
    return True

if __name__ == "__main__":
    print("=== RPA 계정 비밀번호 재설정 ===\n")
    for account_id, email in ACCOUNTS:
        print(f"[{account_id}] {email}")
        res = ask_password(account_id, email)
        if res.get("skip"):
            print(f"  [{account_id}] 건너뜀")
        elif "pw" in res:
            save_password(account_id, res["pw"])
    print("\n완료. 이제 RPA.vbs 를 실행하세요.")
