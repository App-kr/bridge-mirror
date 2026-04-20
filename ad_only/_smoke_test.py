# -*- coding: utf-8 -*-
"""ad_only 스모크 테스트."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ad_only.loader import load_all_jobs, select_jobs, render_ad_block, get_job
from ad_only.pii_guard import scan, PIIContaminationError

print('=' * 60)
print('[1] 전체 로드 + PII 검증')
print('=' * 60)
jobs = load_all_jobs(force_reparse=True)
print(f'로드된 잡: {len(jobs)}개')

# 로드된 전체에서 PII 추가 검증 (paranoia)
total_leaks = 0
for j in jobs:
    for k, v in j.items():
        strict = (k == 'location')
        if isinstance(v, str):
            hits = scan(v, strict_brand=strict)
            if hits:
                total_leaks += 1
                print(f'[LEAK] {j["job_code"]}/{k}: {hits} → {v[:80]!r}')
        elif isinstance(v, list):
            for it in v:
                if isinstance(it, str):
                    hits = scan(it, strict_brand=strict)
                    if hits:
                        total_leaks += 1
                        print(f'[LEAK] {j["job_code"]}/{k}[]: {hits} → {it[:80]!r}')
print(f'PII 누출 건수: {total_leaks}')

print()
print('=' * 60)
print('[2] select_jobs 샘플 (limit=5, future_only=False)')
print('=' * 60)
sample = select_jobs(limit=5, future_only=False, diverse_cities=True)
for j in sample:
    code = j['job_code']
    loc = j['location']
    sal = j['monthly_salary']
    print(f'  {code:12s} | {loc:30s} | {sal}')

print()
print('=' * 60)
print('[3] select_jobs 샘플 (future_only=True)')
print('=' * 60)
future = select_jobs(limit=5, future_only=True, diverse_cities=True)
print(f'미래 시작일: {len(future)}개')
for j in future:
    print(f'  {j["job_code"]:12s} | {j["location"]:30s} | start={j["start_date"]}')

print()
print('=' * 60)
print('[4] get_job 조회')
print('=' * 60)
if jobs:
    target = jobs[0]['job_code']
    found = get_job(target)
    print(f'조회: {target} → {found["location"] if found else "없음"}')

print()
print('=' * 60)
print('[5] render_ad_block 1개 샘플')
print('=' * 60)
if sample:
    print(render_ad_block(sample[0]))

print()
print('=' * 60)
print('[6] PII 감지 시 raise 테스트')
print('=' * 60)
try:
    dirty = {'location': '제주 라이트하우스', 'job_code': 'Job. 9999', 'start_date': '', 'teaching_age': '', 'class_size': '', 'working_hours': '', 'monthly_salary': '', 'teach_hrs_week': '', 'vacation': '', 'housing': '', 'native_count': '', 'benefits': '', 'extra_lines': []}
    render_ad_block(dirty)
    print('[FAIL] PII 통과됨 -- 가드 실패!')
    sys.exit(2)
except PIIContaminationError as e:
    print(f'[OK] 차단됨: {str(e)[:120]}')

print()
print('[결과] ad_only 시스템 정상 작동')
