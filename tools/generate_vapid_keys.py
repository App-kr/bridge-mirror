#!/usr/bin/env python3
"""
Generate VAPID keys for Web Push Notifications (RFC 8291)
====================================================================
VAPID keys are used to identify your server to push notification services.
Public key: Send to clients (stored in database)
Private key: Keep secret on server (stored in environment variables)
"""

import json
import sys
from pathlib import Path

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("[ERROR] cryptography 라이브러리 필요: pip install cryptography")
    sys.exit(1)

try:
    from pywebpush import WebPushException
    # Try to import vapid key generation utilities
    try:
        from pywebpush.main import Vapid01
        VAPID_MODULE = "Vapid01"
    except ImportError:
        try:
            from pywebpush import Vapid01
            VAPID_MODULE = "Vapid01"
        except ImportError:
            VAPID_MODULE = None
except ImportError:
    VAPID_MODULE = None


def generate_vapid_keys_raw():
    """Generate VAPID keys using cryptography library."""
    print("[*] VAPID 키 생성 중 (EC P-256)...")

    # Generate private key
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())

    # Get public key
    public_key = private_key.public_key()

    # Get coordinates (x, y) from public key for base64url encoding
    public_numbers = public_key.public_numbers()

    # Format for VAPID: base64url(x + y) where x, y are 32 bytes each (P-256)
    import base64
    x_bytes = public_numbers.x.to_bytes(32, byteorder='big')
    y_bytes = public_numbers.y.to_bytes(32, byteorder='big')
    public_key_bytes = x_bytes + y_bytes

    # Encode to base64url
    public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode().rstrip('=')

    # Export private key in PEM format
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    return {
        "public_key": public_key_b64,
        "private_key_pem": private_key_pem
    }


def generate_vapid_keys_library():
    """Generate VAPID keys using pywebpush library if available."""
    if VAPID_MODULE is None:
        return None

    try:
        print("[*] pywebpush.Vapid01을 사용하여 VAPID 키 생성 중...")
        from pywebpush import Vapid01

        vapid = Vapid01.generate()

        # Vapid01 format
        public_key = vapid.public_key.urlsafe_b64encode().decode()
        # Get the private key in appropriate format
        private_key = vapid.private_key

        # Convert to PEM format
        from cryptography.hazmat.primitives import serialization
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        return {
            "public_key": public_key,
            "private_key_pem": private_key_pem
        }
    except Exception as e:
        print(f"[WARNING] pywebpush 사용 실패: {e}")
        return None


def main():
    print("=" * 70)
    print("VAPID Key Generator for Web Push Notifications")
    print("=" * 70)

    # Try library method first, fall back to raw cryptography
    keys = generate_vapid_keys_library()
    if keys is None:
        keys = generate_vapid_keys_raw()

    print("\n✅ VAPID 키 생성 완료!\n")
    print("=" * 70)
    print("PUBLIC KEY (클라이언트에 제공):")
    print("-" * 70)
    print(keys["public_key"])
    print("\n" + "=" * 70)
    print("PRIVATE KEY (서버 환경변수로 설정 — 절대 노출 금지):")
    print("-" * 70)
    print(keys["private_key_pem"])
    print("\n" + "=" * 70)

    # Save to JSON for reference
    output_file = Path(__file__).parent.parent / "vapid_keys.json"
    with open(output_file, 'w') as f:
        json.dump({
            "VAPID_PUBLIC_KEY": keys["public_key"],
            "VAPID_PRIVATE_KEY_PEM": keys["private_key_pem"],
            "generated_at": __import__('datetime').datetime.now().isoformat(),
            "warning": "⚠️ 이 파일은 비밀입니다! .gitignore에 추가했는지 확인하세요."
        }, f, indent=2)

    print(f"\n✅ VAPID 키가 {output_file}에 저장되었습니다.")
    print("\n🔧 다음 단계:")
    print("1. PUBLIC KEY를 클라이언트에 저장: usePushNotification.ts에 저장")
    print("2. ENVIRONMENT VARIABLES 설정:")
    print("   - Render Dashboard → Environment 탭")
    print("   - VAPID_PUBLIC_KEY = " + keys["public_key"][:30] + "...")
    print("   - VAPID_PRIVATE_KEY_PEM = (위의 PRIVATE KEY 전체)")
    print("\n✅ 설정 후 Render를 재배포하면 Push 알림이 활성화됩니다.")


if __name__ == "__main__":
    main()
