"""
로컬 master.db → Render /data/master.db 복원.

사용법:
  python tools/render_db_restore.py

동작:
  1. 로컬 master.db를 SQL dump
  2. POST /api/admin/db/restore (관리자 인증)
  3. 복원 결과 출력

환경변수:
  BRIDGE_ADMIN_KEY  — 관리자 API 키 (필수)
  RENDER_API_URL    — Render URL (기본: bridge-n7hk.onrender.com)
"""
import os, sys, sqlite3, io, urllib.request, urllib.error, json
from pathlib import Path

RENDER_API = os.getenv("RENDER_API_URL", "https://bridge-n7hk.onrender.com")
ADMIN_KEY  = os.getenv("BRIDGE_ADMIN_KEY", "")
BASE       = Path(__file__).resolve().parent.parent
DB_PATH    = BASE / "master.db"

def _load_key():
    global ADMIN_KEY
    if ADMIN_KEY:
        return True
    env_file = BASE / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            for prefix in ("ADMIN_API_KEY=", "BRIDGE_ADMIN_KEY="):
                if line.startswith(prefix):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        ADMIN_KEY = key
                        return True
    print("[오류] BRIDGE_ADMIN_KEY 미설정. .env의 ADMIN_API_KEY 값이 필요합니다.")
    print("  set BRIDGE_ADMIN_KEY=<your_key>")
    return False

def _dump_tables(tables=None):
    """지정 테이블만 dump (None이면 전체)"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout=5000")
    buf = io.StringIO()
    buf.write("BEGIN TRANSACTION;\n")
    if tables is None:
        for line in conn.iterdump():
            if line not in ("BEGIN TRANSACTION;", "COMMIT;"):
                buf.write(line + "\n")
    else:
        # 스키마
        for t in tables:
            rows = conn.execute(
                f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)
            ).fetchall()
            for r in rows:
                if r[0]:
                    buf.write(r[0] + ";\n")
            # 인덱스
            idx_rows = conn.execute(
                f"SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (t,)
            ).fetchall()
            for r in idx_rows:
                buf.write(r[0] + ";\n")
        # 데이터
        for t in tables:
            data_rows = conn.execute(f"SELECT * FROM {t}").fetchall()
            cols = [d[0] for d in conn.execute(f"PRAGMA table_info({t})").fetchall()]
            for row in data_rows:
                vals = []
                for v in row:
                    if v is None:
                        vals.append("NULL")
                    elif isinstance(v, (int, float)):
                        vals.append(str(v))
                    else:
                        vals.append("'" + str(v).replace("'", "''") + "'")
                buf.write(f"INSERT OR IGNORE INTO \"{t}\" VALUES({','.join(vals)});\n")
    buf.write("COMMIT;\n")
    conn.close()
    return buf.getvalue()

def _check_stats():
    """Render DB 현재 상태 확인"""
    url = f"{RENDER_API}/api/admin/db/stats"
    req = urllib.request.Request(url, headers={"x-admin-key": ADMIN_KEY})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            print("=== Render DB 현재 상태 ===")
            for k, v in data.get("data", {}).items():
                status = "✓" if v > 0 else "✗ 비어있음"
                print(f"  {k}: {v}건 {status}")
            return data.get("data", {})
    except Exception as e:
        print(f"[통계 확인 실패] {e}")
        return {}

def _restore(sql_text: str) -> bool:
    """SQL dump를 Render에 전송하여 복원"""
    url = f"{RENDER_API}/api/admin/db/restore"

    # multipart/form-data 직접 구성
    boundary = "----BridgeRestoreBoundary"
    sql_bytes = sql_text.encode("utf-8")
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="sql_dump"; filename="master.sql"\r\n'
        f"Content-Type: text/plain; charset=utf-8\r\n\r\n"
    ).encode() + sql_bytes + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "x-admin-key": ADMIN_KEY,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            result = json.loads(r.read())
            print("=== 복원 결과 ===")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return result.get("success", False)
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="replace")
        print(f"[복원 실패] HTTP {e.code}: {body_err[:500]}")
        return False
    except Exception as e:
        print(f"[복원 실패] {e}")
        return False


def main():
    if not _load_key():
        sys.exit(1)

    print(f"[1] Render DB 상태 확인 중... ({RENDER_API})")
    stats = _check_stats()

    # 이미 데이터 있으면 확인
    total = sum(v for v in stats.values() if isinstance(v, int) and v > 0)
    if total > 0:
        print(f"\nRender DB에 이미 데이터({total}건)가 있습니다.")
        ans = input("그래도 복원하시겠습니까? (y/N): ").strip().lower()
        if ans != "y":
            print("취소됨.")
            sys.exit(0)

    # 핵심 테이블만 복원 (로그/임시 데이터 제외)
    TARGET_TABLES = ["candidates", "jobs", "client_inquiries", "interviews",
                     "site_settings", "file_uploads", "mail_introduce_log"]
    print(f"\n[2] 로컬 master.db 덤프 생성 중... (테이블: {', '.join(TARGET_TABLES)})")
    sql_text = _dump_tables(TARGET_TABLES)
    line_count = sql_text.count("\n")
    size_kb = len(sql_text.encode()) // 1024
    print(f"    덤프 완료: {line_count}줄, {size_kb}KB")

    print(f"\n[3] Render에 복원 전송 중... (최대 120초)")
    ok = _restore(sql_text)
    if ok:
        print("\n복원 완료! admin/sheet 와 admin/employers 새로고침하세요.")
    else:
        print("\n복원 실패. api_server.py가 최신 버전으로 배포되었는지 확인하세요.")
        print("  Render 대시보드 → bridge-api → Logs 확인")

if __name__ == "__main__":
    main()
