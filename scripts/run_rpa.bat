@echo off
cd /d "Q:\Claudework\bridge base"
python tools/craigslist_auto_rpa.py --headless --limit 10 >> logs\scheduler.log 2>&1
