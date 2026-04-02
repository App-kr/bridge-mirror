@echo off
chcp 65001 > nul
echo ===================================
echo BRIDGE 보안 작업 마무리
echo ===================================
echo.

cd /d "Q:\Claudework\bridge base"

echo [1/4] DB 암호화 중...
"Q:\Phtyon 3\python.exe" -X utf8 tools\db_backup_enc.py encrypt
if errorlevel 1 (
    echo [!] 암호화 실패 - BRIDGE_FIELD_KEY 확인 필요
    pause
    exit /b 1
)

echo.
echo [2/4] 무결성 검증...
"Q:\Phtyon 3\python.exe" -X utf8 tools\db_backup_enc.py verify

echo.
echo [3/4] git 커밋...
git add .gitignore tools\db_backup_enc.py master.db.enc master.db.enc.meta
git commit -m "security: DB 암호화 백업 도입 + git 히스토리 소각 완료"

echo.
echo [4/4] push...
git push origin main

echo.
echo ===================================
echo 완료!
echo ===================================
pause
