# -*- coding: utf-8 -*-
"""
ad_only/pii_guard.py -- Fail-closed PII 가드 (광고 전용)

규칙:
- 한글 1자라도 포함 → SecurityError
- 이메일 주소 패턴 → SecurityError
- 한국 휴대폰 번호 → SecurityError
- 고정 전화번호 (02-xxx-xxxx / 031-xxx-xxxx) → SecurityError
- 업체 접미사 키워드 → SecurityError
"""
from __future__ import annotations
import re

class PIIContaminationError(RuntimeError):
    """PII가 감지됨. 이 데이터는 광고에 사용 금지."""


RE_KOREAN = re.compile(r'[\uAC00-\uD7A3\u3131-\u318E]')
RE_EMAIL  = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
RE_MOBILE = re.compile(r'\b01[016789][\s\-.]?\d{3,4}[\s\-.]?\d{4}\b')
RE_LAND   = re.compile(r'\b0(?:2|[3-6][0-9])[\s\-.]?\d{3,4}[\s\-.]?\d{4}\b')
RE_URL    = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)

# 실제 업체 브랜드명 (협력처/경쟁사). location 필드에만 엄격 적용.
# 일반어(school, bridge, language 등)는 광고문 정상 사용이므로 제외.
RE_BRAND_STRICT = re.compile(
    r'\b(?:avalon|chungdahm|cdi|poly|polyschool|gnb|april|'
    r'pagoda|ybm|ecc|sogang\s*language|crown\s*english|'
    r'cms|lingo|eyeway|eyelevel|kumon|sylvan|berlitz|wallstreet|'
    r'helen\s*doron|maple\s*bear|little\s*kinder|kidsville|'
    r'riseenglish|rise\s*english|altiora|slp|emg\s*education)\b',
    re.IGNORECASE,
)

# 전체 텍스트 검사용 -- 한글/이메일/전화/URL 만
def _scan_base(text: str) -> list[str]:
    hits: list[str] = []
    if RE_KOREAN.search(text):
        hits.append('KOREAN')
    if RE_EMAIL.search(text):
        hits.append('EMAIL')
    if RE_MOBILE.search(text):
        hits.append('MOBILE')
    if RE_LAND.search(text):
        hits.append('LANDLINE')
    if RE_URL.search(text):
        hits.append('URL')
    return hits


def scan(text: str, *, strict_brand: bool = False) -> list[str]:
    """
    텍스트에서 PII 후보 반환. 빈 리스트면 clean.

    - strict_brand=True  : location 필드 등 업체명 엄격 검사 추가
    - strict_brand=False : 한글/이메일/전화/URL 만 검사 (일반 필드용)
    """
    if not text:
        return []
    hits = _scan_base(text)
    if strict_brand and RE_BRAND_STRICT.search(text):
        hits.append('BRAND_KEYWORD')
    return hits


def assert_clean(text: str, *, context: str = '', strict_brand: bool = False) -> None:
    """PII 감지 시 PIIContaminationError 발생. Fail-closed."""
    hits = scan(text, strict_brand=strict_brand)
    if hits:
        preview = text[:200].replace('\n', ' / ')
        raise PIIContaminationError(
            f"[PII-GUARD] 차단: {','.join(hits)} "
            f"{'@' + context if context else ''} | {preview!r}"
        )


def clean_or_raise(text: str, *, context: str = '', strict_brand: bool = False) -> str:
    """assert_clean 의 alias -- 로더/빌더가 import 하기 쉬운 이름."""
    assert_clean(text, context=context, strict_brand=strict_brand)
    return text


if __name__ == '__main__':
    # self-test
    test_cases = [
        # (text, expected_pass_normal, expected_pass_strict)
        ('Seoul Seongdong', True, True),
        ('Job. 2967', True, True),
        ('제주 라이트하우스', False, False),
        ('contact: abc@gmail.com', False, False),
        ('call 010-1234-5678', False, False),
        ('Chungdahm Academy', True, False),   # Chungdahm = 실 브랜드
        ('Kindergarten - Elementary', True, True),  # 학령어는 통과
        ('Bachelor or higher with an F visa', True, True),  # 일반문
        ('Employee Benefits : Visa sponsorship', True, True),
        ('Teaching Age : Kindy - Elem', True, True),
        ('Monthly Salary : 2.40m - 3.20m KRW', True, True),
        ('visit https://bridgejob.co.kr', False, False),
    ]
    all_ok = True
    for text, exp_normal, exp_strict in test_cases:
        hits_n = scan(text, strict_brand=False)
        hits_s = scan(text, strict_brand=True)
        ok_n = (not hits_n) == exp_normal
        ok_s = (not hits_s) == exp_strict
        mark = 'OK' if (ok_n and ok_s) else 'FAIL'
        if not (ok_n and ok_s):
            all_ok = False
        print(f'[{mark}] {text!r:50s} normal={hits_n} strict={hits_s}')
    print('\n전체:', 'PASS' if all_ok else 'FAIL')
