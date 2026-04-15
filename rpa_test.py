import sys, os
sys.path.insert(0, r"Q:\Claudework\bridge base")
os.chdir(r"Q:\Claudework\bridge base")

try:
    from tools.rpa_credential_vault import _load_mk_cache
    mk = _load_mk_cache()
    print(f"DPAPI cache: {'있음' if mk else '없음'}")
except Exception as e:
    print(f"DPAPI 오류: {e}")

try:
    from tools.rpa_credential_vault import CredentialVault
    v = CredentialVault()
    email = v.get_decrypted("gray_email")
    print(f"gray_email: {email}")
except Exception as e:
    print(f"Vault 오류: {e}")
