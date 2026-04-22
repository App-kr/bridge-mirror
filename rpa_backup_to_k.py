# -*- coding: utf-8 -*-
"""
BRIDGE RPA — K드라이브 백업 + 설치 패키지 생성기
실행: python rpa_backup_to_k.py
"""
import os, sys, shutil, json
from pathlib import Path
from datetime import datetime

SRC = Path(__file__).resolve().parent
DATE = datetime.now().strftime("%Y%m%d_%H%M")
DST = Path(f"K:/bridge_rpa_backup_{DATE}")

# ── 복사할 파일 목록 (RPA 전용) ──────────────────────────────────────────────
COPY_FILES = [
    # 핵심 RPA
    "craigslist_auto_rpa.py",
    "rpa_select_launcher.py",
    "rpa_overlay.py",
    "rpa_console_monitor.py",
    "cl_manual_login.py",
    "crypto_util.py",
    "security_vault.py",
    "auto_vault_setup.py",
    "create_vault_from_env.py",
    # 실행 런처
    "launcher.pyw",
    "start_craig.bat",
    "start_craig.vbs",
    "RPA.vbs",
    "run_rpa_dry.bat",
    "run_rpa_setup.bat",
    "run_login_setup.bat",
    "run_manual_login.bat",
    "run_vault_setup.vbs",
    # 아이콘
    "rpa_icon.ico",
    "rpa_icon_preview.png",
    "make_rpa_icon.py",
    # 의존성
    "requirements_rpa.txt",
    # 계정 설정
    "account1.env",
    "account2.env",
    "account3.env",
    "account4.env",
    "account_usage.json",
    # 암호화된 자격증명 (비밀번호 포함)
    ".rpa_vault.enc.json",
    ".rpa_mk.enc",
    ".rpa_accounts.enc.json",
]

# ── 복사할 폴더 목록 ─────────────────────────────────────────────────────────
COPY_DIRS = [
    "images",
    "ad_only",               # 클린 광고 소스 (RPA 단일 소스)
    ".chrome_rpa_profile",   # 로그인 세션 유지 (핵심!)
]

# ── 빈 폴더로 생성할 것 ──────────────────────────────────────────────────────
MAKE_DIRS = [
    "logs",
    "screenshots/craigslist",
    "data",
]

# ── tools 에서 필요한 것만 ────────────────────────────────────────────────────
COPY_TOOLS = [
    "tools/rpa_credential_vault.py",
    "tools/rpa_vault_manager.py",
]


def copy_file(src_path, dst_path):
    if src_path.exists():
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        return True
    return False


def copy_dir(src_path, dst_path):
    if src_path.exists():
        shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        return True
    return False


def main():
    print("=" * 60)
    print("  BRIDGE RPA — K드라이브 백업")
    print("=" * 60)
    print(f"  원본: {SRC}")
    print(f"  대상: {DST}")
    print()

    # master.db 포함 여부
    include_db = input("master.db(10MB) 포함? [y/N]: ").strip().lower() == "y"

    DST.mkdir(parents=True, exist_ok=True)

    ok, skip = 0, 0

    # 파일 복사
    print("\n[1/4] 파일 복사 중...")
    for fname in COPY_FILES:
        if copy_file(SRC / fname, DST / fname):
            print(f"  ✓ {fname}")
            ok += 1
        else:
            print(f"  - 없음: {fname}")
            skip += 1

    # tools 폴더
    (DST / "tools").mkdir(exist_ok=True)
    for fpath in COPY_TOOLS:
        if copy_file(SRC / fpath, DST / fpath):
            print(f"  ✓ {fpath}")
            ok += 1

    # master.db
    if include_db:
        print("\n[2/4] DB 복사 중 (10MB)...")
        if copy_file(SRC / "master.db", DST / "data" / "master.db"):
            print("  ✓ master.db")
    else:
        print("\n[2/4] DB 스킵")

    # 폴더 복사
    print("\n[3/4] 폴더 복사 중...")
    for dname in COPY_DIRS:
        src_d = SRC / dname
        dst_d = DST / dname
        if src_d.exists():
            print(f"  복사 중: {dname} ...")
            copy_dir(src_d, dst_d)
            print(f"  ✓ {dname}")
        else:
            print(f"  - 없음: {dname}")

    # 빈 폴더 생성
    for dname in MAKE_DIRS:
        (DST / dname).mkdir(parents=True, exist_ok=True)

    # 설치 스크립트 생성
    print("\n[4/4] 설치 스크립트 생성 중...")
    _write_installer(DST)
    print("  ✓ INSTALL.bat 생성")

    print()
    print("=" * 60)
    print(f"  완료! 파일 {ok}개 복사, {skip}개 스킵")
    print(f"  백업 위치: {DST}")
    print()
    print("  다른 PC에서: INSTALL.bat 더블클릭")
    print("=" * 60)


def _write_installer(dst: Path):
    installer = dst / "INSTALL.bat"
    installer.write_text(r"""@echo off
chcp 65001 >nul
echo.
echo =====================================================
echo   BRIDGE RPA 설치 프로그램
echo =====================================================
echo.
echo 설치할 드라이브를 선택하세요:
echo   [1] C:\bridge_rpa
echo   [2] D:\bridge_rpa
echo   [3] Q:\bridge_rpa
echo   [4] S:\bridge_rpa
echo   [5] 직접 입력
echo.
set /p CHOICE="선택 (1-5): "

if "%CHOICE%"=="1" set DEST=C:\bridge_rpa
if "%CHOICE%"=="2" set DEST=D:\bridge_rpa
if "%CHOICE%"=="3" set DEST=Q:\bridge_rpa
if "%CHOICE%"=="4" set DEST=S:\bridge_rpa
if "%CHOICE%"=="5" (
    set /p DEST="설치 경로 입력 (예: E:\bridge_rpa): "
)

if not defined DEST (
    echo [ERROR] 선택 오류. 다시 실행하세요.
    pause
    exit /b 1
)

echo.
echo 설치 경로: %DEST%
echo.
set /p CONFIRM="계속? [Y/n]: "
if /i "%CONFIRM%"=="n" exit /b 0

echo.
echo [1/3] 파일 복사 중...
xcopy /E /I /Y /Q "%~dp0*" "%DEST%\"
echo     완료

echo.
echo [2/3] Python 패키지 설치 중...
where python >nul 2>&1
if errorlevel 1 (
    echo [WARN] Python을 찾을 수 없습니다. 수동으로 설치 후 다시 실행하세요.
    echo        https://www.python.org/downloads/
    goto :setup_done
)
python -m pip install -r "%DEST%\requirements_rpa.txt" --quiet
echo     완료

:setup_done
echo.
echo [3/3] 실행 파일 설정 중...
set CRAIG_BAT=%DEST%\start_craig.bat

echo @echo off > "%DEST%\실행.bat"
echo cd /d "%DEST%" >> "%DEST%\실행.bat"
echo start "" pythonw "%DEST%\launcher.pyw" >> "%DEST%\실행.bat"
echo     완료

echo.
echo =====================================================
echo   설치 완료!
echo   실행: %DEST%\실행.bat  더블클릭
echo   또는: %DEST%\start_craig.bat
echo =====================================================
echo.
pause
""", encoding="utf-8")


if __name__ == "__main__":
    main()
