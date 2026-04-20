# ad_only/ — 광고 전용 잠금 폴더

## 목적
RPA / ESL / Teast 자동 광고 시스템이 **master.db, client_inquiries, 업체 메모, 연락처 등 개인정보에 접근하는 경로를 차단**합니다.

## 단일 진실 공급원
```
original_jobs/BRIDGE_clients_jobs.txt   (원본 — 업체명·연락처 포함)
            ↓ make_clean_jobs.py        (수동 정제)
original_jobs/JOBS_CLEAN.txt
            ↓ sync_from_source.py       (수동 복사)
ad_only/jobs_clean.txt                  ← RPA/ESL/Teast 는 여기만 읽음
            ↓ loader.py (자동 파싱+캐시)
ad_only/jobs_clean.json
```

## 규칙 (LOCKED)
1. **RPA/ESL/Teast 는 `ad_only.loader` 외의 데이터 소스 import 금지**
2. 로드된 모든 필드는 `pii_guard.assert_clean()` 통과 필수 (fail-closed)
3. 원본 파일이 PII 오염되면 → `PIIContaminationError` → 광고 전체 중단
4. 이 폴더 밖 경로를 읽는 import 추가 금지 (코드리뷰 차단)

## 금지 접근 경로 (절대 import 하지 말 것)
- `master.db` 에서 `jobs`, `client_inquiries`, `candidates` 테이블
- `original_jobs/BRIDGE_clients_jobs.txt` 원본 (PII 포함)
- `eslcafe_manager/jobs/jobs_default.json` 직접 → loader 경유
- Employer 관련 API endpoint

## 허용 접근
- `ad_only/jobs_clean.txt`
- `ad_only/jobs_clean.json` (캐시)
- `ad_only.loader` 공개 함수
- `ad_only.pii_guard` 공개 함수

## 사용 예
```python
# OK — 권장 패턴
from ad_only.loader import select_jobs, render_ad_block
jobs = select_jobs(limit=8, future_only=True)
for j in jobs:
    body = render_ad_block(j)
    print(body)

# NG — 금지
import sqlite3
conn = sqlite3.connect('master.db')  # 보안 위반
```

## 갱신 방법 (보스 전용)
```bash
# 원본 수정 후
python Q:/Claudework/bridge\ base/ad_only/sync_from_source.py

# 검증
python Q:/Claudework/bridge\ base/ad_only/loader.py
```

## 자체 테스트
```bash
# PII guard 자가진단
python Q:/Claudework/bridge\ base/ad_only/pii_guard.py

# loader 재파싱 + 캐시 갱신
python Q:/Claudework/bridge\ base/ad_only/loader.py
```

## 위반 시 동작
- 로더가 PII 감지 시: `PIIContaminationError` 발생 → 광고 포스팅 전체 중단
- fail-closed 설계: "에러 나면 광고 안 나감" > "조용히 PII 노출"
