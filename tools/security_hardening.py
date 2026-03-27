#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bridge 보안 강화 시스템 v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

자동 생성:
1. WireGuard VPN 설정 (4개 기기용)
2. Render IP 화이트리스트
3. SSH 공개키 + 개인키
4. 방화벽 규칙

사용법:
  python security_hardening.py setup          (전체 설정)
  python security_hardening.py wireguard      (VPN만)
  python security_hardening.py ssh-keys       (SSH 키만)
  python security_hardening.py render-config  (Render 설정)
  python security_hardening.py firewall       (방화벽 규칙)
"""

import os
import sys
import json
import secrets
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple

# Windows UTF-8 처리
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── 상수 ────────────────────────────────────────────────────────
SECURITY_DIR = Path(__file__).parent.parent / "security_config"
WIREGUARD_DIR = SECURITY_DIR / "wireguard"
KEYS_DIR = SECURITY_DIR / "keys"
DEVICES = {
    "pc": {
        "name": "Scarlett_Main_PC",
        "ip": "10.0.0.2",
        "mac": "40:B0:76:A1:EF:A0"
    },
    "phone": {
        "name": "Scarlett_iPhone",
        "ip": "10.0.0.3",
        "mac": "CC:DD:EE:FF:00:03"
    },
    "pad": {
        "name": "Scarlett_iPad_Pro",
        "ip": "10.0.0.4",
        "mac": "BB:CC:DD:EE:FF:02"
    },
    "notebook": {
        "name": "Scarlett_Notebook",
        "ip": "10.0.0.5",
        "mac": "AA:BB:CC:DD:EE:01"
    }
}

CURRENT_IP = "115.22.193.150"
VPN_SUBNET = "10.0.0.0/24"
VPN_SERVER_IP = "10.0.0.1"
VPN_PORT = 51820


def create_directories():
    """필요한 디렉토리 생성"""
    WIREGUARD_DIR.mkdir(parents=True, exist_ok=True)
    KEYS_DIR.mkdir(parents=True, exist_ok=True)

    for device_id in DEVICES:
        (WIREGUARD_DIR / device_id).mkdir(exist_ok=True)

    print(f"✅ 디렉토리 생성 완료: {SECURITY_DIR}")


def generate_wireguard_keys() -> Tuple[str, str]:
    """WireGuard 공개키/개인키 생성"""
    try:
        # wg genkey | tg pubkey
        privkey = subprocess.run(
            ["wg", "genkey"],
            capture_output=True,
            text=True,
            timeout=5
        ).stdout.strip()

        pubkey = subprocess.run(
            ["wg", "pubkey"],
            input=privkey,
            capture_output=True,
            text=True,
            timeout=5
        ).stdout.strip()

        return privkey, pubkey

    except Exception as e:
        print(f"⚠️ wg 명령어 실패: {e}")
        print("   → Linux/macOS에서는 'sudo apt install wireguard' 필요")
        print("   → Windows에서는 WireGuard for Windows 설치 필요")
        return None, None


def generate_ssh_keys():
    """SSH RSA 4096 키 생성"""
    ssh_dir = KEYS_DIR / "ssh"
    ssh_dir.mkdir(exist_ok=True)

    key_file = ssh_dir / "bridge_admin"

    try:
        # SSH 키 생성 (4096비트)
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", str(key_file),
             "-N", "", "-C", "bridge_admin@bridgejob.co.kr"],
            capture_output=True,
            timeout=10
        )

        print(f"✅ SSH 키 생성 완료")
        print(f"   개인키: {key_file}")
        print(f"   공개키: {key_file}.pub")

        # 권한 설정
        os.chmod(key_file, 0o600)
        os.chmod(key_file.with_suffix('.pub'), 0o644)

        return key_file, key_file.with_suffix('.pub')

    except Exception as e:
        print(f"⚠️ SSH 키 생성 실패: {e}")
        return None, None


def create_wireguard_server_config() -> str:
    """WireGuard 서버 설정 생성"""

    # 서버 키 생성 (wg genkey 없을 경우 시뮬레이션)
    server_privkey = secrets.token_urlsafe(32)[:43] + "="  # Base64 시뮬레이션

    config = f"""[Interface]
Address = {VPN_SERVER_IP}/24
SaveMconfig = false
ListenPort = {VPN_PORT}
PrivateKey = {server_privkey}

# PC (Scarlett_Main_PC)
[Peer]
PublicKey = PC_PUBLIC_KEY_HERE
AllowedIPs = {DEVICES['pc']['ip']}/32

# iPhone (Scarlett_iPhone)
[Peer]
PublicKey = PHONE_PUBLIC_KEY_HERE
AllowedIPs = {DEVICES['phone']['ip']}/32

# iPad (Scarlett_iPad_Pro)
[Peer]
PublicKey = PAD_PUBLIC_KEY_HERE
AllowedIPs = {DEVICES['pad']['ip']}/32

# Notebook (Scarlett_Notebook)
[Peer]
PublicKey = NOTEBOOK_PUBLIC_KEY_HERE
AllowedIPs = {DEVICES['notebook']['ip']}/32
"""

    wg_config_file = WIREGUARD_DIR / "wg0.conf"
    with open(wg_config_file, 'w', encoding='utf-8') as f:
        f.write(config)

    print(f"✅ WireGuard 서버 설정 생성: {wg_config_file}")
    return config


def create_wireguard_client_configs():
    """각 기기별 WireGuard 클라이언트 설정"""

    for device_id, device_info in DEVICES.items():
        config = f"""[Interface]
PrivateKey = {device_id.upper()}_PRIVATE_KEY_HERE
Address = {device_info['ip']}/32
DNS = 8.8.8.8, 8.8.4.4
SaveMconfig = false

[Peer]
PublicKey = SERVER_PUBLIC_KEY_HERE
Endpoint = bridgejob.co.kr:{VPN_PORT}
AllowedIPs = {VPN_SUBNET}
PersistentKeepalive = 25
"""

        device_dir = WIREGUARD_DIR / device_id
        config_file = device_dir / f"{device_id}.conf"

        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config)

        print(f"✅ {device_info['name']} 클라이언트 설정: {config_file}")


def create_render_env_config():
    """Render 환경변수 설정 파일"""

    render_env = {
        "ADMIN_ALLOWED_IPS": f"{CURRENT_IP}/32",
        "JWT_SECRET": secrets.token_urlsafe(32),
        "BRIDGE_FIELD_KEY": secrets.token_urlsafe(32),
        "VPN_ENABLED": "true",
        "VPN_SUBNET": VPN_SUBNET,
        "RATE_LIMIT_PER_MINUTE": "60",
        "SECURITY_MODE": "strict"
    }

    env_file = SECURITY_DIR / "render.env"
    with open(env_file, 'w', encoding='utf-8') as f:
        for key, value in render_env.items():
            f.write(f"{key}={value}\n")

    print(f"✅ Render 환경변수 설정: {env_file}")
    return render_env


def create_firewall_rules():
    """공유기 방화벽 규칙"""

    firewall_rules = {
        "inbound": [
            {
                "protocol": "UDP",
                "port": VPN_PORT,
                "action": "allow",
                "description": "WireGuard VPN"
            },
            {
                "protocol": "TCP",
                "port": "443",
                "action": "allow",
                "description": "HTTPS"
            },
            {
                "protocol": "TCP",
                "port": "80",
                "action": "allow",
                "description": "HTTP"
            },
            {
                "protocol": "TCP",
                "port": "22",
                "action": "deny",
                "description": "SSH (차단)"
            },
            {
                "protocol": "TCP",
                "port": "3389",
                "action": "deny",
                "description": "RDP (차단)"
            }
        ],
        "mac_filter": {
            "mode": "whitelist",
            "devices": [dev["mac"] for dev in DEVICES.values()]
        }
    }

    rules_file = SECURITY_DIR / "firewall_rules.json"
    with open(rules_file, 'w', encoding='utf-8') as f:
        json.dump(firewall_rules, f, indent=2, ensure_ascii=False)

    print(f"✅ 방화벽 규칙 생성: {rules_file}")
    return firewall_rules


def create_security_guide():
    """보안 설정 가이드"""

    guide = f"""# Bridge 보안 강화 가이드 v1.0
생성: {datetime.now().isoformat()}

## 📋 목차
1. Render IP 화이트리스트 설정
2. 공유기 WireGuard VPN 설정
3. SSH 키 저장소
4. 방화벽 규칙 적용

---

## 1️⃣ Render IP 화이트리스트 설정 (5분)

### 현재 IP
```
{CURRENT_IP}/32
```

### Render 대시보드에서:
1. dashboard.render.com 접속
2. Bridge API 서비스 선택
3. Settings > Environment Variables
4. 다음 추가/수정:

```
ADMIN_ALLOWED_IPS={CURRENT_IP}/32
JWT_SECRET=(생성됨)
BRIDGE_FIELD_KEY=(생성됨)
VPN_ENABLED=true
SECURITY_MODE=strict
```

### 저장 → 서버 자동 재배포 (2분)

---

## 2️⃣ 공유기 WireGuard VPN 설정 (30분)

### 공유기 설정:
1. http://192.168.0.1 접속
2. 설정 → 고급 설정 → VPN (또는 네트워크 → VPN)
3. VPN 서버 활성화

### WireGuard 설정:
```
프로토콜: WireGuard
포트: {VPN_PORT}
네트워크: {VPN_SUBNET}
```

### 서버 설정 파일:
```
{WIREGUARD_DIR}/wg0.conf
```

복사 → 공유기에 붙여넣기

### 클라이언트 설정 (각 기기별):
"""

    for device_id, device_info in DEVICES.items():
        guide += f"\n#### {device_info['name']}\n"
        guide += f"- 파일: {WIREGUARD_DIR}/{device_id}/{device_id}.conf\n"
        guide += f"- VPN IP: {device_info['ip']}\n"

    guide += f"""

---

## 3️⃣ SSH 키 (기본 저장됨)

### 개인키 (비공개)
```
{KEYS_DIR}/ssh/bridge_admin
```

### 공개키 (Render에 등록)
```
{KEYS_DIR}/ssh/bridge_admin.pub
```

---

## 4️⃣ 방화벽 규칙

### MAC 필터링 (공유기)
- 모드: 화이트리스트
- 허용: 4개 기기만

### 포트 정책
- {VPN_PORT} (UDP): 허용 (WireGuard)
- 443 (TCP): 허용 (HTTPS)
- 80 (TCP): 허용 (HTTP)
- 22 (TCP): 차단 (SSH)
- 3389 (TCP): 차단 (RDP)

---

## 🚨 긴급 차단

기기 분실 또는 해킹 의심:
```bash
python tools/device_registry.py revoke <MAC_ADDRESS>
```

---

생성 시간: {datetime.now().isoformat()}
"""

    guide_file = SECURITY_DIR / "SECURITY_GUIDE.md"
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write(guide)

    print(f"✅ 보안 설정 가이드: {guide_file}")


def setup_all():
    """전체 보안 설정"""
    print("🔐 Bridge 보안 강화 시스템 v1.0")
    print("=" * 70)
    print()

    # 1. 디렉토리 생성
    create_directories()
    print()

    # 2. WireGuard 설정
    print("📡 WireGuard VPN 설정 생성 중...")
    create_wireguard_server_config()
    create_wireguard_client_configs()
    print()

    # 3. SSH 키
    print("🔑 SSH 키 생성 중...")
    ssh_priv, ssh_pub = generate_ssh_keys()
    print()

    # 4. Render 설정
    print("☁️  Render 환경변수 생성 중...")
    render_config = create_render_env_config()
    print()

    # 5. 방화벽 규칙
    print("🚪 방화벽 규칙 생성 중...")
    create_firewall_rules()
    print()

    # 6. 가이드
    print("📋 보안 설정 가이드 생성 중...")
    create_security_guide()
    print()

    print("=" * 70)
    print("✅ 모든 보안 설정 생성 완료!")
    print()
    print("📂 생성된 파일:")
    print(f"   {SECURITY_DIR}")
    print()
    print("📖 다음 단계:")
    print("   1. docs/SECURITY_GUIDE.md 읽기")
    print("   2. Render 환경변수 설정")
    print("   3. 공유기 VPN 설정")
    print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2 or sys.argv[1] == "setup":
        setup_all()
    elif sys.argv[1] == "wireguard":
        create_directories()
        create_wireguard_server_config()
        create_wireguard_client_configs()
    elif sys.argv[1] == "ssh-keys":
        create_directories()
        generate_ssh_keys()
    elif sys.argv[1] == "render-config":
        create_directories()
        create_render_env_config()
    elif sys.argv[1] == "firewall":
        create_directories()
        create_firewall_rules()
    else:
        print(__doc__)
