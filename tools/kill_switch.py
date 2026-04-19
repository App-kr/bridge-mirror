r"""
kill_switch.py — 긴급 차단 스위치
침해 의심 시 1명령으로 모든 admin mutation + 외부 API 차단

사용법:
  python tools/kill_switch.py ON        # 유지보수 모드 ON (모든 POST/PUT/DELETE 503)
  python tools/kill_switch.py OFF       # 정상 복귀
  python tools/kill_switch.py STATUS    # 현재 상태 조회
  python tools/kill_switch.py PANIC     # PANIC: ON + 세션 전부 무효화 + 텔레그램 긴급 알림

동작:
  1. Render 환경변수에 MAINT=1 설정 (bx에 RENDER_API_TOKEN + RENDER_SERVICE_ID 있을 때)
  2. 로컬 `.maint_flag` 파일 생성 (api_server.py 미들웨어가 체크)
  3. PANIC 모드는 /api/admin/logout-all 호출로 모든 세션 강제 종료 (존재 시)
"""
from __future__ import annotations
import json
import os
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MAINT_FLAG = BASE_DIR / ".maint_flag"

sys.path.insert(0, str(BASE_DIR))


def _read_bx(key: str) -> str:
    try:
        from tools.bx import _read_auto, has_master_pin  # type: ignore
        # PIN 없이 읽기 시도 (v1 항목만 가능)
        if has_master_pin():
            print(f"[kill_switch] {key}는 PIN 필요 — pw.py GUI에서 수동 처리하세요")
            return ""
        return _read_auto(key, None) or ""
    except Exception:
        return ""


def _render_set_maint(value: str) -> tuple[bool, str]:
    token = _read_bx("RENDER_API_TOKEN")
    sid = _read_bx("RENDER_SERVICE_ID")
    if not token or not sid:
        return False, "RENDER_API_TOKEN/SERVICE_ID 미설정 — Render 미동기화"
    try:
        # GET 현재 env
        req = urllib.request.Request(
            f"https://api.render.com/v1/services/{sid}/env-vars",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            current = json.loads(r.read().decode())
        env = {item["envVar"]["key"]: item["envVar"]["value"] for item in current}
        env["MAINT"] = value
        payload = json.dumps([{"key": k, "value": v} for k, v in env.items()]).encode()
        req2 = urllib.request.Request(
            f"https://api.render.com/v1/services/{sid}/env-vars",
            data=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="PUT",
        )
        with urllib.request.urlopen(req2, timeout=15) as r2:
            r2.read()
        return True, f"Render MAINT={value} 적용됨 (Manual Deploy 필요)"
    except Exception as e:
        return False, f"Render API 실패: {e}"


def _notify(msg: str):
    try:
        from tools.tg_notify import send_telegram  # type: ignore
        send_telegram(msg)
    except Exception as e:
        print(f"[kill_switch] 텔레그램 실패: {e}")


def cmd_on(panic: bool = False):
    MAINT_FLAG.write_text("1", encoding="utf-8")
    print(f"[kill_switch] 로컬 .maint_flag 생성: {MAINT_FLAG}")
    ok, msg = _render_set_maint("1")
    print(f"[kill_switch] Render: {msg}")
    tag = "🚨 PANIC" if panic else "⚠️ KILL-SWITCH"
    _notify(f"{tag} 활성화 — 모든 admin mutation 503 반환\n{msg}")


def cmd_off():
    if MAINT_FLAG.exists():
        MAINT_FLAG.unlink()
        print(f"[kill_switch] 로컬 .maint_flag 삭제됨")
    ok, msg = _render_set_maint("0")
    print(f"[kill_switch] Render: {msg}")
    _notify(f"✅ KILL-SWITCH 해제 — 정상 복귀\n{msg}")


def cmd_status():
    print(f"로컬 MAINT 플래그: {'ON' if MAINT_FLAG.exists() else 'OFF'}")
    print(f"파일 위치: {MAINT_FLAG}")


def cmd_panic():
    print("[kill_switch] PANIC 모드 — 모든 세션 무효화 + 유지보수 모드")
    cmd_on(panic=True)
    # 세션 무효화 (존재 시)
    try:
        api_key = _read_bx("ADMIN_API_KEY")
        if api_key:
            req = urllib.request.Request(
                "https://bridge-n7hk.onrender.com/api/admin/sessions/revoke-all",
                data=b"{}",
                headers={"x-admin-key": api_key, "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    r.read()
                print("[kill_switch] 전체 세션 강제 만료 완료")
            except Exception:
                pass  # 엔드포인트 없을 수 있음
    except Exception:
        pass


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1].upper()
    if cmd == "ON":
        cmd_on()
    elif cmd == "OFF":
        cmd_off()
    elif cmd == "STATUS":
        cmd_status()
    elif cmd == "PANIC":
        cmd_panic()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
