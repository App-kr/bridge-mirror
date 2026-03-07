# API Endpoints — 엔드포인트 규칙

## 인증 레벨 분류

```
PUBLIC  (인증 없음)    GET /api/jobs, GET /api/jobs/{id}
RATE    (IP Rate Limit) POST /api/apply, POST /api/inquiry, POST /api/community/{board}
ADMIN   (X-Admin-Key)   /api/admin/*
```

## Rate Limits

| 엔드포인트 | 제한 | 비고 |
|-----------|------|------|
| `GET /api/jobs` | 60/min | IP 기반 |
| `GET /api/jobs/{id}` | 60/min | IP 기반 |
| `POST /api/apply` | 10/hr | IP 기반 |
| `POST /api/inquiry` | 5/hr | IP 기반 |
| `POST /api/community/{board}` | 5/5min | IP 기반 |

## 신규 엔드포인트 생성 규칙
1. POST → `_rate_ok(_ip_hash(request))` 체크 필수
2. Admin → `_check_admin(request)` 호출 필수
3. DB 쿼리 → `?` 파라미터 바인딩, f-string SQL 금지
4. 외부 입력 → PIIMaskingMiddleware 통과 확인
5. 에러 → 제네릭 메시지 + 서버 로그 (내부 예외 노출 금지)

## 응답 형식 (일관성 필수)
```python
# 성공
ok(data={"id": 1, ...}, message="Created successfully")
# → {"success": true, "data": {...}, "message": "..."}

# 실패
err("User-friendly error message", 400)
# → {"success": false, "data": null, "message": "..."}
```

## Community API

| Method | Path | Auth | 설명 |
|--------|------|------|------|
| GET | `/api/community/{board}` | Public | 게시글 목록 (?limit=50) |
| GET | `/api/community/{board}/{id}` | Public | 게시글 상세 (views +1) |
| POST | `/api/community/{board}` | Rate | 게시글 작성 (HTML strip) |
| DELETE | `/api/community/{board}/{id}` | Admin | 게시글 삭제 (soft) |
| PATCH | `/api/admin/community/posts/{id}/pin` | Admin | 고정/해제 |

## Interview API

| Method | Path | Auth | 설명 |
|--------|------|------|------|
| GET | `/api/admin/interviews` | Admin | 인터뷰 목록 |
| POST | `/api/admin/interviews` | Admin | 인터뷰 생성 + 이메일 |
| PATCH | `/api/admin/interviews/{id}` | Admin | 상태 변경 |
| DELETE | `/api/admin/interviews/{id}` | Admin | 삭제 |

## File Upload API

| Method | Path | Auth | 설명 |
|--------|------|------|------|
| POST | `/api/upload/{entity_type}/{entity_id}` | Rate | 파일 업로드 |
| GET | `/api/admin/files/{entity_type}/{entity_id}` | Admin | 파일 목록 |

## CORS 설정
- Methods: `GET, POST, PATCH, DELETE, OPTIONS`
- Headers: `Content-Type, X-Admin-Key`
- Origin: 설정 기반 (prod는 bridgejob.co.kr만)
