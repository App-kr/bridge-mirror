#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WireGuard 공개키 안전 입력 암호화
- 사용자가 직접 입력
- 즉시 AES-256-GCM 암호화
- 평문 보관 절대 금지
"""

import sys
import os
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import secrets
import base64

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def encrypt_key(plaintext_key: str, master_key: bytes) -> str:
    """AES-256-GCM 암호화"""
    nonce = secrets.token_bytes(12)
    cipher = AESGCM(master_key)
    ciphertext = cipher.encrypt(nonce, plaintext_key.encode(), None)

    # Format: nonce + ciphertext
    encrypted = nonce + ciphertext
    return base64.b64encode(encrypted).decode()

def main():
    print("=" * 70)
    print("WireGuard Server Public Key Encryption")
    print("=" * 70)
    print()

    # Get master key from environment or user
    master_key_file = Path("Q:/Claudework/bridge base/.bridge.key")

    if not master_key_file.exists():
        print("[ERR] Master key not found: .bridge.key")
        print("[INFO] Using default key derivation...")
        master_key = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"wireguard_server_key",
            iterations=600000,
        ).derive(b"default_master_key")
    else:
        with open(master_key_file, 'rb') as f:
            master_key = f.read()[:32]

    print("[INFO] Enter WireGuard Server Public Key")
    print("[INPUT] Paste the key and press Enter:")
    print()

    try:
        public_key = input().strip()
    except KeyboardInterrupt:
        print()
        print("[ABORT] Cancelled")
        return 1

    if not public_key:
        print("[ERR] Empty input")
        return 1

    # Encrypt immediately
    print()
    print("[IN] Encrypting with AES-256-GCM...")
    encrypted = encrypt_key(public_key, master_key)

    # Save to file
    enc_file = Path("Q:/Claudework/bridge base/security_config/wireguard/.server_pubkey.enc")
    enc_file.parent.mkdir(parents=True, exist_ok=True)

    with open(enc_file, 'w') as f:
        f.write(encrypted)

    print("[OK] Encrypted and saved")
    print()
    print("=" * 70)
    print("[OK] Public key encrypted")
    print("[FILE] Q:/Claudework/bridge base/security_config/wireguard/.server_pubkey.enc")
    print("=" * 70)
    print()
    print("[NOTE] Plain key is NOT stored anywhere")
    print("[NOTE] Only encrypted version saved to file")
    print()

    # Clear variables
    del public_key
    del master_key
    del encrypted

    return 0

if __name__ == "__main__":
    sys.exit(main())
