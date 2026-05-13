"""
Form CV 자동 처리 파이프라인 v2.0
Drive 폴더 직접 감시 → 신규 파일만 다운로드(원본 보관) → doc_processor PII 제거

원칙:
  - Google Drive 원본: 절대 수정/삭제 금지 (읽기 전용)
  - incoming/originals/ : 다운로드 원본 영구 보관 (삭제 금지)
  - processed/          : PII 제거 결과물 (PDF/DOCX만)
  - 이미지·영상·기타    : originals/ 에만 보관, doc_processor 미실행

실행:
  "Q:/Phtyon 3/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/form_cv_pipeline.py" run
  "Q:/Phtyon 3/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/form_cv_pipeline.py" run --days 3
  "Q:/Phtyon 3/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/form_cv_pipeline.py" run --limit 10
  "Q:/Phtyon 3/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/form_cv_pipeline.py" status
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

# ── 경로 설정 ─────────────────────────────────────────────────────
BASE        = Path("Q:/Claudework/bridge base")
TOKEN_PATH  = BASE / "drive_full_token.json"
ORIGINALS   = BASE / "incoming" / "originals"   # 원본 영구 보관
PROCESSED   = BASE / "processed"                # PII 제거 결과물
STATE_FILE  = BASE / "tools" / "form_cv_state.json"
DOC_PROC    = BASE / "tools" / "doc_processor.py"
PYTHON_EXE  = Path("Q:/Phtyon 3/python.exe")

# Google Forms 파일 업로드 폴더 ID
DRIVE_FOLDER_ID = "1a_6bddT9wkbQOBeoDTU7HQWuQxpDIVso75dgdXLAT-RsBNf6Zoqta0GBfl6tKpQOyGdCIWqP"

# PII 제거 대상 MIME (나머지는 originals/ 에만 보관)
CV_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.google-apps.document",
}

MIME_PDF  = "application/pdf"
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MIME_DOC  = "application/msword"
MIME_GDOC = "application/vnd.google-apps.document"

# New 탭에서 로드한 이름→번호 캐시 (세션 내 1회)
_NAME_NO_CACHE: dict[str, int] | None = None

SPREADSHEET_ID = "1PveCbB7yfPhsmV-YwERf2PjoaKtXJmB0uJngu1dhTxM"
NEW_SHEET_RANGE = "New!B:D"   # B=이름, D=번호

ORIGINALS.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(exist_ok=True)


def _load_name_map(sheets) -> dict[str, int]:
    """New 탭 B열(이름) → D열(번호) 매핑 로드"""
    global _NAME_NO_CACHE
    if _NAME_NO_CACHE is not None:
        return _NAME_NO_CACHE

    res = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=NEW_SHEET_RANGE,
    ).execute()
    rows = res.get("values", [])
    mapping: dict[str, int] = {}
    for row in rows:
        if len(row) < 3:
            continue
        name_raw = row[0].strip()   # B열
        no_raw   = row[2].strip()   # D열 (B:D 에서 인덱스 2)
        if not name_raw or not no_raw:
            continue
        try:
            no = int(no_raw)
        except ValueError:
            continue
        # 세미콜론 구분 별명 포함 모두 등록
        for part in name_raw.split(";"):
            part = part.strip()
            if part:
                mapping[part.lower()] = no
    _NAME_NO_CACHE = mapping
    print(f"  [New탭] 번호 매핑 로드: {len(mapping)}명", flush=True)
    return mapping


def _lookup_sheet_number(name_hint: str, name_map: dict[str, int]) -> int | None:
    """Drive 파일명 이름으로 New탭 번호 조회 (fuzzy)"""
    if not name_hint or not name_map:
        return None
    needle = name_hint.strip().lower()
    # 완전 일치
    if needle in name_map:
        return name_map[needle]
    # 단어 단위 부분 일치 (성 또는 이름 하나라도 매칭)
    parts = needle.split()
    for part in parts:
        if len(part) < 3:
            continue
        for key, no in name_map.items():
            if part in key:
                return no
    return None


def _extract_submitter_name(drive_filename: str) -> str:
    """Drive 파일명 'filename - SubmitterName.ext' 에서 이름 추출"""
    stem = Path(drive_filename).stem          # 확장자 제거
    if " - " in stem:
        return stem.rsplit(" - ", 1)[-1].strip()
    return stem


def _build_services():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))
    drive  = build("drive",  "v3", credentials=creds, cache_discovery=False)
    sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
    return drive, sheets


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"processed": {}, "failed": {}, "last_run": None}


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_name(name: str) -> str:
    name = re.sub(r"[^\w\s\-.]", "", name)
    return re.sub(r"\s+", "_", name.strip())[:60]


def _list_new_files(drive, since_dt: datetime) -> list[dict]:
    """Drive 폴더에서 since_dt 이후 업로드된 파일 목록 반환"""
    since_str = since_dt.strftime("%Y-%m-%dT%H:%M:%S")
    query = (
        f"'{DRIVE_FOLDER_ID}' in parents "
        f"and trashed=false "
        f"and createdTime > '{since_str}'"
    )
    all_files = []
    page_token = None
    while True:
        res = drive.files().list(
            q=query,
            fields="nextPageToken,files(id,name,mimeType,size,createdTime)",
            orderBy="createdTime asc",
            pageSize=1000,
            pageToken=page_token,
        ).execute()
        all_files.extend(res.get("files", []))
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return all_files


def _download(drive, file_id: str, mime: str, dest_base: Path) -> Path | None:
    """파일 다운로드 → originals/ 에 저장. 저장 경로 반환."""
    try:
        if mime == MIME_GDOC:
            data = drive.files().export(fileId=file_id, mimeType=MIME_DOCX).execute()
            ext = ".docx"
        elif mime == MIME_DOC:
            req = drive.files().get_media(fileId=file_id)
            data = req.execute()
            ext = ".doc"
        elif mime == MIME_PDF:
            data = drive.files().get_media(fileId=file_id).execute()
            ext = ".pdf"
        elif mime == MIME_DOCX:
            data = drive.files().get_media(fileId=file_id).execute()
            ext = ".docx"
        else:
            # 이미지/영상 등 — 원본 확장자로 저장
            ext_map = {
                "image/jpeg": ".jpg", "image/png": ".png", "image/heif": ".heif",
                "video/mp4": ".mp4", "video/quicktime": ".mov",
                "text/plain": ".txt",
            }
            ext = ext_map.get(mime, ".bin")
            data = drive.files().get_media(fileId=file_id).execute()

        save_path = dest_base.with_suffix(ext)
        save_path.write_bytes(data if isinstance(data, bytes) else data.encode())
        return save_path

    except Exception as e:
        print(f"  ✗ 다운로드 실패: {e}", flush=True)
        return None


def _run_doc_processor(src: Path, sheet_number: int) -> bool:
    """doc_processor.py 실행 → processed/ 에 저장. 성공 여부 반환."""
    cmd = [
        str(PYTHON_EXE), "-X", "utf8", str(DOC_PROC), "process",
        str(src), "--number", str(sheet_number), "--output", str(PROCESSED),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        if r.returncode == 0:
            for line in r.stdout.strip().splitlines():
                if line.strip():
                    print(f"    {line.strip()}", flush=True)
            return True
        else:
            print(f"  ✗ doc_processor: {r.stderr[:200]}", flush=True)
            return False
    except subprocess.TimeoutExpired:
        print("  ✗ doc_processor 타임아웃", flush=True)
        return False
    except Exception as e:
        print(f"  ✗ doc_processor 예외: {e}", flush=True)
        return False


def cmd_run(args):
    drive, sheets = _build_services()
    name_map = _load_name_map(sheets)
    state  = _load_state()
    done   = set(state["processed"].keys())
    failed = state.get("failed", {})

    # 기준 시각: --days N일 전 (기본 1일)
    days  = getattr(args, "days", 1) or 1
    since = datetime.now(timezone.utc) - timedelta(days=days)
    print(f"[Drive] {days}일 이내 신규 파일 조회 (기준: {since.strftime('%Y-%m-%d %H:%M UTC')})", flush=True)

    files = _list_new_files(drive, since)
    print(f"[Drive] {len(files)}개 발견", flush=True)

    # 이미 처리된 파일 제외
    to_do = [f for f in files if f["id"] not in done]
    print(f"[Drive] 미처리: {to_do}개 | 이미처리: {len(files)-len(to_do)}개\n",
          flush=True)

    if args.limit:
        to_do = to_do[: args.limit]

    ok = fail = 0
    for f in to_do:
        fid   = f["id"]
        fname = f["name"]
        mime  = f["mimeType"]
        ct    = f.get("createdTime", "")[:16]
        is_cv = mime in CV_MIMES

        print(f"[{'CV' if is_cv else '파일'}] {fname[:55]} | {ct}", flush=True)

        # originals/ 에 저장 (파일ID 접두어로 충돌 방지)
        safe  = _safe_name(fname)
        dest  = ORIGINALS / f"{fid[:12]}_{safe}"
        saved = _download(drive, fid, mime, dest)

        if not saved:
            failed[fid] = {"ts": datetime.now().isoformat(), "name": fname, "reason": "download_failed"}
            _save_state(state)
            fail += 1
            continue

        print(f"  ✓ 원본 저장: {saved.name} ({saved.stat().st_size//1024}KB)", flush=True)

        if is_cv:
            # New 탭 D열에서 번호 조회
            submitter = _extract_submitter_name(fname)
            sheet_no  = _lookup_sheet_number(submitter, name_map)
            if sheet_no:
                print(f"  → sheet_number={sheet_no} ({submitter})", flush=True)
                ok_proc = _run_doc_processor(saved, sheet_no)
            else:
                print(f"  ⚠ DB 미등록: {submitter} — originals/ 에만 저장 (sync 후 재처리)", flush=True)
                ok_proc = False

            if ok_proc:
                state["processed"][fid] = {
                    "ts": datetime.now().isoformat(), "name": fname,
                    "mime": mime, "sheet_no": sheet_no,
                }
                ok += 1
            elif sheet_no is None:
                # DB 미등록 → 원본만 보관, 나중에 재처리
                state["processed"][fid] = {
                    "ts": datetime.now().isoformat(), "name": fname,
                    "mime": mime, "cv": True, "pending": True,
                }
                ok += 1
            else:
                failed[fid] = {"ts": datetime.now().isoformat(), "name": fname, "reason": "proc_failed"}
                fail += 1
        else:
            # 이미지·영상은 originals 저장만으로 완료
            state["processed"][fid] = {"ts": datetime.now().isoformat(), "name": fname, "mime": mime, "cv": False}
            ok += 1

        _save_state(state)
        print("", flush=True)

    state["last_run"] = datetime.now().isoformat()
    _save_state(state)
    print(f"[완료] 성공: {ok}개 | 실패: {fail}개", flush=True)


def cmd_status(args):
    state = _load_state()
    done  = state.get("processed", {})
    fail  = state.get("failed", {})
    orig  = list(ORIGINALS.glob("*.*")) if ORIGINALS.exists() else []
    proc  = list(PROCESSED.glob("*.*"))
    last  = state.get("last_run", "없음")
    cv_done = sum(1 for v in done.values() if v.get("cv", True))

    print(f"마지막 실행:         {last}")
    print(f"originals/ 원본:     {len(orig)}개  (Drive에서 받은 전체 파일)")
    print(f"processed/ 변환본:   {len(proc)}개  (PII 제거 완료)")
    print(f"처리 기록:           {len(done)}개  (CV {cv_done}개 + 기타)")
    print(f"실패:                {len(fail)}개")
    if fail:
        print("\n실패 최근 5개:")
        for fid, v in list(fail.items())[-5:]:
            print(f"  {fid[:12]} | {v.get('reason')} | {v.get('name','?')[:40]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Form CV 파이프라인 v2.0")
    sub    = parser.add_subparsers(dest="cmd")

    rp = sub.add_parser("run", help="신규 파일 처리")
    rp.add_argument("--days",  type=float, default=1, help="조회 기간 (기본: 1일)")
    rp.add_argument("--limit", type=int,   help="최대 처리 개수")

    sub.add_parser("status", help="현황 출력")

    args = parser.parse_args()
    if args.cmd == "status":
        cmd_status(args)
    else:
        if args.cmd is None:
            args.days  = 1
            args.limit = None
        cmd_run(args)
