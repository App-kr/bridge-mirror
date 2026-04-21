@echo off
REM Pipeline Failure Watcher — Windows 자동시작 데몬
REM 작업 스케줄러 또는 시작프로그램 폴더에 바로가기로 추가
REM
REM 설치 방법:
REM   1) 이 .bat 파일의 바로가기 생성
REM   2) 바로가기를 %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ 에 복사
REM   또는
REM   3) 작업 스케줄러 → 트리거: 로그온 시, 동작: 이 bat 실행

title BRIDGE Pipeline Watcher
cd /d "Q:\Claudework\bridge base"

echo [%DATE% %TIME%] Pipeline Failure Watcher 시작 중...
echo 감시 대상: %COMPUTERNAME%
echo 저장 경로: Q:\Claudework\bridge base\failed_files\
echo.
echo Ctrl+C 로 종료 | 최소화하여 백그라운드 실행 권장
echo =====================================================

:LOOP
"C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe" ^
  -X utf8 ^
  "Q:\Claudework\bridge base\tools\pipeline_failure_watcher.py" ^
  --daemon

REM 비정상 종료 시 30초 후 재시작
echo [%DATE% %TIME%] Watcher 비정상 종료 — 30초 후 재시작...
timeout /t 30 /nobreak
goto LOOP
