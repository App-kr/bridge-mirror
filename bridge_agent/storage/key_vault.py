"""
AES-256-GCM encrypted key vault for API keys.
Derives encryption key from machine-specific identifier.
"""

import base64
import hashlib
import os
import platform
import uuid
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_SIZE = 12


def _machine_id() -> str:
    """Derive a stable machine identifier."""
    node = str(uuid.getnode())
    system = platform.node()
    return f"bridge-agent-{node}-{system}"


def _derive_key(passphrase: str | None = None) -> bytes:
    """Derive 32-byte AES key from machine ID + optional passphrase."""
    material = _machine_id()
    if passphrase:
        material += passphrase
    return hashlib.sha256(material.encode("utf-8")).digest()


class KeyVault:
    """Encrypted storage for API keys using AES-256-GCM."""

    def __init__(self, vault_path: Path, passphrase: str | None = None):
        self._path = vault_path
        self._key = _derive_key(passphrase)
        self._data: dict[str, str] = {}
        self._load()

    def _encrypt(self, plaintext: str) -> str:
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(NONCE_SIZE)
        ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ct).decode("ascii")

    def _decrypt(self, encoded: str) -> str:
        aesgcm = AESGCM(self._key)
        raw = base64.b64decode(encoded.encode("ascii"))
        nonce = raw[:NONCE_SIZE]
        ct = raw[NONCE_SIZE:]
        return aesgcm.decrypt(nonce, ct, None).decode("utf-8")

    def _load(self):
        if not self._path.exists():
            self._data = {}
            return
        try:
            import json
            blob = self._path.read_text("utf-8")
            stored = json.loads(blob)
            self._data = {}
            for k, v in stored.items():
                try:
                    self._data[k] = self._decrypt(v)
                except Exception:
                    pass  # skip corrupted entries
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _save(self):
        import json
        self._path.parent.mkdir(parents=True, exist_ok=True)
        encrypted = {k: self._encrypt(v) for k, v in self._data.items()}
        self._path.write_text(json.dumps(encrypted, indent=2), "utf-8")

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str):
        self._data[key] = value
        self._save()

    def delete(self, key: str):
        self._data.pop(key, None)
        self._save()

    def has(self, key: str) -> bool:
        return key in self._data

    def list_keys(self) -> list[str]:
        return list(self._data.keys())
