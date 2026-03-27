@echo off
REM Q 드라이브 네트워크 재연결
REM 관리자 권한 필수

setlocal enabledelayedexpansion

echo.
echo ================================
echo Q 드라이브 네트워크 재연결
echo ================================
echo.

REM 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERR] 관리자 권한이 필요합니다.
    echo 마우스 우클릭 "관리자로 실행" 으로 다시 실행하세요.
    pause
    exit /b 1
)

REM 1. 기존 연결 제거
echo [1/4] 기존 Q: 드라이브 연결 해제...
net use Q: /delete /y >nul 2>&1
timeout /t 2 /nobreak >nul

REM 2. NAS 호스트명으로 재연결 시도
echo [2/4] Q: 드라이브 재연결 중...
echo  시도 1: \\koreandobby\Claudework
net use Q: \\koreandobby\Claudework /persistent:yes >nul 2>&1

if %errorlevel% neq 0 (
    echo  시도 1 실패. 시도 2: \\192.168.0.10\Claudework
    net use Q: \\192.168.0.10\Claudework /persistent:yes >nul 2>&1
)

REM 3. 연결 확인
echo [3/4] 연결 상태 확인...
net use Q:

REM 4. 디렉토리 접근 테스트
echo [4/4] 디렉토리 접근 테스트...
if exist "Q:\Claudework\bridge base" (
    echo ✓ Q:\Claudework\bridge base 접근 가능
    echo.
    echo ================================
    echo 재연결 완료
    echo ================================
    echo.
    cd /d Q:\Claudework\bridge base
    echo git 상태 확인:
    git status
) else (
    echo ✗ 디렉토리 접근 불가
    echo.
    echo ================================
    echo 재연결 실패
    echo ================================
    echo.
    echo NAS IP 또는 호스트명을 수동으로 설정하세요:
    echo  net use Q: \\[NAS_IP]\Claudework /persistent:yes
)

pause
