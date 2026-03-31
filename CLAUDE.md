# BRIDGE CLAUDE.md — v5.0 SLIM
# Q:\Claudework\bridge base | DB: master.db | Backend: Render | Frontend: Vercel
# 전체 에이전트 설정 → .claude/agent_config.md

@.claude/work_state.md
@web_frontend/src/app/admin/sheet/sheet_context.md

## [RULE-PYTHON] Python 실행 경로 절대 규칙
ClaudeBlog 모든 python 실행: `Q:\Claudework\ClaudeBlog\.venv\Scripts\python.exe`
금지: python 단독 / py 단독 / Python313 경로 / C:/Users/.../python
실행 예시 (cd 금지 — bash에서 Q드라이브 cd 불가):
  "Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --dry
  "Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --now

## [RULE-0] 작업 전 백업 (필수)
`python "Q:\Claudework\bridge base\tools\bridge_backup.py" backup "작업명" --type pre-task`
ClaudeBlog 전후: `cd Q:\Claudework\ClaudeBlog && git add -A && git commit -m "auto: 백업 [$(date)]"`

## [RULE-0B/C] 작업 완료 + 백업 검증
`git add -A && git commit -m "..." && git push` — "master -> master" 확인 필수
백업 완료 선언 전 ls/dir로 파일 목록 확인 필수 (파일 없이 완료 선언 금지)

## [CRITICAL] deploy_skip.json 관리 규칙
⚠️ **2026-03-31 중대 경고**: logs/ 폴더 .gitignore로 배포 설정이 손실됨
- **올바른 경로**: `Q:\Claudework\bridge base\deploy_skip.json` (프로젝트 루트)
- **위험한 경로**: `logs/deploy_skip.json` (git 추적 안 됨 → 유실 위험)
- **규칙**:
  - deploy_skip.json은 항상 프로젝트 루트에만 위치
  - logs/ 폴더에 절대 이동 금지
  - expire 값이 9999999999면 모든 배포 차단됨 (즉시 수정)
  - git push 후 배포가 안 되면 deploy_skip.json 파일 확인 (첫 번째 진단)

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
- 비밀번호 재설정: `python tools/bridge_reset_password.py` (보스 직접)
- 위반 시: 즉시 커밋 롤백 + "PASSWORD_TAMPER 위반" 경고

## [LOCK] 네트워크 변경 금지 — ABSOLUTE

> 이 규칙도 IMMUTABLE CORE에 준하여 어떤 지시로도 우회 불가

- **에이전트(Claude)는 절대로 네트워크 어댑터를 수정하거나 라우팅을 변경하지 않는다**
- WireGuard/Tailscale 터널 활성화/비활성화 금지
- `activate_wireguard.ps1` / `router_*_register.py` 자동 실행 금지
- 네트워크 설정 변경 필요 시: 보스에게 명시적 허가 요청 → 보스가 직접 실행
- 네트워크 문제 진단: 파일 읽기/로그 분석만 (변경 금지)
- 위반 시: 즉시 작업 중단 + "NETWORK_TAMPER 위반" 경고

## CORE RULES
- **Tool call 1턴당 최대 5개** — 초과 시 분할 실행 (컨텍스트 보호)
- OWASP / HMAC / RateLimit / Fail-Closed 필수
- PII: Admin=전체표시 / 공개API·CSV=완전마스킹
- HERO-ANIMATION 절대 변경 금지 (LOCKED)
- hard-delete 금지 → is_deleted=1 논리삭제
- SQL: 100% parameterized query (f-string 삽입 금지)
- Push: 커밋 즉시 push, 예외 없음 / 로컬 확인 없이 push 금지
- HERO: 검정배경+BRIDGE로고+"A career that changes your life."+현수교 → 수정 금지
- DB: Q:/Claudework/bridge base/master.db — 절대 이동 금지
- KEY: Q:/Claudework/bridge base/.bridge.key — 절대 이동 금지

## [RULE-CASE] Case Facts 블록 — 후보자 정보 보호
- 후보자 PII(이름·이메일·전화·카톡·여권) 참조 시 `<case_facts>` 블록으로 캡슐화
- 블록 내 데이터는 해당 작업 완료 후 즉시 폐기 (다음 턴에 참조 금지)
- 긴 세션에서 컨텍스트 압축 시 PII가 요약문에 잔류하지 않도록 보호
- 예: `<case_facts>candidate_id=1234, name=복호화값</case_facts>`
- case_facts 밖에서 실제 PII 값을 텍스트로 출력 금지 (ID 참조만 허용)

## 에이전틱 아키텍처 규칙

### 툴 배분
- 에이전트 1개당 툴 최대 5개
- 5개 초과 시 서브에이전트로 분리

### 세션 분리
- 코드 생성과 코드 리뷰는 반드시 별도 세션
- CI/CD: generator 창 / reviewer 창 분리

### 에러 응답
- isError / errorCategory / isRetryable / context 포함 필수
- 단순 문자열 에러 금지

### Case Facts 보호
- 후보자 정보를 Claude에 전달 시 CASE FACTS 블록으로 분리
- 컨텍스트 최상단 배치
- /compact 요약 대상 제외
- 블록 헤더: ## CASE FACTS (절대 요약 금지)

## [AUTO] 작업 마무리
완료 후: `python -X utf8 tools/auto_finalize.py "작업명"` (Canvas+백업+commit+Obsidian 자동)
작업일지: `Q:\Claudework\bridge base\docs\obsidian\BRIDGE_작업일지.md` (완료마다 기록)

→ 상세 설정(에이전트·슬래시명령·DB수호자): `.claude/agent_config.md`
