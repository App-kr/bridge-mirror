"""
이력서 텍스트 추출 진단 스크립트
- 원본 PDF 직접 로드 (확정본)
- extract_text_from_pdf() 결과와 raw PyMuPDF 결과 비교
- 날짜 범위 / 불릿 / 이름 누락 여부 진단
"""
import sys
import re
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))

import fitz
from tools.resume_converter.pdf_builder import extract_text_from_pdf, _extract_page_column_aware
from tools.resume_converter.pii_engine import analyze_pii

TEST = HERE / "testdata"
FILES = ["ref_5831.pdf", "ref_6014.pdf", "ref_6053.pdf"]

DATE_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}"
    r"|\d{1,2}/\d{4}"
    r"|\d{4}\s*[-–]\s*\d{4}"
    r"|\d{4}\s*[-–]\s*(?:present|current)",
    re.IGNORECASE,
)
BULLET_RE = re.compile(r"[•●▪◦‣⁃∙·]")


def scan_source(p: Path):
    """raw PyMuPDF text (컬럼 미적용) — 원본에 실제 무엇이 있는지."""
    doc = fitz.open(str(p))
    raw = "\n".join(pg.get_text("text") for pg in doc)
    doc.close()
    return raw


def run(p: Path):
    print(f"\n{'='*70}\nFILE: {p.name} ({p.stat().st_size//1024} KB)\n{'='*70}")
    raw = scan_source(p)
    extracted = extract_text_from_pdf(p)

    raw_dates = DATE_RE.findall(raw)
    ext_dates = DATE_RE.findall(extracted)
    raw_bullets = len(BULLET_RE.findall(raw))
    ext_bullets = len(BULLET_RE.findall(extracted))

    print(f"\n[RAW  원본 PyMuPDF]  chars={len(raw)}  dates={len(raw_dates)}  bullets={raw_bullets}")
    print(f"[EXT  컬럼정렬후 ]  chars={len(extracted)}  dates={len(ext_dates)}  bullets={ext_bullets}")

    missing_dates = [d for d in raw_dates if d not in extracted]
    if missing_dates:
        print(f"\n⚠ 추출 후 사라진 날짜 {len(missing_dates)}개:")
        for d in missing_dates[:5]:
            print(f"  - {d}")

    if raw_bullets > ext_bullets:
        print(f"\n⚠ 불릿 손실: {raw_bullets} → {ext_bullets} ({raw_bullets - ext_bullets}개 누락)")

    # PII 처리 후
    pii = analyze_pii(extracted, known_names=[])
    pii_dates = DATE_RE.findall(pii.cleaned_text)
    pii_bullets = len(BULLET_RE.findall(pii.cleaned_text))
    print(f"[PII  제거후    ]  chars={len(pii.cleaned_text)}  dates={len(pii_dates)}  bullets={pii_bullets}")
    print(f"  PII 매치 {len(pii.pii_found)}건: {[(m.type, m.original_value[:40]) for m in pii.pii_found[:8]]}")

    # 처음 20줄 미리보기
    print(f"\n--- RAW 원본 앞 15줄 ---")
    for ln in raw.split("\n")[:15]:
        print(f"  {ln!r}")
    print(f"\n--- EXT 컬럼정렬 앞 15줄 ---")
    for ln in extracted.split("\n")[:15]:
        print(f"  {ln!r}")


if __name__ == "__main__":
    for fn in FILES:
        run(TEST / fn)
