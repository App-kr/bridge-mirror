"""
test_pii_patch.py — PII 엔진 7건 버그수정 검증
체크리스트:
  □ 대학교명 보존
  □ 학위/전공명 보존
  □ 직함(School/English) 보존
  □ 한국 도시 삭제→South Korea
  □ 해외 도시 보존
  □ 한국 학원명 → English Academy
  □ 해외 교육기관 보존
  □ 이름 삭제 (regex only)
  □ 번호 54pt / 사진 크기 확인 (pdf_builder 상수)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.resume_converter.pii_engine import analyze_pii

PASS = "[PASS]"
FAIL = "[FAIL]"

results = []

def chk(label, text_in, must_contain=None, must_not_contain=None):
    result = analyze_pii(text_in, api_key=None)
    out = result.cleaned_text
    ok = True
    notes = []
    for s in (must_contain or []):
        if s.lower() not in out.lower():
            ok = False
            notes.append(f"  미포함: '{s}'")
    for s in (must_not_contain or []):
        if s.lower() in out.lower():
            ok = False
            notes.append(f"  잔류: '{s}'")
    tag = PASS if ok else FAIL
    results.append((tag, label, notes, out))

# ── 수정 1: 대학교명 보존 ───────────────────────────────────────────────
chk(
    "대학교명 보존 (Oklahoma State University)",
    "Education\nOklahoma State University (2025)\nBachelor of Science",
    must_contain=["Oklahoma State University"],
)
chk(
    "대학교명 보존 (Miami Dade College)",
    "Education\nMiami Dade College (2015)\nAssociate of Arts",
    must_contain=["Miami Dade College"],
)
chk(
    "대학교명 보존 (University of Georgia)",
    "EDUCATION\nUniversity of Georgia, Athens, GA\nB.A. in Psychology",
    must_contain=["University of Georgia"],
)

# ── 수정 2: 학위/전공명 보존 ────────────────────────────────────────────
chk(
    "학위/전공명 보존 (M.Ed., Special Education)",
    "EDUCATION\nMaster of Education (M.Ed.), Special Education\nOklahoma State University",
    must_contain=["Special Education", "M.Ed."],
)
chk(
    "전공명 보존 (Psychology)",
    "EDUCATION\nB.A. in Psychology\nUniversity of Georgia",
    must_contain=["Psychology"],
)

# ── 수정 3: 직함 내 School/English 보존 ────────────────────────────────
chk(
    "직함 보존 (Middle & High School Teacher)",
    "EXPERIENCE\nMiddle & High School Teacher\nABC학원, South Korea 2020-2024",
    must_contain=["Middle & High School Teacher"],
)
chk(
    "직함 보존 (ESL / English Language Development)",
    "Skills: ESL / English Language Development\nEnglish Teacher",
    must_contain=["English Language Development", "English Teacher"],
)

# ── 수정 4: 한국 도시명 삭제 → South Korea ─────────────────────────────
chk(
    "한국 도시 삭제 (Mokpo → South Korea)",
    "Location: Mokpo\nWorked in Mokpo from 2019",
    must_contain=["South Korea"],
    must_not_contain=["Mokpo"],
)
chk(
    "한국 도시 삭제 (Seoul → South Korea)",
    "Seoul, South Korea\nBusan 2018-2020",
    must_not_contain=["Seoul", "Busan"],
)

# ── 수정 4 반대: 해외 도시 보존 ────────────────────────────────────────
chk(
    "해외 도시 보존 (Houston)",
    "Houston, TX\nHouston Public Schools, English Teacher",
    must_contain=["Houston"],
)
chk(
    "해외 도시 보존 (Calgary)",
    "OHC Calgary, Canada\nLanguage Instructor",
    must_contain=["Calgary"],
)
chk(
    "해외 도시 보존 (Prague)",
    "Prague, Czech Republic\nEnglish Teacher 2017-2019",
    must_contain=["Prague"],
)

# ── 수정 5: 한국 학원명 → English Academy ──────────────────────────────
chk(
    "한국 학원명 교체 (Broad Language School → English Academy)",
    "Broad Language School, Mokpo, South Korea\nEnglish Teacher",
    must_contain=["English Academy"],
    must_not_contain=["Broad Language School"],
)
chk(
    "한국 학원명 교체 (Altiora → English Academy)",
    "Altiora, Seoul, South Korea\nESL Teacher 2021-2023",
    must_contain=["English Academy"],
    must_not_contain=["Altiora"],
)
chk(
    "한국 학원명 교체 (YBM → English Academy)",
    "YBM English, Bundang, South Korea",
    must_contain=["English Academy"],
)

# ── 수정 5: 빈칸 방지 (전체 토큰 교체) ─────────────────────────────────
chk(
    "전체 토큰 교체 (잔여 문자 없음)",
    "Rise Academy, South Korea\nTeacher",
    must_not_contain=["Rise Academy"],
)

# ── 수정 6: English 단독 과삭제 방지 ───────────────────────────────────
chk(
    "English 스킬 보존",
    "Skills: English, Korean, French\nEnglish proficiency: Native",
    must_contain=["English"],
)

# ── 수정 7: 해외 교육기관 보존 ─────────────────────────────────────────
chk(
    "해외 교육기관 보존 (Houston Public Schools)",
    "Houston Public Schools\nHouston, TX\nEnglish/ESL Teacher 2016-2018",
    must_contain=["Houston Public Schools"],
)
chk(
    "해외 교육기관 보존 (OHC Calgary)",
    "OHC Calgary, Canada\nInstructor 2019-2020",
    must_contain=["OHC"],
)
chk(
    "해외 교육기관 보존 (Waimea Middle School, Hawaii)",
    "Waimea Middle School, Hawaii\nEnglish Teacher",
    must_contain=["Waimea Middle School"],
)

# ── 이름 삭제 (regex — 전화/이메일) ───────────────────────────────────
chk(
    "이메일 삭제",
    "Contact: john.smith@gmail.com\nTeacher",
    must_not_contain=["@gmail.com"],
)
chk(
    "한국 전화 삭제",
    "Phone: 010-1234-5678",
    must_not_contain=["010-1234-5678"],
)

# ── 출력 ────────────────────────────────────────────────────────────────
print("=" * 62)
print("  BRIDGE PII 패치 검증 결과")
print("=" * 62)
passed = sum(1 for r in results if r[0] == PASS)
total  = len(results)
for tag, label, notes, _ in results:
    print(f"{tag} {label}")
    for n in notes:
        print(n)
print("-" * 62)
print(f"결과: {passed}/{total} 통과")
if passed < total:
    print("\n[실패 항목 상세]")
    for tag, label, notes, out in results:
        if tag == FAIL:
            print(f"\n  {label}")
            print(f"  출력: {out[:120]!r}")
print("=" * 62)

# pdf_builder 상수 확인
print("\n[pdf_builder 크기 확인]")
try:
    import ast, re as _re
    src = (Path(__file__).parent / "pdf_builder.py").read_text(encoding="utf-8")
    font_m = _re.search(r'setFont\("Helvetica-Bold",\s*(\d+)\)', src)
    img_m  = _re.search(r'img\.resize\(\((\d+),\s*(\d+)\)', src)
    print(f"  번호 폰트 크기: {font_m.group(1) if font_m else '?'}pt  (목표: 54pt)")
    print(f"  사진 resize: {img_m.group(1) if img_m else '?'}x{img_m.group(2) if img_m else '?'}px  (목표: 110x147)")
except Exception as e:
    print(f"  확인 실패: {e}")
