"""
Form CV 자동 처리 파이프라인 v4.0
Form 탭 이메일 기반 → 임시폴더 처리 → doc_processor PII 제거 → 임시폴더 삭제

원칙:
  - Google Drive 원본: 절대 수정/삭제 금지 (읽기 전용)
  - 임시폴더: 처리 완료 후 자동 삭제 (폴더 무한 증식 없음)
  - processed/ : PII 제거 결과물만 보관
  - 이메일로 New탭 번호 정확히 매칭

실행:
  "Q:/Phtyon 3/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/form_cv_pipeline.py" run
  "Q:/Phtyon 3/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/form_cv_pipeline.py" run --days 3
  "Q:/Phtyon 3/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/form_cv_pipeline.py" run --limit 5
  "Q:/Phtyon 3/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/form_cv_pipeline.py" status
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

BASE       = Path("Q:/Claudework/bridge base")
TOKEN_PATH = BASE / "drive_full_token.json"
PROCESSED  = BASE / "processed"
STATE_FILE = BASE / "tools" / "form_cv_state.json"
DOC_PROC   = BASE / "tools" / "doc_processor.py"
# 2026-05-13: pythonw (no console flicker on 5min CV pipeline)
PYTHON_EXE = Path("Q:/Phtyon 3/pythonw.exe")
_NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW
MASTER_DB  = BASE / "master.db"

SPREADSHEET_ID = "1PveCbB7yfPhsmV-YwERf2PjoaKtXJmB0uJngu1dhTxM"
FORM_RANGE     = "Form!A2:E"   # A=타임스탬프, B=이메일, D=파일링크, E=이름
NEW_RANGE      = "New!A5:I"    # A=메일, B=이름, D=번호, F=국적, H=나이, I=성별

MIME_PDF  = "application/pdf"
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MIME_DOC  = "application/msword"
MIME_GDOC = "application/vnd.google-apps.document"
CV_MIMES  = {MIME_PDF, MIME_DOCX, MIME_DOC, MIME_GDOC}

FILE_RE = re.compile(r"id=([A-Za-z0-9_-]{25,})")

# 공식 서류 키워드 — 이 단어가 파일명에 포함되면 doc_processor 대상에서 제외
# (이력서/커버레터가 아닌 배경조회, 학력인증, 여권 사본 등)
_NON_CV_KEYWORDS = [
    "apostille", "saqa", "dirco",
    "police_clearance", "police clearance",
    "criminal_record", "criminal record",
    "pcc",                          # Police Clearance Certificate
    "background_check", "background check",
    "birth_certificate", "birth certificate",
    "marriage_certificate", "marriage certificate",
    "passport_copy", "passport copy", "passport_scan",
    "bank_statement", "bank statement",
    "degree_certificate", "degree_cert",
    "transcript",
    "apostilled",
    "clearance_certificate",
]

def _is_cv_file(filename: str) -> bool:
    """파일명 기반으로 이력서/커버레터 여부 판별.
    공식 서류(APOSTILLE, PCC, SAQA 등)는 False 반환 → doc_processor 제외.
    """
    fname_lower = filename.lower().replace("-", "_").replace(" ", "_")
    for kw in _NON_CV_KEYWORDS:
        kw_norm = kw.lower().replace(" ", "_")
        if kw_norm in fname_lower:
            return False
    return True


PROCESSED.mkdir(parents=True, exist_ok=True)


def _build_services():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))
    drive  = build("drive",  "v3", credentials=creds, cache_discovery=False)
    sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
    return drive, sheets


def _load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"processed": {}, "failed": {}, "last_run": None}


def _save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_name(s):
    return re.sub(r"[^\w\-]", "_", s.strip())[:50]


def _load_new_tab(sheets) -> dict:
    """New 탭 로드 → {email: {no, name, nat, dob, gen}}"""
    res = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=NEW_RANGE
    ).execute()
    mapping = {}
    for row in res.get("values", []):
        if len(row) < 4:
            continue
        email  = row[0].strip().lower() if row[0].strip() else ""
        name   = row[1].strip() if len(row) > 1 else ""
        no_raw = row[3].strip() if len(row) > 3 else ""
        nat    = row[5].strip() if len(row) > 5 else ""
        dob    = row[7].strip() if len(row) > 7 else ""
        gen    = row[8].strip() if len(row) > 8 else ""
        if not email or not no_raw:
            continue
        try:
            no = int(no_raw)
        except ValueError:
            continue
        mapping[email] = {"no": no, "name": name, "nat": nat, "dob": dob, "gen": gen}
    return mapping


def _upsert_candidate(info: dict):
    """New 탭 정보를 master.db에 upsert"""
    no = info["no"]
    try:
        con = sqlite3.connect(str(MASTER_DB))
        existing = con.execute(
            "SELECT sheet_number FROM candidates WHERE sheet_number=?", (no,)
        ).fetchone()
        if not existing:
            con.execute(
                "INSERT INTO candidates (sheet_number, full_name, email, nationality, dob, gender, is_deleted) "
                "VALUES (?,?,?,?,?,?,0)",
                (no, info["name"], info.get("email", ""), info["nat"], info["dob"], info["gen"])
            )
            con.commit()
            print(f"  [DB] 등록: #{no} {info['name']} | {info['nat']} {info['gen']} {info['dob']}", flush=True)
        con.close()
    except Exception as e:
        print(f"  ⚠ DB upsert 실패: {e}", flush=True)


def _download(drive, file_id: str, mime: str, dest: Path) -> Path | None:
    """Drive 파일 다운로드 → dest 경로 반환."""
    try:
        if mime == MIME_GDOC:
            data = drive.files().export(fileId=file_id, mimeType=MIME_DOCX).execute()
            ext = ".docx"
        elif mime == MIME_PDF:
            data = drive.files().get_media(fileId=file_id).execute()
            ext = ".pdf"
        elif mime in (MIME_DOCX, MIME_DOC):
            data = drive.files().get_media(fileId=file_id).execute()
            ext = ".docx" if mime == MIME_DOCX else ".doc"
        else:
            ext_map = {
                "image/jpeg": ".jpg", "image/png": ".png", "image/heif": ".heif",
                "video/mp4": ".mp4", "video/quicktime": ".mov", "text/plain": ".txt",
            }
            ext = ext_map.get(mime, ".bin")
            data = drive.files().get_media(fileId=file_id).execute()

        path = dest.with_suffix(ext)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())
        return path
    except Exception as e:
        print(f"    ✗ 다운로드 실패 [{file_id[:16]}]: {e}", flush=True)
        return None


def _run_doc_processor_to(cv_path: Path, sheet_no: int, output_dir: Path,
                          photo_path: Path = None) -> bool:
    """doc_processor process 실행 (사용자 지정 출력 폴더). 성공 여부 반환."""
    cmd = [
        str(PYTHON_EXE), "-X", "utf8", str(DOC_PROC),
        "process", str(cv_path),
        "--number", str(sheet_no),
        "--output", str(output_dir),
    ]
    if photo_path and photo_path.exists():
        cmd.extend(["--photo", str(photo_path)])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120,
                           creationflags=_NO_WINDOW)
        for line in r.stdout.strip().splitlines():
            if line.strip():
                print(f"    {line.strip()}", flush=True)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        print("    ✗ doc_processor 타임아웃", flush=True)
        return False
    except Exception as e:
        print(f"    ✗ doc_processor 예외: {e}", flush=True)
        return False


def _run_doc_processor(cv_path: Path, sheet_no: int, photo_path: Path = None) -> bool:
    """doc_processor process 실행. 성공 여부 반환."""
    cmd = [
        str(PYTHON_EXE), "-X", "utf8", str(DOC_PROC),
        "process", str(cv_path),
        "--number", str(sheet_no),
        "--output", str(PROCESSED),
    ]
    if photo_path and photo_path.exists():
        cmd.extend(["--photo", str(photo_path)])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120,
                           creationflags=_NO_WINDOW)
        for line in r.stdout.strip().splitlines():
            if line.strip():
                print(f"    {line.strip()}", flush=True)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        print("    ✗ doc_processor 타임아웃", flush=True)
        return False
    except Exception as e:
        print(f"    ✗ doc_processor 예외: {e}", flush=True)
        return False


def cmd_run(args):
    drive, sheets = _build_services()
    state   = _load_state()
    done    = set(state["processed"].keys())
    new_tab = _load_new_tab(sheets)
    print(f"  [New탭] {len(new_tab)}명 로드", flush=True)

    res = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=FORM_RANGE
    ).execute()
    form_rows = res.get("values", [])
    print(f"  [Form탭] {len(form_rows)}건", flush=True)

    # 이메일별 중복 제거 — 같은 이메일 여러 제출 시 파일 통합
    email_map: dict = {}
    for i, row in enumerate(form_rows):
        if len(row) < 4:
            continue
        email = row[1].strip().lower() if len(row) > 1 else ""
        links = row[3] if len(row) > 3 else ""
        name  = row[4].strip() if len(row) > 4 else ""

        key = email or f"row{i+2}"
        if key in done or not email or not links:
            continue

        info = new_tab.get(email)
        if not info:
            continue

        file_ids = FILE_RE.findall(links)
        if not file_ids:
            continue

        if email in email_map:
            existing_ids = set(email_map[email]["file_ids"])
            for fid in file_ids:
                if fid not in existing_ids:
                    email_map[email]["file_ids"].append(fid)
                    existing_ids.add(fid)
        else:
            email_map[email] = {
                "key": key, "email": email, "name": name,
                "info": info, "file_ids": file_ids, "row": i + 2,
            }

    to_do = list(email_map.values())
    if args.limit:
        to_do = to_do[:args.limit]

    print(f"  미처리: {len(to_do)}건 | 이미완료: {len(done)}건\n", flush=True)

    ok = fail = 0
    for item in to_do:
        email    = item["email"]
        name     = item["name"]
        info     = item["info"]
        file_ids = item["file_ids"]
        no       = info["no"]

        print(f"[#{no}] {name} | {email} | 파일 {len(file_ids)}개", flush=True)
        _upsert_candidate({**info, "email": email})

        # 임시폴더 — 처리 완료 후 자동 삭제
        with tempfile.TemporaryDirectory(prefix=f"brj_{no}_") as tmp:
            tmp_dir  = Path(tmp)
            cv_paths = []
            photo_path: Path | None = None  # 후보자 사진 (이력서 삽입용)

            for fid in file_ids:
                try:
                    meta = drive.files().get(fileId=fid, fields="name,mimeType,size").execute()
                except Exception as e:
                    print(f"  ✗ 메타 조회 실패 [{fid[:16]}]: {e}", flush=True)
                    continue

                fname = meta.get("name", fid)
                mime  = meta.get("mimeType", "")
                size  = int(meta.get("size", 0))
                dest  = tmp_dir / _safe_name(fname)

                saved = _download(drive, fid, mime, dest)
                if not saved:
                    continue

                if mime in CV_MIMES and not _is_cv_file(fname):
                    print(f"  ⊘ {fname[:50]} ({size//1024}KB) — 공식서류 스킵", flush=True)
                    continue

                print(f"  ✓ {fname[:50]} ({size//1024}KB)", flush=True)

                if mime in CV_MIMES:
                    cv_paths.append(saved)
                elif mime.startswith("image/"):
                    # 이미지 (사진) — 가장 큰 이미지를 후보자 사진으로 채택
                    if photo_path is None or saved.stat().st_size > photo_path.stat().st_size:
                        photo_path = saved

            # 분류: cover letter vs resume (파일명 기반)
            _CL_TOKENS = ("cover", "_cl_", "cl-", "커버", "자기소개")
            _RES_TOKENS = ("resume", "_cv_", "cv-", "이력서")

            def _classify(p: Path) -> str:
                low = p.name.lower()
                has_cl = any(t in low for t in _CL_TOKENS)
                has_res = any(t in low for t in _RES_TOKENS)
                if has_cl and not has_res:
                    return "cover"
                return "resume"  # 기본: 이력서로 간주

            cover_paths = [p for p in cv_paths if _classify(p) == "cover"]
            resume_paths = [p for p in cv_paths if _classify(p) == "resume"]

            cv_ok = 0
            # 각 파일을 별도 staging 폴더에 출력 → 동일 출력명 충돌 방지
            staging = tmp_dir / "staging"
            staging.mkdir(exist_ok=True)
            staging_cover = staging / "cover"
            staging_resume = staging / "resume"
            staging_cover.mkdir(exist_ok=True)
            staging_resume.mkdir(exist_ok=True)

            for cv in resume_paths:
                print(f"  → resume: {cv.name}"
                      + (f"  +photo={photo_path.name}" if photo_path else ""), flush=True)
                if _run_doc_processor_to(cv, no, staging_resume, photo_path=photo_path):
                    cv_ok += 1
                else:
                    fail += 1
            for cv in cover_paths:
                print(f"  → cover: {cv.name}", flush=True)
                if _run_doc_processor_to(cv, no, staging_cover, photo_path=None):
                    cv_ok += 1
                else:
                    fail += 1

            # 병합: cover → resume 순서로 단일 PDF 생성
            try:
                import fitz
                cover_pdfs = sorted(staging_cover.glob("*.pdf"))
                resume_pdfs = sorted(staging_resume.glob("*.pdf"))
                final_name = None
                if resume_pdfs:
                    final_name = resume_pdfs[0].name
                elif cover_pdfs:
                    final_name = cover_pdfs[0].name

                if final_name and (cover_pdfs or resume_pdfs):
                    merged = fitz.open()
                    for cp in cover_pdfs:
                        src = fitz.open(str(cp))
                        merged.insert_pdf(src); src.close()
                    for rp in resume_pdfs:
                        src = fitz.open(str(rp))
                        merged.insert_pdf(src); src.close()
                    final_path = PROCESSED / final_name
                    final_path.unlink(missing_ok=True)
                    merged.save(
                        str(final_path),
                        garbage=4, deflate=True, deflate_images=True,
                        deflate_fonts=True, clean=True,
                    )
                    merged.close()
                    _parts = []
                    if cover_pdfs: _parts.append(f"cover×{len(cover_pdfs)}")
                    if resume_pdfs: _parts.append(f"resume×{len(resume_pdfs)}")
                    print(f"  📑 병합({'+'.join(_parts)}): → {final_name}  "
                          f"({final_path.stat().st_size//1024}KB)", flush=True)
            except Exception as _me:
                print(f"  [WARN] 병합 실패: {_me}", flush=True)

        # with 블록 종료 → 임시폴더 자동 삭제

        if cv_paths and cv_ok == len(cv_paths):
            state["processed"][email] = {
                "ts": datetime.now().isoformat(), "name": name, "no": no,
            }
            _save_state(state)
            ok += 1
            print(f"  ✅ 완료\n", flush=True)
        elif not cv_paths:
            state["processed"][email] = {
                "ts": datetime.now().isoformat(), "name": name, "no": no, "cv": False,
            }
            _save_state(state)
            ok += 1
            print(f"  ✅ CV 없음 (사진/영상)\n", flush=True)
        else:
            state["processed"][email] = {
                "ts": datetime.now().isoformat(), "name": name, "no": no, "partial": True,
            }
            _save_state(state)
            print(f"  ⚠ 일부 실패\n", flush=True)

    state["last_run"] = datetime.now().isoformat()
    _save_state(state)
    print(f"[완료] 성공: {ok}건 | 실패: {fail}건", flush=True)

    # 신규 처리물 있으면 결과 폴더 자동 오픈 (Windows Explorer)
    if ok > 0 and len(to_do) > 0:
        try:
            os.startfile(str(PROCESSED))
            print(f"[OPEN] {PROCESSED}", flush=True)
        except Exception as _oe:
            print(f"[OPEN-FAIL] {_oe}", flush=True)


def cmd_status(args):
    state = _load_state()
    done  = state.get("processed", {})
    proc  = list(PROCESSED.glob("*.*"))
    print(f"마지막 실행:  {state.get('last_run', '없음')}")
    print(f"처리 완료:    {len(done)}명")
    print(f"processed/:  {len(proc)}개")
    if done:
        print("\n최근 5명:")
        for k, v in list(done.items())[-5:]:
            print(f"  #{v.get('no','?')} {v.get('name','?')[:30]:30s} | {k}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    rp = sub.add_parser("run")
    rp.add_argument("--days",  type=float, default=1)
    rp.add_argument("--limit", type=int)
    sub.add_parser("status")
    args = parser.parse_args()
    if args.cmd == "status":
        cmd_status(args)
    else:
        if args.cmd is None:
            args.days = 1
            args.limit = None
        cmd_run(args)
