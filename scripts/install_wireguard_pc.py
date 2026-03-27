#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WireGuard PC Installation Script"""

import os
import sys
import json
import secrets
import base64
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# Windows UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def generate_wireguard_key():
    """Generate WireGuard private key (32 bytes base64)"""
    private_bytes = secrets.token_bytes(32)
    private_key = base64.b64encode(private_bytes).decode('utf-8')
    return private_key

def get_public_key(private_key):
    """Calculate public key from private key using curve25519"""
    try:
        from cryptography.hazmat.primitives.asymmetric import x25519
        from cryptography.hazmat.primitives import serialization

        # Decode private key
        private_bytes = base64.b64decode(private_key)
        private_obj = x25519.X25519PrivateKey.from_private_bytes(private_bytes)

        # Get public key
        public_obj = private_obj.public_key()
        public_bytes = public_obj.public_bytes_raw()
        public_key = base64.b64encode(public_bytes).decode('utf-8')

        return public_key
    except Exception as e:
        print(f"[WARN] Cannot derive public key from private key: {e}")
        print("[INFO] Please generate keys manually in WireGuard app")
        return "MANUAL_PUBLIC_KEY_REQUIRED"

def main():
    print("Installing WireGuard PC Client...")
    print("=" * 70)

    # 1. Check WireGuard installation
    wg_path = Path("C:/Program Files/WireGuard")
    wg_exe = wg_path / "wireguard.exe"

    if wg_exe.exists():
        print("[OK] WireGuard already installed")
    else:
        print("[IN] Installing WireGuard...")
        installer = Path("C:/Users/Scarlett/Desktop/wireguard-installer.exe")

        if installer.exists():
            try:
                subprocess.run([str(installer), "/install"], timeout=60)
                print("[OK] WireGuard installation complete")
            except Exception as e:
                print(f"[ERR] Installation failed: {e}")
                return 1
        else:
            print(f"[ERR] Installer not found: {installer}")
            return 1

    # 2. Generate PC keys
    print("[IN] Generating PC WireGuard keys...")

    private_key = generate_wireguard_key()
    public_key = get_public_key(private_key)

    print("[OK] PC WireGuard keys generated")
    print(f"   Private Key: {private_key[:20]}...")
    print(f"   Public Key:  {public_key[:20] if public_key != 'MANUAL_PUBLIC_KEY_REQUIRED' else 'MANUAL'}...")

    # 3. Create config directory
    config_dir = wg_path / "Data" / "Configurations"
    config_dir.mkdir(parents=True, exist_ok=True)

    # 4. Create PC config file
    pc_conf = config_dir / "Scarlett_Main_PC.conf"
    pc_conf_content = f"""[Interface]
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

    pc_conf.write_text(pc_conf_content, encoding='utf-8')
    print(f"[OK] Config file created: {pc_conf}")

    # 5. Save registration info
    reg_path = Path("Q:/Claudework/bridge base/security_config/wireguard/pc/registration.json")
    reg_info = {
        "device_name": "Scarlett_Main_PC",
        "public_key": public_key,
        "private_key_hash": "SHA256:" + __import__('hashlib').sha256(private_key.encode()).hexdigest()[:16],
        "vpn_ip": "10.0.0.2",
        "created": datetime.now().isoformat()
    }

    reg_path.write_text(json.dumps(reg_info, indent=2), encoding='utf-8')
    print(f"[OK] Registration info saved: {reg_path}")

    # 6. Router registration guide
    print()
    print("NEXT STEP - Register PC public key in router:")
    print("=" * 70)
    print("1. Access 192.168.0.1 (admin/admin)")
    print("2. Advanced > Security > WireGuard > Add Peer")
    print("3. Enter:")
    print("   Name: Scarlett_Main_PC")
    print("   Public Key:")
    print(f"   {public_key}")
    print("   IP: 10.0.0.2")
    print("4. Save and restart WireGuard server")
    print()

    # 7. Copy config to desktop for easy access
    desktop_conf = Path("C:/Users/Scarlett/Desktop/Scarlett_Main_PC.conf")
    shutil.copy(pc_conf, desktop_conf)
    print(f"[OK] Config copied to desktop: {desktop_conf}")

    # 8. Launch WireGuard
    print("[IN] Launching WireGuard app...")
    try:
        subprocess.Popen([str(wg_exe)])
    except Exception as e:
        print(f"[WARN] Could not auto-launch WireGuard: {e}")
        print(f"       Please run manually: {wg_exe}")

    print()
    print("=" * 70)
    print("[OK] Installation complete!")
    print()
    print("Next steps:")
    print("1. Register PC public key in router (see above)")
    print("2. In WireGuard app, add/import 'Scarlett_Main_PC.conf'")
    print("3. Enable 'Scarlett_Main_PC' tunnel")
    print("4. Test VPN: ping 10.0.0.1")
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())
