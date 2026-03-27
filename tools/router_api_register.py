#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공유기 WireGuard Peer REST API 등록 (안정성 우선)
"""

import sys
import json
import requests
import time
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_pc_peer_info():
    """Read PC peer information"""
    try:
        reg_path = Path("security_config/wireguard/pc/registration.json")
        with open(reg_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERR] Failed to read registration: {e}")
        return None

def register_via_api(peer_info, retries=3):
    """Register peer via REST API"""
    device_name = peer_info['device_name']
    public_key = peer_info['public_key']
    vpn_ip = peer_info['vpn_ip']

    router_ip = "192.168.0.1"

    # Try multiple API endpoints
    endpoints = [
        f"http://{router_ip}/cgi-bin/admin",
        f"http://{router_ip}/api/wireguard",
        f"http://{router_ip}/api/network/wireguard",
    ]

    for attempt in range(1, retries + 1):
        print(f"[TRY {attempt}/{retries}] Registering via API...")

        for endpoint in endpoints:
            try:
                # Prepare payload
                payload = {
                    "page": "wireguard",
                    "action": "add_peer",
                    "name": device_name,
                    "public_key": public_key,
                    "ip": vpn_ip,
                    "ip_address": vpn_ip,
                }

                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0"
                }

                print(f"[IN] Trying: {endpoint}")

                response = requests.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=10,
                    allow_redirects=True
                )

                print(f"[OK] Response: {response.status_code}")

                if response.status_code in [200, 201]:
                    print(f"[OK] ✓ Peer registered!")
                    return True

            except requests.exceptions.ConnectionError:
                print(f"[WARN] Connection error to {endpoint}")
            except requests.exceptions.Timeout:
                print(f"[WARN] Timeout at {endpoint}")
            except Exception as e:
                print(f"[WARN] {endpoint}: {e}")

        # Retry wait
        if attempt < retries:
            wait = 5 * (2 ** (attempt - 1))
            print(f"[WAIT] Retrying in {wait}s...")
            time.sleep(wait)

    return False

def main():
    print("=" * 70)
    print("공유기 WireGuard Peer REST API 등록")
    print("=" * 70)
    print()

    peer_info = get_pc_peer_info()
    if not peer_info:
        return 1

    print(f"[OK] Device: {peer_info['device_name']}")
    print(f"[OK] Public Key: {peer_info['public_key'][:30]}...")
    print(f"[OK] VPN IP: {peer_info['vpn_ip']}")
    print()

    print("[IN] Starting API registration...")
    print()

    if register_via_api(peer_info, retries=3):
        print()
        print("=" * 70)
        print("[OK] ✓ PC peer registered via API!")
        print("=" * 70)
        return 0
    else:
        print()
        print("=" * 70)
        print("[INFO] API registration unavailable")
        print("=" * 70)
        print()
        print("공유기 UI에서 수동 등록:")
        print(f"1. 192.168.0.1 접속")
        print(f"2. WireGuard 서버 → Peer 추가")
        print(f"3. 이름: {peer_info['device_name']}")
        print(f"4. 공개키: {peer_info['public_key']}")
        print(f"5. IP: {peer_info['vpn_ip']}")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
