# Canvas Sheet 컨텍스트
경로: `web_frontend/src/app/admin/sheet/`  최종 수정: 2026-03-20

## 파일 구조 및 역할

| 파일 | 역할 (핵심 3줄) |
|------|----------------|
| `page.tsx` | 진입점. AdminAuth 인증 후 BridgeCanvasSheet 렌더. 인증 외 로직 없음. |
| `BridgeCanvasSheet.tsx` | 메인 React Wrapper v4. 데이터 로드·Google Sheets 툴바·줌·메일모달·사진 붙여넣기. |
| `MailModal.tsx` | 선택 행 메일 발송 모달. MAIL_TEMPLATES 기반 템플릿 선택·미리보기·발송. |
| `engine/GridEngine.ts` | Canvas 그리드 코어 v4. 행번호(체크박스 제거)·코너전체선택·셀 렌더링·스크롤. |
| `engine/EditManager.ts` | 인라인 셀 편집. 더블클릭→input overlay→Enter/Esc 확정·취소. |
| `engine/HistoryManager.ts` | Undo/Redo 스택. Ctrl+Z/Y. 최대 50단계 보관. |
| `engine/PrefsManager.ts` | 컬럼 너비·순서 localStorage 영속화. 세션 간 유지. |
| `engine/SelectionManager.ts` | 셀·행 선택. 단일·범위(Shift)·전체선택(Ctrl+A). |
| `engine/StyleManager.ts` | 셀 서식. 굵기·기울임·글자색·배경색·글자크기. |
| `engine/types.ts` | DataRow · MailTemplate · Column · CellStyle 공통 타입 정의. |

## Phase TODO

### Phase 1 — 기초 엔진 ✅
- [x] GridEngine Canvas 렌더링 기반
- [x] SelectionManager 단일/범위 선택
- [x] PrefsManager 컬럼 너비/순서 영속화

### Phase 2 — 편집 기능 ✅
- [x] EditManager 인라인 편집
- [x] HistoryManager Undo/Redo
- [x] StyleManager 셀 서식 (굵기·색·배경)

### Phase 3 — 데이터 연동 ✅
- [x] API 연결 + 전체 로드
- [x] MailModal 발송 UI
- [ ] 발송상태 태그 토글 → DB PATCH 반영
- [ ] 진행단계 드롭다운 → DB 저장

### Phase 3.5 — Google Sheets 스타일 ✅ (v4)
- [x] 체크박스 제거 → 순수 행번호 (Google Sheets style)
- [x] 코너 전체선택 버튼 (좌상단 클릭 → 전체 선택)
- [x] 행번호 클릭 = 행 선택 (Ctrl/Shift 지원)
- [x] 툴바 개선: Undo/Redo 전면 배치 + 줌 + 폰트 드롭다운
- [x] 줌 기능 (50%~150%, CSS transform 기반)

### Phase 4 — 성능/UX
- [ ] 가상 렌더링 (뷰포트 밖 행 skip)
- [ ] 컬럼 필터 드롭다운 완성
- [ ] CSV/Excel 내보내기

## 참조 파일 (읽기 전용)
- API 스키마: `api_server.py` → `/api/admin/candidates`
- 타입 원본: `engine/types.ts` → `DataRow` 인터페이스
- 실운영 템플릿: `engine/types.ts` → `MAIL_TEMPLATES`

## 수정 금지
- `engine/types.ts` DataRow 인터페이스 — API 응답 스키마 의존
- `MailModal.tsx` MAIL_TEMPLATES 내용 — 실운영 발송 템플릿
