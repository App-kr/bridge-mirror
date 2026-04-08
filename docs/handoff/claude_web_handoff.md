# BRIDGE 프로젝트 — Claude 웹 전달용 핸드오프 문서
> 작성일: 2026-03-20 (v2) | 작성: Claude Code (Sonnet 4.6)
> 다음 세션에서 이 문서를 Claude.ai 웹에 붙여넣어 컨텍스트 이어받기
> **상세 컨텍스트**: `docs/AI_CONTEXT.md` / **보안 설계**: `docs/AI_SECURITY_DESIGN.md`

---

## 1. 프로젝트 개요

- **서비스**: bridgejob.co.kr — ESL(원어민 영어교사) 채용 에이전시
- **스택**: FastAPI(Python) + Next.js 15(TypeScript) + SQLite
- **배포**: 백엔드 → Render (`bridge-n7hk.onrender.com`) / 프론트 → Vercel
- **로컬 DB**: `Q:/Claudework/bridge base/master.db` (candidates 3059건)
- **GitHub**: koreadobby/bridge (main 브랜치 → autoDeploy)

---

## 2. 핵심 기능: Canvas Spreadsheet (관리자 시트)

### 위치
```
web_frontend/src/app/admin/sheet/
├── page.tsx               — 진입점 (AdminAuth 인증)
├── BridgeCanvasSheet.tsx  — 메인 React 래퍼 (3000줄+)
├── MailModal.tsx          — 메일 발송 모달 (구인자 스타일 재작성 완료)
└── engine/
    ├── GridEngine.ts      — Canvas 그리드 코어 (렌더링/스크롤/마우스/키)
    ├── EditManager.ts     — 인라인 편집 (더블클릭 → input overlay)
    ├── HistoryManager.ts  — Undo/Redo (Ctrl+Z/Y, 50단계)
    ├── PrefsManager.ts    — 컬럼 너비/순서 localStorage 영속화
    ├── SelectionManager.ts — 셀/행 선택 (단일/범위/전체)
    ├── StyleManager.ts    — 셀 서식 (굵기/기울임/색/배경/크기)
    └── types.ts           — 공통 타입/상수 (DataRow, ColDef, STAGES 등)
```

### 탭 구조
| 탭 키 | 설명 |
|-------|------|
| `active` | 구직자 (DB category='active') |
| `focus` | 집중관리 (stage: interview/proposal/signed/guide_sent/guide_done/caution 인 active) |
| `past` | 체결완료 (DB category='past') |
| `blacklist` | 블랙리스트 |
| `all` | 전체 |

---

## 3. 2026-03-20 세션 완료된 작업 전체 목록

### 3-1. 암호화 필드 복원 (완결)
- **해결**: `web_frontend/master.db` (평문 3057건) → `master.db`에 직접 복원
- **Render 프로덕션**: 서버에 실제 키 존재 → 서버사이드 복호화 정상

### 3-2. 집중관리 탭 추가 (commit `224d81a`)
```tsx
const FOCUS_STAGES = new Set(['interview', 'proposal', 'signed', 'guide_sent', 'guide_done', 'caution'])
const isFocusRow = (r: DataRow): boolean =>
  r.category === 'past' || (r.category === 'active' && FOCUS_STAGES.has(r.stage as string))
```

### 3-3. Pipeline 상태표시줄 (commit `72c173a`)
- 화면 상단 어두운 배경 상태바: 진행단계별 건수 + 업체명 파싱

### 3-4. 열 이동/메모/사진 버그 수정 (commit `3c28b0a`)
- 헤더 우클릭 → "열 왼쪽으로" / "열 오른쪽으로"
- 메모 배경색 color picker + "지우기" 버튼
- 사진 paste 시 textarea 포커스 충돌 방지

### 3-5. 사진 우클릭 업로드 + 완료 토스트 (commit `5149109`)
- 행 우클릭 → "📷 사진 파일 선택..." / "🗑 사진 삭제"
- 업로드/붙여넣기 성공 시 하단 초록 토스트

### 3-6. 발송상태 열 제거 + 진행단계 배경색 (commit `714974f`)
- `mailAction`, `mailStatus` 열 숨김
- stage 변경 시 해당 행 전체 배경색 자동 적용

### 3-7. 사진/행삭제/스타일/mailStatus/stage배경색 (commit `b654f0a`)
- 사진 셀 object-fit:cover 방식 (중앙 크롭)
- 행 삭제: 우클릭 → PATCH is_deleted:1 소프트 삭제
- B/I/S 버튼 토글: 현재 상태 반전 + 선택 전체 행 일괄 적용
- mailStatus 열 defaultCols()에서 완전 삭제
- stage 값에 따라 행 전체 배경색 (33% 불투명도)

### 3-8. 열 선택 스타일 버그 수정 + MailModal 재작성 (commit `60447ee`)
- `hasColSel` 분기: 열 선택 시 전체 행 × 선택 열 대상 batchSet
- MailModal 완전 재작성: 구인자 스타일 (다크 헤더, 템플릿 탭, 수신자 칩)

### 3-9. AI 핸드오프 보안 설계 (현재)
- `docs/AI_CONTEXT.md` — 범용 AI 온보딩 문서
- `docs/AI_SECURITY_DESIGN.md` — AI 보안 설계

---

## 4. API 엔드포인트 (관련 부분)

```
GET  /api/admin/candidates?tab={tab}&limit={n}&offset={n}
PATCH /api/admin/candidates/{cid}
POST /api/admin/upload-image               — 사진 업로드 → { data: { url } }
POST /api/admin/mail/send                  — 메일 발송
GET  /api/admin/decrypt-check              — 암호화 진단
POST /api/admin/candidates/bulk-patch      — 대량 평문 복원
```

---

## 5. 중요 상수 / 타입

```typescript
// engine/types.ts
export const STAGES: Stage[] = [
  { key: 'none',       label: '—',     color: '#ffffff', text: '#000000' },
  { key: 'interview',  label: '인터뷰', color: '#fef9c3', text: '#000000' },
  { key: 'proposal',   label: '계약제안', color: '#fde68a', text: '#000000' },
  { key: 'signed',     label: '서명완료', color: '#bbf7d0', text: '#000000' },
  { key: 'guide_sent', label: '안내발송', color: '#93c5fd', text: '#000000' },
  { key: 'guide_done', label: '안내완료', color: '#dbeafe', text: '#000000' },
  { key: 'caution',    label: '주의',    color: '#fecaca', text: '#000000' },
  { key: 'lost',       label: '두절',    color: '#e5e7eb', text: '#666666' },
]
```

---

## 6. 미완료 / 알려진 이슈

| 항목 | 상태 | 비고 |
|------|------|------|
| 진행단계 → DB 저장 | 미구현 | 현재 로컬 상태 변경만, PATCH 미연결 |
| 발송상태 태그 DB 반영 | 미구현 | Phase 3 |
| 가상 렌더링 | 미구현 | Phase 4 |

---

## 7. 로컬 개발 환경

```bash
# 프론트 (Next.js) — 이미 실행 중 (서버 시작/종료 금지)
# 백엔드 (FastAPI) — 이미 실행 중 (서버 시작/종료 금지)

# Git push
git add 파일 && git commit -m "메시지" && git push origin main
```

---

## 8. 금지 사항 (절대 준수)

- `master.db` 이동/삭제 금지
- hard-delete 금지 → `is_deleted=1` 논리삭제만
- HERO 애니메이션 수정 금지
- CLAUDE.md IMMUTABLE CORE 삭제 금지
- 관리자 비밀번호 코드에 하드코딩 금지
- `Q:` 드라이브 외부 파일 생성 금지

---

## 9. 팀 정보

- **Scarlett** — 대표 (사용자)
- **Claude Code** — AI 개발자 (현재 세션)
- 모델: claude-sonnet-4-6 (Opus 사용 금지)

---

## 10. 다른 AI에서 시작할 때

1. 이 파일 전체 붙여넣기
2. 또는 더 상세한 컨텍스트: `docs/AI_CONTEXT.md` 전체 붙여넣기
3. 보안 규칙: `docs/AI_SECURITY_DESIGN.md` 확인

---

*이 문서는 Claude Code 자동 생성 | 다음 대화 시작 시 이 문서 전체를 Claude.ai에 붙여넣기*
