"""Lorena 샘플 — 실제 /apply 흐름 재현 테스트.

시나리오:
  1) inbox 폴더 생성 (candidate_id=9999)
  2) Cover PDF + CV PDF 복사
  3) candidate_meta 주입 (name=Lorena, 나머지는 웹 제출 시 DB에서 옴)
  4) Pipeline 실행 → 얼굴은 CV 내장에서 자동 추출
  5) 결과 PDF 경로 출력
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))

from tools.resume_converter.pipeline import Pipeline  # noqa: E402

DESK = Path(r"C:/Users/Scarlett/Desktop")
COVER = DESK / "Cover letter 2026.docx - Lorena.pdf"
RESUME = DESK / "Lorena CV 2026 PDF - Lorena.pdf"

assert COVER.exists(), f"Cover 없음: {COVER}"
assert RESUME.exists(), f"CV 없음: {RESUME}"

CID = "9999"
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
inbox = HERE / "testdata" / f"inbox_{CID}_{stamp}"
inbox.mkdir(parents=True, exist_ok=True)

# file_classifier가 이름으로 판단하도록 파일명 맞추기
shutil.copy2(COVER, inbox / f"{CID}_cover.pdf")
shutil.copy2(RESUME, inbox / f"{CID}_resume.pdf")

print(f"[TEST] inbox: {inbox}")
print(f"[TEST] files: {[p.name for p in inbox.iterdir()]}")

pl = Pipeline(auto_mode=True, on_progress=lambda m: print(m))
job = pl.run(
    candidate_id=CID,
    folder=inbox,
    candidate_meta={
        "name": "Lorena",
        "nationality": "USA",
        "gender": "F",
        "birth_year": "1995",
    },
)

print("\n=== RESULT ===")
print(f"output_path: {job.output_path}")
print(f"output_size: {job.output_size//1024}KB")
print(f"errors  ({len(job.errors)}): {job.errors}")
print(f"warnings({len(job.warnings)}): {job.warnings}")

if job.output_path and job.output_path.exists():
    # 바탕화면에 확인용 복사
    out = DESK / f"9999_Lorena_TEST_{stamp}.pdf"
    shutil.copy2(job.output_path, out)
    print(f"\n[TEST] 복사됨: {out}")
