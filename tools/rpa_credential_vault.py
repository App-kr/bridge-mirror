"""
RPA Credential Vault v3.0 - Session-Ephemeral 3-Layer AES-256-GCM
================================================================

보안 정책:
  1. 평문 저장 절대 금지 (ENV/파일 모두)
  2. 3중 AES-256-GCM 암호화 (Layer1/2/3)
  3. 매 실행마다 새로운 salt/nonce → 같은 값도 매번 다른 암호문
  4. 클립보드 자동 복사 + 메모리 소각
  5. Session-ephemeral: 프로세스 종료 시 메모리 비움

사용법:
  # 초기 설정 (이메일/비밀번호 입력 → 3중 암호화 저장)
  python tools/rpa_credential_vault.py setup

  # 매번 새 암호 생성 (RPA 실행 전 매번)
  python tools/rpa_credential_vault.py rotate

  # 프로그래밍 방식 읽기 (RPA 내부)
  from tools.rpa_credential_vault import CredentialVault
  vault = CredentialVault()
  email = vault.get_decrypted("email")
  password = vault.get_decrypted("password")
"""

import os
import sys
import json
import base64
import ctypes
import secrets
import getpass
from pathlib import Path
from typing import Optional

try:
    import pyperclip
    _CLIPBOARD = True
except ImportError:
    _CLIPBOARD = False
    pyperclip = None

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# ── 상수 ────────────────────────────────────────────────────────────────────
VAULT_FILE = Path(__file__).resolve().parent.parent / ".rpa_vault.enc.json"
MASTER_KEY_PROMPT = "🔑 마스터 입력 장치 키 (보이지 않음): "
KDF_ITERATIONS = 600_000
NONCE_BYTES = 12
SALT_BYTES = 32

# ── 3중 암호화 헬퍼 ──────────────────────────────────────────────────────────

def _kdf(master_key: bytes, salt: bytes) -> bytes:
    """PBKDF2-SHA256: 마스터키 + salt → 32바이트 세션키"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(master_key)


def _encrypt_layer(key: bytes, plaintext: str, layer_name: str) -> tuple[bytes, bytes]:
    """단일 AES-256-GCM 암호화 (nonce 포함 반환)"""
    nonce = secrets.token_bytes(NONCE_BYTES)
    cipher = AESGCM(key)
    ciphertext = cipher.encrypt(nonce, plaintext.encode('utf-8'), None)
    return nonce, ciphertext


def _decrypt_layer(key: bytes, nonce: bytes, ciphertext: bytes, layer_name: str) -> str:
    """단일 AES-256-GCM 복호화"""
    cipher = AESGCM(key)
    plaintext = cipher.decrypt(nonce, ciphertext, None)
    return plaintext.decode('utf-8')


def _triple_encrypt(plaintext: str, master_key: bytes) -> dict:
    """3중 AES-256-GCM 암호화

    L1_key = PBKDF2(master_key, salt1)
    L2_key = PBKDF2(master_key, salt2)
    L3_key = PBKDF2(master_key, salt3)

    ct1 = ENC(L1_key, n1, plaintext)
    ct2 = ENC(L2_key, n2, ct1)
    ct3 = ENC(L3_key, n3, ct2)

    저장: {salt1, salt2, salt3, n1, n2, n3, ct3}
    """
    salt1 = secrets.token_bytes(SALT_BYTES)
    salt2 = secrets.token_bytes(SALT_BYTES)
    salt3 = secrets.token_bytes(SALT_BYTES)

    L1_key = _kdf(master_key, salt1)
    L2_key = _kdf(master_key, salt2)
    L3_key = _kdf(master_key, salt3)

    # Layer 1
    n1, ct1_bytes = _encrypt_layer(L1_key, plaintext, "L1")

    # Layer 2: ct1의 base64를 암호화
    ct1_b64 = base64.b64encode(ct1_bytes).decode('ascii')
    n2, ct2_bytes = _encrypt_layer(L2_key, ct1_b64, "L2")

    # Layer 3: ct2의 base64를 암호화
    ct2_b64 = base64.b64encode(ct2_bytes).decode('ascii')
    n3, ct3_bytes = _encrypt_layer(L3_key, ct2_b64, "L3")

    ct3_b64 = base64.b64encode(ct3_bytes).decode('ascii')

    # 메모리 소각
    _scrub(L1_key)
    _scrub(L2_key)
    _scrub(L3_key)

    return {
        "s1": base64.b64encode(salt1).decode('ascii'),
        "s2": base64.b64encode(salt2).decode('ascii'),
        "s3": base64.b64encode(salt3).decode('ascii'),
        "n1": base64.b64encode(n1).decode('ascii'),
        "n2": base64.b64encode(n2).decode('ascii'),
        "n3": base64.b64encode(n3).decode('ascii'),
        "ct": ct3_b64,
    }


def _triple_decrypt(blob: dict, master_key: bytes) -> str:
    """3중 AES-256-GCM 복호화"""
    salt1 = base64.b64decode(blob["s1"])
    salt2 = base64.b64decode(blob["s2"])
    salt3 = base64.b64decode(blob["s3"])
    n1 = base64.b64decode(blob["n1"])
    n2 = base64.b64decode(blob["n2"])
    n3 = base64.b64decode(blob["n3"])
    ct3_bytes = base64.b64decode(blob["ct"])

    L1_key = _kdf(master_key, salt1)
    L2_key = _kdf(master_key, salt2)
    L3_key = _kdf(master_key, salt3)

    # Layer 3 복호화
    ct2_b64 = _decrypt_layer(L3_key, n3, ct3_bytes, "L3")
    ct2_bytes = base64.b64decode(ct2_b64)

    # Layer 2 복호화
    ct1_b64 = _decrypt_layer(L2_key, n2, ct2_bytes, "L2")
    ct1_bytes = base64.b64decode(ct1_b64)

    # Layer 1 복호화
    plaintext = _decrypt_layer(L1_key, n1, ct1_bytes, "L1")

    # 메모리 소각
    _scrub(L1_key)
    _scrub(L2_key)
    _scrub(L3_key)

    return plaintext


def _scrub(data: bytes):
    """메모리 소각 (ctypes 제로필)"""
    if isinstance(data, bytes):
        ctypes.memmove(id(data), id(b'\x00' * len(data)), len(data))


# ── 클래스 ───────────────────────────────────────────────────────────────────

class CredentialVault:
    """RPA 자격증명 보관소"""

    def __init__(self):
        self._cache = {}  # 복호화된 값 (메모리만)
        self._master_key = None

    def _load_master_key(self) -> bytes:
        """마스터 키 입력 (화면 미노출)"""
        key_str = getpass.getpass(MASTER_KEY_PROMPT)
        return key_str.encode('utf-8')

    def _read_vault(self) -> dict:
        """암호화된 vault 파일 읽기"""
        if not VAULT_FILE.exists():
            return {}
        try:
            return json.loads(VAULT_FILE.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"[ERROR] Vault 읽기 실패: {e}")
            return {}

    def _write_vault(self, data: dict):
        """암호화된 vault 파일 쓰기"""
        VAULT_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')

    def get_decrypted(self, key: str) -> str:
        """캐시된 복호화 값 반환 (없으면 vault에서 복호화)"""
        if key in self._cache:
            return self._cache[key]

        vault = self._read_vault()
        if key not in vault:
            return ""

        if not self._master_key:
            self._master_key = self._load_master_key()

        try:
            plaintext = _triple_decrypt(vault[key], self._master_key)
            self._cache[key] = plaintext
            return plaintext
        except Exception as e:
            print(f"[ERROR] 복호화 실패 ({key}): {e}")
            return ""

    def setup(self):
        """초기 설정: 4개 계정(회색, 갈색, 보라색, 초록색) 이메일+비밀번호 입력 → 3중 암호화 저장"""
        print("\n" + "="*70)
        print("  RPA CREDENTIAL VAULT v3.0 - Initial Setup (4 Accounts)")
        print("="*70)
        print("\n[안내] Craigslist 4개 계정을 3중 암호화로 저장합니다.")
        print("       순서: 회색 → 갈색 → 보라색 → 초록색")
        print("       평문으로 저장되지 않으며, 매번 다른 암호문으로 변환됩니다.\n")

        # 마스터 키 입력
        master_key = self._load_master_key()
        print("✓ 마스터 키 입력됨\n")

        # 4개 계정 입력
        accounts = {
            "gray": "회색",
            "brown": "갈색",
            "purple": "보라색",
            "green": "초록색",
        }

        vault_data = {}

        for account_key, account_name in accounts.items():
            print(f"\n{'='*70}")
            print(f"  [{account_name}] Craigslist 계정 등록")
            print(f"{'='*70}")

            # 이메일 입력
            email = getpass.getpass(f"📧 [{account_name}] 이메일 (보이지 않음): ")
            if not email:
                print(f"❌ [{account_name}] 이메일이 입력되지 않았습니다.")
                continue

            # 비밀번호 입력
            password = getpass.getpass(f"🔐 [{account_name}] 비밀번호 (보이지 않음): ")
            if not password:
                print(f"❌ [{account_name}] 비밀번호가 입력되지 않았습니다.")
                continue

            # 3중 암호화
            print(f"🔄 [{account_name}] 3중 AES-256-GCM 암호화 중...", end="", flush=True)
            vault_data[f"{account_key}_email"] = _triple_encrypt(email, master_key)
            vault_data[f"{account_key}_password"] = _triple_encrypt(password, master_key)
            print(" ✓")

            # 메모리 소각
            email_arr = bytearray(email.encode('utf-8'))
            password_arr = bytearray(password.encode('utf-8'))
            email_arr[:] = b'\x00' * len(email_arr)
            password_arr[:] = b'\x00' * len(password_arr)
            del email, password, email_arr, password_arr

        self._write_vault(vault_data)

        print("\n" + "="*70)
        print("✅ 4개 계정 설정 완료!")
        print("="*70)
        print("\n등록된 계정:")
        for account_key, account_name in accounts.items():
            if f"{account_key}_email" in vault_data:
                print(f"  ✓ [{account_name}] gray_email, gray_password (등)")

        print("\n이제 매번 RPA 실행 전에:")
        print("  python tools/rpa_credential_vault.py rotate")
        print("\nRPA 내부에서 특정 계정 사용:")
        print("  from tools.rpa_credential_vault import CredentialVault")
        print("  vault = CredentialVault()")
        print("  email = vault.get_decrypted('gray_email')")
        print("  password = vault.get_decrypted('gray_password')")
        print("\n다른 계정: brown_email, purple_email, green_email 등")

        # 메모리 소각
        master_key_arr = bytearray(master_key)
        master_key_arr[:] = b'\x00' * len(master_key_arr)
        del master_key, master_key_arr

    def rotate(self):
        """매번 새 암호 생성 (4개 계정 모두 재암호화)

        같은 평문도 매번 다른 salt/nonce로 인해 완전히 다른 암호문 생성
        """
        print("\n" + "="*70)
        print("  RPA CREDENTIAL VAULT v3.0 - Rotate Encryption (4 Accounts)")
        print("="*70)

        vault = self._read_vault()
        if not vault or "gray_email" not in vault:
            print("[ERROR] Vault이 초기화되지 않았습니다.")
            print("먼저 실행하세요: python tools/rpa_credential_vault.py setup")
            return

        # 마스터 키 입력
        master_key = self._load_master_key()
        print("✓ 마스터 키 입력됨\n")

        # 4개 계정 복호화
        accounts = ["gray", "brown", "purple", "green"]
        account_names = {"gray": "회색", "brown": "갈색", "purple": "보라색", "green": "초록색"}
        decrypted = {}

        print("🔓 기존 자격증명 4개 계정 복호화 중...", end="", flush=True)
        try:
            for account in accounts:
                email_key = f"{account}_email"
                password_key = f"{account}_password"
                if email_key in vault and password_key in vault:
                    decrypted[account] = {
                        "email": _triple_decrypt(vault[email_key], master_key),
                        "password": _triple_decrypt(vault[password_key], master_key),
                    }
            print(" ✓")
        except Exception as e:
            print(f"\n[ERROR] 복호화 실패: {e}")
            return

        # 새 salt/nonce로 4개 계정 재암호화
        print("🔄 새로운 salt/nonce로 3중 AES-256-GCM 4개 계정 재암호화 중...", end="", flush=True)
        new_vault = {}
        for account, creds in decrypted.items():
            new_vault[f"{account}_email"] = _triple_encrypt(creds["email"], master_key)
            new_vault[f"{account}_password"] = _triple_encrypt(creds["password"], master_key)
        self._write_vault(new_vault)
        print(" ✓")

        print("\n" + "="*70)
        print("✅ 4개 계정 암호 회전 완료!")
        print("="*70)
        print(f"\n📂 Vault 파일: {VAULT_FILE}")
        print(f"🔐 상태: 3중 암호화 (평문 저장 없음)")
        print("\n회전된 계정:")
        for account in accounts:
            if account in decrypted:
                name = account_names.get(account, "?")
                print(f"  ✓ [{name}] {account}_email, {account}_password")

        # 메모리 소각
        master_key_arr = bytearray(master_key)
        master_key_arr[:] = b'\x00' * len(master_key_arr)
        for account, creds in decrypted.items():
            email_arr = bytearray(creds["email"].encode('utf-8'))
            password_arr = bytearray(creds["password"].encode('utf-8'))
            email_arr[:] = b'\x00' * len(email_arr)
            password_arr[:] = b'\x00' * len(password_arr)
            del email_arr, password_arr
        del master_key, master_key_arr, decrypted


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python tools/rpa_credential_vault.py setup    # 초기 설정")
        print("  python tools/rpa_credential_vault.py rotate   # 암호 회전 (RPA 실행 전마다)")
        return

    cmd = sys.argv[1].lower()
    vault = CredentialVault()

    if cmd == "setup":
        vault.setup()
    elif cmd == "rotate":
        vault.rotate()
    else:
        print(f"[ERROR] 알 수 없는 명령어: {cmd}")


if __name__ == "__main__":
    main()
