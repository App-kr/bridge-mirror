"""
batch_process_forms.py — G폼 inbox 배치 변환기 v2.0
====================================================
test_pipeline_6155.py 방식 준수:
  extract_text_from_pdf (PyMuPDF) → analyze_pii → build_pdf (텍스트 기반)

사용:
  "Q:/Phtyon 3/python.exe" -X utf8 batch_process_forms.py [--dry]
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

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

# ── 이름 추출 패턴 (그리디 → 마지막 ' - Name.ext') ────────────────────
NAME_RE        = re.compile(r'.* - (.+?)\.(pdf|docx|doc)$', re.IGNORECASE)
DRIVE_SUFFIX   = re.compile(r'_[A-Za-z0-9]{6,10}$')

# ── 파일 타입 판별 ──────────────────────────────────────────────────────
def _ftype(name: str) -> str:
    n = name.lower()
    if re.search(r"(cover|coverletter|cover_letter|cover letter)", n): return "cover"
    if re.search(r"(recommend|reference|ref_letter)",              n): return "rec"
    if re.search(r"(resume|cv |cv_|\bcv\b|curriculum|teacher.*cv|teaching.*cv)", n): return "resume"
    if re.search(r"(passport|document|scan|adobe)",                n): return "doc"
    if re.search(r"(certif|degree|university|diploma|substitute)", n): return "cert"
    if re.search(r"(self.intro|video|link)",                       n): return "link"
    return "resume"  # 기본


# ── 메타 정보: 국적/성별/생년 추출 ─────────────────────────────────────
_NAT_MAP = {
    "south african": "남아공",  "south africa": "남아공",
    "american":      "미국",    "usa":           "미국",  "u.s.a": "미국",
    "british":       "영국",    "uk":            "영국",  "united kingdom": "영국",
    "canadian":      "캐나다",  "canada":        "캐나다",
    "australian":    "호주",    "australia":     "호주",
    "irish":         "아일랜드","ireland":        "아일랜드",
    "zimbabwean":    "짐바브웨","zimbabwe":       "짐바브웨",
    "kenyan":        "케냐",    "kenya":          "케냐",
    "nigerian":      "나이지리아",
    "german":        "독일",    "germany":        "독일",
    "filipino":      "필리핀",  "philippines":    "필리핀",
    "korean american":"미교포", "korean-american":"미교포",
    "new zealander":  "뉴질랜드","new zealand":   "뉴질랜드",
    "jamaican":       "자메이카",
    "ghanaian":       "가나",
    "philippine":     "필리핀",
}
_GENDER_HINTS = {
    "female": "여성", "she/her": "여성", "her/she": "여성",
    "male":   "남성", "he/him":  "남성", "him/he":  "남성",
    "gender: female": "여성", "sex: female": "여성",
    "gender: male":   "남성", "sex: male":   "남성",
}

def _extract_meta(text: str) -> tuple[str, str, str]:
    t = text.lower()
    # 국적
    nat = "미상"
    for key, val in _NAT_MAP.items():
        if key in t:
            nat = val
            break
    # 성별
    gen = "미상"
    for key, val in _GENDER_HINTS.items():
        if key in t:
            gen = val
            break
    # 생년 (DOB 우선)
    yr = "00"
    dob_m = re.search(r"(?:dob|date\s+of\s+birth|born)[:\s]+.*?(\d{4})", t)
    if dob_m:
        yr = dob_m.group(1)[-2:]
    else:
        ys = re.findall(r"\b((?:19[6-9]\d|200\d))\b", text)
        if ys:
            yr = ys[0][-2:]
    return nat, gen, yr


# ── 이미 변환된 파일 → output/ 이동 ────────────────────────────────────
def _move_converted() -> int:
    moved = 0
    for f in INBOX_DIR.iterdir():
        if not f.is_file():
            continue
        if not re.match(r'^\d{4,5}[가-힣_]', f.name):
            continue
        if f.name.endswith('.meta.json'):
            continue
        dest = OUTPUT_DIR / f.name
        if not dest.exists():
            if not DRY:
                shutil.move(str(f), str(dest))
            log.info(f"[이동] {f.name} → output/")
            moved += 1
        else:
            if not DRY:
                f.unlink()
            log.info(f"[중복] {f.name}")
    return moved


# ── 접수순 지원자 목록 (meta.json created_time 기준) ───────────────────
def _collect_applicants() -> list[dict]:
    """
    inbox/*.meta.json 에서 신규 지원자 파일 수집 → 접수순 정렬.
    Returns list of {name, files: {ftype→Path}, submitted_at}
    """
    # step1: meta.json → {raw_name → (earliest_time, [orig_name, ...])}
    name_times: dict[str, list] = {}
    for meta_path in INBOX_DIR.glob("*.meta.json"):
        try:
            data  = json.loads(meta_path.read_text(encoding="utf-8"))
            orig  = data.get("original_name", "")
            ct    = data.get("created_time", "9999")
        except Exception:
            continue
        if re.match(r'^\d{4,5}[가-힣_]', orig):
            continue  # 이미 변환된 파일
        nm = NAME_RE.search(orig)
        if not nm:
            continue
        raw = DRIVE_SUFFIX.sub('', nm.group(1)).strip()
        if raw not in name_times or ct < name_times[raw][0]:
            name_times[raw] = [ct]
        name_times[raw].append(orig)

    # step2: 실제 inbox 파일 경로 연결
    applicants = []
    for name, info in name_times.items():
        submitted_at = info[0]
        files_by_type: dict[str, Path] = {}
        for f in INBOX_DIR.iterdir():
            if not f.is_file() or f.name.endswith('.meta.json'):
                continue
            nm = NAME_RE.search(f.name)
            if not nm:
                continue
            raw = DRIVE_SUFFIX.sub('', nm.group(1)).strip()
            if raw != name:
                continue
            ft = _ftype(f.name)
            # 같은 타입 → PDF 우선, 그 다음 더 큰 파일
            if ft in files_by_type:
                existing = files_by_type[ft]
                if f.suffix.lower() == ".pdf" and existing.suffix.lower() != ".pdf":
                    files_by_type[ft] = f
                elif f.suffix.lower() == existing.suffix.lower() and f.stat().st_size > existing.stat().st_size:
                    files_by_type[ft] = f
            else:
                files_by_type[ft] = f

        if files_by_type:
            applicants.append({
                "name":         name,
                "files":        files_by_type,
                "submitted_at": submitted_at,
            })

    # 접수순 정렬
    applicants.sort(key=lambda x: x["submitted_at"])
    return applicants


# ── 단일 지원자 변환 ───────────────────────────────────────────────────
def _process_one(app: dict, candidate_id: str) -> bool:
    name        = app["name"]
    files       = app["files"]
    submitted   = app["submitted_at"][:10]

    log.info(f"\n{'='*60}")
    log.info(f"[{candidate_id}] {name} (접수: {submitted})")
    log.info(f"  파일: { {k: v.name for k, v in files.items()} }")

    # 텍스트 추출 (PyMuPDF 우선 — test_pipeline_6155 방식)
    try:
        sys.path.insert(0, str(BASE_DIR.parent.parent))
        from tools.resume_converter.pdf_builder import extract_text_from_pdf, build_pdf
        from tools.resume_converter.pii_engine  import analyze_pii
    except ImportError:
        from pdf_builder import extract_text_from_pdf, build_pdf
        from pii_engine  import analyze_pii

    def _get_text(path: Path) -> str:
        if path.suffix.lower() == ".pdf":
            try:
                return extract_text_from_pdf(path)  # PyMuPDF
            except Exception as e:
                log.warning(f"  PyMuPDF 실패({path.name}): {e}")
        # DOCX fallback
        try:
            import docx as _docx
            d = _docx.Document(str(path))
            return "\n".join(p.text for p in d.paragraphs)
        except Exception as e:
            log.warning(f"  DOCX 추출 실패({path.name}): {e}")
        return ""

    resume_path  = files.get("resume")
    cover_path   = files.get("cover")
    rec_path     = files.get("rec")

    resume_raw   = _get_text(resume_path) if resume_path else ""
    cover_raw    = _get_text(cover_path)  if cover_path  else ""
    rec_raw      = _get_text(rec_path)    if rec_path    else ""

    combined = (resume_raw + "\n" + cover_raw).strip()
    if not combined:
        log.warning(f"  [SKIP] 텍스트 없음 (스캔 이미지만?)")
        return False

    # 메타 추출
    nat, gen, yr = _extract_meta(combined)
    log.info(f"  메타: 국적={nat} 성별={gen} 생년={yr}")

    # PII 분석 — known_names: 성(last)과 전체명 포함 (이름은 남김)
    parts      = name.split()
    last_name  = parts[-1] if len(parts) > 1 else ""
    known      = [name] + ([last_name] if last_name else [])

    resume_pii = analyze_pii(resume_raw, known_names=known) if resume_raw.strip() else None
    cover_pii  = analyze_pii(cover_raw,  known_names=known) if cover_raw.strip()  else None
    rec_pii    = analyze_pii(rec_raw,    known_names=known) if rec_raw.strip()    else None

    if resume_pii: log.info(f"  Resume PII: {len(resume_pii.pii_found)}건 제거")
    if cover_pii:  log.info(f"  Cover  PII: {len(cover_pii.pii_found)}건 제거")
    if rec_pii:    log.info(f"  Rec    PII: {len(rec_pii.pii_found)}건 제거")

    if DRY:
        log.info(f"  [DRY] 변환 건너뜀")
        return True

    # PDF 빌드 — 텍스트 기반 (test_pipeline_6155 동일 방식)
    try:
        out_path, size = build_pdf(
            candidate_id = candidate_id,
            nationality  = nat,
            gender       = gen,
            birth_year   = yr,
            photo_bytes  = None,
            cover_text   = cover_pii.cleaned_text  if cover_pii  else None,
            resume_text  = resume_pii.cleaned_text if resume_pii else None,
            rec_text     = rec_pii.cleaned_text    if rec_pii    else None,
            candidate_name = name,
            out_dir      = OUTPUT_DIR,
        )
        log.info(f"  [OK] {out_path.name} ({size//1024}KB)")
        return True
    except Exception as e:
        log.error(f"  [ERR] {e}", exc_info=True)
        return False


# ── 메인 ───────────────────────────────────────────────────────────────
def main():
    log.info(f"\n{'#'*60}")
    log.info(f"BRIDGE Forms 배치 변환 v2.0: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info(f"모드: {'DRY RUN' if DRY else '실제 변환'}")

    # 이미 변환된 파일 정리
    moved = _move_converted()
    log.info(f"\n이미변환 파일: {moved}개 output/ 이동")

    # 접수순 지원자 목록
    applicants = _collect_applicants()
    log.info(f"\n신규 지원자: {len(applicants)}명 (접수순)")

    # 시작 ID: 현재 output/의 최댓값 + 1
    existing_nums = []
    for f in OUTPUT_DIR.iterdir():
        m = re.match(r'^(\d{4,5})', f.name)
        if m:
            n = int(m.group(1))
            if 1000 <= n <= 9999:
                existing_nums.append(n)
    # inbox meta.json에서도 확인
    for f in INBOX_DIR.glob("*.meta.json"):
        m = re.match(r'^(\d{4,5})', f.name)
        if m:
            n = int(m.group(1))
            if 1000 <= n <= 9999:
                existing_nums.append(n)
    start_id = max(existing_nums, default=6165) + 1
    log.info(f"시작 ID: {start_id}\n")

    ok = err = skip = 0
    for i, app in enumerate(applicants):
        cid    = str(start_id + i)
        result = _process_one(app, cid)
        if result is True:
            ok += 1
        elif result is False:
            err += 1
        else:
            skip += 1

    log.info(f"\n{'='*60}")
    log.info(f"완료: 성공={ok}, 오류={err}, 건너뜀={skip}")
    log.info(f"output/ 총 파일: {len(list(OUTPUT_DIR.iterdir()))}개")
    log.info(f"{'='*60}")


if __name__ == "__main__":
    main()
