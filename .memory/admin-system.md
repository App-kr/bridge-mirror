# Admin System — 관리자 시스템

## Web Admin Pages (6개)

| 경로 | 기능 | 인증 |
|------|------|------|
| `/admin` | Ad Posts 대시보드 + 6-tab 네비 | runtime admin key |
| `/admin/posts` | 커뮤니티 CRUD, 보드 필터, pin/delete | runtime admin key |
| `/admin/interviews` | 인터뷰 스케줄, Google Meet, 이메일 | runtime admin key |
| `/admin/applications` | 지원자+고용주 제출물, 상태 워크플로우 | runtime admin key |
| `/admin/payments` | 결제 기록 (Stripe placeholder) | runtime admin key |
| `/admin/candidates` | AG Grid 스프레드시트 | runtime admin key |

- 모든 페이지: AdminNav 공통 컴포넌트, 런타임 admin key 입력 방식
- nginx: `/admin` 경로 IP 제한 (127.0.0.1 + deploy IP)

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

## Mobile/원격 접근 시
- Admin API 키로 인증 (`X-Admin-Key` header)
- VPN 또는 SSH 터널 경유 권장
- 동일한 보안 규칙 적용 (STRIDE, rate limit, PII 보호)
