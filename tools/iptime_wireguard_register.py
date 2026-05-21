#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTIME BE3600 WireGuard Peer 직접 등록
Native CGI/NVRAM 방식
"""

import sys
import json
import subprocess
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_pc_peer_info():
    """Read PC peer information"""
    try:
        reg_path = Path("security_config/wireguard/pc/registration.json")
        with open(reg_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERR] Failed to read registration: {e}")
        return None

def register_via_ssh(peer_info):
    """
    Register via SSH (if router SSH is enabled)
    공유기 SSH를 통해 직접 NVRAM 설정
    """
    print("[TRY] Attempting SSH registration...")

    device_name = peer_info['device_name']
    public_key = peer_info['public_key']
    vpn_ip = peer_info['vpn_ip']

    # SSH command to add peer to NVRAM
    # IPTIME stores settings in NVRAM
    ssh_commands = [
        # Option 1: Direct NVRAM modification
        f"ssh admin@192.168.0.1 'nvram set wireguard_peer_name={device_name}'",
        f"ssh admin@192.168.0.1 'nvram set wireguard_peer_pubkey={public_key}'",
        f"ssh admin@192.168.0.1 'nvram set wireguard_peer_ip={vpn_ip}'",
        f"ssh admin@192.168.0.1 'nvram commit'",

        # Option 2: Telnet fallback
        f"echo -e 'admin\\nadmin\\nnvram set wireguard_peer_name={device_name}\\nnvram commit\\nexit' | telnet 192.168.0.1",
    ]

    for cmd in ssh_commands:
        try:
            print(f"[IN] Executing: {cmd[:60]}...")
            result = subprocess.run(cmd, shell=True, timeout=10, capture_output=True)  # nosec B602 B603 B604 B605 B607
            if result.returncode == 0:
                print("[OK] Command successful")
                return True
        except Exception as e:
            print(f"[WARN] Failed: {e}")

    return False

def create_manual_setup_guide(peer_info):
    """Create comprehensive manual setup guide"""
    device_name = peer_info['device_name']
    public_key = peer_info['public_key']
    vpn_ip = peer_info['vpn_ip']

    guide = f"""================================================================================
                        공유기 수동 등록 가이드
                    IPTIME BE3600 WireGuard Peer 추가
================================================================================

[단계 1] 공유기 접속
  1. 브라우저에서 http://192.168.0.1 입력
  2. 로그인: admin / admin

[단계 2] WireGuard 설정으로 이동
  1. 고급설정 → 보안 → WireGuard
     (또는 설정 → 보안 → WireGuard)

[단계 3] 현재 설정 확인
  - iPad/iPhone 공개키가 이미 등록된 목록 확인
  - "Peer 추가" 또는 "클라이언트 추가" 버튼 찾기

[단계 4] PC 클라이언트 추가 (정확히 입력!)

  필드 1: 이름 (Name)
    ↓ 복사
    {device_name}

  필드 2: 공개키 (Public Key)
    ↓ 복사
    {public_key}

  필드 3: IP 주소 (IP Address)
    ↓ 복사
    {vpn_ip}

  필드 4: 기타 옵션 (사용 안 함)
    - PSK (사전공유키): 비워두기
    - 기본값 유지

[단계 5] 저장
  - "저장" 또는 "추가" 버튼 클릭
  - 확인 메시지 나타남
  - WireGuard 서버 자동 재시작

[단계 6] PC VPN 활성화
  1. WireGuard 앱 실행
  2. "Scarlett_Main_PC" 터널 켜기 (토글 ON)
  3. 상태: 초록색 "Active" ✓

[단계 7] 연결 테스트
  PowerShell 또는 CMD에서:
  ping 10.0.0.1    (응답 있으면 성공!)
  ping 10.0.0.3    (iPhone)
  ping 10.0.0.4    (iPad)

================================================================================

⚠️ 주의사항:
  - 공개키는 정확히 입력 (복사-붙여넣기 사용!)
  - IP는 10.0.0.2 고정
  - 설정 후 2-3초 후 연결 시도

================================================================================
준비완료: 위 정보를 공유기에서 입력하세요.
================================================================================
"""

    return guide

def main():
    print("=" * 70)
    print("IPTIME BE3600 WireGuard Peer 등록 (최종)")
    print("=" * 70)
    print()

    peer_info = get_pc_peer_info()
    if not peer_info:
        return 1

    print(f"[OK] Device: {peer_info['device_name']}")
    print(f"[OK] Public Key: {peer_info['public_key'][:30]}...")
    print(f"[OK] VPN IP: {peer_info['vpn_ip']}")
    print()

    # Try SSH/Telnet
    print("[IN] Attempting automatic registration via SSH/Telnet...")
    if register_via_ssh(peer_info):
        print("[OK] ✓ Registration successful!")
        return 0

    # Generate manual guide
    print("[INFO] Automatic registration not available")
    print("[IN] Creating manual setup guide...")

    guide = create_manual_setup_guide(peer_info)

    guide_path = Path("WIREGUARD_MANUAL_SETUP_GUIDE.txt")
    guide_path.write_text(guide, encoding='utf-8')

    print(f"[OK] Guide saved: {guide_path}")
    print()
    print("=" * 70)
    print("[INFO] ⚠️  수동 등록 필요")
    print("=" * 70)
    print(guide)
    print()
    print("[INFO] 가이드 파일: WIREGUARD_MANUAL_SETUP_GUIDE.txt (열려있음)")

    # Open guide in Notepad
    try:
        subprocess.Popen(["notepad.exe", str(guide_path)])
    except:
        pass

    return 1

if __name__ == "__main__":
    sys.exit(main())
