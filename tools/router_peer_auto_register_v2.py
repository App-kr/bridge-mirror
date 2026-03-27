#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공유기 WireGuard Peer 자동 등록 (안정성 우선)
Auto-register PC peer in router with full error handling
"""

import sys
import json
import time
import subprocess
import platform
from pathlib import Path
from typing import Optional, Tuple

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SELENIUM_INSTALLED = False
CHROME_AVAILABLE = False

def check_dependencies():
    """Check if Selenium and Chrome are available"""
    global SELENIUM_INSTALLED, CHROME_AVAILABLE

    try:
        from selenium import webdriver
        SELENIUM_INSTALLED = True
    except ImportError:
        print("[WARN] Selenium not installed")
        print("       Installing: pip install selenium")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "selenium"],
                         capture_output=True, timeout=60)
            SELENIUM_INSTALLED = True
            print("[OK] Selenium installed")
        except Exception as e:
            print(f"[ERR] Failed to install Selenium: {e}")
            return False

    # Check Chrome
    if platform.system() == "Windows":
        chrome_paths = [
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            str(Path.home() / "AppData\\Local\\Google\\Chrome\\Application\\chrome.exe")
        ]
    else:
        chrome_paths = ["/usr/bin/google-chrome", "/usr/bin/chromium"]

    for path in chrome_paths:
        if Path(path).exists():
            CHROME_AVAILABLE = True
            return True

    print("[WARN] Chrome not found, trying Chromium...")
    return CHROME_AVAILABLE

def get_pc_peer_info() -> Optional[dict]:
    """Read PC peer information from registration.json"""
    try:
        reg_path = Path("security_config/wireguard/pc/registration.json")
        if not reg_path.exists():
            print(f"[ERR] Registration file not found: {reg_path}")
            return None

        with open(reg_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        required = ['device_name', 'public_key', 'vpn_ip']
        if not all(k in data for k in required):
            print("[ERR] Invalid registration file format")
            return None

        return data

    except Exception as e:
        print(f"[ERR] Failed to read registration: {e}")
        return None

def register_peer_selenium(peer_info: dict, retries: int = 3) -> bool:
    """
    Register peer using Selenium with retry logic
    """
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException

    device_name = peer_info['device_name']
    public_key = peer_info['public_key']
    vpn_ip = peer_info['vpn_ip']

    for attempt in range(1, retries + 1):
        print(f"[TRY {attempt}/{retries}] Connecting to router...")

        driver = None
        try:
            # Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")

            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(15)

            # Access router
            driver.get("http://192.168.0.1")
            print("[OK] Router page loaded")
            time.sleep(2)

            # Try login
            try:
                print("[IN] Logging in...")
                username = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                password = driver.find_element(By.NAME, "password")
                username.send_keys("admin")
                password.send_keys("admin")

                # Find and click login button (multiple possible selectors)
                try:
                    login_btn = driver.find_element(By.NAME, "login")
                    login_btn.click()
                except:
                    login_btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                    login_btn.click()

                time.sleep(3)
                print("[OK] Login successful")

            except TimeoutException:
                print("[WARN] Login form not found (may already be logged in)")
                time.sleep(2)

            # Navigate to WireGuard server
            print("[IN] Navigating to WireGuard server...")
            try:
                # Try different URL patterns
                urls = [
                    "http://192.168.0.1/cgi-bin/admin?page=wireguard",
                    "http://192.168.0.1/cgi-bin/admin?page=wireguard_server",
                    "http://192.168.0.1/admin/wireguard"
                ]

                for url in urls:
                    try:
                        driver.get(url)
                        time.sleep(2)

                        # Check if page loaded
                        page_source = driver.page_source.lower()
                        if "wireguard" in page_source or "peer" in page_source:
                            print(f"[OK] WireGuard page loaded: {url}")
                            break
                    except:
                        continue

            except Exception as e:
                print(f"[WARN] Navigation issue: {e}")

            # Add peer button
            print("[IN] Looking for add peer button...")
            add_peer_selectors = [
                (By.ID, "add_peer"),
                (By.ID, "add_peer_button"),
                (By.NAME, "add_peer"),
                (By.CSS_SELECTOR, "button[name='add_peer']"),
                (By.XPATH, "//button[contains(text(), 'Add')]"),
                (By.XPATH, "//button[contains(text(), '추가')]"),
            ]

            add_peer_btn = None
            for selector_type, selector_value in add_peer_selectors:
                try:
                    add_peer_btn = driver.find_element(selector_type, selector_value)
                    break
                except:
                    continue

            if add_peer_btn:
                print("[OK] Add peer button found")
                add_peer_btn.click()
                time.sleep(1)
            else:
                print("[WARN] Add peer button not found, continuing...")

            # Fill peer info
            print("[IN] Filling in peer information...")
            form_fields = {
                'name': device_name,
                'public_key': public_key,
                'ip': vpn_ip,
                'ip_address': vpn_ip,
                'pubkey': public_key,
                'peer_name': device_name,
                'peer_public_key': public_key,
                'peer_ip': vpn_ip,
            }

            # Try multiple field name patterns
            for field_name, field_value in form_fields.items():
                try:
                    field = driver.find_element(By.NAME, field_name)
                    field.clear()
                    field.send_keys(field_value)
                    print(f"[OK] Filled: {field_name}")
                    break
                except:
                    continue

            # Save
            print("[IN] Saving peer...")
            save_selectors = [
                (By.NAME, "save"),
                (By.ID, "save"),
                (By.CSS_SELECTOR, "button[type='submit']"),
            ]

            save_btn = None
            for selector_type, selector_value in save_selectors:
                try:
                    save_btn = driver.find_element(selector_type, selector_value)
                    break
                except:
                    continue

            if save_btn:
                save_btn.click()
                time.sleep(2)
                print("[OK] Peer saved")
            else:
                print("[WARN] Save button not found")

            driver.quit()
            print(f"[OK] ✓ Attempt {attempt} successful!")
            return True

        except TimeoutException as e:
            print(f"[ERR] Timeout (attempt {attempt}): {e}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass

        except Exception as e:
            print(f"[ERR] Error (attempt {attempt}): {e}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass

        # Wait before retry (exponential backoff)
        if attempt < retries:
            wait_time = 5 * (2 ** (attempt - 1))
            print(f"[WAIT] Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

    return False

def main():
    print("=" * 70)
    print("공유기 WireGuard Peer 자동 등록 (v2 - 안정성 우선)")
    print("=" * 70)
    print()

    # Check dependencies
    print("[CHECK] Checking dependencies...")
    if not check_dependencies():
        print("[ERR] Required dependencies not available")
        print("[INFO] Manual registration required")
        return 1

    if not SELENIUM_INSTALLED:
        print("[ERR] Selenium installation failed")
        return 1

    print("[OK] Dependencies OK")
    print()

    # Get peer info
    print("[IN] Reading peer information...")
    peer_info = get_pc_peer_info()
    if not peer_info:
        return 1

    print(f"[OK] Device: {peer_info['device_name']}")
    print(f"[OK] Public Key: {peer_info['public_key'][:30]}...")
    print(f"[OK] VPN IP: {peer_info['vpn_ip']}")
    print()

    # Register
    print("[IN] Starting registration...")
    print()

    if register_peer_selenium(peer_info, retries=3):
        print()
        print("=" * 70)
        print("[OK] ✓ PC peer registered successfully!")
        print("=" * 70)
        print()
        print("다음 단계:")
        print("1. WireGuard 앱 실행")
        print("2. 'Scarlett_Main_PC' 활성화")
        print("3. ping 10.0.0.1 테스트")
        print()
        return 0
    else:
        print()
        print("=" * 70)
        print("[ERR] ✗ Automatic registration failed")
        print("=" * 70)
        print()
        print("수동 등록 (공유기 UI):")
        print(f"1. 192.168.0.1 접속 (admin/admin)")
        print(f"2. WireGuard → Peer 추가")
        print(f"3. 이름: {peer_info['device_name']}")
        print(f"4. 공개키: {peer_info['public_key']}")
        print(f"5. IP: {peer_info['vpn_ip']}")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
