# BRIDGE AI 범용 컨텍스트 — 어떤 AI에나 붙여넣기 가능
> 버전: 2026-03-20 | 작성: Claude Code (Sonnet 4.6)
> 이 문서를 Claude.ai / GPT / Gemini 등 어떤 AI에나 첫 메시지로 붙여넣어 컨텍스트를 즉시 이어받을 수 있습니다.
> **⚠️ 이 파일에는 API 키 / 비밀번호 / 암호화 키가 포함되지 않습니다.**

---

## ⚡ 즉시 규칙 (AI 시작 전 반드시 읽기)

| 규칙 | 내용 |
|------|------|
| 작업 전 백업 | `python "Q:\Claudework\bridge base\tools\bridge_backup.py" backup "작업명" --type pre-task` |
| 서버 시작/종료 금지 | 로컬 서버 Hot Reload 상시 실행 중 |
| hard-delete 금지 | 삭제는 반드시 `is_deleted=1` |
| master.db 이동 금지 | 절대 경로: `Q:/Claudework/bridge base/master.db` |
| 묻지 말고 실행 | 완료 후 결과만 보고 |
| GUI 앱 실행 금지 | 백그라운드 실행만 허용 |
| C: 드라이브 외부 접근 금지 | 모든 아티팩트는 Q:\Claudework\bridge base 내부만 |
| Opus 모델 사용 금지 | 기본: claude-sonnet-4-6 |

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 서비스 | bridgejob.co.kr — 한국 ESL(원어민 영어교사) 채용 에이전시 |
| 오너 | Scarlett (대표) |
| 스택 | FastAPI (Python) + Next.js 15 (TypeScript) + SQLite |
| 배포 | 백엔드 → Render (`bridge-n7hk.onrender.com`) / 프론트 → Vercel |
| 로컬 루트 | `Q:\Claudework\bridge base\` |
| GitHub | koreadobby/bridge (main → autoDeploy) |

---

## 2. 디렉토리 구조

```
Q:\Claudework\bridge base\
├── api_server.py              — FastAPI 백엔드 메인 (300KB+)
├── master.db                  — SQLite DB (6.6MB) ← 절대 이동 금지
├── .env                       — 환경변수 (git 제외, 공개 금지)
├── .bridge.key                — AES-256 암호화 키 (git 제외)
├── web_frontend/              — Next.js 15 프론트엔드
│   └── src/app/admin/sheet/   — Canvas Spreadsheet (핵심 기능)
│       ├── BridgeCanvasSheet.tsx  — 메인 래퍼 (3000줄+)
│       ├── MailModal.tsx          — 메일 발송 모달
│       └── engine/
│           ├── GridEngine.ts      — Canvas 그리드 코어
│           ├── EditManager.ts     — 인라인 편집
│           ├── HistoryManager.ts  — Undo/Redo
│           ├── PrefsManager.ts    — 컬럼 영속화
│           ├── SelectionManager.ts — 셀/행 선택
│           ├── StyleManager.ts    — 셀 서식
│           └── types.ts           — 공통 타입/상수
├── tools/                     — 유지보수 스크립트
├── docs/                      — 문서
└── backups/                   — 자동 백업 (임의 삭제 금지)
```

---

## 3. DB 구조 (master.db)

| 테이블 | 건수 | 설명 |
|--------|------|------|
| candidates | ~3059 | 구직자 (원어민 교사) |
| client_inquiries | ~1227 | 구인자 (학교/어학원) |
| jobs | ~1072 | 구인 포지션 |

### candidates 주요 컬럼
```sql
id, _cid (고유키), category ('active'|'past'|'blacklist'),
stage ('none'|'interview'|'proposal'|'signed'|'guide_sent'|'guide_done'|'caution'|'lost'),
email, full_name, mobile_phone, kakaotalk,
nationality, current_location, dob, gender,
background, university, total_exp, start_date, pref_region,
reference, current_salary, hope_salary, degree, major, cert,
housing, religion, e2_visa, crim_check, domestic_crim,
info_provide, verified, source, timestamp,
hired, wage, move_in, housing_cost, intro_fee, process,
history, notes, preference, applied, proposal, arc,
sheet_number, photo_url, photo_size,
is_deleted (0=정상, 1=삭제됨),
row_styles (JSON 셀 서식), row_height,
memo_bg (메모 배경색)
```

### 암호화 필드 (AES-256-GCM)
- 프로덕션: `BRIDGE_FIELD_KEY` 환경변수로 서버 복호화
- 암호화 대상: nationality, current_location, dob, korean_criminal_record, reference, email, full_name, mobile_phone, kakaotalk, gender, health_info, religion, notes, criminal_record

---

## 4. Canvas Spreadsheet — 탭 구조

| 탭 | DB 조건 | 설명 |
|----|---------|------|
| `active` | category='active' | 구직자 |
| `focus` | active AND stage IN (interview/proposal/signed/guide_sent/guide_done/caution) | 집중관리 |
| `past` | category='past' | 체결완료 |
| `blacklist` | category='blacklist' | 블랙리스트 |
| `all` | 전체 | 전체 보기 |

### 진행단계 (STAGES) 색상
| key | label | 배경색 |
|-----|-------|--------|
| none | — | #ffffff |
| interview | 인터뷰 | #fef9c3 |
| proposal | 계약제안 | #fde68a |
| signed | 서명완료 | #bbf7d0 |
| guide_sent | 안내발송 | #93c5fd |
| guide_done | 안내완료 | #dbeafe |
| caution | 주의 | #fecaca |
| lost | 두절 | #e5e7eb |

---

## 5. API 엔드포인트 (로컬: http://localhost:8000)

```
# 관리자 인증
POST /api/admin/login                     — 로그인 (x-admin-key 헤더 반환)

# 구직자 관리
GET  /api/admin/candidates                — 목록 (?tab=active&limit=50&offset=0)
PATCH /api/admin/candidates/{cid}         — 필드 수정 (x-admin-key 필수)
DELETE /api/admin/candidates/{cid}        — 소프트 삭제 (is_deleted=1)
POST /api/admin/candidates/bulk-patch     — 대량 필드 수정

# 사진
POST /api/admin/upload-image              — 사진 업로드 → { data: { url } }

# 메일
POST /api/admin/mail/send                 — 메일 발송 (FormData)

# 구인자
GET  /api/admin/employers                 — 구인자 목록
GET  /api/admin/inquiries/new-count       — 신규 문의 건수 폴링

# 진단
GET  /api/admin/decrypt-check             — 암호화 진단
```

---

## 6. 프론트엔드 환경

```bash
# 로컬 개발
프론트: http://localhost:3002 (Next.js 15, hot reload 중)
백엔드: http://localhost:8000 (FastAPI, hot reload 중)

# 절대 실행 금지 (이미 실행 중)
# npm run dev / uvicorn 시작 명령

# 빌드 (필요 시)
cd web_frontend && npm run build
```

---

## 7. 완료된 주요 작업 이력 (2026-03 기준)

| 커밋 | 내용 |
|------|------|
| 224d81a | 집중관리 탭 추가 |
| 72c173a | Pipeline 상태표시줄 |
| 3c28b0a | 열 이동/메모 배경색/사진 paste 충돌 수정 |
| 5149109 | 사진 우클릭 업로드 + 완료 토스트 |
| 714974f | 발송상태 열 제거 + 진행단계 배경색 |
| b654f0a | 사진 cover 채우기 + 행 삭제 + 스타일 토글 |
| 60447ee | 열 선택 스타일 버그 수정 + MailModal 재작성 |

---

## 8. 미완료 / 다음 작업

| 항목 | 우선순위 | 비고 |
|------|---------|------|
| 진행단계 변경 → DB PATCH 연결 | High | 현재 로컬 상태만, API 미연결 |
| 발송상태 태그 토글 → DB 반영 | Medium | Phase 3 |
| 가상 렌더링 (대용량 최적화) | Medium | Phase 4 |
| 컬럼 필터 드롭다운 완성 | Low | Phase 4 |
| CSV/Excel 내보내기 | Low | Phase 4 |

---

## 9. 절대 금지 사항 (IMMUTABLE)

```
⛔ master.db 이동/삭제 금지
⛔ .env / .bridge.key 코드에 하드코딩 금지
⛔ hard-delete 금지 → is_deleted=1 논리삭제만
⛔ HERO 애니메이션 수정 금지 (EarthGlobe.tsx 잠금)
⛔ 관리자 비밀번호 코드에 하드코딩 금지
⛔ Q: 드라이브 외부 파일 생성 금지
⛔ Git push 전 로컬 확인 없이 push 금지
⛔ SQL f-string 삽입 금지 (100% parameterized query)
⛔ CLAUDE.md IMMUTABLE CORE 섹션 삭제/수정 금지
⛔ Opus 모델 사용 금지 (명시적 허가 없이)
```

---

## 10. 작업 완료 루틴

```bash
# 1. 코드 수정 완료 후
python -X utf8 tools/auto_finalize.py "작업명"

# 또는 수동
git add [파일] && git commit -m "type(scope): 설명" && git push origin main

# 2. Render 자동 배포 확인
# → main push 시 https://bridge-n7hk.onrender.com 자동 배포
```

---

## 11. 팀 정보

| 이름 | 역할 |
|------|------|
| Scarlett | 대표 (사용자) |
| Claude Code | AI 개발자 (claude-sonnet-4-6) |

> MARK 명칭 사용 금지 — 반드시 Scarlett / Claude Code 사용

---

*이 문서는 Claude Code 자동 생성 — 다른 AI 세션 시작 시 이 파일 전체를 붙여넣기*
*민감 정보(키/비밀번호) 미포함 — 공유 안전*
