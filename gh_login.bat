@echo off
chcp 65001 > nul
title GitHub Login - koreadobby
color 0A
echo.
echo ================================================================
echo    GitHub 로그인 - koreadobby 계정
echo ================================================================
echo.
echo 잠시 후 8자리 코드가 화면에 표시됩니다.
echo.
echo 1. 코드 자동 클립보드 복사됨 (또는 직접 복사)
echo 2. 브라우저가 자동으로 열립니다
echo 3. koreadobby 계정으로 로그인
echo 4. 코드 붙여넣기 + Authorize
echo.
echo ================================================================
echo.
gh auth login --hostname github.com --git-protocol https --web
echo.
echo ================================================================
if %ERRORLEVEL% EQU 0 (
    color 0A
    echo  로그인 성공!
    echo  이 창을 닫고 클로드에게 "됐어"라고 알려주세요.
) else (
    color 0C
    echo  로그인 실패 - 다시 시도하거나 클로드에게 알려주세요.
)
echo ================================================================
echo.
pause
