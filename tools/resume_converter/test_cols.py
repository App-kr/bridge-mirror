"""6014 2-column PDF의 block 좌표 분석."""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))

import fitz

p = HERE / "testdata" / "ref_6014.pdf"
doc = fitz.open(str(p))

for pgi, page in enumerate(doc):
    print(f"\n=== Page {pgi + 1} (width={page.rect.width:.0f}) ===")
    page_mid = page.rect.width / 2
    left_thr = page_mid * 0.85
    right_thr = page_mid * 1.15
    print(f"left<{left_thr:.0f}  full={left_thr:.0f}~{right_thr:.0f}  right>{right_thr:.0f}\n")

    blocks = page.get_text("blocks")
    for b in blocks:
        if b[6] != 0 or not b[4].strip():
            continue
        cx = (b[0] + b[2]) / 2
        zone = "LEFT " if cx < left_thr else ("RIGHT" if cx > right_thr else "FULL ")
        txt = b[4].strip().replace("\n", " | ")[:80]
        print(f"  y={b[1]:6.1f}  x={b[0]:6.1f}~{b[2]:6.1f}  cx={cx:6.1f} [{zone}]  {txt!r}")

doc.close()
