"""
관리자 비밀번호 변경 스크립트
- 입력 시 화면에 글자 안 보임 (getpass)
- PBKDF2-SHA256 해시로 .env 자동 업데이트
- 실행: python scripts/set_admin_password.py
"""
import os
import sys
import hashlib
import hmac
import secrets
import re
from getpass import getpass
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 260000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    return f"pbkdf2:sha256:{iterations}:{salt}:{dk.hex()}"

def update_env(new_hash: str):
    content = ENV_PATH.read_text(encoding="utf-8")
    pattern = r"^ADMIN_PASSWORD=.*$"
    new_line = f"ADMIN_PASSWORD={new_hash}"
    if re.search(pattern, content, re.MULTILINE):
        updated = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        updated = content.rstrip() + f"\n{new_line}\n"
    ENV_PATH.write_text(updated, encoding="utf-8")

def main():
    print("\n=== BRIDGE 관리자 비밀번호 변경 ===")
    print("(입력하는 글자는 화면에 표시되지 않습니다)\n")

    pw = getpass("새 비밀번호: ")
    if len(pw) < 8:
        print("❌ 비밀번호는 8자 이상이어야 합니다.")
        sys.exit(1)

    pw_confirm = getpass("비밀번호 확인: ")
    if pw != pw_confirm:
        print("❌ 비밀번호가 일치하지 않습니다.")
        sys.exit(1)

    print("\n해시 생성 중...")
    hashed = hash_password(pw)
    update_env(hashed)

    print("✅ 비밀번호 변경 완료 (.env 업데이트됨)")
    print("⚠️  서버를 재시작해야 적용됩니다.\n")

if __name__ == "__main__":
    main()
