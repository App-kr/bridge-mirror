@echo off
REM RDP 초 고도화 보안 연결 스크립트 (포트 4389, MAC 검증)
REM 2026-03-27

setlocal enabledelayedexpansion
cd /d "Q:\Claudework\bridge base"

echo.
echo ============================================================
echo RDP 초 고도화 보안 연결 시스템
echo ============================================================
echo.

REM Python 인증 실행
"C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe" -X utf8 tools\rdp_device_auth.py

if errorlevel 1 (
    echo.
    echo [ERROR] 인증 실패 - RDP 연결 불가
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] RDP 연결 완료
echo.
