# 🌉 BRIDGE — Master Deployment Guide
> Obsidian & Antigravity 입력용 전체 정리 문서
> 생성일: 2026-02-27

---

## 🔴 이 채팅 계속 vs 새 채팅?

**이 채팅 계속을 추천합니다.** 이유:
1. 전체 DB 스키마, 암호화 키, 코드 히스토리가 이 세션에 존재
2. 새 채팅 시 → 컨텍스트 유실 → 처음부터 설명 필요
3. 단, **이 문서를 Obsidian에 저장**한 뒤 새 채팅에서 이 문서를 업로드하면 이어갈 수 있음

**Antigravity에 입력할 때:**
이 `.md` 파일 + `bridge_site.py` + `bridge_core/` 폴더를 통째로 전달

---

## 📋 전체 대화 요약 (Phase 1~6)

### Phase 1: Core Infrastructure
- AES-256 암호화 엔진 (`crypto_engine.py`)
- SQLite DB + WAL 모드 (`db_manager.py`)
- 감사 로그 시스템 (`audit_logger.py`)
- 오프라인 큐 (`offline_queue.py`)

### Phase 2: Admin Dashboard
- Streamlit 관리자 대시보드
- 구직자/구인자/잡 CRUD
- PII 블러 보호

### Phase 3: Newsletter Automation
- 이메일 인프라 (Gmail SMTP → SES → SendGrid 티어)
- 뉴스레터 자동 발송

### Phase 4: Employer Intake + Interview
- 구인자 접수 자동화
- Google Meet 인터뷰 생성
- 인터뷰 안내 이메일

### Phase 5: Smart Search + Email Infrastructure
- 25ms 타입어헤드 검색
- 티어드 SMTP 구조

### Phase 6: Web Admin + Public Website (현재)
- 독립 Python 웹서버 (zero deps)
- Apple 스타일 공개 홈페이지
- DB 연동 잡보드
- 게시판 CMS (About/Korea/Visa/Support/Tips)
- 구직자/구인자 접수 폼 (Google Form 필드 반영)
- 관리자 대시보드

---

## 🏗 실제 배포 절차

### Step 1: 서버 준비
```bash
# Vultr/DigitalOcean/AWS Lightsail ($5/월)
# Ubuntu 24.04 LTS 선택
# SSH 접속
ssh root@your-server-ip
```

### Step 2: 코드 업로드
```bash
# 로컬에서 서버로 전송
scp -r bridge_demo/ root@your-server-ip:/opt/bridge/
```

### Step 3: Python 환경
```bash
apt update && apt install -y python3 python3-pip nginx certbot
cd /opt/bridge
python3 bridge_site.py &  # 테스트 실행
```

### Step 4: systemd 서비스 등록
```bash
cat > /etc/systemd/system/bridge.service << 'EOF'
[Unit]
Description=BRIDGE Website
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/bridge
ExecStart=/usr/bin/python3 /opt/bridge/bridge_site.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable bridge
systemctl start bridge
```

### Step 5: Nginx + SSL
```bash
cat > /etc/nginx/sites-available/bridge << 'EOF'
server {
    server_name bridgejob.co.kr www.bridgejob.co.kr;
    listen 80;
    location / { proxy_pass http://127.0.0.1:8501; proxy_set_header Host $host; }
}
EOF

ln -s /etc/nginx/sites-available/bridge /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# SSL (Let's Encrypt)
certbot --nginx -d bridgejob.co.kr -d www.bridgejob.co.kr
```

### Step 6: 도메인 DNS 설정
```
bridgejob.co.kr → A Record → VPS IP
www.bridgejob.co.kr → CNAME → bridgejob.co.kr
```

### Step 7: 관리자 접속
```
https://bridgejob.co.kr/admin
Password: bridge2026!admin (배포 후 즉시 변경!)
```

---

## 📁 파일 구조

```
/opt/bridge/
├── bridge_site.py          ← 메인 서버 (공개+관리자)
├── bridge_core/
│   ├── config.py           ← DB/키 경로 설정
│   ├── crypto_engine.py    ← AES-256
│   ├── db_manager.py       ← DB CRUD
│   ├── db_schema.py        ← 테이블 스키마
│   └── audit_logger.py     ← 감사 로그
├── bridge_interview/
│   ├── interview_automation.py
│   └── email_infra.py      ← SMTP 발송
├── bridge_newsletter/
│   └── newsletter_manager.py
├── bridge_employer_intake/
│   └── employer_intake.py
└── /root/bridge_data/       ← 데이터 (별도 경로)
    ├── db/master.db         ← SQLite DB
    ├── keys/master.key      ← 암호화 키
    └── logs/                ← 로그
```

---

## 🗄 DB 테이블 요약

| 테이블 | 용도 | 현재 |
|--------|------|------|
| jobseekers | 검증된 구직자 | 60명 |
| employers | 검증된 구인자 | 25개 |
| jobs | 활성 채용공고 | 25개 |
| interviews | 인터뷰 기록 | 0 |
| applications | 웹 접수 원본 | 신규 |
| board_posts | 게시판 | ~15개 |
| payments | 결제 기록 | 신규 |
| audit_log | 감사 로그 | 활성 |
| newsletter_log | 발송 기록 | 활성 |
| system_meta | 시스템 설정 | 활성 |

---

## 📰 기존 bridgejob.co.kr 게시물 이전 목록

### Visa 게시판 (스크린샷 기준)
1. Immigration Hi Korea Guide (하이코리아 출입국 안내)
2. 외국인 등록증 이름 변경 및 갱신 안내 (Name Change & ARC Renewal)
3. Non-F Visa Holders Preparing to Leave Korea
4. E-2 비자 고용 변동 가이드 / E-2 Visa Transfer Guide
5. 해외→국내 서류발송 후 준비 / After receiving VIN from Korea
6. Degree and clean criminal record required (학위/범죄기록 공통)
7. Notarization and Apostille for Australian Degree & Criminal Record (호주서류)
8. New Zealanders applying for an E2 visa (뉴질랜드 서류)
9. UK, Korea Visa Application Center (KVAC) in London (영국비자발급소)
10. UK Criminal Background Check (영국범죄)

### Support 게시판 — 공지 및 서류 안내
1. [BRIDGE] 인력소개 서비스 기본안내
2. 각종 비자에서 E비자로 변경하기 / How to change visas to an E visa
3. 원어민 강사 체류/등록 신고 및 변경 기본 가이드
4. 원어민 강사 영어회화보조강사 해외초청 절차
5. 근로소득 입증서류 종류 / 소득 자료 제출 가이드
6. 사업장 등록 및 추가 근무 절차 안내
7. 계약한 강사가 근무 시작 후 갑자기 이탈했습니다
8. 동반(F-3) 비자 비자 안내: 배우자를 한국의 E비자로 초청하기
9. 원어민 사증발급인정신청서는 온라인으로 신청이 가능합니다
10. 외국인근로자 표준근로계약서
11. 원어민 강사 초청 후 다시 한번 확인해 주세요
12. 원어민 채용이 처음이신가요?
13. 외국인 근로자 고용변동 등 신고 안내
14. 임금명세서 교부 의무와 관련 안내
15. 해외입국자 입국 전 코로나19 음성확인서 제출 및 격리면제서 발급 중단

### Support 게시판 — Information and Documents (EN)
1. How to change from various visas to an E visa
2. Work Experience Certificate Guide (경력증명서 발급가이드)
3. Foreign English Teacher Accommodation Guide (숙소관련)
4. Immediate Information Disclosure Request (즉시정보공개청구)
5. Bridge Agency Preparation Guide
6. Foreign Employee Workplace Change Notification
7. Education Office Registration Documents (교육청 등록 서류)
8. Essential Tasks for Teachers Upon Arrival (한국 입국 후 기본)
9. Renewing ARC for New Employment
10. FBI Background Check Overseas (범죄조회/해외거주)
11. F4/F6 visa holders who wish to teach
12. South African Health examination (남아공 검진)
13. Guide to Extending Stay for Registered Foreigners (체류기간연장)
14. Change of Residence Report (ARC홀더 거주지변경신고)
15. Guide to Notarizing and Apostilling Degree Documents for E-2 Visa

---

## 🎯 다음 할 일 (TODO)

### 오늘 완료해야 할 것
- [ ] `bridge_site.py` 서버에 구인자 폼 전필드(Google Form) 반영
- [ ] 접수 확인 이메일 발송 로직 통합
- [ ] Visa/Support 게시판에 기존 게시물 30개+ 이전
- [ ] 게시판 UI 개선 (제목 강조, 첨부파일, 안내문)
- [ ] VPS 서버 구매 + 도메인 연결 + SSL
- [ ] DNS 변경 (bridgejob.co.kr → 새 서버)

### 향후
- [ ] Stripe/PayPal 결제 연동
- [ ] 파일 업로드 (CV, 사진, 사업자등록증)
- [ ] Google Analytics 연동
- [ ] SEO 최적화 (sitemap.xml, meta tags)
- [ ] 모바일 앱 (PWA)

---

## 🔑 관리자 접근 정보

| 항목 | 값 |
|------|-----|
| URL | http://localhost:8501/admin |
| Password | bridge2026!admin |
| DB 경로 | /root/bridge_data/db/master.db |
| 암호화 키 | /root/bridge_data/keys/master.key |
| 이메일 | bridgejobkr@gmail.com |
| 사업자번호 | 113-94-14997 |

---

## ⚠️ 보안 체크리스트 (배포 전)
- [ ] 관리자 비밀번호 변경
- [ ] /admin 경로 IP 제한 (Nginx)
- [ ] HTTPS 필수 (Let's Encrypt)
- [ ] DB 백업 자동화 (cron)
- [ ] master.key 별도 보관 (서버+로컬 이중)
- [ ] 방화벽 설정 (ufw allow 80,443)
