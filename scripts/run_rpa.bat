@echo off
cd /d "Q:\Claudework\bridge base"
python craigslist_auto_rpa.py --limit 10 >> logs\scheduler.log 2>&1
