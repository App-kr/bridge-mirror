# BRIDGE 마스터 프롬프트 — 전체 시스템 점검 & 오픈 준비
> 작성: 2026-05-11 | 대상: 마누스(Manus) / 외부 보안 감사자 / 신규 합류 AI
> **누락 금지** — 이 문서는 BRIDGE 오픈/유지/확장의 단일 진실 원소스(SSOT).

---

## 0. EXECUTIVE SUMMARY

**BRIDGE**는 한국에서 활동할 영어 원어민 강사 ↔ 학원/유치원을 매칭하는 채용 플랫폼.
- 후보자 DB: 3,134명 (전부 T3v1 3중 암호화)
- 학원 DB: 1,239건 (PII 암호화)
- 채용공고: 2,299건
- 일일 운영: pw.py 단일 진실 원소스 → ClaudeBlog/Render/Vercel 자동 동기화

**왜 아직 정식 오픈을 못 했는가** (요약 5개):
1. 도메인 이관 (`bridgejob.co.kr` DNS A 레코드 → Vercel) 미완료
2. 결제 시스템 통합 — `bridge_ads` (별도 광고 포털) 만 PayPal 키 보유, BRIDGE 본체는 아직 결제 없음
3. Vercel 침해 우려 (2026-04-19~5월) → 보안 강화 반복 작업
4. CAPTCHA / 폼 UX 안정화 (멈춤 복구 / 한영 병기) 완료 직후 단계
5. 약관/개인정보처리방침 최종 검토 + SEO 메타 미점검

**보안 상태**: 10계층 방어 가동 중 (§2.1~2.10), Defense-in-Depth v2.0 자가 진화 시스템 동작.

---

## 1. 시스템 아키텍처 — 어디서 뭘 받아오나

### 1.1 컴포넌트 토폴로지

```
[사용자 브라우저]
    │
    │ HTTPS
    ▼
[Vercel — bridge-chi-lime.vercel.app]   ◀ 정적/SSR Next.js 15
    │   ├── /apply  /inquiry  /admin/*
    │   ├── env: NEXT_PUBLIC_API_URL=https://bridge-n7hk.onrender.com
    │   └── CORS Origin: bridgejob.co.kr (목표), bridge-chi-lime.vercel.app (현재)
    │
    │ fetch (CORS + Origin + 세션 토큰)
    ▼
[Render — bridge-n7hk.onrender.com]   ◀ FastAPI Python 3.11
    │   ├── api_server.py (202 endpoints)
    │   ├── security_middleware.py (10계층)
    │   ├── /data/master.db (Render 영구 디스크, WAL 모드)
    │   ├── S3 — 이력서 PDF, 사진, 영상 (Render presigned URL)
    │   └── 환경변수 20개 (JWT_SECRET, ADMIN_API_KEY 등 §2.2)
    │
    ├──▶ [Anthropic API] — LLM 처리 (이력서 추출, 메일 분류)
    ├──▶ [Gemini API] — ClaudeBlog 글 작성 (4계정 로테이션)
    ├──▶ [Naver SMTP] — 학원 자동응답 메일
    ├──▶ [Gmail SMTP] — 강사 안내 메일
    └──▶ [Telegram Bot] — 운영자 알림 (관리자만)
```

### 1.2 데이터 흐름 — 핵심 4개 시나리오

**① 강사 지원 (POST /api/apply)**
```
브라우저 → /apply 폼 입력 → CAPTCHA 통과
  → POST /api/apply (FormData + JSON)
    1. honeypot (_url 비어있는지 확인 — 봇 차단)
    2. PuzzleCaptcha 토큰 검증
    3. ratelimit (5회/5분, IP 기준)
    4. Pydantic 검증 + 길이/문자셋 검사
    5. T3v1 3중 암호화 (email/phone/name/dob/kakao_id 등 14필드)
    6. INSERT candidates → master.db
    7. apply_token (JWT, 15분) 발급 → 후속 파일 업로드용
    8. 백그라운드: _save_raw_submission (암호화 백업 .enc 별도 보관)
    9. 백그라운드: _auto_process_resume (PII 자동제거 → cv_processed.pdf)
   10. 응답: {id, apply_token, mode: created|updated}
```

**② 학원 문의 (POST /api/inquiry)**
```
브라우저 → /inquiry 3단계 → 동의 + CAPTCHA
  → POST /api/inquiry
    1~7. 위와 동일 (honeypot/captcha/ratelimit/검증/암호화/INSERT)
    8. send_employer_confirmation (Naver SMTP 자동응답)
    9. mail_introduce_log 기록 (다음 강사 추천 시 활용)
```

**③ 관리자 로그인 (POST /api/admin/login)**
```
/admin → 비밀번호 입력
  → POST /api/admin/login {password}
    1. SecurityMiddleware (UA/blacklist/ratelimit/공격패턴 검사)
    2. admin_login_guard.record_fail — 실패 누진 (5/10/15회)
       ★ ADMIN_ALLOWED_IPS(115.22.193.150)은 면역 — record_fail에서 카운트 안 함
    3. _verify_admin_password (pbkdf2 해시 비교)
    4. _create_session (/24 서브넷 바인딩 + 8시간 TTL + 슬라이딩 갱신)
    5. HttpOnly Cookie 'bridge_session' 발급 (Secure, SameSite=None)
    6. 응답: {session_token, expires_at}
  → GET /api/admin/key (x-admin-token 헤더)
    └─ session 검증 → api_key 반환 → 프론트 메모리 보관 (localStorage 금지)
```

**④ 채용공고 광고 (bridge_ads 별도 서비스)**
```
별도 도메인 → bridge-ads.onrender.com
PayPal 결제 → 학원이 광고 게재 → SQLite 광고 DB
* 본체 BRIDGE와 분리됨 — 결제 통합 시 별도 §3 참조
```

### 1.3 외부 API 의존성

| 서비스 | 용도 | 키 위치 | 무료 한도 |
|--------|------|---------|----------|
| Anthropic | LLM (이력서 추출) | `ANTHROPIC_API_KEY` (Render env) | 유료 |
| Gemini (4계정) | ClaudeBlog 자동 글 | `GEMINI_KEY_1~4` (bx) | 일 1500 req/계정 |
| Naver SMTP | 학원 자동응답 | `NAVER_SMTP_PASS` (bx + Render) | 무료 |
| Gmail SMTP | 강사 안내 | `GMAIL_APP_PASSWORD` (bx) | 무료 (500/일) |
| Telegram Bot | 운영 알림 | `TELEGRAM_BOT_TOKEN` (bx + Render) | 무료 |
| AWS S3 (Render storage) | 파일 저장 | Render 자체 통합 | 5GB 무료 |
| Spamhaus DROP | IP 위협 인텔 | 공개 | 무료 |
| Firehol level1 | IP 위협 인텔 | 공개 | 무료 |

### 1.4 데이터베이스 스키마 (핵심 테이블만)

```sql
-- candidates: 후보 강사 (3134명, 87컬럼)
candidates(
  id INTEGER PK,
  candidate_id TEXT UNIQUE,
  sheet_number INTEGER,           -- 5자리 (10000+)
  email TEXT,                     -- T3v1 암호화
  full_name TEXT,                 -- T3v1
  nationality TEXT,               -- T3v1
  nationality_plain TEXT,         -- 검색용 평문 (HASH 대체 예정)
  dob TEXT, gender TEXT, ...      -- 전부 T3v1
  is_deleted INTEGER DEFAULT 0,   -- 논리 삭제만
  created_at TIMESTAMP
);

-- client_inquiries: 학원 문의 (1239건)
client_inquiries(
  id INTEGER PK,
  contact_name TEXT,              -- T3v1
  email TEXT, phone TEXT,         -- T3v1
  school_name_plain TEXT,         -- 검색용 평문
  location_plain TEXT,
  memo TEXT,                      -- T3v1
  source_file TEXT,
  is_deleted INTEGER DEFAULT 0
);

-- jobs: 채용공고 (2299건)
jobs(
  job_id TEXT PK,                 -- Job.XXXX 형식
  title TEXT, region TEXT, salary TEXT,
  posted_at TIMESTAMP,
  is_active INTEGER DEFAULT 1
);

-- 파일 업로드 / 메일 발송 로그 / 인터뷰 / 광고 등 30+ 테이블
```

DB 위치: `/data/master.db` (Render 영구 디스크 1GB) — **이동 절대 금지**

---

## 2. 보안 계층 (10단계 + Defense-in-Depth v2.0)

### 2.1 HTTPS / TLS
- Vercel: 자동 Let's Encrypt + HSTS
- Render: 자동 SSL + TLS 1.2+
- HTTP→HTTPS 강제 리다이렉트 (양쪽 다 기본 적용)

### 2.2 인증 3계층
| 계층 | 대상 | 헤더 | 만료 |
|------|------|------|------|
| **세션 토큰** | 프론트엔드 사용자 | `Cookie: bridge_session` (HttpOnly) | 8시간 슬라이딩 |
| **API 키** | 서버 간 / 자동화 | `X-Admin-Key` | 무기한 |
| **IP 화이트리스트** | 관리자 IP 전용 | `ADMIN_ALLOWED_IPS=115.22.193.150/32` | — |

**★ 화이트리스트 IP는 어떤 차단 메소드(`is_blocked`/`record_attack`/`block`/`block_permanent`/`admin_login_guard.record_fail`)에도 등록되지 않음 — 관리자 lockout 영구 방지** (커밋 b8da8801, 8a46c892).

### 2.3 입력 검증
- Pydantic BaseModel 타입 + 길이/패턴 검증
- SQL: 100% parameterized query (f-string 금지)
- HTML: DOMPurify (DOM 출력 시) + escape
- 파일: magic bytes + 확장자 이중 검증 (PDF/DOC/DOCX/MP4/JPG/PNG)
- ZIP bomb 방어 (해제 후 200MB / 200파일 제한)

### 2.4 T3v1 PII 3중 암호화
```
T3v1 = magic(4) + nonce1(12) + nonce2(12) + nonce3(12) + ciphertext
L1_key = SHA-256(BRIDGE_FIELD_KEY + b"L1" + column_name)
L2_key = SHA-256(BRIDGE_FIELD_KEY + b"L2" + nonce1)
L3_key = SHA-256(BRIDGE_FIELD_KEY + b"L3" + nonce2 + nonce1)
ct1 = AES-GCM(L1_key, n1).encrypt(plaintext)
ct2 = AES-GCM(L2_key, n2).encrypt(ct1)
ct3 = AES-GCM(L3_key, n3).encrypt(ct2)
```
- 컬럼 14개 (candidates), 6개 (client_inquiries) 대상
- `BRIDGE_FIELD_KEY` ≠ `JWT_SECRET` (키 분리 원칙, 커밋 9e8bdfde)

### 2.5 IP/속도 제어
| 미들웨어 | 한도 |
|---------|------|
| `IPRateLimitMiddleware` | 240회/10초 (body 검증 이전) |
| `_rate_ok` 엔드포인트별 | /apply 5/5분, /inquiry 5/5분, export 10/일 |
| `BodySizeLimitMiddleware` | 10MB |
| `IpBlacklist` 누진차단 | 5회/24h, 10회/7일, 15회/영구 (화이트리스트 면역) |

### 2.6 봇/스크래퍼 방어
- `_is_scraper_ua` — curl/wget/Python-urllib 등 UA 패턴 매칭
- 허니팟 경로 (`/admin.php`, `/.env`, `/wp-login.php`) → 즉시 영구 차단
- 폼 honeypot `_url` 필드 (CSS로 숨김, 값 들어오면 봇)
- PuzzleCaptcha (3종 랜덤: slide/rotate/order)

### 2.7 공격 탐지
- `_attack_scan_middleware` — SQLi, XSS, SSRF, LLM 인젝션 패턴
- `ThreatFeedMiddleware` — Spamhaus/Firehol CIDR 매칭 (캐시됨)
- `_pii_scan_body` — 발송 메일 PII 노출 차단
- 위반 시: 텔레그램 즉시 알림

### 2.8 CSRF & 헤더
- `CSRFOriginMiddleware` — admin mutation 요청 Origin 검증
- `TrustedHostMiddleware` — 허용 도메인만
- Security Headers: HSTS / X-Content-Type-Options / X-Frame-Options / CSP

### 2.9 감사 로그
- `AdminAuditMiddleware` — 모든 admin POST/PATCH/DELETE 기록
- `audit/` 디렉토리: `ip_blacklist.json`, `ip_permanent_ban.json`, `audit.log`
- 파일에 PII 절대 미기록 (이메일 마스킹 `to_email[:4]+"***"`)

### 2.10 Defense-in-Depth v2.0 (자가 진화)

**T1 예방** — pre-commit
- `bandit -lll -iii` (HIGH 심각도+신뢰도만 차단)
- `pip-audit` (requirements.txt CVE)
- `gitleaks` (시크릿 누출)

**T2 탐지** — Windows 스케줄러 (자동 실행)
- `BRIDGE_IOC_Watcher` (매시간) — AppData .exe / schtasks / Registry 변경 감시 (Quanta Spot 재감염 방어)
- `BRIDGE_Behavior_Check` (매시간) — 엔드포인트 3σ 이탈 탐지
- `BRIDGE_ThreatFeed_Sync` (매일 03:00) — Spamhaus/Firehol 4587 CIDR 갱신
- `BRIDGE_AdminAccess_Monitor` (5분) — admin lockout 자동 감지 + 자가 복구

**T3 대응**
- `kill_switch.py ON|OFF|PANIC` — MAINT=1 환경변수로 모든 mutation 503
- `auto_security_patch.py apply` (매주 월 04:00) — CVE 자동 패치 + 격리 venv 테스트 + smoke test → 실패 시 자동 롤백

**T4 학습** — `.patch_state.json`
- 최근 50회 시도 기록, 동일 major upgrade 3회 실패 시 자동 skip

---

## 3. 결제 시스템 보안 설계

> 현재 BRIDGE 본체에는 결제 미통합. `bridge_ads` (광고 포털)에만 PayPal 키 존재.
> 향후 BRIDGE 본체에 결제 도입 시 아래 설계 적용.

### 3.1 PayPal 통합 원칙
- **PCI-DSS 회피**: 카드 정보 BRIDGE 서버 절대 미저장 — PayPal 호스팅 결제 페이지만 사용
- 클라이언트 → PayPal SDK 직접 결제 → BRIDGE 서버는 결제 ID만 받아 검증
- 환경변수 분리:
  - `PAYPAL_CLIENT_ID` (공개 OK)
  - `PAYPAL_CLIENT_SECRET` (Sensitive — Render env Sensitive ON)
  - `PAYPAL_WEBHOOK_ID` — webhook 서명 검증용
- Sandbox / Live 분리: `PAYPAL_ENV=sandbox|live`

### 3.2 Webhook 서명 검증
```python
# PayPal Webhook 수신 시
1. Header: PAYPAL-AUTH-ALGO, PAYPAL-CERT-URL, PAYPAL-TRANSMISSION-ID/SIG/TIME 추출
2. PayPal API로 검증: POST /v1/notifications/verify-webhook-signature
3. 검증 실패 → 401 즉시 거부 + 로그
4. 검증 성공 + idempotency key (이벤트 ID 중복 방지) 후 처리
```

### 3.3 결제 사기 방어
- 동일 IP 결제 시도 5회/시간 초과 → 24h IP 차단
- 다른 국가 카드 + 한국 학원명 불일치 → 수동 검토 큐
- 결제 금액 < 1000원 또는 > 1억원 → 자동 거부 (오타/사기 방어)
- 환불 요청 → 텔레그램 알림 + 운영자 수동 승인

### 3.4 결제 데이터 보관 (DB 스키마)
```sql
payments(
  id INTEGER PK,
  paypal_order_id TEXT UNIQUE,    -- PayPal 거래 ID
  amount INTEGER,                  -- 원화 (정수)
  currency TEXT DEFAULT 'KRW',
  status TEXT,                     -- pending|completed|refunded
  payer_email_hash TEXT,           -- SHA-256(email) — 평문 미저장
  webhook_verified INTEGER DEFAULT 0,
  created_at TIMESTAMP,
  refunded_at TIMESTAMP
);
```

---

## 4. 백업 & 재해복구

### 4.1 일일 자동 백업 (Windows 스케줄러)
| 태스크 | 시간 | 대상 |
|--------|------|------|
| `BRIDGE_DB_Backup_Daily` | 매일 03:00 | master.db → backups/db_YYYYMMDD.db |
| `BRIDGE_Daily_Backup` | 매일 04:30 | 전체 코드 + .env (암호화) |
| `BRIDGE_GDrive_Backup` | 매일 02:00 | Google Drive 동기화 |
| `BRIDGE_GDrive_Backup_Frequent` | 30분마다 | 핵심 파일만 |

### 4.2 백업 위치 (3-2-1 규칙)
1. **로컬**: `Q:\Claudework\bridge base\backups\` (RAID 미지원)
2. **Render**: `/data/` 영구 디스크 (Render 자체 백업)
3. **클라우드**: Google Drive + ClaudeBlog secrets.enc

### 4.3 시크릿 백업
- `pw.py` 단일 진실 원소스 → `bx` (DPAPI + PIN 이중 암호화)
- `Q:\Claudework\bridge backup\env\` AES-256-GCM (.enc)
- ClaudeBlog `secrets.enc` (자동 동기화)
- Render env-vars API 백업

### 4.4 복구 절차 (RTO 30분, RPO 1일)
```
1. master.db 손상 → backups/db_YYYYMMDD.db 복사
2. .env 손실 → tools/master_vault.py + PIN으로 복호화
3. 코드 손상 → git reset --hard HEAD~N + git push --force-with-lease
4. Render 다운 → render.yaml 기반 30초 재배포
5. Vercel 다운 → 자동 페일오버 (Vercel CDN 다중 리전)
```

---

## 5. 무중단 업데이트 (Zero-Downtime Deploy)

### 5.1 Render Blue-Green
- 신규 배포 빌드 중에도 **이전 인스턴스 계속 서빙**
- 빌드 성공 → health check 통과 → 트래픽 전환
- 빌드 실패 → 자동 롤백 (이전 라이브 그대로)
- autoDeploy: false (`render.yaml`) — push 후 수동 트리거 가능 (또는 Render API)

### 5.2 Vercel Preview Deploy
- 모든 PR → 자동 미리보기 URL
- main push → 프로덕션 즉시 (10초)
- 실패 시 이전 빌드 유지

### 5.3 Health Check 자동 검증
```
1. /health → {"status":"ok","version":"v2.X.X"} 확인
2. /api/public/talents → {"success":true,...} 확인
3. /api/admin/login (probe with fake pw) → "비밀번호가 올바르지 않습니다" 확인
4. 셋 다 통과 → 배포 완료
5. 하나라도 실패 → 자동 git revert + Render 롤백 + 텔레그램 긴급
```
(auto_security_patch.py v2.0 12단계 파이프라인 §2.10)

### 5.4 DB 마이그레이션 안전 패턴
- 컬럼 추가만 (ALTER TABLE ADD COLUMN) — 절대 DROP 안 함
- `_ensure_*` 함수가 startup 시 자동 백필
- 기존 컬럼 의미 변경 금지 → 새 컬럼 추가 후 점진 이전

---

## 6. 모니터링 & 알림

### 6.1 텔레그램 알림 (실시간)
- 로그인 실패 5회 누진
- 신규 후보 등록 / 학원 문의
- 보안 이벤트 (공격 탐지, IP 차단)
- 자동 패치 결과 (성공/실패/롤백)
- IOC 변경 감지

### 6.2 로그 수집
- `logs/access.log` — 모든 요청 (PII 마스킹)
- `logs/audit/audit.log` — admin mutation
- `logs/security_event.log` — 공격 탐지
- `logs/email.log` — 메일 발송 (to_email 마스킹)
- `logs/ioc_watcher.log`, `logs/behavior.log`, `logs/admin_monitor.log`

### 6.3 Render Observability
- Render Dashboard → Logs (실시간 tail)
- Metrics: CPU/메모리/디스크 (free tier 제한)

---

## 7. 사용자 편의성 (UX) — 누락 없이

### 7.1 폼 자동저장
- (TODO) localStorage 임시 저장 — 30초 주기
- 페이지 이탈 경고 (beforeunload)

### 7.2 CAPTCHA 안정성 (최근 개선)
- 3종 랜덤 (slide/rotate/order)
- **한영 병기** 안내 (캔버스 + HINT 영역)
- **새로고침 버튼** — 멈춤 시 즉시 재생성
- 캔버스 기본 배경 다크 슬레이트 (흰 화면 멈춤 방지)
- Order 캡차: 헤더 2행 레이아웃으로 텍스트/도형 가림 해결

### 7.3 제출 버튼 흰색 sweep 애니메이션
- `.btn-shimmer` 전역 클래스 (`globals.css`)
- `::before` pseudo-element + `mix-blend-mode: screen`
- 2.6초 주기 sweep + 휴식
- `I Agree & Continue` / `Submit Application` / `채용 문의 제출` 모두 적용

### 7.4 모바일 최적화
- PWA (manifest.json + service worker)
- Push 알림 (관리자 전용, VAPID)
- 반응형 (Tailwind sm/md/lg breakpoints)

### 7.5 다국어 (현재 부분 적용)
- /apply, /inquiry 한영 병기
- (TODO) 전체 UI 한영 토글

### 7.6 접근성 (WCAG)
- 키보드 내비게이션 가능
- aria-label / role 명시
- 색맹 대응 (정보를 색으로만 전달 금지)

---

## 8. 오픈 차단 요인 (현재) + 오픈 체크리스트

### 8.1 차단 요인 (9개 — 2026-05-12 법적 필수 4개 추가)
| # | 항목 | 상태 | 해결 방법 |
|---|------|------|-----------|
| 1 | 도메인 이관 | ❌ | Vercel → bridgejob.co.kr DNS A 레코드 |
| 2 | 결제 통합 | ❌ | §3 설계대로 PayPal 통합 |
| 3 | 약관/개인정보 검토 | ⚠️ | 변호사 또는 외부 감사 1회 |
| 4 | SEO 메타 | ⚠️ | og-image / sitemap.xml / robots.txt |
| 5 | 부하 테스트 | ❌ | k6 / Locust로 동시 100명 시뮬레이션 |
| 6 | **유료직업소개사업자 등록** | 🔴 | 관할 시·군·구청 등록 (직업안정법 §19, 무허가 영업 불법) |
| 7 | **/fee-disclosure 수수료 공시 페이지** | 🔴 | 한영 병기 (§8.3 템플릿 참조) — 법정 상한 7.5% 명시 |
| 8 | **사업자등록 (유료직업소개업·부가세 면세)** | 🔴 | 국세청 + 세금계산서 발급 시스템 |
| 9 | **90일 보증·재선발 정책 약관** | 🟠 | 분쟁 방지 — 귀책별 환불/재선발 매트릭스 |

> ※ 경쟁사 Korvia(코비아컨설팅) 분석 결과 6~9번 누락 발견. 오픈 전 필수.

### 8.3 /fee-disclosure 페이지 필수 항목 (Korvia 벤치마크)

1. **법인 정보**
   - 상호 / 대표자 / 사업자등록번호
   - 유료직업소개사업자 등록번호 (관할청 발급)
   - 소재지 / 연락처 / 이메일

2. **법정 상한 안내**
   - 직업안정법 시행령 §15 + 고용노동부 「국내유료직업소개요금 등 고시」
   - 3개월 이상 계약 시 구인자 부담 상한: 3개월 임금의 30% 이하 (≈ 연봉 7.5%)
   - **구직자(강사)로부터는 어떠한 비용도 받지 않음** — 직업안정법 §47

3. **기관 유형별 기본 수수료 표**
   ```
   공·사립 학교 (초·중·고)          : ₩________ (또는 연봉 X%)
   어학원 / 영어유치원              : ₩________ 
   국제학교 / 대학교                : ₩________ 또는 1개월 급여
   헤드헌팅 / 특수 프로그램         : 사례별 협의 (연봉 10~15%)
   ```
   ※ 실제 금액은 사업주 결정.

4. **부가 서비스 요금**
   - 면접 대행 / 통역 / 추가 서류 (아포스티유 등) / 긴급 채용 / 커리큘럼 컨설팅

5. **청구 시점 & 결제 수단**
   - 일반: 50% 채용 확정 시 + 50% 입국·근무 개시 후
   - 공공기관: 100% 채용 확정 시 (또는 약정)
   - 계좌이체 / 세금계산서 / 현금영수증 / 나라장터 (공공)

6. **90일 보증 정책 매트릭스**
   ```
   해지 사유                     | 귀책         | 재선발
   ─────────────────────────────|──────────────|─────────
   개인 사유 (가족 등)            | 교사         | 무료
   객관적 업무 능력 부족          | 교사         | 무료
   건강 문제 (불가항력)          | 불가항력     | 무료
   근로조건 불이행 (급여 미지급) | 기관         | 유료
   경영상 필요 (폐업 등)         | 기관         | 유료
   근무환경 문제 (안전·괴롭힘)   | 기관         | 유료
   ```

7. **업무 범위 명시 (파견법 회피 핵심)**
   - "BRIDGE는 모집·선발·채용·체류자격 안내 업무를 수행하며, **파견사업자가 아닙니다.**"
   - "근태 관리·교육 훈련은 채용 기관(고용주)의 책임입니다."

8. **재선발 불가/부분환불 케이스**
   - 타 업체 통해 채용 → 50% 환불
   - 조건 변경 신규 포지션 → 재선발 불가
   - 포지션 폐쇄 → 재선발 불가
   - **주관적 수업 만족도** → 재선발 대상 아님

### 8.2 오픈 체크리스트 (40개)

**[인프라]**
- [ ] bridgejob.co.kr DNS A 레코드 Vercel 가리킴
- [ ] Vercel 도메인 추가 + SSL 자동 발급 확인
- [ ] Render env CORS_ORIGINS 에 `https://bridgejob.co.kr` 포함
- [ ] Render env CORS_ORIGINS 에 `https://www.bridgejob.co.kr` 포함
- [ ] HTTPS 강제 리다이렉트 (Vercel `vercel.json`)
- [ ] HSTS preload 등록 (https://hstspreload.org)

**[보안]**
- [ ] `JWT_SECRET` 64자 무작위 (BRIDGE_FIELD_KEY와 분리 확인)
- [ ] `ADMIN_PASSWORD` pbkdf2 해시 형식 확인
- [ ] `ADMIN_API_KEY` 64자 + Sensitive
- [ ] `BRIDGE_FIELD_KEY` 32자 (T3v1 마스터키)
- [ ] `ADMIN_ALLOWED_IPS` 정확한 관리자 IP
- [ ] Vercel 환경변수 전부 Sensitive ON
- [ ] Render env-vars 전부 검토
- [ ] gitleaks 전체 히스토리 스캔 통과
- [ ] bandit `-lll -iii` 0 issue
- [ ] pip-audit 0 vulnerability
- [ ] `ip_permanent_ban.json` 비어있는지 확인
- [ ] kill_switch OFF 상태 확인

**[데이터]**
- [ ] master.db WAL 모드 확인
- [ ] PII 전수 암호화 검증 (`SELECT email FROM candidates WHERE length(email) < 50 LIMIT 10` → 0건)
- [ ] T3v1 매직바이트 시작 비율 95%+
- [ ] 백업 3-2-1 작동 확인 (로컬+Render+Drive)
- [ ] 일일 백업 스케줄러 실행 로그 점검
- [ ] 복구 리허설 1회 완료

**[UX]**
- [ ] /apply 모바일 + 데스크탑 정상 (한영)
- [ ] /inquiry 동일
- [ ] CAPTCHA 3종 전부 정상 작동
- [ ] CAPTCHA 새로고침 버튼 작동
- [ ] 제출 버튼 shimmer 가시
- [ ] 폼 자동저장 (구현 후)
- [ ] PWA 설치 가능
- [ ] 404 / 500 / 503 페이지 디자인

**[법무/SEO]**
- [ ] /terms 약관 페이지 검토
- [ ] /privacy 개인정보처리방침 검토
- [ ] og-image.png (1200×630)
- [ ] /sitemap.xml 자동 생성
- [ ] /robots.txt (Allow / + 허니팟 Disallow)
- [ ] Google Search Console 등록

**[부하/장애]**
- [ ] k6 부하 100 vus / 1분 — p95 < 2s
- [ ] Render free tier 콜드스타트 30초 대응 (프론트 wake-up 재시도)
- [ ] DB 락 발생 시뮬레이션 → busy_timeout 5000ms 작동
- [ ] 텔레그램 알림 quota 점검 (1초 30msg)
- [ ] Anthropic API quota 초과 시 fallback

**[모니터링]**
- [ ] Uptime monitor (UptimeRobot 무료) 설정
- [ ] Render dashboard 알림 활성
- [ ] 일일 운영 보고 텔레그램 (요약)

---

## 9. 미래지향적 보안 & 확장성

### 9.1 신규 위협 대응 자동화
- **자가 진화 패치** (§2.10 T3) — 매주 월 04:00 pip-audit → 안전 자동 적용
- **위협 인텔 갱신** — 매일 Spamhaus/Firehol 자동 sync
- **악성코드 IOC** — Quanta Spot, KMS 등 알려진 위장 패턴 감시

### 9.2 확장 시 대비
- DB 100만 row 시: PostgreSQL 마이그레이션 경로 (alembic 준비)
- 트래픽 폭증 시: Render Pro 자동 스케일
- 다국가 진출 시: i18n 구조 (next-intl)

### 9.3 AI 시대 보안
- 프롬프트 인젝션 차단: `_attack_scan_middleware` LLM 패턴
- AI 학습 데이터 보호: `robots.txt User-agent: GPTBot Disallow: /`
- 사용자 PII가 LLM에 들어가는 경로 차단: 메일/이력서 본문 전처리

### 9.4 Compliance
- GDPR (유럽 사용자 — 거의 없지만 대비)
- 한국 개인정보보호법 — 동의 + 보유기간 + 파기절차
- 미국 CAN-SPAM — 이메일 발송 시 unsubscribe 링크

---

## 10. 운영 일상 — 매일 1줄 점검

```bash
# 매일 점검 1줄 (텔레그램으로 자동 보고됨)
python tools/team_status.py
```

출력 예시:
```
✅ Render: live v2.3.2 (commit abc1234, 12h ago)
✅ Vercel: ready (last push 3h ago)
✅ DB: 3134 cand / 1239 inq / 2299 jobs
⚠️  IOC: 1 새 schtasks (검토 필요)
✅ Backups: 03:00 OK
✅ Schedulers: 9/9 작동
✅ Lockout: 없음
```

---

## 11. 절대 건드리면 안 되는 것

- `/data/master.db` (Render 영구 디스크) — 이동/삭제/hard-delete 금지
- `BRIDGE_FIELD_KEY` (PII 마스터키) — 변경 시 기존 데이터 전부 복호화 후 재암호화 필수
- `EarthGlobe.tsx` HERO 애니메이션
- CLAUDE.md IMMUTABLE CORE 섹션
- `is_deleted=1` → 절대 hard DELETE 아님 (논리 삭제만)

---

## 12. 마누스 점검 모드 — 진단 명령어 (read-only)

마누스가 BRIDGE를 분석할 때 실행할 안전한 명령들:

```bash
# 1. 시스템 상태
curl -sH "User-Agent: Mozilla/5.0" https://bridge-n7hk.onrender.com/health
curl -sH "User-Agent: Mozilla/5.0" -o /dev/null -w "%{http_code}" https://bridge-chi-lime.vercel.app/

# 2. 보안 헤더 검사
curl -sIH "User-Agent: Mozilla/5.0" https://bridge-n7hk.onrender.com/ | grep -iE "strict-transport|x-content|x-frame|csp"

# 3. 코드 보안 스캔 (로컬)
"Q:/Phtyon 3/Scripts/bandit.exe" -ll -iii Q:/Claudework/bridge base/api_server.py
"Q:/Phtyon 3/Scripts/pip-audit.exe" -r Q:/Claudework/bridge base/requirements.txt

# 4. 침투 시뮬레이션 (비파괴 12개 시나리오)
"Q:/Phtyon 3/python.exe" -X utf8 Q:/Claudework/bridge base/tools/penetration_test.py

# 5. 백업 상태
ls -lh Q:/Claudework/bridge base/backups/ | tail -10

# 6. 스케줄러 가동 확인
schtasks /query /fo TABLE | grep BRIDGE_

# 7. DB 무결성
"Q:/Phtyon 3/python.exe" -c "import sqlite3; c=sqlite3.connect('Q:/Claudework/bridge base/master.db'); print(c.execute('PRAGMA integrity_check').fetchone())"
```

### 마누스 점검 기준 (체크리스트 — 12개 영역)

각 항목에 대해 **OK / WARN / FAIL** 판정 + 근거:

1. [ ] **인프라** — Render/Vercel 정상, DNS 정상
2. [ ] **인증** — 세션 토큰 + 화이트리스트 면역 작동
3. [ ] **암호화** — T3v1 적용율 95%+
4. [ ] **속도제한** — 5계층 작동 (미들웨어/엔드포인트)
5. [ ] **봇방어** — 허니팟 + CAPTCHA + UA 필터
6. [ ] **공격탐지** — SQLi/XSS/SSRF 패턴 매칭
7. [ ] **감사로그** — PII 마스킹 + 영구보관
8. [ ] **백업** — 3-2-1, 일일 자동
9. [ ] **무중단** — Blue-Green + 자동 롤백
10. [ ] **모니터링** — 9개 스케줄러 + 텔레그램
11. [ ] **UX** — 폼/CAPTCHA/shimmer 정상
12. [ ] **법무** — 약관/개인정보 작성됨

---

## 13. 변경 이력 / 의사결정 기록 (ADR)

이 문서를 변경할 때마다 아래 추가:

- 2026-05-11: 최초 작성 (BRIDGE 전체 시스템 SSOT 확립)

---

## 14. 마지막 — 단 하나도 누락 금지 원칙

이 문서가 누락하는 것 = BRIDGE 운영의 사각지대.
새 기능/도구/위협이 생기면 **즉시 이 문서 갱신**.
지속적 진화가 BRIDGE 보안의 핵심.

> "Security is not a state. It is a continuous process."

---

## 부록 A. 환경변수 전체 목록 (Render BRIDGE)

```
ADMIN_API_KEY              ★ 관리자 API 키 (64자)
ADMIN_PASSWORD             ★ pbkdf2 해시
ADMIN_ALLOWED_IPS          관리자 IP CIDR
ANTHROPIC_API_KEY          LLM
BRIDGE_FIELD_KEY           ★ T3v1 마스터키 (32자)
BRIDGE_HMAC_KEY            ★ HMAC 서명
BRIDGE_SMTP_PASS           SMTP
CORS_ORIGINS               허용 도메인 콤마 구분
EMAIL_FROM
ENV=production
JWT_SECRET                 ★ 세션 토큰 서명 (BRIDGE_FIELD_KEY와 분리)
NAVER_SMTP_PASS            네이버 SMTP
RATE_LIMIT_*               엔드포인트별
RENDER_API_KEY             (배포 트리거용)
SECURITY_MODE=strict
SMTP_USER
TELEGRAM_BOT_TOKEN         운영 알림
UPLOAD_SIGN_KEY            파일 서명
WEBHOOK_SECRET             웹훅 서명

# 결제 통합 후 추가될 변수
PAYPAL_CLIENT_ID
PAYPAL_CLIENT_SECRET       ★ Sensitive
PAYPAL_WEBHOOK_ID
PAYPAL_ENV=sandbox|live
```

★ = Sensitive (절대 노출 금지, Vercel/Render 모두 Sensitive 토글 ON)

## 부록 B. 주요 파일 책임 (1줄 요약)

| 파일 | 책임 |
|------|------|
| `api_server.py` | FastAPI 서버, 202 endpoints, 모든 admin 로직 |
| `security_middleware.py` | 10계층 미들웨어 (IP/Rate/CSRF/UA/공격패턴) |
| `security_vault.py` | T3v1 3중 암호화 (encrypt_field/decrypt_field) |
| `email_templates.py` | Naver/Gmail SMTP 발송 + PII 마스킹 |
| `inbox_api.py` | 학원 문의 자동응답 라우터 |
| `push_api.py` | PWA Push 알림 (관리자) |
| `tools/pw.py` | 크리덴셜 단일 진실 원소스 GUI |
| `tools/bx.py` | DPAPI+PIN 이중 암호화 저장소 |
| `tools/admin_access_monitor.py` | 5분 자가 복구 |
| `tools/auto_security_patch.py` | 주간 자동 패치 |
| `tools/ioc_watcher.py` | Quanta Spot 재감염 감시 |
| `tools/threat_feed.py` | Spamhaus/Firehol 위협 인텔 |
| `tools/penetration_test.py` | 12개 공격 비파괴 시뮬레이션 |
| `tools/kill_switch.py` | 긴급 차단 ON/OFF/PANIC |
| `tools/bridge_backup.py` | 작업 전후 자동 백업 |
| `web_frontend/src/app/apply/ApplyForm.tsx` | 강사 지원 3단계 |
| `web_frontend/src/app/inquiry/InquiryForm.tsx` | 학원 문의 3단계 |
| `web_frontend/src/components/PuzzleCaptcha.tsx` | 3종 랜덤 캡차 |
| `web_frontend/src/context/AdminAuthContext.tsx` | 관리자 세션 |

## 부록 C. 핵심 엔드포인트 카탈로그 (202개 중 운영 필수 30개)

```
[공개]
GET  /health                           ← 상태 확인
GET  /api/public/talents               ← 인재 목록 (PII 차단)
GET  /api/public/jobs                  ← 공개 채용공고
POST /api/apply                        ← 강사 지원
POST /api/inquiry                      ← 학원 문의

[관리자 인증]
POST /api/admin/login                  ← 로그인 (세션 발급)
GET  /api/admin/key                    ← API 키 조회 (세션 토큰 필요)
POST /api/admin/logout
GET  /api/admin/sessions
DELETE /api/admin/sessions/{id}

[관리자 데이터]
GET  /api/admin/candidates             ← 후보 목록 (페이지네이션)
GET  /api/admin/candidates/{id}
PATCH /api/admin/candidates/{id}
GET  /api/admin/candidates/export      ← CSV/XLSX (일 10회 제한)
GET  /api/admin/inquiries              ← 학원 문의 (인메모리 복호 검색)
PATCH /api/admin/inquiries/{id}
GET  /api/admin/jobs/v2

[파일]
POST /api/upload/{entity}/{id}         ← 후보=apply_token / 관리자=admin
GET  /api/admin/candidates/{id}/processed-cv
GET  /api/admin/sign-url

[메일]
POST /api/admin/mail/introduce         ← 학원에 강사 추천 발송
GET  /api/admin/mail/introduce-log

[운영]
POST /api/admin/reset-blacklist        ← IP 일시+영구 청소
GET  /api/admin/dashboard              ← 전체 통계
GET  /api/admin/db/dump                ← DB SQL 백업
```

---

# 끝.
이 프롬프트로 BRIDGE를 처음 보는 누구든 30분 안에 전체 그림을 잡을 수 있도록 설계됨.
누락 발견 시 **즉시 이 문서 갱신** — 그것이 BRIDGE 보안의 핵심.
