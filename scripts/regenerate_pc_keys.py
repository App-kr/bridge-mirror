#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate PC WireGuard Keys"""

import sys
import json
import secrets
import base64
from pathlib import Path
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import x25519

def generate_key_pair():
    """Generate new WireGuard key pair"""
    private_bytes = secrets.token_bytes(32)
    private_key = base64.b64encode(private_bytes).decode('utf-8')

    # Calculate public key
    private_obj = x25519.X25519PrivateKey.from_private_bytes(private_bytes)
    public_obj = private_obj.public_key()
    public_bytes = public_obj.public_bytes_raw()
    public_key = base64.b64encode(public_bytes).decode('utf-8')

    return private_key, public_key

def main():
    print("Regenerating PC WireGuard Keys...")
    print("=" * 70)

    # Generate new keys
    private_key, public_key = generate_key_pair()
    print(f"[OK] New keys generated")
    print(f"     Private: {private_key[:30]}...")
    print(f"     Public:  {public_key[:30]}...")
    print()

    # Update registration.json
    reg_path = Path("security_config/wireguard/pc/registration.json")
    reg_data = {
        "device_name": "Scarlett_Main_PC",
        "public_key": public_key,
        "private_key_hash": "SHA256:" + __import__('hashlib').sha256(private_key.encode()).hexdigest()[:16],
        "vpn_ip": "10.0.0.2",
        "created": datetime.now().isoformat(),
        "regenerated": datetime.now().isoformat()
    }

    with open(reg_path, 'w') as f:
        json.dump(reg_data, f, indent=2)

    print(f"[OK] registration.json updated: {reg_path}")

    # Update config file in WireGuard
    wg_conf_path = Path("C:/Program Files/WireGuard/Data/Configurations/Scarlett_Main_PC.conf")
    wg_conf_content = f"""[Interface]
PrivateKey = {private_key}
Address = 10.0.0.2/32
DNS = 8.8.8.8, 8.8.4.4
SaveMconfig = false

[Peer]
PublicKey = SERVER_PUBLIC_KEY_HERE
Endpoint = bridgejob.co.kr:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
"""

    with open(wg_conf_path, 'w') as f:
        f.write(wg_conf_content)

    print(f"[OK] WireGuard config updated: {wg_conf_path}")

    # Update config file on desktop
    desktop_conf = Path("C:/Users/Scarlett/Desktop/Scarlett_Main_PC.conf")
    with open(desktop_conf, 'w') as f:
        f.write(wg_conf_content)

    print(f"[OK] Desktop copy updated: {desktop_conf}")
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())
