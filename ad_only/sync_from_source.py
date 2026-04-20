# -*- coding: utf-8 -*-
"""
ad_only/sync_from_source.py -- 원본 재생성 (수동 실행 전용)

파이프라인:
  original_jobs/BRIDGE_clients_jobs.txt
     ↓ make_clean_jobs.py
  original_jobs/JOBS_CLEAN.txt
     ↓ (이 스크립트)
  ad_only/jobs_clean.txt           ← RPA/ESL/Teast의 유일한 소스
     ↓ loader.py (자동)
  ad_only/jobs_clean.json (캐시)

RPA/ESL/Teast는 이 스크립트를 직접 실행하지 않음 -- 보스가 수동 갱신.
"""
from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(r"Q:\Claudework\bridge base")
ORIG_DIR = BASE / "original_jobs"
AD_DIR   = BASE / "ad_only"

SRC_RAW   = ORIG_DIR / "BRIDGE_clients_jobs.txt"
SRC_CLEAN = ORIG_DIR / "JOBS_CLEAN.txt"
DST_CLEAN = AD_DIR   / "jobs_clean.txt"
MAKER     = ORIG_DIR / "make_clean_jobs.py"


def main() -> int:
    if not SRC_RAW.exists():
        print(f'[WARN] 원본 없음: {SRC_RAW}', file=sys.stderr)
        print('       JOBS_CLEAN.txt만 ad_only/로 복사합니다.')
    else:
        print(f'[STEP 1] make_clean_jobs.py 실행 → {SRC_CLEAN}')
        result = subprocess.run(
            [sys.executable, str(MAKER)],
            capture_output=True,
            text=True,
            encoding='utf-8',
        )
        if result.returncode != 0:
            print(f'[FAIL] maker 실패:\n{result.stderr}', file=sys.stderr)
            return 1
        print(result.stdout or '(stdout 없음)')

    if not SRC_CLEAN.exists():
        print(f'[FAIL] 소스 미생성: {SRC_CLEAN}', file=sys.stderr)
        return 2

    print(f'[STEP 2] 복사: {SRC_CLEAN.name} → ad_only/{DST_CLEAN.name}')
    AD_DIR.mkdir(exist_ok=True)
    shutil.copy2(SRC_CLEAN, DST_CLEAN)

    print(f'[STEP 3] loader 검증 + 캐시 재생성')
    sys.path.insert(0, str(BASE))
    from ad_only.loader import load_all_jobs
    from ad_only.pii_guard import PIIContaminationError
    try:
        jobs = load_all_jobs(force_reparse=True)
    except PIIContaminationError as e:
        print(f'[FAIL] PII 감지 -- 소스 오염: {e}', file=sys.stderr)
        return 3
    print(f'[OK] {len(jobs)}개 잡 로드 완료 / PII 0건 / 캐시 갱신됨')
    return 0


if __name__ == '__main__':
    sys.exit(main())
