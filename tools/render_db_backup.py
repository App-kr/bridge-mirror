"""
Render /data/master.db → 로컬 SQL 덤프 백업.

사용법:
  python tools/render_db_backup.py

동작:
  1. GET /api/admin/db/dump (관리자 인증 포함)
  2. 로컬 backups/render_db/ 에 날짜별 .sql 파일 저장
  3. 30일 이전 자동 삭제

환경변수:
  BRIDGE_ADMIN_KEY  — 관리자 API 키 (필수)
  RENDER_API_URL    — Render 백엔드 URL (기본값: bridge-n7hk.onrender.com)
"""
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

RENDER_API = os.getenv("RENDER_API_URL", "https://bridge-n7hk.onrender.com")
ADMIN_KEY = os.getenv("BRIDGE_ADMIN_KEY", "")
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups" / "render_db"


def backup() -> bool:
    if not ADMIN_KEY:
        _env = Path(__file__).resolve().parent.parent / ".env"
        if _env.exists():
            for line in _env.read_text(encoding="utf-8").splitlines():
                if line.startswith("ADMIN_API_KEY=") or line.startswith("BRIDGE_ADMIN_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        os.environ["BRIDGE_ADMIN_KEY"] = key
                        globals()["ADMIN_KEY"] = key
                        break
        if not ADMIN_KEY:
            print("[오류] BRIDGE_ADMIN_KEY 환경변수 미설정. .env의 ADMIN_API_KEY 값을 사용하세요.")
            print("  export BRIDGE_ADMIN_KEY=<your_key>")
            return False

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d_%H%M")
    backup_file = BACKUP_DIR / f"render_master_{today}.sql"

    url = f"{RENDER_API}/api/admin/db/dump"
    print(f"[{today}] Render DB 백업 시작 → {url}")

    req = urllib.request.Request(url, headers={"x-admin-key": ADMIN_KEY})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            content = resp.read().decode("utf-8")
            backup_file.write_text(content, encoding="utf-8")
            kb = len(content) // 1024
            print(f"  저장: {backup_file.name} ({kb} KB)")
            # G: drive copy (optional -- silently skip if G: not mounted)
            try:
                import shutil as _shutil
                _gdrive_db = Path("G:/BRIDGE_Backups/db")
                if _gdrive_db.parent.parent.exists():
                    _gdrive_db.mkdir(parents=True, exist_ok=True)
                    _dest = _gdrive_db / f"render_{backup_file.name}"
                    if not _dest.exists():
                        _shutil.copy2(str(backup_file), str(_dest))
                        print("  G: drive copy: done")
                    else:
                        print("  G: drive copy: skip (exists)")
                else:
                    print("  G: drive copy: skipped (G: not mounted)")
            except Exception as _e:
                print(f"  G: drive copy: skipped ({_e})")
    except urllib.error.HTTPError as e:
        print(f"  실패: HTTP {e.code} — {e.read().decode()[:200]}")
        return False
    except urllib.error.URLError as e:
        print(f"  연결 실패: {e.reason}")
        return False

    # 30일 이전 자동 삭제
    cutoff = datetime.now() - timedelta(days=30)
    deleted = 0
    for f in BACKUP_DIR.glob("render_master_*.sql"):
        try:
            date_str = f.stem.replace("render_master_", "")[:8]
            file_date = datetime.strptime(date_str, "%Y%m%d")
            if file_date < cutoff:
                f.unlink()
                deleted += 1
        except (ValueError, OSError):
            pass
    if deleted:
        print(f"  30일 경과 {deleted}개 삭제")

    print("  완료.")
    return True


if __name__ == "__main__":
    ok = backup()
    sys.exit(0 if ok else 1)
