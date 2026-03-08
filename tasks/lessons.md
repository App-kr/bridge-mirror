# Bridge 실수 학습 로그

## 2026-03-08 DB PK 혼동
- 실수: UPDATE 시 id 사용 → 실제 PK는 candidate_id
- 원인: PRAGMA table_info() 확인 안 함
- 재발방지: 모든 UPDATE/DELETE 전 PK 컬럼명 확인 필수

## 2026-03-08 Python 이스케이프
- 실수: SQL 안 != 를 \!= 로 작성 → SyntaxWarning
- 재발방지: SQL은 triple-quote 또는 별도 변수로 분리

## 2026-03-08 세션 시작 루틴 미실행 → 중복 구현
- 실수: 이미 완성된 FaqDndList.tsx + admin/faq/page.tsx를 동일 내용으로 재작성
- 원인: `git log --name-only -3` + `cat tasks/todo.md` 미실행
- 재발방지: 매 작업 전 git log + todo.md 확인 MANDATORY
- 빌드도 rm -rf .next 없이 캐시 충돌 → 항상 클린 빌드로 시작

## 2026-03-08 날짜 → visa_type 추정 위험
- 실수: "날짜 있으면 ARC-Yes로 추정" 규칙 작성
- 원인: 날짜 컬럼이 arc 날짜라고 단정 → 생일/시작일/여권만료일도 날짜
- 재발방지: 필드 의미가 명확히 확인된 경우에만 값 채움, 모호한 필드는 NULL 유지
- 원칙: 단일 패턴으로 다양한 변수를 단일화하면 데이터 위조
