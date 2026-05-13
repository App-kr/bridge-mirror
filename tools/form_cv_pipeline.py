"""
Form CV 자동 처리 파이프라인 v3.0
Form 탭 이메일 기반 → 개인별 폴더 분리 → doc_processor PII 제거

원칙:
  - Google Drive 원본: 절대 수정/삭제 금지 (읽기 전용)
  - incoming/originals/{email}/ : 개인별 폴더로 분리 저장 (사진 혼재 방지)
  - processed/ : PII 제거 결과물
  - 이메일로 New탭 번호 정확히 매칭 (이름 fuzzy 매칭 사용 안 함)

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
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

BASE           = Path("Q:/Claudework/bridge base")
TOKEN_PATH     = BASE / "drive_full_token.json"
ORIGINALS_ROOT = BASE / "incoming" / "originals"   # 개인별 서브폴더
PROCESSED      = BASE / "processed"
STATE_FILE     = BASE / "tools" / "form_cv_state.json"
DOC_PROC       = BASE / "tools" / "doc_processor.py"
PYTHON_EXE     = Path("Q:/Phtyon 3/pythonw.exe")  # 2026-05-13: pythonw (no console)
_NO_WINDOW     = 0x08000000  # CREATE_NO_WINDOW
MASTER_DB      = BASE / "master.db"

SPREADSHEET_ID  = "1PveCbB7yfPhsmV-YwERf2PjoaKtXJmB0uJngu1dhTxM"
FORM_RANGE      = "Form!A2:E"    # A=타임스탬프, B=이메일, D=파일링크, E=이름
NEW_RANGE       = "New!A5:I"     # A=메일, B=이름, D=번호, F=국적, H=나이, I=성별

MIME_PDF  = "application/pdf"
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MIME_DOC  = "application/msword"
MIME_GDOC = "application/vnd.google-apps.document"
CV_MIMES  = {MIME_PDF, MIME_DOCX, MIME_DOC, MIME_GDOC}

FILE_RE = re.compile(r"id=([A-Za-z0-9_-]{25,})")

ORIGINALS_ROOT.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(exist_ok=True)


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
    """New 탭 정보를 master.db에 upsert (doc_processor 국적·성별·생년 사용)"""
    no = info["no"]
    try:
        con = sqlite3.connect(str(MASTER_DB))
        existing = con.execute("SELECT sheet_number FROM candidates WHERE sheet_number=?", (no,)).fetchone()
        if not existing:
            con.execute(
                "INSERT INTO candidates (sheet_number, full_name, email, nationality, dob, gender, is_deleted) "
                "VALUES (?,?,?,?,?,?,0)",
                (no, info["name"], info.get("email",""), info["nat"], info["dob"], info["gen"])
            )
            con.commit()
            print(f"  [DB] 등록: #{no} {info['name']} | {info['nat']} {info['gen']} {info['dob']}", flush=True)
        con.close()
    except Exception as e:
        print(f"  ⚠ DB upsert 실패: {e}", flush=True)


def _download(drive, file_id: str, mime: str, dest: Path) -> Path | None:
    """Drive 파일 다운로드 → dest 경로로 저장. 저장 경로 반환."""
    try:
        if mime == MIME_GDOC:
            data = drive.files().export(fileId=file_id, mimeType=MIME_DOCX).execute()
            ext = ".docx"
        elif mime in (MIME_PDF,):
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


def _run_doc_processor(cv_path: Path, sheet_no: int) -> bool:
    """doc_processor process 실행. 성공 여부 반환."""
    cmd = [
        str(PYTHON_EXE), "-X", "utf8", str(DOC_PROC),
        "process", str(cv_path),
        "--number", str(sheet_no),
        "--output", str(PROCESSED),
    ]
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
    state = _load_state()
    done  = set(state["processed"].keys())
    new_tab = _load_new_tab(sheets)
    print(f"  [New탭] {len(new_tab)}명 로드", flush=True)

    # Form 탭 전체 로드
    res = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=FORM_RANGE
    ).execute()
    form_rows = res.get("values", [])
    print(f"  [Form탭] {len(form_rows)}건", flush=True)

    # 기간 필터
    days  = getattr(args, "days", 1) or 1
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # 처리 대상 수집 (이메일별 중복 제거 — 같은 이메일 여러 제출 시 파일 통합)
    email_map: dict = {}  # email → {key, email, name, info, file_ids, row}
    for i, row in enumerate(form_rows):
        if len(row) < 4:
            continue
        email  = row[1].strip().lower() if len(row) > 1 else ""
        links  = row[3] if len(row) > 3 else ""
        name   = row[4].strip() if len(row) > 4 else ""

        key = email or f"row{i+2}"
        if key in done:
            continue
        if not email or not links:
            continue

        # New탭 매칭 (이메일 기준)
        info = new_tab.get(email)
        if not info:
            continue  # New탭 미등록 → 스킵

        file_ids = FILE_RE.findall(links)
        if not file_ids:
            continue

        if email in email_map:
            # 같은 이메일 재제출 — 파일 ID 합산 (중복 제거)
            existing_ids = set(email_map[email]["file_ids"])
            for fid in file_ids:
                if fid not in existing_ids:
                    email_map[email]["file_ids"].append(fid)
                    existing_ids.add(fid)
        else:
            email_map[email] = {
                "key":  key,
                "email": email,
                "name": name,
                "info": info,
                "file_ids": file_ids,
                "row": i + 2,
            }

    to_do = list(email_map.values())

    if args.limit:
        to_do = to_do[: args.limit]

    print(f"  미처리: {len(to_do)}건 | 이미완료: {len(done)}건\n", flush=True)

    ok = fail = 0
    for item in to_do:
        email    = item["email"]
        name     = item["name"]
        info     = item["info"]
        file_ids = item["file_ids"]
        no       = info["no"]

        print(f"[#{no}] {name} | {email} | 파일 {len(file_ids)}개", flush=True)

        # master.db upsert
        _upsert_candidate({**info, "email": email})

        # 개인별 폴더 (사진 혼재 방지)
        person_dir = ORIGINALS_ROOT / f"{no}_{_safe_name(email)}"
        person_dir.mkdir(exist_ok=True)

        cv_paths = []
        for fid in file_ids:
            try:
                meta = drive.files().get(fileId=fid, fields="name,mimeType,size").execute()
            except Exception as e:
                print(f"  ✗ 메타 조회 실패 [{fid[:16]}]: {e}", flush=True)
                continue

            fname = meta.get("name", fid)
            mime  = meta.get("mimeType", "")
            size  = int(meta.get("size", 0))
            dest  = person_dir / _safe_name(fname)

            saved = _download(drive, fid, mime, dest)
            if not saved:
                continue

            print(f"  ✓ {fname[:50]} ({size//1024}KB) → {saved.name}", flush=True)

            if mime in CV_MIMES:
                cv_paths.append(saved)

        # CV 파일만 doc_processor 실행
        cv_ok = 0
        for cv in cv_paths:
            print(f"  → doc_processor: {cv.name}", flush=True)
            if _run_doc_processor(cv, no):
                cv_ok += 1
            else:
                fail += 1

        if cv_paths and cv_ok == len(cv_paths):
            state["processed"][email] = {
                "ts": datetime.now().isoformat(),
                "name": name, "no": no,
                "cvs": [str(p) for p in cv_paths],
            }
            _save_state(state)
            ok += 1
            print(f"  ✅ 완료\n", flush=True)
        elif not cv_paths:
            # CV 없음 (사진/영상만) → 완료로 기록
            state["processed"][email] = {
                "ts": datetime.now().isoformat(),
                "name": name, "no": no, "cv": False,
            }
            _save_state(state)
            ok += 1
            print(f"  ✅ 파일만 보관 (CV 없음)\n", flush=True)
        else:
            state["processed"][email] = {
                "ts": datetime.now().isoformat(),
                "name": name, "no": no, "partial": True,
            }
            _save_state(state)
            print(f"  ⚠ 일부 실패\n", flush=True)

    state["last_run"] = datetime.now().isoformat()
    _save_state(state)
    print(f"[완료] 성공: {ok}건 | 실패: {fail}건", flush=True)


def cmd_status(args):
    state = _load_state()
    done  = state.get("processed", {})
    fail  = state.get("failed", {})
    orig  = list(ORIGINALS_ROOT.rglob("*.*")) if ORIGINALS_ROOT.exists() else []
    proc  = list(PROCESSED.glob("*.*"))
    print(f"마지막 실행:    {state.get('last_run','없음')}")
    print(f"처리 완료:      {len(done)}명")
    print(f"originals/:     {len(orig)}개 파일 ({len(list(ORIGINALS_ROOT.iterdir()))}명 폴더)")
    print(f"processed/:     {len(proc)}개")
    if done:
        print("\n최근 5명:")
        for k, v in list(done.items())[-5:]:
            print(f"  #{v.get('no','?')} {v.get('name','?')[:30]:30s} | {k}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub    = parser.add_subparsers(dest="cmd")
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
