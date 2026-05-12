"""
Form CV 자동 처리 파이프라인 v1.0
Google Form "Form" 탭 → Drive 파일 다운로드 → doc_processor PII 제거 → processed/ 저장

실행:
  "Q:/Phtyon 3/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/form_cv_pipeline.py"
  "Q:/Phtyon 3/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/form_cv_pipeline.py" --limit 5
  "Q:/Phtyon 3/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/form_cv_pipeline.py" --row 2
  "Q:/Phtyon 3/python.exe" -X utf8 "Q:/Claudework/bridge base/tools/form_cv_pipeline.py" --status
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

# ── 경로 설정 ─────────────────────────────────────────────────────
BASE         = Path("Q:/Claudework/bridge base")
TOKEN_PATH   = BASE / "drive_full_token.json"
INCOMING     = BASE / "incoming"
PROCESSED    = BASE / "processed"
STATE_FILE   = BASE / "tools" / "form_cv_state.json"
DOC_PROC     = BASE / "tools" / "doc_processor.py"
PYTHON_EXE   = Path("Q:/Phtyon 3/python.exe")

SPREADSHEET_ID = "1PveCbB7yfPhsmV-YwERf2PjoaKtXJmB0uJngu1dhTxM"
SHEET_RANGE    = "Form!A2:Z"   # 헤더 제외
COL_TIMESTAMP  = 0
COL_EMAIL      = 1
COL_FILE_LINK  = 3
COL_NAME       = 4
COL_NATIONALITY = 5

MIME_PDF   = "application/pdf"
MIME_DOCX  = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MIME_GDOC  = "application/vnd.google-apps.document"

FILE_RE = re.compile(r"id=([A-Za-z0-9_-]{28,})|/d/([A-Za-z0-9_-]{28,})")

# ── 폴더 생성 ─────────────────────────────────────────────────────
INCOMING.mkdir(exist_ok=True)
PROCESSED.mkdir(exist_ok=True)


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
    return {"processed": {}, "failed": {}}


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean_name(name: str) -> str:
    """파일명 안전하게 변환"""
    name = name.split(";")[0].split(":")[0].strip()
    name = re.sub(r"[^\w\s\-]", "", name)
    return re.sub(r"\s+", "_", name.strip())[:40]


def _extract_file_id(cell: str) -> str | None:
    m = FILE_RE.search(cell)
    if m:
        return m.group(1) or m.group(2)
    return None


def _download_file(drive, file_id: str, dest: Path) -> str | None:
    """Drive 파일 다운로드. 성공 시 실제 저장 경로 반환."""
    try:
        meta = drive.files().get(
            fileId=file_id,
            fields="name,mimeType,size"
        ).execute()
        mime  = meta.get("mimeType", "")
        oname = meta.get("name", file_id)
        size  = int(meta.get("size", 0))

        if mime == MIME_GDOC:
            # Google Docs → DOCX 내보내기
            data = drive.files().export(
                fileId=file_id,
                mimeType=MIME_DOCX
            ).execute()
            ext = ".docx"
        elif mime == MIME_PDF:
            req = drive.files().get_media(fileId=file_id)
            data = req.execute()
            ext = ".pdf"
        elif mime == MIME_DOCX:
            req = drive.files().get_media(fileId=file_id)
            data = req.execute()
            ext = ".docx"
        else:
            # 기타 (Google Sheets 등) → PDF 내보내기 시도
            try:
                data = drive.files().export(
                    fileId=file_id,
                    mimeType=MIME_PDF
                ).execute()
                ext = ".pdf"
            except Exception:
                print(f"  ⚠ 지원 안 되는 MIME: {mime}", flush=True)
                return None

        save_path = dest.with_suffix(ext)
        save_path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
        print(f"  ✓ 다운로드: {oname[:50]} ({len(data)//1024}KB{ext})", flush=True)
        return str(save_path)

    except Exception as e:
        print(f"  ✗ 다운로드 실패 [{file_id[:20]}]: {e}", flush=True)
        return None


def _run_doc_processor(src: Path) -> Path | None:
    """doc_processor.py process 실행. 처리된 파일 경로 반환."""
    cmd = [
        str(PYTHON_EXE), "-X", "utf8",
        str(DOC_PROC), "process",
        str(src),
        "--out", str(PROCESSED),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120
        )
        if result.returncode == 0:
            # processed/ 폴더에 생성된 파일 찾기
            out_lines = result.stdout.strip().splitlines()
            for line in out_lines:
                if "→" in line or "saved" in line.lower() or str(PROCESSED) in line:
                    print(f"  → {line.strip()}", flush=True)
            # 처리 결과 파일 확인 (stem 기반)
            candidates = sorted(PROCESSED.glob(f"*{src.stem}*"), key=lambda p: p.stat().st_mtime, reverse=True)
            if candidates:
                return candidates[0]
            # fallback: 가장 최근 수정 파일
            all_files = sorted(PROCESSED.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
            if all_files:
                return all_files[0]
        else:
            print(f"  ✗ doc_processor 오류: {result.stderr[:200]}", flush=True)
    except subprocess.TimeoutExpired:
        print("  ✗ doc_processor 타임아웃 (120초)", flush=True)
    except Exception as e:
        print(f"  ✗ doc_processor 예외: {e}", flush=True)
    return None


def cmd_run(args):
    """메인: Form 탭 읽어서 미처리 파일 처리"""
    drive, sheets = _build_services()
    state = _load_state()
    processed_keys = set(state["processed"].keys())

    # Form 탭 읽기
    result = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=SHEET_RANGE,
    ).execute()
    rows = result.get("values", [])
    print(f"[Form] 총 {len(rows)}행 읽기 완료", flush=True)

    # 처리 대상 수집
    to_process = []
    for i, row in enumerate(rows):
        row_num = i + 2  # 헤더=1, 데이터 시작=2
        if args.row and row_num != args.row:
            continue
        if len(row) <= COL_FILE_LINK or not row[COL_FILE_LINK]:
            continue
        file_id = _extract_file_id(row[COL_FILE_LINK])
        if not file_id:
            continue
        # 이미 처리됨?
        key = f"row{row_num}_{file_id[:20]}"
        if key in processed_keys and not args.force:
            continue
        name = row[COL_NAME] if len(row) > COL_NAME else "Unknown"
        ts   = row[COL_TIMESTAMP] if len(row) > COL_TIMESTAMP else ""
        to_process.append({
            "row": row_num,
            "key": key,
            "file_id": file_id,
            "name": name,
            "ts": ts,
        })

    if args.limit:
        to_process = to_process[:args.limit]

    print(f"[파이프라인] 처리 대상: {len(to_process)}개 (이미 완료: {len(processed_keys)}개)\n", flush=True)

    ok_count   = 0
    fail_count = 0

    for item in to_process:
        row_num = item["row"]
        file_id = item["file_id"]
        name    = item["name"]
        clean   = _clean_name(name)

        print(f"[row{row_num}] {name[:40]} | id={file_id[:20]}...", flush=True)

        # 임시 다운로드 경로
        tmp_path = INCOMING / f"row{row_num:04d}_{clean}"

        downloaded = _download_file(drive, file_id, tmp_path)
        if not downloaded:
            state["failed"][item["key"]] = {
                "ts": datetime.now().isoformat(),
                "reason": "download_failed",
                "name": name,
            }
            _save_state(state)
            fail_count += 1
            continue

        downloaded_path = Path(downloaded)

        # doc_processor 실행
        out_path = _run_doc_processor(downloaded_path)

        # 임시 파일 삭제
        try:
            downloaded_path.unlink(missing_ok=True)
        except Exception:
            pass

        if out_path:
            state["processed"][item["key"]] = {
                "ts": datetime.now().isoformat(),
                "name": name,
                "out": str(out_path),
                "file_id": file_id,
            }
            _save_state(state)
            ok_count += 1
            print(f"  ✅ 완료: {out_path.name}", flush=True)
        else:
            state["failed"][item["key"]] = {
                "ts": datetime.now().isoformat(),
                "reason": "doc_processor_failed",
                "name": name,
            }
            _save_state(state)
            fail_count += 1

        print("", flush=True)

    print(f"[완료] 성공: {ok_count}개 | 실패: {fail_count}개", flush=True)


def cmd_status(args):
    """처리 상태 출력"""
    state = _load_state()
    done = state.get("processed", {})
    fail = state.get("failed", {})
    print(f"처리 완료: {len(done)}개")
    print(f"실패:       {len(fail)}개")
    processed_files = sorted(PROCESSED.glob("*.*"))
    print(f"processed/ 파일: {len(processed_files)}개")
    if processed_files:
        print("최근 5개:")
        for f in processed_files[-5:]:
            print(f"  {f.name}")
    if fail:
        print("\n실패 목록 (최근 5개):")
        for k, v in list(fail.items())[-5:]:
            print(f"  {k}: {v.get('reason','?')} | {v.get('name','?')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Form CV 자동 처리 파이프라인")
    sub = parser.add_subparsers(dest="cmd")

    # 기본 실행
    run_p = sub.add_parser("run", help="미처리 파일 처리 (기본)")
    run_p.add_argument("--limit", type=int, help="최대 처리 개수")
    run_p.add_argument("--row",   type=int, help="특정 행만 처리 (예: --row 2)")
    run_p.add_argument("--force", action="store_true", help="이미 처리된 파일도 재처리")

    # 상태 확인
    sub.add_parser("status", help="처리 상태 출력")

    args = parser.parse_args()

    # 기본 커맨드 없으면 run
    if args.cmd is None or args.cmd == "run":
        if args.cmd is None:
            # 직접 인자를 run 서브커맨드로 위임
            args.limit = getattr(args, "limit", None)
            args.row   = getattr(args, "row", None)
            args.force = getattr(args, "force", False)
        cmd_run(args)
    elif args.cmd == "status":
        cmd_status(args)
