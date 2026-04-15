@echo off
set PY="Q:\Phtyon 3\pythonw.exe"
set SC="Q:\Claudework\bridge base\craigslist_auto_rpa.py"

start "account1" %PY% -X utf8 %SC% --account account1 --limit 10
timeout /t 5 /nobreak >nul
start "account2" %PY% -X utf8 %SC% --account account2 --limit 10
timeout /t 5 /nobreak >nul
start "account3" %PY% -X utf8 %SC% --account account3 --limit 10
timeout /t 5 /nobreak >nul
start "account4" %PY% -X utf8 %SC% --account account4 --limit 10
