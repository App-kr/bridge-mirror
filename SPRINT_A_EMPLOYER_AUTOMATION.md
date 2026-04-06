# SPRINT A — 구인자 자동화 핵심 연동 (Claude Code 투입용)

> **이 파일을 Claude Code에 첨부 후 "순서대로 작업해줘" 한마디면 끝**
> 
> 작업 범위: profile_sends 연동 + 네이버 SMTP 추가 + 자동저장
> 예상 소요: 작업 3개, 총 ~45분
> 위험도: 낮음 (신규 테이블/엔드포인트 추가만, 기존 코드 수정 최소)

---

## ██ 0. PRE-FLIGHT (작업 전 필수) ██

```bash
# 0-1. 백업 — 무조건 먼저
cd "Q:\Claudework\bridge base"
git add -A && git stash
git log --oneline -3

# 0-2. DB 안전 백업 (master.db 복사)
copy master.db "master_backup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%.db"

# 0-3. 현재 상태 확인 (5초)
python -c "
import sqlite3
conn = sqlite3.connect('master.db')
cur = conn.cursor()

# 테이블 확인
for t in ['jobs','candidates','profile_sends','mail_logs']:
    try:
        cnt = cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
        print(f'{t}: {cnt}건')
    except: print(f'{t}: 없음')

# profile_sends 스키마 확인
try:
    cols = cur.execute('PRAGMA table_info(profile_sends)').fetchall()
    print(f'profile_sends 컬럼: {[c[1] for c in cols]}')
except: print('profile_sends: 테이블 없음')

conn.close()
"

# 0-4. api_server.py 기존 메일 관련 코드 확인
python -c "
import ast
t = open('api_server.py', encoding='utf-8').read()
ast.parse(t)
print('api_server.py 문법 OK')
for kw in ['profile_sends','send-mail','send_mail','/api/admin/mail','smtp','SMTP']:
    if kw in t: print(f'  발견: {kw}')
    else: print(f'  없음: {kw}')
"
```

**0-3 결과를 보고한 후 STEP 1로 진행.**  
profile_sends가 이미 존재하면 ALTER가 아니라 기존 스키마에 맞춰서 작업.

---

## ██ 1. profile_sends 테이블 연동 (발송 이력 추적) ██

### 1-1. 테이블 생성 (없는 경우만)

`api_server.py`의 DB 초기화 함수(`init_db` 또는 마이그레이션 블록)에 추가:

```sql
CREATE TABLE IF NOT EXISTS profile_sends (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id    TEXT NOT NULL,
    candidate_number INTEGER,
    employer_job_id INTEGER,
    employer_name   TEXT,
    employer_email  TEXT,
    subject         TEXT,
    template_used   TEXT DEFAULT 'profile_broadcast',
    sender_email    TEXT,
    attachments     TEXT,
    status          TEXT DEFAULT 'sent' CHECK(status IN ('sent','failed','bounced')),
    error_message   TEXT,
    sent_at         DATETIME DEFAULT (datetime('now','localtime')),
    created_at      DATETIME DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_ps_candidate ON profile_sends(candidate_id);
CREATE INDEX IF NOT EXISTS idx_ps_employer ON profile_sends(employer_job_id);
CREATE INDEX IF NOT EXISTS idx_ps_sent_at ON profile_sends(sent_at);
```

### 1-2. 발송 기록 API 엔드포인트 (3개)

`api_server.py`에 추가:

```python
# ─── 발송 이력 기록 ─────────────────────────────────────────
@app.post("/api/admin/profile-sends")
async def record_profile_send(request: Request):
    """메일 발송 성공 시 프론트에서 호출하여 이력 기록"""
    _check_admin(request)
    data = await request.json()

    required = ["candidate_id", "employer_email", "subject"]
    for field in required:
        if not data.get(field):
            raise HTTPException(400, f"필수 필드 누락: {field}")

    conn = get_db()
    conn.execute("""
        INSERT INTO profile_sends
        (candidate_id, candidate_number, employer_job_id, employer_name,
         employer_email, subject, template_used, sender_email, attachments, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("candidate_id"),
        data.get("candidate_number"),
        data.get("employer_job_id"),
        data.get("employer_name"),
        data["employer_email"],
        data["subject"],
        data.get("template_used", "profile_broadcast"),
        data.get("sender_email", "bridgejobkr@naver.com"),
        data.get("attachments", ""),
        data.get("status", "sent"),
    ))
    conn.commit()
    return {"ok": True, "message": "발송 이력 기록 완료"}


# ─── 발송 이력 조회 ─────────────────────────────────────────
@app.get("/api/admin/profile-sends")
async def get_profile_sends(request: Request):
    """발송 이력 목록 — 최근 100건"""
    _check_admin(request)
    conn = get_db()
    rows = conn.execute("""
        SELECT id, candidate_id, candidate_number, employer_name,
               employer_email, subject, template_used, sender_email,
               status, sent_at
        FROM profile_sends
        ORDER BY sent_at DESC
        LIMIT 100
    """).fetchall()
    cols = ["id","candidate_id","candidate_number","employer_name",
            "employer_email","subject","template_used","sender_email",
            "status","sent_at"]
    return {"sends": [dict(zip(cols, r)) for r in rows]}


# ─── 중복 발송 체크 ─────────────────────────────────────────
@app.get("/api/admin/profile-sends/check-duplicate")
async def check_duplicate_send(request: Request):
    """동일 candidate+employer 조합 24시간 내 발송 여부 확인"""
    _check_admin(request)
    candidate_id = request.query_params.get("candidate_id")
    employer_email = request.query_params.get("employer_email")

    if not candidate_id or not employer_email:
        raise HTTPException(400, "candidate_id, employer_email 필수")

    conn = get_db()
    exists = conn.execute("""
        SELECT COUNT(*) FROM profile_sends
        WHERE candidate_id = ? AND employer_email = ?
          AND sent_at >= datetime('now','localtime','-24 hours')
          AND status = 'sent'
    """, (candidate_id, employer_email)).fetchone()[0]

    return {"duplicate": exists > 0, "count": exists}
```

### 1-3. 검증

```bash
# 문법 확인
python -c "import ast; ast.parse(open('api_server.py',encoding='utf-8').read()); print('OK')"

# 테이블 생성 확인
python -c "
import sqlite3
conn = sqlite3.connect('master.db')
cols = conn.execute('PRAGMA table_info(profile_sends)').fetchall()
print(f'profile_sends 컬럼 {len(cols)}개: {[c[1] for c in cols]}')
conn.close()
"

# 커밋
git add api_server.py
git commit -m "feat: profile_sends 연동 — 발송이력 기록/조회/중복체크 API"
```

---

## ██ 2. 네이버 SMTP 발신자 추가 ██

### 2-1. 현재 SMTP 코드 위치 확인

```bash
grep -rn "smtp\|SMTP\|smtplib\|send.mail\|send_mail" api_server.py --include="*.py" | head -20
grep -rn "smtp\|SMTP" *.py | head -20
```

### 2-2. 발신자 분기 로직

기존 `/api/send-mail` 또는 `/api/admin/mail/send` 엔드포인트를 찾아서,
sender 파라미터에 따라 SMTP 서버를 분기하는 로직 추가:

```python
# 이미 존재하는 메일 발송 엔드포인트를 찾아서 아래 로직으로 보강
# (새로 만드는 게 아님 — 기존 코드에 병합)

import os, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

SMTP_PROVIDERS = {
    "naver": {
        "host": "smtp.naver.com",
        "port": 465,
        "use_ssl": True,       # 네이버는 SSL 직접 연결
        "user_env": "NAVER_SMTP_USER",
        "pass_env": "NAVER_SMTP_PASS",
        "daily_limit": 500,
    },
    "gmail": {
        "host": "smtp.gmail.com",
        "port": 587,
        "use_ssl": False,      # Gmail은 STARTTLS
        "user_env": "GMAIL_SMTP_USER",
        "pass_env": "GMAIL_SMTP_PASS",
        "daily_limit": 100,
    },
}


def _send_one_email(provider_key: str, to_email: str, subject: str,
                    html_body: str, attachments: list[str] = None) -> dict:
    """
    단일 메일 발송. 성공 시 {"ok": True}, 실패 시 {"ok": False, "error": "..."}
    attachments: 파일 경로 리스트 (PII 제거 이력서 등)
    """
    cfg = SMTP_PROVIDERS.get(provider_key)
    if not cfg:
        return {"ok": False, "error": f"알 수 없는 발신자: {provider_key}"}

    user = os.getenv(cfg["user_env"], "")
    pwd  = os.getenv(cfg["pass_env"], "")
    if not user or not pwd:
        return {"ok": False, "error": f"{provider_key} SMTP 자격증명 미설정"}

    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"]    = f"BRIDGE Recruitment <{user}>"
        msg["To"]      = to_email

        # HTML 본문
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # 첨부파일
        if attachments:
            for fpath in attachments:
                if not os.path.isfile(fpath):
                    continue
                with open(fpath, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                fname = os.path.basename(fpath)
                part.add_header("Content-Disposition", f"attachment; filename=\"{fname}\"")
                msg.attach(part)

        # 발송
        if cfg["use_ssl"]:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=15) as server:
                server.login(user, pwd)
                server.sendmail(user, to_email, msg.as_string())
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
                server.starttls()
                server.login(user, pwd)
                server.sendmail(user, to_email, msg.as_string())

        return {"ok": True}

    except smtplib.SMTPAuthenticationError:
        return {"ok": False, "error": "SMTP 인증 실패 — 앱 비밀번호 확인"}
    except smtplib.SMTPRecipientsRefused:
        return {"ok": False, "error": f"수신 거부: {to_email}"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
```

### 2-3. 통합 발송 엔드포인트 (기존 것 교체 또는 신규)

```python
@app.post("/api/admin/mail/send-profile")
async def send_profile_mail(request: Request):
    """
    소개발송 전용 — 1:1 개별 발송 + profile_sends 자동 기록
    body: {
        sender: "naver" | "gmail",
        candidate_id: "cnd_xxx",
        candidate_number: 5681,
        recipients: [
            {"email": "school@email.com", "name": "해피학원", "job_id": 1003}
        ],
        subject: "📢 BRIDGE 원어민 강사 소식",
        html_body: "<p>...</p>",
        attachment_paths: ["tools/processed_docs/processed/5681_USA_F_99.pdf"]
    }
    """
    _check_admin(request)
    data = await request.json()

    sender     = data.get("sender", "naver")
    recipients = data.get("recipients", [])
    subject    = data.get("subject", "")
    html_body  = data.get("html_body", "")
    candidate_id     = data.get("candidate_id", "")
    candidate_number = data.get("candidate_number")
    att_paths  = data.get("attachment_paths", [])

    if not recipients:
        raise HTTPException(400, "수신자 없음")
    if len(recipients) > 99:
        raise HTTPException(400, "1회 최대 99명")

    # 일일 한도 체크
    conn = get_db()
    today_sent = conn.execute("""
        SELECT COUNT(*) FROM profile_sends
        WHERE DATE(sent_at) = DATE('now','localtime')
          AND sender_email LIKE ?
    """, (f"%{sender}%",)).fetchone()[0]

    limit = SMTP_PROVIDERS.get(sender, {}).get("daily_limit", 500)
    if today_sent + len(recipients) > limit:
        raise HTTPException(429, f"일일 한도 초과: 오늘 {today_sent}건 발송, 한도 {limit}건")

    results = {"sent": 0, "failed": 0, "errors": []}

    for rcpt in recipients:
        email = rcpt.get("email", "").strip()
        if not email:
            continue

        # 중복 체크 (24시간)
        dup = conn.execute("""
            SELECT COUNT(*) FROM profile_sends
            WHERE candidate_id = ? AND employer_email = ?
              AND sent_at >= datetime('now','localtime','-24 hours')
              AND status = 'sent'
        """, (candidate_id, email)).fetchone()[0]

        status = "sent"
        error_msg = ""

        if dup > 0:
            status = "skipped"
            error_msg = "24시간 내 중복"
            results["failed"] += 1
            results["errors"].append({"email": email, "error": error_msg})
        else:
            # 실제 발송
            result = _send_one_email(sender, email, subject, html_body, att_paths)
            if result["ok"]:
                results["sent"] += 1
            else:
                status = "failed"
                error_msg = result.get("error", "")
                results["failed"] += 1
                results["errors"].append({"email": email, "error": error_msg})

        # profile_sends 기록 (성공/실패/스킵 모두)
        conn.execute("""
            INSERT INTO profile_sends
            (candidate_id, candidate_number, employer_job_id, employer_name,
             employer_email, subject, template_used, sender_email,
             attachments, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            candidate_id,
            candidate_number,
            rcpt.get("job_id"),
            rcpt.get("name", ""),
            email,
            subject,
            "profile_broadcast",
            sender,
            ",".join(att_paths) if att_paths else "",
            status,
            error_msg,
        ))

    conn.commit()
    results["today_total"] = today_sent + results["sent"]
    results["daily_limit"] = limit
    return results
```

### 2-4. 환경변수 확인

```bash
# .env에 아래 4개 존재하는지 확인
grep -c "NAVER_SMTP_USER\|NAVER_SMTP_PASS\|GMAIL_SMTP_USER\|GMAIL_SMTP_PASS" .env

# 없으면 추가 (실제 비밀번호는 사용자가 직접 입력)
# echo "NAVER_SMTP_USER=bridgejobkr@naver.com" >> .env
# echo "NAVER_SMTP_PASS=" >> .env
# ⚠️ 비밀번호는 사용자가 직접 입력할 것 — 절대 코드에 하드코딩 금지
```

### 2-5. 검증

```bash
python -c "import ast; ast.parse(open('api_server.py',encoding='utf-8').read()); print('OK')"
git add api_server.py
git commit -m "feat: 네이버/Gmail SMTP 분기 + 소개발송 통합 엔드포인트"
```

---

## ██ 3. 프론트엔드 자동저장 + profile_sends 연동 ██

### 3-1. MailComposer 발송 후 자동 기록

EmployerManagement.jsx (또는 .tsx)의 MailComposer 컴포넌트에서
실제 발송 성공 후 `profile_sends` API를 호출하도록 연결:

```
기존 MailComposer의 발송 함수를 찾아라.
"fetch" 또는 "axios" 로 /api/send-mail 또는 /api/admin/mail/send 호출하는 부분.

그 성공 콜백 안에 아래를 추가:

// 발송 성공 후 이력 기록
try {
  await fetch("/api/admin/profile-sends", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      candidate_id: selectedCandidate?.id || "",
      candidate_number: selectedCandidate?.number || null,
      employer_email: recipientEmail,
      employer_name: recipientName || "",
      employer_job_id: recipientJobId || null,
      subject: emailSubject,
      template_used: currentTemplate,
      sender_email: selectedSender,
      status: "sent",
    }),
  });
} catch (e) {
  console.error("발송 이력 기록 실패:", e);
  // 이력 기록 실패해도 발송 자체는 성공 — 사용자에게 경고만
}
```

### 3-2. 중복 발송 경고

MailComposer에서 발송 버튼 클릭 시, 발송 전에 중복 체크:

```
// 발송 전 중복 체크
const checkDuplicate = async (candidateId, email) => {
  try {
    const res = await fetch(
      `/api/admin/profile-sends/check-duplicate?candidate_id=${candidateId}&employer_email=${encodeURIComponent(email)}`
    );
    const data = await res.json();
    if (data.duplicate) {
      return window.confirm(
        `⚠️ 이 업체에 24시간 내 이미 발송한 이력이 있습니다.\n정말 다시 발송하시겠습니까?`
      );
    }
    return true;
  } catch {
    return true; // 체크 실패 시 발송 허용
  }
};
```

### 3-3. 엑셀뷰 인라인 수정 자동저장

엑셀뷰에서 셀 편집 후 blur/Enter 시 자동 PATCH:

```
// EditCell onBlur 핸들러에 추가
const autoSave = async (jobNumber, field, value) => {
  try {
    await fetch(`/api/admin/jobs/v2/${jobNumber}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ [field]: value }),
    });
  } catch (e) {
    console.error("자동저장 실패:", e);
    // 실패 시 셀에 빨간 테두리로 시각적 피드백
  }
};
```

**⚠️ 주의**: PATCH 엔드포인트 `/api/admin/jobs/v2/{jobNumber}`가 이미 존재하는지 확인.
없으면 아래 추가:

```python
@app.patch("/api/admin/jobs/v2/{job_number}")
async def update_job_field(job_number: int, request: Request):
    """단일 필드 인라인 수정 — 자동저장용"""
    _check_admin(request)
    data = await request.json()

    # 허용 필드 화이트리스트
    ALLOWED = {
        "region", "city", "teaching_age", "working_hours", "monthly_salary",
        "avg_teaching_hours", "vacation", "native_teacher_count", "housing",
        "qualifications", "benefits", "starting_date", "memo", "status",
        "enc_contact_name", "enc_contact_email", "enc_contact_phone",
        "enc_company_name", "enc_memo",
    }

    updates = []
    values = []
    for key, val in data.items():
        if key not in ALLOWED:
            raise HTTPException(400, f"수정 불가 필드: {key}")
        # enc_ 접두사 필드는 암호화 처리
        if key.startswith("enc_"):
            val = encrypt_value(val)  # 기존 암호화 함수 사용
        updates.append(f"{key} = ?")
        values.append(val)

    if not updates:
        raise HTTPException(400, "수정할 필드 없음")

    values.append(job_number)
    conn = get_db()
    conn.execute(
        f"UPDATE jobs SET {', '.join(updates)}, updated_at = datetime('now','localtime') WHERE job_number = ?",
        values,
    )
    conn.commit()
    return {"ok": True, "updated": list(data.keys())}
```

### 3-4. 검증

```bash
python -c "import ast; ast.parse(open('api_server.py',encoding='utf-8').read()); print('OK')"
git add -A
git commit -m "feat: 자동저장 PATCH + 발송이력 연동 + 중복체크"
```

---

## ██ 4. POST-FLIGHT (작업 완료 확인) ██

```bash
# 4-1. 전체 문법 확인
python -c "import ast; ast.parse(open('api_server.py',encoding='utf-8').read()); print('api_server.py OK')"

# 4-2. DB 테이블 확인
python -c "
import sqlite3
conn = sqlite3.connect('master.db')
for t in ['profile_sends','mail_logs','jobs','candidates']:
    cnt = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    print(f'{t}: {cnt}건')
cols = conn.execute('PRAGMA table_info(profile_sends)').fetchall()
print(f'profile_sends 컬럼: {[c[1] for c in cols]}')
conn.close()
"

# 4-3. 커밋 로그 확인
git log --oneline -5

# 4-4. 최종 보고
echo "=== SPRINT A 완료 ==="
echo "1. profile_sends 테이블 + API 3개 (기록/조회/중복체크)"
echo "2. 네이버/Gmail SMTP 분기 + 소개발송 통합 엔드포인트"
echo "3. 자동저장 PATCH 엔드포인트"
echo "4. MailComposer 발송 후 자동 이력 기록"
```

---

## ██ 보안 체크리스트 ██

| 항목 | 상태 |
|------|------|
| SQL Injection | ✅ parameterized query 전용 |
| PII 노출 | ✅ enc_ 필드 암호화 유지, 외부 API 마스킹 |
| SMTP 자격증명 | ✅ 환경변수만, 하드코딩 금지 |
| 일일 한도 | ✅ DB 기반 카운팅, 프로바이더별 분리 |
| 중복 발송 | ✅ 24시간 윈도우 체크 |
| 인증 | ✅ _check_admin 모든 엔드포인트 적용 |
| DB 무결성 | ✅ WAL 모드, 트랜잭션 commit |
| 필드 화이트리스트 | ✅ PATCH 허용 필드 제한 |
| 에러 핸들링 | ✅ 발송 실패해도 이력 기록, 사용자에게 결과 반환 |

---

## ██ 배포 주의사항 ██

- `api_server.py` 수정 → Render 자동 배포 트리거됨
- **git push 전에 반드시 확인**: `python -c "import ast; ast.parse(...)"`
- **Render 환경변수에도 NAVER_SMTP_USER/PASS 추가 필요**
- push 후 Render 대시보드에서 빌드 성공 확인

---

## ██ 다음 Sprint B 예고 ██

Sprint A 완료 후 다음 작업:
1. PII 제거 이력서 PDF 자동 첨부 (processed_docs/ → 메일)
2. 지역/연령 매칭 필터 (candidate ↔ jobs 크로스 매칭)
3. 엑셀 다운로드 (한글 인코딩)
