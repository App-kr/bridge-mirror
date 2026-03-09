"""
render_monitor.py — Render 헬스체크 + Windows 토스트 알림
- 매 6시간마다 /health 체크
- 응답 200 이외 → 토스트 알림
- 응답 시간 > 30초 → cold start 경고
- 매일 09:00 → Render 빌드 로그 브라우저 오픈
- 로그: Q:/Claudework/bridge base/tools/render_monitor.log

실행: python render_monitor.py
자동 시작: Task Scheduler → 로그인 시 실행
"""

import time
import webbrowser
import logging
import requests
from datetime import datetime, date
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────────────────────────────
HEALTH_URL      = "https://bridge-n7hk.onrender.com/health"
RENDER_LOG_URL  = "https://dashboard.render.com/web/srv-ctnepulumphs73d8vb80/deploys"
LOG_PATH        = Path("Q:/Claudework/bridge base/tools/render_monitor.log")
CHECK_INTERVAL  = 6 * 60 * 60   # 6시간 (초)
COLD_START_SEC  = 30             # cold start 경고 임계값

# ── 로깅 ──────────────────────────────────────────────────────────────────────
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("render_monitor")


def toast(title: str, message: str) -> None:
    """Windows 토스트 알림 (plyer 사용, 실패 시 로그만)."""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="BRIDGE Monitor",
            timeout=10,
        )
    except Exception as e:
        log.warning("토스트 알림 실패 (plyer 미설치?): %s", e)


def check_health() -> None:
    """헬스체크 1회 실행."""
    try:
        start = time.time()
        resp = requests.get(HEALTH_URL, timeout=60)
        elapsed = time.time() - start

        if resp.status_code != 200:
            msg = f"HTTP {resp.status_code} — 서버 응답 이상"
            log.error(msg)
            toast("🚨 Render 오류", msg)
        elif elapsed > COLD_START_SEC:
            msg = f"응답 {elapsed:.1f}초 — Cold start 감지"
            log.warning(msg)
            toast("❄️ Render Cold Start", msg)
        else:
            log.info("OK — %.2fs (HTTP %d)", elapsed, resp.status_code)

    except requests.exceptions.Timeout:
        msg = "요청 타임아웃 (60초 초과)"
        log.error(msg)
        toast("🚨 Render 타임아웃", msg)
    except Exception as e:
        msg = f"연결 실패: {e}"
        log.error(msg)
        toast("🚨 Render 연결 오류", msg)


def main() -> None:
    log.info("=== render_monitor 시작 ===")
    last_log_open: date | None = None

    while True:
        now = datetime.now()

        # 매일 09:00 → 빌드 로그 브라우저 오픈
        if now.hour == 9 and now.minute < 10 and last_log_open != now.date():
            webbrowser.open(RENDER_LOG_URL)
            last_log_open = now.date()
            log.info("빌드 로그 브라우저 오픈")

        check_health()
        time.sleep(CHECK_INTERVAL)


def register_task_scheduler() -> None:
    """Windows Task Scheduler에 로그인 시 자동 실행 등록."""
    import subprocess, sys
    script = str(Path(__file__).resolve())
    pythonw = str(Path(sys.executable).parent / "pythonw.exe")
    task_name = "BridgeRenderMonitor"
    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers><LogonTrigger><Enabled>true</Enabled></LogonTrigger></Triggers>
  <Actions>
    <Exec>
      <Command>{pythonw}</Command>
      <Arguments>"{script}"</Arguments>
      <WorkingDirectory>{Path(script).parent}</WorkingDirectory>
    </Exec>
  </Actions>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy></Settings>
</Task>"""
    xml_path = Path(__file__).parent / "_task_tmp.xml"
    xml_path.write_text(xml, encoding="utf-16")
    result = subprocess.run(
        ["schtasks", "/Create", "/TN", task_name, "/XML", str(xml_path), "/F"],
        capture_output=True, text=True,
    )
    xml_path.unlink(missing_ok=True)
    if result.returncode == 0:
        print(f"Task Scheduler 등록 완료: {task_name}")
    else:
        print(f"등록 실패 (관리자 권한 필요):\n{result.stderr}")


if __name__ == "__main__":
    import sys
    if "--register" in sys.argv:
        register_task_scheduler()
    else:
        main()
