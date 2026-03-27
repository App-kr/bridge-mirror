#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
마스터렌더키관리 v1.0
Git 코드 → 3중암호화 마스터 키 등록
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from master_vault import MasterVault
import getpass

def main():
    print("\n" + "="*60)
    print("  🔐  마스터렌더키관리 v1.0")
    print("="*60)
    print()

    vault = MasterVault()

    print("📌 Git 코드를 입력하여 3중암호화 마스터 키를 등록합니다")
    print()

    # Git 코드 입력
    git_code = getpass.getpass("🔑 Git 코드 입력 (표시 안 됨): ")

    if not git_code.strip():
        print("\n❌ 코드가 비어있습니다. 다시 시도하세요.\n")
        return

    # 확인
    confirm = getpass.getpass("🔑 한 번 더 입력 (확인): ")

    if git_code != confirm:
        print("\n❌ 코드가 일치하지 않습니다.\n")
        return

    # 저장
    print("\n⏳ 3중암호화 처리 중...")
    vault.seal("BRIDGE_FIELD_KEY", git_code)

    print("✅ 저장 완료!\n")
    print("📋 암호화 정보:")
    print(f"   키 이름: BRIDGE_FIELD_KEY")
    print(f"   상태: 저장됨 (Vault)")
    print(f"   보안: AES-256-GCM (3중)")
    print()

    # 검증
    test = vault.unseal("BRIDGE_FIELD_KEY")
    print(f"✓ 검증: 길이 {len(test)}자, 앞 4자: {test[:4]}***")
    print()
    print("="*60)
    print("완료! BRIDGE_FIELD_KEY가 등록되었습니다.\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹  취소되었습니다.\n")
    except Exception as e:
        print(f"\n❌ 오류: {e}\n")
