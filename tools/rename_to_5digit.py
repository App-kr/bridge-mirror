#!/usr/bin/env python3
"""
BRIDGE — 강사 ID 4자리 → 5자리 전환 자동화 스크립트
파일명에서 4자리 숫자를 감지하여 5자리로 변환합니다.

사용법:
  python rename_to_5digit.py --dry          # 미리보기 (변경 없음)
  python rename_to_5digit.py --execute      # 실제 리네임 실행
  python rename_to_5digit.py --prefix 1     # 앞에 1 추가 (1003 → 11003)
  python rename_to_5digit.py --prefix 0     # 앞에 0 추가 (1003 → 01003) [기본]
"""

import os
import re
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(r"Q:\Claudework\bridge base\웹빌드_자료")
LOG_DIR = Path(r"Q:\Claudework\bridge base\tools\logs")
PATTERN = re.compile(r"(?<!\d)(\d{4})(?!\d)")  # 정확히 4자리 숫자


def find_candidates(base: Path, prefix: str) -> list[dict]:
    """4자리 숫자가 포함된 파일명을 탐색하여 변환 후보 목록 반환."""
    results = []
    if not base.exists():
        print(f"[WARN] 디렉토리 없음: {base}")
        return results

    for root, _dirs, files in os.walk(base):
        for fname in files:
            matches = PATTERN.findall(fname)
            if not matches:
                continue

            # 1000~9999 범위 내 숫자만 필터
            valid_matches = [m for m in matches if 1000 <= int(m) <= 9999]
            if not valid_matches:
                continue

            new_name = fname
            for m in valid_matches:
                new_id = f"{prefix}{m}"
                new_name = new_name.replace(m, new_id, 1)

            if new_name != fname:
                results.append({
                    "dir": root,
                    "old": fname,
                    "new": new_name,
                    "matches": valid_matches,
                })

    return results


def preview(candidates: list[dict]) -> None:
    """변환 예정 목록 출력."""
    if not candidates:
        print("\n변환 대상 파일이 없습니다.")
        return

    print(f"\n{'='*60}")
    print(f"  변환 대상: {len(candidates)}건")
    print(f"{'='*60}")
    for i, c in enumerate(candidates, 1):
        rel = os.path.relpath(c["dir"], BASE_DIR)
        print(f"  [{i:3d}] {rel}")
        print(f"        {c['old']}")
        print(f"     →  {c['new']}")
        print(f"        (숫자: {', '.join(c['matches'])})")
    print(f"{'='*60}\n")


def execute(candidates: list[dict]) -> list[dict]:
    """실제 파일명 변경 실행."""
    log = []
    for c in candidates:
        old_path = os.path.join(c["dir"], c["old"])
        new_path = os.path.join(c["dir"], c["new"])

        if os.path.exists(new_path):
            print(f"  [SKIP] 대상 파일 이미 존재: {c['new']}")
            log.append({**c, "status": "skipped", "reason": "target_exists"})
            continue

        try:
            os.rename(old_path, new_path)
            print(f"  [OK] {c['old']} → {c['new']}")
            log.append({**c, "status": "renamed"})
        except Exception as e:
            print(f"  [ERR] {c['old']}: {e}")
            log.append({**c, "status": "error", "reason": str(e)})

    return log


def save_log(log: list[dict], mode: str) -> None:
    """변환 로그 저장."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"rename_5digit_{mode}_{ts}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"\n로그 저장: {log_path}")


def main():
    parser = argparse.ArgumentParser(description="4자리 → 5자리 ID 전환")
    parser.add_argument("--dry", action="store_true", help="미리보기만 (변경 없음)")
    parser.add_argument("--execute", action="store_true", help="실제 리네임 실행")
    parser.add_argument("--prefix", default="1", help="앞에 붙일 숫자 (기본: 1)")
    parser.add_argument("--dir", default=str(BASE_DIR), help="탐색 디렉토리")
    args = parser.parse_args()

    base = Path(args.dir)
    candidates = find_candidates(base, args.prefix)

    if args.execute:
        preview(candidates)
        if not candidates:
            return

        confirm = input(f"\n{len(candidates)}건 리네임을 실행하시겠습니까? (y/N): ")
        if confirm.lower() != "y":
            print("취소됨.")
            return

        log = execute(candidates)
        save_log(log, "execute")
        renamed = sum(1 for l in log if l["status"] == "renamed")
        print(f"\n완료: {renamed}/{len(candidates)}건 변환")
    else:
        # 기본 = dry-run
        preview(candidates)
        save_log([{**c, "status": "preview"} for c in candidates], "preview")
        if candidates:
            print("실제 실행: python rename_to_5digit.py --execute")


if __name__ == "__main__":
    main()
