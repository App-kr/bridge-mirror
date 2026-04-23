"""Kaesha-Leigh Martin (6059 남아공 여성 1996) 샘플 — /apply 흐름 재현.

원본: KLM nESL Resume / Dear Hiring Manager (Desktop, 실제 제출본)
참조: 6059남아공_여성(96born).pdf (사용자 편집본)
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))

from tools.resume_converter.pipeline import Pipeline  # noqa: E402

DESK = Path(r"C:/Users/Scarlett/Desktop")
RESUME = DESK / "KLM  nESL Resume - Kaesha-Leigh Martin.pdf"
COVER = DESK / "Dear Hiring Manager - Kaesha-Leigh Martin.pdf"

assert RESUME.exists(), f"CV 없음: {RESUME}"

CID = "6059"
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
inbox = HERE / "testdata" / f"inbox_{CID}_{stamp}"
inbox.mkdir(parents=True, exist_ok=True)

shutil.copy2(RESUME, inbox / f"{CID}_resume.pdf")
if COVER.exists():
    shutil.copy2(COVER, inbox / f"{CID}_cover.pdf")
    print(f"[TEST] 커버레터 첨부: {COVER.name}")

print(f"[TEST] inbox: {inbox}")
print(f"[TEST] files: {[p.name for p in inbox.iterdir()]}")

pl = Pipeline(auto_mode=True, on_progress=lambda m: print(m))
job = pl.run(
    candidate_id=CID,
    folder=inbox,
    candidate_meta={
        "name": "Kaesha-Leigh Martin",
        "nationality": "South Africa",
        "gender": "F",
        "birth_year": "1996",
    },
)

print("\n=== RESULT ===")
print(f"output_path: {job.output_path}")
if job.output_path and job.output_path.exists():
    print(f"output_size: {job.output_path.stat().st_size//1024}KB")
print(f"errors  ({len(job.errors)}): {job.errors}")
print(f"warnings({len(job.warnings)}): {job.warnings}")

if job.output_path and job.output_path.exists():
    out = DESK / f"{CID}_Kaesha_TEST_{stamp}.pdf"
    shutil.copy2(job.output_path, out)
    print(f"\n[TEST] 복사됨: {out}")
