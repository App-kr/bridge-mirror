@echo off
REM BRIDGE Craigslist RPA Launcher
REM Windows 배치 파일로 Python 스크립트 실행

setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Python 경로 자동 감지
set "PYTHON="
for /f "delims=" %%A in ('where python 2^>nul') do set "PYTHON=%%A"

if not defined PYTHON (
    echo [ERROR] Python을 찾을 수 없습니다.
    echo.
    echo 다음 경로에 Python을 설치하세요:
    echo - C:\Users\Scarlett\AppData\Local\Programs\Python\Python314
    echo - C:\Users\Scarlett\AppData\Local\Programs\Python\Python313
    echo.
    pause
    exit /b 1
)

echo [INFO] Python: !PYTHON!
echo [INFO] 디렉토리: %cd%
echo.

REM 인자 처리 (기본값: --dry-run --limit 1)
if "%1"=="" (
    echo [INFO] 실행: !PYTHON! craigslist_auto_rpa.py --dry-run --limit 1
    !PYTHON! craigslist_auto_rpa.py --dry-run --limit 1
) else (
    echo [INFO] 실행: !PYTHON! craigslist_auto_rpa.py %*
    !PYTHON! craigslist_auto_rpa.py %*
)

set EXITCODE=%ERRORLEVEL%
echo.
echo [INFO] 종료 코드: %EXITCODE%
echo.

if not %EXITCODE% equ 0 (
    echo [ERROR] RPA 실행 실패 (코드: %EXITCODE%)
    echo.
    echo 해결 방법:
    echo 1. python auto_vault_setup.py
    echo 2. python craigslist_auto_rpa.py --dry-run --limit 1
    echo 3. RPA_GUIDE.md 참조
    echo.
)

pause
exit /b %EXITCODE%
