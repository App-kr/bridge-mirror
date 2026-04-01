@echo off
cd /d Q:\Claudework\bridge base
echo ====================================================
echo  BRIDGE RPA — Vault Setup (account*.env 자동 읽기)
echo ====================================================
echo.
"Q:\Phtyon 3\python.exe" create_vault_from_env.py --show
echo.
if errorlevel 1 (
    echo [ERROR] Vault 생성 실패!
    echo.
    echo 수동 설정:
    echo   "Q:\Phtyon 3\python.exe" auto_vault_setup.py
) else (
    echo [OK] 설정 완료! RPA를 시작할 수 있습니다.
    echo.
    echo 테스트:
    echo   "Q:\Phtyon 3\python.exe" craigslist_auto_rpa.py --dry-run --limit 1
)
echo.
pause
