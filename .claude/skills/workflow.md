---
name: workflow
description: 기능 구현 워크플로우 + 사고 모드
---

# BRIDGE Workflow

## /build-feature [기능명]

```
1. /plan     → 구현 전략 (영향 파일, DB 변경, 보안 검토)
2. /tdd      → 테스트 케이스 (성공/실패/Edge case)
3. /code     → 구현 (coding-style + security-compliance 준수)
4. /security → 보안 검토 (STRIDE, PII 경로, Rate limiting)
5. /verify   → 빌드 검증 (npm run build + py_compile, 오류 시 자동 수정)
```

## 사고 모드 (Adaptive Thinking)

| 작업 유형 | 접근 방식 |
|----------|---------|
| 아키텍처, DB 스키마, 보안 설계 | 심층 분석 — 영향 범위 전체 검토 후 실행 |
| 버그 수정, 리팩토링, 스타일 변경 | 빠른 실행 — 최소 변경, 즉시 적용 |
| 신규 기능 구현 | /build-feature 워크플로우 적용 |
| 간소화/정리 | /simplify — 중복 제거, 공통 패턴 추출, 빌드 검증 |

## 환경별 차이

| 항목 | Desktop (로컬) | Server (prod) | Mobile/Admin |
|------|---------------|---------------|-------------|
| DB 경로 | `./master.db` | `BRIDGE_DB_PATH` env | API 경유 |
| 업로드 | `./uploads/` | `/opt/bridge/uploads/` | API 경유 |
| Swagger | 활성 | `BRIDGE_ENV=production` 비활성 | N/A |
| Admin 접근 | localhost | nginx IP 제한 | VPN/API 키 |
| SMTP | 동일 | 동일 | 동일 |
