"""
test_kaesha_sample.py — Kaesha-Leigh Martin 샘플 변환 테스트 (v3.5 검증)
Desktop의 Kaesha 파일 → inbox/6059_test/ → pipeline 실행 → Desktop으로 결과 복사
"""
import sys, shutil, logging, time
from pathlib import Path

BASE    = Path(__file__).parent
PARENT  = BASE.parent.parent  # bridge base/
DESKTOP = Path("C:/Users/Scarlett/Desktop")

sys.path.insert(0, str(PARENT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

CID = "6059"
CANDIDATE_META = {
    "name": "Kaesha-Leigh Martin",
    "nationality": "South Africa",
    "gender": "female",
    "birth_year": "1996",
}

# 1. Desktop → inbox
SRC_RESUME = DESKTOP / "KLM  nESL Resume - Kaesha-Leigh Martin.pdf"
SRC_COVER  = DESKTOP / "Dear Hiring Manager - Kaesha-Leigh Martin.pdf"

inbox = BASE / "inbox" / f"{CID}_test"
if inbox.exists():
    shutil.rmtree(inbox)
inbox.mkdir(parents=True)

resume_dst = inbox / "resume.pdf"
cover_dst  = inbox / "cover.pdf"
shutil.copy2(str(SRC_RESUME), str(resume_dst))
shutil.copy2(str(SRC_COVER),  str(cover_dst))
print(f"[1] inbox 준비: {inbox}")

# 2. pipeline 실행
print("[2] pipeline.run() 실행")
from tools.resume_converter.pipeline import Pipeline

pl = Pipeline(auto_mode=True)
t0 = time.time()
job = pl.run(CID, inbox, candidate_meta=CANDIDATE_META)
elapsed = time.time() - t0

print(f"\n[3] 결과")
print(f"   output: {job.output_path}")
print(f"   size:   {job.output_size // 1024}KB")
print(f"   time:   {elapsed:.1f}s")
if job.errors:
    print(f"   errors: {job.errors}")
if job.warnings:
    print(f"   warnings: {job.warnings}")

# 4. Desktop으로 결과 복사 (타임스탬프 포함)
if job.output_path and job.output_path.exists():
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_name = f"{CID}_Kaesha_TEST_{ts}.pdf"
    desktop_out = DESKTOP / out_name
    shutil.copy2(str(job.output_path), str(desktop_out))
    print(f"[4] Desktop 복사: {desktop_out.name}")
    print(f"\n✓ 성공")
else:
    print(f"[4] 출력 파일 없음 — 실패")
    sys.exit(1)
