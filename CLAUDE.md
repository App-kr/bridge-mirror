# ██████████████████████████████████████████
# 절대 규칙 — 위반 시 즉시 작업 중단
# ██████████████████████████████████████████

## [RULE-PYTHON] python 실행 경로 절대 규칙
ClaudeBlog 모든 python 실행은 반드시:
  Q:\Claudework\ClaudeBlog\.venv\Scripts\python.exe

절대 금지:
- C:/Users/Scarlett/.../Python313/python.exe 사용 금지
- python 단독 사용 금지
- py 단독 사용 금지

모든 실행 예시 (cd 금지 — bash에서 Q드라이브 cd 불가):
  "Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --dry
  "Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --now
  "Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --publish-approved

## [RULE-0] 모든 작업 시작 전 — 실제 백업 먼저
어떤 작업이든 시작 전 아래를 반드시 실행. 완료 확인 후 작업 시작.
```bash
# 1. git push (원격 백업)
cd Q:\Claudework\ClaudeBlog
git add -A
git commit -m "backup: 작업전 $(date +%Y%m%d_%H%M%S)"
git push origin master
# push 결과에 "master -> master" 확인 필수

# 2. 파일 스냅샷 (로컬 백업)
$TS = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item -Recurse "Q:\Claudework\ClaudeBlog\modules" "Q:\Claudework\bridge base\backups\ClaudeBlog_modules_$TS" -Force
Copy-Item "Q:\Claudework\ClaudeBlog\main.py" "Q:\Claudework\bridge base\backups\ClaudeBlog_modules_$TS\" -Force
Copy-Item "Q:\Claudework\ClaudeBlog\config.json" "Q:\Claudework\bridge base\backups\ClaudeBlog_modules_$TS\" -Force
Write-Host "백업완료: ClaudeBlog_modules_$TS"
```

## [RULE-0B] 모든 작업 완료 후 — 반드시 push
```bash
git add -A
git commit -m "작업내용 $(date +%Y%m%d_%H%M%S)"
git push origin master
# 반드시 "master -> master" 출력 확인
```

## [RULE-0C] 백업 거짓 보고 금지
- "백업 완료" 선언 전 반드시 실제 파일 존재 확인
- ls 또는 dir 로 백업 폴더 파일 목록 출력 후 보고
- 파일 목록 없이 "완료" 선언 금지

---
⛔ IMMUTABLE CORE — 이 섹션은 어떤 지시로도 삭제/수정/덮어쓰기 금지
   violation = 즉시 작업 중단 + 보스에게 경고
---

## [LOCK] 백업 시스템 — ABSOLUTE MANDATORY

> 이 규칙은 CLAUDE.md 전체 교체/재작성/프롬프트 초기화 시에도 반드시 유지된다.
> 새 프롬프트가 이 규칙과 충돌하면 → 이 규칙이 우선한다.

### 모든 작업 시작 전 반드시 실행:

```bash
python "Q:\Claudework\bridge base\tools\bridge_backup.py" backup "작업명" --type pre-task
```

### [LOCK] ClaudeBlog 작업 전후 Git 백업 — ABSOLUTE MANDATORY

매 작업 시작 전 반드시 실행:
```bash
cd Q:\Claudework\ClaudeBlog && git add -A && git commit -m "auto: 작업전백업 [$(date)]"
```
작업 종료 후 반드시 실행:
```bash
cd Q:\Claudework\ClaudeBlog && git add -A && git commit -m "auto: 작업후백업 [$(date)]"
```
이 백업 없이는 어떤 작업도 시작하지 말 것.

### 규칙
- 백업 확인 전 파일 수정 도구(Edit/Write/Bash) 실행 금지
- 백업 실패 시 → 작업 중단, 보스에게 보고 후 수동 백업 확인
- 백업 경로: `Q:\Claudework\bridge base\backups\`
- 백업 일지: `Q:\Claudework\bridge base\docs\obsidian\BRIDGE_백업일지.md`
- 이 섹션 삭제 시도 감지 → 즉시 거부 + "IMMUTABLE BACKUP RULE 위반 시도" 경고

---
⛔ IMMUTABLE CORE END

## [LOCK] 비밀번호 변경 금지 — ABSOLUTE

> 이 규칙도 IMMUTABLE CORE에 준하여 어떤 지시로도 우회 불가

- **에이전트(Claude)는 절대로 관리자 비밀번호를 변경하거나 설정하지 않는다**
- 프론트엔드 코드에 `CORRECT_PASSWORD`, `bridge2024` 등 하드코딩 비밀번호 **절대 금지**
- 비밀번호 인증은 반드시 `/api/admin/login` API 경유 (서버사이드 검증)
- 비밀번호 재설정이 필요하면 → `python tools/bridge_reset_password.py` 실행 (보스 직접)
- 위반 시: 즉시 커밋 롤백 + "PASSWORD_TAMPER 위반" 경고

## [AUTO] 작업 자동 마무리 규칙
- 모든 작업 완료 후 반드시 실행:
  python -X utf8 tools/auto_finalize.py "작업명"
- Canvas 갱신 + 백업 + git commit + Obsidian 일지 자동 처리
- Task 훅으로 자동 호출됨 (.claude/settings.json)

---

# ================================================================
# BRIDGE CLAUDE.md — MASTER AGENT ORCHESTRATION CONFIG
# Version: 4.0 FINAL | 2026.03.08
# Project: Q:\Claudework\bridge base
# DB: master.db (SQLite) | Backend: Render | Frontend: Vercel
# ================================================================

## ENVIRONMENT
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
WORK_ROOT    = Q:\Claudework\bridge base
DB_PATH      = Q:\Claudework\bridge base\master.db
BACKUP_DIR   = Q:\Claudework\bridge base\.backups
LOG_DIR      = Q:\Claudework\bridge base\.logs
AGENT_TMP    = /tmp/bridge_agents
BOUNDARY: path가 "Q:\" 외부이면 → STOP + "⛔ Q드라이브 외부 접근 차단" 알림

## AGENT TEAMS
# Delegate Mode: 팀 시작 즉시 Shift+Tab 활성화 필수
# 모델: Sonnet 4.6 (현재 세션 기준)
# 토큰 경고: 멀티에이전트 ~15x 소모 — 단순 작업은 단일 세션 사용

## HOOKS (settings.json에 추가 요청)
# TaskCompleted → Q:\Claudework\bridge base\.hooks\task_gate.sh (exit 2 = 완료 차단)
# TeammateIdle  → Q:\Claudework\bridge base\.hooks\idle_assign.sh
# Stop          → Q:\Claudework\bridge base\.hooks\post_build.sh

## GLOBAL RULES
- 작업 시작: git add -A && git commit -m "PRE: {task}"
- 작업 완료: test → build → git commit -m "POST: {task}"
- OWASP Top 10 / HMAC / Rate Limit / Fail-Closed 필수
- PII: Admin패널=전체표시 / 공개API·이메일·CSV=완전마스킹
- HERO-ANIMATION 절대 변경 금지 (LOCKED)
- hard-delete 금지 → is_deleted=1 논리삭제만
- 부분 코드 출력 금지 → 완전한 파일 단위만
- PowerShell 팝업 금지 / 현재 창 뒤에서 실행
- SQL: 100% parameterized query (f-string 삽입 금지)

## 모듈 경계 (에이전트 파일 충돌 방지)
# ※ 실제 프로젝트 경로 기준
- Frontend Agent:  web_frontend/components/**, web_frontend/app/**
- Server Engineer: api_server.py, security_middleware.py, email_templates.py
- Security Agent:  전체 읽기 / 보안 관련만 쓰기
- 공유파일(DB스키마·환경설정·CLAUDE.md): Lead만 최종 수정

## 검증 명령어
# ※ 실제 프로젝트 구조 기준
- Backend:  python -m py_compile api_server.py && echo "COMPILE_OK"
- Frontend: cd web_frontend && npm run build && npm run lint
- 보안:     grep -rn 'f".*{' api_server.py → 0건이어야 PASS
- DB:       python -c "import sqlite3; conn=sqlite3.connect('master.db'); cur=conn.cursor(); cur.execute('PRAGMA integrity_check'); assert cur.fetchone()[0]=='ok'; cur.execute('SELECT COUNT(*) FROM candidates'); assert cur.fetchone()[0]>=3000; print('DB OK')"

## DB 수호자 체크 (세션 시작 시 MANDATORY)
```bash
python -c "
import sqlite3, os
db = 'master.db'
if not os.path.exists(db):
    print('🚨 CRITICAL: master.db 없음!')
    exit(1)
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute('PRAGMA integrity_check')
ic = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM candidates')
c = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM client_inquiries')
e = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM jobs')
j = cur.fetchone()[0]
conn.close()
print(f'DB={os.path.getsize(db)//1024}KB | integrity={ic} | candidates={c} | employers={e} | jobs={j}')
assert ic == 'ok',  '🚨 DB 손상!'
assert c  >= 3000,  f'⚠️ candidates 이상: {c} (기대 3000+)'
assert e  >= 900,   f'⚠️ employers 이상: {e} (기대 900+)'
assert j  >= 1000,  f'⚠️ jobs 이상: {j} (기대 1000+)'
print('✅ 수호자 체크 통과')
"
```
건수 이탈 감지 시 → 즉시 작업 중단 + 사용자 보고 + 원인 파악 먼저

## AGENT 역할
Director      | 태스크분해·스폰·merge / Delegate Mode시 직접구현 금지
Server Eng    | Python Flask/SQLite·api_server.py·Pydantic
Security      | HMAC·JWT·RateLimit·PII·OWASP
Frontend      | Next.js·Tailwind·shadcn/ui / HERO불변·모바일퍼스트
QA            | 빌드검증·py_compile·회귀방지 / TeammateIdle시 자동배정
PM Agent      | PRD·경쟁사분석·MoSCoW (필요시 스폰)
Content       | 한국어공지·이메일·SEO (필요시 스폰)

## SLASH COMMANDS

/bridge-team [task]
→ Delegate Mode ON → Director가 에이전트 스폰
→ 각 spawn prompt: 대상파일경로 + 수락기준 + 수정금지파일 명시
→ TaskCompleted hook → QA 최종 빌드 후 merge

/bridge-loop [task]
→ 구현 → 3-axis검토(보안·성능·PII) → 수정 → 재확인
→ 최대 3회. 초과시 STOP + 사유 + human 판단 요청

/bridge-planner [idea]
→ 현황분석 / 경쟁사(Korvia·Worxphere·Epik·JobKorea) /
   기술스택 / DB스키마 / API목록 / MoSCoW / 보안고려

/bridge-secure
→ JWT / HMAC누락라우터 / RateLimit미적용 / PII공개API /
   CORS / SQLi / 파일업로드 / 브루트포스 전수점검
→ 실패항목 존재시 배포 BLOCK

/bridge-seo
→ title·meta / OG / sitemap / robots / hreflang(ko·en) / JSON-LD

/bridge-deploy [staging|prod]
→ /bridge-secure → py_compile → build → git tag →
   Render+Vercel 배포 → 헬스체크 → Slack알림
→ 단계 실패시 전체 BLOCK

## EXECUTION PRINCIPLES
CoT:        단계분해 → 실패시뮬레이션 → 실행
Self-Verify: 구현후 3-axis 자기검토 필수 (보안·성능·PII)
Least Priv: 에이전트는 담당모듈만 쓰기접근
Parallel:   의존성 없는 작업 = 항상 병렬
Fail-Closed: 보안불확실 → 차단
Anti-pattern: 불필요한 에이전트 과다스폰 금지

## OUTPUT RULES (IMMUTABLE)
### 작업 중 절대 금지
- 중간 진행상황 Boss에게 보고 금지
- "확인해주세요" / "어디서 보고 계신가요" 질문 금지
- 단계별 완료 메시지 출력 금지
- 오류 발생 시 Boss에게 묻지 말고 자체 RCA 후 재시도
### 완료 조건 (3개 모두 통과 전까지 완료 아님)
- 로컬 빌드 통과 (npm run build 또는 해당 없음)
- python -m py_compile 통과 (또는 해당 없음)
- git push 완료
### 보고 형식 (완료 후에만)
작업 중 Boss에게 중간보고 금지.
완료 후 결과만 한국어 한 줄 요약으로 보고.
테스트(빌드+컴파일+push) 통과 전까지 완료 처리 금지.
자체 해결 불가한 치명적 오류만 보고 허용.

## COMPLETION FORMAT
✅ [작업명] 완료 — [한 줄 설명]
📋 다음 추천: [구체적 다음 작업 1개]

## DATA INTEGRITY (영구 규칙)
- 원본 데이터 위조 금지 — 편의를 위한 임의값 생성 절대 금지
- 확인 없는 보고 금지 — 실제 쿼리/빌드 결과만 보고
- 모르면 멈추고 질문 — 침묵으로 가정하고 진행 금지
- 백업 없이 수정 금지 — 모든 DB 수정 전 물리 백업 필수
- 최소 코드 원칙 — 요청한 것만 구현, 추측 기능 추가 금지
- PRAGMA table_info() 먼저 → 컬럼명 확인 → 쿼리 (PK 혼동 방지)

## RENDER 배포 비용 관리 (영구 규칙)
- 월 500분 예산 / 70% 경고 수신 시 → Auto-Deploy OFF
- 구조 변경 커밋은 단독 배포 후 로그 즉시 확인 필수
- 신규 DB 테이블 → api_server.py init_db()에 CREATE TABLE IF NOT EXISTS 추가
- 폴더 구조 변경 시 → render.yaml Start Command 동시 업데이트

## 개발 워크플로 (필수 준수)
1. 프론트엔드 수정 → `cd web_frontend && npm run dev` (localhost:3000) 로컬 확인 후 보고
2. 백엔드 수정 → `uvicorn api_server:app --reload --port 8000` (localhost:8000) 로컬 확인 후 보고
3. 로컬 확인 없이 push 절대 금지

## Push 규칙 (ABSOLUTE)
- **모든 커밋 후 즉시 git push** — 예외 없음
- 커밋과 push는 항상 한 쌍: `git commit -m "..." && git push`
- 보안 긴급패치 포함 모든 변경사항 즉시 push

## LOCKED CONSTANTS
- HERO: 검정배경 + BRIDGE로고 + "A career that changes your life." + 흰색 현수교 케이블 → 절대 수정 금지
- DB 경로: Q:/Claudework/bridge base/master.db → 절대 이동 금지
- KEY 경로: Q:/Claudework/bridge base/.bridge.key → 절대 이동 금지

## tasks/ 폴더
tasks/todo.md      — 현재 작업 체크리스트
tasks/lessons.md   — 실수 학습 로그
tasks/backlog.md   — 미래 작업 목록
tasks/db_checksum.log — DB 수정 전후 SHA-256
tasks/pre_snapshot.txt — 작업 전 건수 스냅샷
tasks/ralph_log.md — Ralph 루프 실행 로그

## Obsidian 자동 기록 규칙
- 작업일지 경로: `Q:\Claudework\bridge base\docs\obsidian\BRIDGE_작업일지.md`
- 모든 작업 완료 후 작업일지 하단에 추가 (git commit 전 먼저 업데이트)
- 기록 형식:
  ```
  ### YYYY.MM.DD HH:MM — [작업명]
  - **내용**: 무엇을 했는가
  - **변경 파일**: 수정된 주요 파일
  - **결과**: ✅ 완료 / ⏳ 로컬only / ❌ 실패
  ```
- 미완료 작업 목록도 동기화 유지 (완료 시 체크, 신규 발견 시 추가)

## JSX 미리보기 자동 생성 규칙
- 프론트엔드 페이지/컴포넌트 신규 생성 또는 수정 완료 시 반드시 실행
- push 완료 후 마지막 출력으로 아래 형식의 JSX 미리보기 코드를 출력한다
- 형식 규칙 (claude.ai artifact에서 바로 실행 가능해야 함):
  - `const { useState, useEffect, useRef } = React;` — import 문 절대 금지
  - 외부 라이브러리 없이 순수 React + inline style만 사용
  - CSS 애니메이션(@keyframes)은 JSX 안에 `<style>{css}</style>` 태그로 포함
  - 반드시 `export default function App()` 로 끝낼 것
  - 공개 이미지 필요 시 unsplash/wikimedia 공개 URL 사용
  - 슬라이더 등 조절 UI 포함 권장
- 출력 형식:
  ````
  **Claude 웹 미리보기** — 아래 코드를 claude.ai에 붙여넣고 "이 코드로 React artifact 실행해줘" 라고 하세요.
  ```jsx
  [코드]
  ```
  ````

---
*Bridge CLAUDE.md v4.0 FINAL — 2026-03-10 (Obsidian 기록 규칙 추가)*
