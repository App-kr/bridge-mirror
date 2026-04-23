"""이력서 PDF 내장 이미지 탐색 디버그."""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))

import fitz
from tools.resume_converter.face_crop import crop_face_from_bytes, FaceNotFoundError

# 사용할 후보 PDF 목록
CANDIDATES = [
    Path(r"C:/Users/Scarlett/Desktop/변환전 (2).pdf"),
    HERE / "testdata" / "inbox_6147_20260422_195759" / "6147_resume.pdf",
    HERE / "testdata" / "inbox_6147_20260422_203101" / "6147_resume.pdf",
]

for cand in CANDIDATES:
    if not cand.exists():
        print(f"[SKIP] {cand} 없음")
        continue
    print(f"\n=== {cand.name} ({cand.stat().st_size//1024}KB) ===")
    doc = fitz.open(str(cand))
    print(f"  페이지 수: {len(doc)}")
    total_imgs = 0
    for pgi in range(len(doc)):
        page = doc[pgi]
        imgs = page.get_images(full=True)
        total_imgs += len(imgs)
        for j, info in enumerate(imgs):
            xref = info[0]
            try:
                bi = doc.extract_image(xref)
                w = bi.get("width", 0)
                h = bi.get("height", 0)
                ext = bi.get("ext", "?")
                size = len(bi.get("image", b""))
                filt_reason = ""
                if w < 60 or h < 60:
                    filt_reason = "너무작음"
                elif w > 1200 or h > 1200:
                    filt_reason = "너무큼"
                elif w > h * 1.5:
                    filt_reason = "가로형"
                face_ok = ""
                if not filt_reason:
                    try:
                        crop_face_from_bytes(bi["image"])
                        face_ok = "FACE_OK"
                    except FaceNotFoundError:
                        face_ok = "얼굴없음"
                    except Exception as e:
                        face_ok = f"ERR:{type(e).__name__}"
                print(f"    [p{pgi+1}#{j}] xref={xref} {w}x{h} {ext} {size//1024}KB {filt_reason or face_ok}")
            except Exception as e:
                print(f"    [p{pgi+1}#{j}] xref={xref} EXTRACT_ERR {e}")
    print(f"  총 이미지 {total_imgs}개")
    doc.close()
