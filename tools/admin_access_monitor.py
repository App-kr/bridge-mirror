r"""
admin_access_monitor.py — admin lockout 자동 감지 + 자가 복구
배포 없이 작동, 매 5분 자동 실행

동작:
  1. /api/admin/login 에 가짜 비번으로 호출
  2. 응답 비교:
     - 200/403 with "비밀번호가 올바르지 않습니다" → 정상 (lockout 없음)
     - 403 with "Access denied" → IP blacklist 차단 → 자동 복구 트리거
     - 503/타임아웃 → 서버 다운 → 알림만
  3. 복구 절차:
     a. /api/admin/reset-blacklist 호출 (일시 차단만 풀림)
     b. 그래도 막혀있으면 Render API로 cache-clear 재배포 → 시작 코드가 영구 블랙리스트 클리어
     c. 텔레그램 알림 — 복구 시작/완료/실패

사용법:
  python tools/admin_access_monitor.py check       # 한 번 체크 (드라이런)
  python tools/admin_access_monitor.py heal        # 잠금 감지 시 자동 복구
  python tools/admin_access_monitor.py register    # Windows 스케줄러 등록 (5분마다)
  python tools/admin_access_monitor.py force-heal  # 강제 복구 (테스트용)

상태 저장: .admin_monitor_state.json
  - last_check / last_lockout_detected / last_recovery / consecutive_blocks
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / ".admin_monitor_state.json"
LOG_FILE = BASE_DIR / "logs" / "admin_monitor.log"
LOG_FILE.parent.mkdir(exist_ok=True)

API_BASE = "https://bridge-n7hk.onrender.com"
RENDER_SID = "srv-d6imvn1aae7s73ck5570"
VERCEL_ORIGIN = "https://bridge-chi-lime.vercel.app"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

sys.path.insert(0, str(BASE_DIR))


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"checks": 0, "lockouts_detected": 0, "recoveries": 0,
            "consecutive_blocks": 0, "last_status": "unknown"}


def _save_state(state: dict):
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    except Exception:
        pass


def _notify(msg: str):
    try:
        from tools.tg_notify import send as _send_tg  # type: ignore
        _send_tg(msg)
    except Exception as e:
        _log(f"텔레그램 알림 실패: {e}")


def _read_render_token() -> str:
    from tools.bx import _read  # type: ignore
    return _read("RENDER_API_KEY") or ""


def _read_admin_key() -> str:
    from tools.bx import _read  # type: ignore
    return _read("ADMIN_API_KEY") or ""


def check_admin_access() -> str:
    """admin/login 응답 분류:
    - 'normal' = public 엔드포인트 정상 응답 (차단 없음)
    - 'blocked' = SecurityMiddleware "Access denied" 응답 (IP 차단)
    - 'down' = 서버 응답 없음

    **중요**: 이 함수는 admin_login_guard 카운터를 증가시키지 않는다.
    /api/public/talents 는 인증 불필요한 공개 엔드포인트이지만,
    SecurityMiddleware의 IP 블랙리스트 검사는 동일하게 받는다.
    → 차단 여부 감지 가능 + 잘못된 비번 시도 누적 위험 0.
    """
    req = urllib.request.Request(
        f"{API_BASE}/api/public/talents?limit=1",
        headers={
            "Origin": VERCEL_ORIGIN,
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode("utf-8", errors="ignore")
            if r.status == 200 and "success" in body:
                return "normal"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore") if e.fp else ""
        if "Access denied" in body:
            return "blocked"
    except Exception as ex:
        _log(f"check 요청 실패: {ex}")
        return "down"
    if "Access denied" in body:
        return "blocked"
    if not body.strip():
        return "down"
    return "normal"  # 200이지만 형식 다른 경우도 정상으로 간주


def reset_blacklist_via_api() -> bool:
    """admin API로 일시 블랙리스트 클리어."""
    api_key = _read_admin_key()
    if not api_key:
        _log("ADMIN_API_KEY 없음")
        return False
    req = urllib.request.Request(
        f"{API_BASE}/api/admin/reset-blacklist",
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "X-Admin-Key": api_key,
            "Origin": VERCEL_ORIGIN,
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
        _log("reset-blacklist 호출 성공")
        return True
    except Exception as e:
        _log(f"reset-blacklist 실패: {e}")
        return False


def render_redeploy(clear_cache: bool = True) -> str:
    """Render 재배포 트리거. deploy id 반환."""
    token = _read_render_token()
    if not token:
        _log("RENDER_API_KEY 없음")
        return ""
    payload = b'{"clearCache":"clear"}' if clear_cache else b'{"clearCache":"do_not_clear"}'
    req = urllib.request.Request(
        f"https://api.render.com/v1/services/{RENDER_SID}/deploys",
        data=payload,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            res = json.loads(r.read())
        return res.get("id", "")
    except Exception as e:
        _log(f"render redeploy 실패: {e}")
        return ""


def wait_for_deploy(deploy_id: str, max_wait: int = 600) -> bool:
    """배포 완료 대기."""
    token = _read_render_token()
    if not token or not deploy_id:
        return False
    start = time.time()
    while time.time() - start < max_wait:
        time.sleep(20)
        try:
            req = urllib.request.Request(
                f"https://api.render.com/v1/services/{RENDER_SID}/deploys/{deploy_id}",
                headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.loads(r.read())
            st = d.get("status")
            _log(f"deploy {deploy_id} status={st}")
            if st == "live":
                return True
            if st in ("build_failed", "update_failed", "canceled"):
                return False
        except Exception:
            continue
    return False


def heal() -> bool:
    """자동 복구 절차 — 단계별 시도, 성공 시 즉시 종료."""
    state = _load_state()
    state["last_recovery_attempt"] = datetime.now().isoformat()

    # Step 1: API reset
    _log("[heal step 1] reset-blacklist API 호출")
    reset_blacklist_via_api()
    time.sleep(3)
    if check_admin_access() == "normal":
        _log("[heal] step 1로 복구 완료")
        state["recoveries"] = state.get("recoveries", 0) + 1
        state["last_recovery"] = datetime.now().isoformat()
        state["consecutive_blocks"] = 0
        _save_state(state)
        _notify("✅ BRIDGE 자동 복구 — reset-blacklist API로 해결")
        return True

    # Step 2: Render redeploy (cache clear → 시작 시 영구 블랙리스트 자동 클리어)
    _log("[heal step 2] Render cache-clear 재배포")
    _notify("⚠️ BRIDGE 잠금 감지 — Render 재배포 시작")
    deploy_id = render_redeploy(clear_cache=True)
    if not deploy_id:
        _notify("🚨 BRIDGE: Render API 호출 실패 — 수동 개입 필요")
        return False
    if not wait_for_deploy(deploy_id, max_wait=600):
        _notify(f"🚨 BRIDGE: 재배포 실패 (deploy={deploy_id})")
        return False

    time.sleep(5)
    if check_admin_access() == "normal":
        _log("[heal] step 2로 복구 완료")
        state["recoveries"] = state.get("recoveries", 0) + 1
        state["last_recovery"] = datetime.now().isoformat()
        state["consecutive_blocks"] = 0
        _save_state(state)
        _notify(f"✅ BRIDGE 자동 복구 완료 — Render 재배포로 해결 (deploy={deploy_id})")
        return True

    _notify("🚨 BRIDGE: 자동 복구 실패 — 모든 단계 시도 후에도 차단 지속")
    return False


def check():
    """1회 체크 — 결과만 보고."""
    state = _load_state()
    state["checks"] = state.get("checks", 0) + 1
    state["last_check"] = datetime.now().isoformat()

    status = check_admin_access()
    state["last_status"] = status

    if status == "blocked":
        state["lockouts_detected"] = state.get("lockouts_detected", 0) + 1
        state["consecutive_blocks"] = state.get("consecutive_blocks", 0) + 1
        _log(f"⚠️ admin 차단 감지 (연속 {state['consecutive_blocks']}회)")
    elif status == "normal":
        state["consecutive_blocks"] = 0
        _log("정상 — admin 접근 가능")
    else:
        _log(f"상태 = {status}")

    _save_state(state)
    return status


def cmd_heal():
    """잠금 감지 시 자동 복구 — 스케줄러 호출용."""
    status = check()
    if status == "blocked":
        heal()
    elif status == "down":
        _log("서버 응답 없음 — 복구 시도 안 함 (cold start 가능성)")


def cmd_force_heal():
    """강제 복구 — 잠금 여부 무관, 항상 실행."""
    _log("FORCE-HEAL 모드")
    heal()


def cmd_register():
    """Windows 스케줄러 등록 — 5분마다."""
    python = sys.executable
    script = str(Path(__file__).resolve())
    r = subprocess.run([
        "schtasks", "/create",
        "/sc", "minute", "/mo", "5",
        "/tn", "BRIDGE_AdminAccess_Monitor",
        "/tr", f'"{python}" "{script}" heal',
        "/rl", "limited",
        "/f",
    ], capture_output=True, creationflags=0x08000000)
    if r.returncode == 0:
        _log("스케줄러 등록 완료 — 5분마다 자동 실행")
    else:
        try:
            err = r.stderr.decode("cp949", errors="ignore")
        except Exception:
            err = str(r.stderr)
        _log(f"등록 실패: {err[:200]}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1].lower()
    if cmd == "check":
        check()
    elif cmd == "heal":
        cmd_heal()
    elif cmd == "force-heal":
        cmd_force_heal()
    elif cmd == "register":
        cmd_register()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
