# QA Test Agent Memory

## 실행 환경 메모

- `bash` 셸에서 `cmd /c` 또는 직접 파이썬 실행 시 stdout이 캡처되지 않는 현상 있음
- PowerShell을 통한 우회 실행이 필요: `powershell -Command "& 'python.exe' ..."`
- Python 컴파일 확인 패턴:
  ```
  powershell -Command "& 'C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe' -X utf8 -m py_compile 'Q:\Claudework\bridge base\파일.py' 2>&1; if ($LASTEXITCODE -eq 0) { Write-Output 'COMPILE_OK' } else { Write-Output 'COMPILE_FAIL' }"
  ```
- DB 쿼리용 임시 Python 스크립트는 Write 도구로 파일 생성 후 실행 (인라인 -c 방식은 특수문자 처리 문제로 불안정)

## 프로젝트 구조 패턴

- Python: `Q:\Claudework\bridge base\api_server.py` (메인 FastAPI 서버)
- DB: `Q:\Claudework\bridge base\master.db` (SQLite)
- 프론트: `Q:\Claudework\bridge base\web_frontend\src\app\admin\`
- 도구: `Q:\Claudework\bridge base\tools\`
- 보안: `security_vault.py` (AES-256-GCM 암호화), `security_middleware.py`

## 반복되는 버그 패턴

- `_JOB_WRITABLE` 집합과 실제 DB 컬럼 불일치 발생 이력 있음 (2026-03-16: recruiter_memo)
- HMAC 검증에서 환경변수 미설정 시 검증 건너뜀 → Fail-Closed 위반 패턴
- background thread에서 `SELECT MAX(id)` 기반 ID 생성 시 레이스 컨디션 가능
- `sync_google_sheets.py`의 service account JSON이 파일 경로 방식만 지원 (JSON 문자열 미지원)

## 보고서 경로

- `Q:\bridge-overnight\TEST_REPORT.md`
