# ddns_watchdog.py
# Bridge DDNS Watchdog — 외부 IP 변경 감지 + Cloudflare DNS 자동 갱신
# 5분마다 폴링. IP 변경 감지 시:
#   1. Cloudflare DNS A 레코드 자동 업데이트
#   2. 세션 전체 강제 만료 (보안)
#   3. 키 교체 트리거 (선택)
#   4. Telegram/이메일 알람
# 실행: python ddns_watchdog.py
# 또는 Windows Task Scheduler로 시작시 자동 실행

import os
import time
import json
import logging
import requests
import threading
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DDNS] %(message)s",
    handlers=[
        logging.FileHandler("ddns_watchdog.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
)

# ─── 설정 (모두 환경변수에서 읽음) ──────────────────────────────────────
CF_API_TOKEN    = os.environ.get("CF_API_TOKEN", "")       # Cloudflare API Token
CF_ZONE_ID      = os.environ.get("CF_ZONE_ID", "")        # Cloudflare Zone ID
CF_RECORD_NAME  = os.environ.get("CF_RECORD_NAME", "")    # 예: bridge.example.com
TG_BOT_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "") # Telegram 알람
TG_CHAT_ID      = os.environ.get("TELEGRAM_CHAT_ID", "")
POLL_INTERVAL   = int(os.environ.get("DDNS_POLL_INTERVAL", "300"))  # 초 (기본 5분)
ROTATE_ON_IP_CHANGE = os.environ.get("DDNS_ROTATE_KEYS", "true").lower() == "true"

IP_CACHE_FILE = Path("ddns_last_ip.txt")
IP_SOURCES = [
    "https://api.ipify.org?format=json",
    "https://api.my-ip.io/ip.json",
    "https://checkip.amazonaws.com",
]


# ─── 외부 IP 조회 (복수 소스 failover) ──────────────────────────────────
def get_external_ip() -> str:
    for source in IP_SOURCES:
        try:
            resp = requests.get(source, timeout=5)
            if resp.status_code == 200:
                text = resp.text.strip()
                # JSON 응답 처리
                try:
                    data = resp.json()
                    ip = data.get("ip") or data.get("address") or data.get("query")
                    if ip:
                        return ip.strip()
                except Exception:
                    pass
                # 평문 IP
                if "." in text and len(text) < 20:
                    return text
        except Exception as e:
            logging.warning(f"IP source {source} failed: {e}")
    raise RuntimeError("모든 IP 소스 실패. 네트워크 확인 필요.")


# ─── Cloudflare DNS 업데이트 ─────────────────────────────────────────────
def get_cf_record_id() -> str:
    """현재 DNS A 레코드의 Cloudflare record_id 조회."""
    url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records"
    headers = {"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"}
    params = {"type": "A", "name": CF_RECORD_NAME}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    records = resp.json().get("result", [])
    if not records:
        raise ValueError(f"DNS 레코드 없음: {CF_RECORD_NAME}")
    return records[0]["id"]


def update_cloudflare_dns(new_ip: str) -> bool:
    if not CF_API_TOKEN or not CF_ZONE_ID or not CF_RECORD_NAME:
        logging.warning("[DDNS] Cloudflare 환경변수 미설정. DNS 업데이트 건너뜀.")
        return False
    try:
        record_id = get_cf_record_id()
        url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records/{record_id}"
        headers = {"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"}
        payload = {"type": "A", "name": CF_RECORD_NAME, "content": new_ip, "ttl": 60, "proxied": True}
        resp = requests.put(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        logging.info(f"[DDNS] Cloudflare DNS 업데이트 완료: {CF_RECORD_NAME} → {new_ip}")
        return True
    except Exception as e:
        logging.error(f"[DDNS] Cloudflare 업데이트 실패: {e}")
        return False


# ─── Telegram 알람 ───────────────────────────────────────────────────────
def send_telegram_alert(message: str) -> None:
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TG_CHAT_ID, "text": f"[Bridge DDNS]\n{message}"}, timeout=5)
    except Exception as e:
        logging.warning(f"[DDNS] Telegram 알람 실패: {e}")


# ─── IP 변경 처리 ────────────────────────────────────────────────────────
def on_ip_changed(old_ip: str, new_ip: str) -> None:
    logging.warning(f"[DDNS] IP 변경 감지: {old_ip} → {new_ip}")

    # 1. Cloudflare DNS 업데이트
    dns_ok = update_cloudflare_dns(new_ip)

    # 2. 세션 전체 강제 만료
    try:
        from security_hardened import session_binding
        count = session_binding.revoke_all()
        logging.warning(f"[DDNS] IP 변경으로 인해 {count}개 세션 강제 만료.")
    except Exception as e:
        logging.error(f"[DDNS] 세션 만료 실패: {e}")

    # 3. 키 교체 트리거 (설정에 따라)
    if ROTATE_ON_IP_CHANGE:
        try:
            from security_vault import get_vault
            vault = get_vault()
            vault.force_rotate(reason=f"ip_changed:{old_ip}_to_{new_ip}")
            logging.warning("[DDNS] IP 변경으로 인해 3중 키 교체 완료.")
        except Exception as e:
            logging.error(f"[DDNS] 키 교체 실패: {e}")

    # 4. Telegram 알람
    msg = (
        f"⚠️ 공유기 IP 변경 감지\n"
        f"이전: {old_ip}\n"
        f"현재: {new_ip}\n"
        f"DNS 갱신: {'완료' if dns_ok else '실패'}\n"
        f"세션: 전체 만료됨\n"
        f"키 교체: {'완료' if ROTATE_ON_IP_CHANGE else '건너뜀'}\n"
        f"시각: {datetime.utcnow().isoformat()}Z"
    )
    send_telegram_alert(msg)

    # 5. 캐시 파일 업데이트
    IP_CACHE_FILE.write_text(new_ip)


# ─── 메인 폴링 루프 ──────────────────────────────────────────────────────
def run_watchdog() -> None:
    logging.info(f"[DDNS] Watchdog 시작. 폴링 간격: {POLL_INTERVAL}초")

    # 초기 IP 로드
    last_ip = IP_CACHE_FILE.read_text().strip() if IP_CACHE_FILE.exists() else ""
    if last_ip:
        logging.info(f"[DDNS] 마지막 알려진 IP: {last_ip}")

    while True:
        try:
            current_ip = get_external_ip()
            if not last_ip:
                logging.info(f"[DDNS] 초기 IP 설정: {current_ip}")
                IP_CACHE_FILE.write_text(current_ip)
                last_ip = current_ip
                update_cloudflare_dns(current_ip)
            elif current_ip != last_ip:
                on_ip_changed(last_ip, current_ip)
                last_ip = current_ip
            else:
                logging.debug(f"[DDNS] IP 변화 없음: {current_ip}")
        except Exception as e:
            logging.error(f"[DDNS] 폴링 오류: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_watchdog()
