"""
ads_secrets_init.py — bridge_ads 자동 생성 시크릿 4종을 bx에 저장

실행: "C:/Users/Scarlett/AppData/Local/Programs/Python/Python313/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/ads_secrets_init.py"

생성되는 키 (64바이트 base64url):
  ADS_JWT_SECRET / ADS_CSRF_SECRET / ADS_OTP_HMAC_SECRET / ADS_FIELD_ENCRYPTION_KEY

값은 화면에 출력되지 않음 — bx DPAPI 저장 후 "OK" 확인만 출력
"""
import sys
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.bx import _store, _read

KEYS = [
    "ADS_JWT_SECRET",
    "ADS_CSRF_SECRET",
    "ADS_OTP_HMAC_SECRET",
    "ADS_FIELD_ENCRYPTION_KEY",
]

print("bridge_ads 시크릿 초기화")
print("-" * 36)

for key in KEYS:
    existing = _read(key)
    if existing:
        print(f"  {key:<32} [SKIP — already set]")
        continue
    value = secrets.token_urlsafe(64)
    _store(key, value)
    # 저장 확인 (값 미출력)
    check = _read(key)
    if check == value:
        print(f"  {key:<32} [OK]")
    else:
        print(f"  {key:<32} [FAIL]")
    del value, check  # 메모리 소거

print("-" * 36)
print("완료. ads_env_sync.py 를 실행하면 .env.local 에 반영됩니다.")
