# BRIDGE — Claude Code 지침

## 최우선 규칙: 자동백업
- 모든 작업 시작 전 반드시: `git add -A && git commit -m "pre-work backup: [작업명]"`
- 파일 수정 전 해당 파일 `.bak` 복사본 생성
- 대규모 수정 시 브랜치 생성 후 작업
- 작업 완료 후 반드시: `git add -A && git commit -m "[작업내용]" && git push`
- Q드라이브의 모든 파일은 항시 복구 가능해야 함
- 세션 종료/컨텍스트 클리어 전 반드시 커밋+푸시
- 자동백업 스크립트: `Q:/bridge-overnight/auto-backup.ps1`
- 복구 스크립트: `Q:/bridge-overnight/restore.ps1`

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

## 서버

- dev 서버는 별도 터미널에서 `--reload`로 상시 실행 중
- **서버 시작/종료/재시작 명령 실행 금지**
- `package.json`이나 `.env` 변경 시에만 "서버 재시작 필요"라고 안내
- 코드 수정 후 **반드시 `curl`로 검증** → 통과 후 유저에게 결과 보여주기

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
