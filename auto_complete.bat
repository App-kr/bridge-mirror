@echo off
chcp 65001 >nul
cd /d Q:\Claudework\bridge base

echo.
echo ====================================================
echo RPA 자동 복구 시작
echo ====================================================
echo.

echo [1/3] Vault 파일 삭제...
if exist .rpa_vault.enc.json (
    del .rpa_vault.enc.json
    echo [OK] 파일 삭제 완료
) else (
    echo [OK] 파일이 없습니다
)

echo.
echo [2/3] Vault 설정 (비밀번호 입력받기)...
echo.
python tools/rpa_credential_vault.py setup

echo.
echo [3/3] RPA 자동 테스트 실행...
echo.
python craigslist_auto_rpa.py --account gray --dry-run

echo.
echo ====================================================
echo 완료!
echo ====================================================
pause
