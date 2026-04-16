# BRIDGE 세션 이관 — Opus 인계 문서
# 2026.04.14 작성

---

## 프로젝트 기본 정보

- **서비스**: BRIDGE (bridgejob.co.kr) — 원어민 영어강사 채용 에이전시
- **프론트**: https://bridge-chi-lime.vercel.app (Next.js 14, Vercel)
- **백엔드**: https://bridge-n7hk.onrender.com (FastAPI, Render free tier)
- **소스**: Q:\Claudework\bridge base\ (메인), Q:\Claudework\bridge\ (JSX 파일만)
- **GitHub**: koreadobby/bridge
- **DB**: SQLite master.db → Render /data/master.db + Drive 백업
- **Python**: Q:\Phtyon 3\python.exe (오타 그대로)

---

## 오늘(2026.04.13~14) 완료된 작업

| 작업 | 커밋 | 상태 |
|---|---|---|
| Canvas Sheet Phase 4 (O(n)→O(log n)) | c1954c6a | ✅ |
| 컬럼 필터 드롭다운 | 86ed207f | ✅ |
| CSV/Excel 내보내기 | a9bc23bb | ✅ |
| security_vault.py T3v1 3중 암호화 | 4ea4b080 | ✅ |
| encrypt_migrate.py PII 9,757건 암호화 | 4993f3a0 | ✅ |
| location_plain / school_name_plain 컬럼 추가 | c65395e5 | ✅ |
| 소개발송 자동화 98% (Canvas Sheet → introduce-mail) | b0e726e3 | ✅ |
| supabase 제거 (Render 배포 실패 원인) | a3909912 | ✅ |
| DB_PATH 수정 (master.db → /data/master.db) | - | ✅ |
| Drive 자동 백업 6시간마다 (작업 스케줄러) | - | ✅ |
| EMERGENCY_RESTORE.bat head -10 버그 수정 | - | ✅ |

---

## 현재 미완료 / 진행 중

### 🔴 즉시 필요

1. **DB 백업 주기 강화** (아래 명령어 실행 필요)
   - 현재: 6시간마다
   - 목표: 1시간마다 + 로그인 시 + api_server.py 시작 시 자동 복원
   - 명령어:
   ```
   /model sonnet
   ```
   ```
   작업 스케줄러 BRIDGE_DB_Backup 주기 변경: [직렬]

   1. 기존 스케줄 삭제:
   powershell -Command "Unregister-ScheduledTask -TaskName 'BRIDGE_DB_Backup' -Confirm:\$false"

   2. 새 스케줄 2개 등록:
   powershell -Command "
   \$action = New-ScheduledTaskAction -Execute 'Q:\Phtyon 3\python.exe' -Argument '-X utf8 \"Q:\Claudework\bridge base\tools\db_drive_backup.py\" backup'
   \$trigger1 = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Hours 1) -Once -At (Get-Date)
   \$trigger2 = New-ScheduledTaskTrigger -AtLogOn
   Register-ScheduledTask -TaskName 'BRIDGE_DB_Backup_Hourly' -Action \$action -Trigger \$trigger1 -RunLevel Highest -Force
   Register-ScheduledTask -TaskName 'BRIDGE_DB_Backup_Login' -Action \$action -Trigger \$trigger2 -RunLevel Highest -Force
   "

   3. api_server.py lifespan startup 함수에
      db_drive_backup.py restore 호출 추가
      (Render 재시작 시 Drive에서 자동 복원)

   완료 후 git push origin main.
   ```

2. **Render /admin/sheet 데이터 미표시**
   - 원인: Render /data/master.db 비어있음
   - 해결: `python "Q:\Claudework\bridge base\tools\db_drive_backup.py" restore`
   - 확인: https://bridge-chi-lime.vercel.app/admin/sheet 새로고침

3. **CSP font-src cdn.jsdelivr.net** 여전히 차단
   - next.config.js font-src에 https://cdn.jsdelivr.net 추가 필요

---

## 핵심 파일 위치

```
Q:\Claudework\bridge base\
├── api_server.py          # FastAPI 백엔드 전체
├── requirements.txt       # supabase 주석처리됨
├── render.yaml            # startCommand: uvicorn api_server:app
├── security_vault.py      # T3v1 AES-256-GCM 암호화
├── encrypt_migrate.py     # PII 필드 마이그레이션
├── tools\
│   ├── db_drive_backup.py # Drive 백업/복원
│   ├── render_db_restore.py # Render DB 복원
│   ├── bx.py              # 크리덴셜 관리 (DPAPI)
│   └── doc_processor.py   # 이력서 PII 제거
└── web_frontend\src\app\admin\
    ├── sheet\             # Canvas Sheet (GridEngine.ts 등)
    ├── introduce-mail\    # 소개발송 페이지
    ├── employers\         # 구인자 관리
    └── mail-send\         # 메일 발송
```

---

## 환경변수 (Render 대시보드)

- `DB_PATH`: /data/master.db ← 오늘 수정 완료
- `ADMIN_API_KEY`: bx.py get ADMIN_API_KEY 로 확인
- `JWT_SECRET`: Render 대시보드에서 확인
- `BRIDGE_HMAC_KEY`: Render 대시보드에서 확인
- `GOOGLE_SERVICE_ACCOUNT_JSON`: bridge-sheet-sync-103 서비스 계정

---

## Drive 백업 현황

- **위치**: H:\내 드라이브\BRIDGE_DB_BACKUPS\
- **파일**: bridge_db_20260415_2217.sql.gz (4MB) + master.db
- **스케줄**: 현재 6시간마다 (→ 1시간으로 변경 필요)
- **수동 백업**: `python "Q:\Claudework\bridge base\tools\db_drive_backup.py" backup`
- **수동 복원**: `python "Q:\Claudework\bridge base\tools\db_drive_backup.py" restore`

---

## 소개발송 플로우 (98% 완성)

```
/admin/sheet → 후보자 체크박스 선택
→ 툴바 하늘색 "소개발송" 버튼 클릭
→ /admin/introduce-mail?candidates=5511,5651 새 탭
→ 구인자 지역 필터 → 미리보기 → 개별발송
```

**남은 2%**: 실제 E2E 테스트 (본인 이메일로 발송 확인)

---

## 다음 세션 우선순위

1. DB 백업 주기 강화 (위 명령어 실행)
2. /admin/sheet 데이터 표시 확인
3. CSP font-src 수정
4. 소개발송 E2E 실제 테스트
5. Apply 실제 제출 테스트 (Form → DB → 이메일)
6. GAS 번역 누락 추가 (브라우저에서 직접)

---

## 절대 규칙

- 모든 작업 전: `git add -A && git commit -m "backup: [작업명]"`
- 코드: 전체 파일 제공 (생략 금지)
- PII: 관리자 패널 원본 / 외부 마스킹
- Render autoDeploy: true (push 시 자동 배포)
- 히어로 디자인: 절대 변경 금지
- Python 경로: Q:\Phtyon 3\python.exe (오타 그대로)
- 모든 답변 첫 줄: 📅 날짜 — 주제 | 🤖 추천: 모델
- 클코 명령어: 항상 2박스 (/model 박스 + 명령어 박스)
