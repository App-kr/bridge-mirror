"""
batch_process_forms.py — G폼 inbox 배치 변환기 v4.0
====================================================
v4.0 핵심 변경:
  - doc_processor.process_pdf() / process_docx() 사용 → 원본 레이아웃 보존
  - 시트 ID 없는 강사 → SKIP (임의 ID 부여 금지)
  - 시트 C열 사진 URL → Drive API로 다운로드 → process_pdf에 photo_path 전달
  - build_pdf() (텍스트 재조립) 완전 제거

사용:
  "Q:/Phtyon 3/python.exe" -X utf8 batch_process_forms.py [--dry] [--no-sheet]
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

BASE_DIR   = Path(__file__).parent
INBOX_DIR  = BASE_DIR / "inbox"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR   = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# doc_processor 경로 (bridge base/tools/doc_processor.py)
BRIDGE_TOOLS_DIR = BASE_DIR.parent   # tools/
BRIDGE_BASE_DIR  = BASE_DIR.parent.parent  # bridge base/

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

# ── 이름 추출 패턴 ──────────────────────────────────────────────────────────
NAME_RE      = re.compile(r'.* - (.+?)\.(pdf|docx|doc)$', re.IGNORECASE)
DRIVE_SUFFIX = re.compile(r'_[A-Za-z0-9]{6,10}$')

# ── 파일 타입 판별 ──────────────────────────────────────────────────────────
def _ftype(name: str) -> str:
    n = name.lower()
    if re.search(r"(cover|coverletter|cover_letter|cover letter)", n): return "cover"
    if re.search(r"(recommend|reference|ref_letter)",              n): return "rec"
    if re.search(r"(resume|cv |cv_|\bcv\b|curriculum|teacher.*cv|teaching.*cv)", n): return "resume"
    if re.search(r"(passport|document|scan|adobe)",                n): return "doc"
    if re.search(r"(certif|degree|university|diploma|substitute)", n): return "cert"
    if re.search(r"(self.intro|video|link)",                       n): return "link"
    return "resume"


# ── Sheet H열(생년) 정규화 ─────────────────────────────────────────────────
def _norm_year(h: str) -> str:
    h = (h or "").strip()
    if not h:
        return "00"
    if len(h) == 1:
        return f"0{h}"
    if len(h) == 2:
        return h
    if len(h) >= 4:
        return h[-2:]
    return h


# ── 생년 2자리 → 4자리 dob 변환 (doc_processor 전달용) ──────────────────────
def _yr2dob(yr2: str) -> str:
    """
    "93" → "1993", "02" → "2002", "00" → ""
    기준: 24 이상 → 19xx, 미만 → 20xx
    """
    if not yr2 or yr2 == "00":
        return ""
    try:
        n = int(yr2)
        if n >= 24:
            return f"19{yr2}"
        else:
            return f"20{yr2}"
    except ValueError:
        return ""


# ── Google Drive URL에서 파일 ID 추출 ───────────────────────────────────────
def _extract_drive_id(url: str) -> str | None:
    if not url:
        return None
    # https://drive.google.com/file/d/{ID}/view
    m = re.search(r'/file/d/([A-Za-z0-9_-]+)', url)
    if m:
        return m.group(1)
    # https://drive.google.com/open?id={ID}
    m = re.search(r'[?&]id=([A-Za-z0-9_-]+)', url)
    if m:
        return m.group(1)
    return None


# ── Drive API로 사진 다운로드 → 임시파일 Path 반환 ──────────────────────────
def _download_photo(photo_url: str) -> Path | None:
    if not photo_url:
        return None
    file_id = _extract_drive_id(photo_url)
    if not file_id:
        log.debug(f"  [사진] Drive ID 추출 실패: {photo_url[:60]}")
        return None
    try:
        sys.path.insert(0, str(BASE_DIR))
        from sheets_connector import _get_sheets_service_oauth
        # Drive API는 sheets_service와 같은 credentials로 접근
        from googleapiclient.discovery import build as _gapi_build
        from googleapiclient.http import MediaIoBaseDownload
        import io

        svc_obj = _get_sheets_service_oauth()  # 내부적으로 credentials 반환
        # sheets_connector의 OAuth credentials 재사용
        from sheets_connector import _get_oauth_creds
        creds = _get_oauth_creds()
        if not creds:
            log.warning("  [사진] OAuth 인증 없음 — 사진 건너뜀")
            return None

        drive_svc = _gapi_build("drive", "v3", credentials=creds)
        req = drive_svc.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        buf.seek(0)
        data = buf.read()
        if not data:
            return None

        # 임시파일 저장 (jpg 가정)
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp.write(data)
        tmp.close()
        log.info(f"  [사진] 다운로드 완료: {file_id[:12]}... ({len(data)//1024}KB)")
        return Path(tmp.name)
    except Exception as e:
        log.warning(f"  [사진] 다운로드 실패: {e}")
        return None


# ── Sheet 전체 메타 로드 (main()에서 1회) ─────────────────────────────────
def _load_sheet_meta() -> list[dict]:
    """
    Google Sheet 'New' 탭에서 강사 메타 데이터 로드.
    반환: [{row_idx, id, name, photo_url, nationality, birth_year, gender}, ...]
    sheet 열: B=이름, C=사진URL, D=강사번호, F=국적, H=생년, I=성별
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
            b_val = row[1].strip() if len(row) > 1 else ""
            if not b_val or not re.search(r"[A-Za-z]", b_val):
                continue
            c_val = row[2].strip() if len(row) > 2 else ""  # 사진 URL
            d_val = row[3].strip() if len(row) > 3 else ""
            f_val = row[5].strip() if len(row) > 5 else ""
            h_val = _norm_year(row[7].strip() if len(row) > 7 else "")
            i_val = row[8].strip() if len(row) > 8 else ""

            # D열이 숫자(강사번호)여야만 유효
            if not re.match(r"^\d{4,6}$", d_val):
                continue

            meta.append({
                "row_idx":    i + 1,
                "id":         d_val,
                "name":       b_val,
                "photo_url":  c_val,
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
    """이름 유사도(word overlap ≥ 50%)로 매칭."""
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


# ── 이미 변환된 파일 → output/ 이동 ────────────────────────────────────────
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


# ── 접수순 지원자 목록 ──────────────────────────────────────────────────────
def _collect_applicants() -> list[dict]:
    name_times: dict[str, list] = {}
    for meta_path in INBOX_DIR.glob("*.meta.json"):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            orig = data.get("original_name", "")
            ct   = data.get("created_time", "9999")
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

    applicants.sort(key=lambda x: x["submitted_at"])
    return applicants


# ── doc_processor import (lazy, 1회) ───────────────────────────────────────
_doc_processor_mod = None

def _get_doc_processor():
    global _doc_processor_mod
    if _doc_processor_mod is not None:
        return _doc_processor_mod
    # bridge base/tools/doc_processor.py
    for p in [str(BRIDGE_TOOLS_DIR), str(BRIDGE_BASE_DIR)]:
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        import doc_processor as _dp
        _doc_processor_mod = _dp
        return _dp
    except ImportError:
        # tools 패키지로 시도
        from tools import doc_processor as _dp
        _doc_processor_mod = _dp
        return _dp


# ── 단일 지원자 변환 ───────────────────────────────────────────────────────
def _process_one(app: dict, sheet_hint: dict | None) -> bool:
    """
    sheet_hint: _find_sheet_entry() 결과 또는 None
    → None이면 SKIP (임의 ID 부여 금지)
    """
    name      = app["name"]
    files     = app["files"]
    submitted = app["submitted_at"][:10]

    log.info(f"\n{'='*60}")
    log.info(f"[{name}] (접수: {submitted})")
    log.info(f"  파일: { {k: v.name for k, v in files.items()} }")

    # ── 시트 ID 없으면 SKIP ───────────────────────────────────────────────
    if not sheet_hint:
        log.info(f"  [SKIP] 시트에 강사번호 없음 — 건너뜀 (임의 ID 부여 금지)")
        return True  # 에러 아님

    candidate_id = sheet_hint["id"]
    nat          = sheet_hint.get("nationality", "") or "미상"
    gen          = sheet_hint.get("gender", "")      or "미상"
    yr           = sheet_hint.get("birth_year", "")  or "00"
    photo_url    = sheet_hint.get("photo_url", "")

    # ── 이미 처리됐는지 확인 (meta.json processed 플래그) ──────────────────
    for src_file in files.values():
        for mp in INBOX_DIR.glob("*.meta.json"):
            try:
                mdata = json.loads(mp.read_text(encoding="utf-8"))
                if mdata.get("original_name", "") == src_file.name and mdata.get("processed"):
                    log.info(f"  [SKIP] 이미 처리됨 ({mp.name})")
                    return True
            except Exception:
                continue

    # ── output/에 같은 ID 파일 있으면 건너뜀 ──────────────────────────────
    existing = list(OUTPUT_DIR.glob(f"{candidate_id}*.pdf"))
    if existing:
        log.info(f"  [SKIP] 이미 변환됨: {existing[0].name}")
        return True

    log.info(f"  ID: {candidate_id} | 국적: {nat} | 성별: {gen} | 생년: {yr}")

    # ── 이력서 파일 결정 (resume 우선, 없으면 doc) ─────────────────────────
    resume_path = files.get("resume") or files.get("doc")
    if not resume_path:
        log.warning(f"  [SKIP] 이력서 파일 없음 (파일목록: {list(files.keys())})")
        return False

    # ── 출력 파일명 ─────────────────────────────────────────────────────────
    try:
        sys.path.insert(0, str(BASE_DIR))
        from pdf_builder import build_filename
    except ImportError:
        def build_filename(cid, nat_, gen_, yr_):
            nat_k = nat_ or "미상"
            gen_k = gen_ or "미상"
            yr_k  = str(yr_)[-2:] if yr_ else "00"
            return f"{cid}{nat_k}_{gen_k}({yr_k}born).pdf"

    out_name = build_filename(candidate_id, nat, gen, yr)
    out_path = OUTPUT_DIR / out_name

    if DRY:
        log.info(f"  [DRY] → {out_name}")
        return True

    # ── 사진 다운로드 ────────────────────────────────────────────────────────
    photo_path = _download_photo(photo_url) if photo_url else None

    # ── candidate dict (doc_processor 전달용) ────────────────────────────────
    dob = _yr2dob(yr)
    candidate = {
        "full_name":    name,
        "sheet_number": int(candidate_id),
        "nationality":  nat,
        "gender":       gen,
        "dob":          dob,
        "email":        "",
        "mobile_phone": "",
        "kakaotalk":    "",
    }

    # ── doc_processor 호출 ──────────────────────────────────────────────────
    try:
        dp  = _get_doc_processor()
        ext = resume_path.suffix.lower()

        if ext == ".pdf":
            doc, logs = dp.process_pdf(
                filepath   = resume_path,
                brj_number = int(candidate_id),
                candidate  = candidate,
                dry        = False,
                photo_path = photo_path,
            )
            doc.save(str(out_path), garbage=4, deflate=True)
            doc.close()

        elif ext in (".docx", ".doc"):
            doc, logs = dp.process_docx(
                filepath   = resume_path,
                brj_number = int(candidate_id),
                candidate  = candidate,
                dry        = False,
                photo_path = photo_path,
            )
            doc.save(str(out_path))

        else:
            log.warning(f"  [SKIP] 미지원 형식: {ext}")
            return False

        size = out_path.stat().st_size if out_path.exists() else 0
        log.info(f"  [OK] {out_path.name} ({size//1024}KB, PII {len(logs)}건 삭제)")

    except Exception as e:
        log.error(f"  [ERR] doc_processor 실패: {e}", exc_info=True)
        return False
    finally:
        # 임시 사진 파일 정리
        if photo_path and photo_path.exists():
            try:
                photo_path.unlink()
            except Exception:
                pass

    # ── meta.json에 processed 마커 ────────────────────────────────────────
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

    # ── Google Sheet AV열 기록 ────────────────────────────────────────────
    if not NO_SHEET:
        try:
            from sheets_connector import write_intake_row
            write_intake_row(
                candidate_id    = candidate_id,
                nationality     = nat,
                gender          = gen,
                birth_year      = yr,
                output_filename = out_path.name,
                submission_date = submitted,
                pii_count       = len(logs),
                candidate_name  = name,
            )
        except Exception as se:
            log.warning(f"  [시트 기록 실패] {se}")

    return True


# ── 메인 ───────────────────────────────────────────────────────────────────
def main():
    log.info(f"\n{'#'*60}")
    log.info(f"BRIDGE Forms 배치 변환 v4.0: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info(f"모드: {'DRY RUN' if DRY else '실제 변환'} | Sheet: {'비활성' if NO_SHEET else '활성'}")
    log.info(f"엔진: doc_processor (원본 레이아웃 보존 + PII 삭제)")

    # ── Sheet 메타 1회 로드 ──────────────────────────────────────────────
    sheet_meta = _load_sheet_meta()

    # 이미 변환된 파일 정리
    moved = _move_converted()
    log.info(f"\n이미변환 파일: {moved}개 output/ 이동")

    # 접수순 지원자 목록
    applicants = _collect_applicants()
    log.info(f"\n신규 지원자: {len(applicants)}명 (접수순)")
    if not applicants:
        log.info("처리할 파일 없음.")
        return

    ok = err = skip = 0
    for app in applicants:
        sheet_hint = _find_sheet_entry(sheet_meta, app["name"])
        result = _process_one(app, sheet_hint=sheet_hint)
        if result is True:
            ok += 1
        else:
            err += 1

    log.info(f"\n{'='*60}")
    log.info(f"완료: 성공={ok}, 오류={err}")
    log.info(f"output/ 총 파일: {len(list(OUTPUT_DIR.iterdir()))}개")
    log.info(f"{'='*60}")


if __name__ == "__main__":
    main()
