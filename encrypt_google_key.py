import os
import sys
import base64
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import hashlib

def encrypt_google_json():
    # 1. 암호화 키 가져오기 (로컬 V4 Vault 사용)
    _vault_path = Path("Q:/")
    if str(_vault_path) not in sys.path:
        sys.path.insert(0, str(_vault_path))

    try:
        from secure_vault_v3 import PolymorphicQuantumVault
        vault = PolymorphicQuantumVault()
        raw_key_bytes = vault.unseal_and_roll("BRIDGE_FIELD_KEY")
    except Exception as e:
        print(f"V4 Vault 오류: {e}")
        print("터미널에 'python Q:/secure_vault_v3.py' 를 치고 비밀번호를 넣어 V4 금고를 활성화하세요.")
        sys.exit(1)

    key = hashlib.sha256(raw_key_bytes).digest()

    # 2. JSON 읽어서 암호화
    json_path = Path("google_key.json")
    if not json_path.exists():
        print(f"에러: [ {json_path} ] 파일이 폴더에 없습니다!")
        print(f"구글 콘솔에서 다운로드한 텍스트를 {json_path} 이름으로 같은 폴더에 저장 후 재실행하세요.")
        sys.exit(1)

    with open(json_path, "rb") as f:
        plaintext = f.read()

    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, None)
    
    # 12-byte nonce + ciphertext 형태를 base64로 묶기
    payload = nonce + ciphertext_with_tag
    encrypted_b64 = base64.b64encode(payload).decode("ascii")

    # 3. 렌더 입력용 or 파일 저장
    enc_path = Path("google_key.enc")
    with open(enc_path, "w") as f:
        f.write(encrypted_b64)

    # 4. 메모리 소각
    raw_key_bytes[:] = b'\x00' * len(raw_key_bytes)
    del raw_key_bytes

    print("\n=======================================================")
    print("✅ 최고 보안 수준으로 구글 JSON 평문이 암호화되었습니다!")
    print(f"✅ 생성된 파일: {enc_path.absolute()}")
    print("=======================================================\n")
    print("⭐ [중요 1] 이제 원본인 'google_key.json' 은 삭제하시고 휴지통도 비워주세요!")
    print("⭐ [중요 2] 암호화된 텍스트를 복사하여 Render의 [GOOGLE_SERVICE_ACCOUNT_JSON] 칸에 넣으세요.")
    print("⭐ (서버가 켜질 때 메모리에서 이를 역산하여 자동으로 복호화합니다.)\n")

if __name__ == "__main__":
    encrypt_google_json()
