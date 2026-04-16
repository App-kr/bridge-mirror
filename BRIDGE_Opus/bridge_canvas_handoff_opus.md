# BRIDGE Canvas Sheet — Opus 이관 핸드오프 문서
> 작성일: 2026-04-17 | 이 문서를 Claude Code Opus 세션 시작 시 통째로 붙여넣기

---

## 1. 프로젝트 기본 정보

- **서비스**: BRIDGE (bridgejob.co.kr) — ESL 원어민 교사 채용 에이전시
- **운영자**: Scarlett
- **PC**: Taco (192.168.0.2), Q: 드라이브 기준 작업
- **스택**: FastAPI(Python) + Next.js 15(TypeScript) + SQLite(master.db)
- **배포**: 백엔드 → Render / 프론트 → Vercel (bridge-chi-lime.vercel.app)
- **GitHub**: koreadobby/bridge (main 브랜치)
- **Render**: autoDeploy:true (main push 시 자동 배포)
- **로컬 DB**: Q:\Claudework\bridge base\master.db (candidates 3059건)
- **Python**: Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe (항상 이 경로)

---

## 2. Canvas Sheet 파일 구조

```
Q:\Claudework\bridge base\web_frontend\src\app\admin\sheet\
├── page.tsx                  — 진입점
├── BridgeCanvasSheet.tsx     — 메인 React 래퍼 (3000줄+)
├── MailModal.tsx             — 구직자 전용 메일 발송 모달
└── engine/
    ├── GridEngine.ts         — Canvas 렌더링 코어 (핵심)
    ├── EditManager.ts        — 더블클릭 인라인 편집
    ├── HistoryManager.ts     — Undo/Redo (Ctrl+Z/Y)
    ├── PrefsManager.ts       — 열너비/순서 localStorage 저장
    ├── SelectionManager.ts   — 셀/행/열 선택
    ├── StyleManager.ts       — 셀 서식 (굵기/색/크기 등)
    └── types.ts              — 공통 타입/상수
```

---

## 3. 탭 구조 (확정)

| 탭 키 | 라벨 | 조건 |
|-------|------|------|
| `active` | 구직자 | DB category='active' |
| `focus` | 집중관리 | category='active' AND stage IN(interview/proposal/signed/guide_sent/guide_done/caution) |
| `past` | 체결완료 | DB category='past' |
| `blacklist` | 블랙리스트 | DB category='blacklist' |
| `all` | 전체 | 전체 |

---

## 4. STAGES 상수 (types.ts 기준)

```typescript
export const STAGES = [
  { key: 'none',       label: '—',      color: '#ffffff', text: '#000000' },
  { key: 'interview',  label: '인터뷰',  color: '#fef9c3', text: '#000000' },
  { key: 'proposal',   label: '계약제안', color: '#fde68a', text: '#000000' },
  { key: 'signed',     label: '서명완료', color: '#bbf7d0', text: '#000000' },
  { key: 'guide_sent', label: '안내발송', color: '#93c5fd', text: '#000000' },
  { key: 'guide_done', label: '안내완료', color: '#dbeafe', text: '#000000' },
  { key: 'caution',    label: '주의',    color: '#fecaca', text: '#000000' },
  { key: 'lost',       label: '두절',    color: '#e5e7eb', text: '#666666' },
]
```

---

## 5. 오늘 세션(2026-03-21)까지 완료된 작업

### 5-1. 완료 커밋 목록
| 커밋 | 내용 |
|------|------|
| `224d81a` | 집중관리 탭 추가 |
| `72c173a` | Pipeline 상태표시줄 |
| `3c28b0a` | 열이동/메모/사진 버그 수정 |
| `5149109` | 사진 우클릭 업로드 + 완료 토스트 |
| `714974f` | 발송상태 열 제거 + stage 배경색 |
| `b654f0a` | 사진 cover채우기 / 행삭제 softdelete / B-I-S 토글 / mailStatus 완전 제거 |
| `b231cc1` | 행전체색상 / 메일모달 Gmail·Naver 토글 / decrypt 강화 / 번호 sheet_number 마이그레이션 |

### 5-2. 암호화 현황
- 로컬 master.db: web_frontend/master.db에서 평문 3057건 직접 복원 완료
- Render 프로덕션: 서버에 실제 BRIDGE_FIELD_KEY 존재 → 서버사이드 복호화 정상
- 로컬 .env의 BRIDGE_FIELD_KEY=VAULT (플레이스홀더) → 로컬은 평문 DB 사용

---

## 6. 현재 미완료 항목 (우선순위 순)

### [P0] 즉시 수정 필요

#### A. 셀 내 이상한 수평선 제거 + 텍스트 줄바꿈 수정
**증상**:
- 모든 셀 내부에 수평선이 그어짐 (구분선이 clip 안에서 그려지는 버그)
- '영국' 같은 한국어가 '영' / '국' 으로 한 글자씩 수직 렌더링됨

**원인**:
- `ctx.stroke()`가 `ctx.clip()` 내부에서 실행됨
- `split(' ')`로 단어 분리 시 공백 없는 한국어 텍스트 처리 안 됨

**수정 방법**:
```
renderContent()를 2-패스 구조로 분리:
  PASS 1: 배경색 + 텍스트 (ctx.save/clip/restore 안에서 fillText만)
  PASS 2: 구분선만 별도 루프 (clip 없이 strokeStyle+beginPath+stroke)

drawWrappedText() 줄바꿈 로직:
  공백 있는 텍스트 → 단어 단위 줄바꿈 (기존)
  공백 없는 텍스트(한국어) → 글자 단위 줄바꿈
  셀 너비 초과 시 말줄임표(…)
  행 높이 초과 줄은 그리지 않음
```

#### B. 열 스타일 전체 행 미반영
**증상**: 열 선택 후 배경색 적용 시 최상단 1개 셀만 반영됨
**원인**: `applyStyle()`에서 `cids` 배열이 selection 범위의 첫 행만 포함됨
**수정**:
```typescript
// applyStyle() 에서
const isAllRows = r1 === 0 && r2 === eng.data.length - 1
const cids = isAllRows
  ? allData.current.map(r => String(r.candidate_id ?? r.id))  // allData 전체
  : eng.data.slice(r1, r2 + 1).map(r => String(r.candidate_id ?? r.id))

// StyleManager.ts getCid 통일
const getCid = (row: any) => String(row.candidate_id ?? row.id ?? '')
// applyToSelection, getStyle, _getAllIds 모두 동일 getCid 사용
```

#### C. ABCD 열 클릭 → 개별 열 선택만 (전체선택 버그)
**증상**: 알파벳 클릭 시 전체 선택됨
**원인**: `_hitTest()`에서 alphaClick 조건 분기 버그
**수정**:
```typescript
if (hit.type === 'alphaClick') {
  this.selection = {
    start: { row: 0, col: hit.colIndex },
    end: { row: this.data.length - 1, col: hit.colIndex }
  }
  this.renderSelection()
  return  // 반드시 return
}
```

#### D. 행번호 칸에 4자리 숫자(강사번호) 표시되는 버그
**원인**: mgtNum(sheet_number) 값이 ROW_NUM 영역에 그려짐
**수정**: 행번호 칸은 `r + 1` 순서 숫자만, 강사번호는 별도 '번호' 컬럼에만

#### E. 열 정렬 더블클릭으로만 (단일 클릭 정렬 방지)
**수정**:
```typescript
// 단일 클릭 → 정렬 코드 제거
// ghost.addEventListener('dblclick') 에서만 _toggleSort() 호출
```

### [P1] 기능 추가

#### F. 전체 행높이/열너비 일괄 조절
- 툴바에 행높이/열너비 입력창 추가
- 변경 시 모든 열/행에 동일 적용
- savePrefs()로 탭 전환 후에도 유지

#### G. 진행단계(stage) 변경 → DB PATCH 미연결
- 현재: 로컬 상태만 변경
- 수정: stage 변경 시 `PATCH /api/admin/candidates/{id}` 호출

#### H. 우클릭 카테고리 이동 메뉴
- 선택 행 → 체결완료/구직자/블랙리스트 이동
- `PATCH category: 'past'/'active'/'blacklist'`

#### I. 신규 접수 깜박임 알림
- 30초 폴링 `/api/admin/candidates/new-since?since=...`
- 상단 배너 흰/검 깜박임 + 클릭 시 해당 행으로 스크롤

#### J. 메일 발송 모달 (구직자 전용)
- 템플릿: 인터뷰안내/계약안내/비자안내/정착안내/세금안내/이체안내/갱신안내/직접작성
- Gmail/Naver 토글 발신
- 1:1 개별 발송 (타인 정보 미노출)
- 미리보기 기능

#### K. 가상 렌더링 (성능)
- 현재 3059건 전체 DOM/Canvas 렌더링
- 화면에 보이는 행만 렌더링 (overscan 15)

---

## 7. API 엔드포인트

```
GET  /api/admin/candidates?tab={tab}&limit={n}&offset={n}
PATCH /api/admin/candidates/{id}          — 필드 수정
POST /api/admin/upload-image              — 사진 업로드 → { data: { url } }
POST /api/admin/send-mail                 — 메일 발송
GET  /api/admin/candidates/new-since?since={datetime}  — 신규 건수
PUT  /api/admin/candidates/{id}/viewed    — 확인 처리
GET  /api/admin/prefs/{key}              — 사용자 설정 조회
POST /api/admin/prefs/{key}              — 사용자 설정 저장
```

---

## 8. 절대 금지 사항

- `master.db` 이동/삭제 금지
- hard-delete 금지 → `is_deleted=1` 논리삭제만
- HERO 애니메이션 (검정배경+현수교) 수정 금지
- CLAUDE.md IMMUTABLE CORE 삭제 금지
- 비밀번호/API키 코드 하드코딩 금지
- Q: 드라이브 외부 파일 생성 금지
- 서버(FastAPI/Next.js dev) 재시작 금지 (hot reload 중)

---

## 9. 환경 / 실행 규칙

```bash
# Python 항상 이 경로
"Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 script.py

# Git 커밋 (작업 전후 필수)
git add -A && git commit -m "PRE: 작업명" && git push

# 빌드 검증
cd web_frontend && npx tsc --noEmit && npm run build

# DB 업로드 (로컬→Render)
python tools/render_db_upload.py
```

---

## 10. 첫 번째 실행할 작업 (우선순위)

**즉시 실행**: P0-A (셀 내 선 제거 + 줄바꿈 수정) → P0-B (열 스타일) → P0-C,D,E

```
작업 시작 전 반드시:
1. git log --oneline -5  (현재 커밋 상태 확인)
2. GridEngine.ts 전체 읽기
3. BridgeCanvasSheet.tsx applyStyle() 찾기
4. 백업: git add -A && git commit -m "PRE: P0버그수정"
```

---

## 11. 구글시트 원본과의 차이점

| 항목 | 구글시트 원본 | BRIDGE Sheet 현재 |
|------|-------------|-----------------|
| 렌더링 | Canvas | Canvas ✅ |
| 행번호 | 1 2 3... 고정 | ❌ 강사번호 혼재 (P0-D) |
| 열 헤더 | A B C + 한글명 | ✅ 구현됨 |
| 더블클릭 정렬 | ✅ | ❌ 단일클릭 (P0-E) |
| 셀 줄바꿈 | ✅ 정상 | ❌ 한국어 수직 (P0-A) |
| 셀 내 선 | ❌ 없음 | ❌ 있음 (P0-A) |
| 열 전체 스타일 | ✅ | ❌ 1행만 (P0-B) |
| 우클릭 메뉴 | ✅ | ⚠️ 부분구현 |
| 자동저장 | ✅ | ✅ localStorage+DB |
| 사진 Ctrl+V | ✅ | ✅ |
| 메일 발송 | ✅ | ✅ 모달 구현 |

---

*이 문서는 2026-04-17 Claude.ai 웹에서 자동 생성*
*Claude Code Opus 세션 시작 시 전체 붙여넣기 후 작업 시작*
