"""
DB 영속성 — AWS S3 백업/복원.
기존 S3 크레덴셜(이력서 업로드용) 재사용 → Service Account 쿼터 이슈 해결.

환경변수:
  AWS_ACCESS_KEY_ID     : AWS 액세스 키
  AWS_SECRET_ACCESS_KEY : AWS 시크릿 키
  AWS_S3_BUCKET         : S3 버킷 이름
  AWS_REGION            : AWS 리전 (기본 ap-northeast-2)
  DB_PATH               : master.db 경로 (기본: Q:/Claudework/bridge base/master.db)

사용법:
  python tools/db_persist.py backup
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
S3_PREFIX   = "backups/"       # S3 key prefix
MAX_KEEP    = 7                # 최근 7개만 유지

# ── S3 클라이언트 ──────────────────────────────────────────────────────────────

def _s3_client():
    """boto3 S3 클라이언트 — 환경변수 미설정 시 RuntimeError."""
    import boto3
    ak = os.environ.get("AWS_ACCESS_KEY_ID")
    sk = os.environ.get("AWS_SECRET_ACCESS_KEY")
    bk = os.environ.get("AWS_S3_BUCKET")
    rg = os.environ.get("AWS_REGION", "ap-northeast-2")
    if not all([ak, sk, bk]):
        raise RuntimeError(
            "S3 환경변수 미설정 — AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET 필요"
        )
    return boto3.client("s3", region_name=rg, aws_access_key_id=ak, aws_secret_access_key=sk), bk


def _list_backups(client, bucket: str) -> list[dict]:
    """최신순 백업 목록 (S3)."""
    resp = client.list_objects_v2(Bucket=bucket, Prefix=S3_PREFIX)
    items = resp.get("Contents", [])
    # bridge_db_ 접두사만 필터 + 최신순 정렬
    items = [it for it in items if "bridge_db_" in it["Key"]]
    items.sort(key=lambda x: x["LastModified"], reverse=True)
    return items


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
    """master.db → S3 백업."""
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
    key = S3_PREFIX + fname
    print(f"  크기: {len(gz_data)//1024}KB → s3://.../{key}")

    if dry_run:
        print("  [dry-run] S3 업로드 스킵")
        return True

    client, bucket = _s3_client()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=gz_data,
        ContentType="application/gzip",
        ServerSideEncryption="AES256",
    )
    print(f"  [S3] 업로드 완료: {key}")

    # 오래된 백업 정리 (MAX_KEEP 개 초과 삭제)
    backups = _list_backups(client, bucket)
    if len(backups) > MAX_KEEP:
        for old in backups[MAX_KEEP:]:
            client.delete_object(Bucket=bucket, Key=old["Key"])
            print(f"  [S3] 오래된 백업 삭제: {old['Key']}")

    return True


def restore(dry_run: bool = False) -> bool:
    """S3 최신 백업 → master.db 복원."""
    client, bucket = _s3_client()
    backups = _list_backups(client, bucket)

    if not backups:
        print("[restore] S3에 백업 없음")
        return False

    latest = backups[0]
    print(f"[restore] 최신 백업: {latest['Key']} ({latest['Size']//1024}KB, {latest['LastModified']})")

    if dry_run:
        print("  [dry-run] 복원 스킵")
        return True

    # 다운로드
    resp = client.get_object(Bucket=bucket, Key=latest["Key"])
    gz_data = resp["Body"].read()

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
        # 검증 — 3개 필수 테이블 모두 확인
        counts = {}
        for t in ("candidates", "jobs", "client_inquiries"):
            try:
                counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except Exception:
                counts[t] = 0
        conn.close()
        print(f"  검증: {counts}")
        # 어느 필수 테이블이든 0이면 부분 복원 경고
        if any(v == 0 for v in counts.values()):
            print("  [WARN] 일부 테이블 비어있음 — 백업 덤프 확인 필요")
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
    """S3 백업 목록 출력."""
    try:
        client, bucket = _s3_client()
    except RuntimeError as e:
        print(f"[status] {e}")
        return
    backups = _list_backups(client, bucket)
    if not backups:
        print(f"[status] S3://{bucket}/{S3_PREFIX} 에 백업 없음")
        return
    print(f"S3 백업 목록 ({len(backups)}개, bucket={bucket}):")
    for i, b in enumerate(backups[:20], 1):
        marker = " ← 최신" if i == 1 else ""
        print(f"  {i:2d}. {b['Key']}  {b['Size']//1024}KB  {b['LastModified'].strftime('%Y-%m-%dT%H:%M')}{marker}")


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
