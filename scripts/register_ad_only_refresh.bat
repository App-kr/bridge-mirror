@echo off
REM ── ad_only 일일 자동 전파 Task Scheduler 등록 (관리자 권한 필요) ──
REM  매일 06:30 에 refresh_all.py 실행 → jobs_clean + frontend mirror + ESL Cafe 재생성
REM  주의: schtasks /create 는 bridge_guard 에 의해 자동 차단되므로 사용자가 직접 실행.

setlocal
set PY=Q:\Phtyon 3\python.exe
set SCRIPT=Q:\Claudework\bridge base\ad_only\refresh_all.py
set TASKNAME=BRIDGE_ad_only_refresh

echo [INFO] %TASKNAME% Task Scheduler 등록 시도...
echo        실행 경로: %PY% -X utf8 "%SCRIPT%"
echo        시간:      매일 06:30
echo.

schtasks /create /tn "%TASKNAME%" ^
    /tr "\"%PY%\" -X utf8 \"%SCRIPT%\"" ^
    /sc daily /st 06:30 /rl highest /f

if %errorlevel% neq 0 (
    echo.
    echo [FAIL] 등록 실패. 관리자 권한으로 재실행 하세요.
    exit /b 1
)

echo.
echo [OK] %TASKNAME% 등록 완료.
echo      수동 실행:      schtasks /run /tn %TASKNAME%
echo      실행 이력 확인:  schtasks /query /tn %TASKNAME% /v /fo LIST
echo      삭제:           schtasks /delete /tn %TASKNAME% /f

endlocal
