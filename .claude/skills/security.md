---
name: security
description: STRIDE 기반 보안 규칙 + 체크리스트
---

# BRIDGE Security Rules

## STRIDE 위협 매핑

| 위협 | 대응 규칙 |
|------|---------|
| Spoofing | JWT 서명 검증 필수, BRIDGE_FIELD_KEY != JWT_SECRET |
| Tampering | SQLite WAL 모드, soft-delete 전용 (물리 DELETE 금지) |
| Repudiation | 모든 admin 액션 서버 로그 기록 |
| Info Disclosure | PII 필드 AES-256-GCM 암호화, 에러 응답 내부 노출 금지 |
| DoS | Rate limiting: apply(10/hr), inquiry(5/hr), community(5/5min) |
| Elevation | ADMIN_API_KEY 헤더 검증, prod 환경 미설정 시 503 |

## 시크릿 감지 체크리스트

- `.env` 하드코딩 절대 금지 → `os.getenv()` 사용
- `NEXT_PUBLIC_` 접두사에 비밀 값 절대 금지 (브라우저 번들 노출)
- `console.log`, `print`, `logger` 에 비밀값/PII 출력 금지

## PII 암호화

```python
PII_FIELDS = {
    "full_name", "email", "mobile_phone", "kakaotalk",
    "passport", "criminal_record", "health_info",
    "phone", "contact_name", "business_registration"
}
# 위 필드 저장 전 → is_encrypted() 확인 → encrypt_field() 호출
# security_vault.py (AES-256-GCM) — 수정 금지 파일
```

## API 엔드포인트 신규 생성 규칙

1. POST → `_rate_ok()` 체크 필수
2. Admin → `_check_admin(request)` 호출 필수
3. DB 쿼리 → `?` 파라미터 바인딩 필수, f-string SQL 금지
4. 외부 입력 반환 → PIIMaskingMiddleware 통과 확인
5. 에러 → `err(f"..{exc}")` 금지, 제네릭 메시지 + 서버 로그

## 보안 수준별 엔드포인트

```
PUBLIC (인증 없음): GET /api/jobs, GET /api/jobs/{id}
RATE  (IP 제한):    POST /api/apply, POST /api/inquiry, POST /api/community
ADMIN (키 필요):    /api/admin/*
```

## 프론트엔드

- `dangerouslySetInnerHTML` — 동적 사용자 입력에 절대 사용 금지
- `localStorage` — JWT/세션 토큰 저장 금지 (httpOnly 쿠키 사용)
- 폼 필드 `maxLength` — 모든 텍스트 입력에 명시
