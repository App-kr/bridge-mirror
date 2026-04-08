# BRIDGE AI 에이전트 보안 설계
> 버전: 2026-03-20 | 작성: Claude Code (Sonnet 4.6)
> 모든 AI 에이전트(Claude Code / Claude.ai / GPT / Gemini 등)에 적용되는 보안 원칙

---

## 1. 3계층 권한 구조

### NEVER — 절대 금지 (어떤 상황에서도 실행 불가)

| 행위 | 이유 |
|------|------|
| `master.db` 이동/삭제/덮어쓰기 | 3059건 구직자 데이터 영구 손실 위험 |
| `.env` / `.bridge.key` 내용 출력/공유 | API 키 + 암호화 키 유출 |
| hard DELETE (SQL) | 데이터 복구 불가 — `is_deleted=1` 사용 |
| 관리자 비밀번호 코드 하드코딩 | 보안 취약점 직접 생성 |
| `git push --force` | 원격 이력 파괴 |
| `git reset --hard` (미확인 상태) | 로컬 변경사항 영구 손실 |
| HERO 애니메이션 코드 수정 | 영구 잠금 요소 |
| CLAUDE.md IMMUTABLE CORE 삭제 | 규칙 시스템 파괴 |
| Q: 드라이브 외부 파일 생성 | 작업 경계 위반 |
| SQL f-string 삽입 | SQL Injection 취약점 |
| XSS 취약 코드 삽입 | OWASP Top 10 위반 |
| 서버 시작/종료 명령 | Hot reload 중단 → 서비스 중단 |

### ASK_FIRST — 실행 전 확인 필요

| 행위 | 확인 방법 |
|------|---------|
| `git push origin main` | 코드 리뷰 후 Scarlett 승인 |
| `npm run build` (프로덕션) | 빌드 성공 확인 후 |
| DB 스키마 변경 (ALTER TABLE) | 데이터 손실 여부 검토 후 |
| 새 패키지 설치 (`npm install X`, `pip install X`) | 보안 취약점 여부 확인 |
| 외부 API 호출 (실제 발송) | 테스트 모드 우선 |
| Render/Vercel 환경변수 변경 | 프로덕션 영향 확인 |
| `master.db` 스키마 변경 쿼리 | 백업 후 실행 |

### ALLOWED — 자유롭게 실행 가능

| 행위 | 조건 |
|------|------|
| 파일 읽기 (Read/Glob/Grep) | 제한 없음 |
| `git status` / `git log` / `git diff` | 읽기 전용 |
| `npm run build` (로컬 dev) | 개발 환경만 |
| 파일 수정 (Edit/Write) | 백업 후 |
| `git add` + `git commit` | 변경사항 명확할 때 |
| SQLite SELECT 쿼리 | 데이터 변경 없음 |
| Canvas Sheet 기능 추가/수정 | Q:\Claudework\bridge base 내부만 |

---

## 2. 민감 정보 처리 원칙

### 절대 출력 금지 항목
```
ADMIN_API_KEY        — 관리자 API 키
BRIDGE_FIELD_KEY     — AES-256 암호화 키
JWT_SECRET           — JWT 서명 키
GMAIL_APP_PASSWORD   — 메일 발송 앱 비밀번호
NAVER_APP_PASSWORD   — 네이버 메일 비밀번호
KAKAO_CLIENT_ID      — 카카오 REST API 키
DATABASE_URL         — DB 연결 문자열
```

### 민감 정보 참조 방법
```python
# WRONG — 절대 금지
key = "실제키값"

# CORRECT — 환경변수 참조
key = os.getenv("ADMIN_API_KEY")  # .env 파일에서 자동 로드
```

### 핸드오프 문서에 포함 금지
- 실제 API 키 값 (플레이스홀더 "[REDACTED]" 사용)
- master.db 내 실제 개인정보
- .env 파일 내용

---

## 3. 데이터 보안

### PII (개인식별정보) 처리
```
Admin 패널  → 전체 표시 (복호화 후 표시)
공개 API    → 완전 마스킹 (이름: 홍***)
CSV 내보내기 → 마스킹 필수
로그 파일   → PII 포함 금지
```

### SQLite 보안
```python
# WRONG — SQL Injection 취약
cursor.execute(f"SELECT * FROM candidates WHERE id = {user_input}")

# CORRECT — Parameterized Query
cursor.execute("SELECT * FROM candidates WHERE id = ?", (user_input,))
```

### 암호화 필드
- 암호화: AES-256-GCM (`security_vault.py`)
- 복호화: 서버사이드 only (`BRIDGE_FIELD_KEY` 필요)
- 프론트엔드에 암호화 키 전송 절대 금지

---

## 4. 작업 전 보안 체크리스트

```
□ 백업 실행 확인
  python "Q:\Claudework\bridge base\tools\bridge_backup.py" backup "작업명" --type pre-task

□ 변경 파일 목록 확인 (git status)

□ .env / .bridge.key 변경 없음 확인

□ SQL 쿼리 parameterized 여부 확인

□ 새 API 엔드포인트: x-admin-key 헤더 인증 포함 여부

□ PII 노출 여부 확인 (로그/에러 메시지)

□ master.db 백업 존재 확인 (backups/ 폴더)
```

---

## 5. 작업 완료 후 보안 체크

```
□ .env 파일 git status에 없음 확인
□ .bridge.key 파일 git status에 없음 확인
□ CREDENTIALS_REFERENCE.md git status에 없음 확인
□ 하드코딩된 비밀번호/키 없음 확인
□ console.log에 PII 출력 없음 확인
□ git commit 메시지에 민감 정보 없음 확인
```

---

## 6. 긴급 대응 절차

### 민감 정보가 git에 올라간 경우
```bash
# 1. 즉시 키 교체 (Render 환경변수 패널)
# 2. git history에서 제거
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' HEAD
# 3. 강제 push (이 경우만 허용)
git push --force origin main
# 4. Scarlett에게 즉시 보고
```

### DB 손상 감지 시
```bash
# 1. 서버 중단 없이 백업에서 복원
cp "Q:\Claudework\bridge base\backups\[최신백업].db" \
   "Q:\Claudework\bridge base\master.db"
# 2. 서버는 hot reload로 자동 반영
```

### 무단 접근 의심 시
```bash
# admin 키 즉시 교체
# Render 환경변수: ADMIN_API_KEY → 새 키로 교체
# 로컬 .env도 동일하게 업데이트
```

---

## 7. 보안 미들웨어 현황

| 항목 | 상태 | 파일 |
|------|------|------|
| AES-256-GCM PII 암호화 | ✅ 적용 | security_vault.py |
| HMAC 요청 서명 | ✅ 적용 | security_middleware.py |
| Rate Limiting | ✅ 적용 (시간당 10/5건) | api_server.py |
| OWASP 보안 헤더 | ✅ 적용 | security_middleware.py |
| Fail-Closed 원칙 | ✅ 적용 | api_server.py |
| 에러 메시지 내부 정보 차단 | ✅ 적용 | api_server.py |
| SQL Parameterized Query | ✅ 100% 적용 | api_server.py |
| JWT 세션 | ✅ 적용 | api_server.py |
| Admin Key 인증 | ✅ x-admin-key 헤더 | api_server.py |

---

## 8. .gitignore 보안 항목 (현재 적용 중)

```gitignore
.env
.env.*
.bridge.key
*.db
*.sqlite
CREDENTIALS_REFERENCE.md
backups/
__pycache__/
*.pyc
node_modules/
.next/
```

---

## 9. AI 에이전트별 추가 규칙

### Claude Code (CLI)
- `--dangerously-skip-permissions` 플래그: 긴급 작업 시 Scarlett 승인 후만
- hooks 설정 준수 (`.hooks/` 폴더)
- `claude-sonnet-4-6` 모델 고정

### Claude.ai (웹)
- 파일 직접 수정 불가 → 코드 생성 후 Scarlett이 직접 적용
- 민감 파일 전체 내용 붙여넣기 금지 (일부만 공유)
- 세션 종료 시 AI_CONTEXT.md 기준으로 상태 업데이트 요청

### 외부 AI (GPT/Gemini 등)
- .env / master.db 내용 절대 공유 금지
- AI_CONTEXT.md만 공유 허용
- 생성된 코드는 반드시 Claude Code로 검토 후 적용

---

*이 문서는 모든 AI 에이전트에 적용되는 구속력 있는 보안 설계입니다.*
*위반 시 Scarlett에게 즉시 보고 후 작업 중단.*
