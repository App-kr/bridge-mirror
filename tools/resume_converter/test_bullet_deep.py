"""
_apply_regex 내부 단계별 불릿 카운트 추적 (monkey-patched).
"""
import sys
import re
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))

from tools.resume_converter.pdf_builder import extract_text_from_pdf
from tools.resume_converter import pii_engine as pe

text = extract_text_from_pdf(HERE / "testdata" / "ref_5831.pdf")
print(f"원본 시작: {text.count('•')}\n")

# _apply_regex 코드를 복제하되 단계별 bullet 카운트
_BULLET = "•"
cleaned = text
found = []

_doc_has_korea = bool(
    re.search(r"\b(?:South\s+Korea|Korea|한국)\b", text, re.IGNORECASE)
    or pe._KR_CITY_RE.search(text)
    or re.search(r"[가-힣]", text)
)
print(f"_doc_has_korea = {_doc_has_korea}")
print(f"초기 cleaned: {cleaned.count(_BULLET)}개 불릿\n")

# 기본 PATTERNS 루프
for ptype, pattern in pe._PATTERNS.items():
    before = cleaned.count(_BULLET)
    match_list = list(pattern.finditer(cleaned))
    for m in match_list:
        if ptype in ("phone_kr", "phone_intl", "phone_us") and pe._is_year_range(m.group(0)):
            continue
        replacement = f"[{ptype.upper()}_REMOVED]"
        cleaned = cleaned.replace(m.group(0), replacement, 1)
    after = cleaned.count(_BULLET)
    if match_list:
        print(f"  [{ptype}] {len(match_list)}건 매치, 불릿 {before}→{after}")
        if before != after:
            print(f"    ⚠ 매치 내용:")
            for m in match_list:
                val = m.group(0)
                if _BULLET in val:
                    print(f"      🚨 '•' 포함 매치: {val!r}")
                else:
                    print(f"      - {val!r}")

# RE_KR_RESIDENTIAL
before = cleaned.count(_BULLET)
for m in pe.RE_KR_RESIDENTIAL.finditer(cleaned):
    cleaned = cleaned.replace(m.group(0), "South Korea", 1)
print(f"\n  [RE_KR_RESIDENTIAL] 불릿 {before}→{cleaned.count(_BULLET)}")

# 학교명 줄 단위 루프
lines = cleaned.split("\n")
new_lines = []
in_edu_section = False
_EDU_HDR_RE = pe._EDU_HDR_RE
_NON_EDU_HDR_RE = pe._NON_EDU_HDR_RE

for i, line in enumerate(lines):
    if _EDU_HDR_RE.match(line):
        in_edu_section = True
    elif _NON_EDU_HDR_RE.match(line):
        in_edu_section = False

    window = " ".join(lines[max(0, i - 2):i + 3])
    has_kr_ctx = _doc_has_korea or bool(
        re.search(r"\b(?:South\s+Korea|Korea|한국)\b", window, re.IGNORECASE)
        or pe._KR_CITY_RE.search(window)
        or re.search(r"[가-힣]", window)
    )

    for m in pe.RE_SCHOOL_NAMED.finditer(line):
        orig = m.group(0)
        if any(kw.lower() in orig.lower() for kw in pe.PRESERVE_INSTITUTION):
            continue
        if pe._TITLE_SAFE_RE.search(orig) and not (has_kr_ctx and len(orig.split()) >= 3):
            continue
        if in_edu_section:
            continue
        if not has_kr_ctx:
            continue
        repl = "English Academy, South Korea"
        line = line.replace(orig, repl, 1)

    new_lines.append(line)
before = cleaned.count(_BULLET)
cleaned = "\n".join(new_lines)
print(f"  [RE_SCHOOL_NAMED 루프] 불릿 {before}→{cleaned.count(_BULLET)}")

# _KR_CITY_RE
before = cleaned.count(_BULLET)
for m in pe._KR_CITY_RE.finditer(cleaned):
    cleaned = cleaned.replace(m.group(0), "South Korea", 1)
print(f"  [_KR_CITY_RE] 불릿 {before}→{cleaned.count(_BULLET)}")

# KR_ACADEMY + KR_WORKPLACE 루프
lines3 = cleaned.split("\n")
new_lines3 = []
for i, line in enumerate(lines3):
    window3 = " ".join(lines3[max(0, i - 2):i + 3])
    has_kr3 = _doc_has_korea or bool(
        re.search(r"\b(?:South\s+Korea|Korea|한국)\b", window3, re.IGNORECASE)
        or pe._KR_CITY_RE.search(window3)
        or re.search(r"[가-힣]", window3)
    )
    has_foreign3 = bool(
        pe.RE_FOREIGN_CITY.search(window3) or pe.RE_US_CITY_STATE.search(window3)
    )

    for m in pe._KR_ACADEMY_RE_finditer(line):
        orig = m.group(0)
        if has_foreign3 and not has_kr3:
            continue
        if pe._TITLE_SAFE_RE.search(line) and not has_kr3:
            continue
        line = line.replace(orig, "English Academy, South Korea", 1)

    if has_kr3:
        for m in pe._KR_WORKPLACE.finditer(line):
            orig = m.group(0)
            if pe._TITLE_SAFE_RE.search(orig):
                continue
            line = line.replace(orig, "English Academy, South Korea", 1)

    new_lines3.append(line)
before = cleaned.count(_BULLET)
cleaned = "\n".join(new_lines3)
print(f"  [KR_ACADEMY+WORKPLACE 루프] 불릿 {before}→{cleaned.count(_BULLET)}")

# PII_LABEL
before = cleaned.count(_BULLET)
cleaned = pe._PII_LABEL_RE.sub("", cleaned)
print(f"  [_PII_LABEL_RE] 불릿 {before}→{cleaned.count(_BULLET)}")

# BARE_DOB
before = cleaned.count(_BULLET)
cleaned = pe._BARE_DOB_RE.sub("", cleaned)
print(f"  [_BARE_DOB_RE] 불릿 {before}→{cleaned.count(_BULLET)}")

# BARE_PERSONAL
before = cleaned.count(_BULLET)
cleaned = pe._BARE_PERSONAL_RE.sub("", cleaned)
print(f"  [_BARE_PERSONAL_RE] 불릿 {before}→{cleaned.count(_BULLET)}")

# References
before = cleaned.count(_BULLET)
cleaned = pe.remove_reference_section(cleaned)
print(f"  [references] 불릿 {before}→{cleaned.count(_BULLET)}")

# Campus
before = cleaned.count(_BULLET)
cleaned = re.sub(r"\s+Campus\b(?!\s+of\b)", "", cleaned, flags=re.IGNORECASE)
print(f"  [Campus] 불릿 {before}→{cleaned.count(_BULLET)}")

# ADDR_KR_EN
before = cleaned.count(_BULLET)
cleaned = re.sub(r"\[ADDR_KR_EN_REMOVED\][ \t]*,?[ \t]*", "", cleaned)
print(f"  [ADDR_KR_EN cleanup] 불릿 {before}→{cleaned.count(_BULLET)}")

# Gasan-dong
before = cleaned.count(_BULLET)
cleaned = re.sub(
    r"\b[A-Z][A-Za-z\-]+-(?:dong|gu|si|ro|gil)\b[,\s]*(?:South\s+)?Korea\b",
    "South Korea",
    cleaned,
    flags=re.IGNORECASE,
)
print(f"  [dong-gu pattern] 불릿 {before}→{cleaned.count(_BULLET)}")

# {word},Seoul,Korea
before = cleaned.count(_BULLET)
cleaned = re.sub(
    r"\b[A-Z][A-Za-z\-]+,\s*Seoul,?\s*South\s+Korea\b",
    "South Korea",
    cleaned,
    flags=re.IGNORECASE,
)
print(f"  [word,Seoul,Korea] 불릿 {before}→{cleaned.count(_BULLET)}")

print(f"\n최종: {cleaned.count(_BULLET)}개 불릿")
