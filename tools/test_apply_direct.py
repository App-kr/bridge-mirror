"""Apply Form -> DB 매핑 직접 테스트 (서버 불필요)
api_server.py의 _map_apply_payload 로직을 그대로 재현하여 DB INSERT 후 검증
"""
import sqlite3
import uuid
from datetime import datetime, timezone

DB = "Q:/Claudework/bridge base/master.db"

# ── api_server.py 동일 매핑 로직 ──
_APPLY_FIELD_MAP = {
    "education":                "education_level",
    "marital_status":           "married",
    "personal_considerations":  "personal_consideration",
    "agreement":                "consent",
    "facts":                    "fact_check",
    "admin_notes":              "notes",
    "target_age":               "target",
}
_APPLY_SKIP_FIELDS = {"file_urls", "apply_token"}

def _map_apply_payload(payload):
    mapped = {}
    for k, v in payload.items():
        if k in _APPLY_SKIP_FIELDS:
            continue
        db_key = _APPLY_FIELD_MAP.get(k, k)
        mapped[db_key] = v
    mapped["source_file"] = "web_form"
    return mapped


# ── 테스트 양식 데이터 (Google Form 42개 항목 중 핵심) ──
TEST_FORM = {
    "full_name": "TEST_MAPPING_JaneSmith",
    "email": "test_mapping@bridgetest.com",
    "nationality": "American",
    "gender": "Female",
    "dob": "1990-08-22",
    "current_location": "Busan, South Korea",
    "marital_status": "Married",           # -> married
    "dependents": "1 child",
    "pets": "Cat",
    "education": "Master's Degree",        # -> education_level
    "major": "TESOL",
    "certification": "CELTA, TEFL 120hr",
    "e_visa": "E-2",
    "arc_holders": "Yes",
    "passport": "Valid until 2030",
    "criminal_record": "None",
    "start_date": "2026-05-01",
    "area_prefs": "Seoul, Gyeonggi",
    "target_age": "Middle School",         # -> target
    "job_prefs": "Full-time, afternoon preferred",
    "experience": "5 years in Korea, 2 years in Japan",
    "employment": "Currently employed at XYZ Academy",
    "reference": "Mr. Kim, XYZ Academy Director",
    "how_to": "test_auto_mapping",
    "current_salary": "2.5M KRW",
    "desired_salary": "2.8M KRW",
    "interview_time": "Weekday afternoon preferred",
    "housing": "Own housing",
    "personal_considerations": "None",     # -> personal_consideration
    "religion": "None",
    "health_info": "Good",
    "tattoo": "No",
    "working_hours": "9-6",
    "agreement": "Yes",                    # -> consent
    "facts": "Confirmed",                  # -> fact_check
    "file_urls": "http://example.com/cv.pdf",  # SKIP
}

print("=" * 60)
print("BRIDGE Apply Form -> DB Direct Mapping Test")
print("=" * 60)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA busy_timeout = 5000")

before = conn.execute("SELECT COUNT(*) FROM candidates WHERE status <> 'Deleted'").fetchone()[0]
print(f"[Before] Active candidates: {before}")

# ── 1) _map_apply_payload 적용 ──
now_iso = datetime.now(timezone.utc).isoformat()
payload = dict(TEST_FORM)  # copy
new_id = f"cnd_{uuid.uuid4().hex[:12]}"
payload["candidate_id"] = new_id
payload["source"] = "web_form"
payload["status"] = "Active"
payload["created_at"] = now_iso
payload["updated_at"] = now_iso

db_payload = _map_apply_payload(payload)

print(f"\n[Mapping] Form fields: {len(TEST_FORM)} -> DB columns: {len(db_payload)}")
print(f"  candidate_id: {new_id}")

# ── 2) INSERT ──
cols = ", ".join(db_payload.keys())
placeholders = ", ".join("?" * len(db_payload))
try:
    conn.execute(f"INSERT INTO candidates ({cols}) VALUES ({placeholders})", list(db_payload.values()))
    conn.commit()
    print("  [INSERT] PASS")
except Exception as e:
    print(f"  [INSERT] FAIL: {e}")
    conn.close()
    exit(1)

# ── 3) 매핑 검증 ──
row = conn.execute("SELECT * FROM candidates WHERE candidate_id = ?", (new_id,)).fetchone()
if not row:
    print("  [VERIFY] FAIL - record not found")
    conn.close()
    exit(1)

row_dict = dict(row)

print("\n[Verify] Field-by-field mapping:")
print(f"  {'Form Field':30s} {'DB Column':25s} {'Match':8s} Value")
print("  " + "-" * 95)

pass_cnt = 0
fail_cnt = 0

# 매핑 검증 (form field -> expected db column -> actual value)
checks = [
    ("full_name",               "full_name"),
    ("email",                   "email"),
    ("nationality",             "nationality"),
    ("gender",                  "gender"),
    ("dob",                     "dob"),
    ("current_location",        "current_location"),
    ("marital_status",          "married"),
    ("dependents",              "dependents"),
    ("pets",                    "pets"),
    ("education",               "education_level"),
    ("major",                   "major"),
    ("certification",           "certification"),
    ("e_visa",                  "e_visa"),
    ("arc_holders",             "arc_holders"),
    ("passport",                "passport"),
    ("criminal_record",         "criminal_record"),
    ("start_date",              "start_date"),
    ("area_prefs",              "area_prefs"),
    ("target_age",              "target"),
    ("job_prefs",               "job_prefs"),
    ("experience",              "experience"),
    ("employment",              "employment"),
    ("reference",               "reference"),
    ("how_to",                  "how_to"),
    ("current_salary",          "current_salary"),
    ("desired_salary",          "desired_salary"),
    ("interview_time",          "interview_time"),
    ("housing",                 "housing"),
    ("personal_considerations", "personal_consideration"),
    ("religion",                "religion"),
    ("health_info",             "health_info"),
    ("tattoo",                  "tattoo"),
    ("working_hours",           "working_hours"),
    ("agreement",               "consent"),
    ("facts",                   "fact_check"),
]

for form_f, db_col in checks:
    sent = TEST_FORM.get(form_f, "")
    got = row_dict.get(db_col, "")
    match = (got == sent)
    if match:
        pass_cnt += 1
        tag = "PASS"
    else:
        fail_cnt += 1
        tag = "FAIL"
    val_display = str(got)[:40] if got else "(empty)"
    print(f"  {form_f:30s} {db_col:25s} [{tag:4s}]  {val_display}")

# file_urls 가 SKIP 되었는지 확인
skipped_ok = "file_urls" not in row_dict or not row_dict.get("file_urls")
print(f"\n  {'file_urls (SKIP)':30s} {'(not in DB)':25s} [{'PASS' if skipped_ok else 'FAIL'}]")
if skipped_ok:
    pass_cnt += 1
else:
    fail_cnt += 1

# source_file 자동 설정
sf_ok = row_dict.get("source_file") == "web_form"
print(f"  {'(auto) source_file':30s} {'source_file':25s} [{'PASS' if sf_ok else 'FAIL'}]  {row_dict.get('source_file')}")
if sf_ok:
    pass_cnt += 1
else:
    fail_cnt += 1

# status 자동
st_ok = row_dict.get("status") == "Active"
print(f"  {'(auto) status':30s} {'status':25s} [{'PASS' if st_ok else 'FAIL'}]  {row_dict.get('status')}")
if st_ok:
    pass_cnt += 1
else:
    fail_cnt += 1

total_checks = pass_cnt + fail_cnt

# ── 4) 정리 ──
conn.execute("DELETE FROM candidates WHERE candidate_id = ?", (new_id,))
conn.commit()
rem = conn.execute("SELECT COUNT(*) FROM candidates WHERE candidate_id = ?", (new_id,)).fetchone()[0]
after = conn.execute("SELECT COUNT(*) FROM candidates WHERE status <> 'Deleted'").fetchone()[0]
conn.close()

print(f"\n[Cleanup] Record removed: {'PASS' if rem == 0 else 'FAIL'}")
print(f"[Final] Active: {after} (original: {before}) [{'PASS' if after == before else 'FAIL'}]")

print("\n" + "=" * 60)
print(f"RESULT: {pass_cnt}/{total_checks} mappings passed", end="")
if fail_cnt == 0 and after == before:
    print(" - ALL PASS")
else:
    print(f" - {fail_cnt} FAILED")
print("=" * 60)
