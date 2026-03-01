세션 종료 전 자동 저장을 수행하라:

1. 오늘 날짜와 프로젝트명으로 로그 파일 생성:
   Q:/bridge-overnight/logs/session_bridge-base_[YYYY-MM-DD_HHMM].md

2. 로그에 기록할 내용:
   - 날짜/시간
   - 프로젝트명 (현재 디렉토리 기준)
   - git log --oneline -5 (최근 커밋 5개)
   - git diff --stat (변경 파일 요약)
   - 오늘 이 세션에서 수행한 작업 요약 (대화 기반)
   - 발견된 이슈
   - 다음에 해야 할 작업

3. .memory/ 에도 동일 내용 저장

4. 완료 후 "세션 저장 완료: [파일경로]" 출력
