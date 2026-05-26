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

    # ⚠️ 영구 cleanup (사용자 요청 2026-05-26): extra_lines 오염 자동 정리
    # 매일 06:30 sync 후에도 RPA가 bad_body 가드로 SKIP 안 되도록
    print("\n== 2.5/4 cleanup: extra_lines 오염 자동 정리 ==")
    import json, re
    jobs_json = ad / "jobs_clean.json"
    raw = json.load(jobs_json.open(encoding="utf-8"))
    NOISE_PATTERNS = [
        re.compile(r'^(Starting Date|Working Hours?|Working hour|Monthly Salary|Teaching Age|Teaching hours?|Class size|Vacation|Housing|Native Teacher|Number of Native English Speakers|Average Teaching Hours)\s*:', re.I),
    ]
    CITIES = set('seoul busan incheon daegu daejeon gwangju ulsan sejong suwon seongnam goyang yongin hwaseong bucheon anyang anseong pyeongtaek ansan siheung gimpo paju hanam namyangju gunpo uijeongbu guri uiwang gwangmyeong osan yangju dongducheon cheonan asan cheongju chungbuk chuncheon wonju gangneung gangwon jeonju jeju pohang gyeongju changwon masan jinju tongyeong geoje gimhae yangsan gunsan yeosu sunchun gwangyang'.split())
    def is_noise(line):
        s = (line or "").strip()
        if not s or len(s) <= 2: return True
        for pat in NOISE_PATTERNS:
            if pat.search(s): return True
        words = re.split(r'[,\s]+', s)
        words = [w for w in words if w]
        if 1 <= len(words) <= 3 and all(w.lower() in CITIES for w in words):
            return True
        if words and words[0].lower() in CITIES and len(words) <= 4:
            rest = ' '.join(words[1:]).lower()
            if rest in ('northern area','southern area','eastern area','western area',
                        'coastal city','central area'):
                return True
        return False

    cleaned = 0
    bad_loc_fixed = 0
    for j in raw.get("jobs", []):
        # extra_lines 정리
        extras = j.get("extra_lines") or []
        if isinstance(extras, str):
            extras = [extras] if extras else []
        new_extras = [ln for ln in extras if not is_noise(ln)]
        if new_extras != extras:
            j["extra_lines"] = new_extras
            cleaned += 1
        # location 'Job.' 오염 자동 수정
        loc = (j.get("location") or "").strip()
        if loc.startswith("Job."):
            j["location"] = ""
            bad_loc_fixed += 1

    json.dump(raw, jobs_json.open("w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] 노이즈 정리 {cleaned}건 / location 오염 수정 {bad_loc_fixed}건")

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
