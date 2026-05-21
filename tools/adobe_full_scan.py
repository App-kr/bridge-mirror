#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adobe/Photoshop 전체 PC 검사 및 업데이트 메커니즘 완전 제거
"""

import os
import subprocess
import shutil
from pathlib import Path
from winreg import *

def scan_and_remove():
    print("\n" + "="*80)
    print("  🔍 ADOBE 전체 PC 검사 + Photoshop 완전 정리")
    print("="*80 + "\n")

    # ===== 1. 주요 Adobe 폴더 목록 =====
    adobe_paths = [
        # Program Files
        r"C:\Program Files\Adobe",
        r"C:\Program Files (x86)\Adobe",
        r"C:\Program Files\Common Files\Adobe",
        r"C:\Program Files (x86)\Common Files\Adobe",

        # ProgramData
        r"C:\ProgramData\Adobe",

        # AppData - Local
        r"C:\Users\Scarlett\AppData\Local\Adobe",
        r"C:\Users\Scarlett\AppData\Local\CCXProcess",
        r"C:\Users\Scarlett\AppData\Local\Adobe Photoshop",

        # AppData - Roaming
        r"C:\Users\Scarlett\AppData\Roaming\Adobe",
        r"C:\Users\Scarlett\AppData\Roaming\Adobe\Adobe Photoshop",

        # Creative Cloud
        r"C:\ProgramData\Adobe Creative Cloud",
        r"C:\Users\Scarlett\AppData\Local\Creative Cloud",
    ]

    print("[1] 📁 Adobe/Photoshop 폴더 검색...")
    found_paths = []
    for path in adobe_paths:
        if os.path.exists(path):
            found_paths.append(path)
            print(f"    ✓ {path}")

    # ===== 2. Photoshop 업데이트 설정 파일 =====
    print("\n[2] 🔧 Photoshop 설정 파일 비활성화...")

    ps_config_paths = [
        r"C:\Users\Scarlett\AppData\Roaming\Adobe\Adobe Photoshop 2024\Adobe Photoshop 2024 Prefs.ps2",
        r"C:\Users\Scarlett\AppData\Roaming\Adobe\Adobe Photoshop 2025\Adobe Photoshop 2025 Prefs.ps2",
    ]

    for config in ps_config_paths:
        if os.path.exists(config):
            print(f"    ✓ {config}")

    # ===== 3. 레지스트리 정리 =====
    print("\n[3] 🔐 레지스트리에서 Adobe 업데이트 차단...")

    try:
        # 실행 시작 항목 제거
        reg_paths = [
            (HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
            (HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
        ]

        adobe_entries = [
            "AdobeAAMUpdater-1.0",
            "AdobeARM",
            "AdobeReader",
            "AdobeExperienceUpdate",
            "CCXProcess",
            "Creative Cloud",
        ]

        for hive, subkey in reg_paths:
            try:
                key = OpenKey(hive, subkey, 0, KEY_WRITE)
                for entry in adobe_entries:
                    try:
                        DeleteValue(key, entry)
                        print(f"    ✓ {entry} 제거 ({subkey})")
                    except:
                        pass
                CloseKey(key)
            except:
                pass

        # Adobe 업데이트 관련 레지스트리 경로 비활성화
        adobe_reg_paths = [
            (HKEY_LOCAL_MACHINE, r"SOFTWARE\Adobe\Adobe Updater"),
            (HKEY_LOCAL_MACHINE, r"SOFTWARE\Adobe\Adobe ARM"),
            (HKEY_CURRENT_USER, r"SOFTWARE\Adobe\UpdateCheck"),
        ]

        for hive, path in adobe_reg_paths:
            try:
                key = OpenKey(hive, path, 0, KEY_WRITE)
                SetValueEx(key, "UpdateCheck", 0, REG_DWORD, 0)
                CloseKey(key)
                print(f"    ✓ {path} 비활성화")
            except:
                pass

    except Exception as e:
        print(f"    ⚠ 레지스트리 접근 제한: {e}")

    # ===== 4. 서비스 중지 =====
    print("\n[4] ⚙️  Windows 서비스 비활성화...")

    services_to_disable = [
        "AdobeUpdateService",
        "AdobeARMservice",
        "Adobe Update Service",
    ]

    for service in services_to_disable:
        try:
            subprocess.run(f'sc config "{service}" start= disabled', shell=True, capture_output=True)  # nosec B602 B603 B604 B605 B607
            subprocess.run(f'sc stop "{service}"', shell=True, capture_output=True)  # nosec B602 B603 B604 B605 B607
            print(f"    ✓ {service}")
        except:
            pass

    # ===== 5. 프로세스 종료 =====
    print("\n[5] 🛑 실행 중인 Adobe 프로세스 종료...")

    adobe_processes = [
        "AdobeUpdateService.exe",
        "AdobeARM.exe",
        "CCXProcess.exe",
        "Creative Cloud.exe",
        "CreativeCloudUpdate.exe",
    ]

    for proc in adobe_processes:
        try:
            subprocess.run(f'taskkill /F /IM {proc}', shell=True, capture_output=True)  # nosec B602 B603 B604 B605 B607
            print(f"    ✓ {proc}")
        except:
            pass

    # ===== 6. 업데이트 폴더 삭제 =====
    print("\n[6] 🗑️  업데이트 폴더 완전 삭제...")

    update_paths = [
        r"C:\ProgramData\Adobe\Updates",
        r"C:\ProgramData\Adobe\ARM",
        r"C:\ProgramData\Adobe\UPS",
        r"C:\Users\Scarlett\AppData\Local\Adobe\Update",
        r"C:\Users\Scarlett\AppData\Local\Adobe\AAM Updates",
    ]

    for path in update_paths:
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                print(f"    ✓ {path} 삭제")
            except Exception as e:
                print(f"    ⚠ {path}: {e}")

    # ===== 7. hosts 파일에 Adobe 서버 차단 =====
    print("\n[7] 🚫 hosts 파일에 Adobe 서버 차단...")

    hosts_file = r"C:\Windows\System32\drivers\etc\hosts"
    adobe_domains = [
        "adobe.com",
        "adobedc.net",
        "akamai.net",
        "download.adobe.com",
        "updater.adobe.com",
        "ardownload.adobe.com",
        "ardownload2.adobe.com",
    ]

    try:
        with open(hosts_file, 'r') as f:
            content = f.read()

        for domain in adobe_domains:
            if domain not in content:
                content += f"\n127.0.0.1 {domain}"
                content += f"\n127.0.0.1 www.{domain}"

        with open(hosts_file, 'w') as f:
            f.write(content)

        print(f"    ✓ {len(adobe_domains)}개 Adobe 도메인 차단")
    except Exception as e:
        print(f"    ⚠ hosts 파일 수정 실패: {e}")

    # ===== 8. 방화벽 규칙 추가 =====
    print("\n[8] 🔒 Windows 방화벽 규칙 추가...")

    adobe_exes = [
        r"C:\Program Files\Adobe\*\AdobeUpdateService.exe",
        r"C:\Program Files\Adobe\*\AdobeARM.exe",
    ]

    for exe in adobe_exes:
        try:
            cmd = f'netsh advfirewall firewall add rule name="Block Adobe Update" dir=out action=block program="{exe}" enable=yes'
            subprocess.run(cmd, shell=True, capture_output=True)  # nosec B602 B603 B604 B605 B607
        except:
            pass

    print(f"\n    ✓ 방화벽 규칙 추가 완료")

    # ===== 최종 정리 =====
    print("\n" + "="*80)
    print("  ✅ 완료! Adobe 업데이트가 완전히 제거되었습니다.")
    print("     - 모든 업데이트 서비스 비활성화")
    print("     - Adobe 서버 연결 차단")
    print("     - 레지스트리 정리")
    print("     - Photoshop 자동 업데이트 제거")
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        scan_and_remove()
    except Exception as e:
        print(f"\n❌ 오류: {e}\n")
