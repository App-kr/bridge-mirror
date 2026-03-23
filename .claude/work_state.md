# BRIDGE 작업 상태 (세션 간 유지)
최근 업데이트: 2026-03-23 (세션 14 — 자동화 + 성능 + 안정성)

## 세션 재시작 방법
1. `/clear`
2. `@.claude/work_state.md`
3. `'미완료 작업부터 계속'` 또는 원하는 작업 명시

---

## 현재 진행 중인 작업
없음

## 2026-03-23 세션 14 완료 (자동화 + 성능 + 안정성)
- feat(auto): sheet_number 웹폼 자동 할당 (`3e7f85c`)
  - /api/apply INSERT 시 MAX(sheet_number)+1 자동 부여 (기존: NULL)
- feat(auto): 인터뷰 리마인더 서버 스레드 (`3e7f85c`)
  - 10분 주기 daemon thread — Render에서 자동 실행
  - Windows Task Scheduler 의존성 제거
- fix(stability): sheet_number race condition 제거 (`967bce4`)
  - /api/apply + /api/admin/candidates: INSERT 서브쿼리 원자화
- perf(sheet): 열 뷰포트 컬링 (`9a3656b`)
  - GridEngine draw(): 화면 밖 열 skip (PASS 1/2 + 헤더)
  - 50개 열 중 ~15개만 visible → drawCell 호출 70% 감소
- chore: sql.js + @types/sql.js 의존성 제거 (`9a3656b`)
  - ~1.4MB 번들 절감

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
| ~~High~~ | ~~Canvas Sheet: 가상 렌더링 (Phase 4)~~ | ✅ 행+열 컬링 완료 `9a3656b` |
| High | Social Auto Platform | 계정 준비 후 시작 |
| High | YouTube Shorts 환경 준비 | 계정 준비 후 시작 |

### 보안/인프라
| 우선순위 | 항목 | 비고 |
|---------|------|------|
| High | og-image.png 누락 | SNS 공유 시 이미지 깨짐 |
| ~~Medium~~ | ~~sql.js 미사용 의존성 제거~~ | ✅ `9a3656b` |
| Medium | ag-grid 미사용 의존성 제거 | AllCandidatesGrid dead code |
| Low | Gmail 자동동기화 | Render 환경변수 GMAIL_SYNC_ENABLED=true 설정만 |

### SEO/코드 정리
| 우선순위 | 항목 | 비고 |
|---------|------|------|
| ~~Medium~~ | ~~공개페이지 SEO metadata~~ | ✅ `43f97dd` |
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

## 특이 사항 (현재 유효)
- Render autoDeploy: false → 수동 배포만
- deploy_skip.json: expire=9999999999 → 모든 push 자동 승인
- python3 경로 broken → 항상 절대경로 사용
- 서버 Hot Reload 중 → 시작/종료 금지
- DB 87컬럼 (stage, mail_tags, korea_experience 추가됨)
- bridge_backup.py 실행 불가 (encodings 모듈 에러) → git commit/push로 대체
- 구조화 백업: Q:\Claudework\bridge backup\ (memory/config/db/env)
