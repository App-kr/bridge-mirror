"""T3v1 암호화 단위 테스트 — 마이그레이션 전 안전성 검증"""
import sys, os
sys.path.insert(0, 'Q:/Claudework/bridge base')

try:
    from tools.bx import load_to_env
    load_to_env()
except Exception as e:
    print("BX:", e)

os.environ.setdefault("BRIDGE_FIELD_KEY", os.environ.get("BRIDGE_FIELD_KEY", ""))

from security_vault import (
    t3_encrypt, t3_decrypt, is_t3_encrypted,
    auto_decrypt_value, decrypt_field, is_encrypted
)

ok = 0
fail = 0

def check(label, cond):
    global ok, fail
    if cond:
        print("  OK  " + label)
        ok += 1
    else:
        print("  FAIL " + label)
        fail += 1

print("=== T3v1 단위 테스트 ===")
print()

# 1) 기본 암호화/복호화
plain = "1990-01-15"
enc = t3_encrypt(plain, "dob")
dec = t3_decrypt(enc, "dob")
check("encrypt/decrypt roundtrip", dec == plain)
check("is_t3_encrypted = True", is_t3_encrypted(enc))
check("is_t3_encrypted(plain) = False", not is_t3_encrypted(plain))
check("is_encrypted(enc) = True", is_encrypted(enc))
check("is_encrypted(plain) = False", not is_encrypted(plain))
check("len >= 60", len(enc) >= 60)
print("  INFO enc len =", len(enc), "(기준: >= 60)")

# 2) 같은 값도 매번 다른 암호문
enc2 = t3_encrypt(plain, "dob")
check("nonce 랜덤 (enc != enc2)", enc != enc2)
check("enc2도 복호화 정상", t3_decrypt(enc2, "dob") == plain)

# 3) 컬럼명 분리 (다른 컬럼키로 복호화 실패 확인)
enc3 = t3_encrypt(plain, "dob")
try:
    t3_decrypt(enc3, "nationality")   # 다른 컬럼 → 복호화 실패 기대
    check("컬럼명 키 분리", False)     # 성공하면 버그
except Exception:
    check("컬럼명 키 분리 (다른 컬럼 → 복호화 실패)", True)

# 4) decrypt_field pass-through
check("decrypt_field(plain) = plain", decrypt_field("Seoul") == "Seoul")
check("decrypt_field(None) = None", decrypt_field(None) is None)
check("decrypt_field('') = ''", decrypt_field("") == "")

# 5) auto_decrypt_value
check("auto_decrypt_value(enc) == plain", auto_decrypt_value(enc, "dob") == plain)
check("auto_decrypt_value(plain) == plain", auto_decrypt_value("Seoul") == "Seoul")

# 6) 한국어/특수문자
for s in ["홍길동", "test@example.com", "서울 강남구", "O+", "NONE"]:
    enc_s = t3_encrypt(s, "test")
    dec_s = t3_decrypt(enc_s, "test")
    check("unicode: " + s, dec_s == s)

print()
print("=== 결과: OK=" + str(ok) + " FAIL=" + str(fail) + " ===")
sys.exit(0 if fail == 0 else 1)
