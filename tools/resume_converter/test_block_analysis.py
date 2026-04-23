"""Block 단위 분석 — 2-column 감지 + block 내부 라인 구조."""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))

import fitz

RESUME = HERE / "testdata" / "inbox_6147_20260422_200733" / "6147_resume.pdf"
doc = fitz.open(str(RESUME))

for pgi, page in enumerate(doc):
    print(f"\n=== Page {pgi+1} (w={page.rect.width:.0f}, h={page.rect.height:.0f}) ===")
    mid = page.rect.width / 2
    blocks = page.get_text("blocks")
    blocks = [(b[0], b[1], b[2], b[3], b[4]) for b in blocks if b[6] == 0 and b[4].strip()]

    # x0 분포
    xs = sorted(set(round(b[0], 0) for b in blocks))
    print(f"x0 분포 (페이지 mid={mid:.0f}): {xs[:15]}")

    # 각 block 위치·크기
    print(f"\n블록 {len(blocks)}개:")
    for b in blocks[:30]:
        x0, y0, x1, y1, txt = b
        zone = "L" if (x0+x1)/2 < mid else "R"
        nl = txt.count("\n")
        preview = txt.replace("\n", " | ")[:80]
        print(f"  [{zone}] y={y0:5.1f}-{y1:5.1f}  x={x0:5.1f}-{x1:5.1f} nl={nl}  {preview!r}")

doc.close()
