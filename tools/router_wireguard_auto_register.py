#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto-register WireGuard Peer in Router
공유기 WireGuard에 클라이언트(PC) 자동 등록
"""

import sys
import json
import time
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import Select, WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

def main():
    print("Router WireGuard Auto-Register (Selenium)")
    print("=" * 70)

    if not HAS_SELENIUM:
        print("[WARN] Selenium not installed")
        print("       pip install selenium")
        return 1

    # Read PC public key
    reg_path = Path("security_config/wireguard/pc/registration.json")
    if not reg_path.exists():
        print(f"[ERR] Registration file not found: {reg_path}")
        return 1

    with open(reg_path, 'r') as f:
        pc_data = json.load(f)

    pc_public_key = pc_data['public_key']
    pc_name = pc_data['device_name']
    pc_ip = pc_data['vpn_ip']

    print(f"[INFO] Device: {pc_name}")
    print(f"[INFO] Public Key: {pc_public_key[:30]}...")
    print(f"[INFO] VPN IP: {pc_ip}")
    print()

    # Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Background mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    print("[IN] Connecting to router (192.168.0.1)...")

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("http://192.168.0.1")
        time.sleep(3)

        # Try to find login form
        try:
            username_field = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            password_field = driver.find_element(By.ID, "password")

            print("[IN] Logging in...")
            username_field.send_keys("admin")
            password_field.send_keys("admin")

            login_btn = driver.find_element(By.ID, "login_button")
            login_btn.click()

            time.sleep(3)

        except Exception as e:
            print(f"[WARN] Login form not found: {e}")

        # Navigate to WireGuard
        print("[IN] Navigating to WireGuard settings...")
        driver.get("http://192.168.0.1/cgi-bin/admin?page=wireguard")
        time.sleep(2)

        print("[OK] Router page loaded")
        print("[INFO] Manual registration still required")
        print("       Please use: 공유기등록용_공개키.txt")

        driver.quit()

    except Exception as e:
        print(f"[ERR] Selenium failed: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return 1

    print()
    print("=" * 70)
    print("[INFO] Manual Registration Required")
    print()
    print("Please register PC peer manually:")
    print(f"1. 192.168.0.1 → WireGuard Server")
    print(f"2. Add Peer:")
    print(f"   Name: {pc_name}")
    print(f"   Public Key: {pc_public_key}")
    print(f"   IP: {pc_ip}")
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())
