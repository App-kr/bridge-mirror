@echo off
TITLE BRIDGE SYSTEM - MASTER CONTROL (MAO V3.0)

:: 1. API Backend Server 실행
start "BRIDGE_API_SERVER" cmd /c "Q:\Claudework\bridge base\시작_API서버.bat"

:: 2. Next.js Frontend Dev Server 실행
start "BRIDGE_FRONTEND" cmd /c "cd /d Q:\Claudework\bridge base\web_frontend && npm run dev"

:: 3. RPA Craigslist Automation 실행 (30초 대기 후 시작 - 서버 안정화 시간 확보)
timeout /t 30
start "BRIDGE_RPA_BOT" cmd /c "Q:\Claudework\bridge base\run_rpa.bat"

echo [SUCCESS] All BRIDGE modules are now running in parallel.
pause
