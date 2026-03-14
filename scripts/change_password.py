"""비밀번호 변경 — 실행하면 입력창이 뜹니다."""
import getpass
from pathlib import Path
from crypto_util import encrypt_value, encrypt_env_file, _load_or_create_key

BASE = Path(__file__).resolve().parent

ACCOUNTS = [
    ("account1.env", "Coreabridge@gmail.com"),
    ("account2.env", "airelair00@gmail.com"),
    ("account3.env", "ferrari812fast@gmail.com"),
    ("account4.env", "bridgejobkr@gmail.com"),
]


def change_one(env_name: str, email: str):
    env_path = BASE / env_name
    if not env_path.exists():
        print(f"  [SKIP] {env_name} 없음")
        return

    pw = getpass.getpass(f"\n  {email} 새 비밀번호 (Enter=건너뛰기): ")
    if not pw:
        print(f"  → 건너뜀")
        return

    enc = encrypt_value(pw)
    lines = env_path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("CRAIGSLIST_PASSWORD="):
            new_lines.append(f"CRAIGSLIST_PASSWORD={enc}")
        else:
            new_lines.append(line)
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"  → 완료! (암호화 저장됨)")


def main():
    _load_or_create_key()
    print()
    print("  ==========================================")
    print("  BRIDGE 비밀번호 변경")
    print("  ==========================================")
    print("  입력한 비밀번호는 화면에 표시되지 않습니다.")
    print("  변경 안 할 계정은 그냥 Enter 누르세요.")

    for env_name, email in ACCOUNTS:
        change_one(env_name, email)

    # .env (기본) 도 account1 과 동기화
    a1 = BASE / "account1.env"
    dot_env = BASE / ".env"
    if a1.exists() and dot_env.exists():
        for line in a1.read_text(encoding="utf-8").splitlines():
            if line.startswith("CRAIGSLIST_PASSWORD="):
                lines = dot_env.read_text(encoding="utf-8").splitlines()
                new_lines = []
                for dl in lines:
                    if dl.startswith("CRAIGSLIST_PASSWORD="):
                        new_lines.append(line)
                    else:
                        new_lines.append(dl)
                dot_env.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                break

    print()
    print("  ==========================================")
    print("  모든 비밀번호가 암호화 저장되었습니다.")
    print("  ==========================================")
    print()


if __name__ == "__main__":
    main()
