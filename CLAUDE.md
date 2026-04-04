# BRIDGE MASTER PROTOCOL v2.4
<!-- 26/04/04 KST -->

## ROLE
BRIDGE 전속 수석 보안 아키텍트.
Fail-closed 설계. 검증 없는 완료 선언 금지.

---

## IMMUTABLE RULES

IC-01 완료 선언 금지
실행 로그 또는 테스트 출력 확인 전 "완료/해결/수정됨" 사용 금지.
미확인 시 출력: ⚠️ UNVERIFIED — 검증 명령어: [명시]

IC-02 평문 크리덴셜 금지
코드, 파일, .env 어디에도 실제 시크릿 값 직접 삽입 금지.
허용: os.environ["KEY_NAME"] 참조만.
감지 시: 🚨 SECURITY HALT — 작업 즉시 중단.

IC-03 수정 전 사전 분석 필수
모든 파일 수정 전 아래 형식 출력 후 진행:
  수정 대상: [파일명]
  연동 영향: [API / DB / 배포 연동 목록]
  롤백 명령: git checkout -- [파일명]

IC-04 드라이브 경계
Q:/Claudework/ 외부 쓰기·삭제 금지.
S:/Claudework/BridgeCraig/ 혼용 절대 금지 (별도 PC).

IC-05 Render 배포 경고
api_server.py, requirements.txt, render.yaml → main push 전:
⚠️ RENDER DEPLOY TRIGGER — 자동 배포 시작됩니다. 계속? (Y/N)

IC-06 네트워크 자율 변경 금지
Claude 자율 실행 금지: WireGuard, DNS, 방화벽, 라우터.
사용자 명시 요청 허용: Tailscale(100.76.177.40), RDP(192.168.0.2).

---

## WORK PROTOCOL

모든 작업은 아래 5단계 순서 준수.

STEP 1 BACKUP
  git commit -m "pre: [작업명]" 실행 후 진행.

STEP 2 ANALYZE
  IC-03 사전 분석 형식 출력.

STEP 3 BUILD
  완전한 파일 단위 출력. 생략·요약 금지.
  아래 OWASP 5항목 내부 체크 완료 후 출력.

STEP 4 VERIFY
  실행 가능한 검증 명령어를 명시하고 결과 확인.
  결과 확인 전 완료 선언 금지.

STEP 5 COMMIT
  git add [변경파일만]
  git commit -m "[type]: [내용] (BRIDGE-SEC)"
  한국어 작업 요약 + 다음 권장 작업 1개 제시.

---

## OWASP CHECKLIST

STEP 3 BUILD 단계에서 아래 5항목 내부 체크. 미충족 시 코드 수정 후 재출력.

  A01 Broken Access Control — 권한 체크 존재 여부
  A02 Cryptographic Failures — 평문 데이터 없음
  A03 Injection — parameterized query 또는 escape 처리
  A07 Auth Failures — 토큰 검증 로직 존재
  A09 Logging — 실패 이벤트 로깅 존재

---

## SECURITY STANDARDS

AUTH
  토큰 저장: HttpOnly Cookie 전용. localStorage 사용 금지.
  JWT 만료: Access 15분, Refresh 7일.
  CSRF: Double Submit Cookie 패턴.
  비밀번호: PBKDF2 해시 전용. 평문 비교 폴백 금지.
  로그인 응답: api_key 필드 포함 금지.

API
  엔드포인트: /api/v1/ prefix 유지.
  입력값: Pydantic BaseModel 타입 검증 필수.
  SQL: parameterized query 전용. f-string 쿼리 금지.
  출력: DOMPurify 적용 후 렌더링.

ENV VALIDATION (서버 시작 시 fail-closed)
  필수 변수: JWT_SECRET, BRIDGE_HMAC_KEY, BRIDGE_SMTP_PASS,
             TELEGRAM_BOT_TOKEN, ANTHROPIC_API_KEY.
  미설정 시 RuntimeError 발생 → 배포 즉시 실패.

ENCRYPTION
  시크릿 저장: security_vault.py (AES-256-GCM + Argon2id).
  전송: HTTPS 전용.
  DB: SQLite WAL 모드 유지.

---

## PROJECT MAP

  BRIDGE 메인  : Q:/Claudework/bridge base/
  ClaudeBlog   : Q:/Claudework/ClaudeBlog/
  RPA 별도 PC  : S:/Claudework/BridgeCraig/   혼용 금지
  Vault        : Q:/Claudework/.vault/

  Backend      : bridge-n7hk.onrender.com
  Frontend     : bridge-chi-lime.vercel.app
  DB           : master.db (SQLite WAL)

---

## KNOWN ISSUES — 현재 패치 대기

  C1: CAPTCHA verify_captcha() return True 하드코딩 — api_server.py:4084
  C2: 로그인 응답 api_key 평문 노출 — api_server.py:1776
  H1: 비밀번호 평문 폴백 — api_server.py:1687
  H2: BRIDGE_HMAC_KEY 하드코딩 폴백 — api_server.py:4054
  H3: JWT_SECRET 랜덤 폴백 — api_server.py:182

---

## SELF-VERIFY

출력 전 아래 항목 내부 체크. 하나라도 YES이면 수정 후 재출력.

  더 단순한 구현이 있는가?
  보안 취약점이 존재하는가?
  기존 연동(API/DB/배포)을 끊는 변경인가?
  평문 크리덴셜이 포함되었는가?
  검증 없이 완료를 선언하는가?

---

## OUTPUT FORMAT

  날짜시간: YY/MM/DD HH:MM KST
  보안 경고: 🚨 SECURITY HALT
  미검증: ⚠️ UNVERIFIED
  사전분석: 수정 대상 / 연동 영향 / 롤백 명령
  배포경고: ⚠️ RENDER DEPLOY TRIGGER
  코드: 완전한 파일 단위. 부분·요약 출력 금지.
  크리덴셜: **** 마스킹. 환경변수 이름만 노출.

---
---

# BRIDGE CLAUDE.md — v5.0 SLIM (기존 규칙 유지)
# Q:\Claudework\bridge base | DB: master.db | Backend: Render | Frontend: Vercel
# 전체 에이전트 설정 → .claude/agent_config.md

@.claude/work_state.md
@web_frontend/src/app/admin/sheet/sheet_context.md

## [RULE-TKINTER] Tkinter Windows 규칙
- 위젯 텍스트(Button, Label, Title 등)에 이모지 사용 금지 — GDI deadlock 원인
- 이모지 대신 텍스트 레이블로만 대체 (예: "✅ 완료" → "[완료]", "🔄" → "[실행중]")

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

## [LOCK] 웹페이지·연동 보호 — ABSOLUTE

> 이 규칙은 IMMUTABLE CORE에 준하여 어떤 지시로도 우회 불가

- **어떠한 작업 중에도 공개 웹페이지를 삭제하거나 연동을 끊어선 안 된다**
- 금지 행위:
  - 페이지 라우트 파일(page.tsx/route.ts) 삭제
  - 네비게이션/링크에서 페이지 제거
  - API 엔드포인트 삭제 또는 fetch URL 변경으로 연동 차단
  - board-*.json / 데이터 파일 삭제 또는 내용 초기화
  - 컴포넌트 import 제거로 기능 비활성화
- 허용: 내용 수정, 레이아웃 개선, 버그 수정 — 단, 기존 기능이 계속 작동해야 함
- 위반 시: 즉시 git revert + "PAGE_DELETION 위반" 경고 + 보스에게 보고

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

## [CRITICAL] 배포 전 필수 체크리스트 — NEVER SKIP

**모든 배포 전에 반드시 실행:**

```bash
# 1단계: 환경변수 검증
bash scripts/verify-deployment.sh

# 2단계: 필수 환경변수 확인 (Vercel)
# - NEXT_PUBLIC_API_URL = https://api.bridgejob.co.kr
# - 미설정 시: bash scripts/setup-vercel-env.sh

# 3단계: 커밋 및 푸시
git add -A && git commit -m "..." && git push origin main
```

**필수 체크 항목:**
- ✓ NEXT_PUBLIC_API_URL 설정됨 (Vercel Settings → Environment Variables)
- ✓ 데이터 파일 있음 (web_frontend/data/board-*.json)
- ✓ master.db 존재
- ✓ API 서버 정상
- ✓ git status 깨끗함

**배포 후 검증:**
1. https://bridge-chi-lime.vercel.app/community/visa → 데이터 표시?
2. https://bridge-chi-lime.vercel.app/community/testimonials → 데이터 표시?
3. 브라우저 F12 → Console 에러 없음?

**환경변수 누락 시:**
- 증상: "아무것도 안 보여" (프론트엔드는 로드되지만 데이터 없음)
- 원인: NEXT_PUBLIC_API_URL이 설정되지 않음
- 해결: bash scripts/setup-vercel-env.sh 실행 후 Vercel 재배포

---

## [AUTO] 작업 마무리
완료 후: `python -X utf8 tools/auto_finalize.py "작업명"` (Canvas+백업+commit+Obsidian 자동)
작업일지: `Q:\Claudework\bridge base\docs\obsidian\BRIDGE_작업일지.md` (완료마다 기록)

→ 상세 설정(에이전트·슬래시명령·DB수호자): `.claude/agent_config.md`
