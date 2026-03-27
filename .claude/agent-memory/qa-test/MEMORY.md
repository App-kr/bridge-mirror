# QA Test Agent Memory

## 실행 환경 메모

- Python 컴파일 확인 (bash에서 직접 실행 가능):
  ```
  "C:/Users/Scarlett/AppData/Local/Programs/Python/Python313/python.exe" -X utf8 -c "import py_compile; py_compile.compile('파일경로', doraise=True); print('COMPILE_OK')"
  ```
- PowerShell 방식은 `$LASTEXITCODE` 이스케이프 문제로 불안정 -- bash 직접 실행 선호
- DB 쿼리용 임시 Python 스크립트는 Write 도구로 파일 생성 후 실행 (인라인 -c 가능하나 따옴표 복잡할 때 파일 방식 사용)
- 프론트엔드 API URL 스캔 스크립트: 별도 .py 파일로 작성 후 실행 (인라인 정규식 따옴표 충돌 회피)

## 프로젝트 구조 패턴

- Python: `Q:\Claudework\bridge base\api_server.py` (메인 FastAPI 서버, ~7830줄)
- DB: `Q:\Claudework\bridge base\master.db` (SQLite, 27 tables)
- 프론트: `Q:\Claudework\bridge base\web_frontend\src\app\admin\`
- 도구: `Q:\Claudework\bridge base\tools\` (64 .py files)
- 보안: `security_vault.py` (AES-256-GCM 암호화), `security_middleware.py`
- API 라우트: 122개 (96 auth, 18 public, 8 alternative auth)

## 반복되는 버그 패턴

- `_JOB_WRITABLE` 집합과 실제 DB 컬럼 불일치 발생 이력 있음 (2026-03-16: recruiter_memo) -- 2026-03-23 시점에서는 정상 일치 확인
- HMAC 검증에서 환경변수 미설정 시 검증 건너뜀 → Fail-Closed 위반 패턴 -- sync/incoming은 수정 완료 (503 반환)
- background thread에서 `SELECT MAX(id)` 기반 ID 생성 시 레이스 컨디션 가능
- `sync_google_sheets.py`의 service account JSON이 파일 경로 방식만 지원

## 2026-03-23 전수 점검 결과 요약

### CRITICAL
- `/api/admin/inbox` 백엔드 없음 (inbox 페이지 전체 미작동)
- `/api/admin/stats`, `/stats/monthly`, `/stats/by-source` 백엔드 없음 (대시보드 부분 실패)

### HIGH
- `candidates` 테이블에 `is_deleted` 컬럼 없음 (soft-delete 규칙 위반)
- `/api/admin/gmail/sync` 백엔드 없음

### MEDIUM
- URL 불일치: 프론트 `/api/admin/mail/logs` vs 백엔드 `/api/admin/mail-logs`
- BridgeCanvasSheet.tsx 미사용 qe* 변수 10개
- candidates.email 333건 NULL (10.9%)

## 보고서 경로

- `Q:\bridge-overnight\TEST_REPORT.md` (2026-03-27 세션 20 업데이트됨)

## 2026-03-27 세션 20 (QA 재개 시도)

### 발견사항

**Infrastructure Issues (Blocking):**
- Network unreachable: api.bridgejob.co.kr, bridgejob.co.kr 응답 없음
- master.db 파일 누락 (Q:\Claudework\bridge base\master.db)
- Q: 드라이브 접근 불가 (network drive 문제로 추정)

**Git Status:**
- 최신 커밋: eaa662eb (RPA feature)
- Uncommitted: craigslist_auto_rpa.py (modified), 3개 RPA 스크립트 (new)
- 2026-03-23 이후 추가 변경사항: RPA 통합만 (다른 영역 깨끗함)

**Positive Confirmations:**
- Vault system active (AES-256-GCM)
- .env files properly removed from git (commit 6430ded7)
- Python 코드 구조 정상 (import chains, route counts consistent)

**RPA Feature Status:**
- Craigslist Auto RPA + Credential Vault v3.0 추가됨
- 테스트 불가: DB 필요 (ad_posts 테이블)
- Python path migration scripts included (migrate_python_to_q.bat/ps1)

### 필요한 조치
1. Network/storage 복구 (Render 배포, Q: 드라이브, DNS)
2. master.db 복구 (backup 또는 Render /data/ volume)
3. RPA 변경사항 commit/revert 결정
4. 2026-03-23 CRITICAL 버그 재확인 (DB 복구 후)
