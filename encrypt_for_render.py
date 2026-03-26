import os
import sys
import base64
import hashlib
import getpass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def encrypt_value(master_key_bytes: bytearray, plaintext_str: str) -> str:
    key = hashlib.sha256(master_key_bytes).digest()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext_str.encode('utf-8'), None)
    return "ENC:" + base64.b64encode(nonce + ciphertext).decode('ascii')

def main():
    print("\n=== [초간단 Render 환경변수 암호화 툴 (독립형)] ===")
    print("원격 서버 대시보드에 노출하기 싫은 값(구글 JSON 등)을 넣으면,")
    print("해독 불가능한 'ENC:' 시작 문자열로 꼬아서 변환해줍니다.\n")
    
    # 1. 마스터 키 직접 입력 방어 로직
    master_pass = getpass.getpass("✅ 1. Render에 등록할 마스터 키(RENDER_MASTER_KEY)를 치세요 (화면에 안보임): ").strip()
    if not master_pass:
        print("에러: 마스터 키가 없으면 암호화할 수 없습니다.")
        sys.exit(1)
        
    master_key_bytes = bytearray(master_pass.encode('utf-8'))
    
    # 2. 입력값 판별
    print("\n✅ 2. 암호화할 텍스트 입력 (또는 파일명, 예: google_key.json)")
    val = input("입력: ").strip()
    
    if os.path.exists(val) and os.path.isfile(val):
        print(f"[{val}] 파일의 내용을 읽어와 암호화합니다...")
        with open(val, "r", encoding="utf-8") as f:
            val = f.read()
            
    try:
        enc_val = encrypt_value(master_key_bytes, val)
        
        print("\n🎉 성공적으로 모든 글자를 암호문으로 꼬아놓았습니다!")
        print("아래 텍스트를 복사해서 Render 대시보드의 Value 칸에 그대로 붙여넣으세요:\n")
        print("-" * 60)
        print(enc_val)
        print("-" * 60)
        print("\n(참고: 서버 실행 시 os.environ 코드가 '마스터 키'를 써서 원본으로 풀어 씁니다.)\n")
    finally:
        # 보안을 위해 RAM에 올라온 마스터 키 잔상 즉시 파기
        master_key_bytes[:] = b'\x00' * len(master_key_bytes)
        del master_key_bytes

if __name__ == "__main__":
    main()
