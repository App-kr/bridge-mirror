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
import getpass
import ctypes
import ctypes.wintypes

# ── 설정 ────────────────────────────────────────────────────────────────────
_BX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".bx")

MANAGED = [
    "ADMIN_PASSWORD",
    "ADMIN_API_KEY",
    "JWT_SECRET",
    "CRAIGSLIST_PASSWORD",
    "WEBHOOK_SECRET",
    "GMAIL_APP_PASSWORD",
    "NAVER_APP_PASSWORD",
    "NAVER_SMTP_PASS",
    "TELEGRAM_BOT_TOKEN",
    "BRIDGE_FIELD_KEY",
    "ANTHROPIC_API_KEY",
    "BRIDGE_SMTP_PASS",
    "UPLOAD_SIGN_KEY",
    "BRIDGE_WEBHOOK_SECRET",
    "GEMINI_KEYS_JSON",
    "RENDER_API_KEY",
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
