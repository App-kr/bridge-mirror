@echo off
REM Claude Code Stop hook — runs via CMD.exe (no bash dependency)
"C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe" "Q:\Claudework\bridge base\tools\status_writer.py" STOP
"C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe" -X utf8 "Q:\Claudework\bridge base\tools\auto_finalize.py"
