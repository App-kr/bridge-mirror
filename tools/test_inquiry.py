"""Inquiry Form -> client_inquiries + jobs 매핑 테스트
구인자관리(EmployerManagement)가 읽는 jobs 테이블까지 검증
"""
import sqlite3
import json
import re
from datetime import datetime, timezone

DB = "Q:/Claudework/bridge base/master.db"

# ── api_server.py 동일: _auto_create_job_from_inquiry 로직 재현 ──
def auto_create_job(conn, inquiry_id, school_name):
    """inquiry -> job 자동 생성 (api_server.py _auto_create_job_from_inquiry 동일 로직)"""
    inq = conn.execute("SELECT * FROM client_inquiries WHERE id = ?", (inquiry_id,)).fetchone()
    if not inq:
        return None

    salary_raw = inq["salary_raw"] or ""
    salary_nums = re.findall(r"[\d,.]+", salary_raw.replace(",", ""))
    salary_min = float(salary_nums[0]) if salary_nums else None
    salary_max = float(salary_nums[-1]) if len(salary_nums) > 1 else salary_min

    wh = inq["working_hours"] or inq["schedule"] or ""
    daily_hours = None
    tm = re.search(r"(\d{1,2}):?(\d{2})\s*[~\-]\s*(\d{1,2}):?(\d{2})", wh)
    if tm:
        h1 = int(tm.group(1)) + int(tm.group(2)) / 60
        h2 = int(tm.group(3)) + int(tm.group(4)) / 60
        daily_hours = round(h2 - h1, 2) if h2 > h1 else None

    loc = inq["location"] or ""
    city = loc.split(",")[0].split(" ")[0].strip() if loc else ""

    memo_raw = inq["memo"] or ""
    internal_notes = memo_raw or f"({city} {school_name})"

    housing_val = inq["housing_detail"] or inq["housing_type"] or ""

    # raw_text 생성 (api_server.py 동일)
    raw_parts = [f"School: {school_name}", f"Location: {loc}"]
    if inq["start_date"]:  raw_parts.append(f"Starting Date : {inq['start_date']}")
    if inq["teaching_age"]: raw_parts.append(f"Teaching Age : {inq['teaching_age']}")
    if salary_raw:         raw_parts.append(f"Salary : {salary_raw}")
    if wh:                 raw_parts.append(f"Working Hours : {wh}")
    if housing_val:        raw_parts.append(f"Housing : {housing_val}")
    if inq["benefits"]:    raw_parts.append(f"Benefits : {inq['benefits']}")
    raw_text = "\n".join(raw_parts)

    # job_code
    max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM jobs").fetchone()[0]
    job_code = f"Job.{max_id + 1001}"

    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """INSERT INTO jobs (seq, job_code, location, city, start_date, teaching_age,
           working_hours, daily_hours, salary_min, salary_max, salary_raw,
           vacation, housing, benefits, status, is_hot, is_deleted, created_at,
           internal_notes, raw_text, employer_display_name)
           VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_review', 1, 0, ?, ?, ?, ?)""",
        (
            job_code, loc, city, inq["start_date"] or "", inq["teaching_age"] or "",
            wh, daily_hours, salary_min, salary_max, salary_raw,
            inq["vacation"] or "", housing_val,
            inq["benefits"] or "", now,
            internal_notes, raw_text, school_name,
        ),
    )
    conn.commit()
    return cur.lastrowid, job_code


# ── 테스트 데이터 (실제 구인 문의 양식) ──
TEST_INQUIRY = {
    "school_name":       "TEST_BridgeAcademy",
    "email":             "test_academy@example.com",
    "contact_name":      "Kim Test",
    "phone":             "010-1234-5678",
    "school_location":   "Seoul, Gangnam",
    "location":          "Seoul, Gangnam",
    "vacancies":         "2",
    "teaching_age":      "Elementary",
    "start_date":        "2026-05-01",
    "salary_raw":        "2,500,000 ~ 3,000,000 KRW",
    "working_hours":     "09:00 ~ 18:00",
    "schedule":          "Mon-Fri",
    "housing_type":      "Single apartment",
    "housing_detail":    "Near school, furnished",
    "benefits":          "Health insurance, pension",
    "vacation":          "10 days paid vacation",
    "sick_leave":        "5 days",
    "meal":              "Lunch provided",
    "memo":              "Seoul Gangnam TEST_BridgeAcademy Kim Test 010-1234-5678 test_academy@example.com",
    "source":            "web_form",
    "inbox_status":      "new",
}


print("=" * 60)
print("BRIDGE Inquiry -> client_inquiries + jobs Test")
print("=" * 60)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA busy_timeout = 5000")

inq_before = conn.execute("SELECT COUNT(*) FROM client_inquiries WHERE is_deleted IS NULL OR is_deleted = 0").fetchone()[0]
job_before = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_deleted = 0").fetchone()[0]
print(f"[Before] client_inquiries: {inq_before} | jobs: {job_before}")

# ── 1) INSERT into client_inquiries ──
print("\n[Test 1] INSERT client_inquiries:")
db_cols = {r[1] for r in conn.execute("PRAGMA table_info(client_inquiries)").fetchall()}
payload = dict(TEST_INQUIRY)
payload["submitted_at"] = datetime.now(timezone.utc).isoformat()

insert_payload = {}
extra_fields = {}
for k, v in payload.items():
    if k in db_cols:
        insert_payload[k] = v
    else:
        extra_fields[k] = v
if extra_fields:
    insert_payload["parsed_data"] = json.dumps(extra_fields, ensure_ascii=False)

cols_str = ", ".join(insert_payload.keys())
placeholders = ", ".join("?" * len(insert_payload))
cur = conn.execute(
    f"INSERT INTO client_inquiries ({cols_str}) VALUES ({placeholders})",
    list(insert_payload.values()),
)
conn.commit()
inq_id = cur.lastrowid
print(f"  [PASS] inquiry_id={inq_id}")

# ── 2) Verify client_inquiries ──
print("\n[Test 2] Verify client_inquiries mapping:")
inq_row = conn.execute("SELECT * FROM client_inquiries WHERE id = ?", (inq_id,)).fetchone()
inq_dict = dict(inq_row)

inq_checks = [
    ("school_name", "school_name"),
    ("location", "location"),
    ("vacancies", "vacancies"),
    ("teaching_age", "teaching_age"),
    ("start_date", "start_date"),
    ("salary_raw", "salary_raw"),
    ("working_hours", "working_hours"),
    ("schedule", "schedule"),
    ("housing_type", "housing_type"),
    ("housing_detail", "housing_detail"),
    ("benefits", "benefits"),
    ("vacation", "vacation"),
    ("sick_leave", "sick_leave"),
    ("meal", "meal"),
    ("memo", "memo"),
    ("source", "source"),
    ("inbox_status", "inbox_status"),
]

ip = 0
for form_f, db_col in inq_checks:
    sent = TEST_INQUIRY.get(form_f, "")
    got = inq_dict.get(db_col, "")
    ok = (got == sent)
    if ok:
        ip += 1
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {form_f:20s} -> {db_col:20s} = {str(got)[:40]}")
print(f"  => {ip}/{len(inq_checks)} passed")

# parsed_data에 저장된 추가 필드 확인
if inq_dict.get("parsed_data"):
    pd = json.loads(inq_dict["parsed_data"])
    print(f"\n  [parsed_data] extra fields: {list(pd.keys())}")
    for k, v in pd.items():
        print(f"    {k} = {str(v)[:40]}")

# ── 3) Auto-create job ──
print("\n[Test 3] Auto-create job from inquiry:")
result = auto_create_job(conn, inq_id, TEST_INQUIRY["school_name"])
if result:
    job_id, job_code = result
    print(f"  [PASS] job_id={job_id} job_code={job_code}")
else:
    job_id = None
    job_code = None
    print("  [FAIL] job creation failed")

# ── 4) Verify jobs mapping (= what EmployerManagement reads) ──
print("\n[Test 4] Verify jobs table (EmployerManagement data source):")
if job_id:
    job_row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    job_dict = dict(job_row)

    job_checks = [
        ("employer_display_name", TEST_INQUIRY["school_name"]),
        ("location", TEST_INQUIRY["location"]),
        ("teaching_age", TEST_INQUIRY["teaching_age"]),
        ("salary_raw", TEST_INQUIRY["salary_raw"]),
        ("salary_min", 2500000.0),
        ("salary_max", 3000000.0),
        ("working_hours", TEST_INQUIRY["working_hours"]),
        ("housing", "Near school, furnished"),  # housing_detail fallback
        ("benefits", TEST_INQUIRY["benefits"]),
        ("vacation", TEST_INQUIRY["vacation"]),
        ("start_date", TEST_INQUIRY["start_date"]),
        ("status", "pending_review"),
        ("job_code", job_code),
        ("is_hot", 1),
    ]

    jp = 0
    for db_col, expected in job_checks:
        got = job_dict.get(db_col)
        # float comparison
        if isinstance(expected, float):
            ok = got is not None and abs(float(got) - expected) < 0.01
        else:
            ok = str(got) == str(expected)
        if ok:
            jp += 1
        tag = "PASS" if ok else "FAIL"
        got_s = str(got)[:40] if got is not None else "(null)"
        print(f"  [{tag}] {db_col:20s} expected={str(expected)[:25]:25s} got={got_s}")

    # internal_notes PII 파서용 메모 확인
    inotes = job_dict.get("internal_notes", "")
    has_memo = bool(inotes)
    print(f"\n  [{'PASS' if has_memo else 'FAIL'}] internal_notes present: {str(inotes)[:50]}...")
    if has_memo:
        jp += 1

    total_job = len(job_checks) + 1
    print(f"  => {jp}/{total_job} passed")
else:
    jp = 0
    total_job = 1

# ── 5) Cleanup ──
print("\n[Cleanup]")
if job_id:
    conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
conn.execute("DELETE FROM client_inquiries WHERE id = ?", (inq_id,))
conn.commit()

inq_after = conn.execute("SELECT COUNT(*) FROM client_inquiries WHERE is_deleted IS NULL OR is_deleted = 0").fetchone()[0]
job_after = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_deleted = 0").fetchone()[0]
conn.close()

inq_ok = inq_after == inq_before
job_ok = job_after == job_before
print(f"  inquiries: {inq_after} (was {inq_before}) [{'PASS' if inq_ok else 'FAIL'}]")
print(f"  jobs: {job_after} (was {job_before}) [{'PASS' if job_ok else 'FAIL'}]")

# ── Summary ──
all_ok = ip == len(inq_checks) and jp == total_job and inq_ok and job_ok
total_all = len(inq_checks) + total_job + 2
total_pass = ip + jp + (1 if inq_ok else 0) + (1 if job_ok else 0)
print("\n" + "=" * 60)
print(f"RESULT: {total_pass}/{total_all} passed {'- ALL PASS' if all_ok else '- SOME FAILED'}")
print("=" * 60)
