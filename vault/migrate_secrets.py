"""
BRIDGE Vault Migration Tool
=============================
.env 평문 비밀번호 -> 볼트 이전 자동화

사용법:
  vault.bat 실행 -> [1] init -> passphrases 설정
  이후 이 스크립트 실행:
    "Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 vault/migrate_secrets.py

동작:
  1. .env에서 평문 비밀번호 키 목록 표시
  2. 확인 후 각 값을 볼트에 이중 암호화 저장
  3. .env 원본을 VAULT:참조로 교체
  4. .env.bak 백업 생성
"""

import sys
import os
import getpass
import shutil
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vault_core import SecretVault

VAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ENV_FILE  = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

# Keys that contain real secrets (not paths, not hashed values)
SENSITIVE_KEYS = [
    "CRAIGSLIST_PASSWORD",
    "GMAIL_APP_PASSWORD",
    "NAVER_APP_PASSWORD",
    "TELEGRAM_BOT_TOKEN",
    "ANTHROPIC_API_KEY",
    "BRIDGE_SMTP_PASS",
    "WEBHOOK_SECRET",
    "ADMIN_API_KEY",
    "JWT_SECRET",
    "BRIDGE_FIELD_KEY",
    "UPLOAD_SIGN_KEY",
    "BRIDGE_WEBHOOK_SECRET",
]


def main():
    print("=" * 55)
    print("  BRIDGE Secret Migration: .env -> Vault")
    print("  Sensitive keys will be double-encrypted")
    print("=" * 55)

    # Check vault exists
    if not os.path.exists(os.path.join(VAULT_DIR, "vault_index.enc")):
        print("\n[!] Vault not initialized. Run 'vault.bat' -> [1] init first")
        sys.exit(1)

    # Check .env exists
    if not os.path.exists(ENV_FILE):
        print(f"\n[!] .env not found: {ENV_FILE}")
        sys.exit(1)

    # Get passphrases
    print("\n--- Unlock Vault ---")
    pa = getpass.getpass("Passphrase A (inner): ").encode("utf-8")
    pb = getpass.getpass("Passphrase B (outer): ").encode("utf-8")

    vault = SecretVault(VAULT_DIR)
    try:
        vault.unlock(pa, pb)
    except Exception as e:
        print(f"[!] Vault unlock failed: {e}")
        sys.exit(1)

    # Read .env
    with open(ENV_FILE, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    # Find plaintext sensitive values
    found = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for key in SENSITIVE_KEYS:
            if stripped.startswith(f"{key}="):
                val = stripped[len(key)+1:]
                # Skip if already vault ref, encrypted, or hashed
                if val.startswith("VAULT:") or val.startswith("ENC:") or val.startswith("pbkdf2:"):
                    continue
                # Skip placeholders
                if any(x in val.lower() for x in ["여기에", "입력", "example"]):
                    continue
                found[key] = (i, val)

    if not found:
        print("\n[OK] No plaintext secrets to migrate")
        vault.lock()
        return

    print(f"\n[!] {len(found)} plaintext secrets found:")
    print()
    for key, (line_num, val) in found.items():
        masked = val[:4] + "*" * (len(val) - 8) + val[-4:] if len(val) > 12 else "****"
        print(f"  {key:<30} = {masked}")

    print()
    confirm = input("Migrate all to vault? (type YES): ")
    if confirm != "YES":
        print("Aborted.")
        vault.lock()
        return

    # Backup .env
    backup_path = ENV_FILE + f".bak.{int(time.time())}"
    shutil.copy2(ENV_FILE, backup_path)
    print(f"\n[OK] Backup: {backup_path}")

    # Migrate each key
    migrated = 0
    for key, (line_idx, val) in found.items():
        entry_id = key.lower()
        vault.add(entry_id, val, label=key)
        lines[line_idx] = f"{key}=VAULT:{entry_id}\n"
        migrated += 1
        print(f"  [+] {key} -> VAULT:{entry_id}")

    # Write updated .env
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    vault.lock()

    print(f"\n{'=' * 55}")
    print(f"  Migration complete: {migrated} secrets encrypted")
    print(f"  Backup at: {backup_path}")
    print(f"  .env now uses VAULT: references")
    print(f"{'=' * 55}")
    print()
    print("  IMPORTANT: Passphrase A + B 를 종이에 적어 안전하게 보관하세요")
    print("  두 passphrase를 모두 잃으면 볼트 복구 불가능합니다")


if __name__ == "__main__":
    main()
