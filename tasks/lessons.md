# Bridge 실수 학습 로그

## 2026-03-08 DB PK 혼동
- 실수: UPDATE 시 id 사용 → 실제 PK는 candidate_id
- 원인: PRAGMA table_info() 확인 안 함
- 재발방지: 모든 UPDATE/DELETE 전 PK 컬럼명 확인 필수

## 2026-03-08 Python 이스케이프
- 실수: SQL 안 != 를 \!= 로 작성 → SyntaxWarning
- 재발방지: SQL은 triple-quote 또는 별도 변수로 분리
