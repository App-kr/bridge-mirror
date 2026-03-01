---
name: code-style
description: FastAPI + Next.js 15 코딩 패턴
---

# BRIDGE Coding Style

## FastAPI (Python)

### 에러 핸들링
```python
@app.post("/api/xxx")
async def handler(request: Request, body: SomeModel):
    if not _rate_ok(_ip_hash(request)):
        raise HTTPException(429, "Too many requests.")
    try:
        return ok(data=result, message="성공 메시지")
    except HTTPException:
        raise
    except Exception as e:
        _log.error("xxx 실패: %s", e, exc_info=True)
        err("사용자 친화적 오류 메시지", 500)
```

### DB 접근
```python
conn = sqlite3.connect(str(_ADMIN_DB_PATH))
conn.execute("PRAGMA busy_timeout = 5000")
conn.row_factory = sqlite3.Row
try:
    conn.execute("SELECT col FROM tbl WHERE id=?", (val,))
finally:
    conn.close()
```

### 응답 형식
```python
ok(data=..., message="...")   # 성공
err("메시지", status_code)    # 실패
# → {"success": bool, "data": ..., "message": ...}
```

### 금지 패턴
```python
err(f"실패: {e}", 500)          # 내부 오류 노출
except Exception: pass          # 오류 무시
f"SELECT * FROM {table}"       # SQL 인젝션
conn.execute("SELECT *")       # * 사용 금지, 컬럼 명시
```

## Next.js 15 (TypeScript)

### 컴포넌트 분류
- Server Component (기본): 데이터 페칭, SEO 페이지
- `'use client'`: useState, useEffect, 이벤트 핸들러가 필요한 경우만

### 폼 패턴
```typescript
// type="button" + onClick 분리
<button type="button" onClick={handleNext}>다음</button>
// 금지: <form onSubmit={...}> (Enter 키 조기 제출 방지)
```

### 타입 안전성
```typescript
job?.job_id ?? ''              // nullable 처리
value?.toString() ?? 'default'
// 금지: as any, @ts-ignore, null 체크 없이 접근
```

### Supabase 쿼리
```typescript
// 공개 엔드포인트: anon key + public view만
supabase.from('public_jobs').select('id,city,...')
// 금지: 'jobs', 'candidates' 원시 테이블 직접 접근
```

### 3-Step Wizard 패턴
```typescript
const [step, setStep] = useState<1|2|3>(1)
// Step 이동: 검증 후 setStep
// StepIndicator: 공통 컴포넌트 재사용
```

## CSS 유틸리티 (globals.css)
```
.btn-primary  .btn-secondary  .card  .badge
.badge-hot    .badge-pt       .badge-open
.input        .textarea       .label
```
새 스타일 추가 전 위 클래스 먼저 사용할 것.
