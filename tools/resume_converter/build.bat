@echo off
chcp 65001 >nul
echo ============================================
echo  BRIDGE Resume Converter — PyInstaller 빌드
echo ============================================

set PYTHON="D:/Phtyon 3/python.exe"
if not exist %PYTHON% set PYTHON=python

:: PyInstaller 설치 확인
%PYTHON% -m pip install pyinstaller --quiet

:: 빌드
cd /d "%~dp0.."
%PYTHON% -m PyInstaller ^
  --onefile ^
  --windowed ^
  --name "BRIDGE_Converter" ^
  --add-data "resume_converter/config_template.json;resume_converter" ^
  --hidden-import "PIL._tkinter_finder" ^
  --hidden-import "tkinterdnd2" ^
  --hidden-import "gspread" ^
  --hidden-import "google.auth" ^
  --hidden-import "anthropic" ^
  --hidden-import "pikepdf" ^
  --hidden-import "pdfplumber" ^
  --hidden-import "reportlab" ^
  --hidden-import "watchdog" ^
  --hidden-import "cryptography" ^
  resume_converter/main_gui.py

echo.
if exist dist\BRIDGE_Converter.exe (
  echo [OK] 빌드 성공: dist\BRIDGE_Converter.exe
) else (
  echo [오류] 빌드 실패
)
pause
