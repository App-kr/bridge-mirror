"""
bridge_reset_password.py — 관리자 비밀번호 재설정 CLI
사용법: python tools/bridge_reset_password.py

기능:
  - 새 비밀번호를 화면에 보이지 않게 입력 (getpass)
  - PBKDF2-SHA256 해시 생성 (api_server.py 와 동일 알고리즘)
  - 로컬 .env 파일 자동 업데이트
  - Render 환경변수 업데이트용 해시값 별도 출력
"""

import hashlib
import hmac
import os
import re
import secrets
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

ITERATIONS = 260000


def pbkdf2_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS)
    return f"pbkdf2:sha256:{ITERATIONS}:{salt}:{dk.hex()}"


def verify(password: str, stored: str) -> bool:
    if not stored.startswith("pbkdf2:sha256:"):
        return hmac.compare_digest(password, stored)
    try:
        _, _, iters, salt, dk_hex = stored.split(":", 4)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def update_env(new_hash: str) -> bool:
    if not ENV_PATH.exists():
        print(f"[ERROR] .env 파일 없음: {ENV_PATH}")
        return False
    content = ENV_PATH.read_text(encoding="utf-8")
    if "ADMIN_PASSWORD=" not in content:
        print("[ERROR] .env 에 ADMIN_PASSWORD 항목이 없습니다.")
        return False
    updated = re.sub(
        r"^ADMIN_PASSWORD=.*$",
        f"ADMIN_PASSWORD={new_hash}",
        content,
        flags=re.MULTILINE,
    )
    ENV_PATH.write_text(updated, encoding="utf-8")
    return True


def main():
    print("=" * 55)
    print("  BRIDGE 관리자 비밀번호 재설정")
    print("=" * 55)

    # getpass: 입력 시 화면에 표시 안 됨
    try:
        import getpass
        pw1 = getpass.getpass("새 비밀번호 입력 (화면에 표시 안 됨): ")
        pw2 = getpass.getpass("비밀번호 확인: ")
    except (EOFError, KeyboardInterrupt):
        print("\n[취소됨]")
        sys.exit(0)

    if not pw1:
        print("[ERROR] 비밀번호를 입력하세요.")
        sys.exit(1)

    if pw1 != pw2:
        print("[ERROR] 비밀번호가 일치하지 않습니다.")
        sys.exit(1)

    if len(pw1) < 8:
        print("[ERROR] 비밀번호는 8자 이상이어야 합니다.")
        sys.exit(1)

    # 해시 생성
    new_hash = pbkdf2_hash(pw1)

    # 검증
    assert verify(pw1, new_hash), "해시 검증 실패 — 개발 오류"

    # .env 업데이트
    if update_env(new_hash):
        print("\n[OK] 로컬 .env 업데이트 완료")
    else:
        print("\n[WARN] 로컬 .env 업데이트 실패 — 아래 해시를 수동으로 설정하세요")

    print("\n" + "=" * 55)
    print("  Render 환경변수 업데이트용 해시값:")
    print("=" * 55)
    print(f"\nADMIN_PASSWORD={new_hash}\n")
    print("  위 값을 Render Dashboard > Environment 에 붙여넣으세요.")
    print("=" * 55)


if __name__ == "__main__":
    main()
