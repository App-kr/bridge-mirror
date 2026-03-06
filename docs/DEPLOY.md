# BRIDGE Agency 배포 가이드

## 사전 준비

- [ ] GitHub 계정
- [ ] Vercel 계정 (https://vercel.com)
- [ ] Railway 계정 (https://railway.app)
- [ ] bridgejob.co.kr 도메인 DNS 관리 접근
- [ ] 보안 감사 통과 확인 (Q:/bridge-overnight/SECURITY_FULL_AUDIT.md → HIGH 0건)

---

## Step 1: GitHub 리포지토리

1. https://github.com 에서 새 리포지토리 생성
   - 이름: `bridge-agency` (또는 원하는 이름)
   - Private 설정
   - README, .gitignore 추가하지 않기 (이미 있음)

2. 로컬에서 리모트 연결:
   ```bash
   cd "Q:/Claudework/bridge base"
   git remote add origin https://github.com/YOUR_USERNAME/bridge-agency.git
   git branch -M main
   git push -u origin main
   ```

3. 확인: GitHub에서 코드가 보이는지 확인. `.env` 파일은 보이면 안 됨.

---

## Step 2: Backend 배포 (Railway)

1. https://railway.app 로그인 (GitHub 계정 연동)

2. **New Project** → **Deploy from GitHub repo** → `bridge-agency` 선택

3. 서비스 설정:
   - Root Directory: `/` (루트)
   - Start Command: 자동 감지 (Procfile에서 읽음)

4. **환경변수 설정** (Settings → Variables):

   | 변수 | 설명 | 필수 |
   |------|------|------|
   | `BRIDGE_ENV` | `production` | 필수 |
   | `ADMIN_API_KEY` | 관리자 API 인증 키 (64자 랜덤 문자열) | 필수 |
   | `JWT_SECRET` | JWT 서명 키 (32자+ 랜덤) | 필수 |
   | `SUPABASE_URL` | Supabase 프로젝트 URL | 필수 |
   | `SUPABASE_ANON_KEY` | Supabase 공개 anon 키 | 필수 |
   | `SUPABASE_SERVICE_KEY` | Supabase 서비스 키 (서버 전용) | 필수 |
   | `BRIDGE_DB_PATH` | SQLite 경로 (볼륨 사용 시 `/data/master.db`) | 선택 |
   | `BRIDGE_UPLOAD_DIR` | 업로드 폴더 (볼륨 사용 시 `/data/uploads`) | 선택 |
   | `GMAIL_USER` | Gmail 발신 계정 | 선택 |
   | `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 | 선택 |
   | `SMTP_HOST` | SMTP 호스트 | 선택 |
   | `SMTP_PORT` | SMTP 포트 | 선택 |
   | `SMTP_USER` | SMTP 사용자 | 선택 |
   | `SMTP_PASS` | SMTP 비밀번호 | 선택 |
   | `CONTACT_EMAIL` | 문의 수신 이메일 | 선택 |

   > 키 생성: `python -c "import secrets; print(secrets.token_hex(32))"`

5. **볼륨 마운트** (SQLite 영구 저장):
   - Settings → Volumes → Add Volume
   - Mount Path: `/data`
   - 환경변수: `BRIDGE_DB_PATH=/data/master.db`
   - 환경변수: `BRIDGE_UPLOAD_DIR=/data/uploads`

6. **배포 확인**:
   - Deploy 탭에서 빌드 로그 확인
   - 성공 후 제공되는 URL (예: `bridge-agency.up.railway.app`) 접속
   - `{"service": "BRIDGE Recruitment API", "status": "running"}` 확인

7. **초기 DB 설정** (최초 1회):
   - Railway Shell 또는 로컬에서 master.db를 `/data/master.db`로 업로드
   - Railway CLI: `railway run python -c "import sqlite3; ..."`

---

## Step 3: Frontend 배포 (Vercel)

1. https://vercel.com 로그인 (GitHub 계정 연동)

2. **Add New Project** → **Import Git Repository** → `bridge-agency` 선택

3. 프로젝트 설정:
   - Framework Preset: **Next.js** (자동 감지)
   - Root Directory: `web_frontend`
   - Build Command: `npm run build`
   - Output Directory: `.next`

4. **환경변수 설정** (Settings → Environment Variables):

   | 변수 | 값 | 설명 |
   |------|-----|------|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://bridge-agency.up.railway.app` | Railway 백엔드 URL |
   | `NEXT_PUBLIC_SUPABASE_URL` | Supabase 프로젝트 URL | 공개 |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon 키 | 공개 (anon만!) |
   | `NEXT_PUBLIC_SITE_NAME` | `BRIDGE` | 사이트명 |
   | `NEXT_PUBLIC_SITE_URL` | `https://bridgejob.co.kr` | 사이트 URL |

   > 주의: `NEXT_PUBLIC_`에 SERVICE_KEY나 ADMIN_KEY 절대 넣지 말 것!

5. **Deploy** 클릭 → 빌드 성공 확인

6. **확인**: Vercel 제공 URL (예: `bridge-agency.vercel.app`) 접속하여 페이지 로드 확인

---

## Step 4: 도메인 연결 (bridgejob.co.kr)

### 4-1. Frontend (Vercel)

1. Vercel 대시보드 → 프로젝트 → Settings → Domains
2. `bridgejob.co.kr` 입력 → Add
3. DNS 설정 (도메인 관리자 패널에서):

   | 타입 | 호스트 | 값 |
   |------|--------|-----|
   | CNAME | `@` 또는 비워둠 | `cname.vercel-dns.com` |
   | CNAME | `www` | `cname.vercel-dns.com` |

4. SSL 인증서: Vercel이 자동 발급 (Let's Encrypt)
5. 확인: https://bridgejob.co.kr 접속

### 4-2. Backend (Railway)

1. Railway 대시보드 → 서비스 → Settings → Custom Domain
2. `api.bridgejob.co.kr` 입력 → Add
3. DNS 설정:

   | 타입 | 호스트 | 값 |
   |------|--------|-----|
   | CNAME | `api` | Railway에서 제공하는 도메인 |

4. SSL: Railway 자동 발급
5. Vercel 환경변수 업데이트:
   - `NEXT_PUBLIC_API_BASE_URL` = `https://api.bridgejob.co.kr`
   - Vercel 재배포 (Deployments → Redeploy)

---

## Step 5: 배포 후 확인

### 필수 체크리스트

```bash
# 1. 백엔드 상태
curl https://api.bridgejob.co.kr/
# → {"service": "BRIDGE Recruitment API", "status": "running"}

# 2. 프론트엔드 로드
curl -s -o /dev/null -w "%{http_code}" https://bridgejob.co.kr/
# → 200

# 3. 공개 API
curl https://api.bridgejob.co.kr/api/jobs | head -100
# → 구인 목록 JSON

# 4. 관리자 접근 차단 (키 없이)
curl -s -o /dev/null -w "%{http_code}" https://api.bridgejob.co.kr/api/admin/inbox
# → 403

# 5. CORS 확인
curl -s -I https://api.bridgejob.co.kr/ -H "Origin: https://bridgejob.co.kr" | grep -i access-control
# → Access-Control-Allow-Origin: https://bridgejob.co.kr

# 6. 보안 헤더
curl -s -I https://bridgejob.co.kr/ | grep -iE "x-frame|x-content|referrer"
# → X-Frame-Options: DENY
# → X-Content-Type-Options: nosniff
```

### 관리자 접근 방법
1. 브라우저에서 `https://bridgejob.co.kr/admin` 접속
2. Admin Key 입력 (ADMIN_API_KEY 환경변수 값)
3. 대시보드, 수신함, 게시판 관리 등 사용

---

## 문제 해결

### Railway 빌드 실패
- `requirements.txt`에 누락된 패키지 확인
- Python 버전 확인 (runtime.txt → python-3.11)
- Railway 로그: Deployments → 실패한 배포 → View Logs

### Vercel 빌드 실패
- `npm run build` 로컬에서 먼저 확인
- 환경변수 누락 확인 (특히 NEXT_PUBLIC_API_BASE_URL)
- Node.js 버전 확인 (18+ 필요)

### CORS 에러
- Railway 환경변수 확인: `BRIDGE_ENV=production`
- api_server.py의 ALLOWED_ORIGINS에 도메인 포함 확인
- `https://` 프로토콜 일치 확인

### SQLite 데이터 유실
- Railway 볼륨이 마운트되었는지 확인
- `BRIDGE_DB_PATH`가 볼륨 경로를 가리키는지 확인
- 주기적 백업 권장: Railway Shell에서 `cp /data/master.db /data/backup_$(date +%Y%m%d).db`

---

## 연락처
- 기술 문의: bridgejobkr@gmail.com
