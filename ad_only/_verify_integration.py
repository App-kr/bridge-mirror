# -*- coding: utf-8 -*-
"""
ad_only 통합 검증 -- RPA / Teast 가 실제로 PII 차단하는지 확인.

실행:
  python ad_only/_verify_integration.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ad_only.loader import load_all_jobs, select_jobs, render_ad_block
from ad_only.pii_guard import scan, PIIContaminationError, assert_clean


def _ok(msg: str) -> None:
    print(f'  [OK]   {msg}')


def _fail(msg: str) -> None:
    print(f'  [FAIL] {msg}')
    raise SystemExit(1)


def test_1_source_clean() -> None:
    print('\n[TEST 1] ad_only/jobs_clean.txt 소스에 PII 없음')
    jobs = load_all_jobs(force_reparse=True)
    leaks = 0
    for j in jobs:
        for k, v in j.items():
            strict = (k == 'location')
            if isinstance(v, str) and v:
                if scan(v, strict_brand=strict):
                    leaks += 1
            elif isinstance(v, list):
                for it in v:
                    if isinstance(it, str) and scan(it, strict_brand=strict):
                        leaks += 1
    if leaks > 0:
        _fail(f'{leaks}건 누출')
    _ok(f'{len(jobs)}개 잡, PII 누출 0건')


def test_2_teast_builder() -> None:
    print('\n[TEST 2] Teast build_description -- 클린 출력')
    from tools._teast_build_post import select_jobs as teast_sel, build_description
    jobs = teast_sel(limit=8)
    if not jobs:
        _fail('잡 선택 실패')
    body = build_description(jobs)
    # URL만 예외적으로 허용 (tinyurl.com/bridgekr는 의도된 공개 URL)
    test_body = body.replace('https://tinyurl.com/bridgekr', '')
    hits = scan(test_body, strict_brand=True)
    if hits:
        _fail(f'유출: {hits}')
    _ok(f'{len(jobs)}개 잡, {len(body)}자 본문, PII 0건')


def test_3_teast_rejects_dirty_input() -> None:
    print('\n[TEST 3] render_ad_block -- 오염 입력 차단')
    dirty = {
        'location': '제주 라이트하우스',  # PII 주입
        'job_code': 'Job. 9999',
        'start_date': 'ASAP', 'teaching_age': '', 'class_size': '',
        'working_hours': '', 'monthly_salary': '', 'teach_hrs_week': '',
        'vacation': '', 'housing': '', 'native_count': '', 'benefits': '',
        'extra_lines': [],
    }
    try:
        render_ad_block(dirty)
        _fail('차단 실패 -- PII 통과됨')
    except PIIContaminationError:
        _ok('한글 업체명 차단 확인')


def test_4_rpa_guard_loaded() -> None:
    print('\n[TEST 4] Craigslist RPA -- ad_only 가드 import 성공')
    # craigslist_auto_rpa.py 전체 로드하면 sqlite 연결까지 발생하므로
    # _AD_GUARD_READY 플래그만 간접 확인
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_craig_test",
        str(Path(__file__).resolve().parent.parent / "craigslist_auto_rpa.py"),
    )
    # 경량: 소스만 문자열 검사
    src = Path(spec.origin).read_text(encoding='utf-8')
    required_markers = [
        'from ad_only.loader import load_all_jobs as _ad_load_all_jobs',
        'from ad_only.pii_guard import',
        '_AD_GUARD_READY',
        'ad_only 화이트리스트 미존재',
        '_ad_assert_clean(title_out',
        '_ad_assert_clean(body_out',
    ]
    missing = [m for m in required_markers if m not in src]
    if missing:
        _fail(f'누락 마커: {missing}')
    _ok('가드 import + fetch 필터 + 최종 assert 전부 존재')


def test_5_no_direct_master_db_reads() -> None:
    print('\n[TEST 5] Teast build 가 jobs 테이블에서 읽지 않음')
    from tools import _teast_build_post as tb
    src = Path(tb.__file__).read_text(encoding='utf-8')
    # FROM jobs 직접 SELECT 금지
    bad_patterns = [
        'FROM jobs\n',
        'FROM jobs ',
        'SELECT job_code, location',
    ]
    found = [p for p in bad_patterns if p in src]
    if found:
        _fail(f'금지 패턴 잔존: {found}')
    _ok('master.db jobs 직접 SELECT 없음')


def test_6_ad_only_guard_rejects_pii_fields() -> None:
    print('\n[TEST 6] pii_guard -- 전 방위 PII 차단')
    bad_inputs = [
        ('한글 포함', '강남 학원'),
        ('이메일', 'hr@example.com'),
        ('모바일', '010-1234-5678'),
        ('서울 번호', '02-555-1234'),
        ('URL', 'https://example.com'),
        ('실제 브랜드 (strict)', 'Chungdahm Learning'),
    ]
    for label, text in bad_inputs:
        hits = scan(text, strict_brand=True)
        if not hits:
            _fail(f'{label!r}: 차단 실패 -- {text!r}')
    _ok(f'6가지 PII 패턴 모두 차단')


def main() -> None:
    print('=' * 60)
    print('  ad_only 통합 검증')
    print('=' * 60)
    test_1_source_clean()
    test_2_teast_builder()
    test_3_teast_rejects_dirty_input()
    test_4_rpa_guard_loaded()
    test_5_no_direct_master_db_reads()
    test_6_ad_only_guard_rejects_pii_fields()
    print('\n' + '=' * 60)
    print('  [결과] 6/6 PASS -- ad_only 시스템 정상 작동')
    print('=' * 60)


if __name__ == '__main__':
    main()
