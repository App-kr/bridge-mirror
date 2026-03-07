# Architecture — 시스템 구조

## Data Flow
```
master.db (SQLite) ──→ auto_pipeline_v2.py ──→ Supabase (PostgreSQL)
                                                    │
Supabase public_jobs view ──→ Next.js frontend (anon key)
Web form → api_server.py ──→ Supabase + confirmation email
community_posts → api_server.py /api/community/* ──→ Next.js /community
interview → api_server.py ──→ master.db + email notification
```

## Frontend (web_frontend/)
- **Framework**: Next.js 15, Tailwind CSS, TypeScript
- **Routes**: 14개 (static + dynamic)
- **Entry**: `src/app/page.tsx` (홈), `src/app/layout.tsx`
- **Components**: `src/components/` (JobCard, ApplyPanel, MarkdownBody, NewPostForm)
- **Libraries**: `src/lib/` (boards.ts, animations.ts, image-resize.ts, supabase.ts)
- **Service Worker**: `public/register-sw.js`

## Backend (Python)
- **Entry**: `api_server.py` (FastAPI, uvicorn)
- **DB**: `master.db` (SQLite, WAL mode, busy_timeout=5000)
- **DB Path**: `BRIDGE_DB_PATH` env → default `./master.db`
- **.env 로딩**: `Path(__file__).resolve().parent / ".env"` (portable)
- **Encryption**: `security_vault.py` (AES-256-GCM, 수정 금지)
- **Email**: `email_templates.py` (Gmail SMTP, non-blocking)
- **Sync**: `auto_pipeline_v2.py` (master.db → Supabase)

## Community Board System
- **7 boards**: visa, support, support_kr, about, korea, tips, testimonials
- **주의**: Board name은 `support` (NOT `support_en`)
- **DB**: `community_posts` table, CHECK constraint for 7 boards
- **Backend**: `_BOARDS = {"visa","support_kr","support","about","korea","tips","testimonials"}`
- **Frontend SOT**: `web_frontend/src/lib/boards.ts`
- **Routes**: `/community/[board]/`, `/community/[board]/[id]/`, `/community/[board]/new/`
- **Layouts**: list, hero-cards, card-grid, photo-cards, testimonial
- **258 posts**: 169 tips, 22 visa, 20 support, 19 support_kr, 10 about, 10 korea, 8 testimonials

## File Upload System
- **Endpoint**: `POST /api/upload/{entity_type}/{entity_id}?file_type=...`
- **Entity types**: `candidate`, `inquiry`
- **Limits**: photo(5MB), cv/cover_letter(10MB), certificate(10MB), video(100MB), attachment(10MB)
- **Storage**: `./uploads/` (dev), `/opt/bridge/uploads/` (prod)
- **Photo pipeline**: client resize(1200px) → server thumbnail(150x150, Pillow)
- **DB**: `file_uploads` in Supabase, `photo_url`/`thumb_url` on `candidates`

## Email System
- **Sender**: `email_templates.py` (Gmail SMTP)
- **Env**: `BRIDGE_SMTP_EMAIL`, `BRIDGE_SMTP_PASSWORD` (app password)
- **Templates**: applicant confirm(EN), employer confirm(KR), interview invite(EN+KR)
- **Non-blocking**: email 실패 → form 제출에 영향 없음

## Form UX Pattern
- 5+ options → `<select>` dropdown
- Multi-select → checkbox lists
- 2-4 options → SingleTog buttons
- Components: `Dropdown`, `CheckList`, `FileUpload`
- Post-submission file upload on success screen

## Project Folder Structure (2026-03-06 정리)
```
Q:/Claudework/bridge base/
├── api_server.py          ← 메인 백엔드 (FastAPI)
├── email_templates.py     ← 이메일 모듈 (api_server 임포트)
├── security_vault.py      ← PII 암호화 (수정금지, api_server 임포트)
├── security_middleware.py  ← 보안 미들웨어 (api_server 임포트)
├── inbox_api.py           ← 인박스 라우터 (api_server 임포트)
├── gmail_collector.py     ← Gmail 라우터 (api_server 임포트)
├── auto_pipeline_v2.py    ← master.db → Supabase 동기화
├── parse_jobs.py          ← Job 파싱 CLI
├── master.db              ← 메인 DB
├── CLAUDE.md              ← 프로젝트 규칙
├── requirements.txt       ← Python 의존성
├── Procfile / render.yaml / railway.json / runtime.txt  ← 배포 설정 (루트 필수)
├── run_telegram_bot.py / start_bot.py  ← 봇 실행 스크립트
│
├── web_frontend/          ← Next.js 15 프론트엔드
├── security/              ← 보안 모듈 (pii_scanner, auth, version)
├── audit/                 ← 감사 로그 (JSONL)
├── migrations/            ← DB 마이그레이션 + seeders/
├── scripts/               ← 유틸리티 (audio/, google/, parsers/, generators/)
├── tools/                 ← RPA/자동화 도구 (craigslist, interview, agent)
├── deploy/                ← 배포 설정 (nginx, systemd, deploy.sh)
├── docs/                  ← 문서 (MASTER_PLAN, DEPLOY, CREDENTIALS)
├── bridge_agent/          ← CLI 에이전트 패키지
├── telegram_agent/        ← 텔레그램 봇 패키지
├── admin_app/             ← 데스크톱 관리 앱
├── backups/               ← 백업 (db/, 스냅샷)
├── archive/               ← 레거시/테스트 데이터 (gitignored)
├── uploads/               ← 파일 업로드 저장소
├── secure_downloads/      ← 보안 다운로드 경로
└── .memory/               ← Claude 메모리
```
주의: 루트 Python 파일 6개는 api_server.py가 임포트하므로 이동 불가.
