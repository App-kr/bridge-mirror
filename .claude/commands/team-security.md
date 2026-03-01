security-check 에이전트를 호출하여:
1. pip audit 또는 safety check 실행
2. 하드코딩 시크릿 grep 전수 검사 (*.py 파일)
3. .env가 .gitignore에 포함 확인
4. CORS 설정 확인
5. 결과를 Q:/bridge-overnight/SECURITY_AUDIT.md에 기록