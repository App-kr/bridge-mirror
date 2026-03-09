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

## 배포 비용 규칙 (ABSOLUTE — 절대 준수)

### push 금지 조건
- 단순 텍스트/스타일 수정
- 기능 1개 추가
- 버그 1개 수정
- "일단 확인해보자" 성격의 모든 작업

### push 허용 조건 (배치 기준)
- 최소 5개 이상 작업 묶음
- 보스가 명시적으로 "배포해" 라고 할 때만
- 보안 긴급패치 (이것만 예외)

### 작업 방식
- 모든 수정 → 로컬에서 git commit (push 금지)
- 보스가 "오늘 작업 배포해" → 그때 한번에 push
- push 전 반드시 보고: "현재 X개 작업 묶음, 배포할까요?"
- 월 빌드분 70% 경고 수신 시 → Auto-Deploy 즉시 OFF

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

---
*Bridge CLAUDE.md v4.0 FINAL — 2026-03-08*
