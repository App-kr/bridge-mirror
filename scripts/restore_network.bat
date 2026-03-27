@echo off
REM WireGuard 복구 배치 파일 (관리자 권한 필수)

setlocal enabledelayedexpansion

echo.
echo ================================
echo WireGuard 복구 + 네트워크 정상화
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

REM 1. WireGuard 프로세스 종료
echo [1/6] WireGuard 프로세스 종료 중...
taskkill /IM wireguard.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul

REM 2. WireGuard 서비스 중지
echo [2/6] WireGuard 서비스 중지 중...
sc stop "WireGuardTunnel$Scarlett_Main_PC" >nul 2>&1
timeout /t 2 /nobreak >nul

REM 3. 서비스 자동시작 비활성화
echo [3/6] 서비스 자동시작 비활성화...
sc config "WireGuardTunnel$Scarlett_Main_PC" start= disabled >nul 2>&1

REM 4. 네트워크 어댑터 갱신
echo [4/6] DHCP 갱신 중...
ipconfig /release >nul 2>&1
timeout /t 2 /nobreak >nul
ipconfig /renew >nul 2>&1

REM 5. DNS 캐시 초기화
echo [5/6] DNS 캐시 초기화...
ipconfig /flushdns >nul 2>&1

REM 6. 라우팅 테이블 초기화
echo [6/6] 라우팅 테이블 정리...
route /c >nul 2>&1

echo.
echo ================================
echo 복구 완료. 현재 상태:
echo ================================
echo.
echo 활성 어댑터:
ipconfig | findstr /C:"Ethernet" /C:"IPv4"
echo.
echo 기본 게이트웨이:
route print | findstr "0.0.0.0"
echo.
echo 인터넷 연결 테스트:
timeout /t 2 /nobreak >nul
ping -n 2 8.8.8.8

echo.
echo ================================
echo 네트워크 복구 완료
echo ================================
echo.
pause
