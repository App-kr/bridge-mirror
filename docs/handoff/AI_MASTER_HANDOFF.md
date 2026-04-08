# BRIDGE — AI Master Handoff (v1.0)
# 최종 업데이트: 2026-03-23
# 대상: Claude Code / Gemini / GPT / 모든 AI 에이전트
# 이 문서 하나로 프로젝트 전체를 이해할 수 있어야 한다

---

## 1. 프로젝트 개요

| 항목 | 값 |
|------|-----|
| 서비스명 | BRIDGE (bridgejob.co.kr) |
| 목적 | 한국 내 원어민 영어교사(ESL) 채용 중개 플랫폼 |
| 대표 | Scarlett |
| 운영부장 | Violet |
| 로컬 루트 | `Q:\Claudework\bridge base\` |
| GitHub | koreadobby/bridge (main 브랜치) |
| 백엔드 배포 | Render (bridge-n7hk.onrender.com) — autoDeploy OFF |
| 프론트엔드 배포 | Vercel (자동 배포) |
| DB | SQLite `master.db` (6.6MB, 로컬 단일 파일) |

---

## 2. 기술 스택

```
Backend:   Python 3 + FastAPI + SQLite + AES-256-GCM 암호화
Frontend:  Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS
Sheet:     Pure HTML5 Canvas 스프레드시트 (자체 엔진)
Mobile:    PWA (Progressive Web App) — /admin/m
3D HERO:   Three.js 지구본 (EarthGlobe.tsx — 영구 잠금)
```

---

## 3. 디렉토리 구조

```
Q:\Claudework\bridge base\
├── api_server.py              ← 백엔드 전체 (~7,800줄, 85+ 엔드포인트)
├── master.db                  ← SQLite DB (절대 이동/삭제 금지)
├── .bridge.key                ← AES-256 암호화 키 (절대 이동 금지)
├── .env                       ← 환경변수 (절대 커밋 금지)
├── CLAUDE.md                  ← AI 에이전트 절대 규칙
├── tools/                     ← 자동화 스크립트
│   ├── auto_finalize.py       ← 작업 완료 원클릭 (백업+커밋+Obsidian)
│   ├── doc_processor.py       ← 이력서 PII 제거 v2.2
│   ├── secure_backup.py       ← AES-256 암호화 백업
│   ├── bridge_backup.py       ← 작업 전 백업 (현재 broken → git으로 대체)
│   ├── bx.py                  ← Windows DPAPI 자격증명 로더
│   ├── render_deploy.py       ← Render 수동 배포
│   └── prompt_guard.py        ← 프롬프트 인젝션 방어
├── docs/                      ← 문서
│   ├── AI_CONTEXT.md          ← 범용 AI 온보딩
│   ├── AI_SECURITY_DESIGN.md  ← 3계층 보안 설계
│   ├── AI_MASTER_HANDOFF.md   ← ★ 이 파일 ★
│   └── AUTOMATION_GUIDE.md    ← 자동화 도구 가이드
├── .claude/work_state.md      ← 세션 간 작업 상태 유지
├── .memory/work-history.md    ← 전체 커밋 이력 압축
└── web_frontend/              ← Next.js 프론트엔드
    └── src/
        ├── app/
        │   ├── page.tsx                ← 홈페이지 (HERO 3D 지구본)
        │   ├── about/                  ← 소개 페이지
        │   ├── apply/                  ← 지원서 (공개)
        │   ├── inquiry/                ← 구인 문의 (공개)
        │   ├── jobs/                   ← 채용공고 목록 (공개)
        │   ├── community/[board]/      ← 커뮤니티 게시판
        │   └── admin/                  ← ★ 관리자 대시보드 ★
        │       ├── sheet/              ← Canvas 스프레드시트 (핵심)
        │       │   ├── BridgeCanvasSheet.tsx  ← 메인 래퍼 (3000+줄)
        │       │   ├── MailModal.tsx          ← 메일 발송 모달
        │       │   └── engine/               ← Canvas 렌더링 엔진
        │       │       ├── GridEngine.ts      ← 코어 (2000+줄)
        │       │       ├── EditManager.ts     ← 인라인 편집
        │       │       ├── HistoryManager.ts  ← Undo/Redo
        │       │       ├── PrefsManager.ts    ← 컬럼 설정 영속화
        │       │       ├── SelectionManager.ts← 셀/행 선택
        │       │       ├── StyleManager.ts    ← 셀 서식
        │       │       └── types.ts           ← 공통 타입
        │       ├── interview-setup/    ← 인터뷰 자동화 위저드
        │       ├── interviews/         ← 인터뷰 관리
        │       ├── employers/          ← 구인자 관리
        │       ├── matching/           ← 프로필 매칭
        │       ├── candidates/         ← 후보자 그리드
        │       ├── jobs/               ← 채용공고 관리
        │       ├── inquiries/          ← 문의 관리
        │       ├── inbox/              ← 수신함
        │       ├── mail-send/          ← 메일 발송
        │       ├── mail-logs/          ← 메일 이력
        │       ├── m/                  ← 모바일 PWA
        │       └── (13개 추가 페이지)
        ├── components/
        │   ├── admin/AdminSidebar.tsx   ← 사이드바 네비게이션
        │   ├── EarthGlobe.tsx          ← 3D 지구본 (잠금)
        │   └── (15+ 공용 컴포넌트)
        └── hooks/useAdminAuth.ts       ← 인증 훅 (HMAC 서명)
```

---

## 4. 데이터베이스 (SQLite)

### 주요 테이블
| 테이블 | 레코드 수 | 용도 |
|--------|-----------|------|
| candidates | ~3,059 | 원어민 후보자 (87컬럼) |
| client_inquiries | ~1,227 | 구인처 문의 |
| jobs | ~1,072 | 채용공고 |
| interviews | - | 인터뷰 일정 |
| file_uploads | - | 문서 처리 감사 추적 |

### candidates 테이블 (87컬럼)
```
핵심 식별: id, _cid (candidate_id), category, stage
개인정보: full_name, email, mobile_phone, kakaotalk, dob, gender
직무: nationality, current_location, university, total_exp, start_date
급여: current_salary, hope_salary, housing, wage
문서: verified, arc, crim_check, certification, education_level
UI전용: is_deleted, row_styles(JSON), row_height, memo_bg, photo_url, stage, mail_tags

암호화 필드 (AES-256-GCM):
  nationality, current_location, dob, email, full_name,
  mobile_phone, kakaotalk, gender, health_info, religion,
  notes, criminal_record, reference, korean_criminal_record
```

### 핵심 규칙
- `is_deleted=1` 논리삭제만 허용 (hard DELETE 절대 금지)
- 모든 SQL은 100% parameterized query (f-string 삽입 금지)
- DB 파일 이동/복사/삭제 금지

---

## 5. API 엔드포인트 요약 (85+개)

### 인증
모든 admin API는 `x-admin-key` 헤더 필수.
뮤테이션(POST/PATCH/PUT/DELETE)은 HMAC 서명 추가.

### 주요 엔드포인트 (카테고리별)

**공개 API (인증 불필요)**
```
GET  /api/jobs                    — 채용공고 목록
GET  /api/jobs/{id}               — 공고 상세
POST /api/apply                   — 지원서 제출
POST /api/inquiry                 — 구인 문의
GET  /api/community/{board}       — 게시판
GET  /api/settings                — 사이트 설정
GET  /api/testimonials            — 후기
GET  /api/partners                — 파트너
POST /api/track                   — 이벤트 추적
```

**후보자 관리**
```
GET    /api/admin/candidates              — 목록 (?tab=active|past|blacklist|all&search=&limit=50)
POST   /api/admin/candidates              — 생성
PATCH  /api/admin/candidates/{id}         — 단일 필드 수정
PUT    /api/admin/candidates/{id}         — 복수 필드 수정
DELETE /api/admin/candidates/{id}         — 소프트 삭제
POST   /api/admin/candidates/bulk-patch   — 일괄 수정
GET    /api/admin/candidates/profile-search — candidate_id/nationality/location 검색
POST   /api/admin/candidates/{id}/send-email — 이메일 발송
```

**인터뷰 자동화**
```
GET    /api/admin/interviews              — 목록
POST   /api/admin/interviews              — 생성 (Meet 풀 자동 배정)
PATCH  /api/admin/interviews/{id}         — 수정
DELETE /api/admin/interviews/{id}         — 삭제
POST   /api/admin/interview/confirm       — ★ 원클릭 확정 ★
         (candidate_id + inquiry_id + date/time 입력
          → 후보자/구인처 조회 → Google Calendar → Meet link
          → DB INSERT → 양측 이메일 자동 발송)
```

**매칭**
```
GET  /api/admin/matching/employers        — 후보자별 매칭 구인처 (점수순)
POST /api/admin/matching/send-profile-secure — PII-safe 프로필 발송
```

**메일**
```
POST /api/admin/mail/send          — 개별 메일 (첨부파일 포함)
POST /api/admin/mail/send-bulk     — 대량 발송
GET  /api/admin/mail-logs          — 발송 이력
GET  /api/admin/mail/templates     — 템플릿 목록
```

**문의/채용공고/구인자**
```
GET   /api/admin/inquiries            — 문의 목록
PATCH /api/admin/inquiries/{id}       — 수정
GET   /api/admin/inquiries/new-count  — 새 문의 수 (5초 폴링)
GET   /api/admin/jobs/v2              — 채용공고 v2
POST  /api/admin/jobs/v2              — 생성
GET   /api/admin/employers            — 구인자 관리
```

**콘텐츠 관리**
```
(게시판/배너/파트너/FAQ/가이드링크/이메일템플릿/설정 — 표준 CRUD)
```

**파일 처리**
```
POST /api/admin/upload-image          — 이미지 업로드
POST /api/upload/{type}/{id}          — 파일 업로드
GET  /api/files/{type}/{id}/{file}    — 파일 다운로드
POST /api/admin/sign-url              — S3 서명 URL
```

---

## 6. Canvas 스프레드시트 (핵심 기능)

### 아키텍처
```
BridgeCanvasSheet.tsx (React 래퍼)
  ├── GridEngine.ts      — Canvas 2D 렌더링 (DPR 스케일링, 픽셀 스냅)
  ├── EditManager.ts     — 더블클릭 → input overlay → Enter/Esc
  ├── HistoryManager.ts  — Ctrl+Z/Y (50단계)
  ├── PrefsManager.ts    — 컬럼 너비/순서 localStorage 영속화
  ├── SelectionManager.ts — 단일/범위(Shift)/전체(Ctrl+A) 선택
  └── StyleManager.ts    — Bold/Italic/Strikethrough/Color/BgColor/FontSize
```

### 완료된 기능 (Phase 1~3.7, v4.2)
- 5개 탭 (active/focus/past/blacklist/all) + 더블클릭 이름변경 + 드래그 순서변경
- Pipeline 상태표시줄
- 사진: cover 채우기, 우클릭 업로드, 삭제, 클립보드 붙여넣기
- 행 삭제 (is_deleted=1 소프트 삭제)
- 컬럼 이동 (드래그)
- 스타일 토글 (B/I/S) + 열 선택 시 전체 행 일괄 적용
- stage 배경색 자동 적용 (8가지 색상)
- mail_tags DB 영속화
- MailModal (Apple-style, 다크헤더/탭/칩/첨부파일)
- 인터뷰 버튼 3분할: 📧인터뷰메일 / 📅브릿지IV / 🏢업체IV
- 인라인 셀 편집 + Undo/Redo
- 컬럼 너비/순서 영속화

### 미완료 (Phase 4)
- [ ] 가상 렌더링 (뷰포트 밖 행 스킵 — 3000행 성능)
- [ ] CSV/Excel 내보내기
- [ ] 컬럼 필터 드롭다운

### Stage 값 & 색상
| stage | 한글 | 배경색 |
|-------|------|--------|
| (없음) | — | #ffffff |
| interview | 인터뷰 | #fef9c3 (노랑) |
| proposal | 계약제안 | #fde68a (주황) |
| signed | 서명완료 | #bbf7d0 (초록) |
| guide_sent | 안내발송 | #93c5fd (파랑) |
| guide_done | 안내완료 | #dbeafe (연파랑) |
| caution | 주의 | #fecaca (빨강) |
| lost | 두절 | #e5e7eb (회색) |

---

## 7. 인터뷰 자동화 시스템

### 워크플로우 (기존 수동 → 원클릭)
```
기존: Make.com → Notion → Google Calendar → 수동 메일 (4단계)
현재: interview-setup 위저드 → API 1회 호출 (자동 완료)
```

### 3단계 위저드 (`/admin/interview-setup`)
```
Step 1: 후보자 검색 → 선택
Step 2: 매칭 구인처 자동 조회 → 선택
Step 3: 날짜/시간 설정 → "인터뷰 확정" 클릭
        → Google Calendar 이벤트 생성
        → Meet 링크 자동 배정
        → DB INSERT
        → 후보자 + 구인처 양측 이메일 자동 발송
```

### Meet Room Pool
- 5개 고정 Google Meet 방 (localStorage에 저장)
- 날짜 기준 충돌 회피 자동 배정

---

## 8. 모바일 관리자 (PWA)

경로: `/admin/m`
자동 리다이렉트: iPhone/Android + 화면폭 < 768px

### 페이지
```
/admin/m              — 모바일 홈 (요약 대시보드)
/admin/m/candidates   — 후보자 카드 뷰 (스와이프 액션)
/admin/m/inquiries    — 문의 관리
/admin/m/interviews   — 인터뷰 관리
/admin/m/mail         — 빠른 메일 발송
```

### 컴포넌트
- MobileTabBar (하단 탭)
- PullToRefresh (당겨서 새로고침)
- SwipeAction (좌우 스와이프)
- CandidateCard / InquiryCard / InterviewCard (카드 UI)

---

## 9. 보안 체계

### 3계층 보안 (AI_SECURITY_DESIGN.md)
```
NEVER    — 절대 금지 (DB 직접 접근, 하드삭제, 비밀번호 변경)
ASK_FIRST — 보스 승인 후 (스키마 변경, 배포, 환경변수)
ALLOWED  — 자율 실행 (코드 수정, API 호출, 문서 작성)
```

### 구현된 보안
- AES-256-GCM: 14개 PII 필드 암호화 (at rest)
- HMAC-SHA256: 뮤테이션 요청 서명 (useAdminAuth.ts → signedFetch)
- Rate Limiting: 10/5 요청/시간 (엔드포인트별)
- OWASP 헤더: X-Content-Type-Options, X-Frame-Options, CSP, HSTS
- Fail-Closed: 에러 시 제네릭 메시지만 노출
- Parameterized SQL: f-string 삽입 0건
- Cookie Secure: SameSite=Strict (localhost 예외)
- Progressive Ban: 로그인 실패 누적 → 점진적 차단
- Prompt Injection Guard: LLM 입력 방어

### 환경변수 (이름만, 값은 절대 노출 금지)
```
BRIDGE_FIELD_KEY          — AES-256 암호화 키
ADMIN_API_KEY             — 관리자 인증 키
UPLOAD_SIGN_KEY           — HMAC 파일 서명 키
AWS_ACCESS_KEY_ID         — S3
AWS_SECRET_ACCESS_KEY     — S3
AWS_S3_BUCKET / AWS_REGION
NEXT_PUBLIC_API_URL       — API 주소
```

---

## 10. 전체 커밋 이력 (2026-03-20 ~ 03-23)

### 세션 9 (03-23, 최신)
```
2487052 fix(interview-setup): candidate_id 검색 버그 수정
ca77646 feat(inbox): Supabase→SQLite 마이그레이션
2af0803 feat(security+automation): Cookie Secure + doc_processor v2.2
43f97dd feat(seo): 4개 페이지 metadata
```

### 세션 8 (03-23)
```
ae31962 feat(tools): doc_processor v2.1 파이프라인
```

### 세션 6 (03-23)
```
a4cdca4 fix(employers): rawText 지역 첫줄 자동 주입
694bc36 fix(sidebar): 업체관리→인력관리, 문의→메일관리 이동
118da47 fix(employers): 영문 지역 + 빈줄 kv 병합
956acbf fix(employers): rawText kv flex→inline
06ca5a7 feat(employers): 복사 버튼
```

### 세션 5 (03-23)
```
9c433d8 feat(tools): doc_processor v2.0
7cf910e security: 전수검사 6건 즉시 수정
```

### 세션 4 (03-23)
```
543bde1 feat(admin): interview setup wizard
10cf4be feat(sheet): 탭 커스터마이징
2942e1e feat(sheet): 인터뷰 버튼 3분할
82bed64 feat(interview): step 3 redesign
```

### 세션 3 (03-23)
```
e5d07dc feat(admin): 데스크탑 알림 + 배지
d135d3e feat(mail): MailModal Apple-style
36a5471 fix(sheet): 셀 편집/삭제 영속성
29cb5a0 feat(sheet): 인터뷰 모달 2단 컴팩트
57f604a feat(mobile): PWA mobile admin
```

### 세션 2 (03-23)
```
fix(sheet): 한글수직렌더링 + pixel-snap
fix(sheet): batch row-height/col-width + inline editing
feat(employers): memo PII 파서 + region 한글화 + 무한스크롤
perf(homepage): Vercel proxy caching
```

### 세션 1 (03-23)
```
feat(interviews): 원클릭 생성/취소 + Meet 풀 5개
fix(security): AdminLoginGuard progressive ban
fix(api): stage/mail_tags/korea_experience 마이그레이션
```

### 03-22
```
5464736 fix(frontend): 보안/SEO 수정 5건
269870d fix(api): backend security 4건
```

### 03-21
```
086d867 feat(sheet): stage + mail_tags DB persist
3225325 feat(about): /about 독립 페이지
8d96bb3 chore: .github/workflows CI/CD
```

### 03-20 (최초 대규모 구축)
```
Canvas Sheet Phase 1-3.7 전체 구현
Employer 관리 시스템 구축
ImageFX AI 사진 자동화
ESLCafe 광고 매니저
보안 설계 문서 작성
```

---

## 11. 남은 작업 (우선순위)

| 순위 | 항목 | 난이도 | 비고 |
|------|------|--------|------|
| High | Canvas Sheet 가상 렌더링 | 중 | 3000행 성능 최적화 |
| High | og-image.png 생성 | 하 | SNS 공유 미리보기 |
| Medium | sql.js 의존성 제거 | 하 | npm uninstall (1.4MB 절약) |
| Medium | CSV/Excel 내보내기 | 중 | xlsx 패키지 이미 설치됨 |
| High | Social Auto Platform | 상 | 계정 준비 후 새 프로젝트 |
| High | YouTube Shorts | 상 | 계정 준비 후 |

---

## 12. 절대 규칙 (모든 AI 공통)

### NEVER (어떤 상황에서도 금지)
1. `master.db` 이동/삭제/hard DELETE
2. `.bridge.key` 이동/삭제
3. 비밀번호 하드코딩 또는 변경
4. EarthGlobe.tsx HERO 애니메이션 수정
5. CLAUDE.md IMMUTABLE CORE 섹션 변경
6. `.env` 파일 커밋
7. f-string SQL 쿼리
8. PII를 공개 API/CSV에 노출
9. `_build_profile_card()` 함수 수정

### MUST (반드시 지켜야 하는 것)
1. 작업 전 백업 (git commit 또는 bridge_backup.py)
2. 소프트 삭제만 (is_deleted=1)
3. 100% parameterized SQL
4. 커밋 즉시 push (로컬만 보관 금지)
5. HMAC 서명 (뮤테이션 요청)
6. PII는 admin API에서만 전체 표시

### 작업 흐름
```
1. .claude/work_state.md 읽기 (현재 상태 파악)
2. 백업 실행
3. 작업 수행
4. 빌드 검증 (npx next build)
5. git add + commit + push
6. work_state.md 업데이트
```

---

## 13. 패키지 의존성

### Python (백엔드)
```
fastapi, uvicorn, python-multipart
cryptography (AES-256-GCM)
boto3 (S3)
python-docx (DOCX 처리)
PyMuPDF/fitz (PDF 처리)
google-api-python-client (Calendar)
```

### Node.js (프론트엔드)
```
next@15, react@19, typescript@5
tailwindcss@3, framer-motion@12
three@0.165 (3D 지구본)
lucide-react (아이콘)
recharts (차트)
xlsx (엑셀)
dompurify (HTML 살균)
@dnd-kit (드래그&드롭)
@tanstack/react-virtual (가상 스크롤)
ag-grid-react (그리드, 일부 페이지)
sql.js — ★ 미사용, 제거 예정 (1.4MB) ★
```

---

## 14. 개발 환경

```
OS:       Windows 10 Pro
Shell:    bash (Git Bash) — Unix 문법 사용
Python:   절대경로 필수 (python3 심볼릭 깨짐)
Node:     Next.js dev → localhost:3002
Backend:  uvicorn → localhost:8000 (Hot Reload 상시 가동, 재시작 금지)
Git:      main 브랜치 단일 운용
```

### 주의사항
- `cd Q:` bash에서 불가 → 절대경로로만 실행
- GUI 앱 실행 금지 (포커스 스틸 방지)
- 백그라운드 작업은 반드시 `run_in_background`
- 서버 시작/종료 명령 금지 (Hot Reload 중)

---

## 15. 참조 문서 인덱스

| 파일 | 용도 |
|------|------|
| `CLAUDE.md` | AI 에이전트 절대 규칙 |
| `docs/AI_CONTEXT.md` | 범용 AI 온보딩 (어떤 AI에도 붙여넣기 가능) |
| `docs/AI_SECURITY_DESIGN.md` | 3계층 보안 설계 |
| `docs/AI_MASTER_HANDOFF.md` | ★ 이 파일 (전체 통합) ★ |
| `docs/AUTOMATION_GUIDE.md` | 자동화 도구 사용법 |
| `.claude/work_state.md` | 세션 간 작업 상태 |
| `.memory/work-history.md` | 전체 커밋 이력 |
| `web_frontend/src/app/admin/sheet/sheet_context.md` | Canvas Sheet 컨텍스트 |

---

> 이 문서는 Claude Code, Gemini, GPT 등 어떤 AI 에이전트가 읽어도
> BRIDGE 프로젝트의 전체 구조, 규칙, 현황을 즉시 파악할 수 있도록 작성됨.
> 최신 상태는 `.claude/work_state.md` 참조.
