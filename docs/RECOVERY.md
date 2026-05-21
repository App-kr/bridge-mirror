# BRIDGE 재난복구 RUNBOOK (Disaster Recovery)

> 마지막 검증: 2026-05-22
> 이 문서대로 따라하면 Claude AI 없이도 모든 시스템 복구 가능

---

## 1. 시스템 구성 한눈에

| 컴포넌트 | 위치 | 백업 위치 | 자동 복구 |
|---|---|---|---|
| **메인 백엔드** | Render `BRIDGE` (srv-d6imvn1aae7s73ck5570) | App-kr/bridge-mirror (GitHub) | ✅ autoDeploy=yes |
| **메인 프론트엔드** | Vercel `bridge` project | App-kr/bridge-mirror (GitHub) | ⚠️ **Git 재연결 필요** |
| **광고 결제** | Render `bridge-ads` + Vercel ads | koreadobby/bridge-ads (GitHub) | ✅ autoDeploy=no (수동 deploy) |
| **DB (master.db)** | Render `BRIDGE` ephemeral disk | Google Drive `BRIDGE_DB_BACKUPS` (7개 보관) | ✅ startup 시 _CRITICAL_LOSS 조건에서 자동 restore |
| **시크릿/크리덴셜** | bx (DPAPI+PIN 암호화) on Scarlett PC | Q:/Claudework/.vault/ | ⚠️ Scarlett PC 의존 |

### 도메인
- `bridgejob.co.kr` → `bridge-chi-lime.vercel.app` (Vercel)
- `bridge-n7hk.onrender.com` (백엔드 API)
- `bridge-ads.onrender.com` (광고 결제 백엔드)

---

## 2. 일상 백업 (자동)

### 매일 03:00 KST — 메인 DB Google Drive 백업
- 스케줄러: `BRIDGE_DB_Backup_Daily` (Windows Task Scheduler)
- 명령: `Q:/Phtyon 3/pythonw.exe -X utf8 Q:/Claudework/bridge base/tools/db_persist.py backup`
- 백업 위치: Google Drive `BRIDGE_DB_BACKUPS` 폴더
- 보존: 최근 7개 (MAX_KEEP=7, 일주일치)
- 검증: `python tools/db_persist.py status`

### 메인 코드 — git push 시 자동
- Local: Q:/Claudework/bridge base (워크스테이션)
- Remote: `App-kr/bridge-mirror` (GitHub, public)
- Render: webhook autoDeploy=yes → 새 commit 감지 시 자동 빌드

### 광고 코드 — git push 시 (수동 deploy)
- Local: Q:/Claudework/bridge_ads
- Remote: `koreadobby/bridge-ads` (GitHub, private)
- Render: autoDeploy=no → 수동 deploy 필요

---

## 3. 복구 시나리오

### 시나리오 A: Render 백엔드 다운
1. https://dashboard.render.com → BRIDGE 서비스
2. **Manual Deploy → Deploy latest commit** 클릭
3. ~5분 후 https://bridge-n7hk.onrender.com/ HTTP 200 확인

### 시나리오 B: Vercel 프론트엔드 빌드 실패
**현재 Vercel project (`bridge`) 의 git 연결이 깨져있음** — 자동 deploy 안 됨.

수동 deploy 방법:
```bash
cd "Q:/Claudework/bridge base/web_frontend"
# 1) Vercel 프로젝트의 rootDirectory를 임시로 null 처리
#    (https://vercel.com/koreadobbys-projects/bridge/settings/general → Root Directory → 비우기)
# 2) CLI deploy
vercel --prod --yes --scope koreadobbys-projects --archive=tgz
# 3) rootDirectory를 'web_frontend'로 복원
```

**Git 자동 deploy 영구 복구** (권장):
- Vercel Settings → Git Integration
- 새 repo 연결: `App-kr/bridge-mirror` 또는 새로 만든 `koreadobby/bridge`
- 사전 작업: GitHub Settings → Applications → Vercel app 을 해당 organization에 설치

### 시나리오 C: master.db 손실 (DB 비어있음)
Render 백엔드 자동 복구:
- `_CRITICAL_LOSS` 조건 (candidates < 100 또는 핵심 테이블 비어있음) 감지 시
- `DRIVE_OAUTH_TOKEN_JSON` 환경변수로 Drive 인증
- `tools/db_persist.py:restore()` 호출 → 최신 Drive 백업 자동 다운로드 + 복원

수동 복구 (필요 시):
```bash
cd "Q:/Claudework/bridge base"
"Q:/Phtyon 3/pythonw.exe" -X utf8 tools/db_persist.py restore
```

### 시나리오 D: App-kr/bridge-mirror repo 삭제됨
1. 로컬 작업 디렉토리에서 새 repo 생성:
   ```bash
   cd "Q:/Claudework/bridge base"
   gh repo create <owner>/<name> --public --source=. --push
   ```
2. Render Service Settings → Build & Deploy → Repository URL 변경
3. Render Manual Deploy 트리거

### 시나리오 E: GitHub 전체 계정 잠김 (App-kr + koreadobby + dobby-kr)
1. 로컬 master 파일 Q:/Claudework/bridge base 에 그대로 존재
2. Google Drive에 DB 백업 7일치 보관
3. 새 계정 / Bitbucket / GitLab 으로 마이그레이션:
   ```bash
   cd "Q:/Claudework/bridge base"
   git remote add new <new-remote-url>
   git push new main --tags
   ```
4. Render / Vercel 의 source repo 갱신

### 시나리오 F: Scarlett PC 손실 (워크스테이션 망가짐)
- 코드: GitHub `App-kr/bridge-mirror` clone
- DB: Google Drive `BRIDGE_DB_BACKUPS` → `db_persist.py restore`
- 크리덴셜:
  - **재발급 필요**: bx vault는 DPAPI+PIN 으로 PC에 종속 → 새 PC에선 복호화 불가
  - 각 서비스 (Anthropic, OpenAI, Render, Vercel, GitHub) 토큰 재발급
  - `pw.py` 실행 → 새 토큰 입력 → bx 재구성

---

## 4. 핵심 자격증명 (재발급 가능 여부)

| 자격 | 저장 위치 | 재발급 |
|---|---|---|
| Anthropic API | bx | console.anthropic.com → API Keys |
| Render API | bx | dashboard.render.com → Account Settings → API Keys |
| Vercel CLI Token | %APPDATA%/com.vercel.cli/Data/auth.json | vercel.com → Settings → Tokens |
| GitHub PAT | gh CLI keyring | github.com → Settings → Developer settings → PAT |
| BRIDGE_FIELD_KEY (DB 암호화) | Render env var | ⚠️ 분실 시 암호화 PII 복호화 불가 → 별도 안전 보관 필요 |
| BRIDGE_HMAC_KEY | Render env var | 분실 시 → 새 키 생성 + Vercel 프론트 서명 코드 갱신 |
| JWT_SECRET | Render env var | 분실 시 → 새 키 생성 + 모든 활성 세션 무효화 |

> **CRITICAL**: `BRIDGE_FIELD_KEY` 는 candidates 테이블의 PII (이름/이메일/전화/카톡 등) AES-256-GCM 암호화 키. 분실 시 복호화 불가 영구 손실. **반드시 Render dashboard 외 안전한 곳(bx vault, 종이 메모, 비밀번호 매니저) 에 별도 보관 필수**.

---

## 5. 현재 알려진 결함 (TODO)

### 1. Vercel 자동배포 끊김 ⚠️
- 원인: Vercel project가 `koreadobby/bridge` 가리킴 (deleted)
- 임시 해결: CLI 수동 deploy (시나리오 B 참고)
- 영구 해결: GitHub OAuth로 Vercel app을 App-kr 또는 새 koreadobby org에 설치 → repo 재연결

### 2. App-kr/bridge-mirror 가 PUBLIC ⚠️
- 원인: Render 의 GitHub App이 App-kr 에 미설치 → public repo 만 fetch 가능
- 해결: GitHub Settings → Applications → Render → "App-kr" organization 에 install
- 그 후 repo private 전환 가능

### 3. BRIDGE_GDrive_Backup_Frequent task 실패 중
- daily 백업 (BRIDGE_DB_Backup_Daily, 03:00) 은 정상 동작 → 1일 손실 한계
- 6시간 단위 (Frequent) 는 -2147020576 에러 — 별도 디버깅 필요 시 처리

---

## 6. 헬스 체크 (1분 점검)

```bash
# 백엔드
curl -sS -o /dev/null -w "Render BRIDGE: %{http_code}\n" https://bridge-n7hk.onrender.com/
curl -sS -o /dev/null -w "Vercel front: %{http_code}\n" https://bridge-chi-lime.vercel.app/
curl -sS -o /dev/null -w "bridge-ads: %{http_code}\n" https://bridge-ads.onrender.com/

# DB 통계
curl -sS https://bridge-n7hk.onrender.com/api/testimonials?limit=1 | head -c 80

# Drive 백업 상태
"Q:/Phtyon 3/pythonw.exe" -X utf8 tools/db_persist.py status
```

기대 응답:
- 모두 HTTP 200
- testimonials total=100
- Drive: 7개 백업, 가장 최근 < 24시간 이내

---

## 7. 연락처

- 본인 (Scarlett): koreadobby@gmail.com
- bx 비밀 PIN: 본인만 알고 있음 (재설정 불가 — 분실 시 vault 영구 잠금)
