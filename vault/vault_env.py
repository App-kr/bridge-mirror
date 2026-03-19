"""
BRIDGE Vault Environment Loader
=================================
.env 파일에서 VAULT:entry_id 참조를 감지하고
볼트에서 복호화한 값으로 환경변수를 설정한다.

사용법:
  # .env 파일에서:
  GMAIL_APP_PASSWORD=VAULT:gmail_app_password

  # Python에서:
  from vault.vault_env import load_vault_env
  load_vault_env(pass_a, pass_b)
  # -> os.environ["GMAIL_APP_PASSWORD"] = (복호화된 실제 비밀번호)
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vault_core import SecretVault

VAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load_vault_env(pass_a: bytes, pass_b: bytes,
                   env_file: str = None) -> dict:
    """
    Load .env, replace VAULT: references with decrypted secrets.
    Returns dict of resolved env vars.
    """
    if env_file is None:
        env_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env"
        )

    vault = SecretVault(VAULT_DIR)
    vault.unlock(pass_a, pass_b)

    resolved = {}

    with open(env_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
            if not m:
                continue
            key, val = m.group(1), m.group(2)

            if val.startswith("VAULT:"):
                entry_id = val[6:].strip()
                try:
                    val = vault.get(entry_id)
                except KeyError:
                    print(f"[WARN] Vault entry not found: {entry_id} (for {key})")
                    continue

            os.environ[key] = val
            resolved[key] = key  # Only store key names, not values

    vault.lock()
    return resolved


def migrate_env_to_vault(pass_a: bytes, pass_b: bytes,
                         env_file: str = None,
                         keys_to_migrate: list = None) -> list:
    """
    Read plaintext secrets from .env, store in vault,
    replace with VAULT: references.

    Returns list of migrated keys.
    """
    if env_file is None:
        env_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env"
        )

    vault = SecretVault(VAULT_DIR)
    vault.unlock(pass_a, pass_b)

    lines = []
    migrated = []

    with open(env_file, "r", encoding="utf-8", errors="ignore") as f:
        original_lines = f.readlines()

    for line in original_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            lines.append(line)
            continue

        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', stripped)
        if not m:
            lines.append(line)
            continue

        key, val = m.group(1), m.group(2)

        # Skip if already vault reference or encrypted
        if val.startswith("VAULT:") or val.startswith("ENC:") or val.startswith("pbkdf2:"):
            lines.append(line)
            continue

        # Check if this key should be migrated
        if keys_to_migrate and key not in keys_to_migrate:
            lines.append(line)
            continue

        # Store in vault
        entry_id = key.lower()
        vault.add(entry_id, val, label=key)
        lines.append(f"{key}=VAULT:{entry_id}\n")
        migrated.append(key)

    # Write updated .env
    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    vault.lock()
    return migrated
