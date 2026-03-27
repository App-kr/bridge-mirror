#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Secure WireGuard Setup - Keep public key in files only"""

import sys
import json
from pathlib import Path

def main():
    print("[SECURITY] Securing WireGuard PC setup...")
    print("=" * 70)

    # Read existing registration
    reg_path = Path("security_config/wireguard/pc/registration.json")

    if not reg_path.exists():
        print("[ERR] Registration file not found")
        return 1

    with open(reg_path, 'r') as f:
        reg_data = json.load(f)

    public_key = reg_data.get('public_key', 'UNKNOWN')

    # Create secure guide (file-based, not displayed)
    guide_path = Path("security_config/wireguard/pc/ROUTER_SETUP_GUIDE.txt")

    guide_text = f"""PC WireGuard - Router Registration Guide
========================================

Device: Scarlett_Main_PC
VPN IP: 10.0.0.2

[Step 1] Access Router
1. Open browser: http://192.168.0.1
2. Login: admin / admin

[Step 2] Add Peer
1. Advanced Settings > Security > WireGuard
2. Click "Add Peer" or "Add Client"
3. Fill in:
   Name: Scarlett_Main_PC
   Public Key: (see below)
   IP Address: 10.0.0.2

[Step 3] Public Key
Copy from: {reg_path}
File contents show public_key value

[Step 4] Save and Reboot
1. Click Save/OK
2. Reboot WireGuard server

[Test Connection]
After setup:
  ping 10.0.0.1  (should respond)

Generated: 2026-03-27
"""

    guide_path.write_text(guide_text, encoding='utf-8')

    print("[OK] Secure setup guide created (file-based)")
    print(f"     Location: {guide_path}")
    print()
    print("[WARN] Public key is NO LONGER displayed in chat")
    print("       Access it from: security_config/wireguard/pc/registration.json")
    print()
    print("[INFO] Router setup guide: security_config/wireguard/pc/ROUTER_SETUP_GUIDE.txt")
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())
