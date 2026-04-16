"""
BRIDGE Password Encryption Utility
====================================
Fernet 대칭키 암호화로 .env 비밀번호 보호.

키 파일: .bridge.key (이 파일만 보호하면 됨)
.env 저장 형식: CRAIGSLIST_PASSWORD=ENC:gAAAAABh...

사용법:
  python crypto_util.py encrypt "평문비밀번호"   → 암호문 출력
  python crypto_util.py decrypt "ENC:gAAA..."    → 복호화 출력
  python crypto_util.py setup                     → 대화형 전체 설정
  python crypto_util.py rekey                     → 키 재생성 + .env 재암호화
"""

import sys
from pathlib import Path
from cryptography.fernet import Fernet

KEY_PATH = Path(__file__).resolve().parent / ".bridge.key"


def _load_or_create_key() -> bytes:
    """키 로딩. 없으면 새로 생성."""
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes().strip()
    key = Fernet.generate_key()
    KEY_PATH.write_bytes(key)
    print(f"  [KEY] 새 암호화 키 생성: {KEY_PATH}")
    return key


def _load_key_strict() -> bytes:
    """키 로딩 전용 (복호화용). 키 파일 없으면 RuntimeError — 새 키 생성 금지."""
    if not KEY_PATH.exists():
        raise RuntimeError(f".bridge.key 파일 없음: {KEY_PATH}")
    return KEY_PATH.read_bytes().strip()


def encrypt_value(plain: str) -> str:
    """평문 → ENC:암호문"""
    key = _load_or_create_key()
    f = Fernet(key)
    token = f.encrypt(plain.encode("utf-8")).decode("utf-8")
    return f"ENC:{token}"


def decrypt_value(enc_str: str) -> str:
    """ENC:암호문 → 평문. ENC: 접두사 없으면 그대로 반환.

    복호화 실패 시 새 키를 생성하지 않고 RuntimeError 발생.
    """
    if not enc_str.startswith("ENC:"):
        return enc_str
    key = _load_key_strict()   # 엄격 로딩 — 키 없으면 예외
    f = Fernet(key)
    token = enc_str[4:]
    return f.decrypt(token.encode("utf-8")).decode("utf-8")


def encrypt_env_file(env_path: Path):
    """env 파일의 CRAIGSLIST_PASSWORD 를 암호화."""
    lines = env_path.read_text(encoding="utf-8").splitlines()
    changed = False
    new_lines = []
    for line in lines:
        if line.startswith("CRAIGSLIST_PASSWORD="):
            val = line.split("=", 1)[1]
            if not val.startswith("ENC:"):
                enc = encrypt_value(val)
                new_lines.append(f"CRAIGSLIST_PASSWORD={enc}")
                changed = True
                print(f"  [ENC] {env_path.name}: 비밀번호 암호화 완료")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    if changed:
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return changed


def setup_all():
    """모든 .env 파일의 비밀번호를 대화형으로 암호화."""
    _load_or_create_key()
    base = Path(__file__).resolve().parent
    env_files = sorted(base.glob("*.env")) + (
        [base / ".env"] if (base / ".env").exists() else [])
    # 중복 제거
    seen = set()
    unique = []
    for f in env_files:
        if f.resolve() not in seen:
            seen.add(f.resolve())
            unique.append(f)

    if not unique:
        print("  .env 파일 없음")
        return

    encrypted = 0
    for env_file in unique:
        if encrypt_env_file(env_file):
            encrypted += 1
        else:
            print(f"  [SKIP] {env_file.name}: 이미 암호화됨 또는 비밀번호 없음")

    print(f"\n  완료: {encrypted}개 파일 암호화")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "encrypt":
        if len(sys.argv) < 3:
            print("사용법: python crypto_util.py encrypt \"비밀번호\"")
            return
        result = encrypt_value(sys.argv[2])
        print(result)

    elif cmd == "decrypt":
        if len(sys.argv) < 3:
            print("사용법: python crypto_util.py decrypt \"ENC:...\"")
            return
        result = decrypt_value(sys.argv[2])
        print(result)

    elif cmd == "setup":
        setup_all()

    elif cmd == "rekey":
        print("  [REKEY] 기존 키로 모든 비밀번호 복호화 중...")
        base = Path(__file__).resolve().parent
        env_files = sorted(base.glob("*.env"))
        if (base / ".env").exists():
            env_files.append(base / ".env")

        # 기존 비밀번호 수집
        passwords = {}
        for ef in env_files:
            for line in ef.read_text(encoding="utf-8").splitlines():
                if line.startswith("CRAIGSLIST_PASSWORD="):
                    val = line.split("=", 1)[1]
                    passwords[str(ef)] = decrypt_value(val)

        # 새 키 생성
        KEY_PATH.unlink(missing_ok=True)
        _load_or_create_key()
        print("  [REKEY] 새 키 생성 완료")

        # 재암호화
        for ef in env_files:
            key_str = str(ef)
            if key_str in passwords:
                lines = ef.read_text(encoding="utf-8").splitlines()
                new_lines = []
                for line in lines:
                    if line.startswith("CRAIGSLIST_PASSWORD="):
                        enc = encrypt_value(passwords[key_str])
                        new_lines.append(f"CRAIGSLIST_PASSWORD={enc}")
                    else:
                        new_lines.append(line)
                ef.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                print(f"  [REKEY] {ef.name} 재암호화 완료")

        print("  완료")
    else:
        print(f"알 수 없는 명령: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
