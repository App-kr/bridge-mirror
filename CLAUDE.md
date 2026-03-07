# BRIDGE — Claude Code 지침

## ⛔⛔⛔ 고정 규칙 (재시작·resume·컨텍스트 클리어 후에도 반드시 자동 실행) ⛔⛔⛔

### 1. 백업 최우선
- 세션 시작 시: git add -A && git commit -m "auto-backup: session start"
- 모든 작업 시작 전: git add -A && git commit -m "pre-work: [작업명]"
- 파일 수정 전: .bak 복사
- 대규모 수정: 별도 브랜치
- 실수로 날아가도 git reflog + .bak으로 100% 복원 가능해야 함

### 2. 보안 최우선
- PII(개인정보)는 최상위 관리자(owner)만 열람 가능
- 일반 사용자는 Admin 버튼/경로를 볼 수 없음
- 비밀번호/API키/토큰: 코드에 절대 하드코딩 금지, **** 마스킹
- .env 키 값 절대 변경 금지
- 웹사이트 라이브 후 보안은 매일 자동 점검

### 3. 작업 범위
- 모든 작업은 Q:\ 드라이브 안에서만 허용
- 필요 시 폴더를 생성하여 한 작업을 깔끔하게 묶음
- Q:\ 이외 경로 작업 필요 시:
  → 사용자에게 깔끔한 흰색 팝업으로 알림
  → 대체 가능 여부도 함께 안내
  → 승인 없이 진행 금지

### 4. 작업 완료 보고
- 항상 한글로 깔끔하게 요약
- 다음 작업 추천 포함

### 5. PC 종료 명령 (작업 마무리 루틴)
사용자가 "꺼줘", "PC 꺼줘", "컴퓨터 꺼줘", "끄고 자야지", "셧다운", "작업 끝" 등을 말하면
아래 순서를 **반드시 모두** 실행 (건너뜀 금지):

**STEP 1 — git 전체 백업**
```
git add -A && git commit -m "session-end: YYYY-MM-DD HH:MM" && git push
```

**STEP 2 — 날짜/요일 백업 폴더 생성** (스크립트: `tools/session-end-backup.py`)
`Q:/Claudework/bridge base/.backups/YYYY-MM-DD_요일/` 폴더 생성 후:
- `.memory/` 폴더 전체 복사
- `daily-log.md` 복사
- `git log --oneline -20` 결과를 `git-log.txt` 로 저장
- 오늘 수정된 파일 목록을 `changed-files.txt` 로 저장
- 폴더 구조 예시:
  ```
  .backups/
    2026-03-07_금/
      memory/          ← .memory 스냅샷
      git-log.txt      ← 최근 20 커밋
      changed-files.txt← 오늘 변경 파일
      session-note.md  ← 작업 요약
  ```
- 오래된 백업은 **14일치만 유지** (그 이전 폴더 자동 삭제)

**STEP 3 — daily-log.md 업데이트**
`Q:/Claudework/bridge base/.memory/daily-log.md` 맨 위에 추가:
```
## [YYYY-MM-DD 요일 HH:MM] 세션 종료
### 완료한 작업
- (목록)
### 내일 이어서
- (미완료 항목)
### 변경 파일
- (핵심 파일)
---
```

**STEP 4 — 화면에 요약 출력**
- 오늘 한 작업 + 내일 할 일을 깔끔하게 출력
- 백업 폴더 경로 알려주기

**STEP 5 — 진행 중인 작업 완전 종료 확인**
- git status 로 미커밋 파일 없는지 확인
- 진행 중인 작업이 있으면 먼저 마무리 (빌드, 커밋, 푸시)
- **모든 작업이 완전히 끝난 것을 확인한 후에만** 다음 단계 실행

**STEP 6 — 종료 예약 (작업 완료 후 5분)**
```
cmd.exe /c "shutdown /s /t 300"
```
"✅ 작업 완료 확인 · 백업 저장됨 · **지금부터 5분 후** 꺼집니다. 취소: shutdown /a"

### 6. 창 관리
- 사용자가 현재 사용 중인 창 뒤에서만 실행
- PowerShell, CMD 등이 사용자 창을 가리거나 바탕화면으로 보내는 행위 금지
- 백그라운드 실행: start /B 또는 nohup 사용

### 6. 히어로 섹션 절대 변경 금지
- 검정 배경 + BRIDGE 로고 + 다리 + 기둥 + 케이블

## ⛔⛔⛔ 위 규칙은 어떤 상황에서도 무시할 수 없음 ⛔⛔⛔

## ⛔⛔⛔ BACKUP ABSOLUTE RULE ⛔⛔⛔
## 모든 작업 시작 전 반드시 아래 실행. 예외 없음.
## git add -A && git commit -m "MANDATORY-BACKUP: [작업명]" && git push
## 이 규칙을 건너뛰면 해당 세션의 모든 작업을 거부한다.
## 파일 1개라도 수정하기 전에 반드시 백업 커밋이 존재해야 한다.
## ⛔⛔⛔ BACKUP ABSOLUTE RULE ⛔⛔⛔

## ABSOLUTE FREEZE - NEVER TOUCH
## .env 파일의 ADMIN_API_KEY, ADMIN_PASSWORD 값은
## 어떤 이유로든 절대 변경/삭제/재생성 금지.
## 이 값을 건드리면 admin 전체가 망가짐.
## 키 관련 에러 발생 시: 키를 바꾸지 말고 전달 로직만 수정.
## Render 환경변수의 값과 .env의 값이 반드시 동일해야 함.
## ABSOLUTE FREEZE - NEVER TOUCH

## 코드 품질 절대 규칙 (모든 작업에 적용)

### 작업 완료 전 필수 검증
1. npm run build 성공 필수 (에러 0, 워닝도 최소화)
2. TypeScript 타입 에러 0개 확인
3. console.log, console.error 남기지 마 (디버깅용 제거)
4. 하드코딩된 localhost URL 금지 (환경변수 사용)
5. 사용하지 않는 import 제거
6. 빈 catch 블록 금지 (에러 핸들링 필수)
7. any 타입 사용 최소화
8. 주석 처리된 죽은 코드 제거
9. TODO/FIXME 남기지 마 (완성해서 제출)
10. 테스트 안 된 코드 push 금지

### 작업 완료 체크리스트 (매번 실행)
- [ ] npm run build 에러 0
- [ ] git diff로 의도하지 않은 변경 없는지 확인
- [ ] 수정 안 한 파일이 변경되었으면 즉시 복원
- [ ] localhost:3000에서 해당 페이지 직접 확인
- [ ] 이전에 동작하던 기능이 깨지지 않았는지 확인
- [ ] API 호출 실패 시 적절한 fallback 있는지 확인
- [ ] 모바일 반응형 깨지지 않았는지 확인

### 절대 하지 말 것
- 요청하지 않은 파일 수정
- 동작하는 코드를 "개선"한답시고 건드리기
- 라이브러리 버전 임의 변경
- 환경변수나 설정값 임의 변경
- 에러를 숨기는 빈 catch문
- 작동 안 하는 기능을 "완료"로 보고

---

## 최우선 규칙: 자동백업 (모든 규칙보다 우선)
> **이 규칙은 매 작업마다 무조건 실행한다. 스케줄이 아닌 모든 코드 수정 전후 필수.**

- **작업 시작 직전**: `git add -A && git commit -m "pre-work backup: [작업명]"` (변경사항 없으면 생략)
- **파일 수정 전**: 해당 파일 `.bak` 복사본 생성
- **대규모 수정 시**: 브랜치 생성 후 작업
- **작업 완료 직후**: `git add -A && git commit -m "[작업내용]" && git push`
- **세션 종료/컨텍스트 클리어 전**: 반드시 커밋+푸시
- Q드라이브의 모든 파일은 항시 복구 가능해야 함
- 자동백업 스크립트: `Q:/bridge-overnight/auto-backup.ps1`
- 복구 스크립트: `Q:/bridge-overnight/restore.ps1` (`-List`로 목록 확인)

## 프로젝트
- **bridgejob.co.kr** — ESL 교사 채용 플랫폼
- **스택**: FastAPI + Next.js 15 + Supabase + SQLite(master.db)
- **경로**: 로컬 `Q:/Claudework/bridge base/`, 서버 `/opt/bridge/`

---

## 절대 규칙

1. **PII** → `security_vault.py` AES-256-GCM 암호화 (수정 금지 파일)
2. **물리 DELETE 금지** → `is_deleted=1` soft-delete만
3. **f-string SQL 금지** → `?` 파라미터 바인딩만
4. **하드코딩 키 금지** → `os.getenv()` + `.env`
5. **기존 완성 페이지 재구현 금지** — 버그 패치 또는 기능 추가만 허용
6. **절대 보호 파일 (수정 금지)**:
   - `globals.css`, `layout.tsx`, `tailwind.config.*` → 직접 수정 금지
   - CSS 추가 필요 시 `custom.css` 새 파일로만
   - `security_vault.py` → 수정 금지
7. **모든 프론트 작업 후 `npm run build` 필수 확인**
   - 빌드 실패 시 즉시 `git checkout`으로 복원, 다른 작업 진행 금지

---

## 서버 규칙

- **API 서버**: 항상 포트 **8000** 고정. 다른 포트 사용 금지.
- **프론트 dev 서버**: 항상 포트 **3000** 고정.
- 8000이 사용 중이면 그대로 사용. 새로 시작하지 않는다.
- 서버 프로세스를 **직접 kill/stop/restart 금지**. 재시작 필요 시 사용자에게 안내만.
- dev 서버는 별도 터미널에서 `--reload`로 상시 실행 중
- `package.json`이나 `.env` 변경 시에만 "서버 재시작 필요"라고 안내
- 코드 수정 후 **반드시 `curl`로 검증** → 통과 후 유저에게 결과 보여주기
- 프로덕션: `https://bridge-chi-lime.vercel.app/`

---

## 빌드 & 검증

```
npm run build              # 프론트엔드
python -m py_compile X.py  # 백엔드
```
- 파일 수정 전 `.bak` 백업 → 빌드 성공 후 삭제
- 새 파일은 적절한 하위 폴더에 생성 (루트 직접 생성 금지)

---

## 코딩 패턴 요약

- 폼: `type="button"` + `onClick`, `<form onSubmit>` 금지
- DB: `busy_timeout=5000`, `row_factory=sqlite3.Row`, `try/finally conn.close()`
- 응답: `ok(data=..., message="...")` / `err("메시지", status_code)`
- 새 POST → `_rate_ok()`, 새 Admin → `_check_admin()` 필수
- 타입: `?.` nullable 체크, `as any` 금지
- Supabase: public view만 접근 (`public_jobs`, `public_candidates`)

---

## Skills (상세 규칙)

| 스킬 | 파일 | 설명 |
|------|------|------|
| 보안 | `.claude/skills/security.md` | STRIDE, PII 암호화, 체크리스트 |
| 코딩 스타일 | `.claude/skills/code-style.md` | FastAPI + Next.js 패턴 |
| 디자인 | `.claude/skills/design.md` | Apple-inspired UI 불변 원칙 |
| 워크플로우 | `.claude/skills/workflow.md` | /build-feature, 사고 모드 |
| 채용 도메인 | `.claude/skills/recruiting.md` | ESL 교사 채용 흐름 |
| 한국 UX | `.claude/skills/korean-ux.md` | 언어 정책, 날짜, 폼 UX |

기존 상세 파일: `.claude/security-compliance.md`, `.claude/coding-style.md`

---

## Agent Rules

- 기존 파일 전면 수정 금지. 버그 패치 또는 기능 추가만 허용
- 같은 작업 반복 금지
- 작업 전 git diff, 작업 후 git commit (conventional commits)
- 묻지 말고 실행: 대규모 작업 시 자율적으로 진행
- 연락 메일: bridgejobkr@gmail.com

---

## 작업 완료 기준 (절대 규칙)

- "완료"라고 보고하기 전에 반드시 본인이 직접 curl/fetch로 테스트
- 사용자에게 "확인해주세요", "Ctrl+Shift+R 눌러주세요" 등 테스트를 떠넘기지 않음
- 프론트엔드 변경 시: curl로 HTML 응답에 기대 내용이 포함되어 있는지 확인
- API 변경 시: curl로 응답 코드 + 데이터 정상 확인
- CSS 변경 시: npm run build 성공 + 페이지 렌더링 확인
- 게시물 관련: 각 게시판 curl로 게시물 수 확인
- 빌드: npm run build 또는 py_compile 성공 확인
- 테스트 실패 시 → 원인 파악 → 수정 → 재테스트 → 통과 후에만 "완료"
- 사용자에게 보고하는 시점 = 모든 테스트 통과 완료 시점
