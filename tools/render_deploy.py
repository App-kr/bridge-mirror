"""
render_deploy.py — Render 배포 트리거 (API 방식)
==================================================
secure_store.py 에서 RENDER_API_KEY를 복호화하여 Render REST API로 배포.
(Deploy Hook은 PRO 전용이므로, 무료 플랜에서도 동작하는 API 방식 사용)

사용법:
  python tools/render_deploy.py              <- 배포 실행
  python tools/render_deploy.py --status     <- 서버 상태 확인

사전 설정 (1회):
  python tools/secure_store.py set RENDER_API_KEY "rnd_xxxxxxxxxxxx"
  (Render Dashboard > Account Settings > API Keys 에서 생성)
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import requests  # noqa: E402
from secure_store import store_get  # noqa: E402

SERVICE_ID = "srv-ctnepulumphs73d8vb80"
RENDER_API = "https://api.render.com/v1"
HEALTH_URL = "https://bridge-n7hk.onrender.com/health"
MAX_WAIT = 300  # 5분


def check_health() -> dict | None:
    try:
        r = requests.get(HEALTH_URL, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def get_api_key() -> str:
    try:
        return store_get("RENDER_API_KEY")
    except SystemExit:
        print("[render_deploy] RENDER_API_KEY가 설정되지 않았습니다.")
        print("  1) Render Dashboard > Account Settings > API Keys 에서 키 생성")
        print("  2) python tools/secure_store.py set RENDER_API_KEY \"rnd_xxxxxxxxxxxx\"")
        sys.exit(1)


def trigger_deploy():
    # 1. 현재 서버 상태
    print("[render_deploy] 현재 서버 상태 확인...")
    before = check_health()
    if before:
        print(f"  version : {before.get('version', '?')}")
        print(f"  started : {before.get('timestamp', '?')}")
    else:
        print("  서버 응답 없음 (cold start 또는 다운)")

    # 2. API 키 복호화
    api_key = get_api_key()
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

    # 3. 배포 트리거 (Render API)
    print("\n[render_deploy] Render API 배포 트리거...")
    try:
        r = requests.post(
            f"{RENDER_API}/services/{SERVICE_ID}/deploys",
            headers=headers,
            json={"clearCache": "do_not_clear"},
            timeout=30,
        )
        if r.status_code in (200, 201):
            deploy = r.json()
            deploy_id = deploy.get("id", "?")
            print(f"  --> 배포 시작됨 (deploy_id: {deploy_id})")
        else:
            print(f"  --> 실패: HTTP {r.status_code}")
            print(f"  body: {r.text[:300]}")
            sys.exit(1)
    except Exception as e:
        print(f"  --> 요청 실패: {e}")
        sys.exit(1)

    # 4. 배포 상태 폴링
    print(f"\n[render_deploy] 배포 완료 대기 (최대 {MAX_WAIT}초)...")
    start = time.time()

    while time.time() - start < MAX_WAIT:
        time.sleep(15)
        sys.stdout.write(".")
        sys.stdout.flush()

        # Render API로 배포 상태 확인
        try:
            dr = requests.get(
                f"{RENDER_API}/services/{SERVICE_ID}/deploys/{deploy_id}",
                headers=headers,
                timeout=15,
            )
            if dr.status_code == 200:
                status = dr.json().get("status", "")
                if status == "live":
                    elapsed = int(time.time() - start)
                    after = check_health()
                    print(f"\n\n[render_deploy] 배포 완료! ({elapsed}초)")
                    if after:
                        print(f"  version : {after.get('version', '?')}")
                        print(f"  started : {after.get('timestamp', '?')}")
                    return
                elif status in ("build_failed", "update_failed", "canceled", "deactivated"):
                    print(f"\n\n[render_deploy] 배포 실패: status={status}")
                    print(f"  https://dashboard.render.com/web/{SERVICE_ID}/deploys/{deploy_id}")
                    sys.exit(1)
        except Exception:
            pass

    print(f"\n\n[render_deploy] 타임아웃 ({MAX_WAIT}초). 수동 확인:")
    print(f"  https://dashboard.render.com/web/{SERVICE_ID}/deploys")


def show_status():
    print("[render_deploy] 서버 상태 확인...")
    h = check_health()
    if h:
        for k, v in h.items():
            print(f"  {k}: {v}")
    else:
        print("  응답 없음 (cold start 중이거나 다운)")

    # Render API로 최근 배포 정보
    try:
        api_key = get_api_key()
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
        r = requests.get(
            f"{RENDER_API}/services/{SERVICE_ID}/deploys?limit=3",
            headers=headers,
            timeout=15,
        )
        if r.status_code == 200:
            deploys = r.json()
            if deploys:
                print("\n  최근 배포:")
                for d in deploys[:3]:
                    sid = d.get("deploy", d).get("id", d.get("id", "?"))
                    st = d.get("deploy", d).get("status", d.get("status", "?"))
                    ct = d.get("deploy", d).get("createdAt", d.get("createdAt", "?"))
                    print(f"    {sid[:12]}  {st:15s}  {ct[:19]}")
    except SystemExit:
        pass
    except Exception:
        pass


def main():
    if "--status" in sys.argv:
        show_status()
    else:
        trigger_deploy()


if __name__ == "__main__":
    main()
