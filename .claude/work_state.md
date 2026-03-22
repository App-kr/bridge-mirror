# BRIDGE 작업 상태 (세션 간 유지)
최근 업데이트: 2026-03-23 (세션 3)

## 세션 재시작 방법
1. `/clear`
2. `@.claude/work_state.md`
3. `'미완료 작업부터 계속'` 또는 원하는 작업 명시

---

## 현재 진행 중인 작업
없음

## 2026-03-23 세션 5 완료 (문서 프로세서 도구)
- feat(tools): doc_processor.py v1.0 — 이력서/커버레터 PII 삭제 + 강사번호 입력
  - DOCX/PDF 지원 (PDF→텍스트 추출)
  - PII 삭제: 이메일, 전화, SNS, LinkedIn, 카카오, URL, 여권, 직장명
  - 한국 주소/거주지 → "Korea" 자동 변환
  - DB lookup: sheet_number로 후보자 매칭 + 이름 자동 삭제
  - 원본 자동 백업 → processed_docs/originals/
  - 사용: `python doc_processor.py process <폴더> [--number N]`
  - 사용: `python doc_processor.py lookup <이름/이메일>`

## 2026-03-23 세션 4 완료 (인터뷰 세팅 원클릭 자동화)
- feat(admin): interview setup wizard (`543bde1`)
  - 3단계 위저드: 후보자 검색 → 구인처 매칭 → 일정 확정 & 원클릭 발송
  - 기존 API만 사용 (백엔드 변경 0건)
  - POST /api/admin/interview/confirm → GCal + Meet + DB + 양측 이메일 자동
  - 사이드바: 인터뷰 세팅 href → /admin/interview-setup
  - Make.com/Notion/Google Calendar 외부 도구 대체

## 2026-03-23 세션 3 완료 (관리자 알림 + MailModal + 인터뷰 + 셀 영속성)
- feat(admin): 데스크탑 알림 + 배지 수정 (`e5d07dc`)
  - 브라우저 Notification API — 새 문의 접수 시 데스크탑 팝업
  - Web Audio 알림음 (880Hz→1100Hz, 파일 불필요)
  - 배지 구인자관리→문의 이동, 색상 blue→red
- feat(sheet): MailModal Apple-style 리디자인 (`d135d3e`)
  - 템플릿 CRUD (localStorage), Gmail/Naver 색분리 버튼
  - 첨부파일 "대용량첨부(14일후 만료)", Save/Send 상단 헤더
- fix(sheet): 셀 편집/삭제 영속성 수정 (`36a5471`, `7b50406`)
  - saveToServer 에러 핸들링 + 토스트
  - 삭제: PATCH→DELETE (status='Deleted' 패턴)
  - GET 쿼리 status!='Deleted' 기본 필터
- feat(sheet): 인터뷰 모달 2단 컴팩트 (`29cb5a0`)
  - 날짜 프리뷰 상단, 후보자 정보 그리드, Meet 풀
- fix(sheet): Pipeline/Tab 가독성 개선 (`c3ef0c9`)
  - 인터뷰대기→인터뷰 대기, pill 배지, flexbox gap

## 2026-03-22 세션 2 완료 (Employers 데이터 안정화)
- fix(frontend): 보안/SEO 수정 5건 (`5464736`)
  - DEV_MODE=false, MegaMenu /about 링크 수정, sitemap /about 추가
  - inquiry 가짜계좌 제거, 카카오 http→https
- fix(api): backend security 4건 (`269870d`)
  - _DB_PATH→_ADMIN_DB_PATH (decrypt-check/bulk-patch 크래시 수정)
  - /health DB경로 노출 제거
  - CORS localhost 프로덕션 제외 (_IS_PROD 게이트)
- .github/workflows 커밋: PAT workflow scope 부재로 rebase 분리 (로컬 보존)

## 2026-03-21 세션 완료 (웹사이트 누락작업 P0-P4)
- chore: .github/workflows CI/CD 커밋 (`8d96bb3`) — P0
- feat(sheet): stage + mail_tags DB persist Phase 3 완료 (`086d867`) — P1+P2
  - ALTER TABLE: stage, mail_tags, korea_experience 3컬럼 추가 (87컬럼)
  - api_server.py EDITABLE + MUTABLE_COLS 추가
  - onStageChange/onTagToggle/컨텍스트메뉴/tagPopup → 모두 PATCH 연결
  - mapRow: DB에서 stage/mail_tags 읽기 (localStorage 폴백 유지)
- feat(about): /about 독립 페이지 생성 (`3225325`) — P3
  - Hero + Mission + Stats + Values + Team + CTA 6섹션
  - Nav 링크: /community/about → /about
- DB: korea_experience 컬럼 추가 — P4

---

## 2026-03-20 세션 완료 전체 목록

### Canvas Sheet (핵심)
- fix(db): 272건 암호화 필드 평문 복원 (`0c31de5`)
- fix: 암호화 코드 복원 + Render 복원 API (`8d5125f`)
- fix(sheet): 열이동 + 메모배경색 + paste충돌 (`3c28b0a`)
- fix(sheet): 사진 우클릭 업로드 + 완료 토스트 (`5149109`)
- fix(sheet): photo paste + stage row color + dup col (`714974f`)
- fix(sheet): 사진cover채우기 + 행삭제 + 스타일토글 + stage배경색 (`b654f0a`)
- fix(sheet): 열선택스타일버그 + MailModal 구인자스타일 재작성 (`60447ee`)

### Employer 관리
- fix(employers): MEMO 암호화값 노출 방지 (`7204d56`)
- fix(employers): INIT_DATA 제거 + API 직접 로드 (`94c7d2b`)
- fix(employers): scroll + filter robustness (`1850a7c`)
- fix(employers): MEMO 복호화 필터 제거 (`bd9941c`)
- fix(employers): API → jobs 테이블 전환 (`7aeaef1`)
- fix(api): jNumber Job. 접두사 제거 (`be14905`)

### ImageFX 자동화
- feat(imagefx): abort 버튼 + status bar (`9af8b73`)
- fix(imagefx): photorealistic 프롬프트 + 로고 (`7f41284`)
- fix(imagefx): 6개 품질 이슈 (`6980876`)
- fix(imagefx): eye/race/age 제거 (`a5114b3`)
- feat(imagefx): AI사진 실사화 + JPG 저장 (`a12a64d`)
- feat(imagefx): diversity overhaul (`9f5c124`)

### ESLCafe 광고 관리
- feat: ESLCafe ad manager v5 HTML 앱 (`30fab25`)
- feat: ESLCafe ad manager v6 + anti-copy (`243122e`, `547ff2d`)

### 문서/보안 설계
- docs: AI_CONTEXT.md + AI_SECURITY_DESIGN.md + handoff v2 (`cbcc2d9`)
- docs: .memory/work-history.md 전체 이력 압축 저장 (현재)

---

## 미완료 (다음 세션 우선순위)

### 핵심 기능
| 우선순위 | 항목 | 비고 |
|---------|------|------|
| High | Canvas Sheet: 가상 렌더링 (Phase 4) + PATCH 연결 점검 | 3000행 성능 + DB 동기화 |
| High | Social Auto Platform | 계정 준비 후 시작 |
| High | YouTube Shorts 환경 준비 | 계정 준비 후 시작 |

### 보안/인프라
| 우선순위 | 항목 | 비고 |
|---------|------|------|
| High | prompt_guard.py → social_auto 적용 예정 | 구조적 프롬프트 인젝션 방어 |
| High | og-image.png 누락 | SNS 공유 시 이미지 깨짐 |
| High | securityGuard /api/security/report 라우트 없음 | 보안위협 리포트 무시됨 |
| Medium | Cookie Secure 플래그 추가 (useAdminAuth.ts) | |
| Medium | CSP unsafe-eval 제거 (빌드 테스트 필요) | |

### SEO/코드 정리
| 우선순위 | 항목 | 비고 |
|---------|------|------|
| Medium | 공개페이지 SEO metadata (about/apply/inquiry/jobs) | 검색엔진 최적화 |
| Medium | sql.js 미사용 의존성 제거 (1.4MB 번들) | |
| Low | AdminAuthContext.tsx 데드코드 삭제 | |
| Low | CSV/Excel 내보내기 | |
| Low | .github/workflows push (PAT workflow scope 필요) | |

### 최근 완료 확인 (3/21)
- ~~진행단계 드롭다운 → DB PATCH~~ ✅ `086d867`
- ~~발송상태 태그 → DB 반영~~ ✅ `086d867`
- ~~korea_experience DB 컬럼~~ ✅ `086d867`
- ~~/about 독립 페이지~~ ✅ `3225325`
- ~~.github/ CI/CD 커밋~~ ✅ `8d96bb3`

---

## 절대 건드리면 안 되는 것
- master.db (이동/삭제/hard-delete 금지)
- .bridge.key (암호화 키)
- HERO-ANIMATION (EarthGlobe.tsx 잠금)
- CLAUDE.md IMMUTABLE CORE 섹션
- .env 파일
- `_build_profile_card()` 함수

---

## 특이 사항 (현재 유효)
- Render autoDeploy: false → 수동 배포만
- deploy_skip.json: expire=9999999999 → 모든 push 자동 승인
- python3 경로 broken → 항상 절대경로 사용
- 서버 Hot Reload 중 → 시작/종료 금지
- DB 87컬럼 (stage, mail_tags, korea_experience 추가됨)
