@echo off
REM ── BRIDGE Telegram Commander 자동 시작 등록 (관리자 권한 필요) ──
REM  로그온 시 watchdog 자동 실행 → tg_commander.py 데몬 유지

setlocal
set PY=Q:\Phtyon 3\python.exe
set SCRIPT=Q:\Claudework\bridge base\run_telegram_bot_watchdog.py
set TASKNAME=BRIDGE_TgCommander

echo [INFO] %TASKNAME% Task Scheduler 등록...

schtasks /create /tn "%TASKNAME%" ^
    /tr "wscript.exe \"Q:\Claudework\bridge base\run_tg_commander_silent.vbs\"" ^
    /sc onlogon /rl highest /f

if %errorlevel% neq 0 (
    echo [FAIL] 등록 실패. 관리자 권한으로 재실행 하세요.
    exit /b 1
)

echo [OK] %TASKNAME% 등록 완료.
echo.
echo [INFO] 지금 바로 실행 중...
schtasks /run /tn %TASKNAME%

endlocal
