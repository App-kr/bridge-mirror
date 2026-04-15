"""RPA 계정 비밀번호 설정"""
import sys, os, getpass, secrets
sys.path.insert(0, os.path.dirname(__file__))

from tools.rpa_credential_vault import CredentialVault, _save_mk_cache, ACCOUNTS

ACCT_ORDER = ["gray", "green", "brown", "purple"]

print()
print("=" * 50)
print("  BRIDGE RPA 계정 비밀번호 설정")
print("=" * 50)
print()

pws = {}
for ak in ACCT_ORDER:
    email = ACCOUNTS[ak]["email"]
    print(f"  {email}")
    pw = getpass.getpass("  비밀번호: ")
    if not pw:
        print("  취소됨.")
        sys.exit(1)
    pws[ak] = pw
    print()

# 마스터키 자동생성 (사용자 입력 불필요)
mk_str = secrets.token_hex(32)

v = CredentialVault()
ok = v.setup_from_gui(mk_str, pws)
if ok:
    print("=" * 50)
    print("  저장 완료! RPA.vbs 실행하세요.")
    print("=" * 50)
else:
    print("저장 실패.")
    sys.exit(1)
