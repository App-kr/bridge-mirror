@echo off
REM ─────────────────────────────────────────────────────────────────
REM  Craigslist 세션 설정 (최초 1회 실행)
REM
REM  "Further verification required" 오류가 나면 이 파일을 실행하세요.
REM  Chrome 창이 열리고 계정 선택 → 로그인 화면이 표시됩니다.
REM  직접 로그인 완료하면 세션이 저장되어 이후 run.bat 자동 실행됩니다.
REM ─────────────────────────────────────────────────────────────────
cd /d "%~dp0"
echo.
echo [INFO] Visible Chrome으로 로그인 세션 설정 중...
echo [INFO] Chrome 창이 열리면 직접 로그인하세요.
echo.
"Q:\Phtyon 3\python.exe" craigslist_auto_rpa.py
echo.
echo [완료] 로그인 완료 후 이후 run.bat을 정상 사용할 수 있습니다.
pause
