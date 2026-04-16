"""
로컬 master.db → Render DB 복원 (업로드).

사용법:
  python tools/render_db_upload.py

동작:
  1. 로컬 master.db → SQL dump 생성
  2. POST /api/admin/db/restore 로 Render에 업로드
  3. 복원 결과(candidates/jobs/inquiries 건수) 출력

환경변수:
  BRIDGE_ADMIN_KEY  — 관리자 API 키 (필수)
  RENDER_API_URL    — Render 백엔드 URL (기본값: bridge-n7hk.onrender.com)
"""
import io
import os
import sqlite3
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

RENDER_API = os.getenv("RENDER_API_URL", "https://bridge-n7hk.onrender.com")
ADMIN_KEY  = os.getenv("BRIDGE_ADMIN_KEY", "")
LOCAL_DB   = Path(__file__).resolve().parent.parent / "master.db"


def _load_admin_key() -> str:
    # 1) 환경변수 BRIDGE_ADMIN_KEY 또는 ADMIN_API_KEY
    key = os.getenv("BRIDGE_ADMIN_KEY") or os.getenv("ADMIN_API_KEY") or ADMIN_KEY
    # 2) .env 파일에서 시도
    if not key:
        for name in ("BRIDGE_ADMIN_KEY", "ADMIN_API_KEY"):
            env_path = Path(__file__).resolve().parent.parent / ".env"
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith(f"{name}="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
            if key:
                break
    # 3) 직접 입력
    if not key:
        import getpass
        key = getpass.getpass("ADMIN_API_KEY 입력 (입력값 숨김): ").strip()
    return key


def dump_local_db() -> str:
    print(f"[1/3] 로컬 DB 덤프 중: {LOCAL_DB}")
    if not LOCAL_DB.exists():
        print(f"  오류: {LOCAL_DB} 없음")
        sys.exit(1)
    conn = sqlite3.connect(str(LOCAL_DB))
    buf = io.StringIO()
    for line in conn.iterdump():
        buf.write(line + "\n")
    conn.close()
    sql = buf.getvalue()
    size_mb = len(sql.encode("utf-8")) / 1024 / 1024
    print(f"  덤프 완료: {size_mb:.1f} MB")
    return sql


def upload(sql: str, admin_key: str) -> None:
    print(f"[2/3] Render 업로드 중: {RENDER_API}/api/admin/db/restore")

    # multipart/form-data 직접 구성
    boundary = uuid.uuid4().hex
    sql_bytes = sql.encode("utf-8")

    body_parts = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="sql_dump"; filename="master_dump.sql"\r\n'
        f"Content-Type: text/plain; charset=utf-8\r\n\r\n"
    ).encode("utf-8") + sql_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{RENDER_API}/api/admin/db/restore",
        data=body_parts,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "x-admin-key": admin_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(f"  HTTP {resp.status}")
            print(f"  응답: {body[:500]}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"  오류 HTTP {e.code}: {err_body[:300]}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"  연결 실패: {e.reason}")
        sys.exit(1)


def verify(admin_key: str) -> None:
    print(f"[3/3] Render DB 확인 중...")
    req = urllib.request.Request(
        f"{RENDER_API}/api/admin/db/stats",
        headers={"x-admin-key": admin_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(f"  결과: {body[:300]}")
    except Exception as e:
        print(f"  확인 실패: {e}")


def main():
    admin_key = _load_admin_key()
    if not admin_key:
        print("오류: BRIDGE_ADMIN_KEY 환경변수 또는 .env 파일에 키를 설정하세요.")
        sys.exit(1)

    sql = dump_local_db()
    upload(sql, admin_key)
    verify(admin_key)
    print("\n완료! /admin/sheet 새로고침하세요.")


if __name__ == "__main__":
    main()
