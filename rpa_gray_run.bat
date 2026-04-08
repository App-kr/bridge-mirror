@echo off
rem ─────────────────────────────────────────────────────────────
rem  BRIDGE Craigslist Auto RPA — 회색(gray) 계정 자동 실행 래퍼
rem  Task Scheduler 에서 호출됨
rem  계정: gray (bridgejobkr 회색 ID)
rem  건수: 20건 / 실행
rem ─────────────────────────────────────────────────────────────
setlocal EnableDelayedExpansion

set PYTHON=Q:\Phtyon 3\python.exe
set SCRIPT=Q:\Claudework\bridge base\craigslist_auto_rpa.py
set LOGDIR=Q:\Claudework\bridge base\logs
set LOGFILE=%LOGDIR%\rpa_scheduler.log

rem ── 로그 폴더 생성 ────────────────────────────────────────────
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

rem ── 현재 시간 기록 ────────────────────────────────────────────
echo. >> "%LOGFILE%"
echo ============================================================ >> "%LOGFILE%"
echo [START] %date% %time% — gray 20건 headless >> "%LOGFILE%"
echo ============================================================ >> "%LOGFILE%"

rem ── 중복 실행 방지 (rpa_gray.lock 존재 시 스킵) ──────────────
set LOCKFILE=%LOGDIR%\.rpa_gray.lock
if exist "%LOCKFILE%" (
    echo [SKIP] 이전 실행 중 — 잠금 파일 존재: %LOCKFILE% >> "%LOGFILE%"
    echo [SKIP] %date% %time% 중복 실행 차단 >> "%LOGFILE%"
    exit /b 0
)

rem ── 잠금 파일 생성 ────────────────────────────────────────────
echo %date% %time% > "%LOCKFILE%"

rem ── RPA 실행 ─────────────────────────────────────────────────
"%PYTHON%" -X utf8 "%SCRIPT%" --account gray --limit 20 --headless >> "%LOGFILE%" 2>&1
set EXITCODE=%errorlevel%

rem ── 잠금 파일 제거 ────────────────────────────────────────────
if exist "%LOCKFILE%" del "%LOCKFILE%"

rem ── 종료 기록 ─────────────────────────────────────────────────
echo [END] %date% %time% — exit=%EXITCODE% >> "%LOGFILE%"
echo ============================================================ >> "%LOGFILE%"

exit /b %EXITCODE%
