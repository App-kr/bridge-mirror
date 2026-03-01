@echo off
chcp 65001 > nul
title BRIDGE API Server (port 8000)

cd /d "Q:\Claudework\bridge base"

echo ============================================
echo   BRIDGE API Server
echo   http://localhost:8000
echo   문서: http://localhost:8000/docs
echo ============================================
echo.

:: uvicorn 설치 확인
python -c "import uvicorn" 2>nul
if errorlevel 1 (
    echo [설치] uvicorn 설치 중...
    pip install fastapi uvicorn email-validator
)

echo [시작] API 서버 실행 중...
echo       종료: Ctrl+C
echo.
python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload

pause
