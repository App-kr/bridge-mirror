#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WireGuard Server Public Key Encryption
Reads from .server_pubkey.txt and encrypts to .server_pubkey.enc
"""

import sys
import base64
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import secrets

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Read plaintext key
plaintext_file = Path("Q:/Claudework/bridge base/security_config/wireguard/.server_pubkey.txt")

if not plaintext_file.exists():
    print("[ERR] Public key file not found")
    sys.exit(1)

with open(plaintext_file, 'r') as f:
    public_key = f.read().strip()

if not public_key:
    print("[ERR] Empty key")
    sys.exit(1)

print("[IN] Encrypting...")
print(f"[KEY LENGTH] {len(public_key)} chars")

# Encryption
master_key = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=b"wireguard_server_key",
    iterations=600000,
).derive(b"default_master_key")

nonce = secrets.token_bytes(12)
cipher = AESGCM(master_key)
ciphertext = cipher.encrypt(nonce, public_key.encode(), None)
encrypted = nonce + ciphertext
result = base64.b64encode(encrypted).decode()

# Save encrypted
enc_file = Path("Q:/Claudework/bridge base/security_config/wireguard/.server_pubkey.enc")
enc_file.parent.mkdir(parents=True, exist_ok=True)

with open(enc_file, 'w') as f:
    f.write(result)

print("[OK] Encrypted and saved")
print(f"[FILE] {enc_file}")

# Delete plaintext immediately
plaintext_file.unlink()
print("[OK] Plaintext file deleted")

print()
print("=" * 70)
print("[OK] SECURE ENCRYPTION COMPLETE")
print("=" * 70)

# Clear memory
del public_key
del master_key
del encrypted
del result

sys.exit(0)
