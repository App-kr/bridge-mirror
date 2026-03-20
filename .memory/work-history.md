# BRIDGE 전체 작업 이력 — 압축 메모
> 최신 업데이트: 2026-03-20 | 커밋 기준 역순 정렬

---

## 2026-03-20 세션 (현재)

| 커밋 | 내용 |
|------|------|
| cbcc2d9 | docs: AI_CONTEXT.md + AI_SECURITY_DESIGN.md + handoff v2 |
| be14905 | fix(api): jNumber에서 Job. 접두사 제거 |
| 9f5c124 | feat(imagefx): diversity overhaul (활동/포지션/옷/재시도) |
| 7aeaef1 | fix(employers): API → jobs 테이블 기반 전환 |
| 547ff2d | feat(eslcafe): anti-copy 6-layer protection |
| a12a64d | feat(imagefx): AI사진 실사화 + JPG 저장 |
| 8bc2bc2 | fix(imagefx): 샘플 참조 프롬프트 매칭 |
| bd9941c | fix(employers): MEMO 복호화 필터 제거 |
| 243122e | feat: ESLCafe ad manager v6 (smartDate+HOT+obfuscation) |
| 6980876 | fix(imagefx): 6개 프롬프트 품질 이슈 |
| 1850a7c | fix(employers): scroll + filter robustness |
| 30fab25 | feat: ESLCafe ad manager v5 (단일 HTML) |
| 94c7d2b | fix(employers): INIT_DATA 제거 + API 직접 로드 |
| 7204d56 | fix(employers): MEMO 암호화값 노출 방지 |
| a5114b3 | fix(imagefx): eye/race/age 프롬프트 제거 |
| 6956e3d | fix(employers): 사이드바 중복 + 링크 정정 |
| 1ff5738 | fix: NEW인깜빡임/NO제거/타임버그/rawText체시 |
| ae8b8dd | fix(imagefx): p.ko.season undefined crash |
| 75d895b | docs(sheet): sheet_context.md v4.2 |
| **60447ee** | **fix(sheet): 열선택 스타일버그 + MailModal 구인자스타일 재작성** |
| da74e43 | docs(sheet): Phase 3.6 TODO |
| **b654f0a** | **fix(sheet): 사진cover + 행삭제 + 스타일토글 + mailStatus제거 + stage배경색** |
| 9af8b73 | feat(imagefx): abort 버튼 + status bar |
| **714974f** | **fix(sheet): photo paste + selection highlight + stage row color + dup col** |
| 7f41284 | fix(imagefx): photorealistic 프롬프트 + 로고 |
| 8ae01c3 | fix(sheet): showPhotoToast dep |
| **5149109** | **fix(sheet): 사진 우클릭 업로드 + 완료 토스트** |
| **3c28b0a** | **fix(sheet): 열이동메뉴 + 메모배경색 + paste충돌방지** |
| **8d5125f** | **fix: 암호화 코드 복원 + Render 복원 API** |
| **0c31de5** | **fix(db): 272건 암호화 필드 평문 복원** |

---

## 2026-03-19 세션

| 커밋 | 내용 |
|------|------|
| (다수) | MailModal Gmail/Naver 토글 + handleSend API |
| (다수) | _decrypt_row 공백/개행 제거 edge case |
| (다수) | sheet_number 컬럼 + 3059건 rowid 마이그레이션 |
| (다수) | applyStyleToSelection 체크박스 전체 컬럼 적용 |
| (다수) | CLAUDE.md v5.0 SLIM + sheet_context.md |
| (다수) | Canvas Sheet Phase 1~3 기초 구현 (GridEngine 등) |
| (다수) | ClaudeBlog settings.py 신규 + --count N 지원 |
| (다수) | Gemini 키 고갈 오류 근본 수정 (_SESSION_EXHAUSTED) |

---

## 2026-03-20 이전 세션 (주요 피처)

| 날짜 | 내용 |
|------|------|
| 03-20 | CSP connect-src 와일드카드 수정 (CRITICAL-2) |
| 03-20 | MegaMenu DOM → router.push() SPA 네비게이션 |
| 03-20 | /api/track POST 신규, og:image 추가 |
| 03-20 | Employer: Job번호·업체명 더블클릭 인라인 편집 |
| 03-20 | MailComposer 헤더 드래그 이동 |
| 03-16 | ESLCafe RPA 자동화 craigslist_auto_rpa.py |
| 03-16 | Adobe TOS / Genuine 팝업 차단 |
| 03-15 | ClaudeBlog 전체 자동화 시스템 v6.6 |
| 03-14 | ImageFX 사진 생성 자동화 |
| 03-12 | Bridge 모니터 서버 v3.1 |
| 03-09 | FastAPI 백엔드 전면 재작성 |
| 03-05 | Next.js 15 프론트엔드 초기 구축 |
| 02-28 | HERO 3D 지구본 확정 잠금 |
| 02-24 | AES-256-GCM PII 암호화 시스템 |
| 02-21 | master.db 최초 구축 (SQLite 마이그레이션) |

---

## Canvas Sheet 현재 상태 (2026-03-20 기준)

### 완료된 기능
- [x] GridEngine Canvas 렌더링 (셀/헤더/스크롤/마우스/키보드)
- [x] SelectionManager (단일/범위/열선택/전체)
- [x] EditManager 인라인 더블클릭 편집
- [x] HistoryManager Undo/Redo (50단계)
- [x] StyleManager (굵기/기울임/취소선/색/배경/크기) + 토글
- [x] PrefsManager 컬럼 너비/순서 localStorage
- [x] 5탭 (active/focus/past/blacklist/all)
- [x] Pipeline 상태표시줄 (단계별 건수+업체명)
- [x] 사진 붙여넣기/우클릭 업로드/삭제/cover 채우기
- [x] 열 이동 (헤더 우클릭), 열 숨기기
- [x] 메모 배경색 color picker + 지우기
- [x] 행 삭제 (PATCH is_deleted:1)
- [x] stage 배경색 자동 적용 (33% 불투명도)
- [x] MailModal 구인자 스타일 (다크헤더/탭/칩/첨부)
- [x] 열 선택 → 스타일 전체 적용 (hasColSel 분기)
- [x] 완료 토스트 (초록/빨간, 3초)

### 미완료 (Phase 3~4)
- [ ] 진행단계 변경 → DB PATCH 연결 (High)
- [ ] 발송상태 태그 토글 → DB 반영 (Medium)
- [ ] 가상 렌더링 - 뷰포트 최적화 (Medium)
- [ ] 컬럼 필터 드롭다운 완성 (Low)
- [ ] CSV/Excel 내보내기 (Low)

---

## 현재 AI 핸드오프 문서 위치

| 파일 | 용도 |
|------|------|
| `docs/AI_CONTEXT.md` | 범용 AI 온보딩 (붙여넣기용) |
| `docs/AI_SECURITY_DESIGN.md` | 3계층 보안 설계 |
| `docs/claude_web_handoff.md` | Claude.ai 웹 전달용 |
| `.claude/work_state.md` | 세션 간 작업 상태 |
| `.memory/work-history.md` | 이 파일 (전체 이력) |
