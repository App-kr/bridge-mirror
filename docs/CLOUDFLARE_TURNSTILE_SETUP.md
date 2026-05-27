# Cloudflare Turnstile 설정 가이드

## 왜 Turnstile?
- **무료 무제한** — Cloudflare 계정만 있으면 됨
- **봇 99% 차단** — 산업 표준 검증
- **invisible 위주** — 대부분 사용자는 퍼즐 안 풀어도 됨
- 기존 PuzzleCaptcha의 봇 우회 가능성 해결

## 5분 설정 (한 번만)

### 1. Cloudflare 계정 + 사이트 등록
1. https://dash.cloudflare.com/ 가입 (무료)
2. 좌측 메뉴 → **Turnstile** 클릭
3. **Add site** → 이름: `bridgejob`, 도메인: `bridgejob.co.kr` 와 `bridge-chi-lime.vercel.app` 추가
4. Widget Mode: **Managed** (권장)
5. **Create** → SITE_KEY, SECRET_KEY 발급됨

### 2. Vercel 환경변수 추가 (프론트)
```bash
# Vercel 대시보드 → Settings → Environment Variables
NEXT_PUBLIC_TURNSTILE_SITE_KEY=0x4AAAAAAAxxxxxxxxxxxxxx
```
- Production / Preview / Development 모두 체크
- 저장 후 재배포 (Deployments → 최신 → Redeploy)

### 3. Render 환경변수 추가 (백엔드)
```bash
# Render 대시보드 → bridge-n7hk → Environment
TURNSTILE_SECRET_KEY=0x4AAAAAAAxxxxxxxxxxxxxxxxxxxxxx
```
- Save → 자동 재배포

### 4. 검증
- https://bridge-chi-lime.vercel.app/apply 접속
- 폼 작성 후 CAPTCHA 영역에 Cloudflare 위젯 표시 확인
- 대부분 자동 통과 (체크 안 해도 됨)
- 의심스러운 트래픽일 때만 챌린지 노출

## 환경변수 미설정 시
- 기존 PuzzleCaptcha 폴백 자동 동작 (서비스 중단 없음)
- 단, **봇 우회 가능 상태 유지** → 가급적 빠른 설정 권장

## 보안 검증 항목
- ✅ 서버 측 HTTP 검증 (challenges.cloudflare.com/turnstile/v0/siteverify)
- ✅ 토큰 1회용 마킹 (replay 차단)
- ✅ API 실패 시 fail-closed (검증 통과 금지)
- ✅ 토큰 길이 검증 (20~2048자)
- ✅ 5초 타임아웃 (서버 행 방지)

## 트러블슈팅
- **위젯 안 보임**: 브라우저 콘솔 → `challenges.cloudflare.com` 차단 여부 확인
- **항상 검증 실패**: SITE_KEY/SECRET_KEY 페어 불일치 확인 (Cloudflare 대시보드에서 재생성)
- **퍼즐 항상 뜸**: Cloudflare 대시보드 → Site → Widget Mode `Managed`로 설정
