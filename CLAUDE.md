# BRIDGE SYSTEM — Claude Code 운영 지침
# 이 파일은 모든 세션에서 자동 로드됩니다.
# 환경 무관 적용: Desktop, Mobile, Admin System, 원격 서버 모두 동일 규칙

## 프로젝트
- **서비스**: bridgejob.co.kr — ESL 교사 채용 플랫폼
- **스택**: FastAPI + Next.js 15 + Supabase + SQLite(master.db)
- **경로**: 로컬 `Q:/Claudework/bridge base/`, 서버 `/opt/bridge/`

---

## 절대 규칙 (세션/환경 초기화 후에도 유지)

### 보안 — 위반 시 서비스 중단급 사고
- 상세 규칙: `.claude/security-compliance.md` 참조
- **PII** → `security_vault.py` AES-256-GCM 암호화 필수 (수정 금지 파일)
- **물리 DELETE** 금지 → `is_deleted=1` soft-delete만
- **`NEXT_PUBLIC_`** 에 시크릿 값 절대 금지 (브라우저 번들 노출)
- **f-string SQL** 절대 금지 → `?` 파라미터 바인딩만
- **에러 응답** → 내부 예외 노출 금지, 제네릭 메시지 + 서버 로그
- **하드코딩 키** 금지 → 모든 시크릿은 `os.getenv()` + `.env`
- **console.log/print** 에 PII/시크릿 출력 금지
- **dangerouslySetInnerHTML** 동적 입력에 사용 금지

### 코딩 스타일 — 일관성 강제
- 상세 규칙: `.claude/coding-style.md` 참조
- 폼: `type="button"` + `onClick` 패턴, `<form onSubmit>` 금지
- DB 접근: `busy_timeout=5000`, `row_factory=sqlite3.Row`, `try/finally conn.close()`
- 응답: `ok(data=..., message="...")` / `err("메시지", status_code)` 통일
- 타입: `?.` nullable 체크, `as any` 금지, `@ts-ignore` 금지
- Supabase: public view만 접근 (`public_jobs`, `public_candidates`)
- 새 POST → `_rate_ok()`, 새 Admin → `_check_admin()` 필수

### 서버 규칙 — 절대 금지
- dev 서버는 별도 터미널에서 `--reload`로 상시 실행 중
- 코드 수정 시 자동 반영됨 (Hot Reload)
- **서버 시작/종료/재시작 명령 실행 금지** (`npm run dev`, `uvicorn`, `taskkill` 등)
- `package.json`이나 `.env` 변경 시에만 **"서버 재시작 필요"**라고 안내

### 화면 확인 규칙 — 유저에게 보여주기 전 필수
- 코드 수정 후 브라우저에 보여주기 전, **반드시 `curl` 등으로 서버 응답과 페이지 렌더링을 먼저 검증**
- 서버가 응답하지 않으면 유저에게 "서버가 꺼져 있습니다. 수동으로 시작해주세요"라고 안내
- 렌더링 에러(500, 빈 페이지 등) 발견 시 코드를 먼저 수정한 후 다시 확인
- **검증 통과 후에만** 브라우저를 열어 유저에게 결과를 보여줄 것

### 워크플로우 — 작업 전 반드시 확인
- **파일 수정 전 백업**: `.bak` 복사본 생성 → 빌드 성공 후 삭제
- **하위 폴더 정리**: 새 파일은 적절한 하위 폴더에 생성
- **묻지 말고 실행**: 대규모 작업 시 자율적으로 진행
- **빌드 검증**: 변경 후 반드시 `npm run build` + `py_compile` 실행

### 디자인 불변 원칙 (Apple-inspired)
- 홈, 히어로, 네비, 카운터, 잡보드 카드 레이아웃 변경 금지
- 유리질 블러 네비, Ken Burns 히어로, rounded-2xl/3xl 카드
- 검정 배경 + 흰 글씨 네비 CTA 버튼
- 라이트 테마 색상 팔레트: `#1d1d1f`, `#86868b`, `#0071e3`, `#f5f5f7`

---

## /build-feature 워크플로우

`/build-feature [기능명]` 입력 시 아래 순서로 자동 실행:

```
1. /plan     → 구현 전략 (영향 파일, DB 변경, 보안 검토)
2. /tdd      → 테스트 케이스 (성공/실패/Edge case)
3. /code     → 구현 (coding-style + security-compliance 준수)
4. /security → 보안 검토 (STRIDE, PII 경로, Rate limiting)
5. /verify   → 빌드 검증 (npm run build + py_compile, 오류 시 자동 수정)
```

---

## 사고 모드 (Adaptive Thinking)

| 작업 유형 | 접근 방식 |
|----------|---------|
| 아키텍처, DB 스키마, 보안 설계 | 심층 분석 — 영향 범위 전체 검토 후 실행 |
| 버그 수정, 리팩토링, 스타일 변경 | 빠른 실행 — 최소 변경, 즉시 적용 |
| 신규 기능 구현 | /build-feature 워크플로우 적용 |
| 간소화/정리 | /simplify — 중복 제거, 공통 패턴 추출, 빌드 검증 |

---

## 프로젝트 구조

```
루트/                         ← 핵심 런타임 파일만
├── api_server.py             FastAPI 백엔드
├── security_vault.py         AES-256-GCM (수정 금지)
├── email_templates.py        Gmail SMTP
├── auto_pipeline_v2.py       master.db → Supabase 동기화
├── master.db                 SQLite DB
├── .env                      시크릿 (공유 금지)
├── requirements.txt          Python deps
├── CLAUDE.md                 이 파일
│
├── web_frontend/             Next.js 15 프론트엔드
├── admin_app/                Desktop 관리자 앱
├── deploy/                   배포 설정 (nginx, systemd)
├── migrations/               DB 마이그레이션
├── uploads/                  파일 업로드 저장소
│
├── scripts/                  BAT/PS1 실행 스크립트
├── tools/                    자동화 에이전트, RPA
│   └── legacy/               레거시 마이그레이션 도구
├── docs/                     문서 (MASTER_PLAN, CREDENTIALS)
├── archive/                  이전 데이터, 디버그, 백업
├── backups/                  자동 백업 저장소
│
├── .claude/                  보안/코딩 규칙
└── .memory/                  학습 메모리 (인덱스+토픽)
```

### 폴더 정리 원칙
- **루트**: 런타임 필수 파일만 (api_server, security_vault, email, pipeline, db)
- **새 파일 생성 시**: 반드시 해당 폴더에 배치, 루트 직접 생성 금지
- **백업**: `backups/` 폴더에 날짜별 보관

---

## 환경별 차이 (모든 환경에 규칙 동일 적용)

| 항목 | Desktop (로컬) | Server (prod) | Mobile/Admin |
|------|---------------|---------------|-------------|
| DB 경로 | `./master.db` | `BRIDGE_DB_PATH` env | API 경유 |
| 업로드 | `./uploads/` | `/opt/bridge/uploads/` | API 경유 |
| Swagger | 활성 | `BRIDGE_ENV=production` 비활성 | N/A |
| Admin 접근 | localhost | nginx IP 제한 | VPN/API 키 |
| SMTP | 동일 | 동일 | 동일 |

## Agent Team Rules (auto-appended)
- 에이전트는 기존 완성된 게시판/접수폼/Contact를 절대 재구현하지 않는다
- 기존 파일 전면 수정 금지. 버그 패치 또는 기능 추가만 허용
- 같은 작업 반복 금지
- 작업 전 git diff, 작업 후 git commit (conventional commits)
- 연락 메일: bridgejobkr@gmail.com
