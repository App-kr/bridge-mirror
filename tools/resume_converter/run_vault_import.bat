@echo off
chcp 65001 >nul
:: BRIDGE Resume Converter — Google 서비스계정 임포트
:: 더블클릭 한 번으로 실행

set PYTHON="D:/Phtyon 3/python.exe"
if not exist %PYTHON% set PYTHON=python

cd /d "%~dp0.."
%PYTHON% -X utf8 -m resume_converter.vault_import

if %errorlevel% neq 0 (
  echo.
  echo [오류] 실행 실패. setup.bat을 먼저 실행하세요.
  pause
)
