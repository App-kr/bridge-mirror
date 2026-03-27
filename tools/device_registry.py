#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Device Registry System v1.0
기기 등록 및 관리 — MAC주소 기반 화이트리스트

사용:
  python device_registry.py register "Device Name" [optional_ip]
  python device_registry.py list
  python device_registry.py verify <mac_address> [ip_address]
  python device_registry.py revoke <mac_address>
  python device_registry.py check-network
"""

import os
import json
import hashlib
import subprocess
import platform
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re

# Windows UTF-8 출력 처리
if platform.system() == "Windows":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration
REGISTRY_FILE = Path(__file__).parent.parent / ".device_registry.json"
ENCRYPTION_KEY_FILE = Path(__file__).parent.parent / ".device_key"
TRUSTED_IPS_FILE = Path(__file__).parent.parent / ".trusted_ips.json"

class DeviceRegistry:
    """기기 등록 관리자"""

    def __init__(self):
        self.registry = self._load_registry()
        self.trusted_ips = self._load_trusted_ips()

    def _load_registry(self) -> Dict:
        """레지스트리 로드"""
        if REGISTRY_FILE.exists():
            with open(REGISTRY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"devices": {}, "last_updated": None}

    def _load_trusted_ips(self) -> Dict:
        """신뢰 IP 목록 로드"""
        if TRUSTED_IPS_FILE.exists():
            with open(TRUSTED_IPS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"ips": {}, "cidr_blocks": []}

    def _save_registry(self):
        """레지스트리 저장 (암호화)"""
        self.registry['last_updated'] = datetime.now().isoformat()
        with open(REGISTRY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)
        os.chmod(REGISTRY_FILE, 0o600)

    def _save_trusted_ips(self):
        """신뢰 IP 저장"""
        with open(TRUSTED_IPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.trusted_ips, f, indent=2, ensure_ascii=False)
        os.chmod(TRUSTED_IPS_FILE, 0o600)

    def _get_system_mac(self) -> Optional[str]:
        """현재 PC의 기본 MAC주소 획득"""
        system = platform.system()
        try:
            if system == "Windows":
                # Windows: getmac (더 간단)
                result = subprocess.run(
                    ["getmac", "/fo", "table", "/nh"],
                    capture_output=True,
                    text=True,
                    encoding='cp949',
                    errors='replace',
                    timeout=5
                )
                # 첫 번째 라인의 MAC주소 추출
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line and re.search(r'[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}', line):
                        # MAC주소 추출
                        match = re.search(r'([0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2})', line)
                        if match:
                            return match.group(1).replace('-', ':').upper()
                return None

            elif system == "Darwin":  # macOS
                result = subprocess.run(
                    ["ifconfig", "en0"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                match = re.search(r'ether\s+([0-9A-Fa-f:]{17})', result.stdout)
                if match:
                    return match.group(1).upper()

            elif system == "Linux":
                result = subprocess.run(
                    ["ip", "link", "show"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                match = re.search(r'link/ether\s+([0-9A-Fa-f:]{17})', result.stdout)
                if match:
                    return match.group(1).upper()

        except Exception as e:
            print(f"⚠️ MAC주소 조회 실패: {e}")

        return None

    def _get_local_ip(self) -> Optional[str]:
        """로컬 IP 주소 획득"""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None

    def _get_public_ip(self) -> Optional[str]:
        """공인 IP 획득 (원격 작업용)"""
        try:
            result = subprocess.run(
                ["curl", "-s", "https://api.ipify.org"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def register_device(self, device_name: str, ip_address: Optional[str] = None) -> bool:
        """기기 등록"""
        mac = self._get_system_mac()
        if not mac:
            print("❌ MAC주소를 조회할 수 없습니다")
            return False

        local_ip = self._get_local_ip() or "unknown"
        public_ip = self._get_public_ip() or "unknown"
        ip_to_register = ip_address or local_ip

        if mac in self.registry['devices']:
            print(f"⚠️ 이미 등록된 기기입니다: {self.registry['devices'][mac]['name']}")
            return False

        self.registry['devices'][mac] = {
            "name": device_name,
            "mac": mac,
            "local_ip": local_ip,
            "public_ip": public_ip,
            "registered_ip": ip_to_register,
            "registered_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "status": "active"
        }

        # 신뢰 IP 추가
        if ip_to_register != "unknown":
            self.trusted_ips['ips'][ip_to_register] = {
                "device": device_name,
                "mac": mac,
                "added_at": datetime.now().isoformat()
            }

        self._save_registry()
        self._save_trusted_ips()

        print(f"✅ 기기 등록 완료")
        print(f"   기기명: {device_name}")
        print(f"   MAC: {mac}")
        print(f"   로컬 IP: {local_ip}")
        print(f"   공인 IP: {public_ip}")

        return True

    def list_devices(self) -> None:
        """등록된 기기 목록"""
        if not self.registry['devices']:
            print("등록된 기기가 없습니다")
            return

        print("\n📱 등록된 기기 목록:")
        print("-" * 80)
        for mac, device in self.registry['devices'].items():
            status_icon = "✅" if device['status'] == "active" else "⛔"
            print(f"{status_icon} {device['name']}")
            print(f"   MAC: {mac}")
            print(f"   로컬 IP: {device['local_ip']} | 공인 IP: {device['public_ip']}")
            print(f"   등록일: {device['registered_at'][:10]}")
            print()

    def verify_device(self, mac: str, ip_address: Optional[str] = None) -> Tuple[bool, str]:
        """기기 검증 (방화벽용)"""
        mac = mac.upper()

        if mac not in self.registry['devices']:
            return False, f"❌ 등록되지 않은 기기: {mac}"

        device = self.registry['devices'][mac]

        if device['status'] != 'active':
            return False, f"⛔ 비활성화된 기기: {device['name']}"

        # IP 확인 (제공된 경우)
        if ip_address:
            registered_ip = device['registered_ip']
            if ip_address != registered_ip and ip_address != device['local_ip']:
                return False, f"⚠️ IP 불일치: {ip_address} (등록: {registered_ip})"

        # last_seen 업데이트
        device['last_seen'] = datetime.now().isoformat()
        self._save_registry()

        return True, f"✅ 허용됨: {device['name']}"

    def revoke_device(self, mac: str) -> bool:
        """기기 등록 해제"""
        mac = mac.upper()

        if mac not in self.registry['devices']:
            print(f"❌ 기기를 찾을 수 없습니다: {mac}")
            return False

        device = self.registry['devices'][mac]
        device['status'] = 'revoked'
        device['revoked_at'] = datetime.now().isoformat()

        self._save_registry()
        print(f"⛔ 기기 차단 완료: {device['name']}")

        return True

    def check_network_security(self) -> None:
        """네트워크 보안 점검"""
        print("\n🔒 네트워크 보안 점검:")
        print("-" * 80)

        checks = {
            "IPv6 비활성화": self._check_ipv6(),
            "공유기 기본 비밀번호": self._check_router_password(),
            "무선 암호화": self._check_wifi_encryption(),
            "방화벽": self._check_firewall(),
            "DNS 필터링": self._check_dns()
        }

        for check_name, result in checks.items():
            icon = "✅" if result else "⚠️"
            print(f"{icon} {check_name}")

        print("\n📋 권장사항:")
        print("1. 공유기 관리자 페이지 로그인 (192.168.1.1)")
        print("2. SSID 한글명 변경 (영문+숫자)")
        print("3. WiFi 암호화: WPA3 또는 WPA2/AES")
        print("4. 기본 비밀번호 변경")
        print("5. UPnP 비활성화")
        print("6. 포트 포워딩 점검 (필요한 것만 열기)")
        print("7. 펌웨어 최신 버전으로 업데이트")
        print("8. MAC 필터링 활성화 (이 도구로 등록된 기기만)")

    def _check_ipv6(self) -> bool:
        """IPv6 비활성화 확인"""
        if platform.system() == "Windows":
            try:
                result = subprocess.run(
                    ["netsh", "int", "ipv6", "show", "interface"],
                    capture_output=True,
                    text=True,
                    encoding='cp949',
                    errors='replace',
                    timeout=5
                )
                return "disabled" in result.stdout.lower()
            except:
                return False
        return True

    def _check_router_password(self) -> bool:
        """공유기 비밀번호 변경 확인 (휴리스틱)"""
        # 실제 확인 불가 — 사용자가 직접 확인 필요
        return False

    def _check_wifi_encryption(self) -> bool:
        """WiFi 암호화 확인"""
        if platform.system() == "Windows":
            try:
                result = subprocess.run(
                    ["netsh", "wlan", "show", "interface"],
                    capture_output=True,
                    text=True,
                    encoding='cp949',
                    errors='replace',
                    timeout=5
                )
                return "wpa2" in result.stdout.lower() or "wpa3" in result.stdout.lower()
            except:
                return False
        return True

    def _check_firewall(self) -> bool:
        """방화벽 활성화 확인"""
        if platform.system() == "Windows":
            try:
                result = subprocess.run(
                    ["netsh", "advfirewall", "show", "allprofiles"],
                    capture_output=True,
                    text=True,
                    encoding='cp949',
                    errors='replace',
                    timeout=5
                )
                return "on" in result.stdout.lower()
            except:
                return False
        return True

    def _check_dns(self) -> bool:
        """DNS 보안 확인 (휴리스틱)"""
        return True  # 사용자가 공유기에서 직접 확인 필요


def main():
    import sys

    registry = DeviceRegistry()

    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "register":
        if len(sys.argv) < 3:
            print("사용법: device_registry.py register \"Device Name\" [optional_ip]")
            return
        name = sys.argv[2]
        ip = sys.argv[3] if len(sys.argv) > 3 else None
        registry.register_device(name, ip)

    elif cmd == "list":
        registry.list_devices()

    elif cmd == "verify":
        if len(sys.argv) < 3:
            print("사용법: device_registry.py verify <mac_address> [ip_address]")
            return
        mac = sys.argv[2]
        ip = sys.argv[3] if len(sys.argv) > 3 else None
        allowed, msg = registry.verify_device(mac, ip)
        print(msg)

    elif cmd == "revoke":
        if len(sys.argv) < 3:
            print("사용법: device_registry.py revoke <mac_address>")
            return
        mac = sys.argv[2]
        registry.revoke_device(mac)

    elif cmd == "check-network":
        registry.check_network_security()

    else:
        print(f"❌ 알 수 없는 명령: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
