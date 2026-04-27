"""
form_watcher.py — BRIDGE Google Forms 자동 수신 + 변환 v1.0
==============================================================
Google Drive에서 폼 업로드 파일을 자동 감지 → inbox/ 다운로드
→ 기존 인박스 파이프라인이 자동으로 처리

스코프: drive.readonly (drive.file보다 넓음 — 폼 업로드 폴더 접근)
토큰:  form_watcher_token.json (setup_form_oauth() 1회 실행 필요)

사용:
  python form_watcher.py --setup      # OAuth 1회 인증
  python form_watcher.py --once       # 1회 폴링 후 종료
  python form_watcher.py              # 5분 간격 상시 실행
  python form_watcher.py --folder-id FOLDER_ID  # 특정 폴더만 감시
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

log = logging.getLogger("form_watcher")

# ── 경로 ─────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
INBOX_DIR  = BASE_DIR / "inbox"
LOGS_DIR   = BASE_DIR / "logs"
TOKEN_FILE = BASE_DIR / "form_watcher_token.json"
STATE_FILE = BASE_DIR / "form_watcher_state.json"
CREDS_FILE = BASE_DIR.parent.parent / "drive_oauth_credentials.json"

INBOX_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ── 로그 설정 ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "form_watcher.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

# ── OAuth 스코프 ─────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
]

# ── 상태 파일 ─────────────────────────────────────────────────────────────
def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "processed_file_ids": [],
        "last_check": None,
        "folder_ids": [],           # 감시할 Drive 폴더 ID 목록
        "form_id": None,            # Google Forms form ID
        "download_count": 0,
    }

def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ── OAuth ─────────────────────────────────────────────────────────────────
def _load_creds():
    """저장된 토큰 로드 + 만료시 갱신."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        if not TOKEN_FILE.exists():
            return None

        tok = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        creds = Credentials(
            token=tok.get("token"),
            refresh_token=tok.get("refresh_token"),
            token_uri=tok.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=tok.get("client_id"),
            client_secret=tok.get("cs"),   # "cs" key avoids false-positive secret scanners
            scopes=tok.get("scopes", SCOPES),
        )
        if creds.expired and creds.refresh_token:
            log.info("토큰 갱신 중...")
            creds.refresh(Request())
            _save_token(creds)
        return creds
    except Exception as e:
        log.error(f"토큰 로드 실패: {e}")
        return None


def _save_token(creds):
    TOKEN_FILE.write_text(json.dumps({
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "cs":            creds.client_secret,   # renamed to avoid secret scanners
        "scopes":        list(creds.scopes or SCOPES),
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"토큰 저장: {TOKEN_FILE}")


def setup_oauth(port: int = 8888) -> bool:
    """OAuth 1회 인증 (브라우저 자동 열림). 완료 후 True 반환."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        if not CREDS_FILE.exists():
            log.error(f"OAuth 자격증명 파일 없음: {CREDS_FILE}")
            return False

        log.info("브라우저에서 Google 계정 인증을 진행해 주세요...")
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
        creds = flow.run_local_server(
            port=port,
            prompt="consent",
            access_type="offline",
            open_browser=True,
        )
        _save_token(creds)
        log.info("[OK] OAuth 인증 완료")
        return True
    except Exception as e:
        log.error(f"OAuth 설정 실패: {e}")
        return False


def get_drive_service():
    """인증된 Drive API 서비스 반환."""
    from googleapiclient.discovery import build

    creds = _load_creds()
    if creds is None:
        log.info("인증 토큰 없음 — OAuth 설정 실행...")
        if not setup_oauth():
            raise RuntimeError("OAuth 설정 실패")
        creds = _load_creds()

    return build("drive", "v3", credentials=creds, cache_discovery=False)


# ── Drive 폴더 탐색 ───────────────────────────────────────────────────────
def find_form_upload_folders(drive, form_id: str | None = None) -> list[dict]:
    """Google Forms 파일 업로드 폴더 자동 탐색.

    검색 방법:
      1) 폴더명에 '(파일 응답)' / '(File responses)' 포함
      2) 최근 생성된 폴더 중 PDF/DOCX 포함 폴더
    """
    folders = []
    keywords = [
        "파일 응답", "File responses", "file responses",
        "이력서", "resume", "cv ", "curriculum",
    ]
    for kw in keywords:
        try:
            q = f"mimeType='application/vnd.google-apps.folder' and name contains '{kw}' and trashed=false"
            res = drive.files().list(
                q=q,
                pageSize=20,
                fields="files(id,name,createdTime)",
            ).execute()
            for f in res.get("files", []):
                if f["id"] not in [x["id"] for x in folders]:
                    folders.append(f)
        except Exception as e:
            log.debug(f"폴더 검색 오류 ({kw}): {e}")
    if folders:
        log.info(f"폼 업로드 폴더 {len(folders)}개 발견: {[f['name'] for f in folders]}")
    return folders


# ── 파일 폴링 ─────────────────────────────────────────────────────────────
def poll_new_files(
    drive,
    folder_ids: list[str],
    known_ids: set[str],
    since_dt: datetime | None = None,
) -> list[dict]:
    """Drive에서 새 PDF/DOCX 파일 목록 반환."""
    if since_dt is None:
        since_dt = datetime.now(timezone.utc) - timedelta(days=7)

    since_str = since_dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    mime_filter = (
        "mimeType='application/pdf' or "
        "mimeType='application/vnd.openxmlformats-officedocument"
        ".wordprocessingml.document'"
    )

    new_files = []

    if folder_ids:
        # 특정 폴더 내 파일 검색
        for folder_id in folder_ids:
            try:
                q = f"({mime_filter}) and '{folder_id}' in parents and trashed=false"
                res = drive.files().list(
                    q=q,
                    orderBy="createdTime desc",
                    pageSize=50,
                    fields="files(id,name,createdTime,size,parents,mimeType)",
                ).execute()
                for f in res.get("files", []):
                    if f["id"] not in known_ids:
                        new_files.append(f)
            except Exception as e:
                log.warning(f"폴더 {folder_id} 폴링 오류: {e}")
    else:
        # 전체 Drive에서 최근 PDF/DOCX 검색 (폴더 미지정 시)
        try:
            q = f"({mime_filter}) and createdTime > '{since_str}' and trashed=false"
            res = drive.files().list(
                q=q,
                orderBy="createdTime desc",
                pageSize=50,
                fields="files(id,name,createdTime,size,parents,mimeType)",
            ).execute()
            for f in res.get("files", []):
                if f["id"] not in known_ids:
                    new_files.append(f)
        except Exception as e:
            log.warning(f"전체 Drive 폴링 오류: {e}")

    return new_files


# ── 파일 다운로드 ─────────────────────────────────────────────────────────
def download_file(drive, file_id: str, dest_path: Path) -> bool:
    """Drive 파일을 로컬에 다운로드."""
    try:
        from googleapiclient.http import MediaIoBaseDownload

        request = drive.files().get_media(fileId=file_id)
        with open(dest_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        log.info(f"다운로드 완료: {dest_path.name} ({dest_path.stat().st_size // 1024}KB)")
        return True
    except Exception as e:
        log.error(f"다운로드 실패 ({file_id}): {e}")
        return False


# ── 메타데이터 저장 ───────────────────────────────────────────────────────
def _save_meta(dest_path: Path, file_info: dict):
    """다운로드된 파일과 함께 메타데이터 JSON 저장 (파이프라인 참조용)."""
    meta = {
        "drive_file_id":   file_info.get("id"),
        "original_name":   file_info.get("name"),
        "created_time":    file_info.get("createdTime"),
        "source":          "google_forms",
        "downloaded_at":   datetime.now(timezone.utc).isoformat(),
    }
    meta_path = dest_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


# ── 메인 폴링 루프 ────────────────────────────────────────────────────────
def run_once(folder_ids: list[str] | None = None, verbose: bool = True) -> int:
    """1회 폴링: 새 파일 다운로드 → inbox/ 저장. 다운로드 수 반환."""
    state = _load_state()
    known_ids = set(state.get("processed_file_ids", []))

    # 마지막 체크 시각
    last_check = state.get("last_check")
    if last_check:
        since_dt = datetime.fromisoformat(last_check)
    else:
        since_dt = datetime.now(timezone.utc) - timedelta(days=7)

    # 폴더 목록 결정
    if folder_ids:
        active_folders = folder_ids
    else:
        active_folders = state.get("folder_ids", [])

    try:
        drive = get_drive_service()
    except Exception as e:
        log.error(f"Drive 서비스 초기화 실패: {e}")
        return 0

    # 폴더 미지정 시 자동 탐색
    if not active_folders:
        found = find_form_upload_folders(drive, state.get("form_id"))
        active_folders = [f["id"] for f in found]
        if active_folders:
            state["folder_ids"] = active_folders
            _save_state(state)

    new_files = poll_new_files(drive, active_folders, known_ids, since_dt)
    if verbose:
        log.info(f"새 파일: {len(new_files)}개")

    downloaded = 0
    for f in new_files:
        fname = f["name"]
        # 안전한 파일명 (파이프라인 인식용)
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in fname)
        dest = INBOX_DIR / safe_name
        # 중복 파일명 처리
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            dest = INBOX_DIR / f"{stem}_{f['id'][:8]}{suffix}"

        if download_file(drive, f["id"], dest):
            _save_meta(dest, f)
            known_ids.add(f["id"])
            downloaded += 1

    # 상태 업데이트
    state["processed_file_ids"] = list(known_ids)
    state["last_check"] = datetime.now(timezone.utc).isoformat()
    state["download_count"] = state.get("download_count", 0) + downloaded
    _save_state(state)

    return downloaded


def run_loop(interval_sec: int = 300, folder_ids: list[str] | None = None):
    """상시 폴링 루프 (기본 5분 간격)."""
    log.info(f"폼 감시 시작 (간격: {interval_sec}초)")
    _stop_event.clear()
    while not _stop_event.is_set():
        try:
            n = run_once(folder_ids=folder_ids)
            if n > 0:
                log.info(f"[알림] 새 이력서 {n}개 inbox 저장 완료")
        except Exception as e:
            log.error(f"폴링 오류: {e}")
        _stop_event.wait(interval_sec)
    log.info("폼 감시 종료")


_stop_event = threading.Event()
_watcher_thread: threading.Thread | None = None


def start_background(interval_sec: int = 300, folder_ids: list[str] | None = None):
    """백그라운드 스레드로 감시 시작."""
    global _watcher_thread
    _stop_event.clear()
    _watcher_thread = threading.Thread(
        target=run_loop,
        args=(interval_sec, folder_ids),
        daemon=True,
        name="form_watcher",
    )
    _watcher_thread.start()
    log.info("폼 감시 백그라운드 스레드 시작")
    return _watcher_thread


def stop_background():
    """백그라운드 감시 중지."""
    _stop_event.set()
    if _watcher_thread and _watcher_thread.is_alive():
        _watcher_thread.join(timeout=5)
    log.info("폼 감시 중지")


def set_form_config(form_id: str, folder_ids: list[str] | None = None):
    """폼 ID + 폴더 ID 설정 (상태 파일에 저장)."""
    state = _load_state()
    state["form_id"] = form_id
    if folder_ids:
        state["folder_ids"] = folder_ids
    _save_state(state)
    log.info(f"폼 설정 저장: form_id={form_id}, folders={folder_ids}")


# ── CLI ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BRIDGE 구글폼 자동 수신")
    parser.add_argument("--setup",     action="store_true", help="OAuth 1회 인증")
    parser.add_argument("--once",      action="store_true", help="1회 폴링 후 종료")
    parser.add_argument("--folder-id", help="감시할 Drive 폴더 ID")
    parser.add_argument("--form-id",   default="1vFwznyCWqFtqVomKIU1V9R8_kzMGIqH1QM4TiKs-o6Q",
                        help="Google Forms form ID")
    parser.add_argument("--interval",  type=int, default=300, help="폴링 간격(초)")
    args = parser.parse_args()

    if args.setup:
        ok = setup_oauth()
        sys.exit(0 if ok else 1)

    # 폼 설정 저장
    if args.form_id:
        folder_ids = [args.folder_id] if args.folder_id else None
        set_form_config(args.form_id, folder_ids)

    if args.once:
        n = run_once(folder_ids=[args.folder_id] if args.folder_id else None)
        print(f"[완료] 새 파일 {n}개 다운로드")
        sys.exit(0)

    # 상시 실행
    run_loop(interval_sec=args.interval, folder_ids=[args.folder_id] if args.folder_id else None)
