@echo off
REM ============================================================
REM  BRIDGE 일일 백업 Task Scheduler 등록 (관리자 권한 필요)
REM
REM  실행: 우클릭 → 관리자 권한으로 실행
REM
REM  스케줄: 매일 04:30 (저전력·서버 한가 시간)
REM  실행 사용자: SYSTEM (잠금 화면에서도 실행)
REM  실패 시:    이메일/텔레그램 알림 (tg_notify.py 자동 호출)
REM ============================================================
setlocal

set TASK_NAME=BRIDGE_Daily_Backup
set PYTHON=Q:\Phtyon 3\python.exe
set SCRIPT=Q:\Claudework\bridge base\scripts\daily_backup_runner.py
set TRIGGER_TIME=04:30

echo.
echo ================================================
echo   BRIDGE 일일 백업 Task Scheduler 등록
echo ================================================
echo.
echo Task: %TASK_NAME%
echo Python: %PYTHON%
echo Script: %SCRIPT%
echo Time: %TRIGGER_TIME% daily
echo.

REM 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [FAIL] 관리자 권한 필요. 우클릭 → 관리자 권한으로 실행.
    pause
    exit /b 1
)
echo [OK] 관리자 권한 확인

REM 기존 작업 삭제 (있으면)
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
echo [OK] 기존 작업 정리

REM 새 작업 등록 — SYSTEM 계정으로 매일 04:30
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%PYTHON%\" -X utf8 \"%SCRIPT%\"" ^
    /sc daily ^
    /st %TRIGGER_TIME% ^
    /ru SYSTEM ^
    /rl HIGHEST ^
    /f

if %errorLevel% neq 0 (
    echo [FAIL] 작업 등록 실패
    pause
    exit /b 1
)

echo.
echo [OK] 등록 완료
echo.
echo ── 확인 명령:
echo    schtasks /query /tn "%TASK_NAME%" /v /fo LIST
echo.
echo ── 즉시 테스트 실행:
echo    schtasks /run /tn "%TASK_NAME%"
echo.
echo ── 삭제:
echo    schtasks /delete /tn "%TASK_NAME%" /f
echo.
pause
endlocal
