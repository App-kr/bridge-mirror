@echo off
title BRIDGE Resume Converter v2.1
chcp 65001 >nul 2>&1

set "PYTHON_EXE=Q:\Phtyon 3\python.exe"
set "SCRIPT_DIR=%~dp0tools\resume_converter"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found: %PYTHON_EXE%
    pause
    exit /b 1
)

cd /d "%~dp0"

echo ==========================================
echo   BRIDGE Resume Converter v2.1
echo ==========================================
echo.

"%PYTHON_EXE%" -m tools.resume_converter.main_gui
if errorlevel 1 (
    echo.
    echo [ERROR] Converter exited with error code %errorlevel%
    pause
)
