"""
security/encryption.py — BRIDGE PII Encryption (AES-256-GCM)
=============================================================
PIICrypto: 개인정보 암호화/복호화/마스킹

- encrypt(plaintext) -> base64 암호문
- decrypt(encrypted) -> 평문
- encrypt_dict(data, fields) -> PII 필드 암호화, enc_ prefix 추가
- decrypt_dict(data) -> enc_ prefix 필드 자동 복호화
- mask_phone / mask_email / mask_name -> 마스킹
- 키 파일 자동 생성/로드 (.bridge.key)

의존성: pip install cryptography
"""

import os
import re
import base64
from pathlib import Path
from typing import Optional

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError as e:
    raise ImportError(
        "cryptography package required: pip install cryptography"
    ) from e

# ── PII 필드 목록 ────────────────────────────────────────────────────────────
PII_FIELDS_CRITICAL = [
    "phone", "mobile", "telephone",
    "email", "contact_email",
    "contact_person", "owner_name", "representative",
    "kakao_id", "line_id",
    "passport_number", "alien_registration",
    "address", "detailed_address",
]

NONCE_SIZE = 12  # 96-bit nonce (NIST recommended for AES-GCM)


class PIICrypto:
    """AES-256-GCM 기반 PII 암호화/복호화 클래스."""

    def __init__(self, key_path: Optional[str] = None):
        self._key_path = Path(
            key_path
            or os.getenv("BRIDGE_KEY_PATH", "")
            or (Path(__file__).resolve().parent.parent / ".bridge.key")
        )
        self._key = self._load_or_create_key()

    def _load_or_create_key(self) -> bytes:
        """키 파일 로드. 없으면 32바이트 랜덤 키 자동 생성."""
        if self._key_path.exists():
            raw = self._key_path.read_bytes().strip()
            if len(raw) >= 32:
                return raw[:32]
            # base64로 저장된 경우
            try:
                decoded = base64.b64decode(raw)
                if len(decoded) == 32:
                    return decoded
            except Exception:
                pass

        # 키 파일 생성
        key = os.urandom(32)
        self._key_path.parent.mkdir(parents=True, exist_ok=True)
        self._key_path.write_bytes(base64.b64encode(key))
        # 파일 권한 제한 (Unix 계열)
        try:
            os.chmod(str(self._key_path), 0o600)
        except (OSError, AttributeError):
            pass
        return key

    # ── 암호화 ────────────────────────────────────────────────────────────────

    def encrypt(self, plaintext: str) -> str:
        """
        AES-256-GCM 암호화.
        Returns: base64( nonce[12] + ciphertext + auth_tag[16] )
        빈 문자열은 그대로 반환.
        """
        if not plaintext or not plaintext.strip():
            return plaintext

        aesgcm = AESGCM(self._key)
        nonce = os.urandom(NONCE_SIZE)
        ciphertext_with_tag = aesgcm.encrypt(
            nonce, plaintext.encode("utf-8"), None
        )
        payload = nonce + ciphertext_with_tag
        return base64.b64encode(payload).decode("ascii")

    def decrypt(self, encrypted: str) -> str:
        """
        AES-256-GCM 복호화.
        Raises ValueError on tampered/corrupted data.
        """
        if not encrypted or not encrypted.strip():
            return encrypted

        try:
            raw = base64.b64decode(encrypted.encode("ascii"), validate=True)
        except Exception as exc:
            raise ValueError(f"Invalid base64 ciphertext: {exc}") from exc

        min_length = NONCE_SIZE + 16  # nonce + GCM tag
        if len(raw) < min_length:
            raise ValueError(
                f"Ciphertext too short ({len(raw)} bytes). "
                "Data may be corrupted or not encrypted with this key."
            )

        nonce = raw[:NONCE_SIZE]
        ciphertext_with_tag = raw[NONCE_SIZE:]

        aesgcm = AESGCM(self._key)
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext_bytes.decode("utf-8")

    # ── Dict 암호화/복호화 ────────────────────────────────────────────────────

    def encrypt_dict(self, data: dict, fields: Optional[list] = None) -> dict:
        """
        dict의 PII 필드를 암호화.
        - fields 미지정 시 PII_FIELDS_CRITICAL 사용
        - 암호화된 필드: enc_{field} 로 추가, 원본 삭제
        """
        if not isinstance(data, dict):
            return data
        result = dict(data)
        target_fields = fields or PII_FIELDS_CRITICAL
        for field in target_fields:
            value = result.get(field)
            if value and isinstance(value, str) and value.strip():
                enc_key = f"enc_{field}"
                result[enc_key] = self.encrypt(value)
                del result[field]
        return result

    def decrypt_dict(self, data: dict) -> dict:
        """
        dict의 enc_ prefix 필드를 자동 복호화.
        enc_{field} -> {field} 로 복원.
        """
        if not isinstance(data, dict):
            return data
        result = dict(data)
        enc_keys = [k for k in result if k.startswith("enc_")]
        for enc_key in enc_keys:
            original_key = enc_key[4:]  # "enc_" 제거
            encrypted_value = result[enc_key]
            if encrypted_value and isinstance(encrypted_value, str):
                try:
                    result[original_key] = self.decrypt(encrypted_value)
                except (ValueError, Exception):
                    result[original_key] = "[DECRYPTION_FAILED]"
            del result[enc_key]
        return result

    # ── 마스킹 ────────────────────────────────────────────────────────────────

    @staticmethod
    def mask_phone(phone: str) -> str:
        """010-1234-5678 -> 010-****-5678"""
        if not phone:
            return phone
        clean = re.sub(r"[\s\-]", "", phone)
        if len(clean) >= 8:
            return clean[:3] + "-****-" + clean[-4:]
        return "****"

    @staticmethod
    def mask_email(email: str) -> str:
        """test@gmail.com -> t****@gmail.com"""
        if not email or "@" not in email:
            return email
        local, domain = email.rsplit("@", 1)
        if len(local) <= 1:
            return f"****@{domain}"
        return f"{local[0]}****@{domain}"

    @staticmethod
    def mask_name(name: str) -> str:
        """
        김철수원장 -> 김**
        John Smith -> J**
        """
        if not name or len(name) < 2:
            return "**"
        return name[0] + "**"


# ── Self-test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[encryption] Self-test start...")
    crypto = PIICrypto()
    all_passed = True

    # 1. encrypt/decrypt roundtrip
    test_cases = [
        "010-1234-5678",
        "user@example.com",
        "김철수원장",
        "사업자등록번호 123-45-67890",
        "",
    ]
    for original in test_cases:
        encrypted = crypto.encrypt(original)
        decrypted = crypto.decrypt(encrypted)
        ok = decrypted == original
        if not ok:
            all_passed = False
        label = original[:30] if original else "(empty)"
        print(f"  [{'PASS' if ok else 'FAIL'}] roundtrip: '{label}'")

    # 2. encrypt_dict / decrypt_dict
    test_data = {
        "id": 1,
        "company": "BRIDGE",
        "phone": "010-9999-8888",
        "email": "boss@example.com",
        "address": "Seoul, Korea",
    }
    encrypted_data = crypto.encrypt_dict(test_data)
    ok2 = "phone" not in encrypted_data and "enc_phone" in encrypted_data
    print(f"  [{'PASS' if ok2 else 'FAIL'}] encrypt_dict: phone -> enc_phone")
    if not ok2:
        all_passed = False

    decrypted_data = crypto.decrypt_dict(encrypted_data)
    ok3 = decrypted_data.get("phone") == "010-9999-8888"
    print(f"  [{'PASS' if ok3 else 'FAIL'}] decrypt_dict: enc_phone -> phone")
    if not ok3:
        all_passed = False

    # 3. masking
    ok4 = crypto.mask_phone("010-1234-5678") == "010-****-5678"
    ok5 = crypto.mask_email("test@gmail.com") == "t****@gmail.com"
    masked_n = crypto.mask_name("Kim")
    ok6 = masked_n == "K**"
    print(f"  [{'PASS' if ok4 else 'FAIL'}] mask_phone: {crypto.mask_phone('010-1234-5678')}")
    print(f"  [{'PASS' if ok5 else 'FAIL'}] mask_email: {crypto.mask_email('test@gmail.com')}")
    print(f"  [{'PASS' if ok6 else 'FAIL'}] mask_name('Kim'): {masked_n}")
    if not (ok4 and ok5 and ok6):
        all_passed = False

    if all_passed:
        print("\n  All encryption tests PASSED.")
    else:
        print("\n  Some tests FAILED.")
