"""
v3.0 전체 파이프라인 — Michelle Sibanda PDF 생성
바탕화면에 6147_v3_TEST.pdf 저장 후 자동 오픈
"""
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent.parent))

from tools.resume_converter.pipeline import Pipeline

DESKTOP = Path(r"C:/Users/Scarlett/Desktop")
# 바탕화면 원본이 없으면 이전 inbox 복사본 재사용
SRC_DIR = HERE / "testdata" / "inbox_6147_20260422_195759"
CV = DESKTOP / "변환전 (2).pdf"
CL = DESKTOP / "변환전 (1).pdf"
if not CV.exists():
    CV = SRC_DIR / "6147_resume.pdf"
    CL = SRC_DIR / "6147_cover.pdf"
    print(f"[FALLBACK] 원본 파일 없음 → inbox 복사본 사용")

CAND_ID = "6147"
META = {
    "name": "Michelle Sinikiwe Sibanda",
    "nationality": "South Africa",
    "gender": "F",
    "birth_year": "1997",
}

# inbox 형식 폴더 구성
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
work = HERE / "testdata" / f"inbox_{CAND_ID}_{ts}"
work.mkdir(parents=True, exist_ok=True)

shutil.copy(CV, work / f"{CAND_ID}_resume.pdf")
shutil.copy(CL, work / f"{CAND_ID}_cover.pdf")
print(f"[SETUP] 작업 폴더: {work}")

pipe = Pipeline(auto_mode=True, on_progress=lambda m: print(f"  {m}"))
job = pipe.run(candidate_id=CAND_ID, folder=work, candidate_meta=META)

print("\n" + "=" * 70)
print(f"결과:")
print(f"  output_path = {job.output_path}")
print(f"  output_size = {getattr(job, 'output_size', 0)} bytes")
print(f"  errors      = {job.errors}")
print(f"  pii_found   = {len(getattr(job, 'pii_found', []))}건")
print("=" * 70)

if job.output_path and Path(job.output_path).exists():
    dst = DESKTOP / f"6147_v3_TEST_{ts}.pdf"
    shutil.copy(job.output_path, dst)
    print(f"\n[SAVE] {dst}")
    print(f"[SIZE] {dst.stat().st_size // 1024} KB")
    # Windows 기본 뷰어로 열기
    os.startfile(str(dst))
    print(f"[OPEN] 파일 뷰어로 열림")
else:
    print("\n❌ 변환 실패 — output_path 없음")
