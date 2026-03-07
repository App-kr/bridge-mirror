# Admin System — 관리자 시스템

## Web Admin Pages (9개)

| 경로 | 기능 | 인증 |
|------|------|------|
| `/admin` | Dashboard — 통합 통계 카드 6개 + 월별 차트(BarChart) + 채널별 파이차트 + 최근 활동 + 빠른 액션 | runtime admin key |
| `/admin/inbox` | 통합 수신함 — 소스탭, 상태필터, 검색, 벌크 처리, Gmail 동기화 | runtime admin key |
| `/admin/inbox/[id]` | 수신함 상세 — 정보, 상태변경, 메모, 담당자배정, mailto 액션 | runtime admin key |
| `/admin/ad-posts` | Ad Posts 관리 | runtime admin key |
| `/admin/posts` | 커뮤니티 CRUD, 보드 필터, pin/delete, 검색, 수정 | runtime admin key |
| `/admin/interviews` | 인터뷰 스케줄, Google Meet, 이메일 | runtime admin key |
| `/admin/applications` | 지원자+고용주 제출물, 상태 워크플로우 | runtime admin key |
| `/admin/payments` | 결제 기록 (Stripe placeholder) | runtime admin key |
| `/admin/candidates` | AG Grid 스프레드시트 | runtime admin key |

- 모든 페이지: AdminNav 공통 컴포넌트 (8탭), useAdminAuth 훅, AdminAuth 인증 UI
- nginx: `/admin` 경로 IP 제한 (127.0.0.1 + deploy IP)

## 통합 수신함 시스템 (2026-03 추가)

### 백엔드 모듈
- `inbox_api.py` — FastAPI APIRouter, 8개 엔드포인트
  - GET /api/admin/inbox (필터+페이지네이션), GET /inbox/{id}, PATCH status/notes/assign, POST bulk
  - GET /api/admin/stats, /stats/monthly, /stats/by-source
  - 보안: _sanitize_search(), _validate_date(), _rate_ok() 적용
- `gmail_collector.py` — Gmail API OAuth2, 자동 분류/파싱, 중복 방지
  - POST /api/admin/gmail/sync, GET /api/admin/gmail/status

### DB 스키마 확장
- candidates/client_inquiries에 8개 컬럼: source, inbox_status, gmail_message_id, raw_email_body, parsed_data, notes, assigned_to, last_activity
- 마이그레이션: `migrations/db_migration_inbox.py`

### 프론트엔드
- recharts 사용 (dynamic import, SSR 비활성화)
- 대시보드: 6개 통계 카드 + BarChart(월별) + PieChart(채널별)
- 수신함: 소스탭(5), 상태필터(7), 검색, 체크박스 벌크, Gmail 동기화 버튼

## Desktop Admin App
- **파일**: `admin_app/bridge_admin.py` (Python tkinter)
- **빌드**: `admin_app/build_app.py` → PyInstaller → `dist/BRIDGEAdmin.exe`
- **아이콘**: `admin_app/bridge_icon.ico` (파란 "B" + bridge 심볼)
- **기능**: 인터뷰 관리, 지원서 뷰어, 커뮤니티 통계, DB 백업

## Interview System
- **DB**: `interviews` table in master.db
- **상태**: scheduled → completed / cancelled / no_show
- **API**: GET/POST `/api/admin/interviews`, PATCH/DELETE `/{id}`
- **이메일 자동 발송**:
  - `send_interview_invitation()` — 영어, 후보자용
  - `send_interview_invitation_employer()` — 한국어, 고용주용
  - Google Meet 링크 + 참여 버튼 포함

## Application Status Workflow
```
new → reviewing → interview_scheduled → hired / rejected
```

## Inbox Status Workflow
```
new → reviewed → contacted → interview → hired / rejected
```

## Craigslist 자동 광고 RPA
- **스크립트**: `tools/craigslist_auto_rpa.py`
- **실행 배치**: `scripts/run_rpa.bat` (`--headless --limit 10`)
- **Windows 작업 스케줄러**: `BridgeCraigslistRPA` — 6시간 간격 (03:00, 09:00, 15:00, 21:00)
- **Headless 모드**: 화면 없이 백그라운드 실행. CAPTCHA 발생 시 해당 건 스킵.
- **DB**: `ad_posts` 테이블에 draft/posted/error 상태 기록
- **로그**: `logs/rpa_error.log` (JSON 구조화), `logs/scheduler.log` (실행 로그)
- **보안**: PII 자동 치환 (redact_pii) + 최종 검증 (security_check)
- **주의**: PC 켜져 있어야 함 (잠금 상태 OK). 스케줄러 미등록 시 자동 실행 안 됨.

## Mobile/원격 접근 시
- Admin API 키로 인증 (`X-Admin-Key` header)
- VPN 또는 SSH 터널 경유 권장
- 동일한 보안 규칙 적용 (STRIDE, rate limit, PII 보호)
