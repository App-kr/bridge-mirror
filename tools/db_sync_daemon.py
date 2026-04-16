"""
db_sync_daemon.py — master.db 변경 감지 → Render 자동 업로드

동작:
  - master.db 수정 시각(mtime)을 5초마다 감시
  - 변경 감지 시 15초 debounce 후 Render에 자동 업로드
  - 업로드 성공/실패 텔레그램 알림

실행:
  pythonw tools/db_sync_daemon.py   (백그라운드, 창 없이)
  python  tools/db_sync_daemon.py   (포그라운드, 로그 출력)

자동 시작 등록:
  python tools/db_sync_daemon.py --install   (Task Scheduler 등록)
  python tools/db_sync_daemon.py --uninstall (등록 해제)
"""
import os, sys, time, uuid, json, logging, urllib.request, urllib.error
from pathlib import Path

BASE_DIR  = Path(__file__).resolve().parent.parent
DB_PATH   = BASE_DIR / "master.db"
LOG_PATH  = BASE_DIR / "logs" / "db_sync.log"
LOCK_PATH = BASE_DIR / "logs" / "db_sync.lock"
POLL_SEC  = 5       # 감시 주기 (초)
DEBOUNCE  = 15      # 변경 후 대기 (초) — 연속 쓰기 마무리 대기
RENDER_API = "https://bridge-n7hk.onrender.com"

sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [db_sync] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_PATH), encoding="utf-8"),
    ],
)
log = logging.getLogger("db_sync")


def _bx_read(key: str) -> str:
    try:
        from tools.bx import _read
        return _read(key) or ""
    except Exception:
        return os.getenv(key, "")


def _tg_notify(msg: str) -> None:
    token = _bx_read("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return
    try:
        body = json.dumps({"chat_id": chat_id, "text": msg}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        urllib.request.urlopen(req, timeout=5).close()
    except Exception:
        pass


def upload_db() -> bool:
    admin_key = _bx_read("ADMIN_API_KEY")
    if not admin_key:
        log.error("ADMIN_API_KEY 없음 — 업로드 스킵")
        return False

    try:
        with open(str(DB_PATH), "rb") as f:
            db_bytes = f.read()

        boundary = uuid.uuid4().hex
        body = (
            f"--{boundary}\r\nContent-Disposition: form-data; "
            f'name="db_file"; filename="master.db"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode() + db_bytes + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            f"{RENDER_API}/api/admin/db/restore",
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "x-admin-key": admin_key,
                "Origin": "https://bridge-chi-lime.vercel.app",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
            msg = result.get("message", "완료")
            log.info("업로드 성공: %s", msg)
            _tg_notify(f"[BRIDGE DB Sync] {msg}")
            return True

    except urllib.error.HTTPError as e:
        err = e.read().decode()[:200]
        log.error("업로드 실패 HTTP %d: %s", e.code, err)
        _tg_notify(f"[BRIDGE DB Sync] 실패 HTTP {e.code}: {err[:100]}")
        return False
    except Exception as e:
        log.error("업로드 오류: %s", e)
        _tg_notify(f"[BRIDGE DB Sync] 오류: {e}")
        return False


def run_daemon() -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)

    # 중복 실행 방지
    if LOCK_PATH.exists():
        try:
            pid = int(LOCK_PATH.read_text())
            import psutil
            if psutil.pid_exists(pid):
                log.info("이미 실행 중 (PID %d) — 종료", pid)
                return
        except Exception:
            pass
    LOCK_PATH.write_text(str(os.getpid()))

    log.info("DB Sync Daemon 시작 — %s 감시 중 (%.0fs 주기)", DB_PATH.name, POLL_SEC)
    last_mtime = DB_PATH.stat().st_mtime if DB_PATH.exists() else 0
    changed_at: float = 0

    try:
        while True:
            time.sleep(POLL_SEC)
            if not DB_PATH.exists():
                continue

            mtime = DB_PATH.stat().st_mtime
            if mtime != last_mtime:
                last_mtime = mtime
                changed_at = time.time()
                log.info("변경 감지 — %.0fs 후 업로드", DEBOUNCE)

            # debounce: 마지막 변경 후 DEBOUNCE초 지나면 업로드
            if changed_at and time.time() - changed_at >= DEBOUNCE:
                changed_at = 0
                log.info("Render 업로드 시작...")
                upload_db()

    finally:
        LOCK_PATH.unlink(missing_ok=True)


def install_task() -> None:
    """Windows Task Scheduler에 로그인 시 자동 시작으로 등록."""
    import subprocess
    pythonw = str(Path(sys.executable).parent / "pythonw.exe")
    script  = str(Path(__file__).resolve())
    cmd = (
        f'schtasks /create /tn "BRIDGE\\DBSyncDaemon" '
        f'/tr "\"{pythonw}\" -X utf8 \"{script}\"" '
        f'/sc onlogon /rl highest /f'
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("Task Scheduler 등록 완료: BRIDGE\\DBSyncDaemon")
    else:
        print("등록 실패:", result.stderr)


def uninstall_task() -> None:
    import subprocess
    result = subprocess.run('schtasks /delete /tn "BRIDGE\\DBSyncDaemon" /f', shell=True, capture_output=True, text=True)
    print("해제 완료" if result.returncode == 0 else f"실패: {result.stderr}")


if __name__ == "__main__":
    if "--install" in sys.argv:
        install_task()
    elif "--uninstall" in sys.argv:
        uninstall_task()
    else:
        run_daemon()
