"""
batch_process_forms.py — G폼 inbox 배치 변환기 v3.0
====================================================
test_pipeline_6155.py 방식 준수:
  extract_text_from_pdf (PyMuPDF) → analyze_pii → build_pdf (텍스트 기반)

v3.0 신규:
  - Google Sheet를 1차 메타 소스로 사용 (ID·국적·성별·생년 모두 시트에서 읽기)
  - Sheet D열(강사번호)이 있으면 그 ID를 사용 (자동부여 보조)
  - Sheet F(국적)·H(생년)·I(성별) 컬럼 직접 참조 → PDF 텍스트 파싱 폴백
  - 변환 완료 후 Google Sheet AV열 자동 기록 (sheets_connector.write_intake_row)

사용:
  "Q:/Phtyon 3/python.exe" -X utf8 batch_process_forms.py [--dry] [--no-sheet]
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

DRY      = "--dry"      in sys.argv
NO_SHEET = "--no-sheet" in sys.argv

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


# ── Sheet H열(생년) 정규화 ─────────────────────────────────────────────
def _norm_year(h: str) -> str:
    """
    Sheet H열 값 → 2자리 생년
    예: "2" → "02", "93" → "93", "1993" → "93", "" → "00"
    """
    h = (h or "").strip()
    if not h:
        return "00"
    if len(h) == 1:          # "2" → "02"
        return f"0{h}"
    if len(h) == 2:          # "93" → "93"
        return h
    if len(h) >= 4:          # "1993" → "93"
        return h[-2:]
    return h


# ── 메타 정보: 국적/성별/생년 추출 (PDF 텍스트 폴백용) ─────────────────
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


# ── Sheet 전체 메타 로드 (main()에서 1회) ─────────────────────────────
def _load_sheet_meta() -> list[dict]:
    """
    Google Sheet 'New' 탭에서 강사 메타 데이터 로드.
    반환: [{row_idx, id, name, nationality, birth_year, gender}, ...]
    sheet 열: B=이름, D=강사번호, F=국적, H=생년(나이), I=성별
    """
    if NO_SHEET:
        return []
    try:
        sys.path.insert(0, str(BASE_DIR))
        from sheets_connector import (
            _get_sheets_service_oauth, _get_sheet_id,
            _get_sheet_gid, _get_sheet_tab_name_by_gid
        )
        sid = _get_sheet_id()
        gid = _get_sheet_gid()
        svc = _get_sheets_service_oauth()
        if not svc or not sid:
            log.warning("  [시트] Sheet 접근 불가 — 메타 로드 건너뜀")
            return []

        tab = _get_sheet_tab_name_by_gid(svc, sid, gid)
        res = svc.spreadsheets().values().get(
            spreadsheetId=sid,
            range=f"'{tab}'!A1:I200",
        ).execute()
        raw_rows = res.get("values", [])

        meta = []
        for i, row in enumerate(raw_rows):
            if not row:
                continue
            # 헤더/메모 행 건너뜀 (B열이 이름처럼 보이지 않으면)
            b_val = row[1].strip() if len(row) > 1 else ""
            if not b_val or not re.search(r"[A-Za-z]", b_val):
                continue
            # 데이터 행
            d_val = row[3].strip() if len(row) > 3 else ""
            f_val = row[5].strip() if len(row) > 5 else ""
            h_val = _norm_year(row[7].strip() if len(row) > 7 else "")
            i_val = row[8].strip() if len(row) > 8 else ""

            # D열이 숫자(강사번호)여야만 유효 데이터로 취급
            if not re.match(r"^\d{4,6}$", d_val):
                continue

            meta.append({
                "row_idx":    i + 1,   # 1-indexed
                "id":         d_val,
                "name":       b_val,
                "nationality":f_val,
                "birth_year": h_val,
                "gender":     i_val,
            })

        log.info(f"  [시트] 메타 {len(meta)}행 로드 완료")
        return meta

    except Exception as e:
        log.warning(f"  [시트] 메타 로드 실패: {e}")
        return []


def _find_sheet_entry(sheet_meta: list[dict], name: str) -> dict | None:
    """
    이름 유사도(word overlap ≥ 50%)로 sheet_meta에서 matching row 반환.
    """
    if not sheet_meta or not name:
        return None
    name_parts = set(name.lower().split())
    best_score = 0.0
    best_entry = None
    for entry in sheet_meta:
        sheet_words = set(entry["name"].lower().replace(";", " ").split())
        common = name_parts & sheet_words
        score  = len(common) / max(len(name_parts), 1)
        if score >= 0.5 and score > best_score:
            best_score = score
            best_entry = entry
    if best_entry:
        log.info(f"  [시트매칭] '{name}' → ID={best_entry['id']} (score={best_score:.2f})")
    return best_entry


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
def _process_one(app: dict, fallback_id: str,
                 sheet_hint: dict | None = None) -> bool:
    """
    sheet_hint: _find_sheet_entry() 결과 — {id, nationality, birth_year, gender}
    """
    name        = app["name"]
    files       = app["files"]
    submitted   = app["submitted_at"][:10]

    log.info(f"\n{'='*60}")
    log.info(f"[{name}] (접수: {submitted})")
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

    # ── 이미 처리됐는지 meta.json processed 플래그 확인 ──────────────
    for src_file in files.values():
        meta_path = INBOX_DIR / (src_file.stem.replace("(", "_").replace(")", "_").replace(" ", "_") + ".meta.json")
        # 간단히 같은 디렉토리의 *.meta.json 중 original_name 매칭
        for mp in INBOX_DIR.glob("*.meta.json"):
            try:
                mdata = json.loads(mp.read_text(encoding="utf-8"))
                if mdata.get("original_name", "") == src_file.name and mdata.get("processed"):
                    log.info(f"  [SKIP] 이미 처리됨 (meta: {mp.name})")
                    return True
            except Exception:
                continue

    # ── 메타 결정: 시트 1차, PDF 파싱 폴백 ────────────────────────────
    pdf_nat, pdf_gen, pdf_yr = _extract_meta(combined)

    if sheet_hint:
        candidate_id = sheet_hint.get("id") or fallback_id
        nat = sheet_hint.get("nationality") or pdf_nat
        gen = sheet_hint.get("gender")      or pdf_gen
        yr  = sheet_hint.get("birth_year")  or pdf_yr
        src = "시트"
    else:
        candidate_id = fallback_id
        nat, gen, yr = pdf_nat, pdf_gen, pdf_yr
        src = "PDF파싱"

    log.info(f"  ID: {candidate_id} (소스: {src})")
    log.info(f"  메타: 국적={nat} 성별={gen} 생년={yr}")

    # 이미 output/에 같은 ID 파일이 있으면 건너뜀
    existing = list(OUTPUT_DIR.glob(f"{candidate_id}*.pdf"))
    if existing:
        log.info(f"  [SKIP] 이미 변환됨: {existing[0].name}")
        return True

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
            candidate_id   = candidate_id,
            nationality    = nat,
            gender         = gen,
            birth_year     = yr,
            photo_bytes    = None,
            cover_text     = cover_pii.cleaned_text  if cover_pii  else None,
            resume_text    = resume_pii.cleaned_text if resume_pii else None,
            rec_text       = rec_pii.cleaned_text    if rec_pii    else None,
            candidate_name = name,
            out_dir        = OUTPUT_DIR,
        )
        log.info(f"  [OK] {out_path.name} ({size//1024}KB)")

        # ── inbox 소스 파일 meta.json에 processed 마커 기록 ──────────
        for src_file in files.values():
            for mp in INBOX_DIR.glob("*.meta.json"):
                try:
                    mdata = json.loads(mp.read_text(encoding="utf-8"))
                    if mdata.get("original_name", "") == src_file.name:
                        mdata["processed"]        = True
                        mdata["processed_output"] = out_path.name
                        mdata["processed_at"]     = datetime.now().isoformat()
                        mp.write_text(json.dumps(mdata, indent=2, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    pass

        # ── Google Sheet 접수 기록 ───────────────────────────────────
        if not DRY and not NO_SHEET:
            pii_total = (
                (len(resume_pii.pii_found) if resume_pii else 0) +
                (len(cover_pii.pii_found)  if cover_pii  else 0) +
                (len(rec_pii.pii_found)    if rec_pii    else 0)
            )
            try:
                sys.path.insert(0, str(BASE_DIR))
                from sheets_connector import write_intake_row
                write_intake_row(
                    candidate_id    = candidate_id,
                    nationality     = nat,
                    gender          = gen,
                    birth_year      = yr,
                    output_filename = out_path.name,
                    submission_date = submitted,
                    pii_count       = pii_total,
                    candidate_name  = name,
                )
            except Exception as se:
                log.warning(f"  [시트 기록 실패] {se}")

        return True
    except Exception as e:
        log.error(f"  [ERR] {e}", exc_info=True)
        return False


# ── 메인 ───────────────────────────────────────────────────────────────
def main():
    log.info(f"\n{'#'*60}")
    log.info(f"BRIDGE Forms 배치 변환 v3.0: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info(f"모드: {'DRY RUN' if DRY else '실제 변환'}")

    # (batch_push_pending_to_sheet 제거 — INSERT_ROWS 시트 파괴 위험)

    # ── Sheet 메타 1회 로드 ──────────────────────────────────────────
    sheet_meta = _load_sheet_meta()

    # 이미 변환된 파일 정리
    moved = _move_converted()
    log.info(f"\n이미변환 파일: {moved}개 output/ 이동")

    # 접수순 지원자 목록
    applicants = _collect_applicants()
    log.info(f"\n신규 지원자: {len(applicants)}명 (접수순)")

    # fallback 시작 ID: 현재 output/ + 변환완료 meta.json + Sheet D열 최댓값 + 1
    existing_nums = []
    # output/ 파일: {ID}{한글} 패턴만 (날짜·임시파일 제외)
    for f in OUTPUT_DIR.iterdir():
        m = re.match(r'^(\d{4,5})[가-힣]', f.name)
        if m:
            existing_nums.append(int(m.group(1)))
    # inbox meta.json: 이미 변환된 파일 한정 (한글 국적명 포함 패턴)
    for f in INBOX_DIR.glob("*.meta.json"):
        m = re.match(r'^(\d{4,5})[가-힣_]', f.name)
        if m:
            existing_nums.append(int(m.group(1)))
    # Sheet D열 ID도 포함
    for entry in sheet_meta:
        try:
            existing_nums.append(int(entry["id"]))
        except Exception:
            pass
    start_id = max(existing_nums, default=6200) + 1
    log.info(f"fallback 시작 ID: {start_id}\n")

    ok = err = skip = 0
    for i, app in enumerate(applicants):
        fallback_cid = str(start_id + i)
        sheet_hint   = _find_sheet_entry(sheet_meta, app["name"])
        result = _process_one(app, fallback_cid, sheet_hint=sheet_hint)
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
