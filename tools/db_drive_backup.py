"""
BRIDGE DB → Google Drive 자동 백업
Google Drive 데스크톱 앱 동기화 폴더에 복사 → 자동 클라우드 업로드
토큰/API/서비스계정 불필요.
"""
import shutil, sqlite3, os, sys, gzip
from pathlib import Path
from datetime import datetime

BASE    = Path(r"Q:\Claudework\bridge base")
DB_PATH = BASE / "master.db"
MAX_KEEP = 50


def find_drive_path() -> Path | None:
    """Google Drive 마운트 경로 자동 탐지 → BRIDGE_DB_BACKUPS 폴더 반환"""
    candidates = [
        Path("H:/내 드라이브/BRIDGE_DB_BACKUPS"),
        Path("H:/My Drive/BRIDGE_DB_BACKUPS"),
        Path("G:/내 드라이브/BRIDGE_DB_BACKUPS"),
        Path("G:/My Drive/BRIDGE_DB_BACKUPS"),
        Path("I:/내 드라이브/BRIDGE_DB_BACKUPS"),
        Path("I:/My Drive/BRIDGE_DB_BACKUPS"),
    ]
    for p in candidates:
        if p.parent.exists():
            p.mkdir(exist_ok=True)
            return p
    return None


def backup() -> bool:
    drive_dir = find_drive_path()
    if not drive_dir:
        print("[ERROR] Google Drive 경로를 찾을 수 없음")
        return False

    if not DB_PATH.exists():
        print("[ERROR] master.db 없음")
        return False

    # 1. DB 무결성 + 행 수 확인
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA busy_timeout=3000")
        check = conn.execute("PRAGMA integrity_check").fetchone()[0]
        rows = {}
        for t in ["candidates", "jobs", "client_inquiries"]:
            try:
                rows[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except Exception:
                rows[t] = 0
        conn.close()
    except Exception as e:
        print(f"[ERROR] DB 읽기 실패: {e}")
        return False

    if check != "ok":
        print(f"[ERROR] DB 무결성 실패: {check}")
        return False

    total = sum(rows.values())
    if total == 0:
        print("[SKIP] DB가 비어있음 — 백업 스킵")
        return False

    # 2. SQL 덤프 + gzip → Drive
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    dump_name = f"bridge_db_{ts}.sql.gz"
    dump_path = drive_dir / dump_name

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout=5000")
    with gzip.open(str(dump_path), "wt", encoding="utf-8") as f:
        for line in conn.iterdump():
            f.write(line + "\n")
    conn.close()

    # 3. master.db 직접 복사 (빠른 복원용)
    shutil.copy2(str(DB_PATH), str(drive_dir / "master.db"))

    # 4. 오래된 덤프 삭제 (최근 MAX_KEEP개만 유지)
    old_dumps = sorted(drive_dir.glob("bridge_db_*.sql.gz"), reverse=True)
    for old in old_dumps[MAX_KEEP:]:
        old.unlink()
        print(f"[DEL] {old.name}")

    size_kb = dump_path.stat().st_size // 1024
    print(f"[OK] {dump_name} ({size_kb}KB)")
    print(f"[OK] candidates={rows['candidates']}, jobs={rows['jobs']}, inquiries={rows['client_inquiries']}")
    print(f"[OK] 폴더: {drive_dir}")
    print(f"[OK] Google Drive가 자동으로 클라우드에 동기화합니다")
    return True


def status() -> None:
    drive_dir = find_drive_path()
    if not drive_dir:
        print("[ERROR] Google Drive 경로 없음")
        return
    backups = sorted(drive_dir.glob("bridge_db_*.sql.gz"), reverse=True)
    master_copy = drive_dir / "master.db"
    print(f"백업 폴더: {drive_dir}")
    print(f"덤프 수: {len(backups)}개")
    if master_copy.exists():
        mtime = datetime.fromtimestamp(master_copy.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"master.db 최종수정: {mtime}  ({master_copy.stat().st_size // 1024}KB)")
    for b in backups[:5]:
        print(f"  {b.name}  ({b.stat().st_size // 1024}KB)")


def restore(backup_file: str | None = None) -> bool:
    drive_dir = find_drive_path()
    if not drive_dir:
        print("[ERROR] Google Drive 경로 없음")
        return False

    if backup_file:
        src = drive_dir / backup_file
    else:
        src = drive_dir / "master.db"  # 직접 복사본이 가장 빠름

    if not src.exists():
        # master.db 없으면 최신 덤프로 시도
        dumps = sorted(drive_dir.glob("bridge_db_*.sql.gz"), reverse=True)
        if not dumps:
            print("[ERROR] 복원할 파일 없음")
            return False
        src = dumps[0]
        print(f"[INFO] 최신 덤프 사용: {src.name}")

    # 현재 DB 임시 백업
    if DB_PATH.exists():
        bak = DB_PATH.with_suffix(f".db.pre-restore-{datetime.now().strftime('%H%M')}")
        shutil.copy2(str(DB_PATH), str(bak))
        print(f"[BAK] {bak.name}")

    if src.suffix == ".db":
        shutil.copy2(str(src), str(DB_PATH))
    else:
        with gzip.open(str(src), "rt", encoding="utf-8") as f:
            sql = f.read()
        if DB_PATH.exists():
            DB_PATH.unlink()
        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript(sql)
        conn.close()

    conn = sqlite3.connect(str(DB_PATH))
    check = conn.execute("PRAGMA integrity_check").fetchone()[0]
    count = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    conn.close()
    print(f"[OK] 복원 완료: candidates={count}, integrity={check}")
    return True


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "backup":
        ok = backup()
        sys.exit(0 if ok else 1)
    elif cmd == "restore":
        ok = restore(sys.argv[2] if len(sys.argv) > 2 else None)
        sys.exit(0 if ok else 1)
    elif cmd == "status":
        status()
    else:
        print("사용법: db_drive_backup.py [backup|restore|status] [파일명]")
