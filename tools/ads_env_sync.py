"""
ads_env_sync.py — bx 저장값을 bridge_ads/.env.local 에 기록

실행: "C:/Users/Scarlett/AppData/Local/Programs/Python/Python313/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/ads_env_sync.py"

.env.local은 gitignore 대상 — 평문이지만 로컬 전용 (배포 환경에는 미사용)
Render/Vercel 배포 시에는 pw.py GUI의 Render 동기화 버튼 사용
"""
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ADS_DIR  = Path(r"Q:\Claudework\bridge_ads")
ENV_PATH = ADS_DIR / ".env.local"

sys.path.insert(0, str(BASE_DIR))
from tools.bx import _read

# bx 키 → .env.local 변수명 매핑
KEY_MAP = {
    "ADS_JWT_SECRET":             "JWT_SECRET",
    "ADS_CSRF_SECRET":            "CSRF_SECRET",
    "ADS_OTP_HMAC_SECRET":        "OTP_HMAC_SECRET",
    "ADS_FIELD_ENCRYPTION_KEY":   "FIELD_ENCRYPTION_KEY",
    "ADS_SMTP_PASS":              "SMTP_PASS",
    "ADS_GOOGLE_CLIENT_ID":       "GOOGLE_CLIENT_ID",
    "ADS_GOOGLE_CLIENT_SECRET":   "GOOGLE_CLIENT_SECRET",
    "ADS_PAYPAL_CLIENT_ID":       "PAYPAL_CLIENT_ID",
    "ADS_PAYPAL_CLIENT_SECRET":   "PAYPAL_CLIENT_SECRET",
    "ADS_PAYPAL_WEBHOOK_ID":      "PAYPAL_WEBHOOK_ID",
}

# 고정값 (bx 아닌 직접 설정)
STATIC = {
    "NODE_ENV":         "development",
    "APP_URL":          "http://localhost:3002",
    "SMTP_HOST":        "smtp.gmail.com",
    "SMTP_PORT":        "587",
    "SMTP_USER":        "koreadobby@gmail.com",
    "SMTP_FROM":        "BRIDGE Ads <koreadobby@gmail.com>",
    "GOOGLE_REDIRECT_URI": "http://localhost:3002/api/auth/google/callback",
    "PAYPAL_ENV":       "sandbox",
    "BANK_NAME":        "",
    "BANK_ACCOUNT":     "",
    "BANK_HOLDER":      "",
    "FEATURE_CARD_PAYMENT": "false",
}

lines = ["# bridge_ads .env.local — bx 자동 생성 (수정 금지, ads_env_sync.py 재실행으로 갱신)\n"]

missing = []
for bx_key, env_key in KEY_MAP.items():
    val = _read(bx_key) or ""
    if not val:
        missing.append(bx_key)
    lines.append(f"{env_key}={val}\n")

lines.append("\n# 고정값\n")
for k, v in STATIC.items():
    lines.append(f"{k}={v}\n")

ENV_PATH.write_text("".join(lines), encoding="utf-8")
print(f".env.local 작성 완료: {ENV_PATH}")

if missing:
    print(f"\n⚠ bx 미설정 항목 ({len(missing)}개) — pw.py에서 입력 필요:")
    for k in missing:
        print(f"  - {k}")
else:
    print("모든 키 정상 로드됨")
