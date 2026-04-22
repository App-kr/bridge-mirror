"""
PII 단계별로 '•' 불릿이 어디서 사라지는지 추적.
"""
import sys
import re
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))

from tools.resume_converter.pdf_builder import extract_text_from_pdf
from tools.resume_converter import pii_engine as pe

p = HERE / "testdata" / "ref_5831.pdf"
text = extract_text_from_pdf(p)
print(f"시작: {text.count('•')}개 불릿")

# 실제 _apply_regex 경로
print("\n=== 실제 _apply_regex() 실행 ===")
real_cleaned, real_found = pe._apply_regex(text)
print(f"_apply_regex 후: {real_cleaned.count('•')}개 불릿")
print(f"매치 수: {len(real_found)}")
for m in real_found[:10]:
    print(f"  {m.type}: {m.original_value!r}")
print()
print("--- _apply_regex 결과 앞 20줄 ---")
for ln in real_cleaned.split("\n")[:20]:
    print(f"  {ln!r}")
print()
print("=== 이제 수동 단계별 ===\n")

cleaned = text
# 기본 패턴 하나씩
for name, pattern in pe._PATTERNS.items():
    before = cleaned.count("•")
    cleaned = pattern.sub(f"[{name.upper()}_REMOVED]", cleaned)
    after = cleaned.count("•")
    if before != after:
        print(f"  ⚠ {name}: {before} → {after} (-{before - after})")

# RE_KR_RESIDENTIAL
before = cleaned.count("•")
cleaned = pe.RE_KR_RESIDENTIAL.sub("South Korea", cleaned)
print(f"  RE_KR_RESIDENTIAL: {before} → {cleaned.count('•')}")

# 학교명 루프 (간략)
before = cleaned.count("•")
lines = cleaned.split("\n")
new_lines = []
for line in lines:
    for m in pe.RE_SCHOOL_NAMED.finditer(line):
        line = line.replace(m.group(0), "English Academy, South Korea", 1)
    new_lines.append(line)
cleaned = "\n".join(new_lines)
print(f"  RE_SCHOOL_NAMED 루프: {before} → {cleaned.count('•')}")

# _KR_CITY_RE
before = cleaned.count("•")
cleaned = pe._KR_CITY_RE.sub("South Korea", cleaned)
print(f"  _KR_CITY_RE: {before} → {cleaned.count('•')}")

# _KR_ACADEMY
before = cleaned.count("•")
if pe._KR_ACADEMY_RE_LONG:
    cleaned = pe._KR_ACADEMY_RE_LONG.sub("English Academy, South Korea", cleaned)
if pe._KR_ACADEMY_RE_SHORT:
    cleaned = pe._KR_ACADEMY_RE_SHORT.sub("English Academy, South Korea", cleaned)
print(f"  _KR_ACADEMY: {before} → {cleaned.count('•')}")

# _KR_WORKPLACE
before = cleaned.count("•")
cleaned = pe._KR_WORKPLACE.sub("English Academy, South Korea", cleaned)
print(f"  _KR_WORKPLACE: {before} → {cleaned.count('•')}")

# _PII_LABEL_RE
before = cleaned.count("•")
cleaned = pe._PII_LABEL_RE.sub("", cleaned)
print(f"  _PII_LABEL_RE: {before} → {cleaned.count('•')}")

# _BARE_DOB_RE
before = cleaned.count("•")
cleaned = pe._BARE_DOB_RE.sub("", cleaned)
print(f"  _BARE_DOB_RE: {before} → {cleaned.count('•')}")

# _BARE_PERSONAL_RE
before = cleaned.count("•")
cleaned = pe._BARE_PERSONAL_RE.sub("", cleaned)
print(f"  _BARE_PERSONAL_RE: {before} → {cleaned.count('•')}")

# remove_reference_section
before = cleaned.count("•")
cleaned = pe.remove_reference_section(cleaned)
print(f"  remove_reference_section: {before} → {cleaned.count('•')}")

# Campus
before = cleaned.count("•")
cleaned = re.sub(r"\s+Campus\b(?!\s+of\b)", "", cleaned, flags=re.IGNORECASE)
print(f"  Campus sub: {before} → {cleaned.count('•')}")

# ADDR_KR_EN_REMOVED
before = cleaned.count("•")
cleaned = re.sub(r"\[ADDR_KR_EN_REMOVED\][ \t]*,?[ \t]*", "", cleaned)
print(f"  ADDR_KR_EN cleanup: {before} → {cleaned.count('•')}")

# Gasan-dong pattern
before = cleaned.count("•")
cleaned = re.sub(
    r"\b[A-Z][A-Za-z\-]+-(?:dong|gu|si|ro|gil)\b[,\s]*(?:South\s+)?Korea\b",
    "South Korea",
    cleaned,
    flags=re.IGNORECASE,
)
print(f"  Gasan-dong pattern: {before} → {cleaned.count('•')}")

# Seoul South Korea pattern
before = cleaned.count("•")
cleaned = re.sub(
    r"\b[A-Z][A-Za-z\-]+,\s*Seoul,?\s*South\s+Korea\b",
    "South Korea",
    cleaned,
    flags=re.IGNORECASE,
)
print(f"  {{dong}},Seoul,Korea pattern: {before} → {cleaned.count('•')}")

print(f"\n최종: {cleaned.count('•')}개 불릿")
print("\n--- 최종 결과 앞 30줄 ---")
for ln in cleaned.split("\n")[:30]:
    print(f"  {ln!r}")
