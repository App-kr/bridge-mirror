# BRIDGE 프로젝트 — Claude 웹 전달용 핸드오프 문서
> 작성일: 2026-03-20 | 작성: Claude Code (Sonnet 4.6)
> 다음 세션에서 이 문서를 Claude.ai 웹에 붙여넣어 컨텍스트 이어받기

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
├── MailModal.tsx          — 메일 발송 모달
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

## 3. 이번 세션(2026-03-20) 완료된 작업 전체 목록

### 3-1. 암호화 필드 복원 (8회차 완결)
- **문제**: 국적/나이/현위치/레퍼런스/국내범죄 열이 AES-256-GCM Base64 문자열로 표시됨
- **원인**: 로컬 `.env`의 `BRIDGE_FIELD_KEY=VAULT` (플레이스홀더), 실제 키로 복호화 불가
- **해결**: `web_frontend/master.db` (평문 3057건) → `master.db`에 직접 복원
  - 복원 필드: nationality, current_location, dob, korean_criminal_record, reference, email, full_name, mobile_phone, kakaotalk, gender, health_info, religion, notes, criminal_record
- **Render 프로덕션**: 서버에 실제 키 존재 → 서버사이드 복호화 정상 (`남아공`, `미국` 등 한국어 정상 반환)

### 3-2. 집중관리 탭 추가 (commit `224d81a`)
```tsx
const FOCUS_STAGES = new Set(['interview', 'proposal', 'signed', 'guide_sent', 'guide_done', 'caution'])
const isFocusRow = (r: DataRow): boolean =>
  r.category === 'past' || (r.category === 'active' && FOCUS_STAGES.has(r.stage as string))
```

### 3-3. Pipeline 상태표시줄 (commit `72c173a`)
- 화면 상단에 어두운 배경 상태바: 진행단계별 건수 + 업체명 파싱
- `pipelineData` useMemo: stage별 그룹핑 + proposal 첫줄에서 업체명 추출

### 3-4. 열 이동/메모/사진 버그 수정 (commit `3c28b0a`)
- 헤더 우클릭 → "열 왼쪽으로" / "열 오른쪽으로" 추가
- 메모 배경색 color picker + "지우기" 버튼
- 사진 paste 시 textarea 포커스 충돌 방지 (early return)

### 3-5. 사진 우클릭 업로드 + 완료 토스트 (commit `5149109`)
- 행 우클릭 → "📷 사진 파일 선택..." / "🗑 사진 삭제"
- 업로드/붙여넣기 성공 시 하단 초록 토스트 (fadeInUp 0.2s)

### 3-6. 발송상태 열 제거 + 진행단계 배경색 (commit `714974f`)
- `mailAction`, `mailStatus` 열 v:false (숨김)
- stage 변경 시 해당 행 전체 배경색 자동 적용 (STAGES[stage].color 사용)

### 3-7. 사진/행삭제/스타일/mailStatus/stage배경색 (commit `b654f0a`)
- **사진 셀 cover 채우기**: `GridEngine.drawPhoto` → object-fit:cover 방식 (소스 중앙 크롭 후 셀 전체 채우기)
- **행 삭제**: 우클릭 컨텍스트 메뉴 "행 삭제" → `PATCH is_deleted:1` (soft delete)
- **스타일 토글**: B/I/S 버튼 클릭 시 현재 상태 반전 + 선택 전체 행 일괄 적용
- **mailStatus 열 완전 제거**: `defaultCols()`에서 삭제 (DataRow 인터페이스는 API 호환성 유지)
- **진행단계 배경색**: stage 값에 따라 행 전체 배경색 자동 적용 (33% 불투명도)

---

## 4. API 엔드포인트 (관련 부분)

```
GET  /api/admin/candidates?tab={tab}&limit={n}&offset={n}
PATCH /api/admin/candidates/{cid}          — 필드 수정
POST /api/admin/upload-image               — 사진 업로드 → { data: { url } }
GET  /api/admin/decrypt-check              — 암호화 진단
POST /api/admin/candidates/bulk-patch      — 대량 평문 복원 (이번 세션 추가)
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

export interface DataRow {
  id: number
  _cid?: string
  category: string     // 'active' | 'past' | 'blacklist'
  stage: string        // STAGES key
  mailStatus: string   // 쉼표 구분 tag key 목록 (내부 유지, UI 표시 안 함)
  photoUrl: string
  photoSize: number
  [key: string]: string | number | undefined
}
```

---

## 6. 미완료 / 알려진 이슈

| 항목 | 상태 | 비고 |
|------|------|------|
| 툴바 다중행 스타일 + 토글 | ✅ 완료 (`b654f0a`) | bold/italic/취소선 토글 |
| 행 삭제 | ✅ 완료 (`b654f0a`) | is_deleted=1 소프트 삭제 |
| 사진 셀 꽉 채우기 | ✅ 완료 (`b654f0a`) | cover 방식 canvas drawImage |
| mailStatus 열 제거 | ✅ 완료 (`b654f0a`) | defaultCols에서 완전 삭제 |
| 진행단계 배경색 | ✅ 완료 (`714974f`, `b654f0a`) | STAGES color 33% 불투명도 적용 |
| 진행단계 → DB 저장 | 미구현 | 현재 로컬 상태 변경만, PATCH 미연결 |
| 가상 렌더링 | 미구현 | Phase 4 과제 |
| Render 프로덕션 배포 | 자동 (autoDeploy: true) | main push 시 자동 배포 |

---

## 7. 로컬 개발 환경

```bash
# 프론트 (Next.js) — 이미 실행 중
# 백엔드 (FastAPI) — 이미 실행 중
# 서버 시작/종료 금지 (hot reload 중)

# Python 실행 시 항상 절대경로 사용
"Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" script.py

# Git push (deploy_gate hook 자동 처리)
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

*이 문서는 Claude Code 자동 생성 | 다음 대화 시작 시 이 문서 전체를 Claude.ai에 붙여넣기*
