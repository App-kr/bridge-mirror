"""출력 PDF 페이지 3 폰트·크기 분석 — 제목/소제목 볼드 확인."""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))

import fitz

DESKTOP = Path(r"C:/Users/Scarlett/Desktop")
_cands = sorted(DESKTOP.glob("6147_v3_TEST_*.pdf"), reverse=True)
OUT = _cands[0]
print(f"[ANALYZE] {OUT.name}")
doc = fitz.open(str(OUT))

for pgi in range(min(4, len(doc))):
    page = doc[pgi]
    print(f"\n=== Page {pgi+1} ===")
    d = page.get_text("dict")
    for blk in d["blocks"]:
        if blk.get("type") != 0:
            continue
        for ln in blk.get("lines", []):
            for sp in ln.get("spans", []):
                txt = sp.get("text", "").strip()
                if not txt:
                    continue
                font = sp.get("font", "")
                size = sp.get("size", 0)
                bold = "Bold" in font or "bold" in font.lower()
                mark = "**B**" if bold else "     "
                print(f"  {mark} {size:4.1f}pt  {font:20s}  {txt[:70]!r}")

# marker 검색
print("\n=== MARKER 검색 ===")
full_text = ""
for page in doc:
    full_text += page.get_text()
for m in ["__BRIDGE_COL_START__", "__BRIDGE_COL_BREAK__", "__BRIDGE_COL_END__"]:
    cnt = full_text.count(m)
    print(f"  {m}: {cnt}개")

doc.close()
