# Bridge Security Hardening Plan
# 2026-03-08 | 모든 파일: Q:\Claudework\bridge base\ 내부만

## Context
- 강사 지원(apply) + 채용의뢰(inquiry) 제출 후 백업 미작동
- /uploads/ 직접 접근 시 인증 없이 CV·사진·서류 노출
- DB 암호화 9개 필드만 — dob, nationality, current_location, reference 평문 저장

## 구현 범위

### Task 1 — 파일 서명 URL + /uploads/ 차단 (api_server.py)
1. `.env` + `.env.example` 에 `UPLOAD_SIGN_KEY` 추가
2. `generate_signed_url(rel_path, expires_in=600)` 함수 — HMAC-SHA256
3. `verify_signed_url(rel_path, expires, sig)` 함수 — 만료 + 서명 검증
4. `GET /api/files/{entity_type}/{entity_id}/{filename}` 엔드포인트
   - 서명 유효 OR 관리자 키 → FileResponse 반환
   - 서명 실패/만료 → 403
5. `app.mount("/uploads", StaticFiles(...))` 제거 → `/api/files/` 로 교체
6. SecurityMiddleware에 `/uploads/` 직접 접근 → 403 규칙 추가

### Task 2 — 제출 시 자동 백업 (api_server.py)
1. `_backup_on_submit()` 함수 신규 작성
   - SQLite VACUUM INTO encrypted_path (plaintext → AES-GCM encrypted .enc)
   - 로컬 저장: `/data/backups/auto/submit_YYYYMMDD_HHMMSS.enc`
   - 기존 auto_backup 파일도 함께 갱신
2. `apply()` 핸들러 INSERT 성공 후 → `_backup_on_submit()` 호출
3. `inquiry()` 핸들러 INSERT 성공 후 → `_backup_on_submit()` 호출
4. `_maybe_auto_backup()` 카운터: 메모리→파일 영속화 (재시작 후에도 유지)

### Task 3 — PII 암호화 확장 (api_server.py + migration)
현재 _CANDIDATE_ENCRYPT 9개 → 13개로 확장:
- 추가: `dob`, `nationality`, `current_location`, `reference`

현재 _INQUIRY_ENCRYPT 4개 → 6개로 확장:
- 추가: `school_location`, `memo`

기존 데이터 마이그레이션:
- `tools/encrypt_migrate.py` 스크립트 신규 작성
- 평문 필드를 읽어 암호화 후 UPDATE (이미 암호화된 것은 skip)
- 완료 후 검증 리포트 출력

### Task 4 — 관리자 패널 서명 URL 자동 생성 (api_server.py)
- 기존 파일 URL 반환 엔드포인트들: `/uploads/...` → 서명 URL로 변환
- `GET /api/admin/sign-url?path={rel_path}` 신규 엔드포인트 (관리자 전용)

### Task 5 — 프론트엔드 블랙스크린 + 우클릭 차단
파일: `web_frontend/src/components/FileViewer.tsx` (신규 or 기존 수정)
- 파일 뷰어에서 403 수신 시: 블랙스크린 오버레이 표시
- `onContextMenu={(e) => e.preventDefault()}` — 우클릭 차단
- 이미지/PDF 뷰어에 `pointer-events: none` + `user-select: none`
- 관리자 패널 파일 목록: 클릭 시 서명 URL fetch → 안전한 뷰어에서 표시

## 수정 파일 목록
- `api_server.py` — Task 1,2,3,4 (주 작업)
- `security_middleware.py` — Task 1 (/uploads/ 차단)
- `.env.example` — UPLOAD_SIGN_KEY 추가
- `tools/encrypt_migrate.py` — Task 3 (신규)
- `web_frontend/src/components/FileViewer.tsx` — Task 5 (신규 또는 수정)
- 관리자 패널 파일 표시 컴포넌트 (탐색 후 수정)

## 검증
1. `python -m py_compile api_server.py` → COMPILE_OK
2. `curl /uploads/candidates/xxx/photo.jpg` → 403
3. `curl /api/files/...?expires=...&sig=...` (유효) → 200
4. `curl /api/files/...?expires=expired&sig=...` → 403
5. apply 제출 → master.db.auto_backup 갱신 확인
6. `python tools/encrypt_migrate.py` → migration 완료
7. `npm run build` → error 0
8. DB guardian: candidates=3059, integrity=ok

## 실행 순서
Task 1 → Task 2 → Task 3 migration → Task 4 → Task 5 → 전체 빌드 검증
