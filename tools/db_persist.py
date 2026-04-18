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
MAX_KEEP    = 7
SCOPES      = ["https://www.googleapis.com/auth/drive.file"]  # 자기가 만든 파일만 (최소 권한)


# ── OAuth Drive 클라이언트 ─────────────────────────────────────────────────────

def _drive():
    """OAuth 기반 Drive 클라이언트. 최초 실행 시 브라우저 인증 → token.json 저장."""
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GRequest
    from googleapiclient.discovery import build

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
            import webbrowser
            flow = InstalledAppFlow.from_client_secrets_file(str(CRED_PATH), SCOPES)
            # open_browser=True 명시 + webbrowser.open 백업 (Windows에서 자동 실행 보장)
            _old_open = webbrowser.open
            def _force_open(url, *a, **k):
                print(f"\n[oauth] 브라우저 열기: {url[:80]}...\n")
                try:
                    import subprocess
                    subprocess.Popen(['cmd.exe', '/c', 'start', '', url], shell=False)
                except Exception:
                    _old_open(url, *a, **k)
                return True
            webbrowser.open = _force_open
            try:
                creds = flow.run_local_server(port=0, open_browser=True)
            finally:
                webbrowser.open = _old_open
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


# ── SQL 덤프 생성 ──────────────────────────────────────────────────────────────

def _make_sql_dump() -> bytes:
    TARGET = ["candidates", "jobs", "client_inquiries", "interviews",
              "site_settings", "file_uploads", "mail_introduce_log"]

    def quote_val(v):
        if v is None: return "NULL"
        if isinstance(v, (int, float)): return str(v)
        return "'" + str(v).replace("'", "''") + "'"

    def build_create(conn, tbl):
        cols = conn.execute(f'PRAGMA table_info("{tbl}")').fetchall()
        if not cols: return None
        pk_cols = [c[1] for c in cols if c[5] > 0]
        defs = []
        for _, name, typ, notnull, dflt, pk in cols:
            typ = typ or "TEXT"
            parts = [f'"{name}" {typ}']
            if len(pk_cols) == 1 and pk: parts.append("PRIMARY KEY")
            if notnull and not pk: parts.append("NOT NULL")
            if dflt is not None: parts.append(f"DEFAULT {dflt}")
            defs.append("    " + " ".join(parts))
        if len(pk_cols) > 1:
            defs.append("    PRIMARY KEY (" + ", ".join(f'"{c}"' for c in pk_cols) + ")")
        return f'CREATE TABLE IF NOT EXISTS "{tbl}" (\n' + ",\n".join(defs) + "\n);"

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout=5000")
    buf = io.StringIO()
    buf.write("BEGIN TRANSACTION;\n")
    for t in TARGET:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone():
            continue
        cs = build_create(conn, t)
        if cs: buf.write(cs + "\n")
        for (idx_sql,) in conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (t,)
        ).fetchall():
            buf.write(idx_sql + ";\n")
        for row in conn.execute(f'SELECT * FROM "{t}"').fetchall():
            vals = ",".join(quote_val(v) for v in row)
            buf.write(f'INSERT OR IGNORE INTO "{t}" VALUES({vals});\n')
    buf.write("COMMIT;\n")
    conn.close()
    sql = buf.getvalue()
    return gzip.compress(sql.encode("utf-8"), compresslevel=6)


# ── 공개 API ──────────────────────────────────────────────────────────────────

def backup(dry_run: bool = False) -> bool:
    if not DB_PATH.exists():
        print("[backup] master.db 없음 — 스킵")
        return False

    db_rows = 0
    try:
        c = sqlite3.connect(str(DB_PATH))
        for t in ["candidates", "jobs", "client_inquiries"]:
            try: db_rows += c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except Exception: pass
        c.close()
    except Exception:
        pass

    if db_rows == 0:
        print("[backup] DB가 비어있음 — 백업 스킵")
        return False

    print(f"[backup] 덤프 생성 중... (DB rows ~{db_rows})")
    gz_data = _make_sql_dump()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    fname = f"bridge_db_{ts}.sql.gz"
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
    drive = _drive()
    folder_id = _get_or_create_folder(drive)
    backups = _list_backups(drive, folder_id)

    if not backups:
        print("[restore] Drive에 백업 없음")
        return False

    latest = backups[0]
    print(f"[restore] 최신 백업: {latest['name']} ({int(latest.get('size',0))//1024}KB)")

    if dry_run:
        print("  [dry-run] 복원 스킵")
        return True

    from googleapiclient.http import MediaIoBaseDownload
    request = drive.files().get_media(fileId=latest["id"])
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    gz_data = buf.read()

    sql_text = gzip.decompress(gz_data).decode("utf-8")
    print(f"  SQL: {sql_text.count(chr(10)):,}줄")

    db_str = str(DB_PATH)
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
        if any(v == 0 for v in counts.values()):
            print("  [WARN] 일부 테이블 비어있음")
        os.replace(tmp_path, db_str)
        print(f"  [restore] 완료 ✓")

        c2 = sqlite3.connect(db_str)
        result = c2.execute("PRAGMA integrity_check").fetchone()[0]
        c2.close()
        print(f"  integrity_check: {result}")
        return True
    except Exception as e:
        try: os.unlink(tmp_path)
        except Exception: pass
        print(f"  [restore] 실패: {e}")
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
