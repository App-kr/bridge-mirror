# -*- coding: utf-8 -*-
"""
ad_only/export_esl_cafe.py

ad_only/jobs_clean.* -> eslcafe_manager/BRIDGE_ESLCafe.html 의 DEFAULT_JOBS 배열 재생성.

- 오직 ad_only 만 소스 (master.db, original_jobs 접근 금지)
- 각 문자열 필드에 assert_clean 최종 검증
- DEFAULT_JOBS 배열만 정규식으로 교체 (다른 HTML 구조 보존)
"""
from __future__ import annotations
import json
import re
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from ad_only.loader import load_all_jobs
from ad_only.pii_guard import assert_clean, PIIContaminationError

# ── Starting Date 미래 치환 (동적) ──────────────────────────────────────────
_ESL_NOW_MONTH = datetime.now().month
_ESL_MONTHS_EN = [
    "january","february","march","april","may","june",
    "july","august","september","october","november","december"
]
_ESL_PAST_KEYS: set[str] = (
    {m[:3] for m in _ESL_MONTHS_EN[:_ESL_NOW_MONTH]}
    | {f"{i+1}월" for i in range(_ESL_NOW_MONTH)}
)
_ESL_FUTURE_MONTHS = [
    _ESL_MONTHS_EN[i].capitalize()
    for i in range(_ESL_NOW_MONTH, min(_ESL_NOW_MONTH + 5, 12))
]
_ESL_FUTURE_POOL = ["ASAP"] + _ESL_FUTURE_MONTHS


def _fix_start_date_esl(sd: str) -> str:
    """과거/현재 월 → 미래 또는 ASAP 치환. 복수 월이면 미래 부분만 유지."""
    s = (sd or "").strip()
    if not s:
        return "ASAP"
    sl = s.lower()
    # 특수값 그대로
    if any(k in sl for k in ("asap", "즉시", "negotiable", "tbd", "flexible", "year-round", "year round")):
        return s
    # 복수 월 처리 (쉼표·슬래시·대시 구분)
    parts = [p.strip() for p in re.split(r"[,/\-]", s) if p.strip()]
    if len(parts) > 1:
        future_parts = [
            p for p in parts
            if not any(k in p.lower() for k in _ESL_PAST_KEYS)
        ]
        if future_parts:
            return ", ".join(future_parts)
        # 전부 과거 → 미래 풀에서 첫 번째
        return _ESL_FUTURE_POOL[0]
    # 단일 월 — 과거면 미래 풀 첫 번째로 교체
    if any(k in sl for k in _ESL_PAST_KEYS):
        return _ESL_FUTURE_POOL[0]
    return s  # 이미 미래

HTML_PATH = BASE / "eslcafe_manager" / "BRIDGE_ESLCafe.html"

# ESL Cafe 내부 region 분류
REGION_SEOUL = {
    "seoul",
}
REGION_GG = {
    "seongnam", "suwon", "yongin", "goyang", "incheon", "bucheon",
    "ansan", "anyang", "gwangmyeong", "hwaseong", "pyeongtaek",
    "uijeongbu", "gwangju",  # 경기 광주
    "gimpo", "paju", "namyangju", "yangju", "siheung", "gunpo",
    "osan", "icheon", "yongin",
}


def _region_of(location: str) -> str:
    low = (location or "").lower()
    first = low.split()[0] if low else ""
    if first in REGION_SEOUL or "seoul" in low:
        return "seoul"
    if first in REGION_GG:
        return "gg"
    # 광역시(인천/부산/대구/광주/울산/대전), 도, 제주 등은 etc
    return "etc"


def _job_id(job_code: str) -> str:
    """'Job. 1234' -> '1234'"""
    m = re.search(r"(\d+)", job_code or "")
    return m.group(1) if m else ""


def _build_txt(j: dict) -> str:
    """ESL Cafe txt 필드용 멀티라인 블록. 날짜 원본 그대로 사용 (변환 금지)."""
    j = dict(j)
    lines: list[str] = []
    fields = [
        ("start_date",     "Starting Date"),
        ("teaching_age",   "Teaching Age"),
        ("class_size",     "Class size"),
        ("working_hours",  "Working Hours"),
        ("teach_hrs_week", "Average Teaching Hours/Week"),
        ("vacation",       "Vacation"),
        ("monthly_salary", "Monthly Salary"),
        ("housing",        "Housing"),
        ("native_count",   "Native Teacher"),
        ("benefits",       "Employee Benefits"),
    ]
    for key, label in fields:
        val = (j.get(key) or "").strip()
        if val:
            lines.append(f"{label}: {val}")
    for extra in j.get("extra_lines", []) or []:
        e = (extra or "").strip()
        if e:
            lines.append(e)
    return "\n".join(lines)


def _to_esl_entry(j: dict) -> dict:
    jid = _job_id(j.get("job_code", ""))
    location = (j.get("location") or "").strip()
    raw_date = (j.get("start_date") or "").strip()
    entry = {
        "id":   jid,
        "l":    location,
        "r":    _region_of(location),
        "p":    False,  # premium: 관리자가 ESL UI 에서 토글
        "h":    False,  # hot: 관리자가 ESL UI 에서 토글
        "a":    True,   # active: 기본 ON
        "sal":  (j.get("monthly_salary") or "").strip(),
        "date": raw_date,  # 원본 그대로 (과거월 변환 금지)
        "hrs":  (j.get("working_hours")  or "").strip(),
        "hsg":  (j.get("housing")        or "").strip(),
        "txt":  _build_txt(j),
    }
    # 각 문자열 필드 최종 PII 검증
    for k, v in entry.items():
        if isinstance(v, str) and v:
            strict = k in ("l",)
            assert_clean(v, context=f"esl_cafe[{jid}].{k}", strict_brand=strict)
    return entry


def _render_default_jobs(entries: list[dict]) -> str:
    """compact JSON 한 줄씩 -- 원본 HTML 포맷과 동일."""
    rows = [json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in entries]
    return "var DEFAULT_JOBS=[\n" + ",\n".join(rows) + "\n];"


_RE_DEFAULT_JOBS = re.compile(
    r"var\s+DEFAULT_JOBS\s*=\s*\[.*?\]\s*;",
    re.DOTALL,
)


def main() -> int:
    try:
        jobs = load_all_jobs()
    except PIIContaminationError as e:
        print(f"[FAIL] ad_only 소스 오염 감지: {e}", file=sys.stderr)
        return 1

    if not HTML_PATH.exists():
        print(f"[FAIL] HTML 없음: {HTML_PATH}", file=sys.stderr)
        return 2

    entries: list[dict] = []
    skipped = 0
    for j in jobs:
        jid = _job_id(j.get("job_code", ""))
        if not jid:
            skipped += 1
            continue
        try:
            entries.append(_to_esl_entry(j))
        except PIIContaminationError as e:
            print(f"[SKIP] {j.get('job_code')}: {e}", file=sys.stderr)
            skipped += 1

    if not entries:
        print("[FAIL] 유효 엔트리 0건", file=sys.stderr)
        return 3

    new_block = _render_default_jobs(entries)

    html = HTML_PATH.read_text(encoding="utf-8")
    if not _RE_DEFAULT_JOBS.search(html):
        print("[FAIL] DEFAULT_JOBS 블록 찾기 실패", file=sys.stderr)
        return 4

    # re.sub 는 replacement 문자열 내 백슬래시 이스케이프를 해석한다 (\n -> LF).
    # 콜러블로 넘겨 원본 그대로 삽입.
    html2 = _RE_DEFAULT_JOBS.sub(lambda _m: new_block, html, count=1)
    if html2 == html:
        print("[WARN] 변경 없음 (이미 최신)", file=sys.stdout)
    HTML_PATH.write_text(html2, encoding="utf-8")

    print(f"[OK] {len(entries)}건 -> {HTML_PATH.name} (skip={skipped})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
