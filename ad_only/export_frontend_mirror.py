# -*- coding: utf-8 -*-
"""
ad_only/export_frontend_mirror.py

ad_only/jobs_clean.json (내부 스키마) -> web_frontend/data/jobs_clean.json
(프론트엔드 rowToPublic 스키마 호환) 로 미러 생성.

RPA/Teast 와 동일하게 공개 웹사이트(/jobs, 홈 Featured Positions) 도 ad_only 만 사용.
sync_from_source.py 실행 후 호출하거나 수동 실행.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from ad_only.loader import load_all_jobs
from ad_only.pii_guard import assert_clean, PIIContaminationError

DST = BASE / "web_frontend" / "data" / "jobs_clean.json"


def main() -> int:
    try:
        jobs = load_all_jobs()
    except PIIContaminationError as e:
        print(f"[FAIL] ad_only 소스 오염 감지: {e}", file=sys.stderr)
        return 1

    # frontend rowToPublic 은 row.city / row.location / row.job_code / row.start_date 등을 읽음.
    # 최소한의 호환 dict 로 변환.
    out = []
    for j in jobs:
        row = {
            "city":           j.get("location", ""),
            "location":       j.get("location", ""),
            "job_code":       j.get("job_code", ""),
            "start_date":     j.get("start_date", ""),
            "teaching_age":   j.get("teaching_age", ""),
            "class_size":     j.get("class_size", ""),
            "working_hours":  j.get("working_hours", ""),
            "salary_raw":     j.get("monthly_salary", ""),
            "teach_hrs_week": j.get("teach_hrs_week", ""),
            "vacation":       j.get("vacation", ""),
            "housing":        j.get("housing", ""),
            "native_count":   j.get("native_count", ""),
            "benefits":       j.get("benefits", ""),
            "raw_text":       "\n".join(j.get("extra_lines", []) or []),
            "is_hot":         0,
            "is_part_time":   0,
            "daily_hours":    None,
            "status":         "open",
            "is_deleted":     0,
        }
        # 방어선: 행별 PII 최종 검증
        for k, v in row.items():
            if isinstance(v, str) and v:
                assert_clean(v, context=f"frontend_mirror.{k}",
                             strict_brand=(k in ("city", "location")))
        out.append(row)

    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"[OK] {len(out)}건 -> {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
