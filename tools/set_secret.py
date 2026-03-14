"""
set_secret.py — .env 보안 입력 도구
입력 시 값이 화면에 표시되지 않음 (getpass 방식)

사용법:
  python tools/set_secret.py SUPABASE_URL
  python tools/set_secret.py SUPABASE_SERVICE_KEY
  python tools/set_secret.py  (← 키 이름 없이 실행하면 직접 입력)
"""
import sys
import getpass
import re
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def set_env_key(key: str, value: str):
    """기존 .env에서 해당 키의 값을 교체. 없으면 파일 끝에 추가."""
    if not ENV_PATH.exists():
        ENV_PATH.write_text(f"{key}={value}\n", encoding="utf-8")
        print(f"✅ {key} 저장 완료 (새 파일 생성)")
        return

    text = ENV_PATH.read_text(encoding="utf-8")
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)

    if pattern.search(text):
        new_text = pattern.sub(f"{key}={value}", text)
        ENV_PATH.write_text(new_text, encoding="utf-8")
        print(f"✅ {key} 업데이트 완료")
    else:
        # 파일 끝에 추가
        if not text.endswith("\n"):
            text += "\n"
        text += f"{key}={value}\n"
        ENV_PATH.write_text(text, encoding="utf-8")
        print(f"✅ {key} 추가 완료")


def main():
    if len(sys.argv) >= 2:
        key = sys.argv[1].strip()
    else:
        key = input("키 이름 입력 (예: SUPABASE_SERVICE_KEY): ").strip()

    if not key:
        print("❌ 키 이름이 비어있습니다.")
        sys.exit(1)

    print(f"🔑 {key} 값 입력 (입력값은 화면에 표시되지 않습니다)")
    value = getpass.getpass(prompt="값: ")

    if not value.strip():
        print("❌ 값이 비어있습니다. 취소됨.")
        sys.exit(1)

    set_env_key(key, value.strip())


if __name__ == "__main__":
    main()
