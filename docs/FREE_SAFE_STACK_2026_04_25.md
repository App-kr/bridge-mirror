# BRIDGE 무료·안전 스택 감사 + 보강 — 2026-04-25

## 결론
**기존 인프라 건드리지 않음**. 운영 중인 SQLite + Render + Vercel + S3 그대로 유지.
**자동화 누락 부분만 보강** (신규 파일 추가 only).

---

## 1. 사전 점검 — 이미 존재하는 백업 도구 (잘 작동 중)

| 도구 | 위치 | 기능 | 자동 스케줄 |
|------|------|------|-------------|
| `bridge_backup.py` | `tools/` | 전체 프로젝트 스냅샷 | ❌ (수동) |
| `db_backup_enc.py` | `tools/` | master.db → AES-256-GCM 암호화 | ❌ (수동) |
| `render_db_backup.py` | `tools/` | Render `/data/master.db` SQL 덤프 + 30일 롤링 | ❌ (수동) |
| `secure_backup.py` | `tools/` | 환경변수 .enc 보관 | ❌ (수동) |
| `gdrive_backup.py` | `tools/` | Google Drive 업로드 | ❌ (수동) |

**문제**: 도구는 충분한데 매일 자동 실행이 없음. PC 끄거나 까먹으면 백업 0.

---

## 2. 추가한 파일 (additive only — 기존 코드 0줄 수정)

### a. `scripts/daily_backup_runner.py`
- 기존 도구 3개를 순차 호출하는 wrapper
- 단계별 timeout + 실패 시 텔레그램 알림
- logs/daily_backup/YYYYMMDD.log 자동 기록
- 옵션: `--skip-render` / `--quick`

### b. `scripts/register_daily_backup.bat`
- Windows Task Scheduler 등록 (관리자 권한 1회 실행)
- 매일 04:30 SYSTEM 계정으로 실행 (잠금화면에서도 동작)
- Task 이름: `BRIDGE_Daily_Backup`

### c. `.github/workflows/weekly-encrypted-backup.yml`
- 주 1회(일요일 19:00 UTC) Render DB → AES 암호화 → GitHub Releases 업로드
- 클라우드 이중화 보루 (PC 다운 시 안전망)
- **평문 push 절대 안 함** — `.enc`만 Releases 자산으로

### d. `docs/cron_job_org_setup.md`
- Render Free Cold Start 핑 가이드 (외부 무료 서비스, 코드 0줄)

---

## 3. 무료 안전 스택 — 운영 권장 매트릭스

| 계층 | 현재 | 권장 (변경 없음) | 작업 |
|------|------|-----------------|------|
| DB | SQLite master.db (자체) | 유지 | 일일 암호화 백업 추가 |
| 백엔드 | Render Free | 유지 | cron-job.org 핑 (코드 0) |
| 파일 저장 | AWS S3 | 유지 (R2 마이그레이션은 별도 세션) | 없음 |
| 프론트 | Vercel Hobby | 유지 | 없음 |
| Google Sheets | sheets_connector.py | 유지 (관리자 미러용) | 없음 |
| 자동 백업 | ❌ 없음 | **로컬 일일 + GitHub Actions 주간** | ✅ 추가됨 |

---

## 4. 활성화 절차 (사용자 1회 작업)

### 4-1. 로컬 일일 백업 자동화
```cmd
:: 관리자 권한으로 실행
Q:\Claudework\bridge base\scripts\register_daily_backup.bat
```
확인: `schtasks /query /tn BRIDGE_Daily_Backup /v /fo LIST`

### 4-2. 즉시 1회 검증 (관리자 권한 불필요)
```bash
"Q:/Phtyon 3/python.exe" -X utf8 "Q:/Claudework/bridge base/scripts/daily_backup_runner.py" --quick
```
확인: `Q:/Claudework/bridge base/master.db.enc` 갱신 + `logs/daily_backup/YYYYMMDD.log`

### 4-3. GitHub Actions 활성화
GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret:
- `BRIDGE_ADMIN_KEY` — Render `/api/admin/db/dump` 호출 키
- `BRIDGE_FIELD_KEY` — AES 암호화 키 (db_backup_enc.py와 동일)
- `RENDER_API_URL` — (선택) 기본값 `https://bridge-n7hk.onrender.com`

확인: Actions 탭 → "Weekly Encrypted DB Backup" → Run workflow (수동 1회)

### 4-4. Render Cold Start 차단 (cron-job.org)
`docs/cron_job_org_setup.md` 참조 — 5분 작업.

---

## 5. 안 한 것 (의도적 — 사용자 지시 "잘 되는 것 건드리지 마"")

- ❌ S3 → Cloudflare R2 마이그레이션 (작동 중인 흐름 위험)
- ❌ Google Sheets 의존 제거 (resume_converter/pipeline.py + main_gui.py + resume_api.py 사용 중)
- ❌ Render Starter 유료 전환
- ❌ DB 스키마 변경 / 코드 수정

---

## 6. 데이터 손실 시나리오 — 다중 방어

| 시나리오 | 방어선 |
|----------|--------|
| 로컬 PC 디스크 고장 | Render `/data/master.db` (영구 디스크) + GitHub Releases enc |
| Render 영구 디스크 손실 | 로컬 `master.db.enc` + GitHub Releases enc |
| GitHub 계정 정지 | 로컬 `backups/` 일일 스냅샷 + Render `/data` |
| 키(BRIDGE_FIELD_KEY) 유출 | enc 파일 즉시 폐기 + 키 교체 + 평문 백업 재암호화 |
| 키 분실 | ⚠️ 복호화 불가 — 키 다중 보관 필수 (pw.py + BX) |

---

## 7. 다음 단계 (별도 세션 권장)

1. cron-job.org 등록 (사용자 직접, 5분)
2. `register_daily_backup.bat` 관리자 권한 실행 (사용자 직접, 1분)
3. GitHub Secrets 3개 등록 + Actions 수동 실행 1회 검증 (사용자 직접, 5분)
4. (먼 미래) S3 → R2 마이그레이션 — 별도 세션, 트래픽/비용 검토 후
5. (먼 미래) Google Sheets 점진적 격하 — sheets_connector 사용처별 1개씩 DB로 이전
