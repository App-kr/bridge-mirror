# Security Check Agent — Memory

## Project: bridge base (api_server.py)

### PII 보안 아키텍처 (확인 완료 2026-03-16)
- `PIIMaskingMiddleware` (line 255): 모든 JSON 응답에 적용, _scrub_obj() 재귀 처리
- `_PII_BLOCKED_KEYS` (line 181): school_name, name, contact_*, phone, email, address 등 키 자체 제거
- `_PII_PATTERNS` (line 206): 잔류 PII 정규식 마스킹 (전화, 이메일, 사업자번호, 주민번호)
- 관리자 /api/admin/* + 올바른 x-admin-key 헤더 → 미들웨어 PII 마스킹 통과 (의도된 설계)

### 공개 엔드포인트 PII 상태 (CLEAN)
- `_job_row_to_public()` (line 604): enc_* 필드 일체 포함 안 함. 위치·급여·근무조건만 반환
- `PublicJob` 타입: enc_employer_name 등 enc_* 필드 없음. 완전 분리
- `/api/community/{board}`: author_hash(SHA-256 앞 16자) 반환 — 재식별 불가
- `POST /api/apply` 응답: id + apply_token + mode만 반환
- `POST /api/inquiry` 응답: id만 반환
- `POST /api/admin/sync/incoming` 응답: HMAC 검증 필수 (fail-closed), id + type만 반환

### 관리자 엔드포인트 PII 처리 방식
- `/api/admin/candidates` (line 1410): _decrypt_row()로 복호화 후 반환 — 의도된 설계
- `/api/admin/applications` (line 3015): candidates 블록에서 full_name, email, mobile_phone 평문 반환
  → 관리자 엔드포인트이므로 x-admin-key 헤더 있으면 미들웨어 통과 (의도된 설계)
  → 단, _decrypt_row() 미호출 — 암호화된 값이 그대로 반환될 수 있음 (주의사항)
- `/api/admin/matching/employers` (line 2532): candidate.full_name을 평문으로 응답에 포함
  → 이 필드는 암호화 저장된 것이나 DB에서 읽은 후 복호화 없이 반환 (암호화 상태로 노출)
- `/api/admin/jobs/v2` (line 4919): SELECT * 후 전체 컬럼 반환 (enc_* 포함)
  → 관리자 엔드포인트이므로 의도된 설계

### 알려진 주의사항
- `_CONTENT_FIELDS` (line 233): body, description 등 콘텐츠 필드는 값 레벨 정규식 스캔 제외
  → 관리자가 작성한 공개 게시글 본문에 이메일/전화 의도 포함 가능 (설계상 허용)
- `raw_text` 필드: 서버에서 괄호 블록 `()` 제거 후 공개. 프론트에서도 이중 필터
- community_create (POST): 게시글 제출 시 PII 패턴(전화/이메일) 포함 시 400 차단
- `kakao_id` / `sns` / `instagram` / `facebook` — _PII_BLOCKED_KEYS에 없음
  → kakaotalk 필드는 candidates DB에 암호화 저장. 공개 API에는 미반환 (clean)
  → 그러나 _PII_BLOCKED_KEYS에 "kakaotalk" 키가 없어 미들웨어 키 차단 미적용 (패턴 스캔은 적용)
- `recruiter_memo` — _PII_BLOCKED_KEYS에 없음. 관리자 엔드포인트에만 노출되므로 허용 범위
- `memo`, `memo_kr`, `memo_en` — client_inquiries에 존재. inquiry endpoint에서 암호화 저장

### 점검 범위 파일
- `api_server.py` — 전체 읽기 완료 (2026-03-16)
- `web_frontend/src/types/index.ts` — PublicJob 타입 확인
- `web_frontend/src/components/JobCard.tsx` — enc_* 없음
- `web_frontend/src/components/JobDetailModal.tsx` — enc_* 없음
- `web_frontend/src/app/jobs/page.tsx` — PublicJob 타입만 사용
- `web_frontend/src/app/jobs/[id]/page.tsx` — 존재하지 않음 (modal 방식 사용)
