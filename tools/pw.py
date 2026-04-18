"""
pw.py — BX Credential Manager GUI  v3.0
보안 강화: 마스터 PIN 잠금 + DPAPI+PIN 이중 암호화 + 클립보드 자동삭제 + 세션 타임아웃

설치 불필요 (tkinter 기본 내장)
독립 실행 가능 — 바탕화면 아이콘으로 실행
"""
import hashlib
import hmac
import secrets
import subprocess
import sys
import os
import json
import threading
import time
from pathlib import Path
from urllib.request import Request as UrlRequest, urlopen
from urllib.error import URLError

BASE_DIR   = Path(__file__).resolve().parent.parent
ITERATIONS = 260000
RENDER_API = "https://bridge-n7hk.onrender.com"

# 세션 설정
CLIPBOARD_CLEAR_AFTER = 30   # 초 — 클립보드 자동 삭제
SESSION_TIMEOUT       = 300  # 초 — 5분 비활성화 시 잠금

# ── 세션 상태 (메모리에만, 디스크 저장 안 함) ──────────────────────────────
_session_pin_key: bytes | None = None
_last_activity: float = 0.0

# ── 프리셋: (표시명, BX키, 해시여부) ────────────────────────────────────────
PRESETS = [
    ("네이버 Bridge (bridgejob 블로그)",  "BRIDGE_NAVER_PW",       False),
    ("네이버 맛족도 (matjokdo 블로그)",   "MATJOKDO_NAVER_PW",     False),
    ("네이버 bestpucca",                 "BESTPUCCA_NAVER_PW",    False),
    ("BRIDGE Admin (bridgejob.co.kr)",  "ADMIN_PASSWORD",        True),
    ("Gmail App Password",              "GMAIL_APP_PASSWORD",    False),
    ("Naver App Password",              "NAVER_APP_PASSWORD",    False),
    ("Naver SMTP Password",             "NAVER_SMTP_PASS",       False),
    ("Telegram Bot Token",              "TELEGRAM_BOT_TOKEN",    False),
    ("Anthropic API Key",               "ANTHROPIC_API_KEY",     False),
    ("Bridge SMTP Password",            "BRIDGE_SMTP_PASS",      False),
    ("Craigslist Password",             "CRAIGSLIST_PASSWORD",   False),
    ("Admin API Key",                   "ADMIN_API_KEY",         False),
    ("JWT Secret",                      "JWT_SECRET",            False),
    ("Webhook Secret",                  "WEBHOOK_SECRET",        False),
    ("Bridge Webhook Secret",           "BRIDGE_WEBHOOK_SECRET", False),
    ("Upload Sign Key",                 "UPLOAD_SIGN_KEY",       False),
    ("PII Encryption Key",              "BRIDGE_FIELD_KEY",      False),
    ("Notion Integration Token",        "NOTION_TOKEN",          False),
    ("Notion Page ID",                  "NOTION_PAGE_ID",        False),
    ("Supabase DB Password",            "SUPABASE_DB_PASSWORD",  False),
    ("OpenRun Admin Secret",            "OPENRUN_ADMIN_SECRET",  False),
    ("직접 입력",                        "",                      False),
]


# ── 유틸 ────────────────────────────────────────────────────────────────────

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


def copy_to_clipboard(text: str):
    try:
        subprocess.run(["clip"], input=text.encode("utf-8"), check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass


def clear_clipboard_after(seconds: int):
    """지정 시간 후 클립보드를 빈 문자열로 덮어씀"""
    def _clear():
        time.sleep(seconds)
        try:
            subprocess.run(["clip"], input=b"", check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass
    threading.Thread(target=_clear, daemon=True).start()


def touch_activity():
    global _last_activity
    _last_activity = time.monotonic()


def save_to_bx(key: str, value: str) -> bool:
    sys.path.insert(0, str(BASE_DIR))
    try:
        from tools.bx import _store_v2, _store, has_master_pin
        if has_master_pin() and _session_pin_key is not None:
            _store_v2(key, value, _session_pin_key)
        else:
            _store(key, value)  # PIN 미설정 시 기존 v1
        return True
    except Exception:
        return False


def read_from_bx(key: str) -> str:
    sys.path.insert(0, str(BASE_DIR))
    try:
        from tools.bx import _read_auto, has_master_pin
        return _read_auto(key, _session_pin_key if has_master_pin() else None) or ""
    except Exception:
        return ""


def reset_blacklist() -> tuple[bool, str]:
    api_key = read_from_bx("ADMIN_API_KEY")
    if not api_key:
        return False, "ADMIN_API_KEY가 BX에 없습니다.\npw.py에서 Admin API Key를 먼저 저장하세요."
    try:
        req = UrlRequest(
            f"{RENDER_API}/api/admin/reset-blacklist",
            data=b"{}",
            headers={"Content-Type": "application/json", "X-Admin-Key": api_key},
            method="POST",
        )
        with urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
            return True, body.get("message", "초기화 완료")
    except URLError as e:
        if hasattr(e, "code") and e.code == 403:
            return False, "API 키 검증 실패 (403)\nAdmin API Key가 서버와 일치하는지 확인하세요."
        return False, f"서버 연결 실패:\n{getattr(e, 'reason', e)}"
    except Exception as e:
        return False, f"오류: {e}"


# ── PIN 잠금 화면 ────────────────────────────────────────────────────────────

def show_pin_dialog() -> bool:
    """
    PIN 설정/입력 창을 보여주고, 성공 시 _session_pin_key를 설정.
    반환값: True = 인증 성공 / False = 취소(창 닫음)
    """
    global _session_pin_key

    import tkinter as tk
    from tkinter import messagebox
    from tools.bx import has_master_pin, set_master_pin, verify_master_pin, derive_pin_key

    result = {"ok": False}

    dlg = tk.Tk()
    dlg.title("BX 잠금 해제")
    dlg.geometry("340x280")
    dlg.resizable(False, False)
    dlg.configure(bg="#0d0d1a")
    dlg.attributes("-topmost", True)

    # 아이콘
    ico_path = Path(__file__).resolve().parent / "bx_icon.ico"
    if ico_path.exists():
        try:
            dlg.iconbitmap(str(ico_path))
        except Exception:
            pass

    is_first_run = not has_master_pin()

    tk.Label(dlg,
             text="BX Credential Manager",
             font=("Segoe UI", 13, "bold"),
             fg="#e0e0e0", bg="#0d0d1a").pack(pady=(18, 4))

    tk.Label(dlg,
             text="[PIN 설정 — 처음 실행]" if is_first_run else "[PIN 입력]",
             font=("Segoe UI", 10),
             fg="#888888", bg="#0d0d1a").pack()

    inner = tk.Frame(dlg, bg="#0d0d1a")
    inner.pack(padx=30, fill="x", pady=(12, 0))

    tk.Label(inner, text="PIN", font=("Segoe UI", 10),
             fg="#cccccc", bg="#0d0d1a", anchor="w").pack(fill="x")
    pin1 = tk.Entry(inner, show="*", font=("Segoe UI", 12),
                    bg="#16213e", fg="white", insertbackground="white",
                    relief="flat", highlightthickness=1, highlightcolor="#4a90d9")
    pin1.pack(fill="x", ipady=5, pady=(2, 8))

    if is_first_run:
        tk.Label(inner, text="PIN 확인", font=("Segoe UI", 10),
                 fg="#cccccc", bg="#0d0d1a", anchor="w").pack(fill="x")
        pin2 = tk.Entry(inner, show="*", font=("Segoe UI", 12),
                        bg="#16213e", fg="white", insertbackground="white",
                        relief="flat", highlightthickness=1, highlightcolor="#4a90d9")
        pin2.pack(fill="x", ipady=5, pady=(2, 8))
    else:
        pin2 = None

    msg_var = tk.StringVar()
    tk.Label(inner, textvariable=msg_var, font=("Segoe UI", 9),
             fg="#ef5350", bg="#0d0d1a", anchor="w").pack(fill="x")

    attempt_count = [0]

    def on_confirm(event=None):
        p = pin1.get()
        if len(p) < 4:
            msg_var.set("PIN은 4자 이상이어야 합니다.")
            return

        if is_first_run:
            if pin2 and p != pin2.get():
                msg_var.set("PIN이 일치하지 않습니다.")
                return
            set_master_pin(p)
            _session_pin_key = derive_pin_key(p)
            result["ok"] = True
            dlg.destroy()
        else:
            attempt_count[0] += 1
            if verify_master_pin(p):
                _session_pin_key = derive_pin_key(p)
                result["ok"] = True
                dlg.destroy()
            else:
                remaining = 5 - attempt_count[0]
                if remaining <= 0:
                    messagebox.showerror("잠금", "PIN 5회 오류. 프로그램을 종료합니다.")
                    dlg.destroy()
                else:
                    msg_var.set(f"PIN 오류. ({remaining}회 남음)")
                    pin1.delete(0, "end")

    btn = tk.Button(inner, text="확인", command=on_confirm,
                    font=("Segoe UI", 11, "bold"),
                    bg="#1a5276", fg="white", activebackground="#2980b9",
                    activeforeground="white", relief="flat", cursor="hand2")
    btn.pack(fill="x", ipady=5, pady=(4, 0))

    if is_first_run:
        (pin2 or pin1).bind("<Return>", on_confirm)
    pin1.bind("<Return>", on_confirm)
    pin1.focus_set()

    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)
    dlg.mainloop()

    return result["ok"]


# ── 메인 UI ─────────────────────────────────────────────────────────────────

def main():
    import tkinter as tk
    from tkinter import ttk, messagebox
    from tools.bx import has_master_pin, migrate_all_to_v2, set_master_pin, derive_pin_key

    # PIN 인증
    if not show_pin_dialog():
        sys.exit(0)

    touch_activity()

    root = tk.Tk()
    root.title("BX Credential Manager")
    root.geometry("460x580")
    root.resizable(False, False)
    root.configure(bg="#1a1a2e")
    root.attributes("-topmost", True)

    ico_path = Path(__file__).resolve().parent / "bx_icon.ico"
    if ico_path.exists():
        try:
            root.iconbitmap(str(ico_path))
        except Exception:
            pass

    # ── 세션 타임아웃 감시 ─────────────────────────────────────────────────
    def check_timeout():
        if time.monotonic() - _last_activity > SESSION_TIMEOUT:
            messagebox.showwarning("세션 만료", f"{SESSION_TIMEOUT // 60}분 비활성화로 자동 잠금됩니다.")
            root.destroy()
            return
        root.after(10_000, check_timeout)

    root.after(10_000, check_timeout)

    def on_any_interaction(event=None):
        touch_activity()

    root.bind_all("<Key>", on_any_interaction)
    root.bind_all("<Button>", on_any_interaction)

    # ── 상태 표시 바 ───────────────────────────────────────────────────────
    is_pin_set = has_master_pin()
    enc_label  = "DPAPI + PIN 이중 암호화" if is_pin_set else "DPAPI 암호화 (PIN 미설정)"
    enc_color  = "#4caf50" if is_pin_set else "#ff9800"

    hdr_frame = tk.Frame(root, bg="#0d0d1a", pady=6)
    hdr_frame.pack(fill="x")
    tk.Label(hdr_frame, text="BX Credential Manager",
             font=("Segoe UI", 13, "bold"), fg="#e0e0e0", bg="#0d0d1a").pack()
    tk.Label(hdr_frame, text=f"[{enc_label}]",
             font=("Segoe UI", 9), fg=enc_color, bg="#0d0d1a").pack()

    frame = tk.Frame(root, bg="#1a1a2e")
    frame.pack(padx=30, fill="x", pady=(8, 0))

    # ── 서비스 선택 ────────────────────────────────────────────────────────
    tk.Label(frame, text="서비스 선택", font=("Segoe UI", 10),
             fg="#aaaaaa", bg="#1a1a2e", anchor="w").pack(fill="x")

    preset_names = [p[0] for p in PRESETS]
    combo = ttk.Combobox(frame, values=preset_names, state="readonly",
                         font=("Segoe UI", 10), width=38)
    combo.set(preset_names[0])
    combo.pack(pady=(2, 8), fill="x")

    custom_frame = tk.Frame(frame, bg="#1a1a2e")
    custom_lbl   = tk.Label(custom_frame, text="BX 키 이름", font=("Segoe UI", 10),
                             fg="#aaaaaa", bg="#1a1a2e", anchor="w")
    custom_entry = tk.Entry(custom_frame, width=38, font=("Segoe UI", 10),
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

    def sync_hash_check(event=None):
        idx = combo.current()
        hash_var.set(PRESETS[idx][2])

    combo.bind("<<ComboboxSelected>>", lambda e: (on_combo_change(e), sync_hash_check(e)))

    # ── 해시 체크박스 ──────────────────────────────────────────────────────
    hash_var = tk.BooleanVar(value=True)
    tk.Checkbutton(frame, text="pbkdf2 해시 저장 (비밀번호용)",
                   variable=hash_var, font=("Segoe UI", 9),
                   fg="#888888", bg="#1a1a2e", selectcolor="#16213e",
                   activebackground="#1a1a2e", activeforeground="#cccccc"
                   ).pack(anchor="w", pady=(5, 5))

    # ── 비밀번호 입력 ──────────────────────────────────────────────────────
    tk.Label(frame, text="새 값", font=("Segoe UI", 10),
             fg="#cccccc", bg="#1a1a2e", anchor="w").pack(fill="x", pady=(5, 0))
    pw1 = tk.Entry(frame, show="*", width=38, font=("Segoe UI", 11),
                   bg="#16213e", fg="white", insertbackground="white",
                   relief="flat", highlightthickness=1, highlightcolor="#0f3460")
    pw1.pack(fill="x", ipady=4, pady=(2, 5))

    tk.Label(frame, text="확인", font=("Segoe UI", 10),
             fg="#cccccc", bg="#1a1a2e", anchor="w").pack(fill="x")
    pw2 = tk.Entry(frame, show="*", width=38, font=("Segoe UI", 11),
                   bg="#16213e", fg="white", insertbackground="white",
                   relief="flat", highlightthickness=1, highlightcolor="#0f3460")
    pw2.pack(fill="x", ipady=4, pady=(2, 6))

    # ── 클립보드 알림 ──────────────────────────────────────────────────────
    clip_var = tk.StringVar()
    tk.Label(frame, textvariable=clip_var, font=("Segoe UI", 8),
             fg="#888888", bg="#1a1a2e", anchor="w").pack(fill="x")

    # ── 저장 버튼 ──────────────────────────────────────────────────────────
    def on_save():
        touch_activity()
        idx    = combo.current()
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

        store_val = pbkdf2_hash(p1) if hash_var.get() else p1
        if hash_var.get():
            assert verify(p1, store_val)

        if save_to_bx(bx_key, store_val):
            copy_to_clipboard(store_val)
            clear_clipboard_after(CLIPBOARD_CLEAR_AFTER)
            clip_var.set(f"클립보드 복사 완료 — {CLIPBOARD_CLEAR_AFTER}초 후 자동 삭제")
            svc_name = preset[0] if preset[1] else bx_key
            enc_info = "DPAPI+PIN 이중 암호화" if is_pin_set else "DPAPI 암호화"
            messagebox.showinfo(
                "저장 완료",
                f"{svc_name}\n\n"
                f"BX 저장 완료 ({enc_info})\n"
                f"클립보드 복사됨 ({CLIPBOARD_CLEAR_AFTER}초 후 자동 삭제)"
            )
            pw1.delete(0, "end")
            pw2.delete(0, "end")
            clip_var.set("")
        else:
            messagebox.showerror("오류", "BX 저장 실패")

    tk.Button(frame, text="저장", command=on_save,
              font=("Segoe UI", 11, "bold"), width=38,
              bg="#0f3460", fg="white", activebackground="#1a5276",
              activeforeground="white", relief="flat", cursor="hand2"
              ).pack(ipady=4)

    # ── 구분선 ─────────────────────────────────────────────────────────────
    tk.Frame(frame, bg="#333355", height=1).pack(fill="x", pady=(14, 10))

    # ── 서버 보안 + v2 마이그레이션 ────────────────────────────────────────
    tk.Label(frame, text="서버 보안 관리",
             font=("Segoe UI", 11, "bold"), fg="#e0e0e0", bg="#1a1a2e",
             anchor="w").pack(fill="x", pady=(0, 5))

    status_var = tk.StringVar()
    status_lbl = tk.Label(frame, textvariable=status_var,
                          font=("Segoe UI", 9), fg="#66bb6a", bg="#1a1a2e",
                          anchor="w", wraplength=380)
    status_lbl.pack(fill="x")

    def on_reset_blacklist():
        touch_activity()
        btn_reset.config(state="disabled", text="처리 중...")
        root.update_idletasks()
        ok, msg = reset_blacklist()
        status_var.set(f"{'[OK]' if ok else '[오류]'} {msg}")
        status_lbl.config(fg="#66bb6a" if ok else "#ef5350")
        btn_reset.config(state="normal", text="[서버] 접속차단 초기화 (IP Blacklist Reset)")

    btn_reset = tk.Button(frame,
                          text="[서버] 접속차단 초기화 (IP Blacklist Reset)",
                          command=on_reset_blacklist,
                          font=("Segoe UI", 10), width=38,
                          bg="#4a1942", fg="white", activebackground="#6a2462",
                          activeforeground="white", relief="flat", cursor="hand2")
    btn_reset.pack(ipady=3, pady=(5, 3))

    tk.Label(frame, text="* 반복 로그인 실패로 차단된 IP를 해제합니다",
             font=("Segoe UI", 8), fg="#555566", bg="#1a1a2e",
             anchor="w").pack(fill="x")

    # v2 마이그레이션 버튼 (PIN 설정된 경우만 표시)
    if is_pin_set and _session_pin_key is not None:
        def on_migrate():
            touch_activity()
            if not messagebox.askyesno("v2 재암호화",
                "기존 DPAPI 전용 항목을 모두 DPAPI+PIN 이중 암호화로 업그레이드합니다.\n계속하시겠습니까?"):
                return
            n = migrate_all_to_v2(_session_pin_key)
            status_var.set(f"[OK] {n}개 항목 v2 재암호화 완료")
            status_lbl.config(fg="#66bb6a")

        tk.Button(frame,
                  text="[보안] 기존 항목 v2 재암호화 (DPAPI+PIN)",
                  command=on_migrate,
                  font=("Segoe UI", 10), width=38,
                  bg="#1a3a1a", fg="#88cc88", activebackground="#2a5a2a",
                  activeforeground="white", relief="flat", cursor="hand2"
                  ).pack(ipady=3, pady=(8, 0))
        tk.Label(frame, text="* 기존 저장 항목에 PIN 레이어를 추가합니다 (1회만)",
                 font=("Segoe UI", 8), fg="#555566", bg="#1a1a2e",
                 anchor="w").pack(fill="x")

    root.bind("<Return>", lambda e: on_save())
    pw1.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()
