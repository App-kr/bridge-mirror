"""추출된 텍스트 라인 폭 분포 진단 — 가로 여백 원인 확인."""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))

from tools.resume_converter.pdf_builder import extract_text_from_pdf
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
import os

# 폰트 등록
pdfmetrics.registerFont(TTFont("KO", "C:/Windows/Fonts/malgun.ttf"))

page_w, page_h = A4
max_w = page_w - 1.5 * cm * 2   # 본문 폭
print(f"본문 폭: {max_w:.1f}pt")

RESUME = HERE / "testdata" / "inbox_6147_20260422_200733" / "6147_resume.pdf"
text = extract_text_from_pdf(RESUME)

lines = text.split("\n")
print(f"\n총 라인 수: {len(lines)}")

# 분포 계산
buckets = {"빈줄": 0, "<30%": 0, "30~50%": 0, "50~70%": 0, "70~90%": 0, "90%+": 0}
short_samples = []
for ln in lines:
    s = ln.rstrip()
    if not s.strip():
        buckets["빈줄"] += 1
        continue
    w = stringWidth(s, "KO", 10)
    ratio = w / max_w
    if ratio < 0.3:
        buckets["<30%"] += 1
        if len(short_samples) < 20:
            short_samples.append((ratio, s))
    elif ratio < 0.5:
        buckets["30~50%"] += 1
    elif ratio < 0.7:
        buckets["50~70%"] += 1
    elif ratio < 0.9:
        buckets["70~90%"] += 1
    else:
        buckets["90%+"] += 1

print("\n라인 폭 분포 (본문 폭 대비):")
for k, v in buckets.items():
    print(f"  {k:10s}: {v:3d}")

print("\n<30% 샘플 (처음 20개):")
for r, s in short_samples:
    print(f"  {r*100:5.1f}%  {s[:80]!r}")

# 연속된 짧은 라인 탐지 → 병합 후보
print("\n연속 짧은 라인 (3개 이상 연속, <60%):")
run = []
runs = []
for ln in lines:
    s = ln.rstrip()
    if not s.strip():
        if len(run) >= 3:
            runs.append(run[:])
        run = []
        continue
    w = stringWidth(s, "KO", 10)
    if w / max_w < 0.6:
        run.append(s)
    else:
        if len(run) >= 3:
            runs.append(run[:])
        run = []
if len(run) >= 3:
    runs.append(run)
print(f"  총 {len(runs)} 블록, 평균 {sum(len(r) for r in runs)/max(1,len(runs)):.1f}줄")
for r in runs[:5]:
    print(f"  --- {len(r)}줄 ---")
    for ln in r[:6]:
        print(f"     {ln[:80]!r}")
