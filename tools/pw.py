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
    # ── 알파벳순 ────────────────────────────────────────────────────────────
    ("Admin API Key",                          "ADMIN_API_KEY",                 False),
    ("Admin Token (legacy)",                   "ADMIN_TOKEN",                   False),
    ("Anthropic API Key",                      "ANTHROPIC_API_KEY",             False),
    ("BRIDGE Admin Login Password",            "BRIDGE_ADMIN_LOGIN_PW",         True),
    ("BRIDGE Gmail SMTP App Password",         "BRIDGE_GMAIL_SMTP_APPKEY",      False),
    ("BRIDGE PII Encryption Key",              "BRIDGE_FIELD_KEY",              False),
    ("BRIDGE Webhook Secret",                  "BRIDGE_WEBHOOK_SECRET",         False),
    ("Craigslist gray Account Password",       "CRAIGSLIST_GRAY_ACCOUNT_PW",    False),
    ("Gemini Key — airelair00@gmail.com",      "GEMINI_KEY_4",                  False),
    ("Gemini Key — bridgejobkr@gmail.com",     "GEMINI_KEY_1",                  False),
    ("Gemini Key — coreabridge@gmail.com",     "GEMINI_KEY_2",                  False),
    ("Gemini Key — ferrari812fast@gmail.com",  "GEMINI_KEY_3",                  False),
    ("GitHub Personal Access Token",           "GIT_TK",                        False),
    ("Gmail App Password (bridgejobkr 이메일자동화)", "BRIDGEJOBKR_GMAIL_APPKEY", False),
    ("Google OAuth Client ID",                 "GOOGLE_CLIENT_ID",              False),
    ("Google OAuth Client Secret",             "GOOGLE_CLIENT_SECRET",          False),
    ("JWT Secret",                             "JWT_SECRET",                    False),
    ("Naver SMTP App Password (BRIDGE 발신)",  "BRIDGE_NAVER_SMTP_APPKEY",      False),
    ("Naver SMTP Password (보조)",             "NAVER_SMTP_PASS",               False),
    ("Naver bestpucca 블로그",                 "BESTPUCCA_NAVER_PW",            False),
    ("Naver Bridge 블로그 (bridgejob)",        "BRIDGE_NAVER_PW",               False),
    ("Naver 맛족도 블로그 (matjokdo)",         "MATJOKDO_NAVER_PW",             False),
    ("NextAuth Secret",                        "NEXTAUTH_SECRET",               False),
    ("Notion Integration Token",               "NOTION_TOKEN",                  False),
    ("Notion Page ID",                         "NOTION_PAGE_ID",                False),
    ("OpenRun Admin Secret",                   "OPENRUN_ADMIN_SECRET",          False),
    ("Render API Key (통합)",                  "RENDER_API_KEY",                False),
    ("Render API Token",                       "RENDER_API_TOKEN",              False),
    ("Render Service ID (bridge-api)",         "RENDER_SERVICE_ID",             False),
    ("Render Service ID (bridge-ads)",         "ADS_RENDER_SERVICE_ID",         False),
    ("Supabase DB Password",                   "SUPABASE_DB_PASSWORD",          False),
    ("Telegram Bot Token",                     "TELEGRAM_BOT_TOKEN",            False),
    ("Upload Sign Key",                        "UPLOAD_SIGN_KEY",               False),
    ("Vercel Access Token",                    "VERCEL_TOKEN",                  False),
    ("Webhook Secret",                         "WEBHOOK_SECRET",                False),
    # ── bridge_ads 광고 포털 ────────────────────────────────────────────────
    ("[ADS] CSRF Secret",                      "ADS_CSRF_SECRET",               False),
    ("[ADS] Field Encryption Key",             "ADS_FIELD_ENCRYPTION_KEY",      False),
    ("[ADS] Gmail App Password (SMTP)",        "ADS_SMTP_PASS",                 False),
    ("[ADS] Google OAuth Client ID",           "ADS_GOOGLE_CLIENT_ID",          False),
    ("[ADS] Google OAuth Client Secret",       "ADS_GOOGLE_CLIENT_SECRET",      False),
    ("[ADS] JWT Secret",                       "ADS_JWT_SECRET",                False),
    ("[ADS] OTP HMAC Secret",                  "ADS_OTP_HMAC_SECRET",           False),
    ("[ADS] PayPal Client ID",                 "ADS_PAYPAL_CLIENT_ID",          False),
    ("[ADS] PayPal Client Secret",             "ADS_PAYPAL_CLIENT_SECRET",      False),
    ("[ADS] PayPal Webhook ID",                "ADS_PAYPAL_WEBHOOK_ID",         False),
    ("직접 입력",                              "",                              False),
]


CLAUDEBLOG_DIR = Path(r"Q:\Claudework\ClaudeBlog")

GEMINI_ACCOUNTS = [
    ("GEMINI_KEY_1", "bridgejobkr@gmail.com"),
    ("GEMINI_KEY_2", "coreabridge@gmail.com"),
    ("GEMINI_KEY_3", "ferrari812fast@gmail.com"),
    ("GEMINI_KEY_4", "airelair00@gmail.com"),
]

# 저장 시 ClaudeBlog 자동 동기화 트리거 키
CLAUDEBLOG_SYNC_KEYS = {
    "BRIDGE_NAVER_PW", "MATJOKDO_NAVER_PW", "ANTHROPIC_API_KEY",
    "GEMINI_KEY_1", "GEMINI_KEY_2", "GEMINI_KEY_3", "GEMINI_KEY_4",
}

# bx 키 → Render 환경변수명 매핑 (저장 시 Render 자동 푸시 대상)
RENDER_SYNC_MAP = {
    "JWT_SECRET":           "JWT_SECRET",
    "BRIDGE_HMAC_KEY":      "BRIDGE_HMAC_KEY",
    "ANTHROPIC_API_KEY":    "ANTHROPIC_API_KEY",
    "TELEGRAM_BOT_TOKEN":   "TELEGRAM_BOT_TOKEN",
    "BRIDGE_FIELD_KEY":     "BRIDGE_FIELD_KEY",
    "BRIDGE_GMAIL_SMTP_APPKEY": "BRIDGE_GMAIL_SMTP_APPKEY",
    "ADMIN_API_KEY":            "ADMIN_API_KEY",
    "BRIDGE_ADMIN_LOGIN_PW":    "BRIDGE_ADMIN_LOGIN_PW",
    "WEBHOOK_SECRET":       "WEBHOOK_SECRET",
    # bridge_ads → Render bridge-ads 서비스
    "ADS_SMTP_PASS":              "SMTP_PASS",
    "ADS_GOOGLE_CLIENT_ID":       "GOOGLE_CLIENT_ID",
    "ADS_GOOGLE_CLIENT_SECRET":   "GOOGLE_CLIENT_SECRET",
    "ADS_PAYPAL_CLIENT_ID":       "PAYPAL_CLIENT_ID",
    "ADS_PAYPAL_CLIENT_SECRET":   "PAYPAL_CLIENT_SECRET",
    "ADS_PAYPAL_WEBHOOK_ID":      "PAYPAL_WEBHOOK_ID",
    "ADS_JWT_SECRET":             "JWT_SECRET",
    "ADS_CSRF_SECRET":            "CSRF_SECRET",
    "ADS_OTP_HMAC_SECRET":        "OTP_HMAC_SECRET",
    "ADS_FIELD_ENCRYPTION_KEY":   "FIELD_ENCRYPTION_KEY",
}


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


def sync_to_claudeblog() -> tuple[bool, str]:
    """bx에 저장된 값을 읽어 ClaudeBlog secrets.enc에 자동 반영."""
    try:
        sys.path.insert(0, str(CLAUDEBLOG_DIR))
        from encrypt_secrets import encrypt_programmatic

        updates = {}

        naver_pw = read_from_bx("BRIDGE_NAVER_PW")
        if naver_pw:
            updates["BRIDGE_NAVER_PW"] = naver_pw

        matjokdo_pw = read_from_bx("MATJOKDO_NAVER_PW")
        if matjokdo_pw:
            updates["MATJOKDO_NAVER_PW"] = matjokdo_pw

        anthropic = read_from_bx("ANTHROPIC_API_KEY")
        if anthropic:
            updates["ANTHROPIC_API_KEY"] = anthropic

        # Gemini 키 4개 → JSON 배열로 조합
        gemini_list = []
        for bx_key, account in GEMINI_ACCOUNTS:
            val = read_from_bx(bx_key)
            if val:
                gemini_list.append({"key": val, "account": account})
        if gemini_list:
            updates["GEMINI_KEYS"] = json.dumps(gemini_list)

        if not updates:
            return False, "동기화할 값이 없습니다.\n먼저 pw.py에서 값을 저장하세요."

        ok = encrypt_programmatic(updates)
        if ok:
            keys = list(updates.keys())
            gemini_count = len(gemini_list)
            return True, (
                f"ClaudeBlog 동기화 완료\n\n"
                f"반영된 항목: {', '.join(k for k in keys if k != 'GEMINI_KEYS')}\n"
                f"Gemini 키: {gemini_count}개\n\n"
                f"secrets.enc 업데이트됨"
            )
        return False, "encrypt_programmatic 실패"
    except Exception as e:
        return False, f"동기화 오류: {e}"


ADS_BX_KEYS = {k for k in RENDER_SYNC_MAP if k.startswith("ADS_")}


def _sync_one_render_service(api_token: str, service_id: str, key_filter, changed_key: str, changed_value: str) -> tuple[bool, str, list]:
    """단일 Render 서비스 동기화 공통 로직."""
    import urllib.request, urllib.error
    req = urllib.request.Request(
        f"https://api.render.com/v1/services/{service_id}/env-vars",
        headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        current = json.loads(resp.read().decode())
    env_dict = {item["envVar"]["key"]: item["envVar"]["value"] for item in current}
    updated = []
    for bx_key, render_key in RENDER_SYNC_MAP.items():
        if not key_filter(bx_key):
            continue
        val = read_from_bx(bx_key)
        if val and val != env_dict.get(render_key, ""):
            env_dict[render_key] = val
            updated.append(render_key)
    if changed_key in RENDER_SYNC_MAP and key_filter(changed_key) and changed_value:
        render_key = RENDER_SYNC_MAP[changed_key]
        env_dict[render_key] = changed_value
        if render_key not in updated:
            updated.append(render_key)
    if not updated:
        return True, "", []
    payload = json.dumps([{"key": k, "value": v} for k, v in env_dict.items()]).encode()
    req2 = urllib.request.Request(
        f"https://api.render.com/v1/services/{service_id}/env-vars",
        data=payload,
        headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(req2, timeout=15) as resp2:
        resp2.read()
    return True, "", updated


def sync_to_render(changed_key: str = "", changed_value: str = "") -> tuple[bool, str]:
    """bx에 저장된 값을 Render 환경변수에 자동 반영 (bridge-api + bridge-ads 분리)."""
    import urllib.error
    api_token = read_from_bx("RENDER_API_TOKEN")
    if not api_token:
        return None, ""
    msgs = []
    # ── bridge-api (ADS 제외)
    service_id = read_from_bx("RENDER_SERVICE_ID")
    if service_id:
        try:
            ok, _, updated = _sync_one_render_service(
                api_token, service_id,
                lambda k: k not in ADS_BX_KEYS,
                changed_key, changed_value,
            )
            if updated:
                msgs.append(f"bridge-api: {', '.join(updated)}")
        except urllib.error.HTTPError as e:
            return False, f"bridge-api Render 오류 ({e.code}): {e.reason}"
        except Exception as e:
            return False, f"bridge-api Render 오류: {e}"
    # ── bridge-ads (ADS_* 키만)
    ads_service_id = read_from_bx("ADS_RENDER_SERVICE_ID")
    if ads_service_id and any(k in ADS_BX_KEYS for k in ([changed_key] if changed_key else RENDER_SYNC_MAP)):
        try:
            ok, _, updated = _sync_one_render_service(
                api_token, ads_service_id,
                lambda k: k in ADS_BX_KEYS,
                changed_key, changed_value,
            )
            if updated:
                msgs.append(f"bridge-ads: {', '.join(updated)}")
        except urllib.error.HTTPError as e:
            return False, f"bridge-ads Render 오류 ({e.code}): {e.reason}"
        except Exception as e:
            return False, f"bridge-ads Render 오류: {e}"
    if not msgs:
        return True, "변경된 항목 없음 (Render와 동일)"
    return True, "Render 동기화 완료\n" + "\n".join(msgs) + "\n\n* Render Manual Deploy를 실행해야 적용됩니다."


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
    sys.path.insert(0, str(BASE_DIR))
    from tools.bx import has_master_pin, migrate_all_to_v2, set_master_pin, derive_pin_key

    # PIN 인증
    if not show_pin_dialog():
        sys.exit(0)

    touch_activity()

    root = tk.Tk()
    root.title("BX Credential Manager")
    root.geometry("540x820")
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
    tk.Label(frame, text="저장할 서비스 선택", font=("Segoe UI", 14),
             fg="white", bg="#1a1a2e", anchor="w").pack(fill="x", pady=(0, 4))

    preset_names = [p[0] for p in PRESETS]
    style = ttk.Style()
    style.configure("Big.TCombobox", padding=8)
    combo = ttk.Combobox(frame, values=preset_names, state="readonly",
                         font=("Segoe UI", 14), width=36,
                         style="Big.TCombobox")
    root.option_add("*TCombobox*Listbox.Font", ("Segoe UI", 13))
    combo.set(preset_names[0])
    combo.pack(pady=(2, 6), fill="x", ipady=8)

    # 선택된 서비스명 크게 표시
    selected_svc_var = tk.StringVar(value=preset_names[0])
    selected_svc_lbl = tk.Label(frame, textvariable=selected_svc_var,
                                font=("Segoe UI", 15),
                                fg="#4fc3f7", bg="#1a1a2e", anchor="w",
                                wraplength=420)
    selected_svc_lbl.pack(fill="x", pady=(0, 8))

    custom_frame = tk.Frame(frame, bg="#1a1a2e")
    custom_lbl   = tk.Label(custom_frame, text="BX 키 이름", font=("Segoe UI", 10),
                             fg="#aaaaaa", bg="#1a1a2e", anchor="w")
    custom_entry = tk.Entry(custom_frame, width=38, font=("Segoe UI", 10),
                            bg="#16213e", fg="white", insertbackground="white",
                            relief="flat", highlightthickness=1, highlightcolor="#0f3460")

    def on_combo_change(event=None):
        idx = combo.current()
        selected_svc_var.set(PRESETS[idx][0])
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

    # ── 해시 토글 (큼직한 ON/OFF 버튼, 상태 명확) ─────────────────────────
    hash_var = tk.BooleanVar(value=True)
    hash_info = tk.Label(frame,
                   text="해시 저장 (비밀번호만 ON / API 키·토큰은 OFF)",
                   font=("Segoe UI", 14), fg="white", bg="#1a1a2e", anchor="w")
    hash_info.pack(fill="x", pady=(8, 4))

    hash_btn = tk.Button(frame, text="", font=("Segoe UI", 22),
                          relief="raised", bd=4, cursor="hand2",
                          padx=30, pady=18, width=30)
    hash_btn.pack(fill="x", pady=(0, 8))

    def _update_hash_btn():
        if hash_var.get():
            hash_btn.config(text="✅  해시 저장  ON", bg="#00c853", fg="white",
                            activebackground="#00e676", activeforeground="white")
        else:
            hash_btn.config(text="⭕  해시 저장  OFF", bg="#424242", fg="#eeeeee",
                            activebackground="#616161", activeforeground="white")

    def _toggle_hash():
        hash_var.set(not hash_var.get())
        _update_hash_btn()

    hash_btn.config(command=_toggle_hash)
    _update_hash_btn()

    # 깜박임 — OFF 일 때 배경에 노란 깜박임 (API 키 실수 방지)
    _blink_state = {"on": True}
    def _blink_hash():
        if not hash_var.get():  # OFF 상태일 때만 깜박임
            if _blink_state["on"]:
                hash_btn.config(bg="#ffeb3b", fg="#000000")
            else:
                hash_btn.config(bg="#424242", fg="#eeeeee")
            _blink_state["on"] = not _blink_state["on"]
        root.after(600, _blink_hash)
    root.after(300, _blink_hash)

    # ── 비밀번호 / 값 입력 ────────────────────────────────────────────────
    pw1_label = tk.Label(frame, text="비밀번호 / 값 입력", font=("Segoe UI", 13),
             fg="white", bg="#1a1a2e", anchor="w")
    pw1_label.pack(fill="x", pady=(6, 2))
    pw1 = tk.Entry(frame, show="*", width=38, font=("Segoe UI", 14),
                   bg="#16213e", fg="white", insertbackground="white",
                   relief="flat", highlightthickness=1, highlightcolor="#0f3460")
    pw1.pack(fill="x", ipady=8, pady=(0, 6))

    tk.Label(frame, text="비밀번호 재확인", font=("Segoe UI", 13),
             fg="white", bg="#1a1a2e", anchor="w").pack(fill="x", pady=(0, 2))
    pw2 = tk.Entry(frame, show="*", width=38, font=("Segoe UI", 14),
                   bg="#16213e", fg="white", insertbackground="white",
                   relief="flat", highlightthickness=1, highlightcolor="#0f3460")
    pw2.pack(fill="x", ipady=8, pady=(0, 8))

    # ── 클립보드 알림 ──────────────────────────────────────────────────────
    clip_var = tk.StringVar()
    tk.Label(frame, textvariable=clip_var, font=("Segoe UI", 8),
             fg="#888888", bg="#1a1a2e", anchor="w").pack(fill="x")

    # ── 저장 버튼 ──────────────────────────────────────────────────────────
    def _auto_sync_claudeblog():
        status_var.set("ClaudeBlog 자동 동기화 중...")
        status_lbl.config(fg="#ff9800")
        root.update_idletasks()
        ok, msg = sync_to_claudeblog()
        first_line = msg.split('\n')[0]
        status_var.set(f"{'[동기화 완료]' if ok else '[동기화 오류]'} {first_line}")
        status_lbl.config(fg="#66bb6a" if ok else "#ef5350")

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
            # ClaudeBlog 자동 동기화 (관련 키인 경우)
            if bx_key in CLAUDEBLOG_SYNC_KEYS:
                root.after(100, _auto_sync_claudeblog)
            # Render 자동 동기화 (관련 키인 경우)
            if bx_key in RENDER_SYNC_MAP:
                raw_val = p1  # 해시 전 원본값
                root.after(200, lambda v=raw_val, k=bx_key: _auto_sync_render(k, v))
        else:
            messagebox.showerror("오류", "BX 저장 실패")

    tk.Button(frame, text="저장", command=on_save,
              font=("Segoe UI", 16), width=38,
              bg="#0f3460", fg="white", activebackground="#1a5276",
              activeforeground="white", relief="flat", cursor="hand2"
              ).pack(ipady=10, pady=(4, 2))

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

    # ── ClaudeBlog 동기화 버튼 ─────────────────────────────────────────────
    def on_sync_claudeblog():
        touch_activity()
        btn_sync.config(state="disabled", text="동기화 중...")
        root.update_idletasks()
        ok, msg = sync_to_claudeblog()
        status_var.set(f"{'[완료]' if ok else '[오류]'} {msg.split(chr(10))[0]}")
        status_lbl.config(fg="#66bb6a" if ok else "#ef5350")
        btn_sync.config(state="normal", text="[ClaudeBlog] 시크릿 동기화 (Naver/Anthropic/Gemini)")
        if ok:
            messagebox.showinfo("동기화 완료", msg)

    btn_sync = tk.Button(frame,
                         text="[ClaudeBlog] 시크릿 동기화 (Naver/Anthropic/Gemini)",
                         command=on_sync_claudeblog,
                         font=("Segoe UI", 10), width=38,
                         bg="#1a3a3a", fg="#88cccc", activebackground="#2a5a5a",
                         activeforeground="white", relief="flat", cursor="hand2")
    btn_sync.pack(ipady=3, pady=(5, 3))
    tk.Label(frame, text="* bx에 저장된 값을 ClaudeBlog secrets.enc에 자동 반영",
             font=("Segoe UI", 8), fg="#555566", bg="#1a1a2e",
             anchor="w").pack(fill="x")

    # ── Render 동기화 버튼 ─────────────────────────────────────────────────
    def on_sync_render():
        touch_activity()
        btn_render.config(state="disabled", text="Render 동기화 중...")
        root.update_idletasks()
        ok, msg = sync_to_render()
        btn_render.config(state="normal", text="[Render] 환경변수 동기화 (JWT/HMAC/API Keys)")
        if ok is None:
            messagebox.showwarning("Render 토큰 필요",
                "RENDER_API_TOKEN 과 RENDER_SERVICE_ID를\n먼저 pw.py에서 저장하세요.\n\n"
                "Render 대시보드 → Account Settings → API Keys")
            return
        status_var.set(f"{'[완료]' if ok else '[오류]'} {msg.split(chr(10))[0]}")
        status_lbl.config(fg="#66bb6a" if ok else "#ef5350")
        if ok:
            messagebox.showinfo("Render 동기화 완료", msg)

    btn_render = tk.Button(frame,
                           text="[Render] 환경변수 동기화 (JWT/HMAC/API Keys)",
                           command=on_sync_render,
                           font=("Segoe UI", 10), width=38,
                           bg="#1a2a3a", fg="#88aacc", activebackground="#2a4a6a",
                           activeforeground="white", relief="flat", cursor="hand2")
    btn_render.pack(ipady=3, pady=(5, 3))
    tk.Label(frame, text="* bx 값을 Render 서버 환경변수에 자동 반영 (API Token 필요)",
             font=("Segoe UI", 8), fg="#555566", bg="#1a1a2e",
             anchor="w").pack(fill="x")

    # _auto_sync_render 헬퍼
    def _auto_sync_render(bx_key: str, raw_value: str):
        ok, msg = sync_to_render(bx_key, raw_value)
        if ok is None:  # 토큰 미설정 — 조용히 스킵
            return
        first = msg.split("\n")[0]
        status_var.set(f"{'[Render 동기화 완료]' if ok else '[Render 오류]'} {first}")
        status_lbl.config(fg="#66bb6a" if ok else "#ef5350")

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
