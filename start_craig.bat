@echo off
REM BRIDGE Craigslist RPA Launcher
REM Windows 배치 파일로 Python 스크립트 실행

setlocal
cd /d "%~dp0"

REM 인자 처리 (기본값: --dry-run --limit 1)
if "%1"=="" (
    python craigslist_auto_rpa.py --dry-run --limit 1
) else (
    python craigslist_auto_rpa.py %*
)

if errorlevel 1 (
    echo.
    echo [ERROR] RPA 실행 실패
    echo.
    echo 해결 방법:
    echo 1. python auto_vault_setup.py
    echo 2. RPA_GUIDE.md 참조
    echo.
)

pause
