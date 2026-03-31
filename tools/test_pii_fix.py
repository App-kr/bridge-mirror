#!/usr/bin/env python3
"""
doc_processor v2.5 PII 규칙 테스트
- 이름: 성(Last name)만 삭제
- 위치: "South Korea"로 통일
- 근무처: 기호 제거 + 일반명 대체
"""

import sys
import re
from pathlib import Path

# doc_processor import
sys.path.insert(0, str(Path(__file__).parent))

# doc_processor의 필요한 함수/변수들을 직접 복사
def _is_korea(text: str) -> bool:
    KR_KEYWORDS = [
        "seoul", "busan", "daegu", "incheon", "gwangju", "daejeon", "ulsan",
        "jeju", "gyeonggi", "gangwon", "chungbuk", "chungnam", "jeonbuk", "jeonnam",
        "gyeongbuk", "gyeongnam", "korea", "korean", "k-", "rok"
    ]
    lower = text.lower().strip()
    return any(kw in lower for kw in KR_KEYWORDS)


def _replace_workplace_generic(value: str) -> str:
    """근무처 명을 일반명으로 대체"""
    cleaned = value.strip()
    if not cleaned:
        return "Academy"

    # 기호 제거
    cleaned = re.sub(r"[!@#$%&*\-_~'\".,;():\[\]{}/?\\]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    lower = cleaned.lower()

    # 키워드 매칭
    if any(kw in lower for kw in ["english", "esl", "language", "english institute", "english academy"]):
        return "English Institute"
    if any(kw in lower for kw in ["academy", "hagwon", "cram"]):
        return "Academy"
    if any(kw in lower for kw in ["institute"]):
        return "Institute"
    if any(kw in lower for kw in ["university", "college", "school"]):
        return "University"
    if any(kw in lower for kw in ["company", "corporation", "co", "ltd", "inc"]):
        return "Company"

    return "Academy"


# ════════════════════════════════════════════════════
# 테스트 케이스
# ════════════════════════════════════════════════════

print("=" * 70)
print("TEST 1: 이름 처리 (성만 삭제)")
print("=" * 70)

test_cases_name = [
    ("John Smith", "Smith"),          # 성 제거
    ("Maria Garcia Lopez", "Garcia"),  # 가운데 이름 + 성
    ("Yuki Tanaka", "Tanaka"),        # 성 제거
]

for full_name, expected_deleted in test_cases_name:
    words = full_name.split()
    if len(words) >= 2:
        last_name = words[-1]
        if len(last_name) >= 2:
            pat = re.compile(re.escape(last_name), re.IGNORECASE)
            result_text = pat.sub("", full_name)
            print(f"  원본: '{full_name}'")
            print(f"  → 삭제된 성: '{last_name}'")
            print(f"  → 결과: '{result_text.strip()}'")
            print()

print("\n" + "=" * 70)
print("TEST 2: 위치 처리 (South Korea로 통일)")
print("=" * 70)

test_cases_location = [
    "Seoul, South Korea",
    "Busan, Korea",
    "current location: Seoul",
    "residing in Gangnam, South Korea",
]

for location in test_cases_location:
    if _is_korea(location):
        # LOCATION_LABELS 처리 시뮬레이션
        # "location:" 패턴 찾기
        pat = re.compile(r"(location\s*:?\s*)(.+)", re.I)
        def _loc_rep(m):
            prefix, value = m.group(1), m.group(2).strip()
            return f"{prefix}South Korea"

        result = pat.sub(_loc_rep, location) if pat.search(location) else location
        if pat.search(location):
            print(f"  원본: '{location}'")
            print(f"  → 결과: '{result}'")
        else:
            print(f"  원본: '{location}' (라벨 없음, 직접 확인 필요)")
    print()

print("\n" + "=" * 70)
print("TEST 3: 근무처 처리 (기호 제거 + 일반명 대체)")
print("=" * 70)

test_cases_workplace = [
    ("JS English Academy Seoul", "English Institute"),
    ("POLY-HAGWON (Busan Center)", "Academy"),
    ("YBM ECC Incheon", "English Institute"),
    ("TOP Academy & Cram School", "Academy"),
    ("ABC Company Ltd.", "Company"),
    ("Random Name!@#$%", "Academy"),  # 기본값
    ("K-University", "University"),
]

for workplace, expected in test_cases_workplace:
    result = _replace_workplace_generic(workplace)
    status = "OK" if result == expected else "NG"
    print(f"  [{status}] '{workplace}' -> '{result}' (Expected: '{expected}')")

print("\n" + "=" * 70)
print("TEST 4: WORKPLACE_LABELS 통합 처리")
print("=" * 70)

test_text = """
Current Employer: YBM ECC Seoul
School Name: TOP Academy & Hagwon
Workplace: JS English Institute Busan
Academy: Random School !@#$%
"""

print("원본 텍스트:")
print(test_text)
print("\n처리된 텍스트 (예상):")

WORKPLACE_LABELS = [
    "current employer", "employer", "company", "workplace",
    "school name", "academy name", "hagwon",
    "현 직장", "근무지", "학원명", "학교명",
]

result = test_text
for label in WORKPLACE_LABELS:
    pat = re.compile(rf"({re.escape(label)}\s*:?\s*)(.+)", re.I)
    def _work_rep(m):
        original_value = m.group(2).strip()
        generic_value = _replace_workplace_generic(original_value)
        return f"{m.group(1)}{generic_value}"
    result = pat.sub(_work_rep, result)

print(result)

print("\n" + "=" * 70)
print("✅ 모든 테스트 완료!")
print("=" * 70)
