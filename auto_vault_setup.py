#!/usr/bin/env python3
"""
BRIDGE Craigslist RPA — Vault Setup
====================================
.rpa_vault.json 생성 및 계정 자격증명 설정

사용법:
  python auto_vault_setup.py                    # 대화형 설정
  python auto_vault_setup.py --account gray     # 특정 계정만 설정
  python auto_vault_setup.py --reset            # 모든 계정 초기화
"""

import json
import sys
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
    print(f"✅ Vault 저장됨: {VAULT_FILE}")

def setup_account(vault: dict, account: str):
    """특정 계정 설정"""
    desc = ACCOUNTS.get(account, "알 수 없는 계정")
    print(f"\n📝 [{account}] {desc} 설정")
    print("-" * 50)

    email = input(f"  이메일: ").strip()
    if not email:
        print("  ❌ 이메일이 비어있습니다. 건너뜁니다.")
        return

    password = input(f"  비밀번호: ").strip()
    if not password:
        print("  ❌ 비밀번호가 비어있습니다. 건너뜁니다.")
        return

    vault[f"{account}_email"] = email
    vault[f"{account}_password"] = password
    print(f"  ✅ [{account}] 저장됨")

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
        print("⚠️  Vault을 초기화합니다...")
        confirm = input("정말 초기화하시겠습니까? (yes/no): ").strip().lower()
        if confirm == "yes":
            vault = {}
            save_vault(vault)
            print("✅ Vault 초기화 완료")
        else:
            print("❌ 취소됨")
        return

    if args.account:
        if args.account not in ACCOUNTS:
            print(f"❌ 알 수 없는 계정: {args.account}")
            print(f"   사용 가능: {', '.join(ACCOUNTS.keys())}")
            sys.exit(1)
        setup_account(vault, args.account)
    else:
        print("\n🔐 Craigslist RPA Vault Setup")
        print("=" * 50)
        print("다음 계정의 이메일과 비밀번호를 입력하세요.")
        print("(계정을 건너뛰려면 비워두고 엔터를 누르세요)")

        for account in ACCOUNTS.keys():
            setup_account(vault, account)

        print("\n" + "=" * 50)

    if vault:
        save_vault(vault)
        print("\n✅ 설정 완료!")
        print("\n실행 예시:")
        print("  python craigslist_auto_rpa.py --dry-run")
        print("  python craigslist_auto_rpa.py --account gray --limit 1")
    else:
        print("\n⚠️  저장된 계정이 없습니다.")

if __name__ == "__main__":
    main()
