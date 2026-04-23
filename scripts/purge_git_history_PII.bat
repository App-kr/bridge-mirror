@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title BRIDGE Git History PII Purge

rem ============================================================
rem  BRIDGE Git 히스토리 PII 소각 스크립트
rem  - filter-repo로 과거 커밋의 PII 파일 완전 제거
rem  - force push로 origin/main 덮어쓰기
rem  - 실행 전 백업 번들 존재 확인
rem ============================================================

set REPO=Q:\Claudework\bridge base
set MIRROR=Q:\Claudework\.tmp_repo_cleanup_20260423
set BUNDLE=Q:\Claudework\.vault\pii_backup_20260423\full_repo_20260423_100547.bundle
set PATHS=%REPO%\.git_purge_paths.txt
set PY=Q:\Phtyon 3\python.exe

echo ================================================
echo   BRIDGE Git History PII Purge
echo ================================================
echo.
echo Repo:   %REPO%
echo Mirror: %MIRROR%
echo Bundle: %BUNDLE%
echo Paths:  %PATHS%
echo.

rem ── 1단계: 백업 번들 존재 확인 ─────────────────────
if not exist "%BUNDLE%" (
    echo [FAIL] 백업 번들이 없습니다. 실행 중단.
    pause
    exit /b 1
)
echo [OK] 백업 번들 확인됨
for %%I in ("%BUNDLE%") do echo      크기: %%~zI bytes
echo.

rem ── 2단계: 미러 클론 존재 확인 ─────────────────────
if not exist "%MIRROR%\HEAD" (
    echo [FAIL] 미러 클론이 없습니다. 재생성:
    echo        git clone --mirror "%REPO%" "%MIRROR%"
    pause
    exit /b 1
)
echo [OK] 미러 클론 확인됨
echo.

rem ── 3단계: 삭제 경로 목록 확인 ─────────────────────
if not exist "%PATHS%" (
    echo [FAIL] 삭제 경로 파일이 없습니다: %PATHS%
    pause
    exit /b 1
)
echo [OK] 삭제 경로 목록:
type "%PATHS%"
echo.

rem ── 4단계: 사용자 확인 ─────────────────────────────
echo ================================================
echo   경고: 이 작업은 되돌릴 수 없습니다.
echo   - git 히스토리 재작성
echo   - origin/main 강제 덮어쓰기
echo   - GitHub 캐시 purge는 별도 요청 필요
echo ================================================
set /p CONFIRM=계속하려면 'YES' 입력:
if /i not "!CONFIRM!"=="YES" (
    echo 취소됨.
    pause
    exit /b 0
)

rem ── 5단계: filter-repo 실행 ───────────────────────
echo.
echo [RUN] git filter-repo 실행 중...
pushd "%MIRROR%"
"%PY%" -m git_filter_repo --paths-from-file "%PATHS%" --invert-paths --force
if errorlevel 1 (
    echo [FAIL] filter-repo 실패. 번들에서 복원:
    echo        git clone "%BUNDLE%" restored_repo
    popd
    pause
    exit /b 1
)
echo [OK] filter-repo 완료
echo.

rem ── 6단계: 결과 검증 ──────────────────────────────
echo [CHECK] 히스토리에 PII 경로가 남아있는지 확인:
git log --all --name-only --pretty=format: | findstr /R "testdata samples inbox output originals processing processed_docs email_pending email_processed" | find /c /v "" > tmp_count.txt
set /p REMAINING=<tmp_count.txt
del tmp_count.txt
echo        남은 PII 경로 참조: !REMAINING!줄
if not "!REMAINING!"=="0" (
    echo [WARN] PII 경로가 여전히 남아있습니다. 수동 확인 권장.
)
echo.

rem ── 7단계: force push ─────────────────────────────
echo [CONFIRM] force push를 진행하시겠습니까?
set /p PUSH=계속하려면 'PUSH' 입력:
if /i not "!PUSH!"=="PUSH" (
    echo push 건너뜀. 미러는 %MIRROR% 에 유지됨.
    popd
    pause
    exit /b 0
)

echo [RUN] git push --force 실행 중...
git push --force --all
git push --force --tags
if errorlevel 1 (
    echo [FAIL] push 실패
    popd
    pause
    exit /b 1
)
popd
echo [OK] force push 완료
echo.

rem ── 8단계: 메인 repo 재동기화 안내 ─────────────────
echo ================================================
echo   완료! 다음 단계 수동 실행:
echo   1. cd "%REPO%"
echo   2. git fetch origin
echo   3. git reset --hard origin/main
echo   4. PAT 재발급: github.com/settings/tokens
echo   5. GitHub Support에 cache purge 요청:
echo      support.github.com/contact/private-information
echo ================================================
pause
endlocal
