"""
migrate_env_to_vault.py — .env 파일 → MasterVault v3 자동 마이그레이션
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
백업된 .env 파일을 읽어 MasterVault에 주입.
완료 후 .env 파일은 삭제하지 않음 (보스가 직접 확인 후 삭제).

실행:
  python tools/migrate_env_to_vault.py
  python tools/migrate_env_to_vault.py --env-path "Q:/Claudework/bridge base_backup/.env"
"""

import sys
import re
from pathlib import Path

# tools/ 디렉토리 sys.path 추가
_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from master_vault import MasterVault


def parse_env_file(env_path: Path) -> dict[str, str]:
    """
    .env 파일 파싱 → {KEY: VALUE} dict 반환.
    - 주석(#) 무시
    - 인용부호 제거
    - KEY=VALUE 형식만 처리
    """
    result = {}
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        # 따옴표 제거
        if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
            val = val[1:-1]
        if key and val:
            result[key] = val
    return result


def main():
    # .env 경로 결정
    default_paths = [
        Path("Q:/Claudework/bridge base_backup/.env"),
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent / ".env.backup",
    ]

    env_path = None

    # CLI 인수로 경로 지정 가능
    if len(sys.argv) > 2 and sys.argv[1] == "--env-path":
        env_path = Path(sys.argv[2])
    else:
        for p in default_paths:
            if p.exists():
                env_path = p
                break

    if not env_path or not env_path.exists():
        print("⚠  .env 파일을 찾을 수 없습니다.")
        print("다음 명령으로 경로를 지정하세요:")
        print('  python tools/migrate_env_to_vault.py --env-path "경로/.env"')
        sys.exit(1)

    print(f"\n=== .env → MasterVault v3 마이그레이션 ===")
    print(f"소스: {env_path}\n")

    # .env 파싱
    env_data = parse_env_file(env_path)
    print(f"파싱된 키: {len(env_data)}개")
    for k in env_data:
        print(f"  - {k}")

    # 확인
    confirm = input(f"\n위 {len(env_data)}개 키를 MasterVault에 주입할까요? (y/N): ").strip().lower()
    if confirm != "y":
        print("취소됨.")
        sys.exit(0)

    # MasterVault 주입
    vault = MasterVault()
    migrated = 0
    skipped  = 0

    for key, val in env_data.items():
        existing = vault.list_keys()
        if key in existing:
            overwrite = input(f"  [{key}] 이미 존재. 덮어쓰기? (y/N): ").strip().lower()
            if overwrite != "y":
                skipped += 1
                continue
        vault.seal(key, val)
        migrated += 1
        print(f"  ✓ {key} ({len(val)}자)")

    print(f"\n완료: {migrated}개 주입 / {skipped}개 건너뜀")
    print(f"Vault 저장 위치: {vault.__class__.__module__}")

    # .env 파일 후처리
    print(f"\n⚠  {env_path} 파일은 삭제되지 않았습니다.")
    delete = input("마이그레이션 완료 후 원본 .env를 삭제하시겠습니까? (y/N): ").strip().lower()
    if delete == "y":
        env_path.unlink()
        print(f"[삭제] {env_path}")
    else:
        print("[유지] 필요 시 수동으로 삭제하세요.")


if __name__ == "__main__":
    main()
