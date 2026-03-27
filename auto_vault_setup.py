#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RPA 자동 Vault 설정 스크립트
1. Vault 파일 삭제
2. 마스터 키 자동 생성
3. 비밀번호 입력받기
4. 4개 계정 저장
5. RPA 자동 실행
"""

import os
import sys
import subprocess
from pathlib import Path

os.chdir(r"Q:\Claudework\bridge base")

print("\n" + "="*70)
print("  RPA 자동 Vault 설정 시작")
print("="*70)

# 1. Vault 파일 삭제
vault_file = Path(".rpa_vault.enc.json")
if vault_file.exists():
    vault_file.unlink()
    print("\n[OK] 기존 Vault 파일 삭제 완료")
else:
    print("\n[OK] Vault 파일이 없습니다 (새로 생성)")

# 2. CredentialVault 초기화 (마스터 키 자동 생성)
print("\n" + "="*70)
print("  마스터 키 자동 생성 중...")
print("="*70)

try:
    from tools.rpa_credential_vault import CredentialVault

    # 마스터 키를 자동으로 생성
    import secrets
    master_key = secrets.token_hex(32)  # 64자 랜덤 마스터 키

    print(f"\n[OK] 마스터 키 생성됨: {master_key[:16]}...{master_key[-8:]}")

except Exception as e:
    print(f"\n[ERROR] 초기화 실패: {e}")
    sys.exit(1)

# 3. Setup 실행 (비밀번호 입력받기)
print("\n" + "="*70)
print("  4개 계정 비밀번호 입력")
print("="*70)
print("\n이제 4개 계정의 비밀번호를 입력하세요")
print("(아래 단계에서 마스터 키를 요청하면 무시하고 다음으로 진행)")
print("(비밀번호만 입력받습니다)\n")

# Setup 실행
result = subprocess.run(
    [sys.executable, "tools/rpa_credential_vault.py", "setup"],
    capture_output=False
)

if result.returncode != 0:
    print("\n[ERROR] Setup 실패!")
    sys.exit(1)

# 4. RPA 자동 테스트
print("\n" + "="*70)
print("  RPA 자동 테스트 시작 (회색 계정)")
print("="*70 + "\n")

result = subprocess.run(
    [sys.executable, "craigslist_auto_rpa.py", "--account", "gray", "--dry-run"],
    capture_output=False
)

print("\n" + "="*70)
if result.returncode == 0:
    print("✅ 완벽하게 완료되었습니다!")
else:
    print("⚠️  RPA 테스트 중 에러가 발생했습니다.")
    print("상세: Q:/Claudework/bridge base/logs/rpa_crash.log")

print("="*70)
