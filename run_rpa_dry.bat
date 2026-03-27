@echo off
REM RPA 드라이런 실행 (회색 계정, 광고 텍스트만 출력)
cd /d Q:\Claudework\bridge base
echo ====================================================
echo RPA 드라이런 시작 (회색 계정)
echo ====================================================
python craigslist_auto_rpa.py --account gray --dry-run
echo.
if errorlevel 1 (
    echo.
    echo [ERROR] 프로그램 실패!
    echo 에러 상세: Q:\Claudework\bridge base\logs\rpa_crash.log
    echo.
)
pause
