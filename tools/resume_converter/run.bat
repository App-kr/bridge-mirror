@echo off
chcp 65001 >nul
:: BRIDGE Resume Converter 실행

set PYTHON="D:/Phtyon 3/python.exe"
if not exist %PYTHON% set PYTHON=python

cd /d "%~dp0.."
%PYTHON% -X utf8 -m resume_converter.main_gui
if %errorlevel% neq 0 (
  echo [오류] 실행 실패. setup.bat 을 먼저 실행하세요.
  pause
)
