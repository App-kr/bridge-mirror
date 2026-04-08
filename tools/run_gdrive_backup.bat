@echo off
REM BRIDGE Google Drive Auto Backup -- daily 02:00
cd /d "Q:\Claudework\bridge base"
"Q:\Phtyon 3\python.exe" -X utf8 tools/gdrive_backup.py --all >> "Q:\Claudework\bridge base\tools\gdrive_backup.log" 2>&1
