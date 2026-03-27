#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BRIDGE Craigslist RPA — Vault Setup
====================================
.rpa_vault.json 생성 및 계정 자격증명 설정

사용법:
  python auto_vault_setup.py                    # 대화형 설정
  python auto_vault_setup.py --account gray     # 특정 계정만 설정
  python auto_vault_setup.py --reset            # 모든 계정 초기화
"""

import io
import json
import sys
import os

# UTF-8 인코딩 강제
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from pathlib import Path

VAULT_FILE = Path(__file__).resolve().parent / ".rpa_vault.json"

# 계정 목록
ACCOUNTS = {
    "gray": "회색 계정",
    "green": "초록 계정",
    "brown": "갈색 계정",
    "purple": "보라 계정",
}

def load_vault() -> dict:
    """기존 vault 파일 로드"""
    if VAULT_FILE.exists():
        try:
            with open(VAULT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"[WARN] Vault 파일이 손상되었습니다. 초기화합니다: {VAULT_FILE}")
            return {}
    return {}

def save_vault(vault: dict):
    """vault 파일 저장"""
    with open(VAULT_FILE, "w", encoding="utf-8") as f:
        json.dump(vault, f, ensure_ascii=False, indent=2)
    print(f"[OK] Vault saved: {VAULT_FILE}")

def setup_account(vault: dict, account: str):
    """특정 계정 설정"""
    desc = ACCOUNTS.get(account, "알 수 없는 계정")
    print(f"\n[SETUP] [{account}] {desc}")
    print("-" * 50)

    email = input(f"  Email: ").strip()
    if not email:
        print("  [SKIP] Email empty, skipping.")
        return

    password = input(f"  Password: ").strip()
    if not password:
        print("  [SKIP] Password empty, skipping.")
        return

    vault[f"{account}_email"] = email
    vault[f"{account}_password"] = password
    print(f"  [OK] [{account}] saved")

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Craigslist RPA Vault 설정",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python auto_vault_setup.py                  # 모든 계정 설정
  python auto_vault_setup.py --account gray   # gray 계정만 설정
  python auto_vault_setup.py --reset          # vault 초기화
        """
    )
    parser.add_argument("--account", help="특정 계정만 설정 (gray/green/brown/purple)")
    parser.add_argument("--reset", action="store_true", help="Vault 초기화")

    args = parser.parse_args()

    vault = load_vault()

    if args.reset:
        print("[WARN] Resetting vault...")
        confirm = input("Confirm (yes/no): ").strip().lower()
        if confirm == "yes":
            vault = {}
            save_vault(vault)
            print("[OK] Vault reset")
        else:
            print("[CANCEL] Cancelled")
        return

    if args.account:
        if args.account not in ACCOUNTS:
            print(f"[ERROR] Unknown account: {args.account}")
            print(f"[INFO] Available: {', '.join(ACCOUNTS.keys())}")
            sys.exit(1)
        setup_account(vault, args.account)
    else:
        print("\n[RPA] Craigslist RPA Vault Setup")
        print("=" * 50)
        print("Enter email and password for each account.")
        print("(Leave blank to skip)")

        for account in ACCOUNTS.keys():
            setup_account(vault, account)

        print("\n" + "=" * 50)

    if vault:
        save_vault(vault)
        print("\n[OK] Setup complete!")
        print("\nExample:")
        print("  python craigslist_auto_rpa.py --dry-run")
        print("  python craigslist_auto_rpa.py --account gray --limit 1")
    else:
        print("\n[WARN] No accounts configured.")

if __name__ == "__main__":
    main()
