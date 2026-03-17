# BRIDGE Project — Memory Index
> 인덱스 전용. 상세 내용은 각 토픽 파일 참조.
> 절대 규칙 → `CLAUDE.md` | 학습 내용 → 아래 파일들
> 환경 무관 적용: Desktop, Mobile, Admin System 모두 동일

## Quick Reference
- **서비스**: bridgejob.co.kr (ESL 교사 채용)
- **스택**: FastAPI + Next.js 15 + Supabase + SQLite
- **빌드**: 36 routes, 0 errors (2026-03-08)
- **DB**: candidates=3059 | client_inquiries=1227 | jobs=1072 | 5.2MB
- **최근 세션**: [WORK_LOG_20260308.md](../WORK_LOG_20260308.md)

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
| [worklog-2026-03-13-bridgejob-old.md](worklog-2026-03-13-bridgejob-old.md) | 구 홈페이지(bridgejob.co.kr) 작업 — 그누보드5+카페24 | 2026-03-13 |

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

## Render 배포 비용 (영구 규칙 — 2026-03-08 확정)
- 월 500분 한도 / 70% 경고 → 즉시 Auto-Deploy OFF
- 커밋 전 필수: api_server.py 루트 위치 + requirements.txt 존재 확인
- 신규 테이블 → init_db()에 CREATE TABLE IF NOT EXISTS 추가
- 구조 변경 커밋 → render.yaml / Start Command 동시 업데이트
- Free tier: 15분 무트래픽 sleep, SQLite ephemeral(master.db 로컬 전용)
→ 상세: CLAUDE.md 섹션 10

## HERO 3D 지구 확정 설정 (2026-03-14 영구 기억)
- **컴포넌트**: `web_frontend/src/components/EarthGlobe.tsx`
- **텍스처**: `/earth-map.jpg` (NASA Blue Marble, 로컬 public)
- **구체**: `R=7`, `yOffset=-6.9`, `scale.x=1.28` (X축만 넓게)
- **카메라**: `position(0,0,6)`, `fov=42`
- **기울기**: `tiltGroup.rotation.x=-0.45` (적도 정면) — Group으로 분리
- **자전**: `earth.rotation.y += 0.0014` (tiltGroup 내부만 회전)
- **초기방향**: `rotation.y=1.8` (아프리카·유럽·아시아)
- **투명도**: `opacity=0.32`
- **좌우 페이드**: `maskImage` 20%~80% (canvas div에 직접)
- **조명**: AmbientLight 0.72 + DirectionalLight(4,1,6) 1.2
- **핵심**: tiltGroup(기울기+위치) / earth(자전만) 분리 필수 — 섞으면 축 틀어짐

## Team Names (영국식 영문 이름)
- **Scarlett** — 대표 (User)
- **Violet** — 운영부장
- 이름 규칙: 영국식 영어 이름으로 통일
- **MARK 사용 금지**

## 보안 레이어 현황 (2026-03-16 확정)
| 레이어 | 파일 | 상태 |
|---|---|---|
| 1 | `.hooks/guard.py` | ✅ 크리덴셜 차단 패턴 추가 완료 |
| 2 | `.hooks/task_gate.py` | ✅ DB integrity + PII 검증 |
| 3 | `.hooks/post_stop.py` | ⚠️ git 명령 정상, bash→powershell 교체 다음 세션 |
| 4 | `.env` 분리 | ✅ |
| 5 | AES-256-GCM | ✅ security_vault.py |
| 6 | Trail of Bits | ❌ 미설치 |

## 플러그인 관련 중요 사항
- `/plugin marketplace add` — Claude Code에 **존재하지 않는 명령어**
- Trail of Bits, superpowers, context7 → **MCP 서버 방식**으로 설치해야 함
- `/simplify` — 내장 명령어 아님, 수동 코드 분석으로 대체
- context7 MCP: `npx @upstash/context7-mcp` 방식으로 설치

## api_server.py 코드 이슈 (2026-03-16 분석)
- L446/470: `target_age` 중복 필드 (CandidateApply) — L446 사문화
- L34+2708: `import hashlib` 중복
- L1969~1972, 3948, 6045~: 파일 중간 분산 import

## bridge_backup.py 이슈 (2026-03-16 분석)
- `register_hook()` (L328~): 구버전 flat hooks 포맷 — 직접 호출 금지, settings.json 손상 가능

## Agent Teams 활성화
- settings.json에 `"env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}` 추가됨 (2026-03-16)
- Delegate Mode: Shift+Tab으로 활성화

## ClaudeBlog 블로그 자동화 설정 (2026-03-16 확정)
- **경로**: `Q:\Claudework\ClaudeBlog`
- **실행 방법**: `Q:\Claudework\ClaudeBlog\실행.vbs` 더블클릭 (콘솔창 없음)
- **바탕화면 아이콘**: `바탕화면_아이콘_만들기.bat` 실행하면 생성됨
- **venv**: `.venv\Scripts\pythonw.exe` (app.py 실행 전용)
- **config**: `config.json` — Gemini 키 4개(스칼렛/바이올렛/세번째/네번째), 모델=gemini-2.5-flash
- **쿠키**: `logs/naver_cookies.json` — 절대경로 필수 (`_BASE_DIR` 기준)
- **네이버 계정**: `bridgejobkr` / blog_id=`bridgejob`
- **GUI 앱**: `app.py` (tkinter) — 쿠키저장/건조실행/지금발행/스케줄 버튼
- **시크릿**: `modules/secret_loader.py` → Windows Credential Manager `BridgeBlogAuto/master_key`
- **중요**: 테스트 실행 남발 금지 — 네이버 보안 블락 유발함. 실제 발행만 실행.
- **글 구조**: 글↔사진 교차 (글-사진-글-사진-...) + 마지막에 배너사진(카카오링크)
- **인용구**: ENTER+BACKSPACE로 탈출 (ENTER+ENTER 아님)
- **확정 동작 (2026-03-17)**: 제목 입력 ✅ / 인용구 삽입 ✅ / 본문 글쓰기 ✅

## ClaudeBlog 확정 수정 이력 (2026-03-17)
- **서론→제목 침범 방지**: `_force_body_focus()` 추가 — 제목 입력 후 포커스 검증+강제 이동
- **가운데 정렬**: Ctrl+E → `document.execCommand('justifyCenter')` 전면 교체 (SE4 호환)
- **배너 링크**: JS click → ActionChains click + `button[data-name='link']` 광범위 탐색
- **예약 날짜**: `days_ahead: 2` (2일 후) + React nativeInputValueSetter 날짜 주입

## ClaudeBlog 개선 필요 사항 (2026-03-17 확정)
- **가운데 정렬**: 글 전체 가운데 정렬 필요 — 작성 완료 후 Ctrl+A → Ctrl+E 적용
- **서론 우선**: 본문에서 사진 삽입 전 반드시 서론(서론) 텍스트 먼저 입력
  - [IMG_TOP]을 서론 이후 위치로 이동 (기존: body 첫 줄 강제 → 변경: 서론 다음)
- **제목 커버 이미지**: 제목 섹션에도 사진 삽입 필요 (Naver SE4 커버 이미지 기능)
  - `_set_cover_image()` 메서드로 구현, 실패 시 graceful fallback
- **글자수 기준**: 1500자 이상 (순수 한글, 공백 제외)
- **태그 분포**: 필수 5개(브릿지/원어민채용/원어민에이전시/브릿지에이전시/영어선생님고용) + 서이추/서이추환영 마지막 고정

## 광고 키워드 규칙 (2026-03-17 확정)
- **"광고"** = Teast 구인공고 포스팅 작업을 의미
- 실행 스크립트: `Q:\Claudework\bridge base\tools\_teast_build_post.py`
- 스케줄러: `Q:\Claudework\bridge base\scripts\teast_monthly.py --once --live`
- 배치파일: `Q:\Claudework\bridge base\scripts\teast_post.bat`
- 바탕화면 바로가기: `C:\Users\Scarlett\Desktop\광고 올리기.lnk`
- 예약 작업: `TeastPost30Day` — 매 30일마다 09:00 자동실행 (다음: 2026-04-16)
- `--show` 플래그로 포스팅 내용 미리보기 가능 (실제 포스팅 안 함)

## Python 실행 규칙 (2026-03-14 확정)
- `C:\Python314` — 환경 깨짐, 사용 금지
- **항상 사용**: `C:\Users\Scarlett\AppData\Local\Programs\Python\Python313\python.exe`
- D 드라이브 Python 접근 금지
- C 드라이브는 실행 파일(Python 등) 용도만 — 아티팩트/메모리 저장 금지
- **모든 저장 파일은 Q:\Claudework\bridge base 내부에만**
