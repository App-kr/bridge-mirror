"""
BRIDGE PII 암호화 모듈
- AES-256-GCM (인증된 암호화)
- enc_ prefix 필드 자동 감지
- 키 파일 자동 생성/로드
- 마스킹 유틸

Usage:
    from security.encryption import PIICrypto

    crypto = PIICrypto()  # 자동으로 .bridge.key 로드 또는 생성
    
    encrypted = crypto.encrypt("010-1234-5678")
    decrypted = crypto.decrypt(encrypted)
    
    masked = crypto.mask_phone("010-1234-5678")  # → 010-****-5678
    masked = crypto.mask_email("test@gmail.com")  # → t****@gmail.com
"""

from __future__ import annotations

import os
import base64
import secrets
import hashlib
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("bridge.security")

# ─── 키 관리 ─────────────────────────────────────────────
DEFAULT_KEY_PATH = os.environ.get(
    "BRIDGE_KEY_PATH",
    str(Path(__file__).parent.parent / ".bridge.key")
)


def load_or_create_key(key_path: str = DEFAULT_KEY_PATH) -> bytes:
    """암호화 키 로드. 없으면 생성."""
    p = Path(key_path)
    if p.exists():
        key = p.read_bytes()
        if len(key) < 32:
            raise ValueError(f"키 파일 손상: {key_path} ({len(key)} bytes, 최소 32 필요)")
        log.info(f"암호화 키 로드: {key_path}")
        return key[:32]
    else:
        key = secrets.token_bytes(32)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(key)
        # 파일 권한 제한 (Unix)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass  # Windows에서는 무시
        log.warning(f"새 암호화 키 생성: {key_path} — 반드시 안전하게 백업하세요!")
        return key


# ─── AES-256-GCM 암호화 ──────────────────────────────────
class PIICrypto:
    """PII 필드 암호화/복호화

    포맷: base64(nonce_12bytes + ciphertext + tag_16bytes)
    """

    def __init__(self, key: Optional[bytes] = None, key_path: str = DEFAULT_KEY_PATH):
        if key:
            self._key = key[:32]
        else:
            self._key = load_or_create_key(key_path)

    def encrypt(self, plaintext: str) -> str:
        """평문 → 암호문 (base64 인코딩)"""
        if not plaintext:
            return ""

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            raise ImportError(
                "cryptography 패키지 필요: pip install cryptography --break-system-packages"
            )

        nonce = secrets.token_bytes(12)  # 96-bit nonce (GCM 권장)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        # nonce + ciphertext(+tag 포함) → base64
        return base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, encrypted: str) -> str:
        """암호문 (base64) → 평문"""
        if not encrypted:
            return ""

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            raise ImportError("cryptography 패키지 필요")

        raw = base64.b64decode(encrypted)
        if len(raw) < 28:  # 12(nonce) + 16(tag) 최소
            raise ValueError("암호문 손상: 길이 부족")

        nonce = raw[:12]
        ciphertext = raw[12:]
        aesgcm = AESGCM(self._key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")

    def encrypt_dict(self, data: dict, fields: list[str]) -> dict:
        """딕셔너리의 지정된 필드들을 암호화 (enc_ prefix 추가)"""
        result = dict(data)
        for field in fields:
            if field in result and result[field]:
                enc_key = f"enc_{field}" if not field.startswith("enc_") else field
                result[enc_key] = self.encrypt(str(result[field]))
                if not field.startswith("enc_"):
                    del result[field]  # 원본 평문 삭제
        return result

    def decrypt_dict(self, data: dict) -> dict:
        """딕셔너리의 enc_ prefix 필드들을 복호화"""
        result = dict(data)
        for key in list(result.keys()):
            if key.startswith("enc_") and result[key]:
                try:
                    plain_key = key[4:]  # enc_ 제거
                    result[plain_key] = self.decrypt(result[key])
                except Exception as e:
                    log.error(f"복호화 실패 [{key}]: {e}")
                    result[plain_key] = "복호화 오류"
        return result

    # ─── 마스킹 유틸 ─────────────────────────────────────
    @staticmethod
    def mask_phone(phone: str) -> str:
        """전화번호 마스킹: 010-1234-5678 → 010-****-5678"""
        if not phone:
            return "—"
        import re
        m = re.match(r"(\d{2,4})[-.\s]?(\d{3,4})[-.\s]?(\d{4})", phone.replace("-", ""))
        if m:
            return f"{m.group(1)}-****-{m.group(3)}"
        return phone[:3] + "****" + phone[-4:] if len(phone) > 7 else "****"

    @staticmethod
    def mask_email(email: str) -> str:
        """이메일 마스킹: test@gmail.com → t****@gmail.com"""
        if not email or "@" not in email:
            return "—"
        local, domain = email.split("@", 1)
        if len(local) <= 1:
            return f"*@{domain}"
        return f"{local[0]}****@{domain}"

    @staticmethod
    def mask_name(name: str) -> str:
        """이름 마스킹: 김철수 → 김**, 원장홍길동 → 원장홍**"""
        if not name:
            return "—"
        import re
        # 직함+이름 패턴
        m = re.match(r"(원장|부장|대표|사장|팀장|실장)(.+)", name)
        if m:
            title = m.group(1)
            n = m.group(2)
            return f"{title}{n[0]}**" if n else f"{title}**"
        if len(name) <= 1:
            return "*"
        return f"{name[0]}**"


# ─── PII 필드 목록 ───────────────────────────────────────
PII_FIELDS_CRITICAL = [
    "employer_name", "contact_name", "contact_phone",
    "contact_email", "contact_kakao",
]
PII_FIELDS_HIGH = [
    "address", "school_name", "health_info",
    "salary_detail", "visa_detail",
]
PII_FIELDS_ALL = PII_FIELDS_CRITICAL + PII_FIELDS_HIGH


# ─── 테스트 ──────────────────────────────────────────────
if __name__ == "__main__":
    import tempfile

    # 임시 키로 테스트
    key = secrets.token_bytes(32)
    crypto = PIICrypto(key=key)

    # 암호화/복호화 테스트
    test_data = [
        ("010-1234-5678", "전화번호"),
        ("test@gmail.com", "이메일"),
        ("김철수원장", "이름"),
        ("서울시 강남구 테헤란로 123", "주소"),
        ("", "빈 값"),
    ]

    print("=" * 60)
    print("BRIDGE PII 암호화 테스트")
    print("=" * 60)

    for plaintext, label in test_data:
        encrypted = crypto.encrypt(plaintext)
        decrypted = crypto.decrypt(encrypted)
        match = "✅" if decrypted == plaintext else "❌"
        print(f"\n{label}: {match}")
        print(f"  평문:   {plaintext or '(빈값)'}")
        print(f"  암호문: {encrypted[:40]}..." if encrypted else "  암호문: (빈값)")
        print(f"  복호화: {decrypted or '(빈값)'}")

    # 마스킹 테스트
    print(f"\n{'=' * 60}")
    print("마스킹 테스트")
    print(f"{'=' * 60}")
    print(f"  전화번호: {PIICrypto.mask_phone('010-1234-5678')}")
    print(f"  이메일:   {PIICrypto.mask_email('test@gmail.com')}")
    print(f"  이름:     {PIICrypto.mask_name('김철수원장')}")
    print(f"  이름:     {PIICrypto.mask_name('홍길동')}")

    # dict 암호화 테스트
    print(f"\n{'=' * 60}")
    print("Dict 암호화 테스트")
    print(f"{'=' * 60}")
    sample = {
        "contact_name": "김테스원장",
        "contact_phone": "010-2542-6545",
        "contact_email": "test@gmail.com",
        "region": "서울",
        "city": "구로",
    }
    encrypted_dict = crypto.encrypt_dict(sample, PII_FIELDS_CRITICAL)
    print(f"  암호화 후 키: {list(encrypted_dict.keys())}")
    print(f"  region(비PII): {encrypted_dict.get('region')}")
    print(f"  enc_contact_name: {encrypted_dict.get('enc_contact_name', 'N/A')[:30]}...")

    decrypted_dict = crypto.decrypt_dict(encrypted_dict)
    print(f"  복호화 후 contact_name: {decrypted_dict.get('contact_name')}")
    print(f"  복호화 후 contact_phone: {decrypted_dict.get('contact_phone')}")
