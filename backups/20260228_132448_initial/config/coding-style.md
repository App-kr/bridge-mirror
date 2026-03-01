# BRIDGE Coding Style Rules
# Next.js 15 + FastAPI 불변성 패턴 — 모든 세션 절대 준수

---

## FastAPI (Python) 패턴

### 에러 핸들링 — 반드시 이 패턴
```python
# ✅ 올바른 패턴
@app.post("/api/xxx")
async def handler(request: Request, body: SomeModel):
    if not _rate_ok(_ip_hash(request)):
        raise HTTPException(429, "Too many requests.")
    try:
        # 로직
        return ok(data=result, message="성공 메시지")
    except HTTPException:
        raise
    except Exception as e:
        import logging as _log
        _log.getLogger("bridge.api").error("xxx 실패: %s", e, exc_info=True)
        err("사용자 친화적 오류 메시지", 500)

# ❌ 금지 패턴
err(f"실패: {e}", 500)          # 내부 오류 노출
except Exception: pass          # 오류 무시
conn = sqlite3.connect(path)    # busy_timeout 없이 연결
```

### DB 접근 패턴
```python
# ✅ 올바른 패턴
conn = sqlite3.connect(str(_ADMIN_DB_PATH))
conn.execute("PRAGMA busy_timeout = 5000")
conn.row_factory = sqlite3.Row
try:
    # 쿼리
finally:
    conn.close()

# ❌ 금지 패턴
f"SELECT * FROM {table} WHERE id={user_input}"  # SQL 인젝션
conn.execute("SELECT *")  # * 사용 금지, 컬럼 명시
```

### 응답 형식 — 일관성 유지
```python
# 성공: ok(data=..., message="...")
# 실패: err("메시지", status_code)
# 둘 다 내부적으로 {"success": bool, "data": ..., "message": ...} 형식
```

---

## Next.js 15 (TypeScript) 패턴

### 컴포넌트 분류
```typescript
// Server Component (기본): 데이터 페칭, SEO 필요한 페이지
// 'use client' 필요한 경우만: useState, useEffect, 이벤트 핸들러

// ✅ 올바른 패턴 — 폼은 type="button" + handleNext/handleSubmit 분리
<button type="button" onClick={handleNext}>다음</button>
// ❌ 금지 — form onSubmit (Enter 키 조기 제출 방지)
<form onSubmit={handleSubmit}>
```

### 타입 안전성
```typescript
// ✅ nullable 처리
job?.job_id ?? ''
value?.toString() ?? 'default'

// ❌ 금지
job.job_id          // null 체크 없이 접근
as any              // any 타입 캐스팅
// @ts-ignore      // TypeScript 오류 무시
```

### Supabase 쿼리 규칙
```typescript
// ✅ 공개 엔드포인트: anon key + public view
supabase.from('public_jobs').select('id,city,employment_type,...')

// ❌ 금지
supabase.from('jobs').select('*')     // 민감 테이블 직접 접근
supabase.from('candidates').select() // 원시 테이블 금지
```

### 3-Step Wizard 패턴 (apply/inquiry/community 폼)
```typescript
const [step, setStep] = useState<1|2|3>(1)
// Step 이동: 검증 후 setStep
// Reset: useEffect(() => { if (condition) setStep(1) }, [dep])
// StepIndicator: 공통 컴포넌트 재사용
```

---

## 파일 구조 규칙

```
web_frontend/src/
  app/           → 페이지 (Server Component 기본)
  components/    → 재사용 UI (Client Component 허용)
  lib/           → supabase.ts, utils
  types/         → index.ts (PublicJob, PublicCandidate 등)

backend/
  migrate_bbs.py → CSV → master.db

루트/
  api_server.py      → FastAPI 엔트리포인트
  security_vault.py  → AES-256-GCM (수정 금지)
  auto_pipeline_v2.py → Supabase 동기화
```

---

## CSS 유틸리티 클래스 (globals.css)
```
.btn-primary  .btn-secondary  .card  .badge
.badge-hot    .badge-pt       .badge-open
.input        .textarea       .label
```
새 스타일 추가 전 위 클래스 먼저 사용할 것.
