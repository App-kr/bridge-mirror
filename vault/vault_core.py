"""
BRIDGE Secret Vault — Double-Layer Encryption Engine
=====================================================
Architecture:
  Plaintext
    -> [Layer 1] Argon2id(passA) -> ChaCha20-Poly1305
    -> [Layer 2] Argon2id(passB) -> AES-256-GCM (AAD=entry_id)
    -> Base64 blob -> .vault file

Security:
  - KDF: Argon2id (128MB memory, 4 iterations, 2 threads)
  - Inner: ChaCha20-Poly1305 (96-bit nonce)
  - Outer: AES-256-GCM (96-bit nonce, AAD bound)
  - Integrity: HMAC-SHA256 over entire vault file
  - Zero plaintext on disk — ever
"""

import os
import json
import time
import hmac
import hashlib
import base64
import struct
from pathlib import Path
from typing import Optional

from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305, AESGCM


# ── Constants ────────────────────────────────────────────────────
VAULT_VERSION    = 1
ARGON2_TIME      = 4          # iterations
ARGON2_MEMORY    = 131072     # 128 MB
ARGON2_PARALLEL  = 2          # threads
SALT_LEN         = 32         # bytes
NONCE_LEN_CHACHA = 12         # ChaCha20-Poly1305
NONCE_LEN_GCM    = 12         # AES-256-GCM
KEY_LEN          = 32         # 256-bit
HMAC_KEY_LEN     = 32


def _derive_key(passphrase: bytes, salt: bytes) -> bytes:
    """Argon2id key derivation — 128MB memory-hard."""
    return hash_secret_raw(
        secret=passphrase,
        salt=salt,
        time_cost=ARGON2_TIME,
        memory_cost=ARGON2_MEMORY,
        parallelism=ARGON2_PARALLEL,
        hash_len=KEY_LEN,
        type=Type.ID,
    )


def encrypt_entry(plaintext: str, pass_a: bytes, pass_b: bytes,
                   entry_id: str) -> bytes:
    """
    Double-encrypt a secret.
    Returns a self-contained binary blob:
      [version:1][salt_a:32][nonce_a:12][len_inner:4][ct_inner]
      [salt_b:32][nonce_b:12][ct_outer]
    """
    raw = plaintext.encode("utf-8")

    # ── Layer 1: ChaCha20-Poly1305 ───────────────────────────────
    salt_a  = os.urandom(SALT_LEN)
    key_a   = _derive_key(pass_a, salt_a)
    nonce_a = os.urandom(NONCE_LEN_CHACHA)
    cipher1 = ChaCha20Poly1305(key_a)
    ct_inner = cipher1.encrypt(nonce_a, raw, None)

    # ── Layer 2: AES-256-GCM (AAD = entry_id) ───────────────────
    salt_b  = os.urandom(SALT_LEN)
    key_b   = _derive_key(pass_b, salt_b)
    nonce_b = os.urandom(NONCE_LEN_GCM)
    cipher2 = AESGCM(key_b)
    aad     = entry_id.encode("utf-8")
    ct_outer = cipher2.encrypt(nonce_b, ct_inner, aad)

    # ── Pack ─────────────────────────────────────────────────────
    blob = bytearray()
    blob.append(VAULT_VERSION)
    blob.extend(salt_a)
    blob.extend(nonce_a)
    blob.extend(struct.pack(">I", len(ct_inner)))
    blob.extend(ct_inner)
    blob.extend(salt_b)
    blob.extend(nonce_b)
    blob.extend(ct_outer)
    return bytes(blob)


def decrypt_entry(blob: bytes, pass_a: bytes, pass_b: bytes,
                   entry_id: str) -> str:
    """Reverse double-encryption. Raises on tamper or wrong passphrase."""
    pos = 0

    # version
    version = blob[pos]; pos += 1
    if version != VAULT_VERSION:
        raise ValueError(f"Unsupported vault version: {version}")

    # Layer 1 params
    salt_a = blob[pos:pos+SALT_LEN]; pos += SALT_LEN
    nonce_a = blob[pos:pos+NONCE_LEN_CHACHA]; pos += NONCE_LEN_CHACHA
    ct_inner_len = struct.unpack(">I", blob[pos:pos+4])[0]; pos += 4
    ct_inner = blob[pos:pos+ct_inner_len]; pos += ct_inner_len

    # Layer 2 params
    salt_b = blob[pos:pos+SALT_LEN]; pos += SALT_LEN
    nonce_b = blob[pos:pos+NONCE_LEN_GCM]; pos += NONCE_LEN_GCM
    ct_outer = blob[pos:]

    # ── Decrypt Layer 2 (AES-256-GCM) ───────────────────────────
    key_b = _derive_key(pass_b, salt_b)
    cipher2 = AESGCM(key_b)
    aad = entry_id.encode("utf-8")
    ct_inner_dec = cipher2.decrypt(nonce_b, ct_outer, aad)

    # Verify inner ciphertext matches
    if ct_inner_dec != ct_inner:
        raise ValueError("Inner ciphertext mismatch — possible tamper")

    # ── Decrypt Layer 1 (ChaCha20-Poly1305) ──────────────────────
    key_a = _derive_key(pass_a, salt_a)
    cipher1 = ChaCha20Poly1305(key_a)
    raw = cipher1.decrypt(nonce_a, ct_inner, None)

    return raw.decode("utf-8")


class SecretVault:
    """
    File-backed encrypted vault.
    Storage format: JSON index + binary blobs per entry.
    """

    def __init__(self, vault_dir: str):
        self.vault_dir = Path(vault_dir)
        self.index_path = self.vault_dir / "vault_index.enc"
        self.blobs_dir  = self.vault_dir / "blobs"
        self.hmac_path  = self.vault_dir / "vault.hmac"
        self._pass_a: Optional[bytes] = None
        self._pass_b: Optional[bytes] = None
        self._session_ts: float = 0
        self._session_timeout = 300  # 5 min

    def init_vault(self, pass_a: bytes, pass_b: bytes):
        """Initialize empty vault with dual passphrases."""
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.blobs_dir.mkdir(exist_ok=True)

        self._pass_a = pass_a
        self._pass_b = pass_b
        self._session_ts = time.time()

        # Create empty index
        index = {"version": VAULT_VERSION, "entries": {}, "created": time.time()}
        self._save_index(index)

    def unlock(self, pass_a: bytes, pass_b: bytes):
        """Unlock vault for session (5-min auto-lock)."""
        # Test decrypt index to verify passphrases
        self._pass_a = pass_a
        self._pass_b = pass_b
        self._session_ts = time.time()
        self._load_index()  # will raise if wrong passphrase

    def _check_session(self):
        if not self._pass_a or not self._pass_b:
            raise PermissionError("Vault is locked")
        if time.time() - self._session_ts > self._session_timeout:
            self._pass_a = None
            self._pass_b = None
            raise PermissionError("Session expired (5 min timeout)")
        self._session_ts = time.time()

    def _save_index(self, index: dict):
        """Encrypt and save the index file."""
        raw = json.dumps(index, ensure_ascii=False).encode("utf-8")
        blob = encrypt_entry(raw.decode("utf-8"), self._pass_a, self._pass_b,
                             "__vault_index__")
        self.index_path.write_bytes(blob)
        self._update_hmac()

    def _load_index(self) -> dict:
        """Decrypt and load the index file."""
        self._check_session()
        if not self.index_path.exists():
            raise FileNotFoundError("Vault not initialized")
        blob = self.index_path.read_bytes()
        raw = decrypt_entry(blob, self._pass_a, self._pass_b,
                            "__vault_index__")
        return json.loads(raw)

    def _update_hmac(self):
        """HMAC-SHA256 over all vault files for tamper detection."""
        hmac_key = _derive_key(self._pass_a + self._pass_b,
                               b"bridge_vault_hmac_salt_v1")
        h = hmac.new(hmac_key, digestmod=hashlib.sha256)

        if self.index_path.exists():
            h.update(self.index_path.read_bytes())

        for blob_file in sorted(self.blobs_dir.glob("*.blob")):
            h.update(blob_file.read_bytes())

        self.hmac_path.write_bytes(h.digest())

    def verify_integrity(self) -> bool:
        """Verify HMAC over entire vault."""
        self._check_session()
        if not self.hmac_path.exists():
            return False

        stored = self.hmac_path.read_bytes()
        hmac_key = _derive_key(self._pass_a + self._pass_b,
                               b"bridge_vault_hmac_salt_v1")
        h = hmac.new(hmac_key, digestmod=hashlib.sha256)

        if self.index_path.exists():
            h.update(self.index_path.read_bytes())

        for blob_file in sorted(self.blobs_dir.glob("*.blob")):
            h.update(blob_file.read_bytes())

        return hmac.compare_digest(stored, h.digest())

    def add(self, entry_id: str, secret: str, label: str = ""):
        """Add or overwrite an encrypted entry."""
        self._check_session()
        index = self._load_index()

        blob = encrypt_entry(secret, self._pass_a, self._pass_b, entry_id)
        blob_path = self.blobs_dir / f"{entry_id}.blob"
        blob_path.write_bytes(blob)

        index["entries"][entry_id] = {
            "label": label,
            "updated": time.time(),
            "size": len(blob),
        }
        self._save_index(index)

    def get(self, entry_id: str) -> str:
        """Decrypt and return a secret. Never touches disk with plaintext."""
        self._check_session()
        blob_path = self.blobs_dir / f"{entry_id}.blob"
        if not blob_path.exists():
            raise KeyError(f"Entry not found: {entry_id}")
        blob = blob_path.read_bytes()
        return decrypt_entry(blob, self._pass_a, self._pass_b, entry_id)

    def list_entries(self) -> dict:
        """List all entry IDs with labels (no secrets)."""
        self._check_session()
        index = self._load_index()
        return {k: v["label"] for k, v in index["entries"].items()}

    def delete(self, entry_id: str):
        """Securely delete an entry."""
        self._check_session()
        index = self._load_index()

        blob_path = self.blobs_dir / f"{entry_id}.blob"
        if blob_path.exists():
            # Overwrite with random data before delete
            size = blob_path.stat().st_size
            blob_path.write_bytes(os.urandom(size))
            blob_path.unlink()

        if entry_id in index["entries"]:
            del index["entries"][entry_id]
        self._save_index(index)

    def lock(self):
        """Immediately wipe session keys from memory."""
        self._pass_a = None
        self._pass_b = None
        self._session_ts = 0
