"""Nathan Mullen (6159 아일랜드 남성 2002) 샘플 — /apply 흐름 재현.

원본: Nathan Mullen CV  - Nathan Mullen.pdf (Desktop)
참조: 6159아일랜드_남성(02born).pdf (사용자 편집본, 1페이지)
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))

from tools.resume_converter.pipeline import Pipeline  # noqa: E402

DESK = Path(r"C:/Users/Scarlett/Desktop")
RESUME = DESK / "Nathan Mullen CV  - Nathan Mullen.pdf"
SELFIE = DESK / "nathan_selfie.png"

assert RESUME.exists(), f"CV 없음: {RESUME}"

CID = "9999"
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
inbox = HERE / "testdata" / f"inbox_{CID}_{stamp}"
inbox.mkdir(parents=True, exist_ok=True)

shutil.copy2(RESUME, inbox / f"{CID}_resume.pdf")
if SELFIE.exists():
    shutil.copy2(SELFIE, inbox / f"{CID}_photo.png")
    print(f"[TEST] 셀피 첨부: {SELFIE.name}")
else:
    print(f"[TEST] 셀피 없음 (CV 내장 이미지 탐색 예정)")

print(f"[TEST] inbox: {inbox}")
print(f"[TEST] files: {[p.name for p in inbox.iterdir()]}")

pl = Pipeline(auto_mode=True, on_progress=lambda m: print(m))
job = pl.run(
    candidate_id=CID,
    folder=inbox,
    candidate_meta={
        "name": "Nathan Mullen",
        "nationality": "Ireland",
        "gender": "M",
        "birth_year": "2002",
    },
)

print("\n=== RESULT ===")
print(f"output_path: {job.output_path}")
if job.output_path and job.output_path.exists():
    print(f"output_size: {job.output_path.stat().st_size//1024}KB")
print(f"errors  ({len(job.errors)}): {job.errors}")
print(f"warnings({len(job.warnings)}): {job.warnings}")

if job.output_path and job.output_path.exists():
    out = DESK / f"9999_Nathan_TEST_{stamp}.pdf"
    shutil.copy2(job.output_path, out)
    print(f"\n[TEST] 복사됨: {out}")
