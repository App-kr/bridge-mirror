# -*- coding: utf-8 -*-
"""
ad_only/loader.py -- 광고 전용 클린 데이터 유일한 로더

사용 예:
    from ad_only.loader import select_jobs, get_job, iter_jobs
    jobs = select_jobs(limit=8, future_only=True)

규칙 (LOCKED):
- master.db, original_jobs/*, client_inquiries 어디에서도 읽지 않음
- 오직 ad_only/jobs_clean.txt 만 원본 소스
- 로드 시 전체 필드를 pii_guard.assert_clean 으로 검증 (fail-closed)
"""
from __future__ import annotations
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Iterator

from .pii_guard import assert_clean, scan as pii_scan, PIIContaminationError

_HERE = Path(__file__).resolve().parent
SOURCE_TXT = _HERE / 'jobs_clean.txt'
CACHE_JSON = _HERE / 'jobs_clean.json'

_RE_JOB   = re.compile(r'^\s*Job\.?\s*(\d+)\s*$', re.IGNORECASE)
_RE_KV    = re.compile(r'^\s*(`*)([A-Za-z][A-Za-z\- /]+?)\s*[:：]\s*(.+)$')

# 현재 월 필터용
_MONTHS = {
    1:'january', 2:'february', 3:'march', 4:'april',
    5:'may', 6:'june', 7:'july', 8:'august',
    9:'september', 10:'october', 11:'november', 12:'december',
}


def _normalize_key(raw: str) -> str:
    """'Starting Date' / 'Monthly Salary' 등 → 통일된 key"""
    k = raw.strip().lower()
    k = re.sub(r'\s+', '_', k)
    k = k.replace('-', '_').replace('/', '_')
    mapping = {
        'starting_date': 'start_date',
        'teaching_age': 'teaching_age',
        'class_size': 'class_size',
        'working_hours': 'working_hours',
        'monthly_salary': 'monthly_salary',
        'average_teaching_hours_per_week': 'teach_hrs_week',
        'teaching_hours_per_week': 'teach_hrs_week',
        'vacation': 'vacation',
        'housing': 'housing',
        'employee_benefits': 'benefits',
        'native_teacher_(numbers_can_change)': 'native_count',
        'native_teacher': 'native_count',
    }
    return mapping.get(k, k)


def _parse_block(block_lines: list[str]) -> dict | None:
    """연속된 라인 블록 하나를 파싱."""
    if not block_lines:
        return None

    location = block_lines[0].strip()
    if not location:
        return None

    job: dict = {
        'location': location,
        'job_code': '',
        'start_date': '',
        'teaching_age': '',
        'class_size': '',
        'working_hours': '',
        'monthly_salary': '',
        'teach_hrs_week': '',
        'vacation': '',
        'housing': '',
        'native_count': '',
        'benefits': '',
        'extra_lines': [],
    }

    for line in block_lines[1:]:
        s = line.strip().lstrip('`').strip()
        if not s:
            continue
        m = _RE_JOB.match(s)
        if m:
            job['job_code'] = f'Job. {m.group(1)}'
            continue
        kv = _RE_KV.match(s)
        if kv:
            key = _normalize_key(kv.group(2))
            val = kv.group(3).strip().rstrip(',')
            if key in job:
                job[key] = val
                continue
        # 키:값이 아닌 자유 텍스트 (ex. 거주요건)
        job['extra_lines'].append(s)

    if not job['job_code']:
        return None
    return job


_STRICT_FIELDS = {'location'}  # 업체 브랜드까지 엄격 검사


def _enforce_clean(job: dict) -> None:
    """단일 job dict의 모든 문자열 필드에 PII 가드 적용."""
    code = job.get('job_code', '?')
    for k, v in job.items():
        strict = k in _STRICT_FIELDS
        if isinstance(v, str) and v:
            assert_clean(v, context=f'{code}/{k}', strict_brand=strict)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, str) and item:
                    assert_clean(item, context=f'{code}/{k}[{i}]', strict_brand=strict)


def _parse_source() -> list[dict]:
    if not SOURCE_TXT.exists():
        raise FileNotFoundError(
            f'[ad_only] 원본 파일 없음: {SOURCE_TXT}\n'
            f'복구: python ad_only/sync_from_source.py'
        )
    text = SOURCE_TXT.read_text(encoding='utf-8-sig')
    blocks: list[list[str]] = []
    cur: list[str] = []
    for raw in text.splitlines():
        if raw.strip() == '':
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(raw)
    if cur:
        blocks.append(cur)

    jobs: list[dict] = []
    rejected: list[tuple[str, list[str]]] = []
    for blk in blocks:
        job = _parse_block(blk)
        if not job:
            continue
        try:
            _enforce_clean(job)
        except PIIContaminationError as e:
            rejected.append((job.get('job_code', '?'), pii_scan(str(job))))
            continue
        jobs.append(job)

    if rejected:
        # 원본 jobs_clean.txt 에서 PII가 감지되면 절대 진행 금지 (소스 오염)
        raise PIIContaminationError(
            f'[ad_only] 원본 소스 오염 감지 -- {len(rejected)}건 거부: '
            f'{rejected[:3]}'
        )
    return jobs


def _write_cache(jobs: list[dict]) -> None:
    CACHE_JSON.write_text(
        json.dumps({
            'generated_at': datetime.now().isoformat(timespec='seconds'),
            'source': SOURCE_TXT.name,
            'count': len(jobs),
            'jobs': jobs,
        }, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def _load_cached() -> list[dict] | None:
    if not CACHE_JSON.exists():
        return None
    try:
        src_mtime = SOURCE_TXT.stat().st_mtime
        cache_mtime = CACHE_JSON.stat().st_mtime
        if cache_mtime < src_mtime:
            return None
        payload = json.loads(CACHE_JSON.read_text(encoding='utf-8'))
        return payload.get('jobs') or None
    except Exception:
        return None


def load_all_jobs(*, force_reparse: bool = False) -> list[dict]:
    """모든 광고 job을 리턴. 캐시가 유효하면 캐시 사용."""
    if not force_reparse:
        cached = _load_cached()
        if cached is not None:
            return cached
    jobs = _parse_source()
    _write_cache(jobs)
    return jobs


def iter_jobs() -> Iterator[dict]:
    yield from load_all_jobs()


def get_job(job_code: str) -> dict | None:
    want = re.sub(r'[^0-9]', '', str(job_code))
    for j in load_all_jobs():
        have = re.sub(r'[^0-9]', '', j['job_code'])
        if have == want:
            return j
    return None


def is_future_start(sd: str) -> bool:
    """현재 월 이후 시작 또는 ASAP/flexible 이면 True."""
    if not sd:
        return False
    sl = sd.lower()
    if any(tag in sl for tag in ('asap', 'year-round', 'year round', 'flexible')):
        return True
    now_month = datetime.now().month
    future_months = [_MONTHS[m] for m in range(now_month + 1, 13)]
    return any(m in sl for m in future_months)


def select_jobs(
    *,
    limit: int = 8,
    future_only: bool = True,
    min_salary_m: float = 0.0,
    diverse_cities: bool = True,
) -> list[dict]:
    """
    Teast/Craigslist 광고용 job 선택.

    - future_only: 현재월 이후 시작만
    - diverse_cities: 같은 도시 중복 제거
    - min_salary_m: 최소 월급(백만 단위). 0이면 전체.
    """
    jobs = load_all_jobs()
    pool = []
    for j in jobs:
        if future_only and not is_future_start(j.get('start_date', '')):
            continue
        if min_salary_m > 0:
            m = re.search(r'(\d+(?:[,.]\d+)?)\s*m', j.get('monthly_salary', ''), re.IGNORECASE)
            if m:
                try:
                    v = float(m.group(1).replace(',', '.'))
                    if v < min_salary_m:
                        continue
                except ValueError:
                    pass
        pool.append(j)

    if diverse_cities:
        seen: set[str] = set()
        selected: list[dict] = []
        for j in pool:
            city_key = (j.get('location') or '').split()[0].lower()
            if city_key and city_key not in seen:
                seen.add(city_key)
                selected.append(j)
            if len(selected) >= limit:
                break
        return selected

    return pool[:limit]


def render_ad_block(job: dict, *, divider: str = '-' * 60) -> str:
    """광고 포스팅용 단일 잡 블록 생성 -- PII 재검증 포함."""
    lines = [job['location'], job['job_code']]
    fields_ordered = [
        ('start_date',     'Starting Date'),
        ('teaching_age',   'Teaching Age'),
        ('class_size',     'Class size'),
        ('working_hours',  'Working Hours'),
        ('monthly_salary', 'Monthly Salary'),
        ('teach_hrs_week', 'Average Teaching Hours per Week'),
        ('vacation',       'Vacation'),
        ('housing',        'Housing'),
        ('native_count',   'Native Teacher (Numbers can change)'),
        ('benefits',       'Employee Benefits'),
    ]
    for key, label in fields_ordered:
        val = (job.get(key) or '').strip()
        if val:
            lines.append(f'`{label} : {val}')
    for extra in job.get('extra_lines', []):
        lines.append(f'`{extra}')
    lines.append(divider)
    block = '\n'.join(lines)
    # 최종 출력물에 다시 한 번 guard -- location 포함하므로 strict
    assert_clean(block, context=f'render_ad_block/{job["job_code"]}', strict_brand=True)
    return block


if __name__ == '__main__':
    import sys
    try:
        jobs = load_all_jobs(force_reparse=True)
    except PIIContaminationError as e:
        print(f'[FATAL] {e}')
        sys.exit(2)

    print(f'[OK] {len(jobs)}개 잡 로드 (PII 0건)')
    print(f'[OK] 캐시 저장: {CACHE_JSON.name}')

    # 샘플 출력
    sample = select_jobs(limit=3, future_only=False, diverse_cities=True)
    print(f'\n샘플 {len(sample)}개:')
    for j in sample:
        print(f"  {j['job_code']:12s} {j['location']:30s} {j['monthly_salary']}")
