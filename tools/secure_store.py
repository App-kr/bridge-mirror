"""
secure_store.py — AES-256-GCM 암호화 시크릿 저장소
=====================================================
security_vault.py 의 암호화 엔진을 재사용하여
민감한 키-값 쌍을 암호화된 JSON 파일에 저장.

저장 위치: .secrets.enc.json (gitignore 대상)
암호화 키: .env BRIDGE_FIELD_KEY (SHA-256 → 32byte)

사용법:
  python tools/secure_store.py set  RENDER_DEPLOY_HOOK "https://api.render.com/deploy/..."
  python tools/secure_store.py get  RENDER_DEPLOY_HOOK
  python tools/secure_store.py list
  python tools/secure_store.py delete RENDER_DEPLOY_HOOK
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from security_vault import encrypt_field, decrypt_field  # noqa: E402

STORE_PATH = PROJECT_ROOT / ".secrets.enc.json"


def _load() -> dict:
    if not STORE_PATH.exists():
        return {}
    try:
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict):
    STORE_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def store_set(key: str, value: str):
    data = _load()
    data[key] = encrypt_field(value)
    _save(data)
    print(f"[secure_store] '{key}' encrypted and saved ({len(data[key])} chars)")


def store_get(key: str) -> str:
    data = _load()
    enc = data.get(key)
    if enc is None:
        print(f"[secure_store] '{key}' not found", file=sys.stderr)
        sys.exit(1)
    return decrypt_field(enc)


def store_list():
    data = _load()
    if not data:
        print("[secure_store] (empty)")
        return
    for k, v in data.items():
        print(f"  {k} = [encrypted, {len(v)} chars]")


def store_delete(key: str):
    data = _load()
    if key in data:
        del data[key]
        _save(data)
        print(f"[secure_store] '{key}' deleted")
    else:
        print(f"[secure_store] '{key}' not found")


def main():
    if len(sys.argv) < 2:
        print("Usage: python secure_store.py <set|get|list|delete> [key] [value]")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "set" and len(sys.argv) >= 4:
        store_set(sys.argv[2], sys.argv[3])
    elif cmd == "get" and len(sys.argv) >= 3:
        val = store_get(sys.argv[2])
        print(val)
    elif cmd == "list":
        store_list()
    elif cmd == "delete" and len(sys.argv) >= 3:
        store_delete(sys.argv[2])
    else:
        print("Usage: python secure_store.py <set|get|list|delete> [key] [value]")
        sys.exit(1)


if __name__ == "__main__":
    main()
