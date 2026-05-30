"""
DB 영속성 — Google Drive OAuth 백업/복원 (개인 계정 15GB 무료 활용).

Service Account는 개인 Drive 쿼터 없음 → OAuth (installed app) 로 교체.

환경변수:
  DRIVE_OAUTH_CREDENTIALS : OAuth client credentials 경로 (기본: drive_oauth_credentials.json)
  DRIVE_OAUTH_TOKEN       : 인증 토큰 경로 (기본: drive_oauth_token.json, 최초 실행 시 자동 생성)
  DRIVE_BACKUP_FOLDER     : 폴더명 (기본: BRIDGE_DB_BACKUPS)
  DB_PATH                 : master.db 경로 (기본: 리포 루트)

사용법:
  python tools/db_persist.py backup       # 최초 실행 시 브라우저 OAuth 인증
  python tools/db_persist.py backup --dry-run
  python tools/db_persist.py restore
  python tools/db_persist.py status
"""
from __future__ import annotations
import argparse, gzip, io, os, sqlite3, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE        = Path(__file__).resolve().parent.parent
DB_PATH     = Path(os.getenv("DB_PATH", str(BASE / "master.db")))
CRED_PATH   = Path(os.getenv("DRIVE_OAUTH_CREDENTIALS", str(BASE / "drive_oauth_credentials.json")))
TOKEN_PATH  = Path(os.getenv("DRIVE_OAUTH_TOKEN", str(BASE / "drive_oauth_token.json")))
FOLDER_NAME = os.getenv("DRIVE_BACKUP_FOLDER", "BRIDGE_DB_BACKUPS")
# 백업 보관 기간 — 30일 (휴가/긴 부재 중 손실 감지 안 돼도 복구 가능)
# 5MB × 30 = 150MB → Drive 15GB 무료 할당량 대비 1% 이하
MAX_KEEP    = int(os.getenv("DRIVE_BACKUP_KEEP", "30"))
SCOPES      = ["https://www.googleapis.com/auth/drive.file"]  # 자기가 만든 파일만 (최소 권한)


SA_FOLDER_ID = "1hmdplsuWZZWElVvxPk3gnymNZZMXmgFk"   # BRIDGE_DB_BACKUPS (SA reader 공유됨)
SA_SCOPES    = ["https://www.googleapis.com/auth/drive.readonly"]


# ── Service Account Drive 클라이언트 (GCP_SA_JSON_B64 폴백) ───────────────────

def _drive_sa():
    """GCP Service Account 기반 Drive 클라이언트 (Render GCP_SA_JSON_B64 폴백)."""
    import base64, json, tempfile
    import warnings; warnings.filterwarnings("ignore", category=FutureWarning)
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    sa_b64 = os.getenv("GCP_SA_JSON_B64", "").strip()
    if not sa_b64:
        raise EnvironmentError("GCP_SA_JSON_B64 환경변수 미설정")

    sa_json = base64.b64decode(sa_b64).decode("utf-8")
    sa_info = json.loads(sa_json)
    creds = service_account.Credentials.from_service_account_info(sa_info, scopes=SA_SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def restore_sa(dry_run: bool = False) -> bool:
    """GCP_SA_JSON_B64 기반 Drive 복원 (DRIVE_OAUTH_TOKEN_JSON 미설정 시 폴백)."""
    try:
        drive = _drive_sa()
    except Exception as e:
        print(f"[restore_sa] SA 초기화 실패: {e}")
        return False

    # SA에 공유된 고정 폴더 ID 사용 (OAuth _get_or_create_folder 우회)
    folder_id = SA_FOLDER_ID
    backups = _list_backups(drive, folder_id)
    if not backups:
        print("[restore_sa] SA Drive에 접근 가능한 백업 없음")
        return False

    binary_backups = [b for b in backups if b["name"].endswith(".db.gz")]
    target = binary_backups[0] if binary_backups else backups[0]

    print(f"[restore_sa] SA 복원 대상: {target['name']} ({int(target.get('size',0))//1024}KB)")
    if dry_run:
        return True

    from googleapiclient.http import MediaIoBaseDownload
    request = drive.files().get_media(fileId=target["id"])
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    gz_data = buf.read()

    raw = gzip.decompress(gz_data)
    if not raw.startswith(b"SQLite format 3"):
        print("[restore_sa] SQLite 매직 바이트 불일치 — 파일 손상")
        return False

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False, dir=str(DB_PATH.parent)) as tmp:
        tmp_path = tmp.name
    try:
        with open(tmp_path, "wb") as f:
            f.write(raw)
        conn = sqlite3.connect(tmp_path)
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        conn.close()
        if result != "ok":
            print(f"[restore_sa] 무결성 오류: {result}")
            os.unlink(tmp_path)
            return False
        import shutil
        shutil.move(tmp_path, str(DB_PATH))
        print(f"[restore_sa] ✓ SA 복원 성공 ({len(raw):,} bytes)")
        return True
    except Exception as e:
        print(f"[restore_sa] 실패: {e}")
        try: os.unlink(tmp_path)
        except Exception: pass
        return False


# ── OAuth Drive 클라이언트 ─────────────────────────────────────────────────────

def _drive():
    """OAuth 기반 Drive 클라이언트. 최초 실행 시 브라우저 인증 → token.json 저장."""
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GRequest
    from googleapiclient.discovery import build

    # ── Headless/Render 모드: 환경변수에서 토큰 복원 ──────────────────────────
    token_json_env = os.getenv("DRIVE_OAUTH_TOKEN_JSON", "").strip()
    if token_json_env and not TOKEN_PATH.exists():
        try:
            TOKEN_PATH.write_text(token_json_env, encoding="utf-8")
            try:
                os.chmod(str(TOKEN_PATH), 0o600)
            except Exception:
                pass
            print("[oauth] DRIVE_OAUTH_TOKEN_JSON → token 파일 복원 완료", flush=True)
        except Exception as e:
            print(f"[oauth] token 환경변수 복원 실패: {e}", flush=True)

    creds = None
    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GRequest())
            except Exception as e:
                print(f"[oauth] token refresh 실패 — 재인증 필요: {e}")
                creds = None
        if not creds:
            if not CRED_PATH.exists():
                raise FileNotFoundError(
                    f"OAuth credentials 없음: {CRED_PATH}. "
                    "Google Cloud Console에서 Desktop app credentials 발급 후 저장 필요."
                )
            from google_auth_oauthlib.flow import InstalledAppFlow
            import webbrowser, threading, time
            flow = InstalledAppFlow.from_client_secrets_file(str(CRED_PATH), SCOPES)
            PORT = 18765

            def _open_browser_delayed(url):
                time.sleep(1.5)
                print(f"\n[oauth] 브라우저 열기 시도: {url[:100]}\n")
                opened = False
                # 1) PowerShell Start-Process (Windows GUI 보장)
                try:
                    import subprocess
                    subprocess.Popen(
                        ["powershell", "-NoProfile", "-Command",
                         f"Start-Process '{url}'"],
                        creationflags=0x08000000  # CREATE_NO_WINDOW
                    )
                    opened = True
                    print("[oauth] PowerShell Start-Process 성공")
                except Exception as e:
                    print(f"[oauth] PowerShell 실패: {e}")
                # 2) cmd start 폴백
                if not opened:
                    try:
                        subprocess.Popen(['cmd.exe', '/c', 'start', '', url], shell=False)
                        opened = True
                        print("[oauth] cmd start 성공")
                    except Exception as e:
                        print(f"[oauth] cmd 실패: {e}")
                # 3) webbrowser 폴백
                if not opened:
                    webbrowser.open(url)
                    print("[oauth] webbrowser.open 시도")

            URL_FILE = BASE / "_oauth_url.txt"
            _old_open = webbrowser.open
            def _force_open(url, *a, **k):
                # URL을 파일에 저장 (다른 프로세스에서 읽어 브라우저 오픈용)
                try:
                    URL_FILE.write_text(url, encoding="utf-8")
                    print(f"\n[oauth] URL 파일 저장: {URL_FILE}", flush=True)
                except Exception:
                    pass
                # 브라우저 열기 시도
                t = threading.Thread(target=_open_browser_delayed, args=(url,), daemon=True)
                t.start()
                return True
            webbrowser.open = _force_open
            try:
                print(f"[oauth] 로컬 서버 포트 {PORT} 시작 중...", flush=True)
                creds = flow.run_local_server(port=PORT, open_browser=True,
                                              success_message="인증 완료! 이 창을 닫아도 됩니다.")
            finally:
                webbrowser.open = _old_open
                try: URL_FILE.unlink(missing_ok=True)
                except Exception: pass
        # token 저장 (0600 권한)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        try:
            os.chmod(str(TOKEN_PATH), 0o600)
        except Exception:
            pass
        print(f"[oauth] token 저장: {TOKEN_PATH}")

    return build("drive", "v3", credentials=creds)


def _get_or_create_folder(drive) -> str:
    """BRIDGE_DB_BACKUPS 폴더 찾기 or 생성."""
    q = f"mimeType='application/vnd.google-apps.folder' and name='{FOLDER_NAME}' and trashed=false"
    res = drive.files().list(q=q, fields="files(id, name)", pageSize=10).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    # 새로 생성
    meta = {"name": FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"}
    folder = drive.files().create(body=meta, fields="id").execute()
    print(f"[drive] 백업 폴더 생성: {FOLDER_NAME} ({folder['id']})")
    return folder["id"]


def _list_backups(drive, folder_id: str) -> list[dict]:
    """최신순 백업 목록."""
    res = drive.files().list(
        q=f"'{folder_id}' in parents and name contains 'bridge_db_' and trashed=false",
        orderBy="createdTime desc",
        fields="files(id, name, size, createdTime)",
        pageSize=50,
    ).execute()
    return res.get("files", [])


# ── 바이너리 SQLite 백업 ───────────────────────────────────────────────────────
# SQL 덤프 방식 폐기 — 멀티라인 문자열/세미콜론 파싱 오류 근본 해결
# sqlite3.connect().backup() API 사용 → 100% 무손실 바이너리 복사

def _make_binary_backup() -> bytes:
    """SQLite 바이너리 백업 → gzip 압축. SQL 파싱 이슈 없이 완전 복원 보장."""
    import tempfile as _tf
    with _tf.NamedTemporaryFile(suffix=".db", delete=False,
                                dir=str(DB_PATH.parent)) as tmp:
        tmp_path = tmp.name
    try:
        src = sqlite3.connect(str(DB_PATH))
        src.execute("PRAGMA busy_timeout=5000")
        dst = sqlite3.connect(tmp_path)
        src.backup(dst)           # WAL 포함 완전 복사
        src.close()
        dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        dst.close()
        with open(tmp_path, "rb") as f:
            raw = f.read()
        return gzip.compress(raw, compresslevel=6)
    finally:
        try: os.unlink(tmp_path)
        except Exception: pass


# ── 공개 API ──────────────────────────────────────────────────────────────────

def backup(dry_run: bool = False) -> bool:
    if not DB_PATH.exists():
        print("[backup] master.db 없음 — 스킵")
        return False

    # 백업 가치 판단 — 핵심 테이블 + UI 설정 모두 합산
    db_rows = 0
    table_counts = {}
    try:
        c = sqlite3.connect(str(DB_PATH))
        for t in ["candidates", "jobs", "client_inquiries", "sheet_prefs",
                  "boards", "community_posts", "form_configs"]:
            try:
                cnt = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                table_counts[t] = cnt
                db_rows += cnt
            except Exception:
                table_counts[t] = "(없음)"
        c.close()
    except Exception:
        pass

    if db_rows == 0:
        print("[backup] DB가 비어있음 — 백업 스킵")
        return False

    # ★ 바이너리 백업 (SQL 덤프 방식 폐기 — 세미콜론/멀티라인 파싱 오류 근본 해결)
    print(f"[backup] 바이너리 백업 생성 중... (총 rows ~{db_rows})")
    print(f"  테이블별: {table_counts}")
    gz_data = _make_binary_backup()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    fname = f"bridge_db_{ts}.db.gz"          # .db.gz = 바이너리 포맷 식별자
    print(f"  크기: {len(gz_data)//1024}KB → {fname}")

    if dry_run:
        print("  [dry-run] Drive 업로드 스킵")
        return True

    from googleapiclient.http import MediaIoBaseUpload
    drive = _drive()
    folder_id = _get_or_create_folder(drive)

    media = MediaIoBaseUpload(io.BytesIO(gz_data), mimetype="application/gzip", resumable=False)
    drive.files().create(
        body={"name": fname, "parents": [folder_id]},
        media_body=media,
        fields="id",
    ).execute()
    print(f"  [Drive] 업로드 완료: {fname}")

    backups = _list_backups(drive, folder_id)
    if len(backups) > MAX_KEEP:
        for old in backups[MAX_KEEP:]:
            drive.files().delete(fileId=old["id"]).execute()
            print(f"  [Drive] 오래된 백업 삭제: {old['name']}")

    return True


def restore(dry_run: bool = False) -> bool:
    """Drive 최신 백업 → master.db 복원.
    .db.gz = 바이너리 SQLite (권장), .sql.gz = 레거시 SQL 덤프 (폐기됨).
    바이너리 백업 우선 선택 — 없으면 레거시 SQL 폴백.
    """
    drive = _drive()
    folder_id = _get_or_create_folder(drive)
    backups = _list_backups(drive, folder_id)

    if not backups:
        print("[restore] Drive에 백업 없음")
        return False

    # ★ .db.gz 바이너리 백업 우선 — .sql.gz 레거시 건너뜀
    binary_backups = [b for b in backups if b["name"].endswith(".db.gz")]
    sql_backups    = [b for b in backups if b["name"].endswith(".sql.gz")]
    target = binary_backups[0] if binary_backups else (sql_backups[0] if sql_backups else None)

    if not target:
        print("[restore] 복원 가능한 백업 없음")
        return False

    is_binary = target["name"].endswith(".db.gz")
    print(f"[restore] 최신 백업: {target['name']} ({int(target.get('size',0))//1024}KB)"
          f" [{'바이너리' if is_binary else '레거시SQL'}]")

    if dry_run:
        print("  [dry-run] 복원 스킵")
        return True

    from googleapiclient.http import MediaIoBaseDownload
    request = drive.files().get_media(fileId=target["id"])
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    gz_data = buf.read()

    db_str = str(DB_PATH)

    # ── 바이너리 복원 (메인 경로) ──────────────────────────────────────────────
    if is_binary:
        raw = gzip.decompress(gz_data)
        print(f"  SQLite 바이너리: {len(raw):,} bytes")
        # SQLite magic bytes 검증
        if not raw.startswith(b"SQLite format 3"):
            print("  [restore] ✗ SQLite 매직 바이트 불일치 — 파일 손상")
            return False
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False,
                                         dir=str(DB_PATH.parent)) as tmp:
            tmp_path = tmp.name
        try:
            with open(tmp_path, "wb") as f:
                f.write(raw)
            # 무결성 검증
            conn = sqlite3.connect(tmp_path)
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            counts = {}
            for t in ("candidates", "jobs", "client_inquiries", "sheet_prefs"):
                try: counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                except Exception: counts[t] = 0
            conn.close()
            print(f"  integrity: {result}, 검증: {counts}")
            critical = {"candidates", "jobs", "client_inquiries"}
            if any(counts.get(t, 0) == 0 for t in critical):
                print("  [WARN] 핵심 테이블 비어있음 — 복원은 진행")

            # ── community_posts union 보존 ──────────────────────────────────────
            # 복원본은 백업 시점 기준이라, 그 이후 라이브에서 작성된 글이 빠져 있을 수 있음.
            # 덮어쓰기 전 현재 DB의 글을 스냅샷 → 복원 후 복원본에 없는 id만 추가(무손실 합집합).
            existing_cp = []
            try:
                if os.path.exists(db_str):
                    _ec = sqlite3.connect(db_str)
                    _ec.row_factory = sqlite3.Row
                    existing_cp = [dict(r) for r in _ec.execute(
                        "SELECT * FROM community_posts").fetchall()]
                    _ec.close()
            except Exception as _ce:
                print(f"  [restore] community_posts 스냅샷 스킵: {_ce}")

            os.replace(tmp_path, db_str)
            print(f"  [restore] 바이너리 복원 완료 ✓")

            if existing_cp:
                try:
                    _mc = sqlite3.connect(db_str)
                    restored_ids = {r[0] for r in _mc.execute(
                        "SELECT id FROM community_posts").fetchall()}
                    cols = list(existing_cp[0].keys())
                    add = [r for r in existing_cp if r.get("id") not in restored_ids]
                    if add:
                        ph = ",".join(["?"] * len(cols))
                        cn = ",".join(cols)
                        _mc.executemany(
                            f"INSERT INTO community_posts ({cn}) VALUES ({ph})",
                            [tuple(r[c] for c in cols) for r in add])
                        _mc.commit()
                        print(f"  [restore] community_posts union: 라이브 전용 {len(add)}건 보존")
                    _mc.close()
                except Exception as _me:
                    print(f"  [restore] community union 실패(무시): {_me}")
            return True
        except Exception as e:
            try: os.unlink(tmp_path)
            except Exception: pass
            print(f"  [restore] ✗ 실패: {e}")
            return False

    # ── 레거시 SQL 복원 폴백 (가능하면 사용, 실패해도 무방) ─────────────────────
    print("  [WARN] 레거시 SQL 백업 — 세미콜론 파싱 오류 가능성 있음")
    sql_text = gzip.decompress(gz_data).decode("utf-8")
    print(f"  SQL: {sql_text.count(chr(10)):,}줄")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False,
                                     dir=str(DB_PATH.parent)) as tmp:
        tmp_path = tmp.name
    try:
        conn = sqlite3.connect(tmp_path)
        conn.executescript(sql_text)
        conn.commit()
        counts = {}
        for t in ("candidates", "jobs", "client_inquiries"):
            try: counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except Exception: counts[t] = 0
        conn.close()
        print(f"  검증: {counts}")
        os.replace(tmp_path, db_str)
        print(f"  [restore] 레거시 SQL 복원 완료 ✓")
        return True
    except Exception as e:
        try: os.unlink(tmp_path)
        except Exception: pass
        print(f"  [restore] ✗ 레거시 SQL 실패: {e}")
        return False


def status() -> None:
    drive = _drive()
    folder_id = _get_or_create_folder(drive)
    backups = _list_backups(drive, folder_id)
    if not backups:
        print(f"[status] Drive 폴더 '{FOLDER_NAME}' 비어있음")
        return
    print(f"Drive 백업 목록 ({len(backups)}개, 폴더={FOLDER_NAME}):")
    for i, b in enumerate(backups[:20], 1):
        marker = " ← 최신" if i == 1 else ""
        size_kb = int(b.get("size", 0)) // 1024
        print(f"  {i:2d}. {b['name']}  {size_kb}KB  {b['createdTime'][:16]}{marker}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["backup", "restore", "status"])
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.cmd == "backup":
        ok = backup(dry_run=args.dry_run)
        sys.exit(0 if ok else 1)
    elif args.cmd == "restore":
        ok = restore(dry_run=args.dry_run)
        sys.exit(0 if ok else 1)
    else:
        status()


if __name__ == "__main__":
    main()
