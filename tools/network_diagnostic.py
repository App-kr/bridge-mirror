#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네트워크 진단 도구 — 공유기 IP 자동 감지 + 상태 확인

사용법:
  python network_diagnostic.py
"""

import subprocess
import socket
import platform
import sys
from pathlib import Path

# Windows UTF-8 처리
if platform.system() == "Windows":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def get_gateway_ip():
    """기본 게이트웨이(공유기 IP) 획득"""
    system = platform.system()

    try:
        if system == "Windows":
            result = subprocess.run(
                ["ipconfig"],
                capture_output=True,
                text=True,
                encoding='cp949',
                errors='replace',
                timeout=5
            )

            for line in result.stdout.split('\n'):
                if '기본 게이트웨이' in line or 'Default Gateway' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        ip = parts[-1].strip()
                        if ip and ip != '(설정 없음)':
                            return ip

        elif system == "Darwin":  # macOS
            result = subprocess.run(
                ["route", "-n", "get", "default"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'gateway' in line.lower():
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[-1]

        elif system == "Linux":
            result = subprocess.run(
                ["ip", "route", "show"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'default via' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        return parts[2]

    except Exception as e:
        print(f"⚠️ 게이트웨이 조회 실패: {e}")

    return None


def get_local_ips():
    """모든 로컬 IP 주소 획득"""
    ips = []

    try:
        hostname = socket.gethostname()
        all_ips = socket.gethostbyname_ex(hostname)

        if len(all_ips) >= 3:
            ips = list(set(all_ips[2]))  # 중복 제거

    except Exception as e:
        print(f"⚠️ 로컬 IP 조회 실패: {e}")

    return ips


def ping_host(ip, timeout=2):
    """호스트 핑 확인"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["ping", "-n", "1", "-w", str(timeout * 1000), ip],
                capture_output=True,
                timeout=timeout + 1
            )
            return result.returncode == 0
        else:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", str(timeout * 1000), ip],
                capture_output=True,
                timeout=timeout + 1
            )
            return result.returncode == 0

    except Exception:
        return False


def check_port(ip, port, timeout=2):
    """특정 포트 접근 가능 확인"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0

    except Exception:
        return False


def main():
    print("🔍 네트워크 진단 도구")
    print("=" * 60)

    # 1. 로컬 IP
    print("\n1️⃣ 로컬 IP 주소:")
    local_ips = get_local_ips()
    if local_ips:
        for ip in local_ips:
            print(f"   ✅ {ip}")
    else:
        print("   ⚠️ 로컬 IP를 찾을 수 없습니다")

    # 2. 게이트웨이(공유기 IP) 자동 감지
    print("\n2️⃣ 공유기 IP (게이트웨이):")
    gateway = get_gateway_ip()

    if gateway:
        print(f"   ✅ {gateway}")
        print(f"\n   브라우저에서 접속: http://{gateway}")

        # 3. 공유기 핑 확인
        print(f"\n3️⃣ 공유기 연결 확인 (ping {gateway}):")
        if ping_host(gateway):
            print(f"   ✅ 공유기 응답 OK")

            # 4. 관리 포트(80/443) 확인
            print(f"\n4️⃣ 공유기 관리 인터페이스:")
            if check_port(gateway, 80):
                print(f"   ✅ HTTP(80) 접속 가능")
                print(f"      → http://{gateway} 에서 로그인")
            elif check_port(gateway, 443):
                print(f"   ✅ HTTPS(443) 접속 가능")
                print(f"      → https://{gateway} 에서 로그인")
            else:
                print(f"   ⚠️ 관리 포트를 찾을 수 없음")
                print(f"      → 공유기 재부팅 시도")

        else:
            print(f"   ❌ 공유기 응답 없음")
            print(f"\n   해결 방법:")
            print(f"   1. 공유기 전원 확인")
            print(f"   2. 공유기 재부팅 (전원 끄고 30초 후 켜기)")
            print(f"   3. 라우터 케이블 연결 확인")
            print(f"   4. PC WiFi/LAN 연결 상태 확인")

    else:
        print("   ⚠️ 게이트웨이를 찾을 수 없습니다")
        print(f"\n   시도 IP 목록:")
        common_ips = ["192.168.1.1", "192.168.0.1", "10.0.0.1", "192.168.100.1"]
        for ip in common_ips:
            print(f"      • {ip}")

        print(f"\n   각 IP 테스트 중...")
        for ip in common_ips:
            if ping_host(ip):
                print(f"   ✅ {ip} 응답 있음 → 이것이 공유기 IP입니다!")
                if check_port(ip, 80) or check_port(ip, 443):
                    print(f"      → http://{ip} 또는 https://{ip} 에서 로그인")
                break

    # 5. 네트워크 권장사항
    print("\n" + "=" * 60)
    print("📋 체크리스트:")
    print("  □ 공유기 전원 켜있음?")
    print("  □ PC가 WiFi/LAN에 연결됨?")
    print("  □ IP 자동 할당(DHCP) 활성화?")
    print("  □ 공유기 기본 IP 확인 (모델별로 다를 수 있음)")
    print("  □ 방화벽이 관리 페이지 차단하고 있지 않은지?")


if __name__ == "__main__":
    main()
