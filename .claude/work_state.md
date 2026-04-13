# BRIDGE 작업 상태 (세션 간 유지)
최근 업데이트: 2026-04-13 (세션 35 — Phase 4 완료 + git 진단)

## ⏭ 다음 세션 우선순위 (2026-04-13 기준)

1. ~~**Canvas Sheet 가상 렌더링 (Phase 4)**~~ ✅ 완료 (c1954c6a, 86ed207f, a9bc23bb)
2. ~~**master.db git tracking 제거**~~ ✅ 불필요 — 한 번도 커밋된 적 없음 (.gitignore 정상 차단 확인)
3. **security_vault.py 3중 AES-256-GCM** — T3v1 포맷 구현
4. **encrypt_migrate.py PII 필드 확장** — candidates + client_inquiries 전체

## ✅ 2026-04-13 점검 완료 (세션 34)

### 안정성 점검 결과
- OPUS_MASTER_PROMPT.md → .bak 폐기 (9개 중 4개 이미 해결, 경로 오류 다수)
- Render 배포: autoDeploy=true, HEAD=origin/main=6dc6a9de — 이미 최신 배포됨
- bridge_jobs 광고매니저 CRUD: 커밋 587d8f8c에서 이미 완료 (API+UI 전부 존재)
- pre_snapshot.py: Write/Edit/MultiEdit 훅 정상 동작 확인 (5건 테스트 전부 PASS)
- EMERGENCY_RESTORE.bat: `head -10` 버그 수정 + `setlocal enabledelayedexpansion` 추가
- target_age 중복: L692에 1건만 존재, 이미 해결됨

## ✅ 2026-04-11 완료된 작업 (세션 33 — 커밋 9cf17a0e)

### Craigslist RPA 복구 완료

#### 원인
- `--headless=new` → Craigslist 봇 감지 → category 단계 무한 로딩
- rpa_relogin.py가 `account="default"` 프로필에 쿠키 저장 → 실제 RPA는 `account="gray"` 사용 → 쿠키 미적용
- RPA.vbs에 `--account` 미지정 → 팝업에서 brown 계정 선택 → 이메일 인증 실패

#### 수정 (커밋 9cf17a0e)
- `craigslist_auto_rpa.py`: Selenium fallback에서 `--headless=new` 제거 → `--window-position=-10000,0` (사용자 안보이나 headless 아님)
- `RPA.vbs`: `--account gray` 추가 → 팝업 없이 gray 계정 직접 실행
- `rpa_relogin.py`: `account="default"` → `account="gray"` (gray 프로필에 쿠키)

#### 검증
- Job.1960 (Guri | Kindy - Elem) 실제 게시 완료 ✅
- URL: https://post.craigslist.org/k/gooy13dL2cRnK8UmUMde4Z/rT74O
- 스크린샷: screenshots/craigslist/Job.1960_20260411_011929.png

#### RPA 실행 방법
- 일반 실행: `RPA.vbs` 더블클릭 (gray 계정, headless, 10건)
- 쿠키 갱신: `python rpa_relogin.py` (쿠키 만료 시)
- 수동 테스트: `python craigslist_auto_rpa.py --account gray --headless --limit 1`

## ✅ 2026-04-10 완료된 작업 (세션 32 — 커밋 a574bce1, 5f6ea40e)

### 보안 훅 3종 + pytest 뼈대

#### bridge_agent 패치 (커밋 a574bce1)
- `base.py`: tool result 2차 인젝션 차단 (`<tool_output>` 구조적 격리)
- `security_check.py`: `_guard_context()` — context 파일 sanitize + 길이 제한
- `skills/loader.py`: allowlist + resolve() 경로탈주 차단

#### bridge_guard.py 신규 (커밋 5f6ea40e)
- 경로: `.claude/hooks/bridge_guard.py`
- PreToolUse 훅: Bash/Write/Edit/WebFetch 위험 패턴 차단
- Bash: `rm -rf` / force push / sqlite3 DROP TABLE / 프로덕션 curl POST
- Write/Edit: 경로탈주 / .env / master.db / 시스템경로
- WebFetch: 프로덕션 쓰기 메서드 (POST/PATCH/DELETE)
- ALLOWED_WRITE_ROOTS에 Q:\openrun_api/app/admin 추가됨 (사용자 수동 수정)
- 오탐 방지: heredoc 제거 + 명령 경계 regex 적용

#### tests/ 신규 (커밋 5f6ea40e)
- `conftest.py`: 인메모리 SQLite + TestClient (Production 미사용)
- `test_auth.py`: 15개 케이스 — 403/429/세션토큰/공개API

#### 글로벌 훅 추가 (`C:\Users\Scarlett\.claude\settings.json`)
- PostToolUse Read: `read_guard.py` (경로탈주 + 인젝션 스캔)
- PreToolUse Write|Edit|MultiEdit: `pre_snapshot.py` (사용자 설정)
- PreToolUse Bash|Write|Edit|WebFetch: `bridge_guard.py`

## ✅ 2026-04-08 완료된 작업 (세션 30 — 커밋 9ebcf5c5)

### admin/sheet + admin/employers 값 저장 버그 수정 (커밋 6fe51756, 9ebcf5c5)

#### 문제
1. `BridgeAdminSheet`: `stage`, `mailStatus` 변경이 localStorage에만 저장, DB 저장 없음
2. `EmployerManagement`: `memo`, `notes`(본문수정) 변경이 로컬 state에만, DB 저장 없음

#### 수정 내용
- `BridgeAdminSheet.tsx`
  - `FB_MAP` 상수 추가: 프론트 필드명 → 백엔드 DB 컬럼명 매핑 (28개 필드)
  - `patchDB(cid, body)` 헬퍼: PATCH `/api/admin/candidates/{cid}` 호출
  - `setSt`, `tMT`, `setField`, `cE` 모두 `patchDB` 연동 → 변경 즉시 DB 저장
  - `proposal` 필드: `c.recruiter_memo` fallback 추가
- `api_server.py`
  - `StatusUpdate` 모델: `memo`, `notes` Optional 필드 추가
  - PATCH `/api/admin/applications/{id}`: memo/notes 저장 지원
    - `jobs`: `memo → internal_notes`(암호화), `notes → raw_text`
    - `inq_`: `memo → client_inquiries.memo`(암호화), `notes → client_inquiries.notes`
- `EmployerManagement.tsx`
  - `editMemo`, `editNotes`: 로컬 state + DB PATCH 동시 저장

⚠️ Render 배포 필요: api_server.py 변경됨
- Render 대시보드 → bridge-api → Manual Deploy

## ✅ 2026-04-08 완료된 작업 (세션 29 — 커밋 9e82e9f8)

### 소개 메일 발송 시스템 (원어민 관리 확장)

#### 백엔드 (api_server.py — 이전 세션 미커밋분 포함)
- `mail_introduce_log` 테이블 신규 생성 (DB 스키마)
- `GET /api/admin/employers-for-mail` — 구인자 목록 (위치/대상연령 필터)
- `POST /api/admin/mail/introduce` — 소개 메일 자동 발송
  - 강사 sheet_number 기반 프로필 조회
  - CV presigned URL (S3, 유효기간 설정 가능)
  - `_build_teacher_html_block()` — 강사 HTML 블록 생성
  - 구인자별 개별 발송 + 발송 로그 기록
- `GET /api/admin/mail/introduce-log` — 발송 이력 조회

#### 프론트엔드
- `web_frontend/src/app/admin/introduce-mail/page.tsx` **신규 생성**
  - 강사 선택: sheet_number 자유 입력 (쉼표/줄바꿈)
  - 구인자 선택: 목록 불러오기 + 위치/연령 필터 + 다중선택
  - 발송 설정: 발신자, CV 링크 유효기간(3~30일), 추가 메시지
  - 발송 결과 표시 + 발송 이력 테이블
- `AdminSidebar.tsx`: 메일 관리 섹션에 "소개 메일 발송" 추가
- `layout.tsx` + `MegaMenu.tsx`: /talents/login 인재보기 네비 추가

#### 배포
- push → Render 자동 배포 진행 중 (autoDeploy: true)
- Vercel 자동 배포 (프론트엔드)

### ⚠️ 다음 세션 확인 사항
1. Render 배포 완료 확인 → /api/admin/employers-for-mail 응답 확인
2. mail_introduce_log 테이블 자동 생성 확인 (api_server.py _ensure_* 함수에 포함됨)
3. 소개 메일 실제 발송 테스트 (1건)
4. SMTP 설정 확인 — naver/gmail SMTP_CONFIG 키 일치 여부

---

## 세션 재시작 방법
1. `/clear`
2. `@.claude/work_state.md`

---

## ✅ 2026-04-07 완료된 작업 (세션 28)

### Sprint D: LinkPanel 양방향 연동 패널 (커밋 e3751b8d)
- `web_frontend/src/app/admin/components/LinkPanel.tsx` **신규 생성**
  - 420px 오른쪽 고정 오버레이 패널, employer/candidate 듀얼 모드
  - employer 모드: `/api/admin/matching/candidates-for-job` + 이력서 iframe
  - candidate 모드: `/api/admin/matching/jobs-for-candidate` + 인터뷰 목록
- `DocBlock.tsx`: `onLinkPanel` prop → [매칭 연동] 버튼
- `EmployerManagement.tsx`: linkPanel state + [연동] 버튼 + LinkPanel 렌더
- `BridgeAdminSheet.tsx`: 우클릭 컨텍스트 메뉴 [매칭 연동] + LinkPanel 렌더
- `MailComposer.tsx`: ■XXXX 자동 스캔 + 이력서 자동첨부

### Render Cold Start 수정 (커밋 2d63a6d8)
- `useAdminAuth.ts`: MAX_WAKE_RETRIES 3 → 20 (60초)
- `AdminAuth.tsx`: 경과초 + 앰버 프로그레스 바

### 긴급 안정성 패치 (커밋 6be067ba) — main push 완료
- ① render.yaml autoDeploy true → **false**
- ② api_server.py: `/api/admin/db/dump` 신규 엔드포인트
- ② tools/render_db_backup.py 신규 (Render DB → 로컬 SQL, 30일 자동삭제)
- ④ LOCAL-DISABLED 7개 주석 명시 (모두 S3 마이그레이션, 버그 아님)
- ⑤ src/lib/api.ts 단일 진실 → db.ts / jobs/route.ts / talent-auth 2개 import 통일
- ⑥ tsconfig.tsbuildinfo .gitignore 확인 완료

### ⚠️ 다음 세션 첫 작업 (필수)
1. **Render 수동 배포**: Render 대시보드 → bridge-api → Manual Deploy
   (api_server.py DB dump 엔드포인트 반영 필요)
2. 배포 후 `python "Q:\Claudework\bridge base\tools\render_db_backup.py"` 테스트
3. 3순위 보고 항목: ③ BRIDGE_FIELD_KEY W1/W2 일치 여부, ⑧ CORS_ORIGINS 현황

---

## ✅ 2026-04-01 완료된 작업 (세션 27 추가)

### doc_processor.py v2.7 ✅ 완료 (커밋 7dd93de0, d310c3df)
- **RE_KR_RESIDENTIAL → PDF _build_search_patterns() 추가**: 부영 1차 아파트 등 한국 아파트명 PDF에서도 삭제
- **SCHOOL 패턴 줄 단위 스캔**: ndent School 잔류 버그 수정 (페이지 전체 텍스트 → 줄별 스캔)
- **이름 줄 단위 폴백**: Nandi Mthembu 같은 케이스 풀네임 미검출 시 줄 단위 재시도
- **전 세계 PII 패턴 추가**: RE_SCHOOL_NAMED, RE_UNIV_OF, RE_US_CITY_STATE, RE_FOREIGN_CITY, RE_AGE_MENTION, RE_VISA_STATUS
- **Pass 2.7/2.8**: 학교명 → University/School 일반화, 외국 도시/나이/비자 삭제
- **전화 False Positive 수정**: 연도 범위 (2017-2021 등) 전화번호로 오인식 차단
- **KR_WORKPLACE_KEYWORDS**: "april" 제거 (April 2016 오인식 방지)

### api_server.py 사진 S3 폴백 ✅ 완료 (커밋 3c910d4b)
- **DB photo_url 조회 추가**: SELECT에 photo_url 컬럼 추가
- **S3 폴백**: 폼 사진 없으면 DB photo_url → s3_download_bytes() → 임시파일 생성
- **오류 로깅 추가**: 기존 `except Exception: pass` → logging.warning() 출력

### 2026-04-01 이전 완료 (세션 26)
#### Python D:\Phtyon 3 → Q:\Phtyon 3 이동 ✅
- `Q:\Phtyon 3\python.exe` (3.10.0) 정상 동작
- `D:\Phtyon 3` → Junction으로 대체 (하위 호환 유지)
- `D:\Python314` 삭제 완료

#### doc_processor.py v2.6 ✅
- 이름: 성(Last name)만 삭제, 이름 유지 — DOCX + PDF
- RE_KR_RESIDENTIAL 추가 (아파트/빌라/오피스텔 등)
- KR_WORKPLACE_KEYWORDS 확장
- Reference 섹션 자동 감지 + 완전 삭제 (_REF_HEADERS)
- PII 라벨 (nationality/citizenship/race/ethnicity/religion) 줄 삭제
- 국적 자동 추출 + DB 업데이트 (_extract_nationality_from_text)

#### api_server.py (v2.6) ✅
- files_photo → temp파일 → photo_tmp_path 전달
- brj_number = int(candidate_id) 사용
- candidate_dict에 sheet_number, nationality 포함

---

---

## ⚠️ 내일 이어서 할 작업 (우선순위 순) — 2026-04-03 업데이트

### 0순위: Make 계정 연동 복구
- Make(구 Integromat) 계정 잠금 해제 확인
- 기존 시나리오 연결 상태 점검 및 재연동

### T002: Teacher ID 5자리 전환
- 4자리(1000~9000) → 5자리(10000+) 전환
- 이력서·영상·Client Sheet·New Sheet 전체 동기화

### T005: RPA Tkinter 안정화
- 이모지 → 텍스트 레이블 전면 교체 (GDI deadlock 방지)
- headless=new 모드 안정성 검증

### T007: Inbox API 추가 작업
- 세부 사항 확인 후 진행

### 1순위: 이력서 변환기 실제 테스트 [Render 배포 후]
- Render 대시보드 → bridge-n7hk → Manual Deploy 클릭 (아직 미배포)
- 배포 후 /admin/resume-converter에서 테스트:
  - PDF + 사진 함께 업로드 → 사진 삽입 확인
  - PDF만 업로드 (사진 미업로드) → S3 폴백 작동 확인
  - 이름(성 삭제/이름 유지), 아파트명, 학교명 결과 확인
- Render 로그에서 `[RESUME]` 로그 확인

### 2순위: doc_processor 추가 테스트 (7개 샘플 파일 기준)

### 완료된 것 (세션 18)
- `tools/master_vault.py` — Session-Ephemeral AES-256-GCM vault (c3aefce) ✅
- `tools/migrate_env_to_vault.py` — .env → vault 마이그레이션 스크립트 ✅
- `security_vault.py` — vault 폴백 추가 (.env 없어도 동작) ✅
- `.gitignore` — .vault.enc.json 추가 ✅
- ClaudeBlog AES-256-GCM 업그레이드 (encrypt_secrets.py + secret_loader.py) ✅
- Gemini 잘못된 변경 5파일 되돌림 (from secure_vault import 오류 제거) ✅
- web_frontend/.env.production 복원 ✅

### 미완료 — 내일 이어서 할 것 (우선순위 순)

#### 1순위: master.db → git 완전 소각 [매우 중요]
- `git rm --cached master.db` (git tracking 제거)
- `.gitignore`에서 `!master.db` 예외 제거 → `*.db`만 남기기
- `git filter-repo --path master.db --invert-paths` (히스토리 소각)
- `git push --force` (force push 필요)
- **주의**: Render는 `/data/master.db` 별도 사용 → 영향 없음

#### 2순위: security_vault.py → 3중 AES-256-GCM 암호화 추가
설계 확정:
```
T3v1 포맷: magic(4) + nonce1(12) + nonce2(12) + nonce3(12) + ciphertext
L1_key = SHA-256(base_key + b"L1" + column_name)
L2_key = SHA-256(base_key + b"L2" + nonce1)
L3_key = SHA-256(base_key + b"L3" + nonce2 + nonce1)
ct1 = AES-GCM(L1_key, n1).encrypt(plaintext)
ct2 = AES-GCM(L2_key, n2).encrypt(ct1)
ct3 = AES-GCM(L3_key, n3).encrypt(ct2)
output = base64(T3v1 + n1 + n2 + n3 + ct3)
최소 출력: ~124자 (30자 이상 보장)
```
추가 함수:
- `triple_encrypt_field(plaintext, column_name)` — 3중 암호화
- `triple_decrypt_field(encoded, column_name)` — 3중 복호화
- `auto_decrypt_value(value, column_name)` — T3v1/단순 자동 판별
- `is_t3_encrypted(value)` — T3v1 감지
- `rotate_db_encryption(db_path)` — 전체 DB 재암호화 (세션 변경 효과)

#### 3순위: encrypt_migrate.py → 전체 PII 필드 확장
현재: dob, nationality, current_location, reference, korean_criminal_record (일부)
추가 필요 (candidates):
- name, email, phone, kakao_id
- gender, passport_number, home_country, emergency_contact
기존 단일암호화 → T3v1 마이그레이션 포함

추가 필요 (client_inquiries) — 업체 1100명 포함:
- contact_name, email, phone, company_name, business_registration
- school_name(=school_location), memo

#### 4순위: api_server.py → auto_decrypt 적용
- `auto_decrypt_value()` 사용하는 `_decrypt_candidate_full(row)` 헬퍼
- 관리자 엔드포인트 읽기 시 자동 복호화
- 3중암호화된 값도 투명하게 복호화

### 사용자 요구사항 (반드시 준수)
- 관리자(나)에게는 원문 표시
- git/외부에는 절대 평문 없음
- 3중암호화 + 세션마다 자동변경 (rotate_db_encryption 실행 시)
- 30자 이상 암호화값 (설계상 ~124자)
- 업체 연락처(client_inquiries) 포함 모든 PII

### 현재 커밋 상태
- 최신: c3aefce (MasterVault v3.0)
- master.db 아직 git tracking 중 → 내일 제거 필요
- .env 파일 없음 → vault setup 필요

### BRIDGE_FIELD_KEY 상태
- .env 삭제됨, 백업에도 없음
- 새 키 입력 필요: `python tools/master_vault.py setup`
- BRIDGE_FIELD_KEY 새로 입력하면 기존 암호화 4개 필드는 null 처리 후 재입력

### Render 환경변수 (별도 관리 중, 영향 없음)
- BRIDGE_FIELD_KEY, JWT_SECRET 등 Render 대시보드에 설정됨
- /data/master.db (1GB 영구디스크) — git master.db와 무관

## 2026-03-27 세션 20 (RPA 자동화 작업 완료)
- feat(rpa): Craigslist 자동 게시 + 3중 암호화 자격증명 관리 시스템
  - `craigslist_auto_rpa.py` — Selenium 기반 Craigslist 자동 게시
    - master.db jobs → 광고 생성 → Seoul Craigslist 자동 게시
    - PII 마스킹: 회사명·연락처·이메일 완전 차단
    - 파일 무결성 검증 (SHA-256) + 해킹 감지
    - 다중 계정 지원 (--account 플래그)
    - 옵션: --dry-run / --generate / --limit / --job-code / --headless
    - 구조화 에러 로그 (JSON 포맷, rpa_error.log)

  - `tools/rpa_credential_vault.py` — Session-Ephemeral 3중 AES-256-GCM 자격증명 보관소
    - setup: 이메일/비밀번호 입력 → 3중 암호화 저장 (.rpa_vault.enc.json)
    - rotate: 매 실행마다 새 salt/nonce 생성 (같은 값도 매번 다른 암호문)
    - get_decrypted: 프로그래밍 방식 읽기 (RPA 내부 사용)
    - PBKDF2 600k iterations + AESGCM
    - 클립보드 자동 복사 + 메모리 소각

  - `scripts/migrate_python_to_q.*` — Python 마이그레이션 배치
    - .bat: 관리자 권한 확인 + PowerShell 호출
    - .ps1: C/D 드라이브의 Python → Q 드라이브 복사 + PATH 업데이트

- **상태**: 파일 완성 ✅ / Git 추가 대기 ⏳
  - gitleaks hook 이슈: "no leaks found" 반환 후 exit code 1
  - craigslist_auto_rpa.py: 46줄 변경 (46 +++---)
  - 3개 신규 파일: tools/rpa_credential_vault.py (343줄), scripts/*.bat/*.ps1 (245줄)
  - 총 616줄 추가

- **파일 위치** (Q 드라이브 저장됨, 손실 없음):
  - `Q:/Claudework/bridge base/craigslist_auto_rpa.py`
  - `Q:/Claudework/bridge base/tools/rpa_credential_vault.py`
  - `Q:/Claudework/bridge base/scripts/migrate_python_to_q.bat`
  - `Q:/Claudework/bridge base/scripts/migrate_python_to_q.ps1`

- **다음 단계**:
  1. gitleaks hook 재점검 필요
  2. Commit 재시도
  3. GitHub push
  4. Craigslist 자동 게시 E2E 테스트 (한 건 시도)

- **PC 다운 상황**: 안전하게 파일 백업 + 상태 기록 완료

## 2026-03-26 세션 17 (Settings 오류 수정 + 라우터 다운 전 백업)
- fix(settings): settings.local.json 잘못된 CLAUDE_TOOL_NAME 패턴 6개 제거 (`8298e06`)
  - 이전 훅 스크립트가 남긴 `CLAUDE_TOOL_NAME=Bash` 포함 비정상 항목 792→786개
  - :* 문법 오류로 Claude Code 시작 시 Settings Error 발생하던 문제 해결
  - 인덱스: [778], [780], [786], [787], [788], [791]
- **특이사항**: 해킹 시도 극심으로 오늘밤 공유기 차단 예정 — 재시작 후 이 파일로 복구

## ⚠️ 라우터 재연결 후 체크리스트
1. Render 백엔드 (api.bridgejob.co.kr) 정상 응답 확인
2. Vercel 프론트엔드 (bridgejob.co.kr) 정상 로드 확인
3. 관리자 로그인 → 세션 토큰 재발급 확인
4. 텔레그램 알림 재연결 확인
5. 공격 로그 확인: api_server.py 감사 로그 / security_log.jsonl

## 2026-03-24 세션 16 (OPUS Final 보안 강화)
- fix(security): 보안 감사 6건 수정 (`47d9bbb`)
  - [HIGH] /api/upload 인증 누락 → _check_admin 전체 적용
  - [HIGH] SMTP 예외 메시지 노출 → 일반 메시지로 교체
  - [MEDIUM] 메일 rate limit 우회 → _mail_rate_check 추가
  - [MEDIUM] employer email 평문 응답 → 마스킹 처리
  - [LOW] change-password PBKDF2 해시 노출 제거
  - [LOW] S3 업로드 오류 메시지 노출 제거
- fix(security): 쿠키 SameSite/Secure 플래그 4곳 통일 (`6113b79`)
  - AdminAuthContext, EditModeBar, AdminSidebar, admin/page
- fix(api): brute-force + 상위 보안 시스템 (`bf188d1`)
  - **세션 토큰 시스템**: /24 서브넷 바인딩, 8시간 만료, 슬라이딩 갱신
  - **ADMIN_ALLOWED_IPS 화이트리스트**: CIDR 지원, 환경변수 설정
  - **CSRF Origin 검증**: 관리자 mutation 요청의 Origin 헤더 검증
  - **AdminAuditMiddleware**: 모든 admin POST/PATCH/DELETE 감사 로그
  - **BodySizeLimitMiddleware**: 10MB 요청 크기 제한
  - **TrustedHostMiddleware**: 허용 도메인만 접근
  - 세션 관리 API: /logout, /sessions, /sessions(DELETE)
- feat(security): 세션 토큰 프론트엔드 지원 (`f7a9547`)
  - useAdminAuth: session_token 저장/전송/폐기
  - headers/signedFetch/adminFetch 모두 x-admin-token 헤더 자동 첨부

### 보안 계층 현황 (7계층)
| # | 계층 | 상태 |
|---|------|------|
| 1 | HMAC 서명 (X-Bridge-Signature) | ✅ |
| 2 | 세션 토큰 (/24 서브넷 바인딩) | ✅ NEW |
| 3 | IP 화이트리스트 (ADMIN_ALLOWED_IPS) | ✅ NEW |
| 4 | IP 블랙리스트 (누진차단+허니팟) | ✅ |
| 5 | Rate Limiting (엔드포인트별+국가별) | ✅ |
| 6 | 공격 탐지 (SQLi/XSS/SSRF/LLM) | ✅ |
| 7 | CSRF Origin 검증 | ✅ NEW |

## 2026-03-23 세션 15 (안정화 + 상태 점검)
- fix(employers): Error Boundary + DOMPurify 안전화 (`bd221c6`)
  - Vercel 런타임 크래시 방지: EmployerErrorBoundary 클래스 추가
  - DOMPurify require() try/catch 래핑
  - mapJobsV2 null 입력 방어, useEffect cleanup
- fix(stability): sheet_number 동시접수 race condition 제거 (`967bce4`)
- 미완료 목록 정리: og-image/securityGuard/Cookie/CSP 이미 완료 확인 → 제거

## 2026-03-23 세션 14 완료 (자동화 확장 — CV 파이프라인 + 서버 스레드)
- feat(auto-process): CV 업로드 시 PII 자동 제거 파이프라인 (`ada2665`)
  - _auto_process_resume: 백그라운드 스레드로 S3 원본 보관 + processed 버전 별도 저장
  - MailModal: 이력서 자동첨부 토글 (attach_cv_ids)
  - FormData/JSON 듀얼 파싱, MIME 첨부 지원
  - DB: cv_processed_s3_key, file_uploads.s3_key 컬럼 추가
- fix(auto-process): 1차 감사 3건 수정 (`f621535`)
  - Critical: sheet_number 없는 웹 지원자 스킵 → candidate_id 숫자 폴백
  - S3 orphan 정리 + CRUD 엔드포인트 3개 추가
- fix(auto-process): 2차 감사 3건 수정 (`4a0e1fa`)
  - photo_url UPDATE WHERE id→candidate_id
  - 수동 첨부파일 drop 버그 수정
  - busy_timeout 추가
- feat(auto): sheet_number 웹폼 자동 할당 + 리마인더 스레드 (`3e7f85c`)
  - /api/apply INSERT 시 MAX(sheet_number)+1 자동 할당 (최소 10000)
  - 인터뷰 리마인더 백그라운드 스레드 (10분 주기, Render 서버 내장)

## 2026-03-23 세션 13 완료 (데이터 동기화 + Inbox API)
- fix(data): interview 이중매핑 수정 (`97f6ca9`)
  - NEW_COL_MAP col 17: `interview_time` → `recruiter_memo` (포지션제안 한국어 메모)
  - col 17 "Interview" = 지원처/제안 메모 ≠ col 21 "Interview time" = 가용시간
  - 12건 recruiter_memo 업데이트, 전체 40명 × 9필드 검증 — 불일치 0건
  - ichigo.milk@me.com (Wendy Veronie) INSERT 완료
  - 중복 Thobeka Mhlongo 논리삭제 (Active 40명 유지)
- feat(inbox): 상세/메모/배정 3개 엔드포인트 추가 (`0aecfc1`)
  - GET /api/admin/inbox/{id} — 상세 조회
  - PATCH /api/admin/inbox/{id}/notes — 메모 저장
  - PATCH /api/admin/inbox/{id}/assign — 담당자 배정
  - inbox_api.py에 구현 (inbox/[id]/page.tsx 프론트엔드 호출 커버)

## 2026-03-23 세션 12 완료 (CV 자동처리 + 메일 이력서 자동첨부)
- feat(auto-process): CV 업로드 시 PII 자동 제거 파이프라인
  - api_server.py: `_auto_process_resume()` 백그라운드 태스크
  - 업로드 시 자동 트리거: candidate + cv/cover_letter → threading.Thread
  - S3 원본 보관 + processed 버전 별도 저장 (`cv_processed.pdf`)
  - DB: `candidates.cv_processed_s3_key` + `file_uploads.s3_key` 컬럼 추가
  - doc_processor.py `process_pdf()` 서버사이드 import (Render 호환)
  - GET `/api/admin/candidates/{id}/processed-cv` presigned URL 엔드포인트
- feat(storage): `download_bytes()` + `upload_bytes_sync()` 추가 (threading용)
- fix(mail): `_handle_mail_send` FormData 지원 (기존 JSON + 신규 FormData)
  - 이메일에 processed CV MIME 첨부 (`attach_cv_ids` 파라미터)
  - `MIMEMultipart("mixed")` + `MIMEBase("application", "pdf")` 첨부
- feat(MailModal): 이력서 자동첨부 토글 체크박스
  - 활성화 시 수신자 candidate_id → 서버에서 S3 다운로드+첨부
- requirements.txt: `PyMuPDF>=1.24.0,<2.0` 추가

## 2026-03-23 세션 11 완료 (doc_processor v2.3 PII 완전삭제)
- feat(doc_processor): v2.3 완성 (`86f56e4`)
  - PII_LINE_LABELS 확장: permanent address, u.k./korean telephone 등
  - KR_WORKPLACE_KEYWORDS 확장: slp, rise, altiora, emg education 등 30+
  - Pass 2.5: 한국 경력 → "S.Korea" + 날짜만 / 도시명·학원명 삭제
  - _build_output_filename(): `3060영국_여(76born).docx` 포맷 자동생성
  - find_candidate_by_email: dob/gender 반환 추가
  - 하이퍼링크 강제 클리어 (python-docx 한계 우회)
  - cmd_batch/cmd_process/cmd_download: out_name 일괄 교체

## 2026-03-23 세션 10 완료 (PWA Push 알림 시스템)
- feat(pwa): push notifications + mobile settings (`839fd5b`)
  - push_api.py: Web Push API (pywebpush RFC 8291 암호화)
    - /subscribe, /unsubscribe, /test, /broadcast, /vapid-key
    - push_subscriptions DB 테이블, 만료 구독 자동 비활성화
  - api_server.py: push 라우터 등록 + apply/inquiry 접수 시 자동 푸시
  - usePushNotification.ts: 구독/해제/테스트 React 훅
  - /admin/m/settings: 푸시 토글, 테스트 버튼, PWA 설치, 로그아웃
  - Mobile layout: 헤더 알림 벨 아이콘 (미설정 시 빨간 점)
  - MobileTabBar: 더보기 메뉴에 설정 추가
  - tg_notify.py: 텔레그램 알림 유틸리티
  - requirements.txt: pywebpush 추가
- **미완료**: Render 환경변수에 VAPID 키 등록 필요 (Scarlett 직접)

## 2026-03-23 세션 9 완료 (병렬 보안+자동화+SEO)
- feat(seo): 4개 페이지 metadata layout.tsx (`43f97dd`)
  - about/apply/inquiry/jobs — OpenGraph + description
- feat(security+automation): Cookie Secure + doc_processor v2.2 (`2af0803`)
  - useAdminAuth: SameSite=Strict + Secure (localhost 예외)
  - securityGuard: API_URL import 수정
  - doc_processor v2.2: init-db 명령 + file_uploads DB 기록
  - auto_finalize: incoming/ batch 자동 트리거
  - master.db: file_uploads 테이블 생성
- sql.js 미사용 확인 (package.json에만 존재, import 0건)

## 2026-03-23 세션 8 완료 (doc_processor v2.1 파이프라인)
- feat(tools): doc_processor v2.1 (`ae31962`)
  - PDF redaction: location→"Korea" 대체 텍스트 삽입 (기존: 흰 박스만)
  - `batch` 명령: incoming/ 폴더 일괄 처리 + 완료 후 자동 제거
  - `download` 명령: S3 boto3 다운로드 + 자동 처리
  - `setup` 명령: 폴더 상태 확인
  - `doc_run.bat`: Windows 원클릭 런처
  - 폴더 구조: incoming/ → processed/ + originals/ + logs/
  - E2E 테스트 통과 (PDF Korea삽입 + DOCX PII삭제 + 감사로그)

## 2026-03-23 세션 7 (백업 + 문서 정리)
- 구조화 백업: `Q:\Claudework\bridge backup\` 생성
  - memory/ config/ db/ env/ — 8개 파일 날짜별 보관
- work-history.md 전면 재작성 (3/20→3/23 전체 커밋 반영)
- MEMORY.md 최신화

## 2026-03-23 세션 6 완료 (Employer 본문 정리 + 사이드바 + 복사)
- fix(employers): rawText 지역 첫줄 자동 주입 (`a4cdca4`)
- fix(sidebar): 업체관리→인력관리, 문의→메일관리 이동 (`694bc36`)
- fix(employers): 영문 지역(Gwangmyeong) + 빈줄 kv 병합 (`118da47`)
- fix(employers): rawText kv flex→inline 전환 (`956acbf`)
- feat(employers): 복사 버튼 (`06ca5a7`)

## 2026-03-23 세션 5 완료 (문서 프로세서 v2 + 보안 전수검사)
- feat(tools): doc_processor.py v2.0 (`9c433d8`)
- security: 전수검사 6건 즉시 수정 (`7cf910e`)

## 2026-03-23 세션 4 완료 (인터뷰 세팅 + Sheet 탭)
- feat(admin): interview setup wizard (`543bde1`)
- feat(sheet): 탭 커스터마이징 (`10cf4be`)
- feat(sheet): 인터뷰 버튼 3분할 (`2942e1e`)
- feat(interview): step 3 redesign (`82bed64`)

## 2026-03-23 세션 3 완료 (알림 + MailModal + 인터뷰 + 영속성)
- feat(admin): 데스크탑 알림 + 배지 (`e5d07dc`)
- feat(mail): MailModal Apple-style (`d135d3e`)
- fix(sheet): 셀 편집/삭제 영속성 (`36a5471`, `7b50406`)
- feat(sheet): 인터뷰 모달 2단 컴팩트 (`29cb5a0`)
- feat(mobile): PWA mobile admin (`57f604a`)

## 2026-03-23 세션 2 완료 (Sheet 렌더링 + Employer 대량 수정)
- fix(sheet): 한글수직렌더링 + 셀내선제거 + pixel-snap
- fix(sheet): batch row-height/col-width + inline editing
- feat(employers): memo PII 파서 + region 한글화 + 무한스크롤
- perf(homepage): Vercel proxy caching

## 2026-03-23 세션 1 완료 (인터뷰 자동화 + 보안 + API)
- feat(interviews): 원클릭 생성/취소 + Meet 풀 5개
- fix(security): AdminLoginGuard progressive ban
- fix(api): stage/mail_tags/korea_experience 마이그레이션

## 2026-03-22 완료 (보안/SEO)
- fix(frontend): 보안/SEO 수정 5건 (`5464736`)
- fix(api): backend security 4건 (`269870d`)

## 2026-03-21 완료 (P0-P4 + 보안강화)
- feat(sheet): stage + mail_tags DB persist (`086d867`)
- feat(about): /about 독립 페이지 (`3225325`)
- security: CSP unsafe-eval 제거, prompt injection guard

---

## 미완료 (다음 세션 우선순위)

### 핵심 기능
| 우선순위 | 항목 | 비고 |
|---------|------|------|
| High | Canvas Sheet: 가상 렌더링 (Phase 4) | 3000행 성능 |
| High | Social Auto Platform | 계정 준비 후 시작 |
| High | YouTube Shorts 환경 준비 | 계정 준비 후 시작 |
| Medium | sql.js 미사용 의존성 제거 (1.4MB 번들) | 미사용 확인완료 |

### 완료 확인 (제거)
| 항목 | 상태 |
|------|------|
| ~~og-image.png 누락~~ | ✅ opengraph-image.tsx 동적 생성 구현됨 |
| ~~securityGuard /api/security/report~~ | ✅ api_server.py:5528 구현됨 |
| ~~Cookie Secure 플래그~~ | ✅ `2af0803` |
| ~~CSP unsafe-eval 제거~~ | ✅ `7a085ea` |
| ~~공개페이지 SEO metadata~~ | ✅ `43f97dd` |

### SEO/코드 정리
| 우선순위 | 항목 | 비고 |
|---------|------|------|
| Low | CSV/Excel 내보내기 | |
| Low | .github/workflows push (PAT 필요) | |

---

## 절대 건드리면 안 되는 것
- master.db (이동/삭제/hard-delete 금지)
- .bridge.key (암호화 키)
- HERO-ANIMATION (EarthGlobe.tsx 잠금)
- CLAUDE.md IMMUTABLE CORE 섹션
- .env 파일
- `_build_profile_card()` 함수

---

## 특이 사항 (현재 유효) — 2026-04-07 갱신
- Render autoDeploy: **false** (render.yaml 직접 확인, 2026-04-07 false로 변경 완료)
- deploy_skip.json: expire=1234567890 (2009년 만료 → 배포 차단 없음, 정상 동작)
- python3 경로: Q:\Phtyon 3\python.exe (정상, 세션 26에서 복구됨)
- 서버 Hot Reload 중 → 시작/종료 금지
- DB 87컬럼 (stage, mail_tags, korea_experience 추가됨)
- bridge_backup.py 정상 동작 (2026-04-05 수리 확인, Q:\Phtyon 3\python.exe 사용)
- 구조화 백업: Q:\Claudework\bridge backup\ (memory/config/db/env)
