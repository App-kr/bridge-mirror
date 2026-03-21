@echo off
title BRIDGE Telegram Bot
echo ========================================
echo   BRIDGE Agent Telegram Bot
echo ========================================
echo.
echo [CHECK] TELEGRAM_BOT_TOKEN in .env ...
"C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe" -c "from dotenv import load_dotenv; import os; load_dotenv('Q:/Claudework/bridge base/.env'); t=os.getenv('TELEGRAM_BOT_TOKEN',''); print('  Token: ' + ('SET (' + t[:8] + '...)' if t and t != 'VAULT' else 'NOT SET (VAULT)  <- .env에 실제 토큰 입력 필요!'))"
echo.
echo Starting bot...
"C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe" -m telegram_agent
pause
