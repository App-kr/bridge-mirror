#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WireGuard Triple Encryption - Decryption & Auto-Apply
3중 복호화 후 PC 설정 자동 적용
"""

import sys
import base64
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 3중 마스터 키 (암호화 프로그램과 동일)
master_key1 = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=b"wireguard_layer1_key",
    iterations=600000,
).derive(b"level1_encryption")

master_key2 = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=b"wireguard_layer2_key",
    iterations=600000,
).derive(b"level2_encryption")

master_key3 = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=b"wireguard_layer3_key",
    iterations=600000,
).derive(b"level3_encryption")

# 암호화된 값
encrypted_value = "VDN2MfJeYJdFwkhpmFtRbY8pzArIU/jdcllZl4yWvoPcriJIv4aayagZ/wPc+PLZx7i3VEqBxqVzT1mDifOJ5kPRicil6AWWDkQ5E9A7PXmUNXasl++DNVa++7aD2JxHrqieaKEuJUnMj/ywvWpeXJFNZE4E+c8iOvB+BP2bq3VZs87p"

print("=" * 70)
print("WireGuard - Decryption & Auto-Apply")
print("=" * 70)
print()

try:
    # Decode
    print("[IN] Decoding base64...")
    payload = base64.b64decode(encrypted_value)

    # Parse (correct format)
    magic = payload[:4]
    nonce1 = payload[4:16]
    nonce2 = payload[16:28]
    nonce3 = payload[28:40]
    ct3 = payload[40:]

    print(f"[OK] Magic: {magic}")
    print(f"[OK] Nonces: L1={nonce1.hex()[:8]}... L2={nonce2.hex()[:8]}... L3={nonce3.hex()[:8]}...")

    # Layer 3 Decryption (reverse order)
    print("[IN] Layer 3 decryption...")
    cipher3 = AESGCM(master_key3)
    ct2 = cipher3.decrypt(nonce3, ct3, None)
    print("[OK] L3 ✓")

    # Layer 2 Decryption
    print("[IN] Layer 2 decryption...")
    cipher2 = AESGCM(master_key2)
    ct1 = cipher2.decrypt(nonce2, ct2, None)
    print("[OK] L2 ✓")

    # Layer 1 Decryption
    print("[IN] Layer 1 decryption...")
    cipher1 = AESGCM(master_key1)
    plaintext = cipher1.decrypt(nonce1, ct1, None)
    public_key = plaintext.decode()
    print("[OK] L1 ✓")

    print()
    print(f"[OK] Decrypted Public Key: {public_key[:30]}...")
    print()

    # Apply to PC config
    print("[IN] Applying to PC WireGuard config...")
    pc_conf_path = Path("Q:/Claudework/bridge base/security_config/wireguard/pc/Scarlett_Main_PC.conf")
    c_conf_path = Path("C:/Program Files/WireGuard/Data/Configurations/Scarlett_Main_PC.conf")

    # Read current config
    with open(pc_conf_path, 'r') as f:
        config = f.read()

    # Replace placeholder
    updated_config = config.replace("SERVER_PUBLIC_KEY_HERE", public_key)

    # Write to Q
    with open(pc_conf_path, 'w') as f:
        f.write(updated_config)
    print(f"[OK] Q: config updated")

    # Write to C (if exists)
    if c_conf_path.exists():
        with open(c_conf_path, 'w') as f:
            f.write(updated_config)
        print(f"[OK] C: config updated")

    print()
    print("=" * 70)
    print("[OK] ✓ All complete!")
    print("=" * 70)
    print()
    print("Next: Activate WireGuard and test")
    print("  ping 10.0.0.1")
    print()

    # Clear memory
    del public_key
    del plaintext
    del ct1, ct2, ct3

except Exception as e:
    print(f"[ERR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
