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
    print("\n" + "="*60)
    print("  === [Render 환경변수 보안 암호화 도구 (V4 Quantum)] ===")
    print("="*60)
    print("\n[안내] Render 대시보드 변수값(구글 JSON 등)을 'ENC:' 암호문으로 변환합니다.")
    print("서버 실행 시 RENDER_MASTER_KEY를 통해 자동으로 복호화됩니다.\n")
    
    # 1. 마스터 키 보안 입력
    try:
        master_pass = getpass.getpass("🔑 1. Render 마스터 키 입력 (화면에 노출되지 않음): ").strip()
        if not master_pass:
            print("\n❌ 오류: 마스터 키가 입력되지 않았습니다.")
            return
        
        master_key_bytes = bytearray(master_pass.encode('utf-8'))
        
        # 2. 암호화 대상 입력
        print("\n📝 2. 암호화할 원본 텍스트(평문) 또는 파일명을 입력하세요.")
        val = input("평문/파일명: ").strip()
        
        if not val:
            print("\n❌ 오류: 입력값이 없습니다.")
            return

        if os.path.exists(val) and os.path.isfile(val):
            print(f"\n📂 [{val}] 파일을 읽어오는 중...")
            with open(val, "r", encoding="utf-8") as f:
                val = f.read()
                
        # 3. 암호화 실행
        enc_val = encrypt_value(master_key_bytes, val)
        
        print("\n" + "✨"*30)
        print("🎉 암호화 성공! 아래 텍스트를 Render Value 칸에 붙여넣으세요.")
        print("="*60)
        print(enc_val)
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 실행 중 오류 발생: {e}")
    finally:
        # 보안을 위해 메모리 상의 마스터 키 즉시 소거
        if 'master_key_bytes' in locals():
            master_key_bytes[:] = b'\x00' * len(master_key_bytes)
            del master_key_bytes
        print("\n🔐 보안 처리가 완료되었습니다. 프로그램을 종료합니다.")
        input("\n[Enter] 키를 누르면 종료됩니다...")

if __name__ == "__main__":
    main()
