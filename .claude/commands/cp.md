---
description: 현재 세션에서 건드린 파일만 안전하게 commit + push
---

# /cp — Safe Commit & Push

## 실행

### 1. 세션 변경 파일만 추출
git diff --name-only HEAD
git diff --name-only --cached
git ls-files --others --exclude-standard

### 2. 확인 출력
변경된 파일 목록을 사용자에게 보여준다.
세션에서 건드리지 않은 파일이 포함되어 있으면 즉시 중단하고 보고.

### 3. 안전 체크
- .env 파일 포함 여부 → 포함 시 즉시 중단
- master.db 포함 여부 → 포함 시 즉시 중단
- Q드라이브 외부 경로 포함 여부 → 포함 시 즉시 중단

### 4. 커밋 메시지 생성
변경 내용 기반으로 컨벤셔널 커밋 메시지 자동 생성.
형식: feat|fix|chore|docs|perf: 한국어 설명

### 5. 실행
git add [세션_변경_파일만]
git commit -m "[자동생성_메시지]"
git push origin main

### 6. 완료 보고
커밋 해시 + push 결과 출력.
