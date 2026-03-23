# BRIDGE 작업 상태 (세션 간 유지)
최근 업데이트: 2026-03-23 (세션 8 — doc_processor v2.1 pipeline)

## 세션 재시작 방법
1. `/clear`
2. `@.claude/work_state.md`
3. `'미완료 작업부터 계속'` 또는 원하는 작업 명시

---

## 현재 진행 중인 작업
없음

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

### 보안/인프라
| 우선순위 | 항목 | 비고 |
|---------|------|------|
| High | og-image.png 누락 | SNS 공유 시 이미지 깨짐 |
| Medium | sql.js 미사용 의존성 제거 (1.4MB 번들) | |

### SEO/코드 정리
| 우선순위 | 항목 | 비고 |
|---------|------|------|
| Medium | 공개페이지 SEO metadata | 검색엔진 최적화 |
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
