"""
v3.0 PII 엔진 — Michelle Sibanda (6147) 실테스트
- 변환전 (2).pdf 원본 로드
- pii_engine.analyze_pii() 실행
- Knox / Leeuwpoort / PROFESSIONAL EXPERIENCES / closing firstname 검증
"""
import sys
import re
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))

from tools.resume_converter.pdf_builder import extract_text_from_pdf
from tools.resume_converter.pii_engine import analyze_pii

CV = Path(r"C:/Users/Scarlett/Desktop/변환전 (2).pdf")
CL = Path(r"C:/Users/Scarlett/Desktop/변환전 (1).pdf")

KNOWN = ["Michelle Sinikiwe Sibanda", "Michelle Sibanda", "Sibanda", "Sinikiwe"]


def check(label: str, text_before: str, text_after: str, needle: str, should_remain: bool):
    hit_before = needle.lower() in text_before.lower()
    hit_after = needle.lower() in text_after.lower()
    ok = (hit_after == should_remain) if hit_before else True
    mark = "✅" if ok else "❌"
    verb = "보존" if should_remain else "익명화"
    print(f"  {mark} [{verb}] {label!r}: 원본={hit_before} → 결과={hit_after}")


def run(pdf: Path, label: str):
    print(f"\n{'='*70}\n{label}: {pdf.name}\n{'='*70}")
    if not pdf.exists():
        print(f"  ⚠ 파일 없음")
        return
    text = extract_text_from_pdf(pdf)
    print(f"  원본 추출: {len(text)} chars, 줄수={text.count(chr(10))+1}")

    result = analyze_pii(text, known_names=KNOWN)
    print(f"\n  PII 매치 {len(result.pii_found)}건:")
    for m in result.pii_found[:15]:
        v = m.original_value.replace("\n", " ")[:60]
        print(f"    - {m.type:14s}  {v!r}")

    print(f"\n  검증:")
    check("Knox Academy", text, result.cleaned_text, "Knox Academy", False)
    check("Leeuwpoort Primary School", text, result.cleaned_text, "Leeuwpoort", False)
    check("University of South Africa", text, result.cleaned_text, "University of South Africa", True)
    check("PROFESSIONAL EXPERIENCES header", text, result.cleaned_text, "PROFESSIONAL EXPERIENCE", True)
    check("phone +27670216180", text, result.cleaned_text, "+27670216180", False)
    check("email sibandam156", text, result.cleaned_text, "sibandam156", False)
    check("South Africa", text, result.cleaned_text, "South Africa", False)
    check("날짜 2023", text, result.cleaned_text, "2023", True)
    check("Sibanda (성)", text, result.cleaned_text, "Sibanda", False)
    check("Michelle (이름)", text, result.cleaned_text, "Michelle", True)

    # 커버레터 종결인사 (Yours sincerely 등) 보존 확인
    for phrase in ["Yours sincerely", "Sincerely", "Best regards", "Kind regards"]:
        if phrase.lower() in text.lower():
            check(f"closing '{phrase}'", text, result.cleaned_text, phrase, True)

    # 결과 텍스트 일부 미리보기
    print(f"\n  결과 마지막 20줄:")
    for ln in result.cleaned_text.split("\n")[-20:]:
        if ln.strip():
            print(f"    {ln!r}")


if __name__ == "__main__":
    run(CL, "커버레터")
    run(CV, "이력서")
