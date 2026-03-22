"""
secure_input.py — 보안 키 입력 + 암호화 저장 (독립 실행)
=========================================================
터미널에서 직접 키를 입력받아 AES-256-GCM 암호화 후 저장.
대화 로그에 키가 노출되지 않음.
"""

import getpass
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from secure_store import store_set, store_get, store_list  # noqa: E402


def main():
    print("=" * 50)
    print("  BRIDGE Secure Key Manager")
    print("  AES-256-GCM 암호화 저장")
    print("=" * 50)
    print()

    # 현재 저장된 키 목록
    print("[현재 저장된 키]")
    store_list()
    print()

    # 키 이름 입력
    key_name = input("저장할 키 이름 (예: RENDER_API_KEY): ").strip()
    if not key_name:
        print("키 이름이 비어있습니다. 종료.")
        input("\nEnter를 누르면 닫힙니다...")
        return

    # 키 값 입력 (화면에 표시 안 됨)
    print(f"\n'{key_name}' 값을 입력하세요 (입력 내용은 화면에 표시되지 않습니다):")
    value = getpass.getpass(prompt=">>> ")

    if not value.strip():
        print("값이 비어있습니다. 종료.")
        input("\nEnter를 누르면 닫힙니다...")
        return

    # 암호화 저장
    store_set(key_name, value.strip())

    # 검증
    print("\n[검증] 복호화 테스트...")
    decrypted = store_get(key_name)
    if decrypted == value.strip():
        print("  --> 암호화/복호화 정상 확인!")
    else:
        print("  --> 경고: 복호화 값 불일치!")

    print("\n[최종 저장 상태]")
    store_list()

    # 배포 실행 여부
    print()
    ans = input("바로 Render 배포를 실행할까요? (y/n): ").strip().lower()
    if ans in ("y", "yes"):
        print("\n" + "=" * 50)
        print("  배포 시작...")
        print("=" * 50 + "\n")
        import render_deploy
        render_deploy.trigger_deploy()

    input("\nEnter를 누르면 닫힙니다...")


if __name__ == "__main__":
    main()
