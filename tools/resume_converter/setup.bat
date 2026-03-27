@echo off
chcp 65001 >nul
echo ============================================
echo  BRIDGE Resume Converter — 환경 설정
echo ============================================

:: Python 확인
for %%P in (
  "D:\Phtyon 3\python.exe"
  "C:\Python310\python.exe"
  "C:\Python311\python.exe"
  "C:\Python312\python.exe"
) do (
  if exist %%P (
    set PYTHON=%%P
    goto :found_python
  )
)

:: PATH에서 찾기
python --version >nul 2>&1
if %errorlevel% equ 0 (
  set PYTHON=python
  goto :found_python
)

echo [오류] Python을 찾을 수 없습니다.
echo D:\Phtyon 3\python.exe 가 있는지 확인하세요.
pause
exit /b 1

:found_python
echo [OK] Python: %PYTHON%
%PYTHON% --version

:: 패키지 설치
echo.
echo [설치] 필요 패키지 설치 중...
%PYTHON% -m pip install -r "%~dp0requirements.txt" --quiet
if %errorlevel% neq 0 (
  echo [경고] 일부 패키지 설치 실패. 계속 진행합니다.
)

:: config.json 생성
if not exist "%~dp0config.json" (
  echo.
  echo [설정] config.json 생성 중...
  copy "%~dp0config_template.json" "%~dp0config.json" >nul
  echo config.json이 생성되었습니다. 편집기로 열어 설정하세요.
  echo   - sheet_id: 구글시트 ID 입력
  echo   - service_account_path: 서비스 계정 JSON 경로
)

:: 구글 서비스 계정 경로 입력
echo.
set /p SA_PATH="서비스 계정 JSON 경로 (Enter=건너뜀): "
if not "%SA_PATH%"=="" (
  :: config.json에 경로 업데이트
  %PYTHON% -c "
import json, sys
path = r'%~dp0config.json'
try:
    cfg = json.load(open(path, encoding='utf-8'))
    cfg['service_account_path'] = r'%SA_PATH%'
    json.dump(cfg, open(path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print('[OK] config.json 업데이트 완료')
except Exception as e:
    print(f'[오류] {e}')
"
)

:: 연결 테스트
echo.
echo [테스트] 구글시트 연결 테스트...
%PYTHON% -c "
import sys, os
sys.path.insert(0, r'%~dp0..')
os.chdir(r'%~dp0')
try:
    from resume_converter.sheets_connector import is_connected
    print('[OK] 시트 연결 성공' if is_connected() else '[경고] 시트 연결 실패 (설정 확인 필요)')
except Exception as e:
    print(f'[정보] 시트 연결 건너뜀: {e}')
"

echo.
echo ============================================
echo  설정 완료! 실행: run.bat
echo ============================================
pause
