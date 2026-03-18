@echo off
REM Claude Code PreToolUse hook — runs via CMD.exe (no bash dependency)
"C:\Python314\python.exe" "Q:\Claudework\bridge base\tools\status_writer.py" PRE
"C:\Python314\python.exe" "Q:\Claudework\bridge base\tools\bridge_backup.py" --pre-hook %CLAUDE_TOOL_NAME%
