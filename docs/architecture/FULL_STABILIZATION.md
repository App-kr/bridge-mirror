# ████████████████████████████████████████████████████████████
# BRIDGE 전체 안정화 + 기능 완성 + 개선 — 통합 명령서
# ████████████████████████████████████████████████████████████
#
# Claude Code에 첨부 후 "순서대로 작업해줘"
# 12개 작업을 의존성 순서로 배치. 각 PHASE 완료 후 커밋.
# 예상 총 소요: ~2시간 (순차 실행)
#
# 절대 규칙:
# - 각 PHASE 시작 전 git commit (롤백 가능)
# - 기존 동작 중인 엔드포인트 시그니처 변경 금지
# - DB 스키마 변경 시 ALTER TABLE만 (DROP 금지)
# - 환경변수/시크릿 화면 출력 금지
# - Render push는 맨 마지막 1회만
# - 에러 시 해당 PHASE만 스킵하고 다음 진행 (전체 중단 금지)

---

## ██ PHASE 0: 전체 백업 + 환경 진단 ██

```bash
cd "Q:\Claudework\bridge base"

# 0-1. Git 풀 백업
git add -A && git commit -m "MEGA-BACKUP: pre-full-stabilization $(date +%Y%m%d-%H%M)" 2>/dev/null

# 0-2. DB 스냅샷
mkdir -p "Q:\Claudework\backups\stabilization"
copy master.db "Q:\Claudework\backups\stabilization\master_%date:~0,4%%date:~5,2%%date:~8,2%.db"

# 0-3. 전체 환경 진단 (수정 없이 보고만)
python -X utf8 -c "
import sqlite3, os, glob, ast, json

print('═══ DB 현황 ═══')
conn = sqlite3.connect('master.db')
for t in ['jobs','candidates','client_inquiries','employers','interviews',
          'interview_status_log','profile_sends','mail_logs','file_uploads']:
    try:
        cnt = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
        cols = len(conn.execute(f'PRAGMA table_info({t})').fetchall())
        print(f'  {t}: {cnt}건 ({cols}컬럼)')
    except: print(f'  {t}: 없음')

print()
print('═══ api_server.py 상태 ═══')
src = open('api_server.py',encoding='utf-8').read()
ast.parse(src)
print(f'  문법: OK ({len(src)} bytes, {src.count(chr(10))}줄)')
for kw in ['LOCAL-DISABLED','# DISABLED','TODO.*disabled']:
    import re
    matches = re.findall(f'.*{kw}.*', src)
    print(f'  {kw}: {len(matches)}건')

print()
print('═══ render.yaml ═══')
ry = open('render.yaml',encoding='utf-8').read()
for kw in ['autoDeploy','buildFilter','BRIDGE_FIELD_KEY','CORS']:
    for line in ry.split(chr(10)):
        if kw.lower() in line.lower():
            # 시크릿 마스킹
            if 'KEY' in kw or 'SECRET' in kw:
                print(f'  {kw}: ****')
            else:
                print(f'  {line.strip()}')

print()
print('═══ 프론트 API URL 불일치 ═══')
for f in glob.glob('web_frontend/src/**/*.ts', recursive=True) + glob.glob('web_frontend/src/**/*.tsx', recursive=True):
    try:
        content = open(f, encoding='utf-8', errors='ignore').read()
        if 'bridge-n7hk.onrender.com' in content:
            print(f'  하드코딩: {f}')
    except: pass

print()
print('═══ 미커밋 파일 ═══')
import subprocess
r = subprocess.run(['git','status','--short'], capture_output=True, text=True)
print(r.stdout.strip() or '  없음')

print()
print('═══ nationality 암호화 확인 ═══')
sample = conn.execute('SELECT nationality FROM candidates LIMIT 5').fetchall()
for r in sample:
    val = r[0] or ''
    is_enc = val.startswith('T3v1') or val.startswith('enc_') or len(val) > 50
    print(f'  {val[:40]}... encrypted={is_enc}')

conn.close()

print()
print('═══ CORS 설정 ═══')
for line in src.split(chr(10)):
    if 'cors' in line.lower() or 'origin' in line.lower():
        if 'import' not in line.lower():
            print(f'  {line.strip()[:100]}')
"
```

**결과 보고 후 PHASE 1 진행.**

---

## ██ PHASE 1: 서비스 안정성 (🔴 즉시) ██

### 1-A. render.yaml autoDeploy 수정

```bash
grep -n "autoDeploy" render.yaml
```

`autoDeploy: true`이면 `false`로 변경:
```yaml
autoDeploy: false
```

### 1-B. work_state.md 스테일 수정

work_state.md를 열어서 아래 3개 항목을 실제 값과 일치하도록 수정:

```
찾아서 수정:
1. "autoDeploy" 관련 → "autoDeploy: false — 수동 배포. Render 대시보드에서 Manual Deploy 클릭"
2. "deploy_skip.json" 관련 → "expire=1234567890 (2009년, 만료됨) — 배포 차단 없음"
3. "Python3" 경로 관련 → "Python3: Q:\Phtyon 3\python.exe (정상 동작)"
```

### 1-C. 미커밋 파일 정리

```bash
git add rpa_overlay.py 2>/dev/null
git add rpa_backup_to_k.py 2>/dev/null
grep -q "tsbuildinfo" .gitignore || echo -e "\n# Build info\n*.tsbuildinfo\ntsconfig.tsbuildinfo" >> .gitignore
git add .gitignore
```

### 1-D. Render DB 원격 백업 엔드포인트

api_server.py에 추가:

```python
# ─── Render DB 원격 백업 ─────────────────────────────
@app.get("/api/admin/db/dump")
async def dump_database(request: Request):
    """SQLite .dump → 텍스트 반환. 원격 백업용."""
    _check_admin(request)
    import sqlite3
    from io import StringIO
    from fastapi.responses import PlainTextResponse

    conn = sqlite3.connect(DB_PATH)
    buf = StringIO()
    for line in conn.iterdump():
        buf.write(line + "\n")
    conn.close()

    from datetime import datetime
    fname = f"master_dump_{datetime.now().strftime('%Y%m%d_%H%M')}.sql"
    return PlainTextResponse(
        buf.getvalue(),
        headers={"Content-Disposition": f"attachment; filename={fname}"}
    )
```

### 1-E. 로컬 백업 스크립트

파일: `tools/render_db_backup.py`

```python
"""
Render DB 원격 백업 — 로컬에서 실행.
cron 또는 Task Scheduler로 매일 실행 권장.

사용법: python tools/render_db_backup.py
환경변수: RENDER_API_URL, BRIDGE_ADMIN_KEY
"""
import os, sys, requests
from datetime import datetime, timedelta
from pathlib import Path

RENDER_API = os.getenv("RENDER_API_URL", "https://bridge-n7hk.onrender.com")
ADMIN_KEY = os.getenv("BRIDGE_ADMIN_KEY", "")
BACKUP_DIR = Path("Q:/Claudework/backups/render_db")

def backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y%m%d_%H%M")
    out = BACKUP_DIR / f"render_master_{now}.sql"

    print(f"[{now}] Render DB 백업...")
    try:
        r = requests.get(
            f"{RENDER_API}/api/admin/db/dump",
            headers={"Authorization": f"Bearer {ADMIN_KEY}"},
            timeout=120,
        )
        if r.status_code == 200:
            out.write_text(r.text, encoding="utf-8")
            print(f"  OK: {out} ({len(r.text):,} bytes)")
        else:
            print(f"  FAIL: HTTP {r.status_code}")
            return
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    # 30일 이전 삭제
    cutoff = datetime.now() - timedelta(days=30)
    for f in BACKUP_DIR.glob("render_master_*.sql"):
        try:
            ds = f.stem.replace("render_master_","")[:8]
            if datetime.strptime(ds,"%Y%m%d") < cutoff:
                f.unlink()
                print(f"  삭제: {f.name}")
        except: pass

if __name__ == "__main__":
    backup()
```

### 1-F. PHASE 1 커밋

```bash
python -c "import ast; ast.parse(open('api_server.py',encoding='utf-8').read()); print('OK')"
git add render.yaml work_state.md .gitignore rpa_overlay.py rpa_backup_to_k.py api_server.py tools/render_db_backup.py
git commit -m "stability: autoDeploy=false + DB원격백업 + 미커밋정리 + work_state수정"
```

---

## ██ PHASE 2: API URL 통일 + CORS 환경변수화 (🟠) ██

### 2-A. API URL 단일 소스

`web_frontend/src/lib/api.ts`를 열어서 API_URL 정의 확인.
다른 파일에서 하드코딩된 `bridge-n7hk.onrender.com`을 전부 이 import로 교체:

```
검색: grep -rn "bridge-n7hk.onrender.com" web_frontend/src/ --include="*.ts" --include="*.tsx"

각 파일에서:
  변경 전: const API_URL = "https://bridge-n7hk.onrender.com"
  또는:    fetch("https://bridge-n7hk.onrender.com/api/...")
  
  변경 후: import { API_URL } from "@/lib/api"  (또는 상대경로)
  
  ★ api.ts 자체는 수정하지 마라. 다른 파일에서 import만.
  ★ api.ts의 폴백이 빈 문자열 ''이면 → "https://bridge-n7hk.onrender.com"으로 수정.
```

### 2-B. CORS 환경변수 분리

api_server.py에서 CORS origins를 찾아서:

```python
# 변경 전: 하드코딩 리스트
# origins = ["https://bridgejob.co.kr", "https://www.bridgejob.co.kr", ...]

# 변경 후: 환경변수 우선, 폴백으로 기존 값
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else [
    "https://bridgejob.co.kr",
    "https://www.bridgejob.co.kr",
    "https://bridge-chi-lime.vercel.app",
    "http://localhost:3000",
]
# CORSMiddleware에 origins=CORS_ORIGINS 적용
```

### 2-C. API retry 통일

`web_frontend/src/lib/api.ts`에 retry 유틸 추가 (이미 있으면 확인만):

```typescript
// 이미 MAX_WAKE_RETRIES 등이 있으면 그 패턴을 다른 fetch 호출에도 적용.
// 핵심: Render cold start 시 첫 요청 실패 → 자동 재시도.
// adminFetch, signedFetch 등 모든 fetch 래퍼에 동일 retry 적용.

// 이미 구현되어 있으면 이 단계 스킵.
// 없으면:
export async function fetchWithRetry(url: string, options?: RequestInit, maxRetries = 3): Promise<Response> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const res = await fetch(url, { ...options, signal: AbortSignal.timeout(15000) });
      if (res.ok || res.status < 500) return res;
    } catch (e) {
      if (i === maxRetries - 1) throw e;
    }
    await new Promise(r => setTimeout(r, 2000 * (i + 1))); // 2s, 4s, 6s
  }
  throw new Error(`Failed after ${maxRetries} retries: ${url}`);
}
```

### 2-D. PHASE 2 커밋

```bash
cd web_frontend && npm run build 2>&1 | tail -5 && cd ..
python -c "import ast; ast.parse(open('api_server.py',encoding='utf-8').read()); print('OK')"
git add web_frontend/src/ api_server.py
git commit -m "fix: API URL 통일 + CORS 환경변수화 + fetch retry"
```

---

## ██ PHASE 3: LOCAL-DISABLED 정리 + nationality 검색 해결 (🟠🟡) ██

### 3-A. LOCAL-DISABLED 블록 검토

```bash
grep -n "LOCAL-DISABLED\|# DISABLED\|TEMP.*disabled" api_server.py
```

각 블록에 대해:
```python
# 판단 기준:
# - 사진 썸네일 → 변환기에서 처리 → 비활성 유지, 주석 추가
# - 파일 업로드 경로 기록 → 활성화 필요 여부 확인 (S3 키 기록이 있으면 불필요)
# - 에디터 이미지 삽입 → 현재 미사용 → 비활성 유지

# 각 블록에 이유 명시:
# [LOCAL-DISABLED] 이유: 변환기에서 별도 처리. 복원 시: 이 주석 제거. 2026-04-07
```

### 3-B. nationality 검색 가능화

nationality가 암호화되어 WHERE 검색 불가 문제 해결:

```python
# 방법: candidates 테이블에 nationality_plain 컬럼 추가 (비암호화)
# nationality는 PII가 아님 (미국, 캐나다, 영국 등 7개국만)
# → 검색/필터용 평문 컬럼 추가가 안전

# PHASE 0 진단에서 nationality가 실제로 암호화된 경우에만 실행:
```

api_server.py의 DB 초기화 부분에:

```sql
-- nationality_plain 컬럼 없으면 추가
ALTER TABLE candidates ADD COLUMN nationality_plain TEXT DEFAULT '';
```

그리고 기존 암호화된 nationality를 복호화하여 nationality_plain에 채우는 1회성 마이그레이션:

```python
# DB 초기화 함수 안에 (서버 시작 시 1회 실행):
def _migrate_nationality_plain():
    """nationality가 암호화된 경우 평문 컬럼에 복사"""
    conn = get_db()
    try:
        # 이미 채워져 있으면 스킵
        empty_count = conn.execute(
            "SELECT COUNT(*) FROM candidates WHERE nationality_plain = '' OR nationality_plain IS NULL"
        ).fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        
        if empty_count == 0 or total == 0:
            return  # 이미 완료 또는 데이터 없음
        
        rows = conn.execute("SELECT id, nationality FROM candidates WHERE nationality_plain = '' OR nationality_plain IS NULL").fetchall()
        for row_id, nat_val in rows:
            if not nat_val:
                continue
            # 암호화 여부 판단
            plain = nat_val
            if nat_val.startswith("T3v1") or len(nat_val) > 30:
                try:
                    plain = decrypt_field(nat_val)
                except:
                    plain = nat_val  # 복호화 실패 시 원본 유지
            conn.execute("UPDATE candidates SET nationality_plain = ? WHERE id = ?", (plain, row_id))
        
        conn.commit()
        import logging
        logging.getLogger("bridge").info(f"nationality_plain 마이그레이션: {len(rows)}건")
    except Exception as e:
        import logging
        logging.getLogger("bridge").warning(f"nationality_plain 마이그레이션 스킵: {e}")
```

### 3-C. PHASE 3 커밋

```bash
python -c "import ast; ast.parse(open('api_server.py',encoding='utf-8').read()); print('OK')"
git add api_server.py
git commit -m "fix: LOCAL-DISABLED 주석정리 + nationality 평문검색 컬럼 추가"
```

---

## ██ PHASE 4: client_inquiries 마이그레이션 (🟠) ██

### 4-A. 컬럼 매핑 분석

```bash
python -X utf8 -c "
import sqlite3
conn = sqlite3.connect('master.db')

print('═══ client_inquiries 컬럼 ═══')
ci_cols = conn.execute('PRAGMA table_info(client_inquiries)').fetchall()
for c in ci_cols: print(f'  {c[1]} ({c[2]})')

print()
print('═══ jobs 컬럼 ═══')
j_cols = conn.execute('PRAGMA table_info(jobs)').fetchall()
for c in j_cols: print(f'  {c[1]} ({c[2]})')

print()
print('═══ client_inquiries 샘플 3건 ═══')
rows = conn.execute('SELECT * FROM client_inquiries LIMIT 3').fetchall()
ci_names = [c[1] for c in ci_cols]
for row in rows:
    d = dict(zip(ci_names, row))
    for k,v in d.items():
        if v: print(f'  {k}: {str(v)[:80]}')
    print('  ---')

print()
print('═══ jobs에 이미 있는 job_number 범위 ═══')
r = conn.execute('SELECT MIN(job_number), MAX(job_number), COUNT(*) FROM jobs').fetchone()
print(f'  MIN: {r[0]}, MAX: {r[1]}, COUNT: {r[2]}')

conn.close()
"
```

**보고 후 매핑 결정. 아래는 예상 매핑 (실제 컬럼명에 맞게 수정):**

### 4-B. 마이그레이션 스크립트

파일: `tools/migrate_inquiries_to_jobs.py`

```python
"""
client_inquiries 1,227건 → jobs 테이블 마이그레이션.
dry-run 먼저, 결과 확인 후 실행.

사용법:
  python tools/migrate_inquiries_to_jobs.py --dry-run
  python tools/migrate_inquiries_to_jobs.py --execute
"""
import sqlite3
import sys
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("Q:/Claudework/bridge base/master.db")

# ─── 컬럼 매핑 (PHASE 4-A 결과 기반으로 수정할 것) ───
# client_inquiries 컬럼명 → jobs 컬럼명
COLUMN_MAP = {
    # 실제 컬럼명은 PHASE 4-A 보고 후 수정
    # "ci_컬럼": "jobs_컬럼",
    "location": "city",
    "teaching_age": "teaching_age",
    "salary": "monthly_salary",
    "working_hours": "working_hours",
    "housing": "housing",
    "benefits": "benefits",
    "vacation": "vacation",
    "class_size": "class_size",
    "starting_date": "starting_date",
    "memo": "memo",
    "status": "status",
    # PII (암호화 필드)
    "company_name": "enc_company_name",
    "contact_name": "enc_contact_name",
    "contact_email": "enc_contact_email",
    "contact_phone": "enc_contact_phone",
}


def migrate(dry_run=True):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # 기존 jobs job_number 최대값
    max_jn = conn.execute("SELECT COALESCE(MAX(job_number),0) FROM jobs").fetchone()[0]

    # client_inquiries 전체
    ci_rows = conn.execute("SELECT * FROM client_inquiries").fetchall()
    ci_cols = [desc[0] for desc in conn.execute("PRAGMA table_info(client_inquiries)").fetchall()]

    # jobs 컬럼 목록
    j_cols = [desc[1] for desc in conn.execute("PRAGMA table_info(jobs)").fetchall()]

    migrated = 0
    skipped = 0
    errors = []

    for ci in ci_rows:
        ci_dict = dict(ci)

        # 중복 체크: 같은 company_name + city 이미 jobs에 있는지
        # (암호화되어 있으면 비교 불가 → job_number 기반으로만)
        # 간단한 중복 체크: ci에 자체 ID가 있으면 그걸로
        ci_id = ci_dict.get("id") or ci_dict.get("inquiry_id")

        # 이미 마이그레이션된 건 스킵 (memo에 마킹)
        existing = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE memo LIKE ?",
            (f"%[migrated:ci_{ci_id}]%",)
        ).fetchone()[0]
        if existing > 0:
            skipped += 1
            continue

        # 새 job_number 발급
        max_jn += 1
        new_jn = max_jn

        # 컬럼 매핑
        job_data = {"job_number": new_jn}
        for ci_col, j_col in COLUMN_MAP.items():
            if ci_col in ci_dict and j_col in j_cols:
                val = ci_dict[ci_col]
                if val is not None:
                    job_data[j_col] = val

        # 마이그레이션 마킹
        job_data["memo"] = (job_data.get("memo","") or "") + f"\n[migrated:ci_{ci_id}] {datetime.now().strftime('%Y-%m-%d')}"

        if dry_run:
            print(f"  [DRY] Job#{new_jn} ← ci_{ci_id}: city={job_data.get('city','?')}")
            migrated += 1
        else:
            try:
                cols_str = ", ".join(job_data.keys())
                placeholders = ", ".join(["?"] * len(job_data))
                conn.execute(
                    f"INSERT INTO jobs ({cols_str}) VALUES ({placeholders})",
                    list(job_data.values())
                )
                migrated += 1
            except Exception as e:
                errors.append(f"ci_{ci_id}: {e}")

    if not dry_run:
        conn.commit()

    conn.close()

    print(f"\n{'[DRY-RUN]' if dry_run else '[EXECUTED]'}")
    print(f"  마이그레이션: {migrated}건")
    print(f"  스킵 (중복): {skipped}건")
    print(f"  에러: {len(errors)}건")
    for e in errors[:5]:
        print(f"    {e}")

    return migrated, skipped, errors


if __name__ == "__main__":
    dry = "--execute" not in sys.argv
    if not dry:
        confirm = input("실행 모드. DB에 직접 쓰기. 계속? (yes/no): ")
        if confirm.lower() != "yes":
            print("취소됨.")
            sys.exit(0)
    migrate(dry_run=dry)
```

### 4-C. 실행

```bash
# 1. 컬럼 매핑 확인 (PHASE 4-A 결과 기반으로 COLUMN_MAP 수정 후)
# 2. dry-run
python tools/migrate_inquiries_to_jobs.py --dry-run

# 3. 결과 확인 후 실행
python tools/migrate_inquiries_to_jobs.py --execute

# 4. 검증
python -c "
import sqlite3
conn = sqlite3.connect('master.db')
cnt = conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
mi = conn.execute(\"SELECT COUNT(*) FROM jobs WHERE memo LIKE '%migrated:ci_%'\").fetchone()[0]
print(f'jobs 총: {cnt}건 (마이그레이션: {mi}건)')
conn.close()
"
```

### 4-D. PHASE 4 커밋

```bash
git add tools/migrate_inquiries_to_jobs.py
git commit -m "feat: client_inquiries → jobs 마이그레이션 스크립트 + 실행"
```

---

## ██ PHASE 5: /inquiry 폼 → FastAPI 직접 저장 (🟠) ██

### 5-A. 현재 /inquiry 폼 제출 흐름 확인

```bash
# 프론트에서 inquiry 폼이 어디로 POST하는지
grep -rn "inquiry\|submit\|onSubmit\|handleSubmit" web_frontend/src/app/inquiry/ --include="*.tsx" --include="*.jsx" | head -20
grep -rn "/api.*inquiry\|/api.*employer.*register" web_frontend/src/ --include="*.ts" --include="*.tsx" | head -10

# 백엔드에 inquiry 관련 엔드포인트
grep -n "inquiry\|employer.*register" api_server.py | head -10
```

### 5-B. FastAPI 엔드포인트 (없으면 생성)

```python
@app.post("/api/employers/register")
async def register_employer_inquiry(request: Request, background_tasks: BackgroundTasks):
    """
    /inquiry 폼 제출 → jobs 테이블 + 관리자 알림.
    Google Forms와 병행 운영 (2주 후 Forms 비활성화).
    """
    data = await request.json()

    # 입력 검증
    required = ["contact_email", "contact_name", "school_name"]
    for f in required:
        if not data.get(f):
            raise HTTPException(400, f"필수 항목 누락: {f}")

    # Sanitize
    def sanitize(v):
        if not isinstance(v, str): return v
        return v.replace("<","&lt;").replace(">","&gt;").replace("'","&#39;").strip()

    data = {k: sanitize(v) if isinstance(v, str) else v for k, v in data.items()}

    conn = get_db()

    # 새 job_number 발급
    max_jn = conn.execute("SELECT COALESCE(MAX(job_number),0) FROM jobs").fetchone()[0]
    new_jn = max_jn + 1

    # PII 암호화
    enc_fields = {}
    for plain_key, enc_key in [
        ("school_name", "enc_company_name"),
        ("contact_name", "enc_contact_name"),
        ("contact_email", "enc_contact_email"),
        ("contact_phone", "enc_contact_phone"),
        ("address", "enc_address"),
        ("kakao", "enc_kakao"),
    ]:
        val = data.get(plain_key, "")
        if val:
            try:
                enc_fields[enc_key] = encrypt_field(val)
            except:
                enc_fields[enc_key] = val  # 암호화 실패 시 원문 (개발 모드)

    # INSERT
    conn.execute("""
        INSERT INTO jobs (
            job_number, region, city, teaching_age, working_hours,
            monthly_salary, starting_date, status,
            enc_company_name, enc_contact_name, enc_contact_email, enc_contact_phone,
            memo, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, datetime('now','localtime'))
    """, (
        new_jn,
        data.get("region", ""),
        data.get("city", ""),
        data.get("teaching_age", ""),
        data.get("working_hours", ""),
        data.get("monthly_salary", ""),
        data.get("starting_date", ""),
        enc_fields.get("enc_company_name", ""),
        enc_fields.get("enc_contact_name", ""),
        enc_fields.get("enc_contact_email", ""),
        enc_fields.get("enc_contact_phone", ""),
        f"[웹접수] {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    ))
    conn.commit()

    # 관리자 알림 (백그라운드)
    background_tasks.add_task(
        _send_admin_notification,
        f"[BRIDGE] 신규 구인 접수 — Job#{new_jn}",
        f"업체: {data.get('school_name','')}\n담당: {data.get('contact_name','')}\n이메일: {data.get('contact_email','')}"
    )

    # 접수 안내메일 (백그라운드)
    contact_email = data.get("contact_email", "")
    if contact_email:
        background_tasks.add_task(
            _send_one_email, "naver", contact_email,
            "[BRIDGE] 구인 신청 접수 완료",
            f"<p>안녕하세요, BRIDGE입니다.</p><p>구인 신청이 정상 접수되었습니다.</p><p>접수번호: Job#{new_jn}</p><p>빠른 시일 내 연락드리겠습니다.</p><p>감사합니다.<br>BRIDGE Recruitment Team</p>"
        )

    return {"ok": True, "job_number": new_jn}


async def _send_admin_notification(subject: str, body: str):
    """관리자에게 간단 알림메일"""
    try:
        _send_one_email("gmail", "bridgejobkr@gmail.com", subject, f"<pre>{body}</pre>")
    except:
        pass  # 알림 실패해도 접수 자체는 성공
```

### 5-C. 프론트 /inquiry 폼 연결

```
/inquiry 페이지의 onSubmit 핸들러를 찾아서:

현재 Google Forms로 POST하고 있으면 → FastAPI로 변경:
  const res = await fetch("/api/employers/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(formData),
  });

★ Google Forms URL은 주석으로 보존 (2주 병행 후 제거):
  // [LEGACY] Google Forms: https://docs.google.com/forms/...
```

### 5-D. PHASE 5 커밋

```bash
python -c "import ast; ast.parse(open('api_server.py',encoding='utf-8').read()); print('OK')"
npm run build 2>&1 | tail -5
git add api_server.py web_frontend/src/app/inquiry/
git commit -m "feat: /inquiry → FastAPI 직접 저장 + 안내메일 + 관리자 알림"
```

---

## ██ PHASE 6: PII 엔진 버그 수정 (🟠) ██

```
★ PII 엔진 수정은 별도 명령서 PII_ENGINE_FIX.md에 상세 기술됨.
★ 이 PHASE에서는 해당 파일의 존재 여부만 확인하고,
   tools/resume_converter/ 디렉토리가 있으면 수정 진행.
   없으면 스킵.
```

```bash
# PII 엔진 파일 위치
find . -name "pii_engine.py" -o -name "text_cleaner.py" -o -name "*pii*" | grep -v node_modules | grep -v .next

# 있으면: PII_ENGINE_FIX.md의 7건 수정 적용
# 없으면: 이 PHASE 스킵 → "PII 엔진 파일 미발견, 스킵" 보고
```

수정할 경우 핵심 변경점만:
```
1. University/College 포함 → 삭제 스킵
2. Education 섹션 내 학위/전공 → 삭제 금지
3. Middle School/High School/English Language → 직함 보호
4. 한국 도시 → "South Korea"만 남김
5. 한국 업체 → "English Academy" 교체 (빈칸 금지)
6. "English" 단독 → 삭제 금지
7. 해외 교육기관 → 보존
```

```bash
# 수정 후
python -m py_compile tools/resume_converter/pii_engine.py 2>/dev/null && echo "pii OK" || echo "pii 없음"
git add tools/resume_converter/ 2>/dev/null
git commit -m "fix: PII엔진 7건 — 대학보존/도시삭제/업체교체" 2>/dev/null
```

---

## ██ PHASE 7: RPA + Calendar + 최종 정리 (🟡) ██

### 7-A. RPA overlay 수정 (파일 있으면)

```bash
# rpa_overlay.py 확인
ls rpa_overlay.py 2>/dev/null
```

있으면:
```python
# 수정 1: show_complete()를 데몬 스레드로 분리
#   기존: root.after(0, show_complete)
#   변경: threading.Thread(target=show_complete, daemon=True).start()

# 수정 2: 이모지 텍스트 전체 교체 (GDI deadlock 방지)
#   기존: label.config(text="✅ 완료!")
#   변경: label.config(text="[OK] Complete")
#   
#   모든 이모지(✅🔴🟢⚠️🎉 등) → ASCII 텍스트로 교체

# [RULE-TKINTER] 윈도우즈에서 Tkinter 위젯에 이모지 사용 금지
```

### 7-B. Google Calendar Service Account 안내

```bash
# interview_calendar.py 존재 확인
ls interview_calendar.py 2>/dev/null

# SA 키 존재 확인
ls "Q:\Claudework\.vault\google_service_account.json" 2>/dev/null
```

SA 키가 없으면 아래 안내 출력:
```
[안내] Google Calendar Meet 자동생성을 위해:
1. Google Cloud Console → Calendar API 활성화
2. Service Account 생성 → JSON 키 다운로드
3. Q:\Claudework\.vault\google_service_account.json 에 저장
4. Google Calendar 설정 → Service Account 이메일 초대 (편집 권한)
5. .env에 GOOGLE_CALENDAR_ID=bridgejobkr@gmail.com

※ 없어도 인터뷰 시스템 동작함 (Meet 링크 수동 입력)
```

### 7-C. Render 유료 전환 메모

```
# 코드 수정 아님 — 정보 출력만
echo "=== Render 유료 전환 권장사항 ==="
echo "현재: Free tier — cold start 30~60초, 디스크 불안정"
echo "권장: Starter ($7/월) — always on, 영구 디스크"
echo "효과: cold start 제거, DB 안정성 확보, autoDeploy 활용 가능"
echo "전환: Render 대시보드 → Settings → Instance Type → Starter"
```

---

## ██ PHASE 8: 최종 검증 + PUSH ██

```bash
cd "Q:\Claudework\bridge base"

echo "═══ 최종 검증 ═══"

# 1. api_server.py 문법
python -c "import ast; ast.parse(open('api_server.py',encoding='utf-8').read()); print('api_server: OK')"

# 2. 프론트 빌드
cd web_frontend && npm run build 2>&1 | tail -3 && cd ..

# 3. DB 무결성
python -c "
import sqlite3
conn = sqlite3.connect('master.db')
integrity = conn.execute('PRAGMA integrity_check').fetchone()[0]
print(f'DB integrity: {integrity}')
for t in ['jobs','candidates','interviews','profile_sends']:
    cnt = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    print(f'  {t}: {cnt}건')
conn.close()
"

# 4. Git 상태
git log --oneline -10
echo ""
git status --short

# 5. 커밋 로그 확인 후 push
echo ""
echo "═══ PUSH 준비 ═══"
echo "render.yaml autoDeploy=false 확인됨 → push해도 Render 자동 배포 안 됨"
echo "Render 수동 배포 필요 시: 대시보드 → Manual Deploy"
echo ""

git push origin main
```

---

## ██ 완료 보고 형식 ██

```
모든 PHASE 완료 후 아래 형식으로 보고:

═══ 전체 안정화 완료 ═══
날짜: YYYY-MM-DD HH:MM KST

PHASE 0: 백업 + 진단          → ✅/❌
PHASE 1: 서비스 안정성         → ✅/❌ (autoDeploy, 백업, 미커밋)
PHASE 2: API URL + CORS        → ✅/❌
PHASE 3: DISABLED 정리 + nationality → ✅/❌
PHASE 4: 마이그레이션          → ✅/❌ (N건 이관)
PHASE 5: /inquiry 직접 저장    → ✅/❌
PHASE 6: PII 엔진             → ✅/❌/스킵
PHASE 7: RPA + Calendar        → ✅/❌/스킵
PHASE 8: 최종 검증 + push     → ✅/❌

커밋 해시: [각 PHASE별]
Push: main → main

사용자 수동 조치:
  □ Render BRIDGE_FIELD_KEY 확인
  □ GAS 설치 (Apps Script)
  □ Google Calendar SA 키 (선택)
  □ Render 수동 배포 (필요 시)
```
