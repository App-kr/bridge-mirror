"""
render_deploy.py — Render 수동 배포 트리거
=============================================
secure_store.py 에서 RENDER_DEPLOY_HOOK URL을 복호화하여 배포 트리거.

사용법:
  python tools/render_deploy.py              ← 배포 실행
  python tools/render_deploy.py --status     ← 서버 상태 확인

사전 설정 (1회):
  python tools/secure_store.py set RENDER_DEPLOY_HOOK "https://api.render.com/deploy/srv-xxx?key=yyy"
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import requests  # noqa: E402
from secure_store import store_get  # noqa: E402

HEALTH_URL = "https://bridge-n7hk.onrender.com/health"
DEPLOY_KEY = "RENDER_DEPLOY_HOOK"
MAX_HEALTH_WAIT = 300  # 5분


def check_health() -> dict | None:
    try:
        r = requests.get(HEALTH_URL, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def trigger_deploy():
    # 1. 배포 전 현재 서버 버전 확인
    print("[render_deploy] 현재 서버 상태 확인...")
    before = check_health()
    if before:
        print(f"  version: {before.get('version', '?')}")
        print(f"  timestamp: {before.get('timestamp', '?')}")
    else:
        print("  서버 응답 없음 (cold start 또는 다운)")

    # 2. Deploy hook URL 복호화
    print("\n[render_deploy] Deploy hook 복호화...")
    try:
        hook_url = store_get(DEPLOY_KEY)
    except SystemExit:
        print("\n[render_deploy] RENDER_DEPLOY_HOOK이 설정되지 않았습니다.")
        print("  먼저 실행: python tools/secure_store.py set RENDER_DEPLOY_HOOK \"URL\"")
        print("  URL 위치: Render Dashboard > Settings > Deploy Hook")
        sys.exit(1)

    # 3. 배포 트리거
    print("[render_deploy] 배포 트리거 전송...")
    try:
        r = requests.get(hook_url, timeout=30)
        if r.status_code == 200:
            print(f"  --> 배포 시작됨 (HTTP {r.status_code})")
        else:
            print(f"  --> 예상치 못한 응답: HTTP {r.status_code}")
            print(f"  body: {r.text[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"  --> 실패: {e}")
        sys.exit(1)

    # 4. 배포 완료 대기 + 헬스체크
    print(f"\n[render_deploy] 배포 완료 대기 (최대 {MAX_HEALTH_WAIT}초)...")
    start = time.time()
    dots = 0

    while time.time() - start < MAX_HEALTH_WAIT:
        time.sleep(10)
        dots += 1
        sys.stdout.write(".")
        sys.stdout.flush()

        after = check_health()
        if after:
            ts_after = after.get("timestamp", "")
            ts_before = before.get("timestamp", "") if before else ""

            if ts_after != ts_before:
                elapsed = int(time.time() - start)
                print(f"\n\n[render_deploy] 배포 완료! ({elapsed}초)")
                print(f"  version: {after.get('version', '?')}")
                print(f"  timestamp: {ts_after}")
                return

    print(f"\n\n[render_deploy] 타임아웃 ({MAX_HEALTH_WAIT}초). 수동 확인 필요:")
    print(f"  https://dashboard.render.com/web/srv-ctnepulumphs73d8vb80/deploys")


def show_status():
    print("[render_deploy] 서버 상태 확인...")
    h = check_health()
    if h:
        for k, v in h.items():
            print(f"  {k}: {v}")
    else:
        print("  응답 없음 (cold start 중이거나 다운)")


def main():
    if "--status" in sys.argv:
        show_status()
    else:
        trigger_deploy()


if __name__ == "__main__":
    main()
