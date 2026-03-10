---
description: 커밋 전 코드 리뷰. 보안/로직/PII 3축 검증.
---

# /rr — Code Review Before Commit

현재 세션 변경사항 기준으로 리뷰 수행.

## 리뷰 체크리스트

### 🔒 보안 (BRIDGE 특화)
- [ ] PII(이메일/전화/이름) 공개 API 라우터 노출 여부
- [ ] SQL injection 가능성 (raw query 사용 시)
- [ ] ADMIN_API_KEY 하드코딩 여부
- [ ] .env 값 코드 내 노출 여부
- [ ] 미인증 엔드포인트 신규 추가 여부

### 🧠 로직
- [ ] hard-delete 시도 (is_deleted=1 논리삭제 원칙 위반)
- [ ] HERO-ANIMATION 파일 변경 여부
- [ ] 기존 패턴과 불일치
- [ ] TODO/return null/return {} 플레이스홀더 잔존

### 📋 품질
- [ ] 부분 코드 (완전한 파일 단위인지)
- [ ] 빌드 통과 여부
- [ ] 한국어 완료 요약 포함 여부

## 출력 형식
통과 항목: ✅
경고 항목: ⚠️ + 설명
차단 항목: ❌ + 수정 필요 내용

❌ 항목 존재 시 → /cp 실행 금지, 수정 후 재실행.
모두 ✅/⚠️ → "/cp 실행 가능" 명시.
