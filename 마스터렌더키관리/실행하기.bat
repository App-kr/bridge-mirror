@echo off
title Render Master Key Manager (Secure)
chcp 65001 > nul
cls

echo ==================================================
echo   Render 환경변수 암호화 도구 실행기
echo ==================================================
echo.

:: 1. Python 설치 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!ERROR] Python이 설치되어 있지 않거나 PATH에 없습니다.
    pause
    exit /b
)

:: 2. 필수 라이브러리(cryptography) 확인 및 자동 설치
python -c "import cryptography" >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] 필수 라이브러리(cryptography)를 설치하는 중입니다...
    python -m pip install cryptography
)

:: 3. 프로그램 실행
echo [*] 프로그램을 시작합니다...
python "%~dp0main.py"

pause
