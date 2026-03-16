# BRIDGE 프로젝트 작업일지

> 자동 업데이트 파일 — 모든 작업 완료 후 하단에 추가
> 마지막 업데이트: 2026.03.10

---

## 프로젝트 기본 정보

| 항목 | 값 |
|------|-----|
| 프론트엔드 | https://bridge-chi-lime.vercel.app (Next.js 14+, Vercel) |
| 백엔드 | https://bridge-n7hk.onrender.com (FastAPI, Render Free) |
| DB | `Q:\Claudework\bridge base\master.db` (SQLite) |
| GitHub | https://github.com/koreadobby/bridge.git (main) |
| 로컬 작업 루트 | `Q:\Claudework\bridge base` |

### DB 현황 (2026.03.10 기준)
- candidates: **3,059건** (Active 43 / Inactive 3,016)
- employers (client_inquiries): **1,227건**
- jobs: **1,072건** (raw_text 1,042건 포함)
- payments 테이블: 신규 생성
- visa_type 보강: 980건

---

## 파일 구조 현황

```
Q:\Claudework\bridge base\
├── api_server.py              # FastAPI 백엔드 메인
├── email_templates.py         # 이메일 템플릿
├── security_middleware.py     # 보안 미들웨어 (HMAC·Rate Limit·차단)
├── master.db                  # SQLite DB (Git 포함, Render 배포용)
├── CLAUDE.md                  # 에이전트 마스터 설정
├── render.yaml                # Render 배포 설정 (autoDeploy: false)
├── requirements.txt
├── web_frontend/              # Next.js 14+ 프론트엔드
│   ├── app/
│   │   ├── page.tsx           # 홈 (HERO LOCKED)
│   │   ├── jobs/page.tsx      # 잡보드
│   │   ├── community/         # 커뮤니티 허브
│   │   ├── admin/             # 관리자 패널
│   │   │   ├── sheet/         # 스프레드시트 (가상스크롤)
│   │   │   ├── employers/     # 구인자 관리
│   │   │   ├── jobs/          # 잡 관리
│   │   │   ├── faq/           # FAQ DnD 관리
│   │   │   └── mail-send/     # 이메일 발송
│   │   └── faq/page.tsx
│   ├── components/
│   │   ├── DocBlock.tsx       # 워드뷰 문서 블록
│   │   ├── FaqDndList.tsx     # FAQ 드래그앤드롭
│   │   └── JobDetailModal.tsx
│   └── lib/
│       └── boards.ts          # 게시판 설정
├── backend/
│   ├── routers/payments.py
│   └── utils/storage.py
├── .hooks/                    # 자동화 훅
│   ├── guard.py               # 보안 게이트
│   ├── auto_backup.py
│   └── task_gate.py
├── .memory/                   # 에이전트 메모리
├── audit/                     # 보안 감사 로그
├── docs/
│   └── obsidian/
│       └── BRIDGE_작업일지.md  ← 이 파일
├── import_source/
│   └── word_import.csv        # Word 원문 임포트 소스
└── tasks/
    ├── todo.md
    ├── lessons.md
    └── backlog.md
```

---

## 작업 이력

### 2026.03.01

#### [f62b5ed] 초기 커밋 — unified inbox 이전
- **작업 내용**: 프로젝트 최초 커밋 (Supabase 기반 초기 상태)
- **상태**: ✅ 배포완료

#### [08c6092] Gmail 수집기 + unified inbox API
- **변경 파일**: `gmail_collector.py`, `inbox_api.py`
- **작업 내용**: Gmail 자동분류 수집기 + 통합 inbox API 엔드포인트 추가
- **상태**: ✅ 배포완료

#### [cc936a4] 통합 inbox UI
- **변경 파일**: `web_frontend/app/admin/`
- **작업 내용**: 필터·상세뷰 포함 통합 inbox UI 구현
- **상태**: ✅ 배포완료

#### [4b8dd1f] 대시보드 통계 카드·차트
- **작업 내용**: stats cards + charts 추가
- **상태**: ✅ 배포완료

#### [6a221c4] 보안 패치 — Supabase 검색 인젝션 + 레이트 리밋
- **작업 내용**: SQL 인젝션 방지 + rate limiting 적용
- **상태**: ✅ 배포완료

#### [0f7b1a4] CLAUDE.md 슬림화 (137→72줄)
- **작업 내용**: CLAUDE.md 리팩토링, 스킬 파일 분리
- **상태**: ✅ 배포완료

---

### 2026.03.02

#### [da2f2b6] 배포 전 보안 감사 10/10 PASS
- **작업 내용**: 전체 보안 항목 점검 통과
- **상태**: ✅ 배포완료

#### [9da2f2b] Vercel + Railway 배포 설정
- **변경 파일**: `vercel.json`, `railway.toml`
- **작업 내용**: Vercel 프론트/Railway 백엔드 배포 구성
- **상태**: ✅ 배포완료

#### [bbe7e7b] Render 배포 설정 + 운영 보안 강화
- **변경 파일**: `render.yaml`, `api_server.py`
- **작업 내용**: Railway→Render 전환, 운영 환경 보안 하드닝
- **상태**: ✅ 배포완료

#### [183b839] 관리자 하드코딩 비밀번호 제거
- **작업 내용**: admin dashboard 하드코딩 기본 비번 삭제
- **상태**: ✅ 배포완료

---

### 2026.03.03

#### [52c6ff4] Supabase→SQLite 전환
- **변경 파일**: `api_server.py`, `web_frontend/lib/`
- **작업 내용**: candidates/applications/inquiry/dashboard 모두 SQLite로 전환
- **상태**: ✅ 배포완료

#### [f4805de] Part1 백엔드 통합 — DB 확장 + API + 보안 미들웨어
- **변경 파일**: `api_server.py`, `security_middleware.py`
- **작업 내용**: DB 스키마 확장, 보안 미들웨어 초기 구현
- **상태**: ✅ 배포완료

#### [313281] 보안 강화 + PDF/Word 파일 업로드 수정
- **작업 내용**: 파일 업로드 보안, CSP 업데이트
- **상태**: ✅ 배포완료

#### [ec50dcb] 히어로 현수교 재설계 — 케이블·트윈타워·스테이와이어
- **변경 파일**: `web_frontend/app/page.tsx` (HERO)
- **작업 내용**: 현수교 SVG 히어로 시각 완성
- **상태**: ✅ 배포완료

---

### 2026.03.04

#### [a65de6e] 자동 백업 시스템 — CLAUDE.md 규칙 + PowerShell 스크립트
- **변경 파일**: `CLAUDE.md`, `.hooks/auto_backup.py`
- **작업 내용**: 매 작업 전 자동 백업 체계 구축
- **상태**: ✅ 배포완료

#### [2090b2b] 정보 게시판 + 소셜 링크 + CORS Render 도메인
- **작업 내용**: Information board 구현, CORS 설정 완료
- **상태**: ✅ 배포완료

#### [29c573a] admin boards/banners/posts + HMAC 서명
- **작업 내용**: 관리자 게시판·배너·게시글 CRUD + HMAC 인증
- **상태**: ✅ 배포완료

#### [3e5458e] 관리자 비밀번호 로그인 + Render wake-up 재시도
- **변경 파일**: `web_frontend/app/admin/`, `api_server.py`
- **작업 내용**: 관리자 패스워드 인증 구현, Render cold-start 재시도 로직
- **상태**: ✅ 배포완료

#### [8fc2e34] nav 재구성 + Community 허브 페이지 재설계
- **변경 파일**: `web_frontend/app/community/page.tsx`
- **작업 내용**: 네비게이션 구조 개편, Community 허브 전면 재설계
- **상태**: ✅ 배포완료

#### [0aa7270] 잡보드 프리미엄 디자인
- **변경 파일**: `web_frontend/app/jobs/page.tsx`
- **작업 내용**: 잡보드 카드 플립·셔플·날짜변환·관리자 기능 완성
- **상태**: ✅ 배포완료

#### [b2415359] 어드민 버튼 통일 — 수정(주황)/저장(파란)/취소(회색)/삭제(빨강)
- **작업 내용**: 전체 관리자 페이지 버튼 색상 통일
- **상태**: ✅ 배포완료

---

### 2026.03.06

#### [905b4c8] 스프레드시트 로딩속도 개선 + 사진 DB 저장
- **변경 파일**: `web_frontend/app/admin/sheet/`
- **작업 내용**: 단일 요청 + localStorage 캐시로 스프레드시트 속도 개선
- **상태**: ✅ 배포완료

#### [08e9ba9] DocBlock 레이아웃 개선 — 메모 상단 노랑박스
- **변경 파일**: `web_frontend/components/DocBlock.tsx`
- **작업 내용**: 메모 상단 이동, 편집버튼 명확화, 이동버튼 텍스트 추가
- **상태**: ✅ 배포완료

#### [0401c28] employer data jobs 테이블 기반 + 상태 드롭다운 수정
- **변경 파일**: `web_frontend/app/admin/employers/`
- **작업 내용**: employer 데이터를 jobs 테이블에서 집계, AG Grid 타입 수정
- **상태**: ✅ 배포완료

#### [9ca48af] 스프레드시트 cursor-based 150건/page + DB 인덱스
- **변경 파일**: `api_server.py`, `web_frontend/app/admin/sheet/`
- **작업 내용**: 무한스크롤 + cursor 페이지네이션 성능 최적화
- **상태**: ✅ 배포완료

---

### 2026.03.07

#### [f8f8e1b] jobs 쿼리 존재하지 않는 컬럼 제거
- **변경 파일**: `api_server.py`
- **작업 내용**: sick_leave/meal/travel_support 컬럼 쿼리에서 제거
- **상태**: ✅ 배포완료

#### [0ef7072] 해외 해킹 방지 강화 — 누진차단/허니팟/관리자로그인보호
- **변경 파일**: `security_middleware.py`
- **작업 내용**: 해외IP 누진차단, 허니팟 엔드포인트, 관리자 로그인 보호
- **상태**: ✅ 배포완료

#### [993ce7d] 강화감지 국가 확대 — 중국/UAE/러시아/북한/브라질 외
- **변경 파일**: `security_middleware.py`
- **작업 내용**: 위험 국가 목록 확장, 패턴 1회 탐지 즉시 24h 차단
- **상태**: ✅ 배포완료

#### [ca0f45c] FAQ 순서변경 드래그앤드롭 구현
- **변경 파일**: `web_frontend/app/admin/faq/`, `web_frontend/components/FaqDndList.tsx`
- **작업 내용**: 번호 배지를 grab 핸들로 사용하는 DnD FAQ 순서 변경
- **상태**: ✅ 배포완료

#### [17e4368] 보안: 6개 high/medium 이슈 수정
- **변경 파일**: `api_server.py`, `security_middleware.py`
- **작업 내용**: 개발환경 우회 제거, XSS/SQLi 패치
- **상태**: ✅ 배포완료

#### [6f79b9f] XSS — DOMPurify.sanitize() 적용
- **변경 파일**: `web_frontend/app/admin/mail-send/page.tsx`
- **작업 내용**: dangerouslySetInnerHTML에 DOMPurify 적용
- **상태**: ✅ 배포완료

#### [6f8e1b4] IP 해시 X-Forwarded-For 기반으로 수정
- **변경 파일**: `security_middleware.py`
- **작업 내용**: Render/Cloudflare 프록시 뒤 정확한 클라이언트 IP 감지
- **상태**: ✅ 배포완료

---

### 2026.03.08

#### [b6dcf41] CLAUDE.md v4 ULTIMATE + tasks 초기화 + Ralph 설치
- **작업 내용**: 에이전트 오케스트레이션 설정 대대적 개편
- **상태**: ✅ 배포완료

#### [9acafee] FAQ 관리 페이지 — 드래그앤드롭 + 인라인 편집
- **변경 파일**: `web_frontend/app/admin/faq/page.tsx`, `FaqDndList.tsx`
- **작업 내용**: FAQ 전체 관리 UI 구현 (DnD + 인라인 편집)
- **상태**: ✅ 배포완료

#### [03035c9] 채용의뢰 is_deleted+중복마킹 + vacancies·housing_type 정리
- **변경 파일**: `api_server.py`, `web_frontend/app/admin/employers/`
- **작업 내용**: 논리삭제 컬럼 추가, 중복의심 마킹 기능, 오염 데이터 정리
- **상태**: ✅ 배포완료

#### [6118472] 카카오 채널 바로가기 — 사이드바 하단 고정
- **변경 파일**: `web_frontend/components/`
- **작업 내용**: 카카오톡 채널 사이드바 상시 버튼 + 대시보드 빠른 실행
- **상태**: ✅ 배포완료

#### [8ddfd42] DocBlock 워드뷰 — MEMO 최상단 + Job번호 초록뱃지
- **변경 파일**: `web_frontend/components/DocBlock.tsx`
- **작업 내용**: 메모 최상단 이동, 잡 번호 초록 뱃지, 도시 통합 표시
- **상태**: ✅ 배포완료

#### [218ad50] word_import.csv ZERO TRUNCATION 완전 임포트
- **변경 파일**: `master.db` (raw_text 1,042건 갱신, 총 1,072건)
- **작업 내용**: Word 원문 전체 컬럼 무손실 임포트 (신규 6건 INSERT)
- **상태**: ✅ 배포완료

#### [311703d] FAQ 드래그핸들 수정 — setActivatorNodeRef 제거
- **변경 파일**: `web_frontend/components/FaqDndList.tsx`
- **작업 내용**: DnD 핸들 버그 수정, listeners 직접 적용
- **상태**: ✅ 배포완료

#### [d00fc9b] 보안: _check_admin 개발환경 우회 제거
- **변경 파일**: `api_server.py`
- **작업 내용**: 키 미설정 시 항상 503 반환 (fail-closed)
- **상태**: ✅ 배포완료

#### [918c7c9] admin/employer 전면 재구현 — PII마스킹 제거·MEMO 인라인
- **변경 파일**: `web_frontend/app/admin/employers/page.tsx`
- **작업 내용**: 노란박스+본문 구조, 인라인 저장, PATCH API 추가
- **상태**: ✅ 배포완료

#### [e63261c] NEW 접수 알림 시스템
- **변경 파일**: `api_server.py`, `web_frontend/app/admin/`
- **작업 내용**: 신규 접수 감지 및 관리자 알림 UI 구현
- **상태**: ✅ 배포완료

#### [a6dc6bb] Render 배포 비용 관리 영구 규칙 추가
- **변경 파일**: `CLAUDE.md`
- **작업 내용**: 월 500분 예산 관리, Auto-Deploy 정책 문서화
- **상태**: ✅ 배포완료

---

### 2026.03.09

#### [da3eeb3] 보안: 파일보호·백업·PII암호화 3종 강화
- **변경 파일**: `security_middleware.py`, `.hooks/guard.py`
- **작업 내용**: 파일 접근 보호, 자동 백업 강화, PII 암호화 레이어 추가
- **상태**: ✅ 배포완료

#### [4d51fed] hook 시스템 최종본 — 보안게이트/품질검증/영구백업
- **변경 파일**: `.hooks/task_gate.py`, `.hooks/post_build.sh`, `.hooks/auto_backup.py`
- **작업 내용**: grep→re 마이그레이션, push 제거, 형식 수정
- **상태**: ✅ 배포완료

#### [ed864b3] korea board category grouping (living/city_guides)
- **변경 파일**: `web_frontend/lib/boards.ts`
- **작업 내용**: 한국 섹션 카테고리 그룹핑 (생활/도시가이드)
- **상태**: ✅ 배포완료

#### [e45997d] FAQ save button 3-state + auto-backup on reorder/edit
- **변경 파일**: `web_frontend/components/FaqDndList.tsx`
- **작업 내용**: 저장 버튼 3상태(idle/dirty/saving) + 순서변경시 자동 백업
- **상태**: ✅ 배포완료

#### [fcf2468] boards.ts 롤백 + community hub Life in Korea 카드 복원
- **변경 파일**: `web_frontend/lib/boards.ts`, `web_frontend/app/community/page.tsx`
- **작업 내용**: 잘못된 boards.ts 롤백, Life in Korea 카드 재복원
- **상태**: ✅ 배포완료

#### [8821a16] community support_kr 카카오톡 버튼 Employers only 구분선
- **변경 파일**: `web_frontend/app/community/`
- **작업 내용**: FAQ 카카오톡 버튼 Employers only 구분선 추가
- **상태**: ✅ 배포완료

#### [e3237f8] 이메일 발송 시스템 — stats/send/bulk/templates 엔드포인트
- **변경 파일**: `api_server.py`, `email_templates.py`
- **작업 내용**: SMTP 설정 + 메일 발송/통계/템플릿 API 완성
- **상태**: ✅ 배포완료

#### [42721ff] SHEET-INFINITE-SCROLL — cursor-based 150건/page + DB 인덱스
- **변경 파일**: `api_server.py`, `web_frontend/app/admin/sheet/`
- **작업 내용**: 무한스크롤 성능 재최적화, DB 인덱스 추가
- **상태**: ✅ 배포완료

#### [2b675e8] job detail raw_text 전문 표시 + 빈 컨텐츠 잡 뒤로 정렬
- **변경 파일**: `web_frontend/app/jobs/page.tsx`
- **작업 내용**: 잡 상세에서 원문 전문 표시, 빈 잡 자동 후순위 배치
- **상태**: ✅ 배포완료

#### [41951709] boards.ts 비자종류/비자관련/출입국사무소 3개 board config 추가
- **변경 파일**: `web_frontend/lib/boards.ts`
- **작업 내용**: 비자 관련 3개 커뮤니티 게시판 신규 구성
- **상태**: ✅ 배포완료

#### [463ecba] mail-send naver-style UI + 기본서명 + 법적고지 + personal-send 뱃지
- **변경 파일**: `web_frontend/app/admin/mail-send/page.tsx`
- **작업 내용**: 네이버 스타일 메일 UI 완성, 서명/법적고지 자동 삽입
- **상태**: ✅ 배포완료

#### [c534618] /admin/sheet 원어민 스프레드시트 렌더링 복구 + 150건 오프셋 페이지네이션
- **변경 파일**: `web_frontend/app/admin/sheet/`
- **작업 내용**: 스프레드시트 탭별 렌더링 버그 수정, 오프셋 페이지네이션 복구
- **상태**: ✅ 배포완료

#### [eb31730] render_monitor --register + Task Scheduler 자동등록
- **변경 파일**: `render_monitor.py` (신규)
- **작업 내용**: Render 빌드 예산 모니터링 + Windows Task Scheduler 자동 등록
- **상태**: ⏳ 로컬only

#### [31a285c] /admin/sheet 전체 탭 외 blank — dbAll 기반 렌더링으로 전환
- **변경 파일**: `web_frontend/app/admin/sheet/`
- **작업 내용**: 탭 전환 시 빈 화면 버그 수정, dbAll 단일 소스로 통합
- **상태**: ✅ 배포완료

#### [8ab3396] mobile responsive — JobDetailModal + apply date picker
- **변경 파일**: `web_frontend/components/JobDetailModal.tsx`
- **작업 내용**: 모바일 반응형 수정, 지원일 날짜 선택기 모바일 최적화
- **상태**: ✅ 배포완료

#### [0538b04] board-korea.json category 필드 복구
- **작업 내용**: 한국 게시판 JSON 카테고리 필드 누락 복구
- **상태**: ✅ 배포완료

#### [22a83ae] 배포 비용 규칙 강화 — 5개 묶음 이상 / 보스 명시 허가만 push
- **변경 파일**: `CLAUDE.md`
- **작업 내용**: push 금지/허용 조건 명문화, 배치 배포 원칙 강화
- **상태**: ✅ 배포완료

#### [d44aad9] sheet 가상스크롤(append) + PII 복호화 + 페이지네이션 버튼 제거
- **변경 파일**: `web_frontend/app/admin/sheet/`
- **작업 내용**: 진짜 가상스크롤 append 방식, PII 복호화 표시, 버튼 제거
- **상태**: ✅ 배포완료

#### [418775e] 로컬 개발 워크플로 추가 — npm run dev / uvicorn 로컬 확인 필수
- **변경 파일**: `CLAUDE.md`
- **작업 내용**: 개발 워크플로 섹션 신규 추가 (push 전 로컬 확인 의무화)
- **상태**: ✅ 배포완료

#### [3d8d403] render.yaml autoDeploy false — 커밋 시 자동 빌드 차단
- **변경 파일**: `render.yaml`
- **작업 내용**: Render 자동 배포 비활성화 (비용 절감)
- **상태**: ✅ 배포완료

#### [253cbc9] fix: split literal newline bug
- **변경 파일**: `api_server.py`
- **작업 내용**: 문자열 split 리터럴 개행 버그 수정
- **상태**: ✅ 배포완료

---

## 현재 미완료 작업

- [ ] ADMIN_API_KEY 로컬↔Render 불일치 문제 해결
- [ ] `community/[board]/page.tsx` 미커밋 (로컬 변경 있음)
- [ ] Claude Token Monitor 삭제
- [ ] FAQ 카카오톡 버튼 Employers only 추가 (UI 미완성)
- [ ] bridge_guardian.py 설치
- [ ] bridgejob.com 도메인 등록
- [ ] .co.kr DNS → Cloudflare 위임
- [ ] Render 빌드분 04/01 리셋 후 Railway 이전 검토

---

## 주요 결정사항 및 교훈

| 날짜 | 결정 | 이유 |
|------|------|------|
| 2026.03.03 | Supabase→SQLite 전환 | Render Free tier 비용 절감 |
| 2026.03.04 | Railway→Render 전환 | 백엔드 안정성 |
| 2026.03.08 | autoDeploy: false | 월 500분 빌드 예산 보호 |
| 2026.03.09 | push 5개 이상 묶음 원칙 | 배포 비용 최소화 |
| 2026.03.09 | Render 빌드 모니터링 도입 | 예산 초과 사전 방지 |

---

*이하 신규 작업은 자동으로 추가됩니다*


### 2026.03.12 11:00 — 키워드 자동 조사 시스템 구현
- **내용**: ClaudeBlog에 Naver AC API + Google Trends 기반 키워드 자동 조사 파이프라인 구현
- **변경 파일**: modules/keyword_researcher.py (신규), modules/keyword_manager.py, modules/main.py, config.json
- **결과**: ✅ 완료 (로컬 커밋)
n### 2026.03.17 07:34 — ClaudeBlog 자동화 완전 수정n- **내용**: 인용구 탈출(Escape+Tab×2), 스케줄 시간→날짜 순서, 제목 입력 안정화n- **변경 파일**: modules/naver_uploader.py, modules/content_generator.pyn- **결과**: ✅ 완료 — 실제 발행 성공 확인 (원어민강사 채용, 2026-03-18 09:30 예약)n- **해결된 이슈**: 인용구 in_quote=False 5개, 스케줄 시간먼저 설정 성공
