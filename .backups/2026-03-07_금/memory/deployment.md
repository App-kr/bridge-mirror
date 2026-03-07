# Deployment — 배포 및 환경설정

## 환경변수 (.env)

### 필수 시크릿
| 변수 | 용도 | 주의 |
|------|------|------|
| `BRIDGE_FIELD_KEY` | AES-256-GCM 암호화 키 | 변경 시 기존 데이터 복호화 불가 |
| `JWT_SECRET` | JWT 서명 | BRIDGE_FIELD_KEY와 다른 값 |
| `ADMIN_API_KEY` | Admin API 인증 | **FROZEN — 절대 변경 금지** |
| `ADMIN_PASSWORD` | Admin 로그인 비밀번호 | **FROZEN — 절대 변경 금지** |
| `SUPABASE_URL` | Supabase 프로젝트 URL | |
| `SUPABASE_ANON_KEY` | Supabase anon key | |
| `SUPABASE_SERVICE_KEY` | Supabase service key | 서버만 |
| `BRIDGE_SMTP_EMAIL` | Gmail 발송 주소 | |
| `BRIDGE_SMTP_PASSWORD` | Gmail 앱 비밀번호 | 2FA 필요 |

### 환경 설정
| 변수 | 값 | 효과 |
|------|------|------|
| `BRIDGE_DB_PATH` | 경로 | SQLite 파일 위치 (기본: ./master.db) |
| `BRIDGE_ENV` | `production` | Swagger 비활성 + admin key 강제 |

### 프론트엔드 공개 변수 (.env.local)
```
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```
→ `NEXT_PUBLIC_`에 시크릿 절대 금지

## 서버 배포 (Ubuntu 24.04)

### 파일 구조
```
deploy/
  setup.sh              — 초기 세팅 스크립트
  bridge-api.service    — FastAPI systemd unit
  bridge-frontend.service — Next.js systemd unit
  nginx-bridge.conf     — Reverse proxy + SSL
  deploy.sh             — 전체 자동화
```

### nginx 설정 핵심
- Reverse proxy: 3000 (frontend) + 8000 (API)
- SSL 인증서 (Let's Encrypt)
- `/admin` IP 제한: allow 127.0.0.1 + deploy IP
- 정적 파일: `/uploads/` → `/opt/bridge/uploads/`
- 보안 헤더: CSP, Permissions-Policy, X-Permitted-Cross-Domain-Policies

### systemd 서비스
```bash
sudo systemctl start bridge-api        # FastAPI
sudo systemctl start bridge-frontend   # Next.js
sudo systemctl status bridge-api
sudo journalctl -u bridge-api -f       # 로그 확인
```

### 배포 절차
```bash
ssh deploy@server
cd /opt/bridge
git pull
pip install -r requirements.txt
cd web_frontend && npm install && npm run build
sudo systemctl restart bridge-api bridge-frontend
```

## Migration 관리
```
migrations/
  alter_community_boards.py  — 7-board CHECK 제약
  seed_community_posts.py    — JSON seed 로딩 (idempotent)
  add_file_uploads.sql       — file_uploads 테이블
  post_content/              — 11 JSON seed 파일
```

## Supabase 뷰
- `public_jobs` — 민감 컬럼 제외
- `public_candidates` — 민감 컬럼 제외
→ 프론트엔드는 반드시 뷰만 접근
