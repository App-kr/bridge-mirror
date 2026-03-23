# BRIDGE 전체 작업 이력 — 압축 메모
> 최신 업데이트: 2026-03-23 | 커밋 기준 역순 정렬

---

## 2026-03-23 세션 (6세션 완료)

### 세션 6 — Employer 본문 정리 + 사이드바 + 복사
| 커밋 | 내용 |
|------|------|
| 06ca5a7 | feat(employers): 본문 복사 버튼 — clipboard.writeText() |
| 956acbf | fix(employers): rawText kv flex→inline 전환 |
| 118da47 | fix(employers): 영문 지역 + 빈줄 kv 병합 + CITY 40+ |
| 694bc36 | fix(sidebar): 업체관리→인력관리, 문의→메일관리 |
| a4cdca4 | fix(employers): rawText 지역 첫줄 자동 주입 |

### 세션 5 — 문서 프로세서 v2 안정성 재설계
| 커밋 | 내용 |
|------|------|
| 7cf910e | security: 전수검사 6건 즉시 수정 |
| 9c433d8 | feat(tools): doc_processor v2.0 — PDF redaction + 6결함 수정 |

### 세션 4 — 인터뷰 세팅 + Sheet 탭/모달
| 커밋 | 내용 |
|------|------|
| 2942e1e | feat(sheet): 인터뷰 버튼 3분할 (email/bridge/employer) |
| 82bed64 | feat(interview): step 3 redesign + edit/delete |
| 10cf4be | feat(sheet): 탭 커스터마이징 — 더블클릭 이름수정 + 드래그 순서변경 |
| 543bde1 | feat(admin): interview setup wizard — 원클릭 자동화 |
| b66e267 | fix(employers): 헤더 레이아웃 정리 |
| 9d2d62b | feat(tools): doc_processor v1.0 |

### 세션 3 — 알림 + MailModal + 인터뷰 + 셀 영속성
| 커밋 | 내용 |
|------|------|
| e5d07dc | feat(admin): 데스크탑 알림 + 배지 위치 |
| d135d3e | feat(mail): MailModal Apple-style + template CRUD |
| 36a5471 | fix(sheet): 셀 편집/삭제 영속성 |
| 7b50406 | fix(api): Supabase→SQLite 전면 전환 |
| 29cb5a0 | feat(sheet): 인터뷰 모달 2단 컴팩트 |
| c3ef0c9 | fix(sheet): pipeline + tab 가독성 |
| 57f604a | feat(mobile): PWA mobile admin Phase 1-4 |

### 세션 2 — Sheet 렌더링 + Employer 데이터
| 커밋 | 내용 |
|------|------|
| be79676 | perf(employers): IntersectionObserver 무한 스크롤 |
| e852309 | perf(employers): 로딩 속도 최적화 3건 |
| 574166f | fix(employers): DB마이그레이션 + salary/name + CITY 26개 |
| 892a52e~d090f86 | fix(employers): 지역확장 + 도시표시 + display_name 정리 |
| a4d264a | fix(employers): /api/admin/jobs/v2 전환 |
| 1d7ba13 | fix(employers): PII마스킹바이패스 + rawText정리 |
| aae34d8 | feat(employers): memo PII 파서 + region 한글화 |
| 8692ea0 | fix(sheet): per-cell canvas clip 제거 (anti-alias 선) |
| 4807d87 | fix[P0]: 한글수직렌더링 + 셀내선완전제거 + 2패스 |
| 6aa9958 | fix(sheet): 셀줄제거 + 너비높이무제한 + 정렬더블클릭 |
| 3c5325e | fix(sheet): snap grid lines to physical pixels |
| 64a0cd7 | feat(sheet): batch row-height/col-width + category move |
| bbda974 | fix(sheet): inline editing all fields |
| 4233998 | ui(sheet): 메일/인터뷰 모달 대형화 |
| 334735d | perf(homepage): Vercel proxy caching |

### 세션 1 — 인터뷰 자동화 + 보안
| 커밋 | 내용 |
|------|------|
| 2631097 | feat(interview): Apple-style modal + Meet pool + email |
| cc56ad5 | feat(interviews): 원클릭 생성/일정변경/취소 + 카드 |
| 34fb70f | feat(interviews): Meet 링크 풀 5개 + 랜덤 배정 |
| f3104f1 | fix(security): AdminLoginGuard progressive ban + Cookie Secure |
| ab5aa81 | feat(tools): AES-256-GCM 시크릿 저장소 + Render 배포 |
| 36d3bf2 | fix(api): inquiry form 500 — 15 missing DB columns |
| 0cc7bd2 | fix(api): stage/mail_tags/korea_experience 마이그레이션 |
| b2b5b0e | fix(api): _COLS에 stage/mail_tags/korea_experience 추가 |

---

## 2026-03-22 세션 — 보안/SEO + Employers 안정화
| 커밋 | 내용 |
|------|------|
| 5464736 | fix(frontend): 보안/SEO 수정 5건 |
| 269870d | fix(api): backend security 4건 |

---

## 2026-03-21 세션 — 웹사이트 누락작업 P0-P4
| 커밋 | 내용 |
|------|------|
| 8d96bb3 | chore: .github/workflows CI/CD |
| 086d867 | feat(sheet): stage + mail_tags DB persist Phase 3 |
| 3225325 | feat(about): /about 독립 페이지 |
| 7a085ea | security: CSP unsafe-eval 제거 + CI/CD |
| 69b80b7 | hotfix: 로그인 블랙리스트 순환잠금 해제 |
| ca01dfc | hotfix(api): bridge_error 함수 누락 복원 |
| e9019cd | security: prompt injection guard |
| 75e5470 | feat: Architect pattern rules in CLAUDE.md |

---

## 2026-03-20 세션

| 커밋 | 내용 |
|------|------|
| cbcc2d9 | docs: AI_CONTEXT.md + AI_SECURITY_DESIGN.md + handoff v2 |
| be14905 | fix(api): jNumber에서 Job. 접두사 제거 |
| 9f5c124 | feat(imagefx): diversity overhaul |
| 7aeaef1 | fix(employers): API → jobs 테이블 기반 전환 |
| 547ff2d | feat(eslcafe): anti-copy 6-layer protection |
| a12a64d | feat(imagefx): AI사진 실사화 + JPG 저장 |
| 60447ee | fix(sheet): 열선택 스타일버그 + MailModal 재작성 |
| b654f0a | fix(sheet): 사진cover + 행삭제 + 스타일토글 + stage배경색 |
| 714974f | fix(sheet): photo paste + stage row color + dup col |
| 5149109 | fix(sheet): 사진 우클릭 업로드 + 완료 토스트 |
| 3c28b0a | fix(sheet): 열이동 + 메모배경색 + paste충돌방지 |
| 8d5125f | fix: 암호화 코드 복원 + Render 복원 API |
| 0c31de5 | fix(db): 272건 암호화 필드 평문 복원 |

---

## 2026-03-19 이전 (주요 피처)

| 날짜 | 내용 |
|------|------|
| 03-19 | Canvas Sheet Phase 1~3 기초, MailModal, sheet_number |
| 03-16 | ESLCafe RPA 자동화 |
| 03-15 | ClaudeBlog 전체 자동화 v6.6 |
| 03-14 | ImageFX 사진 생성 자동화 |
| 03-12 | Bridge 모니터 서버 v3.1 |
| 03-09 | FastAPI 백엔드 전면 재작성 |
| 03-05 | Next.js 15 프론트엔드 초기 구축 |
| 02-28 | HERO 3D 지구본 확정 잠금 |
| 02-24 | AES-256-GCM PII 암호화 시스템 |
| 02-21 | master.db 최초 구축 |

---

## Canvas Sheet 현재 상태 (2026-03-23 기준)

### 완료된 기능
- [x] GridEngine Canvas 렌더링 + 2패스 렌더링 + pixel-snap
- [x] SelectionManager / EditManager / HistoryManager / PrefsManager
- [x] StyleManager (굵기/기울임/취소선/색/배경/크기) + 열선택 일괄
- [x] 5탭 커스터마이징 (더블클릭 이름수정 + 드래그 순서변경)
- [x] Pipeline 상태표시줄 + stage/mail_tags DB persist
- [x] 사진 붙여넣기/업로드/삭제/cover + 행삭제
- [x] MailModal Apple-style + template CRUD
- [x] 인터뷰 모달 + 인터뷰 버튼 3분할
- [x] 셀 편집/삭제 영속성 (saveToServer)
- [x] batch row-height/col-width + inline editing all fields

### 미완료
- [ ] 가상 렌더링 — 뷰포트 최적화 (Medium)
- [ ] CSV/Excel 내보내기 (Low)

---

## AI 핸드오프 문서 위치

| 파일 | 용도 |
|------|------|
| `docs/AI_CONTEXT.md` | 범용 AI 온보딩 |
| `docs/AI_SECURITY_DESIGN.md` | 3계층 보안 설계 |
| `.claude/work_state.md` | 세션 간 작업 상태 |
| `.memory/work-history.md` | 이 파일 (전체 이력) |
