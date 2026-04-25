# Render Free Cold Start 차단 — cron-job.org 핑 설정

## 목적
Render Free 플랜은 15분 무활동 시 sleep → 첫 요청 시 cold start 30~60초 지연.
외부 무료 서비스로 14~20분마다 `/api/health` 핑 → 절대 sleep 안 함.

## 비용
0원. cron-job.org 무료 플랜 = 월 50개 작업 / 1분 단위 가능.

## 한도 주의
Render Free = 750hr/월. 24/7 가동 시:
- 30일달 = 720hr → 30hr 여유 ✅
- 31일달 = 744hr → 6hr 여유 ⚠️
→ **20분 간격** 권장 (하루 3hr sleep 허용 → 31일달 안전)

---

## 설정 절차

### 1) 가입
https://cron-job.org/ → Sign up (이메일만)

### 2) Cronjob 생성
**Create cronjob** 버튼:

| 필드 | 값 |
|------|----|
| Title | `BRIDGE Render Keepalive` |
| URL | `https://bridge-n7hk.onrender.com/api/health` |
| Schedule | Every 20 minutes |
| Enabled | ✅ |
| Save responses | (선택) Last 10 |
| Notifications | Failure only |

### 3) 검증
- 저장 후 "Run now" 클릭 → HTTP 200 + `{"status":"ok",...}` 응답 확인
- Render 대시보드에서 활동 로그 확인

---

## 백엔드 측 준비 (이미 존재 가능 — 확인 필요)

`/api/health` 엔드포인트 부재 시 추가:
```python
@app.get("/api/health")
def health():
    return {"status": "ok", "ts": int(time.time())}
```
이미 있으면 작업 0.

---

## 대안 (cron-job.org 외)

| 서비스 | 무료 한도 | 비고 |
|--------|----------|------|
| **cron-job.org** | 50 jobs / 분 단위 | 추천 (가장 무료·안정) |
| UptimeRobot | 50 monitors / 5분 단위 | 모니터링 겸용 |
| GitHub Actions | 무제한 (무료 계정 2000분/월) | cron 정확도 낮음 |
| Cloudflare Workers Cron | 100k req/일 | 코드 작성 필요 |

---

## 비활성화

- 트래픽 충분 → 자연 sleep 안 함 → 핑 불필요
- Render Starter $7/월 전환 → sleep 없음 → 핑 불필요

cron-job.org 대시보드에서 Disable 토글만.
