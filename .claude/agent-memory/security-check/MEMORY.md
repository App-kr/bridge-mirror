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

### f-string SQL 패턴 (PARTIAL RISK — 2026-03-18 재확인)
아래 패턴들은 f-string으로 SQL을 조립하나, 컬럼명 생성에 사용 (값 삽입 아님).
값은 항상 ? 바인딩. 컬럼명은 화이트리스트 frozenset으로 필터링.
- `UPDATE candidates SET {sets} WHERE candidate_id = ?` (line 1638~1715): sets = "k=?" 문자열 — 값은 바인딩됨
- `UPDATE client_inquiries SET {sets} WHERE id = ?` (line 1837~1864): 동일 패턴
- `INSERT INTO candidates ({cols}) VALUES ({placeholders})` (line 1594~1596): cols는 허용 키셋으로 필터됨
- `SELECT {_COLS} FROM candidates WHERE {where_sql}` (line 1505~1522): _COLS는 하드코딩 문자열, where_sql은 "k=?" 구성
실제 SQL Injection 위험 없음 (컬럼명이 화이트리스트 제어, 값은 모두 ? 바인딩).

### 발견된 WARNING (2026-03-18, 2026-03-18 재점검 완료)

#### WARNING-1: f-string SQL — PASS (진짜 위험 없음)
- 모든 컬럼명 f-string 패턴은 화이트리스트 frozenset 필터 후 사용 (값은 ? 바인딩)
- 신규 예외 발견: `UPDATE candidates SET {col} = ?` (line 2337) — col은 _TEMPLATE_COL_MAP.values()에서만 옴
  → _TEMPLATE_COL_MAP 값: email_contract, email_immigration, email_overseas, email_transition, email_arrival
  → 하드코딩 문자열이므로 injection 불가 — PASS

#### WARNING-2: HMAC_SECRET — PASS (2026-03-19 수정)
- HMAC_SECRET 미설정 시 ADMIN_API_KEY로 폴백 (security_middleware.py line 43)
- 모든 시크릿은 Windows Credential Manager (BX) 관리로 전환 완료
- .env에 평문 키 값 없음 (VAULT 마커만 존재)
- x-admin-key 헤더 일치 시 HMAC 검증 skip (line 617-623) — 의도된 설계

#### WARNING-3: CSP unsafe-inline — WARNING (개선 권장, 즉각 FAIL 아님)
- security_middleware.py line 546: script-src에 'unsafe-inline' 포함
- style-src에도 'unsafe-inline' 포함 (폰트/관리자 UI용)
- Next.js 프론트엔드는 별도 CSP 설정 (이 헤더는 API 서버 응답에만 적용)
- API 서버는 JSON만 반환 — script 실행 없음. unsafe-inline은 실질적 위험 없음
- 그러나 Nonce 방식 전환 권장 (관리자 UI가 API 서버를 직접 프레임하는 경우 대비)

#### FAIL 신규 발견 (2026-03-18 재점검)
- 모든 시크릿은 BX (Windows Credential Manager)로 이전 완료 (2026-03-19)
  → .env에 평문 값 없음 (VAULT 마커만)
  → 파일 탈취 시에도 시크릿 노출 불가
- admin_matching_employers (line 2629): matched/unmatched에 client_inquiries 전체 행 포함
  → school_name, contact_name 등 PII 필드가 관리자 응답에 포함 (의도된 설계)
  → x-admin-key가 있으면 PIIMaskingMiddleware 통과 — 관리자 전용이므로 PASS
- profile_sends.to_email: employer 이메일 평문 저장 (line 2704) — 로그 DB 별도 보호 필요

#### HMAC 폴백 아키텍처 정리
- HMAC_SECRET 미설정 → ADMIN_API_KEY 폴백 (security_middleware.py line 43)
- x-admin-key 헤더 일치 시 HMAC 검증 skip (line 617-623) — 의도된 설계
- verify_hmac()에서 ADMIN_API_KEY도 secrets_to_try에 추가 (line 453-456) — 이중 검증
- 모든 키 값은 BX (Windows Credential Manager)에서 런타임 로드 — 파일에 평문 없음

### 점검 범위 파일
- `api_server.py` — 전체 읽기 완료 (2026-03-16, 2026-03-18 재확인)
- `security_middleware.py` — 전체 읽기 완료 (2026-03-18)
- `web_frontend/src/types/index.ts` — PublicJob 타입 확인
- `web_frontend/src/components/JobCard.tsx` — enc_* 없음
- `web_frontend/src/components/JobDetailModal.tsx` — enc_* 없음, dangerouslySetInnerHTML 미사용
- `web_frontend/src/components/MarkdownBody.tsx` — dangerouslySetInnerHTML 미사용, React 노드 직접 렌더
- `web_frontend/src/components/admin/SplitEditor.tsx` — dangerouslySetInnerHTML 사용 확인
  → DOMPurify.sanitize() 통과 후 사용 (line 57-80) — PASS
- `web_frontend/src/hooks/useAdminAuth.ts` — 하드코딩 비밀번호 없음, API 경유 로그인
- `web_frontend/src/lib/api.ts` — NEXT_PUBLIC_API_URL만 사용, 하드코딩 시크릿 없음
- `web_frontend/.env.production` — NEXT_PUBLIC_API_URL만 포함, 민감 시크릿 없음
- `web_frontend/src/app/jobs/page.tsx` — PublicJob 타입만 사용
- `web_frontend/src/app/jobs/[id]/page.tsx` — 존재하지 않음 (modal 방식 사용)
- `.gitignore` — .env, .bridge.key 제외 확인 (PASS)
