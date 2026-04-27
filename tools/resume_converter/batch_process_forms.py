"""
batch_process_forms.py — G폼 inbox 파일 배치 변환기
=======================================================
inbox/에 있는 새 지원자 파일을 지원자별로 그룹화 → PII 제거 → PDF 빌드 → output/

사용:
  "Q:/Phtyon 3/python.exe" -X utf8 batch_process_forms.py [--dry]

--dry: 파일 목록만 출력, 실제 변환 없음
"""

from __future__ import annotations

import re
import sys
import shutil
import logging
from pathlib import Path
from datetime import datetime

# ── 경로 설정 ─────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
INBOX_DIR  = BASE_DIR / "inbox"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR   = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "batch_forms.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("batch")

DRY = "--dry" in sys.argv

# ── 파일 타입 판별 ─────────────────────────────────────────────────────────
def classify_ftype(name: str) -> str:
    n = name.lower()
    if re.search(r"(cover|coverletter|cover_letter)", n):
        return "cover"
    if re.search(r"(recommend|reference|ref_letter)", n):
        return "rec"
    if re.search(r"(resume|cv |cv_|curriculum|_cv\b)", n):
        return "resume"
    if re.search(r"(passport|document|scan|adobe)", n):
        return "doc"
    if re.search(r"(certif|degree|university|diploma)", n):
        return "cert"
    if re.search(r"(self.intro|video|link)", n):
        return "link"
    # 기본: resume
    return "resume"


# ── 지원자 그룹화 ──────────────────────────────────────────────────────────
NAME_RE = re.compile(r'.* - (.+?)\.(pdf|docx|doc)$', re.IGNORECASE)
DRIVE_SUFFIX_RE = re.compile(r'_[A-Za-z0-9]{6,10}$')  # _1VW9B0dW 같은 Drive 중복 suffix

def normalize_name(name: str) -> str:
    """Drive 중복 파일 suffix 제거: 'Bomikazi Nkolongwane_1VW9B0dW' → 'Bomikazi Nkolongwane'"""
    return DRIVE_SUFFIX_RE.sub('', name).strip()

def group_inbox_files() -> dict[str, list[Path]]:
    """inbox/ 파일을 지원자별로 그룹화. 이미 변환된 파일(숫자 이름) 제외."""
    files = [f for f in INBOX_DIR.iterdir()
             if f.is_file() and not f.name.endswith('.meta.json')]

    groups: dict[str, list[Path]] = {}
    already_converted = []

    for f in files:
        # 이미 변환된 파일 (숫자로 시작하는 한국어 이름 패턴)
        if re.match(r'^\d{4,5}[가-힣]', f.name) or re.match(r'^\d{4,5}_[가-힣]', f.name):
            already_converted.append(f)
            continue

        m = NAME_RE.search(f.name)
        if not m:
            continue

        raw_name = m.group(1).strip()
        name = normalize_name(raw_name)
        groups.setdefault(name, []).append(f)

    return groups, already_converted


# ── 이미 변환된 파일 → output/ 이동 ───────────────────────────────────────
def move_converted_files(converted: list[Path]):
    """숫자 이름 파일을 output/ 으로 이동 (이미 처리됨)."""
    moved = 0
    for f in converted:
        dest = OUTPUT_DIR / f.name
        if not dest.exists():
            if not DRY:
                shutil.move(str(f), str(dest))
            log.info(f"[이동] {f.name} → output/")
            moved += 1
        else:
            if not DRY:
                f.unlink()  # 중복 → 삭제
            log.info(f"[중복제거] {f.name}")
    return moved


# ── 메타 추출 (국적/성별/생년) ──────────────────────────────────────────────
NAT_PATTERNS = {
    "south african": "남아공", "south africa": "남아공",
    "american": "미국", "usa": "미국", "u.s.a": "미국", "u.s.": "미국",
    "british": "영국", "uk": "영국", "united kingdom": "영국",
    "canadian": "캐나다", "canada": "캐나다",
    "australian": "호주", "australia": "호주",
    "irish": "아일랜드", "ireland": "아일랜드",
    "zimbabwean": "짐바브웨", "zimbabwe": "짐바브웨",
    "kenyan": "케냐", "kenya": "케냐",
    "nigerian": "나이지리아", "nigeria": "나이지리아",
    "german": "독일", "germany": "독일",
    "filipino": "필리핀", "philippines": "필리핀",
    "korean american": "미교포", "korean-american": "미교포",
}

def extract_meta(text: str) -> tuple[str, str, str]:
    """텍스트에서 국적/성별/생년 추출. 실패시 ('미상','미상','00') 반환."""
    t = text.lower()

    # 국적
    nationality = "미상"
    for key, val in NAT_PATTERNS.items():
        if key in t:
            nationality = val
            break

    # 성별
    gender = "미상"
    if re.search(r"\b(she/her|her/she)\b", t):
        gender = "여성"
    elif re.search(r"\b(he/him|him/he)\b", t):
        gender = "남성"
    elif re.search(r"\bgender\s*:\s*female\b|\bsex\s*:\s*female\b", t):
        gender = "여성"
    elif re.search(r"\bgender\s*:\s*male\b|\bsex\s*:\s*male\b", t):
        gender = "남성"

    # 생년 (DOB or year 4자리)
    birth_year = "00"
    dob_m = re.search(
        r"(?:dob|date\s+of\s+birth|born)[:\s]+.*?(\d{4})", t
    )
    if dob_m:
        birth_year = dob_m.group(1)[-2:]
    else:
        # 첫 번째 출현하는 1980~2009 범위 연도
        years = re.findall(r"\b((?:19[8-9]\d|200\d))\b", text)
        if years:
            birth_year = years[0][-2:]

    return nationality, gender, birth_year


# ── 텍스트 추출 ────────────────────────────────────────────────────────────
def extract_text(path: Path) -> str:
    """PDF 또는 DOCX에서 텍스트 추출."""
    try:
        if path.suffix.lower() == ".pdf":
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                return "\n".join(
                    (p.extract_text() or "") for p in pdf.pages
                )
        elif path.suffix.lower() in (".docx", ".doc"):
            try:
                import docx
                doc = docx.Document(str(path))
                return "\n".join(para.text for para in doc.paragraphs)
            except Exception:
                return ""
    except Exception as e:
        log.warning(f"텍스트 추출 실패 {path.name}: {e}")
        return ""


# ── 다음 강사 번호 계산 ────────────────────────────────────────────────────
def get_next_id() -> int:
    """output/의 기존 파일에서 최댓값 + 1. 4-5자리 강사번호만 대상."""
    nums = []
    for folder in (OUTPUT_DIR, INBOX_DIR):
        for f in folder.iterdir():
            m = re.match(r'^(\d{4,5})', f.name)
            if m:
                n = int(m.group(1))
                if 1000 <= n <= 99999:  # 유효 강사번호 범위
                    nums.append(n)
    return max(nums, default=6165) + 1


# ── 메인 배치 처리 ─────────────────────────────────────────────────────────
def process_group(name: str, files: list[Path], candidate_id: str) -> bool:
    """한 지원자 그룹 처리 → output/ 저장. 성공시 True."""
    try:
        from .pii_engine import analyze_pii
        from .pdf_builder import build_pdf, build_filename
    except ImportError:
        # 직접 실행 시
        sys.path.insert(0, str(BASE_DIR.parent.parent))
        from tools.resume_converter.pii_engine import analyze_pii
        from tools.resume_converter.pdf_builder import build_pdf, build_filename

    log.info(f"\n{'='*60}")
    log.info(f"[{candidate_id}] {name} ({len(files)}개 파일)")

    # 파일 분류
    by_type: dict[str, Path] = {}
    for f in files:
        ft = classify_ftype(f.name)
        # resume/cover 중 이미 있으면 더 좋은 것 유지 (PDF 우선)
        if ft in ("resume", "cover"):
            existing = by_type.get(ft)
            if existing is None:
                by_type[ft] = f
            elif f.suffix.lower() == ".pdf" and existing.suffix.lower() != ".pdf":
                by_type[ft] = f  # PDF 우선
        else:
            by_type.setdefault(ft, f)

    log.info(f"  분류: {dict((k, v.name) for k, v in by_type.items())}")

    # 텍스트 추출
    resume_path = by_type.get("resume")
    cover_path  = by_type.get("cover")

    resume_text = extract_text(resume_path) if resume_path else ""
    cover_text  = extract_text(cover_path) if cover_path else ""

    if not resume_text and not cover_text:
        log.warning(f"  [SKIP] 텍스트 없음")
        return False

    # 메타 추출 (resume 우선, 없으면 cover)
    combined = (resume_text + "\n" + cover_text).strip()
    nationality, gender, birth_year = extract_meta(combined)
    log.info(f"  메타: 국적={nationality} 성별={gender} 생년={birth_year}")

    if DRY:
        log.info(f"  [DRY] 변환 건너뜀")
        return True

    # PII 제거
    known_names = [name]
    resume_pii = analyze_pii(resume_text, known_names=known_names) if resume_text.strip() else None
    cover_pii  = analyze_pii(cover_text,  known_names=known_names) if cover_text.strip() else None

    if resume_pii:
        log.info(f"  Resume PII 제거: {len(resume_pii.pii_found)}개")
    if cover_pii:
        log.info(f"  Cover PII 제거: {len(cover_pii.pii_found)}개")

    # PDF 빌드
    try:
        out_path, size = build_pdf(
            candidate_id  = candidate_id,
            nationality   = nationality,
            gender        = gender,
            birth_year    = birth_year,
            cover_text    = cover_pii.cleaned_text if cover_pii else None,
            resume_text   = resume_pii.cleaned_text if resume_pii else None,
            cover_pdf_path  = cover_path  if cover_path  and cover_path.suffix.lower()  == ".pdf" else None,
            resume_pdf_path = resume_path if resume_path and resume_path.suffix.lower() == ".pdf" else None,
            cover_pii_strings  = [m.original_value for m in cover_pii.pii_found]  if cover_pii  else None,
            resume_pii_strings = [m.original_value for m in resume_pii.pii_found] if resume_pii else None,
            candidate_name = name,
            out_dir        = OUTPUT_DIR,
        )
        log.info(f"  [OK] {out_path.name} ({size//1024}KB)")
        return True
    except Exception as e:
        log.error(f"  [ERR] PDF 빌드 실패: {e}", exc_info=True)
        return False


def main():
    log.info(f"\n{'#'*60}")
    log.info(f"BRIDGE Forms 배치 변환 시작: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info(f"모드: {'DRY RUN' if DRY else '실제 변환'}")

    groups, already_converted = group_inbox_files()

    # 이미 변환된 파일 → output/ 이동
    moved = move_converted_files(already_converted)
    log.info(f"\n이미변환 파일: {moved}개 output/ 이동")

    log.info(f"\n신규 지원자: {len(groups)}명")

    next_id = get_next_id()
    ok_count = err_count = skip_count = 0

    for name, files in sorted(groups.items()):
        cid = str(next_id)
        result = process_group(name, files, cid)
        if result:
            ok_count += 1
            next_id += 1
        elif result is False:
            # None이면 skip, False면 error
            err_count += 1
        else:
            skip_count += 1

    log.info(f"\n{'='*60}")
    log.info(f"완료: 성공={ok_count}, 오류={err_count}, 건너뜀={skip_count}")
    log.info(f"output/ 폴더: {len(list(OUTPUT_DIR.iterdir()))}개 파일")


if __name__ == "__main__":
    main()
