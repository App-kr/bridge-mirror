# BRIDGE Project — Memory Index
> 인덱스 전용. 상세 내용은 각 토픽 파일 참조.
> 절대 규칙 → `CLAUDE.md` | 학습 내용 → 아래 파일들
> 환경 무관 적용: Desktop, Mobile, Admin System 모두 동일

## Quick Reference
- **서비스**: bridgejob.co.kr (ESL 교사 채용)
- **스택**: FastAPI + Next.js 15 + Supabase + SQLite
- **빌드**: 35 routes, 0 errors (2026-03-07)
- **최근 세션**: [worklog-2026-03-07.md](worklog-2026-03-07.md)

---

## Topic Files

| 파일 | 내용 | 최종 업데이트 |
|------|------|-------------|
| [architecture.md](architecture.md) | 시스템 구조, 데이터 흐름, 파일 맵 | 2026-02-28 |
| [api-endpoints.md](api-endpoints.md) | API 엔드포인트, Rate limit, 인증 레벨 | 2026-02-28 |
| [debugging-patterns.md](debugging-patterns.md) | 디버깅 패턴, 흔한 오류, 해결법 | 2026-02-28 |
| [admin-system.md](admin-system.md) | 관리자 페이지, Desktop 앱, 인터뷰 | 2026-02-28 |
| [design-system.md](design-system.md) | UI 디자인 규칙, CSS 클래스, 레이아웃 | 2026-02-28 |
| [deployment.md](deployment.md) | 배포 설정, nginx, systemd, 환경변수 | 2026-02-28 |
| [worklog-2026-03-07.md](worklog-2026-03-07.md) | 24시간 작업 기록 — 보안·MailComposer·드래그UX 등 | 2026-03-07 |

---

## 자동 실행 규칙 (사용자 누락 시에도 반드시 실행)

### 세션 시작 시 — 무조건 자동 실행
```bash
# 1. 이전 실수 복습
cat tasks/lessons.md | tail -20

# 2. 미완료 작업 확인
cat tasks/todo.md | grep "^\- \[ \]"

# 3. 최근 커밋 + 변경 파일 확인 (중복 구현 방지)
git log --name-only -3

# 4. DB 건수 수호자
python -c "import sqlite3; conn=sqlite3.connect('master.db'); cur=conn.cursor(); [print(t, cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]) for t in ['candidates','client_inquiries','jobs']]; conn.close()"
```
→ 이 루틴 없이 코드 수정 시작 금지. 사용자가 요청하지 않아도 자동 실행.

### 작업 전 — 중복 구현 방지 체크
```bash
git log --name-only -5 | grep -E "\.tsx|\.py|\.ts"
```
→ 이미 커밋된 파일이 있으면 내용 확인 후 차이점만 추가. 재작성 금지.

### 빌드 시 — 항상 클린 빌드
```bash
rm -rf web_frontend/.next && cd web_frontend && npm run build
```
→ `.next` 캐시 충돌 방지. `npm run build` 단독 실행 금지.

---

## User Preferences
- 파일 수정 전 반드시 백업
- 하위 폴더 정리 원칙
- 묻지 말고 자율 실행 선호
- **완료 보고 필수 형식** (2026-03-08 확정 — 모든 작업 완료 시 의무):
  1. 날짜·시간·제목
  2. 변경 파일별: 변경 내용 + 기능 한글 설명 1줄
  3. 검증 수치 (실측값만)
  4. 추천 다음 작업 3가지 (웹 레퍼런스 확인 후 실현 가능한 것만)
  → CLAUDE.md 섹션 6 참조
- `.next` 캐시 충돌 → `rm -rf .next` 후 재시작
- `.env.local`: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
- 모든 메모리/설정 파일은 프로젝트 내부(`Q:\Claudework\bridge base`)에만 보관
- **서버 규칙**: dev 서버는 별도 터미널에서 --reload로 상시 실행 중. 코드 수정 시 Hot Reload 자동 반영. 서버 시작/종료/재시작 명령 실행 금지. package.json이나 .env 변경 시에만 "재시작 필요" 안내.
- **화면 확인 규칙**: 브라우저를 열어 보여주기 전 반드시 curl로 서버 응답/렌더링 검증. 검증 통과 후에만 브라우저 열기.
- **포커스 스틸 금지**: 게임 중 바탕화면 튕김 방지. GUI 앱(브라우저/탐색기/메모장) 실행 금지, `start` 명령 금지, 모든 작업은 현재 bash 셸 내에서만. 서버는 `run_in_background`로만 시작.
- **백그라운드 실행 규칙**: 자동실행/타이머/스케줄러 → `-WindowStyle Hidden` 필수. 타스크 스케줄러 → `wscript + silent_run.vbs` 래퍼. Python 백그라운드 → `pythonw.exe` 또는 `Start-Process -WindowStyle Hidden`. 로그 → `logs/` 디렉토리 파일 출력 (콘솔 금지).

## Team Names (영국식 영문 이름)
- **Scarlett** — 대표 (User)
- **Violet** — 운영부장
- 이름 규칙: 영국식 영어 이름으로 통일
- **MARK 사용 금지**
