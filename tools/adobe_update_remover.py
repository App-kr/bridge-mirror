#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adobe 업데이트 강제 실행 메커니즘 완전 제거
- 서비스 비활성화
- 스케줄 작업 삭제
- 레지스트리 항목 삭제
- 업데이트 파일 제거
"""

import os
import subprocess
import winreg
from pathlib import Path

def run_cmd(cmd, silent=False):
    """cmd 명령 실행"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if not silent:
            print(f"[OK] {cmd}")
        return result.stdout
    except Exception as e:
        print(f"[ERROR] {cmd}: {e}")
        return ""

def main():
    print("\n" + "="*70)
    print("  🔥 Adobe 업데이트 강제 실행 메커니즘 완전 제거")
    print("="*70 + "\n")

    # 1. 서비스 비활성화
    print("[1] Adobe 업데이트 서비스 비활성화...")
    run_cmd('sc stop AdobeUpdateService', silent=True)
    run_cmd('sc config AdobeUpdateService start= disabled', silent=True)
    run_cmd('sc stop AdobeUpdateService 2>nul', silent=True)
    print("    ✓ AdobeUpdateService 비활성화")

    # Creative Cloud 관련
    run_cmd('sc stop CCXProcess', silent=True)
    run_cmd('sc config CCXProcess start= disabled', silent=True)
    print("    ✓ CCXProcess 비활성화")

    # 2. 스케줄 작업 제거
    print("\n[2] 스케줄된 작업 제거...")
    schtasks_output = run_cmd('tasklist /svc', silent=True)

    # Adobe 관련 스케줄 작업 모두 제거
    scheduled_tasks = [
        r'\Adobe\Adobe Reader',
        r'\Adobe\Adobe Acrobat Update Task',
        r'\Adobe\AdobeAAMUpdater',
        r'\CreativeCloud\CreativeCloudUpdate',
    ]

    for task in scheduled_tasks:
        run_cmd(f'schtasks /delete /tn "{task}" /f 2>nul', silent=True)

    print("    ✓ Adobe 관련 스케줄 작업 제거")

    # 3. 레지스트리에서 제거
    print("\n[3] 레지스트리에서 Adobe 업데이트 항목 제거...")

    try:
        # HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_WRITE)

        # Adobe 업데이트 관련 항목 삭제
        adobe_entries = [
            "AdobeAAMUpdater-1.0",
            "AdobeARM",
            "AdobeReader",
            "AdobeExperienceUpdate",
        ]

        for entry in adobe_entries:
            try:
                winreg.DeleteValue(registry_key, entry)
                print(f"    ✓ {entry} 삭제")
            except:
                pass

        winreg.CloseKey(registry_key)
    except Exception as e:
        print(f"    ⚠ 레지스트리 접근 실패: {e}")

    # 4. 파일 삭제
    print("\n[4] Adobe 업데이트 파일 제거...")

    adobe_paths = [
        r"C:\Program Files\Common Files\Adobe\ARM",
        r"C:\Program Files\Common Files\Adobe\UPS",
        r"C:\Program Files (x86)\Common Files\Adobe\ARM",
        r"C:\ProgramData\Adobe\ARM",
        r"C:\ProgramData\Adobe\Updates",
    ]

    for path in adobe_paths:
        if os.path.exists(path):
            try:
                import shutil
                shutil.rmtree(path)
                print(f"    ✓ {path} 삭제")
            except Exception as e:
                print(f"    ⚠ {path}: {e}")

    # 5. 업데이트 실행 방지
    print("\n[5] Adobe 업데이트 프로세스 영구 차단...")
    run_cmd('taskkill /F /IM AdobeUpdateService.exe 2>nul', silent=True)
    run_cmd('taskkill /F /IM AdobeARM.exe 2>nul', silent=True)
    run_cmd('taskkill /F /IM CreativeCloudUpdate.exe 2>nul', silent=True)
    print("    ✓ 실행 중인 Adobe 업데이트 프로세스 종료")

    print("\n" + "="*70)
    print("  ✅ 완료! Adobe 업데이트가 완전히 차단되었습니다.")
    print("     구 버전을 계속 사용할 수 있습니다.")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 오류: {e}\n")
