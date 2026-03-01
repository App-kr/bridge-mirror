# Debugging Patterns — 디버깅 패턴

## 흔한 문제 & 즉시 해결법

### 1. localhost:3000 접속 불가 (ERR_FAILED)
**원인**: Next.js dev 서버 미실행
**해결**:
```bash
cd web_frontend && npm run dev
```
**확인**: `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/`

### 2. localhost:8000 API 응답 없음
**원인**: FastAPI 서버 미실행
**해결**:
```bash
cd "Q:/Claudework/bridge base" && python -m uvicorn api_server:app --host 0.0.0.0 --port 8000
```

### 3. .next 캐시 충돌 (빌드 오류, 라우팅 이상)
**증상**: 페이지 404, 이전 코드 표시, 빌드 에러
**해결**:
```bash
rm -rf web_frontend/.next && cd web_frontend && npm run dev
```

### 4. SQLite "database is locked"
**원인**: 다른 프로세스가 DB 점유, busy_timeout 미설정
**해결**: `conn.execute("PRAGMA busy_timeout = 5000")` 확인
**확인**: `fuser master.db` 또는 프로세스 확인

### 5. npm run build 타입 에러
**접근**:
1. 에러 메시지에서 파일:줄번호 확인
2. `?.` nullable 체크 누락이 가장 흔함
3. `as any` 사용 금지 — 올바른 타입 정의
4. 수정 후 `npm run build` 재실행

### 6. API CORS 에러 (브라우저)
**증상**: `Access-Control-Allow-Origin` 에러
**확인**: `api_server.py` CORSMiddleware 설정
- `allow_methods`: GET, POST, PATCH, DELETE, OPTIONS
- `allow_headers`: Content-Type, X-Admin-Key
- `allow_origins`: 적절한 origin 설정

### 7. PII 복호화 실패
**증상**: `bridge.security` 로거에 복호화 에러
**확인**:
1. `BRIDGE_FIELD_KEY` env 설정 확인
2. 암호화 시 사용된 키와 동일한지 확인
3. `security_vault.py`의 `decrypt_field()` 호출 추적

### 8. 이메일 발송 실패
**증상**: 폼 제출 성공하지만 이메일 미수신
**확인**:
1. `BRIDGE_SMTP_EMAIL`, `BRIDGE_SMTP_PASSWORD` env
2. Gmail 앱 비밀번호 (2FA 필수)
3. 서버 로그에서 SMTP 에러 확인
**참고**: email 실패는 form 제출을 차단하지 않음 (non-blocking)

## 빌드 검증 체크리스트
```bash
# Frontend
cd web_frontend && npm run build    # 14 routes, 0 errors 기대

# Backend
python -m py_compile api_server.py
python -m py_compile email_templates.py
python -m py_compile auto_pipeline_v2.py
```

## 서버 상태 빠른 확인
```bash
curl -s http://localhost:3000/ -o /dev/null -w "%{http_code}"   # Frontend: 200
curl -s http://localhost:8000/api/jobs -o /dev/null -w "%{http_code}"  # API: 200
```

## 코드 간소화 패턴 (/simplify)
- 중복 코드 → 공통 컴포넌트/유틸리티 추출
- 예: `BoardHeader`, `stripMd()`, `accentHex()` 추출 (2026-02-28)
- 변경 후 반드시 `npm run build` 검증
- 백업 → 수정 → 빌드 성공 → 백업 삭제 순서
