# -*- coding: utf-8 -*-
"""
ad_only/refresh_all.py -- ad_only 전파 오케스트레이터.

순서:
  1) sync_from_source.py         # 원본 -> ad_only/jobs_clean.txt
  2) loader.load_all_jobs(force)  # jobs_clean.json 캐시 재생성
  3) export_frontend_mirror.py   # Next.js data/jobs_clean.json
  4) export_esl_cafe.py           # BRIDGE_ESLCafe.html DEFAULT_JOBS

옵션:
  --skip-source   1단계 스킵 (원본 변경 없을 때)
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

PY = sys.executable
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def _run(script: Path, label: str) -> int:
    print(f"\n== {label} ==")
    r = subprocess.run([PY, "-X", "utf8", str(script)],
                       creationflags=_NO_WINDOW)
    if r.returncode != 0:
        print(f"[FAIL] {label} -- exit {r.returncode}", file=sys.stderr)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-source", action="store_true",
                    help="원본 -> jobs_clean.txt 재생성 스킵")
    args = ap.parse_args()

    ad = BASE / "ad_only"

    if not args.skip_source:
        rc = _run(ad / "sync_from_source.py", "1/4 sync_from_source")
        if rc != 0:
            return rc
    else:
        print("== 1/4 sync_from_source SKIPPED ==")

    # loader 캐시 재생성 (force_reparse=True)
    print("\n== 2/4 loader.load_all_jobs(force) ==")
    from ad_only.loader import load_all_jobs
    from ad_only.pii_guard import PIIContaminationError
    try:
        jobs = load_all_jobs(force_reparse=True)
        print(f"[OK] {len(jobs)}건 캐시 재생성")
    except PIIContaminationError as e:
        print(f"[FAIL] PII 감지: {e}", file=sys.stderr)
        return 10

    rc = _run(ad / "export_frontend_mirror.py", "3/4 export_frontend_mirror")
    if rc != 0:
        return rc

    rc = _run(ad / "export_esl_cafe.py", "4/4 export_esl_cafe")
    if rc != 0:
        return rc

    print("\n[ALL OK] ad_only -> {frontend mirror + ESL Cafe} 전파 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
