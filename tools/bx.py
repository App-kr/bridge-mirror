r"""
BX — Bridge eXtensions credential manager
pip install 필요 없음 — Python 표준 라이브러리 + Windows DPAPI만 사용

== 다른 AI(Gemini·GPT 등)도 이 파일을 읽고 그대로 사용 가능 ==

사용법 (어떤 Python이든 OK):
  python tools/bx.py ls                # 키 이름만 표시 (값 절대 미출력)
  python tools/bx.py set KEY           # 대화형 입력 (화면 미표시)
  python tools/bx.py set KEY value     # 직접 지정
  python tools/bx.py load              # 환경변수에 로드 (서버 시작용)
  python tools/bx.py get KEY           # 앞 8자만 마스킹 출력
  python tools/bx.py rm KEY            # 삭제
  python tools/bx.py verify            # 누락 키 확인
  python tools/bx.py export-env        # .env 복원용 (긴급 시)

저장 위치: Q:\Claudework\bridge base\.bx\  (gitignored, DPAPI 암호화)
암호화: Windows DPAPI — 현재 Windows 사용자 계정에 바인딩 (다른 계정 복호화 불가)
의존성: 없음 (ctypes + os + hashlib 만 사용)
"""
import sys
import os
import json
import hashlib
import hmac
import struct
import getpass
import ctypes
import ctypes.wintypes

# ── 설정 ────────────────────────────────────────────────────────────────────
_BX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".bx")

MANAGED = [
    # ── BRIDGE 핵심 ────────────────────────────────────────
    "BRIDGE_ADMIN_LOGIN_PW",          # 관리자 페이지 로그인
    "ADMIN_API_KEY",                  # 관리자 API 키
    "JWT_SECRET",                     # JWT 서명 키
    "BRIDGE_FIELD_KEY",               # DB PII 암호화 키
    "WEBHOOK_SECRET",                 # Webhook 서명
    "BRIDGE_WEBHOOK_SECRET",          # BRIDGE Webhook 서명 (보조)
    "UPLOAD_SIGN_KEY",                # 파일 업로드 서명 키
    # ── 이메일 ────────────────────────────────────────────
    "BRIDGEJOBKR_GMAIL_APPKEY",       # bridgejobkr@gmail.com 이메일 자동화 앱 비밀번호
    "BRIDGE_GMAIL_SMTP_APPKEY",       # BRIDGE 발신 Gmail SMTP 앱 비밀번호
    "BRIDGE_NAVER_SMTP_APPKEY",       # 네이버 메일 SMTP 앱 비밀번호
    "NAVER_SMTP_PASS",                # 네이버 SMTP 보조
    # ── 외부 서비스 ───────────────────────────────────────
    "TELEGRAM_BOT_TOKEN",             # 텔레그램 알림 봇
    "ANTHROPIC_API_KEY",              # Claude API
    "GEMINI_KEYS_JSON",               # Gemini API 키 목록
    "RENDER_API_KEY",                 # Render 배포 API
    "CRAIGSLIST_GRAY_ACCOUNT_PW",     # Craigslist gray 계정 비밀번호
    # ── bridge_ads 광고 포털 ──────────────────────────────
    "ADS_SMTP_PASS",
    "ADS_GOOGLE_CLIENT_ID",
    "ADS_GOOGLE_CLIENT_SECRET",
    "ADS_PAYPAL_CLIENT_ID",
    "ADS_PAYPAL_CLIENT_SECRET",
    "ADS_PAYPAL_WEBHOOK_ID",
    "ADS_JWT_SECRET",
    "ADS_CSRF_SECRET",
    "ADS_OTP_HMAC_SECRET",
    "ADS_FIELD_ENCRYPTION_KEY",
    "ADS_RENDER_SERVICE_ID",
]

# ── Windows DPAPI (ctypes, 설치 불필요) ─────────────────────────────────────
class _BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD),
                 ("pbData", ctypes.POINTER(ctypes.c_char))]

_crypt32 = ctypes.windll.crypt32
_kernel32 = ctypes.windll.kernel32

def _encrypt(data: bytes) -> bytes:
    bi = _BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data, len(data)),
                                       ctypes.POINTER(ctypes.c_char)))
    bo = _BLOB()
    if not _crypt32.CryptProtectData(ctypes.byref(bi), None, None, None, None, 0, ctypes.byref(bo)):
        raise OSError("DPAPI encrypt failed")
    out = ctypes.string_at(bo.pbData, bo.cbData)
    _kernel32.LocalFree(bo.pbData)
    return out

def _decrypt(data: bytes) -> bytes:
    bi = _BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data, len(data)),
                                       ctypes.POINTER(ctypes.c_char)))
    bo = _BLOB()
    if not _crypt32.CryptUnprotectData(ctypes.byref(bi), None, None, None, None, 0, ctypes.byref(bo)):
        raise OSError("DPAPI decrypt failed")
    out = ctypes.string_at(bo.pbData, bo.cbData)
    _kernel32.LocalFree(bo.pbData)
    return out

# ── 파일 I/O (파일명 = SHA256 해시, 내용 = DPAPI 암호화) ───────────────────
def _path(name: str) -> str:
    h = hashlib.sha256(name.encode()).hexdigest()[:16]
    return os.path.join(_BX_DIR, h)

def _ensure_dir():
    os.makedirs(_BX_DIR, exist_ok=True)

def _store(name: str, value: str):
    _ensure_dir()
    enc = _encrypt(value.encode("utf-8"))
    with open(_path(name), "wb") as f:
        f.write(enc)

def _read(name: str):
    p = _path(name)
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        enc = f.read()
    return _decrypt(enc).decode("utf-8")

def _delete(name: str):
    p = _path(name)
    if os.path.exists(p):
        os.remove(p)
        return True
    return False

# ── CLI 명령어 ──────────────────────────────────────────────────────────────
def cmd_set(args):
    name = args[0] if args else input("Key: ").strip()
    if len(args) > 1:
        value = args[1]
    else:
        value = getpass.getpass(f"  {name} (hidden): ")
    _store(name, value)
    if name not in MANAGED:
        MANAGED.append(name)
    print(f"  + {name}")

def cmd_get(args):
    name = args[0]
    val = _read(name)
    if val:
        masked = val[:8] + "..." if len(val) > 8 else val[:2] + "***"
        print(f"  {name} = {masked}")
    else:
        print(f"  {name} = (empty)")

def cmd_load(_args=None):
    n = 0
    for key in MANAGED:
        val = _read(key)
        if val:
            os.environ[key] = val
            n += 1
    print(f"BX: {n}/{len(MANAGED)} loaded")
    return n

def cmd_ls(_args=None):
    print(f"  BX Credential Store (DPAPI)")
    print(f"  {'Key':<28} Status")
    print(f"  {'-'*28} ------")
    for key in MANAGED:
        val = _read(key)
        tag = "OK" if val else "--"
        print(f"  {key:<28} [{tag}]")

def cmd_rm(args):
    name = args[0]
    if _delete(name):
        print(f"  - {name} removed")
    else:
        print(f"  ? {name} not found")

def cmd_verify(_args=None):
    missing = [k for k in MANAGED if not _read(k)]
    if missing:
        print(f"  Missing ({len(missing)}):")
        for k in missing:
            print(f"    - {k}")
    else:
        print(f"  All {len(MANAGED)} keys OK")

def cmd_export_env(args):
    """긴급 시 .env 복원용 (화면 출력 없이 파일 생성)"""
    out = args[0] if args else os.path.join(os.path.dirname(_BX_DIR), ".env.restored")
    lines = []
    for key in MANAGED:
        val = _read(key)
        if val and key != "GEMINI_KEYS_JSON":
            lines.append(f"{key}={val}")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Exported {len(lines)} keys -> {out}")
    print(f"  WARNING: delete this file after use!")

def cmd_import_json(args):
    """JSON 파일에서 일괄 import (마이그레이션용)"""
    path = args[0]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    n = 0
    for k, v in data.items():
        _store(k, v)
        n += 1
        print(f"  + {k}")
    print(f"  Imported {n} keys")

# ── PIN 2중 암호화 (v2) — DPAPI + PIN 파생 키 ──────────────────────────────
_V2_MAGIC      = b"BXv2"
_PIN_HASH_FILE = os.path.join(_BX_DIR, ".pinlock")
_KEY_SALT_FILE = os.path.join(_BX_DIR, ".keysalt")


def _get_or_create_key_salt() -> bytes:
    """설치별 고유 salt — .bx 디렉터리와 함께 이동 가능"""
    if os.path.exists(_KEY_SALT_FILE):
        with open(_KEY_SALT_FILE, "rb") as f:
            return f.read()
    salt = os.urandom(32)
    _ensure_dir()
    with open(_KEY_SALT_FILE, "wb") as f:
        f.write(salt)
    return salt


def _stream_cipher(key: bytes, nonce: bytes, length: int) -> bytes:
    """HMAC-SHA256 기반 스트림 암호 (외부 라이브러리 불필요)"""
    ks, counter = b"", 0
    while len(ks) < length:
        ks += hmac.new(key, nonce + struct.pack(">Q", counter), "sha256").digest()
        counter += 1
    return ks[:length]


def _pin_encrypt(data: bytes, pin_key: bytes) -> bytes:
    """PIN 키로 암호화: BXv2 magic + nonce(16) + MAC(32) + ciphertext"""
    nonce = os.urandom(16)
    ks    = _stream_cipher(pin_key, nonce, len(data))
    ct    = bytes(a ^ b for a, b in zip(data, ks))
    mac   = hmac.new(pin_key, nonce + ct, "sha256").digest()
    return _V2_MAGIC + nonce + mac + ct


def _pin_decrypt(data: bytes, pin_key: bytes) -> bytes:
    """PIN 키로 복호화 + MAC 검증 (MAC 불일치 → 즉시 오류)"""
    if not data.startswith(_V2_MAGIC):
        raise ValueError("v2 포맷 아님")
    body          = data[4:]
    nonce, mac, ct = body[:16], body[16:48], body[48:]
    expected = hmac.new(pin_key, nonce + ct, "sha256").digest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError("PIN 오류 또는 데이터 변조")
    ks = _stream_cipher(pin_key, nonce, len(ct))
    return bytes(a ^ b for a, b in zip(ct, ks))


def set_master_pin(pin: str):
    """마스터 PIN을 PBKDF2-SHA256 (600k iterations) 으로 해시 저장"""
    _ensure_dir()
    salt  = os.urandom(16).hex()
    iters = 600_000
    dk    = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt.encode(), iters)
    with open(_PIN_HASH_FILE, "w") as f:
        json.dump({"salt": salt, "iters": iters, "dk": dk.hex(), "v": 1}, f)


def verify_master_pin(pin: str) -> bool:
    """PIN 검증. PIN 미설정 시 항상 True 반환."""
    if not os.path.exists(_PIN_HASH_FILE):
        return True
    with open(_PIN_HASH_FILE) as f:
        d = json.load(f)
    dk = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), d["salt"].encode(), d["iters"])
    return hmac.compare_digest(dk.hex(), d["dk"])


def has_master_pin() -> bool:
    return os.path.exists(_PIN_HASH_FILE)


def derive_pin_key(pin: str) -> bytes:
    """PIN → 32바이트 암호화 키 파생 (PBKDF2, 300k iterations, 설치별 salt)"""
    salt = _get_or_create_key_salt()
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 300_000, dklen=32)


def _store_v2(name: str, value: str, pin_key: bytes):
    """v2 이중 암호화: PIN → DPAPI 순서로 래핑"""
    _ensure_dir()
    pin_enc  = _pin_encrypt(value.encode("utf-8"), pin_key)
    dpapi_enc = _encrypt(pin_enc)
    with open(_path(name), "wb") as f:
        f.write(dpapi_enc)


def _read_auto(name: str, pin_key: bytes | None = None) -> str | None:
    """v1(DPAPI 전용) / v2(DPAPI+PIN) 자동 판별 후 복호화"""
    p = _path(name)
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        enc = f.read()
    dpapi_dec = _decrypt(enc)
    if dpapi_dec.startswith(_V2_MAGIC):
        if pin_key is None:
            raise ValueError("v2 항목은 PIN 키 필요")
        return _pin_decrypt(dpapi_dec, pin_key).decode("utf-8")
    return dpapi_dec.decode("utf-8")


def migrate_all_to_v2(pin_key: bytes) -> int:
    """기존 v1(DPAPI 전용) 항목을 전부 v2로 재암호화. 완료 건수 반환."""
    migrated = 0
    for key in MANAGED:
        try:
            p = _path(key)
            if not os.path.exists(p):
                continue
            with open(p, "rb") as f:
                raw = f.read()
            dpapi_dec = _decrypt(raw)
            if dpapi_dec.startswith(_V2_MAGIC):
                continue  # 이미 v2
            val = dpapi_dec.decode("utf-8")
            _store_v2(key, val, pin_key)
            migrated += 1
        except Exception:
            pass
    return migrated


# ── api_server.py / main.py 에서 import 용 ─────────────────────────────────
def load_to_env():
    """
    사용법:
      from tools.bx import load_to_env; load_to_env()
    Windows에서만 동작, Linux/Mac은 자동 skip
    """
    if sys.platform != "win32":
        return 0
    try:
        n = 0
        for key in MANAGED:
            val = _read(key)
            if val:
                os.environ[key] = val
                n += 1
        return n
    except Exception:
        return 0

# ── Gemini keys 전용 헬퍼 ───────────────────────────────────────────────────
def get_gemini_keys() -> list:
    """
    사용법 (어떤 AI/스크립트에서든):
      from tools.bx import get_gemini_keys
      keys = get_gemini_keys()  # [{"name":"스칼렛","key":"AIzaSy..."},...]
    """
    raw = _read("GEMINI_KEYS_JSON")
    if raw:
        return json.loads(raw)
    return []

# ── CLI 라우터 ──────────────────────────────────────────────────────────────
COMMANDS = {
    "set": cmd_set,
    "get": cmd_get,
    "load": cmd_load,
    "ls": cmd_ls,
    "rm": cmd_rm,
    "verify": cmd_verify,
    "export-env": cmd_export_env,
    "import-json": cmd_import_json,
}

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("BX — credential manager (DPAPI, no install needed)")
        print()
        print("  python tools/bx.py ls              # list keys")
        print("  python tools/bx.py set KEY          # store (hidden input)")
        print("  python tools/bx.py set KEY value    # store directly")
        print("  python tools/bx.py load             # load to env vars")
        print("  python tools/bx.py get KEY          # peek (masked)")
        print("  python tools/bx.py rm KEY           # delete")
        print("  python tools/bx.py verify           # check missing")
        print("  python tools/bx.py export-env       # emergency .env restore")
        print("  python tools/bx.py import-json F    # bulk import from JSON")
        return
    COMMANDS[sys.argv[1]](sys.argv[2:])

if __name__ == "__main__":
    main()
