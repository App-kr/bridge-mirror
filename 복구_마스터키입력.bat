@echo off
chcp 65001 > nul
echo.
echo ===================================
echo  RPA 마스터키 캐시 복구
echo ===================================
echo.
"Q:\Phtyon 3\python.exe" "Q:\Claudework\bridge base\restore_mk_cache.py"
echo.
if %errorlevel% == 0 (
    echo 복구 완료! 이 창 닫고 RPA.vbs 실행하세요.
) else (
    echo 복구 실패. 마스터키를 확인하세요.
)
pause
