@echo off
REM Python 마이그레이션 배치 파일 (관리자 권한 필수)
REM
REM C/D 드라이브의 Python을 Q로 옮기고 PATH 업데이트

setlocal enabledelayedexpansion

REM 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ============================================
    echo ERROR: 관리자 권한이 필요합니다!
    echo ============================================
    echo.
    echo 다음 방법으로 실행해주세요:
    echo   1. 이 배치 파일을 우클릭
    echo   2. "관리자 권한으로 실행" 선택
    echo.
    pause
    exit /b 1
)

cls
echo.
echo ============================================
echo Python 마이그레이션 (C/D → Q)
echo ============================================
echo.
echo 이 스크립트는:
echo   1. C/D 드라이브의 Python을 찾습니다
echo   2. Q 드라이브로 복사합니다
echo   3. PATH 환경변수를 업데이트합니다
echo   4. Python 3.14를 설치합니다 (필요시)
echo.
echo 진행하시겠습니까? (Y/N)
set /p answer=">> "

if /i "%answer%"=="Y" (
    REM PowerShell 스크립트 실행
    echo.
    echo PowerShell 스크립트 실행 중...
    powershell -ExecutionPolicy Bypass -NoProfile -File "Q:\Claudework\bridge base\scripts\migrate_python_to_q.ps1"

    if %errorLevel% equ 0 (
        echo.
        echo ============================================
        echo OK: 마이그레이션 완료!
        echo ============================================
        echo.
        echo PowerShell을 다시 열어서 테스트:
        echo   python --version
        echo   py --version
        echo.
    ) else (
        echo.
        echo ERROR: 마이그레이션 중 오류 발생
        echo.
    )
) else (
    echo 취소됨.
)

pause
