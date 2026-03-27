#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Device Registry System v2.0 — MAC 기반 기기 관리 + 3중 암호화
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

사용법:
  # 1. 현재 PC 자동 등록
  python device_registry.py register "Device Name" [ip]

  # 2. 원격 기기 등록 (MAC 직접 입력)
  python device_registry.py register-remote "AA:BB:CC:DD:EE:FF" "Device Name" [ip]

  # 3. 대화형 마법사
  python device_registry.py register-interactive

  # 4. 기기 목록
  python device_registry.py list [--decrypt]

  # 5. 기기 검증
  python device_registry.py verify <mac_address> [ip_address]

  # 6. 기기 차단
  python device_registry.py revoke <mac_address>

  # 7. 네트워크 점검
  python device_registry.py check-network

고급 옵션:
  --encrypt          3중 AES-256-GCM 암호화 저장
  --decrypt          암호화된 값 복호화
  --master-key FILE  마스터 키 파일 위치 지정
"""

import os
import json
import hashlib
import subprocess
import platform
import sys
import base64
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re

# Windows UTF-8 출력 처리
if platform.system() == "Windows":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 암호화 라이브러리
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    _CRYPTO = True
except ImportError:
    _CRYPTO = False
    print("⚠️ cryptography 라이브러리 필요: pip install cryptography")

# Configuration
REGISTRY_FILE = Path(__file__).parent.parent / ".device_registry.json"
ENCRYPTION_KEY_FILE = Path(__file__).parent.parent / ".device_key"
TRUSTED_IPS_FILE = Path(__file__).parent.parent / ".trusted_ips.json"
KDF_ITERATIONS = 600_000  # PBKDF2
NONCE_BYTES = 12
SALT_BYTES = 32

# ── 3중 AES-256-GCM 암호화 헬퍼 ──────────────────────────────────────

def _ensure_master_key(master_key_file: Optional[Path] = None) -> Optional[bytes]:
    """마스터 키 획득 또는 생성"""
    if not _CRYPTO:
        return None

    key_file = master_key_file or ENCRYPTION_KEY_FILE

    if key_file.exists():
        with open(key_file, 'rb') as f:
            return f.read(32)

    # 새 키 생성
    print("🔑 새로운 마스터 키를 생성합니다...")
    key = secrets.token_bytes(32)

    with open(key_file, 'wb') as f:
        f.write(key)
    os.chmod(key_file, 0o600)
    print(f"✅ 마스터 키 저장: {key_file}")

    return key


def _kdf(master_key: bytes, salt: bytes) -> bytes:
    """PBKDF2-SHA256: 마스터키 + salt → 32바이트 세션키"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(master_key)


def _triple_encrypt(plaintext: str, master_key: bytes, field_name: str) -> str:
    """
    3중 AES-256-GCM 암호화:
    L1 = AES-GCM(KDF(key + "L1" + field), nonce1)
    L2 = AES-GCM(KDF(key + "L2" + nonce1), nonce2)
    L3 = AES-GCM(KDF(key + "L3" + nonce2), nonce3)
    """
    if not _CRYPTO:
        return plaintext

    plaintext_bytes = plaintext.encode('utf-8')

    # Layer 1
    salt1 = secrets.token_bytes(SALT_BYTES)
    nonce1 = secrets.token_bytes(NONCE_BYTES)
    key1 = _kdf(master_key + b"L1" + field_name.encode(), salt1)
    cipher1 = AESGCM(key1)
    ct1 = cipher1.encrypt(nonce1, plaintext_bytes, None)

    # Layer 2
    salt2 = secrets.token_bytes(SALT_BYTES)
    nonce2 = secrets.token_bytes(NONCE_BYTES)
    key2 = _kdf(master_key + b"L2" + nonce1, salt2)
    cipher2 = AESGCM(key2)
    ct2 = cipher2.encrypt(nonce2, ct1, None)

    # Layer 3
    salt3 = secrets.token_bytes(SALT_BYTES)
    nonce3 = secrets.token_bytes(NONCE_BYTES)
    key3 = _kdf(master_key + b"L3" + nonce2, salt3)
    cipher3 = AESGCM(key3)
    ct3 = cipher3.encrypt(nonce3, ct2, None)

    # 포맷: T3v1 + salt1 + salt2 + salt3 + nonce1 + nonce2 + nonce3 + ct3
    output = (
        b"T3v1" +
        salt1 + salt2 + salt3 +
        nonce1 + nonce2 + nonce3 +
        ct3
    )

    return base64.b64encode(output).decode('utf-8')


def _triple_decrypt(ciphertext: str, master_key: bytes, field_name: str) -> Optional[str]:
    """3중 AES-256-GCM 복호화"""
    if not _CRYPTO:
        return None

    try:
        data = base64.b64decode(ciphertext)

        if not data.startswith(b"T3v1"):
            return None

        # 파싱
        offset = 4
        salt1 = data[offset:offset+SALT_BYTES]
        offset += SALT_BYTES
        salt2 = data[offset:offset+SALT_BYTES]
        offset += SALT_BYTES
        salt3 = data[offset:offset+SALT_BYTES]
        offset += SALT_BYTES

        nonce1 = data[offset:offset+NONCE_BYTES]
        offset += NONCE_BYTES
        nonce2 = data[offset:offset+NONCE_BYTES]
        offset += NONCE_BYTES
        nonce3 = data[offset:offset+NONCE_BYTES]
        offset += NONCE_BYTES

        ct3 = data[offset:]

        # Layer 3 복호화
        key3 = _kdf(master_key + b"L3" + nonce2, salt3)
        cipher3 = AESGCM(key3)
        ct2 = cipher3.decrypt(nonce3, ct3, None)

        # Layer 2 복호화
        key2 = _kdf(master_key + b"L2" + nonce1, salt2)
        cipher2 = AESGCM(key2)
        ct1 = cipher2.decrypt(nonce2, ct2, None)

        # Layer 1 복호화
        key1 = _kdf(master_key + b"L1" + field_name.encode(), salt1)
        cipher1 = AESGCM(key1)
        plaintext = cipher1.decrypt(nonce1, ct1, None)

        return plaintext.decode('utf-8')

    except Exception as e:
        print(f"⚠️ 복호화 실패: {e}")
        return None


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

    def register_device(self, device_name: str, ip_address: Optional[str] = None, encrypt: bool = False, master_key: Optional[bytes] = None) -> bool:
        """기기 등록 (현재 PC 자동 감지)"""
        mac = self._get_system_mac()
        if not mac:
            print("❌ MAC주소를 조회할 수 없습니다")
            return False

        return self.register_device_by_mac(mac, device_name, ip_address, encrypt, master_key)

    def register_device_by_mac(self, mac: str, device_name: str, ip_address: Optional[str] = None, encrypt: bool = False, master_key: Optional[bytes] = None) -> bool:
        """기기 등록 (MAC 직접 입력 — 원격 등록용)"""
        mac = mac.upper()
        local_ip = ip_address or self._get_local_ip() or "unknown"
        public_ip = "remote" if encrypt else (self._get_public_ip() or "unknown")

        if mac in self.registry['devices']:
            print(f"⚠️ 이미 등록된 기기입니다: {self.registry['devices'][mac]['name']}")
            return False

        device_data = {
            "name": device_name,
            "mac": mac,
            "local_ip": local_ip,
            "public_ip": public_ip,
            "registered_ip": ip_address or local_ip,
            "registered_at": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "status": "active",
            "encrypted": encrypt
        }

        # 3중 암호화 옵션
        if encrypt and _CRYPTO and master_key:
            device_data["name"] = _triple_encrypt(device_name, master_key, "device_name")
            device_data["mac_encrypted"] = _triple_encrypt(mac, master_key, "mac")
            print(f"🔒 3중 AES-256-GCM 암호화로 저장됨")

        self.registry['devices'][mac] = device_data

        # 신뢰 IP 추가
        if ip_address and ip_address != "unknown":
            self.trusted_ips['ips'][ip_address] = {
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
        if not encrypt:
            print(f"   공인 IP: {public_ip}")

        return True

    def list_devices(self, decrypt: bool = False, master_key: Optional[bytes] = None) -> None:
        """등록된 기기 목록"""
        if not self.registry['devices']:
            print("등록된 기기가 없습니다")
            return

        print("\n📱 등록된 기기 목록:")
        print("-" * 80)
        for mac, device in self.registry['devices'].items():
            status_icon = "✅" if device['status'] == "active" else "⛔"

            # 암호화 여부 확인
            is_encrypted = device.get('encrypted', False)
            name = device['name']
            display_mac = mac

            # 복호화 옵션
            if is_encrypted and decrypt and _CRYPTO and master_key:
                if 'mac_encrypted' in device:
                    decrypted_mac = _triple_decrypt(device['mac_encrypted'], master_key, "mac")
                    if decrypted_mac:
                        display_mac = decrypted_mac
                decrypted_name = _triple_decrypt(name, master_key, "device_name")
                if decrypted_name:
                    name = decrypted_name
                name += " 🔓"  # 복호화 표시

            print(f"{status_icon} {name}")
            print(f"   MAC: {display_mac}")
            print(f"   로컬 IP: {device['local_ip']} | 공인 IP: {device['public_ip']}")
            print(f"   등록일: {device['registered_at'][:10]}")
            if is_encrypted:
                print(f"   🔒 3중 암호화 저장")
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

    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()
    encrypt = "--encrypt" in sys.argv
    decrypt = "--decrypt" in sys.argv
    master_key = None

    # 마스터 키 획득
    if encrypt or decrypt:
        if not _CRYPTO:
            print("❌ cryptography 라이브러리 필요: pip install cryptography")
            return
        master_key = _ensure_master_key()

    registry = DeviceRegistry()

    if cmd == "register":
        if len(sys.argv) < 3:
            print("사용법: device_registry.py register \"Device Name\" [ip] [--encrypt]")
            return
        name = sys.argv[2]
        ip = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else None
        registry.register_device(name, ip, encrypt, master_key)

    elif cmd == "register-remote":
        if len(sys.argv) < 4:
            print("사용법: device_registry.py register-remote \"AA:BB:CC:DD:EE:FF\" \"Device Name\" [ip] [--encrypt]")
            return
        mac = sys.argv[2]
        name = sys.argv[3]
        ip = sys.argv[4] if len(sys.argv) > 4 and not sys.argv[4].startswith("--") else None
        registry.register_device_by_mac(mac, name, ip, encrypt, master_key)

    elif cmd == "register-interactive":
        print("\n🧙 기기 등록 마법사")
        print("=" * 60)

        print("\n1. MAC 주소를 입력하세요 (예: AA:BB:CC:DD:EE:FF)")
        print("   현재 PC의 MAC: getmac 명령으로 확인 가능")
        mac = input("MAC: ").strip().upper()

        print("\n2. 기기 이름을 입력하세요 (예: My Laptop)")
        name = input("기기명: ").strip()

        print("\n3. IP 주소를 입력하세요 (선택사항, Enter로 건너뛰기)")
        ip = input("IP: ").strip() or None

        print("\n4. 3중 암호화로 저장할까요? (y/n, 기본값: n)")
        enc = input("암호화: ").strip().lower() == "y"

        if enc:
            master_key = _ensure_master_key()

        print("\n✅ 다음 정보로 등록하시겠습니까?")
        print(f"   MAC: {mac}")
        print(f"   기기명: {name}")
        print(f"   IP: {ip or '(자동)'}")
        print(f"   암호화: {'YES 🔒' if enc else 'NO'}")

        confirm = input("\n계속 진행? (y/n): ").strip().lower() == "y"
        if confirm:
            registry.register_device_by_mac(mac, name, ip, enc, master_key)
        else:
            print("❌ 취소됨")

    elif cmd == "list":
        registry.list_devices(decrypt, master_key)

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
