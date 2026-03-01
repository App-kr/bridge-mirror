qa-test 에이전트를 호출하여 통합 QA:
1. FastAPI 서버 실행 가능 확인
2. 각 API 엔드포인트 응답 확인
3. 보안 점검 (pip audit, 시크릿 grep, XSS)
4. 결과를 Q:/bridge-overnight/TEST_REPORT.md에 기록
코드 전면 수정 금지.