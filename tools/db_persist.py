"""
DB 영속성 — Google Drive 백업/복원.
서비스 계정: bridge-sheet-sync-103 (기존, 추가 토큰 불필요)
스코프: drive.file (자기가 만든 파일만)

사용법:
  python tools/db_persist.py backup
  python tools/db_persist.py backup --dry-run
  python tools/db_persist.py restore
  python tools/db_persist.py status
"""
from __future__ import annotations
import argparse, gzip, io, os, sqlite3, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

BASE        = Path(__file__).resolve().parent.parent
DB_PATH     = Path(os.getenv("DB_PATH", str(BASE / "master.db")))
SA_JSON     = BASE / "gcp_service_account.json"
FOLDER_NAME = "BRIDGE_DB_BACKUPS"
FOLDER_ID   = "19dTJgPDQjPG-8ukIR9q_8K2TWAd5G0eF"  # 사용자 Drive 공유 폴더
MAX_KEEP    = 20
SCOPES      = ["https://www.googleapis.com/auth/drive"]

# ── Drive 클라이언트 ──────────────────────────────────────────────────────────

def _drive():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    creds = Credentials.from_service_account_file(str(SA_JSON), scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def _get_or_create_folder(drive) -> str:
    """공유된 BRIDGE_DB_BACKUPS 폴더 ID 반환."""
    return FOLDER_ID


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
    """master.db → SQL dump → gzip bytes."""
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
    """master.db → Drive 백업."""
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
        print("[backup] DB가 비어있음 — 백업 스킵 (복원 전 실행으로 보임)")
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

    # 오래된 백업 정리
    backups = _list_backups(drive, folder_id)
    if len(backups) > MAX_KEEP:
        for old in backups[MAX_KEEP:]:
            drive.files().delete(fileId=old["id"]).execute()
            print(f"  [Drive] 오래된 백업 삭제: {old['name']}")

    return True


def restore(dry_run: bool = False) -> bool:
    """Drive 최신 백업 → master.db 복원."""
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

    # 다운로드
    from googleapiclient.http import MediaIoBaseDownload
    request = drive.files().get_media(fileId=latest["id"])
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    gz_data = buf.read()

    # gunzip → SQL
    sql_text = gzip.decompress(gz_data).decode("utf-8")
    print(f"  SQL: {sql_text.count(chr(10)):,}줄")

    # 임시 DB에 실행 후 교체
    db_str = str(DB_PATH)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False,
                                     dir=str(DB_PATH.parent)) as tmp:
        tmp_path = tmp.name
    try:
        conn = sqlite3.connect(tmp_path)
        conn.executescript(sql_text)
        conn.commit()
        # 검증
        cand = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        conn.close()
        print(f"  검증: candidates={cand}행")
        os.replace(tmp_path, db_str)
        print(f"  [restore] 완료 ✓")

        # integrity check
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
    """Drive 백업 목록 출력."""
    drive = _drive()
    folder_id = _get_or_create_folder(drive)
    backups = _list_backups(drive, folder_id)
    if not backups:
        print("Drive에 백업 없음")
        return
    print(f"Drive 백업 목록 ({len(backups)}개):")
    for i, b in enumerate(backups):
        mark = " ← 최신" if i == 0 else ""
        size_kb = int(b.get("size", 0)) // 1024
        print(f"  {i+1:2d}. {b['name']}  {size_kb}KB  {b['createdTime'][:16]}{mark}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="BRIDGE DB ↔ Google Drive")
    p.add_argument("cmd", choices=["backup", "restore", "status"])
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.cmd == "backup":
        ok = backup(dry_run=args.dry_run)
        sys.exit(0 if ok else 1)
    elif args.cmd == "restore":
        ok = restore(dry_run=args.dry_run)
        sys.exit(0 if ok else 1)
    elif args.cmd == "status":
        status()
