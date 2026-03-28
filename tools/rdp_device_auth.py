#!/usr/bin/env python3
"""
RDP Device Registry 연동 인증 — MAC 기반 이중 검증
세션 27 구현 — 2026-03-27
"""

import json
import subprocess
import socket
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

# 설정 경로
REGISTRY_PATH = Path("Q:/Claudework/bridge base/.device_registry.json")
LOG_PATH = Path("Q:/Claudework/bridge base/logs/rdp_auth.log")

def get_device_mac() -> Optional[str]:
    """현재 연결된 기기의 MAC 주소 반환"""
    try:
        result = subprocess.run(
            ['cmd', '/c', 'getmac'],
            capture_output=True,
            text=True,
            encoding='utf-16-le',
            timeout=5
        )
        # 첫 번째 물리 주소 추출 (하이픈 제거)
        for line in result.stdout.split('\n'):
            if 'Physical Address' in line or '물리적 주소' in line or 'MAC' in line:
                continue
            if line.strip() and '-' in line:
                mac = line.split()[0].upper().replace('-', ':')
                if len(mac) == 17:  # MAC 형식 검증
                    return mac
    except Exception as e:
        log(f"[ERROR] MAC 조회 실패: {e}")
        # 대체 방법: ipconfig 사용
        try:
            result = subprocess.run(
                ['ipconfig', '/all'],
                capture_output=True,
                text=True,
                encoding='cp949',
                timeout=5
            )
            for line in result.stdout.split('\n'):
                if '물리적 주소' in line or 'Physical Address' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        mac = parts[-1].strip().replace('-', ':').upper()
                        if len(mac) == 17:
                            return mac
        except:
            pass
    return None

def get_local_ip() -> Optional[str]:
    """현재 기기의 로컬 IP 주소 반환"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        log(f"[ERROR] 로컬 IP 조회 실패: {e}")
    return None

def load_registry() -> Dict:
    """Device Registry 로드"""
    try:
        with open(REGISTRY_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        log(f"[ERROR] Registry 로드 실패: {e}")
        return {"devices": {}}

def verify_device() -> Tuple[bool, str]:
    """
    현재 기기를 Device Registry로 검증
    반환: (인증 성공/실패, 메시지)
    """
    mac = get_device_mac()
    local_ip = get_local_ip()

    if not mac:
        return False, "MAC 주소를 조회할 수 없습니다"

    registry = load_registry()
    devices = registry.get("devices", {})

    # MAC 주소로 기기 검색
    if mac in devices:
        device = devices[mac]
        device_name = device.get("name", "Unknown")

        # 로컬 IP 검증 (선택)
        registered_ip = device.get("registered_ip")
        if local_ip and registered_ip and local_ip != registered_ip:
            log(f"[WARN] IP 불일치: 등록={registered_ip}, 현재={local_ip}")

        # RDP 세션 환경변수에 설정
        set_rdp_env(device_name, mac, local_ip)

        return True, f"✅ 인증 성공: {device_name} ({mac})"
    else:
        return False, f"❌ 미등록 기기: {mac}"

def set_rdp_env(device_name: str, mac: str, local_ip: Optional[str]) -> None:
    """RDP 세션 환경변수 설정"""
    try:
        # Windows 환경변수 설정 (현재 세션에만)
        subprocess.run(
            f'set RDP_DEVICE_NAME={device_name} && set RDP_DEVICE_MAC={mac}',
            shell=True
        )
        log(f"[INFO] RDP 환경변수 설정: {device_name}")
    except Exception as e:
        log(f"[WARN] RDP 환경변수 설정 실패: {e}")

def log(message: str) -> None:
    """로그 기록"""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        f.write(f"{timestamp} {message}\n")
    print(message)

def main():
    """메인 인증 로직"""
    print("\n" + "="*60)
    print("RDP Device Registry 인증 시스템")
    print("="*60 + "\n")

    success, message = verify_device()
    print(message)

    if not success:
        log(f"[ALERT] RDP 접속 거부: {message}")
        sys.exit(1)

    # 성공 시 RDP 진행
    print("\n[INFO] RDP 연결 준비 완료...")
    print("[INFO] mstsc /v:127.0.0.1:4389 실행 중...\n")

    try:
        subprocess.Popen(['mstsc', '/v:127.0.0.1:4389'])
    except Exception as e:
        log(f"[ERROR] RDP 시작 실패: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
