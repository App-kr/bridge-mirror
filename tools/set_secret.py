"""
set_secret.py — .env 보안 입력 도구 (팝업 다이얼로그)
입력값이 화면에 표시되지 않음

사용법:
  python tools/set_secret.py SUPABASE_URL
  python tools/set_secret.py SUPABASE_SERVICE_KEY
  python tools/set_secret.py  (← 키 이름 없이 실행하면 직접 입력)
"""
import sys
import re
import tkinter as tk
from tkinter import simpledialog, messagebox
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def set_env_key(key: str, value: str):
    if not ENV_PATH.exists():
        ENV_PATH.write_text(f"{key}={value}\n", encoding="utf-8")
        return f"{key} 저장 완료 (새 파일 생성)"

    text = ENV_PATH.read_text(encoding="utf-8")
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)

    if pattern.search(text):
        new_text = pattern.sub(f"{key}={value}", text)
        ENV_PATH.write_text(new_text, encoding="utf-8")
        return f"{key} 업데이트 완료"
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += f"{key}={value}\n"
        ENV_PATH.write_text(text, encoding="utf-8")
        return f"{key} 추가 완료"


def main():
    key = sys.argv[1].strip() if len(sys.argv) >= 2 else ""

    root = tk.Tk()
    root.withdraw()  # 메인 창 숨기기
    root.attributes("-topmost", True)

    if not key:
        key = simpledialog.askstring(
            "set_secret", "키 이름 입력\n(예: SUPABASE_SERVICE_KEY)",
            parent=root
        )
        if not key or not key.strip():
            messagebox.showerror("취소", "키 이름이 비어있습니다.")
            sys.exit(1)
        key = key.strip()

    value = simpledialog.askstring(
        "set_secret",
        f"{key}\n\n값을 입력하세요 (입력값은 *** 로 표시됩니다)",
        show="*",
        parent=root
    )

    if not value or not value.strip():
        messagebox.showerror("취소", "값이 비어있습니다. 취소됨.")
        sys.exit(1)

    msg = set_env_key(key, value.strip())
    messagebox.showinfo("완료", f"✅ {msg}")
    print(f"✅ {msg}")


if __name__ == "__main__":
    main()
