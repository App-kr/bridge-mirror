"""
security_vault.py — Bridge Base Field Encryption Module

Provides AES-256-GCM encryption and decryption for sensitive personal data fields.
Uses BRIDGE_FIELD_KEY from .env as the key material (SHA-256 derived → 32 bytes).

Encrypted format (base64-encoded):
    [ 12-byte nonce | ciphertext | 16-byte GCM auth tag ]

Sensitive fields encrypted:
    candidates → passport_status, criminal_record, health_info, criminal_record_check
    clients    → business_registration
"""

import os
import base64
import hashlib
from pathlib import Path

# .env 로드 시도 (있으면 사용, 없어도 vault 폴백 존재)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
except ImportError:
    pass

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError as e:
    raise ImportError(
        "cryptography package is required. Install with: pip install cryptography"
    ) from e

NONCE_SIZE = 12  # 96-bit nonce — NIST recommended for AES-GCM


# ── Key Derivation ─────────────────────────────────────────────────────────────

def _get_field_key_raw() -> str:
    """
    BRIDGE_FIELD_KEY 조회.
    1순위: 환경변수 (Render 프로덕션)
    2순위: MasterVault v3 (로컬 개발 — .env 없어도 동작)
    """
    raw = os.environ.get("BRIDGE_FIELD_KEY", "").strip()
    if raw:
        return raw
    # vault 폴백 (로컬 개발용)
    try:
        import sys
        _tools = Path(__file__).parent / "tools"
        if str(_tools) not in sys.path:
            sys.path.insert(0, str(_tools))
        from master_vault import get_secret
        return get_secret("BRIDGE_FIELD_KEY")
    except Exception:
        pass
    raise EnvironmentError(
        "BRIDGE_FIELD_KEY 없음. "
        "python tools/master_vault.py seal BRIDGE_FIELD_KEY 로 등록하세요."
    )


def _derive_key() -> bytes:
    """
    Derive a 32-byte AES-256 key from BRIDGE_FIELD_KEY.
    SHA-256 guarantees exactly 32 bytes regardless of raw key length.
    """
    raw = _get_field_key_raw()
    return hashlib.sha256(raw.encode("utf-8")).digest()


# ── Encryption ─────────────────────────────────────────────────────────────────

def encrypt_field(plaintext: str) -> str:
    """
    Encrypt a sensitive string field using AES-256-GCM.

    Returns a base64-encoded string:
        base64( nonce[12] + ciphertext + auth_tag[16] )

    Empty or whitespace-only strings are returned as-is (not encrypted).
    Each call generates a fresh cryptographically-random nonce.
    """
    if not plaintext or not plaintext.strip():
        return plaintext

    key = _derive_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_SIZE)  # fresh random nonce per encryption

    # encrypt() returns ciphertext + 16-byte GCM authentication tag
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

    payload = nonce + ciphertext_with_tag
    return base64.b64encode(payload).decode("ascii")


# ── Decryption ─────────────────────────────────────────────────────────────────

def decrypt_field(encoded: str) -> str:
    """
    Decrypt a base64-encoded AES-256-GCM ciphertext back to plaintext.

    Raises:
        ValueError  — if the ciphertext is too short or the auth tag is invalid
                      (indicates tampered or corrupted data)
    """
    if not encoded or not encoded.strip():
        return encoded

    key = _derive_key()
    aesgcm = AESGCM(key)

    try:
        raw = base64.b64decode(encoded.encode("ascii"), validate=True)
    except Exception as exc:
        raise ValueError(f"Invalid base64 ciphertext: {exc}") from exc

    min_length = NONCE_SIZE + 16  # nonce + GCM tag (no plaintext required)
    if len(raw) < min_length:
        raise ValueError(
            f"Ciphertext too short ({len(raw)} bytes). "
            "Data may be corrupted or was not encrypted with this vault."
        )

    nonce = raw[:NONCE_SIZE]
    ciphertext_with_tag = raw[NONCE_SIZE:]

    # decrypt() verifies the GCM tag and raises InvalidTag on mismatch
    plaintext_bytes = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
    return plaintext_bytes.decode("utf-8")


# ── Utility ────────────────────────────────────────────────────────────────────

def is_encrypted(value: str) -> bool:
    """
    Heuristic check: returns True if the value looks like a vault ciphertext.
    Checks for valid base64 and minimum byte length (nonce + tag = 28 bytes).
    Not 100% definitive — use only for diagnostics.
    """
    if not value or not value.strip():
        return False
    try:
        raw = base64.b64decode(value.encode("ascii"), validate=True)
        return len(raw) >= NONCE_SIZE + 16
    except Exception:
        return False


# ── Self-test (run directly: python security_vault.py) ────────────────────────

if __name__ == "__main__":
    print("[security_vault] Running self-test...")

    test_cases = [
        "123456789",                      # passport number
        "Clean record",                   # criminal record
        "No known conditions",            # health info
        "사업자등록번호 123-45-67890",    # business registration (Korean)
        "",                               # empty string — should pass through unchanged
    ]

    all_passed = True
    for original in test_cases:
        encrypted = encrypt_field(original)
        decrypted = decrypt_field(encrypted)

        ok = (decrypted == original)
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_passed = False

        if original:
            print(f"  [{status}] '{original[:30]}' → encrypted({len(encrypted)} chars) → '{decrypted[:30]}'")
        else:
            print(f"  [{status}] (empty string) → unchanged: '{encrypted}'")

    if all_passed:
        print("\n  All tests passed. AES-256-GCM encryption is working correctly.")
    else:
        print("\n  Some tests FAILED. Check BRIDGE_FIELD_KEY in .env.")
