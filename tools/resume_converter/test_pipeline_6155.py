"""
test_pipeline_6155.py — 6155 샘플 변환 테스트
샘플커버.pdf + 샘플이력서.pdf → 6155미국_여성(93born).pdf
"""
import sys, os, logging, time
from pathlib import Path

# 경로 설정
BASE    = Path(__file__).parent
PARENT  = BASE.parent
DESKTOP = Path("C:/Users/Scarlett/Desktop")

sys.path.insert(0, str(PARENT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE / "logs" / "test_6155.log", encoding="utf-8"),
    ]
)
log = logging.getLogger("test_6155")

# ─────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("BRIDGE Resume Converter — 파이프라인 테스트 (6155)")
print("="*60)

# 1. 의존성 확인
print("\n[1/6] 의존성 확인")
try:
    import fitz        # PyMuPDF
    import pdfplumber
    from reportlab.lib.pagesizes import A4
    from PIL import Image
    print("  ✓ PyMuPDF / pdfplumber / reportlab / Pillow OK")
except ImportError as e:
    print(f"  ✗ 의존성 누락: {e}")
    sys.exit(1)

# 2. 샘플 파일 확인
print("\n[2/6] 샘플 파일 확인")
cover_src  = DESKTOP / "샘플커버.pdf"
resume_src = DESKTOP / "샘플이력서.pdf"
result_ref = DESKTOP / "샘플결과 6155미국_여성(93born).pdf"

for p, label in [(cover_src, "커버레터"), (resume_src, "이력서"), (result_ref, "기준결과")]:
    if p.exists():
        size_kb = p.stat().st_size // 1024
        print(f"  ✓ {label}: {p.name} ({size_kb}KB)")
    else:
        print(f"  ✗ {label} 없음: {p}")
        sys.exit(1)

# 3. 텍스트 추출
print("\n[3/6] 텍스트 추출 (PyMuPDF 우선)")

from resume_converter.pdf_builder import extract_text_from_pdf

cover_raw  = extract_text_from_pdf(cover_src)
resume_raw = extract_text_from_pdf(resume_src)

print(f"  커버레터: {len(cover_raw)} chars, {cover_raw.count(chr(10))} lines")
print(f"  이력서:   {len(resume_raw)} chars, {resume_raw.count(chr(10))} lines")

# 텍스트 미리보기 (앞 200자)
print(f"\n  [커버레터 첫 200자]")
print("  " + cover_raw[:200].replace("\n", "\n  "))
print(f"\n  [이력서 첫 200자]")
print("  " + resume_raw[:200].replace("\n", "\n  "))

# 4. PII 분석
print("\n[4/6] PII 탐지 + 제거")
from resume_converter.pii_engine import analyze_pii

# API 키 없이 실행 (Layer 1 regex only)
cover_result  = analyze_pii(cover_raw,  api_key=None)
resume_result = analyze_pii(resume_raw, api_key=None)

print(f"\n  커버레터 PII:")
print(f"    탐지됨: {len(cover_result.pii_found)}개 제거, {len(cover_result.uncertain)}개 불확실")
for m in cover_result.pii_found:
    print(f"    [{m.type}] '{m.original_value[:50]}' (신뢰도: {m.confidence:.0%})")

print(f"\n  이력서 PII:")
print(f"    탐지됨: {len(resume_result.pii_found)}개 제거, {len(resume_result.uncertain)}개 불확실")
for m in resume_result.pii_found:
    print(f"    [{m.type}] '{m.original_value[:50]}' (신뢰도: {m.confidence:.0%})")

# 5. 체크리스트 검증
print("\n[5/6] 체크리스트 검증")

all_original_text = cover_raw + "\n" + resume_raw
all_cleaned_text  = cover_result.cleaned_text + "\n" + resume_result.cleaned_text

import re

def check(label, condition, detail=""):
    mark = "✓" if condition else "✗"
    msg = f"  {mark} {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return condition

results = []

# 전화번호 제거
phone_remaining = re.findall(r"010[-.\s]?\d{3,4}[-.\s]?\d{4}|\+\d{1,3}[-.\s]\(?\d", all_cleaned_text)
results.append(check("전화번호 삭제", len(phone_remaining) == 0,
    f"남은 것: {phone_remaining[:3]}" if phone_remaining else "없음"))

# 이메일 제거
email_remaining = re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", all_cleaned_text)
results.append(check("이메일 삭제", len(email_remaining) == 0,
    f"남은 것: {email_remaining[:3]}" if email_remaining else "없음"))

# 한국 주소 제거 (간단 체크)
kr_addr = re.findall(r"(?:서울|부산|대구|인천|광주|대전|울산)[가-힣\s\d,.-]{2,30}(?:시|구|동|로|길)", all_cleaned_text)
results.append(check("한국 주소 삭제", len(kr_addr) == 0,
    f"남은 것: {kr_addr[:2]}" if kr_addr else "없음"))

# 카카오/SNS
kakao = re.findall(r"(?:카카오|kakao|카톡)", all_cleaned_text, re.IGNORECASE)
results.append(check("카카오/SNS 삭제", len(kakao) == 0,
    f"남은 것: {kakao[:2]}" if kakao else "없음"))

# Reference 섹션 제거 (원본에 있었는지 확인)
ref_in_original = bool(re.search(r"\bREFERENCE[S]?\b", all_original_text, re.IGNORECASE))
ref_in_cleaned  = bool(re.search(r"\bREFERENCE[S]?\b", all_cleaned_text, re.IGNORECASE))
if ref_in_original:
    results.append(check("Reference 섹션 삭제", not ref_in_cleaned,
        "원본에 있었음" + (" → 삭제됨" if not ref_in_cleaned else " → 남아있음!")))
else:
    check("Reference 섹션", True, "원본에 없음 — 확인 불필요")

# 6. PDF 빌드
print("\n[6/6] PDF 조립")
from resume_converter.pdf_builder import build_pdf, build_filename

out_dir = BASE / "output"
out_dir.mkdir(exist_ok=True)

t0 = time.time()
out_path, size = build_pdf(
    candidate_id = "6155",
    nationality  = "usa",
    gender       = "female",
    birth_year   = "1993",
    photo_bytes  = None,       # 사진 없음 (별도 jpg 없을 경우)
    cover_text   = cover_result.cleaned_text,
    resume_text  = resume_result.cleaned_text,
    rec_text     = None,
    out_dir      = out_dir,
)
elapsed = time.time() - t0

print(f"  출력: {out_path.name}")
print(f"  크기: {size//1024}KB ({size:,} bytes)")
print(f"  시간: {elapsed:.1f}초")
results.append(check("파일명 형식", out_path.name.startswith("6155"), out_path.name))
results.append(check("300KB 이하", size < 300*1024, f"{size//1024}KB"))

# 기준 결과 비교
ref_size = result_ref.stat().st_size
print(f"\n  기준 결과 크기: {ref_size//1024}KB")
print(f"  생성 결과 크기: {size//1024}KB")
size_diff_pct = abs(size - ref_size) / ref_size * 100
print(f"  크기 차이: {size_diff_pct:.0f}%")

# 최종 결과
print("\n" + "="*60)
passed = sum(results)
total  = len(results)
print(f"최종 결과: {passed}/{total} 통과")
if passed == total:
    print("✅ 모든 체크 통과")
else:
    print("⚠️  일부 체크 실패 — 위 로그 확인")
print(f"출력 파일: {out_path}")
print("="*60 + "\n")
