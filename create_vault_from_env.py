#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BRIDGE Craigslist RPA — Vault Auto-Create from account*.env
============================================================
account1~4.env 파일에서 자격증명을 읽어 .rpa_vault.json 자동 생성.
ENC: 암호화된 비밀번호는 .bridge.key로 자동 복호화.

사용법:
  python create_vault_from_env.py         # 자동 생성 (계정 1~4)
  python create_vault_from_env.py --show  # 생성 후 계정 목록 표시
"""

import io, json, sys, os
from pathlib import Path

# UTF-8 강제
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
VAULT_FILE = BASE_DIR / ".rpa_vault.json"

# account1→gray, account2→green, account3→brown, account4→purple
ACCOUNT_MAP = {
    "account1": "gray",
    "account2": "green",
    "account3": "brown",
    "account4": "purple",
}


def decrypt_password(enc_str: str) -> str:
    """ENC: Fernet 복호화. 평문이면 그대로 반환."""
    if not enc_str.startswith("ENC:"):
        return enc_str
    try:
        from crypto_util import decrypt_value
        return decrypt_value(enc_str)
    except ImportError:
        print("[ERROR] crypto_util.py 없음")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 복호화 실패: {e}")
        print("  .bridge.key 파일이 있는지 확인하세요.")
        sys.exit(1)


def read_env_file(env_path: Path) -> dict:
    """env 파일 파싱 → dict 반환"""
    data = {}
    if not env_path.exists():
        return data
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        data[key.strip()] = val.strip()
    return data


def main():
    show = "--show" in sys.argv

    print("\n[BRIDGE] Vault Auto-Create from account*.env")
    print("=" * 50)

    # .bridge.key 확인
    key_path = BASE_DIR / ".bridge.key"
    if not key_path.exists():
        print(f"[ERROR] .bridge.key 없음: {key_path}")
        print("  crypto_util.py setup 실행 또는 키 파일 복원 필요")
        sys.exit(1)

    vault = {}
    found = 0

    for account_id, color in ACCOUNT_MAP.items():
        env_path = BASE_DIR / f"{account_id}.env"
        env_data = read_env_file(env_path)

        if not env_data:
            print(f"  [{account_id}→{color}] 파일 없음: {env_path.name} — SKIP")
            continue

        email = env_data.get("CRAIGSLIST_EMAIL", "")
        raw_pw = env_data.get("CRAIGSLIST_PASSWORD", "")

        if not email or not raw_pw:
            print(f"  [{account_id}→{color}] EMAIL 또는 PASSWORD 없음 — SKIP")
            continue

        password = decrypt_password(raw_pw)

        vault[f"{color}_email"] = email
        vault[f"{color}_password"] = password

        masked = password[:4] + "*" * max(0, len(password) - 4)
        print(f"  [{account_id}→{color}] {email}  pw={masked}")
        found += 1

    if not vault:
        print("\n[ERROR] 사용 가능한 계정 없음. account*.env 파일을 확인하세요.")
        sys.exit(1)

    # vault 저장
    with open(VAULT_FILE, "w", encoding="utf-8") as f:
        json.dump(vault, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] .rpa_vault.json 생성 완료 ({found}개 계정)")
    print(f"     경로: {VAULT_FILE}")

    if show:
        print("\n[VAULT 내용]")
        for k, v in vault.items():
            if "password" in k:
                print(f"  {k}: {v[:4]}{'*'*max(0,len(v)-4)}")
            else:
                print(f"  {k}: {v}")

    print("\n[다음 단계]")
    print("  python craigslist_auto_rpa.py --dry-run --limit 1")
    print("  python craigslist_auto_rpa.py --account gray --limit 1")


if __name__ == "__main__":
    main()
