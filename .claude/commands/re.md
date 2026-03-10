---
description: Research-first implementation. 바로 코드 짜기 금지. 7단계 강제 실행.
---

# /re — Research & Execute Mode

## 규칙
바로 구현하지 않는다. 아래 7단계를 순서대로 완주한다.

## 실행 순서

### STEP 1 — 공식 문서 확인
관련 라이브러리/프레임워크 공식 docs 확인.
Next.js, FastAPI, SQLite, Tailwind 중 해당하는 것.
없으면 SKIP 명시.

### STEP 2 — 웹 리서치
최신 구현 사례, known issues, breaking changes 확인.
2025년 이후 자료 우선.

### STEP 3 — 코드베이스 분석
`Q:\Claudework\bridge base` 내 관련 파일 전체 확인.
- 기존 패턴과 일관성 체크
- PII 마스킹 정책 충돌 여부
- HERO-ANIMATION 영향 여부
- hard-delete 시도 여부

### STEP 4 — 옵션 비교
구현 방법 최소 2가지 제시.
각 옵션: 장단점 + 토큰 비용 + 보안 리스크 명시.
선택 근거 명시 후 진행.

### STEP 5 — 구현
선택된 옵션으로 완전한 파일 단위 구현.
부분 코드 출력 금지.

### STEP 6 — 검증
```bash
cd "Q:\Claudework\bridge base"
npm run build 2>&1 | tail -20
python -c "import api_server; print('OK')"
```
빌드 실패 시 수정 후 재검증. 통과 전 커밋 금지.

### STEP 7 — 커밋
```bash
git add -A
git commit -m "POST: $작업명"
```

## 완료 보고 형식
📅 날짜 시간 KST — /re 완료: $작업명
- STEP별 결과 요약
- 선택한 옵션 및 근거
- 빌드 결과
- 커밋 해시
