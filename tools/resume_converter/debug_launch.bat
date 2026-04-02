@echo off
chcp 65001 > nul
echo ============================================
echo  BRIDGE Converter - Debug Launch
echo ============================================
echo.

set PYTHON="Q:\Phtyon 3\python.exe"
set TOOLS="Q:\Claudework\bridge base\tools"

echo [1] Python 경로 확인...
if not exist %PYTHON% (
    echo ERROR: Python not found at Q:\Phtyon 3\python.exe
    pause
    exit /b 1
)
echo     OK: %PYTHON%
echo.

echo [2] 모듈 임포트 테스트...
%PYTHON% -X utf8 -c "import sys; sys.path.insert(0, r'Q:\Claudework\bridge base\tools'); print('  sys.path OK'); import tkinter; print('  tkinter OK'); from tkinterdnd2 import TkinterDnD; print('  tkinterdnd2 OK'); from PIL import Image; print('  PIL OK'); import fitz; print('  PyMuPDF OK'); from resume_converter import main_gui; print('  main_gui import OK')"
echo.

echo [3] GUI 실행 (에러 있으면 이 창에 표시됨)...
echo     닫으면 프로그램 종료됩니다.
echo.
%PYTHON% -X utf8 -c "import sys,os; sys.path.insert(0,r'Q:\Claudework\bridge base\tools'); from resume_converter.main_gui import main; main()"

if errorlevel 1 (
    echo.
    echo *** 오류 발생! 위 메시지를 확인하세요 ***
)
pause
