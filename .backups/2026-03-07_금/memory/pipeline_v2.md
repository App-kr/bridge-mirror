# Bridge Data Pipeline v2 (웹 자립)

## 메인 경로 (운영)
웹 /apply → POST /api/apply → DB INSERT (즉시)
→ admin/candidates에서 관리
→ PII 암호화 (AES-256-GCM, BRIDGE_FIELD_KEY)

## 백업 경로 (이중 안전)
DB → Google Sheet 동기화 (향후 구현, 역방향)
Google Form → 유지하되 메인 아님

## Google Form 상태
- 유지: 백업 + 외부 채널용 (SNS 링크 등)
- Form 접수 → Sheet New 시트 → puller → DB (기존 경로 유지)
- 단, 메인은 웹 폼

## 데이터 소스 우선순위
1순위: 웹 폼 (/api/apply) — 즉시 DB
2순위: Google Form → Sheet → puller → DB — 5분 딜레이
3순위: admin 수동 입력 — /admin/candidates

## 필드명 매핑 (CandidateApply 모델 → DB)
| 모델 필드 | DB 컬럼 |
|-----------|---------|
| education | education_level |
| marital_status | married |
| personal_considerations | personal_consideration |
| agreement | consent |
| facts | fact_check |
| admin_notes | notes |

## 암호화 대상 PII 필드 (9개)
full_name, email, mobile_phone, kakaotalk, passport,
criminal_record, religion, health_info, criminal_record_check

## 키 참조
- BRIDGE_FIELD_KEY → .env (AES-256 키 파생)
- JWT_SECRET → .env (apply_token 서명)
- ADMIN_API_KEY, ADMIN_PASSWORD → ABSOLUTE FREEZE
