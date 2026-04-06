#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BRIDGE SMTP 자격증명 Vault 저장 스크립트
────────────────────────────────────────
사용법:
    python tools/store_smtp_credentials.py

동작:
    1. BRIDGE_FIELD_KEY 입력 (화면 미표시)
    2. SMTP 이메일/비밀번호 입력 (화면 미표시)
    3. T3v1 3중 AES-256-GCM 암호화 후 tools/smtp_creds.enc.json 저장

주의:
    - 입력값은 메모리에만 존재하며 화면에 표시되지 않습니다
    - tools/smtp_creds.enc.json은 git 커밋 가능 (암호화된 상태)
    - 이 스크립트는 사용 후 Claude가 자동 삭제합니다
"""

import sys
import os
import json
import getpass
import hashlib
import secrets
import base64
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# T3v1 내장 암호화 (security_vault.py 의존 없음 — 독립 실행 가능)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    print("❌ cryptography 패키지 필요: pip install cryptography")
    sys.exit(1)

_T3_MAGIC = b"T3v1"


def _t3_encrypt(plaintext: str, field_key: bytes, column_name: str = "") -> str:
    """T3v1 3중 AES-256-GCM 암호화 (내장)."""
    base = hashlib.sha256(field_key).digest()
    col  = column_name.encode()
    n1 = secrets.token_bytes(12)
    n2 = secrets.token_bytes(12)
    n3 = secrets.token_bytes(12)
    k1 = hashlib.sha256(base + b"L1" + col).digest()
    k2 = hashlib.sha256(base + b"L2" + n1).digest()
    k3 = hashlib.sha256(base + b"L3" + n2 + n1).digest()
    ct1 = AESGCM(k1).encrypt(n1, plaintext.encode("utf-8"), None)
    ct2 = AESGCM(k2).encrypt(n2, ct1, None)
    ct3 = AESGCM(k3).encrypt(n3, ct2, None)
    return base64.b64encode(_T3_MAGIC + n1 + n2 + n3 + ct3).decode("ascii")


def _t3_verify(encrypted: str, field_key: bytes, column_name: str = "") -> str:
    """복호화 검증 (저장 전 자가 검증)."""
    raw  = base64.b64decode(encrypted)
    if raw[:4] != _T3_MAGIC:
        raise ValueError("T3v1 magic 불일치")
    n1, n2, n3 = raw[4:16], raw[16:28], raw[28:40]
    ct3 = raw[40:]
    base = hashlib.sha256(field_key).digest()
    col  = column_name.encode()
    k1 = hashlib.sha256(base + b"L1" + col).digest()
    k2 = hashlib.sha256(base + b"L2" + n1).digest()
    k3 = hashlib.sha256(base + b"L3" + n2 + n1).digest()
    ct2 = AESGCM(k3).decrypt(n3, ct3, None)
    ct1 = AESGCM(k2).decrypt(n2, ct2, None)
    return AESGCM(k1).decrypt(n1, ct1, None).decode("utf-8")


# ──────────────────────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 54)
    print("  BRIDGE SMTP Vault 저장")
    print("  입력값은 화면에 표시되지 않습니다")
    print("=" * 54)
    print()

    # BRIDGE_FIELD_KEY 입력 (또는 환경변수)
    field_key_raw = os.environ.get("BRIDGE_FIELD_KEY", "").strip()
    if not field_key_raw:
        field_key_raw = getpass.getpass(
            "BRIDGE_FIELD_KEY (Render 환경변수와 동일한 값): "
        ).strip()
    if not field_key_raw:
        print("❌ BRIDGE_FIELD_KEY를 입력해야 합니다.")
        sys.exit(1)
    field_key = field_key_raw.encode("utf-8")

    print()
    print("[네이버 SMTP]")
    naver_user = input("  이메일 (예: bridgejobkr@naver.com): ").strip()
    naver_pass = getpass.getpass("  앱 비밀번호: ").strip()

    print()
    print("[Gmail SMTP]")
    gmail_user = input("  이메일 (예: bridgejobkr@gmail.com): ").strip()
    gmail_pass = getpass.getpass("  앱 비밀번호: ").strip()

    print()
    print("암호화 중...")

    creds = {}

    # 입력값 유효성 검사 + 암호화
    entries = [
        ("NAVER_SMTP_USER", naver_user, "smtp_naver_user"),
        ("NAVER_SMTP_PASS", naver_pass, "smtp_naver_pass"),
        ("GMAIL_SMTP_USER", gmail_user, "smtp_gmail_user"),
        ("GMAIL_SMTP_PASS", gmail_pass, "smtp_gmail_pass"),
    ]

    skipped = []
    for env_key, value, col_name in entries:
        if not value:
            skipped.append(env_key)
            continue
        enc = _t3_encrypt(value, field_key, col_name)
        # 자가 검증
        verified = _t3_verify(enc, field_key, col_name)
        if verified != value:
            print(f"❌ {env_key} 암호화 자가검증 실패 — 중단합니다")
            sys.exit(1)
        creds[env_key] = {"enc": enc, "col": col_name}

    if skipped:
        print(f"  건너뜀 (빈 값): {', '.join(skipped)}")

    out_path = Path(__file__).parent / "smtp_creds.enc.json"
    out_path.write_text(
        json.dumps({"version": "T3v1", "entries": creds}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"✅ 암호화 저장 완료: {out_path}")
    print(f"   저장된 키: {list(creds.keys())}")
    print()
    print("다음 단계:")
    print("  Claude에게 '계속 진행해줘'라고 하세요.")
    print("  (Claude가 api_server.py 연동 + .env 정리 + 스크립트 삭제)")

    # 메모리 소각
    field_key = bytearray(field_key)
    field_key[:] = b'\x00' * len(field_key)


if __name__ == "__main__":
    main()
