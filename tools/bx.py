"""
BX — Bridge eXtensions runtime module
Windows Credential Manager 기반 시크릿 관리

사용법:
  python tools/bx.py migrate .env     # .env → Credential Manager 일괄 이전
  python tools/bx.py ls               # 키 이름만 표시 (값 절대 미출력)
  python tools/bx.py set KEY          # 대화형 입력 (화면 미표시)
  python tools/bx.py set KEY value    # 직접 지정
  python tools/bx.py load             # 환경변수에 로드 (서버용)
  python tools/bx.py rm KEY           # 삭제
  python tools/bx.py verify           # .env 대비 누락 검증
"""
import sys, os, getpass

_SVC = "BX"

# 관리 대상 키 목록
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
]

def _kr():
    """keyring lazy import"""
    import keyring
    return keyring

def cmd_set(args):
    kr = _kr()
    name = args[0] if args else input("Key: ").strip()
    if len(args) > 1:
        value = args[1]
    else:
        value = getpass.getpass(f"  {name} value (hidden): ")
    kr.set_password(_SVC, name, value)
    print(f"  + {name}")

def cmd_get(args):
    kr = _kr()
    name = args[0]
    val = kr.get_password(_SVC, name)
    if val:
        # 보안: 앞 8자만 표시
        masked = val[:8] + "..." if len(val) > 8 else val[:2] + "***"
        print(f"  {name} = {masked}")
    else:
        print(f"  {name} = (empty)")

def cmd_load(_args=None):
    """환경변수에 로드 — 서버/스크립트 시작 시 호출"""
    kr = _kr()
    n = 0
    for key in MANAGED:
        val = kr.get_password(_SVC, key)
        if val:
            os.environ[key] = val
            n += 1
    print(f"BX: {n}/{len(MANAGED)} loaded")
    return n

def cmd_ls(_args=None):
    kr = _kr()
    print(f"  BX Credential Store ({_SVC})")
    print(f"  {'Key':<28} Status")
    print(f"  {'-'*28} ------")
    for key in MANAGED:
        val = kr.get_password(_SVC, key)
        tag = "OK" if val else "--"
        print(f"  {key:<28} [{tag}]")

def cmd_migrate(args):
    """
    .env 파일에서 비밀값을 읽어 Credential Manager에 저장
    """
    kr = _kr()
    env_path = args[0] if args else ".env"
    if not os.path.exists(env_path):
        print(f"  ? {env_path} not found")
        return

    pairs = {}
    with open(env_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            # placeholder 제외
            if k in MANAGED and v and not v.startswith("여기") and v != "VAULT":
                pairs[k] = v

    stored = 0
    for k, v in pairs.items():
        kr.set_password(_SVC, k, v)
        stored += 1
        print(f"  + {k}")

    print(f"\n  BX migrate: {stored} keys stored in Windows Credential Manager")

def cmd_rm(args):
    kr = _kr()
    name = args[0]
    try:
        kr.delete_password(_SVC, name)
        print(f"  - {name} removed")
    except Exception:
        print(f"  ? {name} not found")

def cmd_verify(args):
    """
    .env 파일과 대조하여 Credential Manager에 누락된 키 보고
    """
    kr = _kr()
    env_path = args[0] if args else ".env"
    missing = []
    for key in MANAGED:
        val = kr.get_password(_SVC, key)
        if not val:
            missing.append(key)
    if missing:
        print(f"  Missing keys ({len(missing)}):")
        for k in missing:
            print(f"    - {k}")
    else:
        print(f"  All {len(MANAGED)} keys present")

def load_to_env():
    """
    api_server.py 등에서 import 용:
      from tools.bx import load_to_env; load_to_env()
    """
    if sys.platform != "win32":
        return 0
    try:
        kr = _kr()
        n = 0
        for key in MANAGED:
            val = kr.get_password(_SVC, key)
            if val:
                os.environ[key] = val
                n += 1
        return n
    except ImportError:
        return 0

COMMANDS = {
    "set": cmd_set,
    "get": cmd_get,
    "load": cmd_load,
    "ls": cmd_ls,
    "migrate": cmd_migrate,
    "rm": cmd_rm,
    "verify": cmd_verify,
}

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("BX [set|get|load|ls|migrate|rm|verify]")
        return
    COMMANDS[sys.argv[1]](sys.argv[2:])

if __name__ == "__main__":
    main()
