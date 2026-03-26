@echo off
cd /d "Q:\Claudework\bridge base"
call .venv\Scripts\activate.bat
python ddns_watchdog.py >> ddns_watchdog.log 2>&1
