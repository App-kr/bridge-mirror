"""
bridge_reset_password.py — 관리자 비밀번호 재설정 CLI
사용법: 터미널에서 직접 실행 (Claude Code 아닌 별도 터미널)

  "C:/Users/Scarlett/AppData/Local/Programs/Python/Python313/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/bridge_reset_password.py"

기능:
  - 새 비밀번호를 화면에 보이지 않게 입력 (getpass)
  - PBKDF2-SHA256 해시 생성 (api_server.py 와 동일 알고리즘)
  - BX (DPAPI 암호화 저장소) 자동 업데이트
  - Render 환경변수 업데이트용 해시값 별도 출력
"""

import hashlib
import hmac
import os
import secrets
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
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


def main():
    print("=" * 55)
    print("  BRIDGE 관리자 비밀번호 재설정")
    print("  입력 내용은 화면에 표시되지 않습니다")
    print("=" * 55)

    try:
        import getpass
        pw1 = getpass.getpass("\n  새 비밀번호: ")
        pw2 = getpass.getpass("  비밀번호 확인: ")
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

    # 해시 생성 + 검증
    new_hash = pbkdf2_hash(pw1)
    assert verify(pw1, new_hash), "해시 검증 실패"

    # BX에 저장 (DPAPI 암호화)
    sys.path.insert(0, str(BASE_DIR))
    try:
        from tools.bx import _store
        _store("ADMIN_PASSWORD", new_hash)
        print("\n  [OK] BX 저장 완료 (DPAPI 암호화)")
    except Exception as e:
        print(f"\n  [WARN] BX 저장 실패: {e}")
        print("  아래 해시를 수동으로 bx.py set ADMIN_PASSWORD 로 저장하세요")

    # Render용 해시 출력
    print("\n" + "=" * 55)
    print("  Render 환경변수 업데이트:")
    print("=" * 55)
    print(f"\n  ADMIN_PASSWORD={new_hash}\n")
    print("  Render Dashboard > Environment 에 붙여넣으세요.")
    print("=" * 55)


if __name__ == "__main__":
    main()
