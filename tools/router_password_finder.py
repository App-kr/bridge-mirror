#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공유기 비밀번호 찾기 도구
- 공유기 모델 감지
- 기본 비밀번호 자동 시도
- 비밀번호 변경만 가능 (기타 설정 유지)

사용법:
  python router_password_finder.py
  python router_password_finder.py --change-password
"""

import subprocess
import platform
import sys
import requests
from pathlib import Path
from typing import Optional, Dict, Tuple

# Windows UTF-8 처리
if platform.system() == "Windows":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 일반적인 공유기 기본 비밀번호 데이터베이스
DEFAULT_PASSWORDS = {
    # SK Broadband (SK 텔레콤)
    "sk": [
        ("admin", "admin"),
        ("admin", "1234"),
        ("1234", "1234"),
    ],
    # KT (KT 텔레콤)
    "kt": [
        ("admin", "1234"),
        ("admin", "admin"),
        ("admin", "kt"),
    ],
    # LG U+ (LG 유플러스)
    "lgu": [
        ("admin", "admin"),
        ("admin", "1234"),
        ("lgadmin", "lgadmin"),
    ],
    # 일반 IPTIME
    "iptime": [
        ("admin", "admin"),
        ("admin", "1234"),
        ("iptime", "iptime"),
    ],
    # D-Link
    "dlink": [
        ("admin", "admin"),
        ("admin", ""),
    ],
    # TP-Link
    "tplink": [
        ("admin", "admin"),
        ("admin", "admin123"),
    ],
    # Asus
    "asus": [
        ("admin", "admin"),
        ("admin", "admin123"),
    ],
    # 기타 일반
    "generic": [
        ("admin", "admin"),
        ("admin", "1234"),
        ("admin", "password"),
        ("root", "root"),
        ("root", "admin"),
        ("", ""),
    ],
}


def get_router_model(gateway_ip: str = "192.168.0.1") -> Optional[str]:
    """공유기 모델명 감지"""
    try:
        # UPnP를 통한 모델 감지 시도
        result = subprocess.run(
            ["powershell", "-Command",
             f"(New-Object System.Net.WebClient).DownloadString('http://{gateway_ip}') | Select-String -Pattern 'model|Model|MODEL' -All"],
            capture_output=True,
            text=True,
            encoding='cp949',
            errors='replace',
            timeout=5
        )

        output = result.stdout.lower()

        # 공유기 브랜드 감지
        if 'iptime' in output or 'iptime' in gateway_ip.lower():
            return "IPTIME"
        elif 'sk' in output or 'broadband' in output:
            return "SK Broadband"
        elif 'kt' in output or 'olleh' in output:
            return "KT"
        elif 'lgu' in output or 'uplus' in output:
            return "LG U+"
        elif 'dlink' in output:
            return "D-Link"
        elif 'tp-link' in output or 'tplink' in output:
            return "TP-Link"
        elif 'asus' in output:
            return "Asus"

    except Exception as e:
        print(f"⚠️ 모델 감지 실패: {e}")

    return None


def test_password(gateway_ip: str, username: str, password: str) -> bool:
    """비밀번호 테스트"""
    try:
        response = requests.get(
            f"http://{gateway_ip}",
            auth=(username, password),
            timeout=3
        )
        return response.status_code < 400

    except Exception:
        return False


def find_password(gateway_ip: str = "192.168.0.1") -> Optional[Tuple[str, str]]:
    """기본 비밀번호 찾기"""
    print("🔍 공유기 기본 비밀번호 찾는 중...")
    print("-" * 60)

    model = get_router_model(gateway_ip)
    if model:
        print(f"✅ 공유기 모델: {model}")
    else:
        print(f"⚠️ 모델 감지 실패 — 일반 기본값 시도")

    # 시도할 비밀번호 조합
    attempts = []

    if model and model.lower() in DEFAULT_PASSWORDS:
        attempts = DEFAULT_PASSWORDS[model.lower()]
    else:
        attempts = DEFAULT_PASSWORDS["generic"]

    print(f"\n시도 중 ({len(attempts)}개)...")

    for username, pwd in attempts:
        print(f"  시도: {username}:{pwd[:2]}{'*' * (len(pwd) - 2) if pwd else ''}", end="... ")

        if test_password(gateway_ip, username, pwd):
            print("✅ 성공!")
            return (username, pwd)
        else:
            print("❌")

    print("\n❌ 기본 비밀번호를 찾을 수 없습니다")
    return None


def reset_password_only(gateway_ip: str = "192.168.0.1",
                        username: str = "admin",
                        old_password: str = "admin",
                        new_password: str = "new_password") -> bool:
    """
    비밀번호만 변경 (다른 설정 유지)

    주의: 공유기마다 API가 다르므로, 이 함수는 기본적인 HTTP 요청 시도만 합니다.
    대부분의 경우 웹 브라우저로 직접 진행해야 합니다.
    """
    print(f"🔐 비밀번호 변경 시도 중...")
    print(f"   주소: http://{gateway_ip}")
    print(f"   사용자: {username}")

    try:
        # 로그인 시도
        session = requests.Session()
        session.auth = (username, old_password)

        # 일반적인 비밀번호 변경 경로들
        change_paths = [
            "/admin/password",
            "/admin/sys/passwd",
            "/cgi-bin/admin?cmd=change_passwd",
            "/system.html",
            "/settings.html",
        ]

        for path in change_paths:
            try:
                response = session.get(f"http://{gateway_ip}{path}", timeout=3)
                if response.status_code == 200:
                    print(f"\n✅ 비밀번호 변경 페이지 발견: {path}")
                    print(f"\n📋 수동으로 진행하세요:")
                    print(f"   1. http://{gateway_ip}{path} 접속")
                    print(f"   2. 현재 비밀번호 입력")
                    print(f"   3. 새 비밀번호 입력 (12자 이상)")
                    print(f"   4. 저장 클릭")
                    return True

            except Exception:
                continue

        print(f"\n⚠️ 자동 비밀번호 변경 실패")
        print(f"\n📋 수동으로 진행하세요:")
        print(f"   1. http://{gateway_ip} 접속")
        print(f"   2. 로그인 (현재 비밀번호)")
        print(f"   3. 설정 → 관리자 설정 또는 보안 메뉴")
        print(f"   4. 비밀번호 변경 선택")
        print(f"   5. 새 비밀번호 입력 (12자 이상, 특수문자 포함)")
        print(f"   6. 저장")

        return False

    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def main():
    import sys

    gateway_ip = "192.168.0.1"

    if "--help" in sys.argv:
        print(__doc__)
        return

    # 1단계: 기본 비밀번호 찾기
    print("=" * 60)
    print("공유기 비밀번호 복구 도구")
    print("=" * 60)
    print()

    credentials = find_password(gateway_ip)

    if credentials:
        username, password = credentials
        print(f"\n✅ 기본 비밀번호 발견!")
        print(f"   사용자명: {username}")
        print(f"   비밀번호: {password}")

        print(f"\n🌐 공유기 접속:")
        print(f"   주소: http://{gateway_ip}")
        print(f"   사용자명: {username}")
        print(f"   비밀번호: {password}")

        # 2단계: 비밀번호 변경
        print(f"\n🔐 비밀번호 변경:")
        print(f"   1. 위 주소로 접속")
        print(f"   2. 로그인")
        print(f"   3. 설정 → 관리자 설정 또는 보안")
        print(f"   4. 비밀번호 변경")
        print(f"   5. 새 비밀번호 입력 (12자 이상, 특수문자)")
        print(f"   6. 저장 (다른 설정은 건드리지 않음)")

    else:
        print(f"\n⚠️ 기본 비밀번호를 자동으로 찾을 수 없습니다")
        print(f"\n📋 다른 방법:")
        print(f"   1️⃣ 공유기 뒷면 스티커 확인 (기본 정보)")
        print(f"   2️⃣ 공유기 구입 상자 또는 설명서 확인")
        print(f"   3️⃣ 공유기 모델명 + '기본 비밀번호' 구글 검색")
        print(f"   4️⃣ ISP(통신사) 고객센터 전화")
        print(f"      • SK: 080-1000-0075")
        print(f"      • KT: 100 (유선전화) / 1588-0010 (휴대폰)")
        print(f"      • LG U+: 1577-0010")
        print(f"   5️⃣ 공유기 초기화 버튼 (모든 설정 초기화됨 — 비추천)")
        print()
        print(f"🔘 초기화 버튼 위치:")
        print(f"   • 공유기 뒷면의 작은 'Reset' 버튼")
        print(f"   • 10초 이상 누르면 초기화됨")
        print(f"   ⚠️ 모든 설정이 초기화되므로 마지막 수단")


if __name__ == "__main__":
    main()
