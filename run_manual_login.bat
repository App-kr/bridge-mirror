@echo off
chcp 65001 > nul
echo.
echo  ===================================================
echo   Craigslist RPA - 수동 로그인 도우미
echo  ===================================================
echo.
echo  Chrome이 RPA 전용 프로필로 열립니다.
echo  로그인 완료 후 Chrome을 닫고, run.bat을 실행하세요.
echo.

"Q:\Phtyon 3\python.exe" -X utf8 "Q:\Claudework\bridge base\cl_manual_login.py" %*

echo.
pause
