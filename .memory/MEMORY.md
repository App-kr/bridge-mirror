# BRIDGE Project — Memory Index
> 인덱스 전용. 상세 내용은 각 토픽 파일 참조.
> ⚠️ 200줄 초과 시 잘림 — 이 파일은 항상 200줄 이내 유지

## Quick Reference
- **서비스**: bridgejob.co.kr (ESL 교사 채용)
- **스택**: FastAPI + Next.js 15 + Supabase + SQLite
- **DB**: candidates=3059 | client_inquiries=1227 | jobs=1072 | 5.2MB

---

## ⚡ 블로그 작업 시 필독 (매번 잊지 말 것)
> 상세 규칙: `.memory/blog-gemini-prompt-v6.6.md`
> 원본 자동화 규칙: `Q:/Claudework/ClaudeBlog/CLAUDE.md` (세션 시작 시 읽을 것)

**글자수**: 최소 1,500 / 목표 1,600 / 권장 2,000 / 채용실무 2,000~2,500자
**내부 백링크**: 결론 직후 2개 이상 필수
**이미지 마커**: Claude 응답에는 출력 금지, inject_draft.py body에는 포함
**마커 종류**: [IMG_TOP] [IMG_1]~[IMG_6] [QUOTE]...[/QUOTE] [IMG_BANNER]
**3대 태그 고정 (1~3번)**: #원어민강사 #원어민채용 #원어민구인
**태그 끝 고정**: #서이추 #서이추환영 / 총 11~13개
**저작권**: ⓒ 무단 전재 및 재배포 금지 / 중요 내용은 사실 확인 후 시행바랍니다
**마침표 전면 금지** / **비자명 직접 언급 금지** (E-2 등)
**에이전시 섹션**: 100자 이내 2~3문장
**사례**: 매 포스팅 완전 교체 (수치·상황 재사용 절대 금지)
**출력 순서**: 제목→서론→본문1→본문2→[확장]→본문3→결론→**내부백링크2개**→에이전시섹션→저작권→태그

## ⚡ ClaudeBlog python 실행 (cd 없이 절대경로)
```
"Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --dry
"Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --now
"Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe" -X utf8 "Q:/Claudework/ClaudeBlog/main.py" --publish-approved
```
**config.json**: `claude_fallback: true` 유지 필수
**Gemini 429**: 한국 오전 9시 초기화 / Anthropic 크레딧 부족 시 Plans&Billing 충전

---

## Topic Files

| 파일 | 내용 | 최종 업데이트 |
|------|------|-------------|
| [architecture.md](architecture.md) | 시스템 구조, 데이터 흐름 | 2026-02-28 |
| [api-endpoints.md](api-endpoints.md) | API 엔드포인트, Rate limit | 2026-02-28 |
| [debugging-patterns.md](debugging-patterns.md) | 디버깅 패턴, 흔한 오류 | 2026-02-28 |
| [admin-system.md](admin-system.md) | 관리자 페이지 | 2026-02-28 |
| [design-system.md](design-system.md) | UI 디자인 규칙 | 2026-02-28 |
| [deployment.md](deployment.md) | 배포 설정 | 2026-02-28 |
| [blog-gemini-prompt-v6.6.md](blog-gemini-prompt-v6.6.md) | 블로그 마스터 규칙 v6.6 **최신** | 2026-03-18 |
| [blog-automation.md](blog-automation.md) | ClaudeBlog 자동화 전체 기술 레퍼런스 (**환각 방지**) | 2026-03-18 |

---

## 자동 실행 규칙 (세션 시작 시)
```bash
cat tasks/lessons.md | tail -20
cat tasks/todo.md | grep "^\- \[ \]"
git log --name-only -3
```

## User Preferences
- 묻지 말고 자율 실행 선호
- 포커스 스틸 금지 (게임 중 바탕화면 튕김 방지)
- GUI 앱 실행 금지 / 백그라운드는 run_in_background로만
- **서버 규칙**: Hot Reload 상시 실행 중 — 서버 시작/종료 명령 금지

## Python 실행 규칙
- **ClaudeBlog**: `Q:/Claudework/ClaudeBlog/.venv/Scripts/python.exe` 전용
- `C:\Python314` 사용 금지 (환경 깨짐)
- 모든 저장 파일은 `Q:\Claudework\bridge base` 내부에만

## Render 배포 비용
- 월 500분 한도 / 70% 경고 → Auto-Deploy OFF
- Free tier: 15분 무트래픽 sleep, SQLite ephemeral

## HERO 3D 지구 확정 (영구)
- `EarthGlobe.tsx` / R=7, yOffset=-6.9, scale.x=1.28
- 자전: earth.rotation.y += 0.0014 / 투명도 0.32
- tiltGroup(기울기) / earth(자전) 분리 필수

## 보안 레이어 현황
| 레이어 | 파일 | 상태 |
|---|---|---|
| 1 | `.hooks/guard.py` | ✅ |
| 2 | `.hooks/task_gate.py` | ✅ |
| 4 | `.env` 분리 | ✅ |
| 5 | AES-256-GCM `security_vault.py` | ✅ |

## ClaudeBlog 자동화 확정 동작
- **업로더 마커**: [IMG_TOP] 서론 뒤 / [IMG_1~6] 단락 사이 / [QUOTE]소제목[/QUOTE] / [IMG_BANNER] 끝
- **인용구 탈출**: ENTER+BACKSPACE (ENTER+ENTER 아님)
- **쿠키**: logs/naver_cookies.json (절대경로 필수)
- **예약 발행**: days_ahead=2 / 즉시 발행 금지
- **inject_draft.py**: 승인 글 직접 Excel 삽입 → --publish-approved 발행

## Team Names
- **Scarlett** — 대표 / **Violet** — 운영부장 / MARK 사용 금지

## Bridge 업무 흐름
- **파일 규칙**: `번호_성별_국적(00born).pdf`
- **구인자**: 구글폼→이메일→워드파일(Job.XXXX) + Client 시트
- **광고** = Teast 구인공고 (`tools/_teast_build_post.py`)

## Agent Teams
- settings.json `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` 활성화
- Delegate Mode: Shift+Tab
