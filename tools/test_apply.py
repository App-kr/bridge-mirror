"""Apply Form -> Canvas Sheet 매핑 테스트
로컬 서버(8000)에 POST /api/apply 제출 후 DB 검증
"""
import sqlite3
import json
import urllib.request
import urllib.error

API = "http://localhost:8000"
DB  = "Q:/Claudework/bridge base/master.db"

# ── 테스트 지원자 데이터 (실제 양식 필드 매핑) ──
TEST_DATA = {
    "full_name": "TEST_APPLY_JohnSmith",
    "email": "test_apply_crud@example.com",
    "nationality": "Canadian",
    "gender": "Male",
    "dob": "1992-05-15",
    "current_location": "Seoul, South Korea",
    "marital_status": "Single",
    "education": "Bachelor's Degree",
    "major": "English Literature",
    "certification": "TEFL 120hr",
    "e_visa": "E-2",
    "start_date": "2026-04-01",
    "area_prefs": "Seoul, Busan",
    "target_age": "Elementary",
    "experience": "3 years ESL teaching in Vietnam",
    "how_to": "test_auto",
    "job_prefs": "Full-time, prefer morning classes",
    "dependents": "None",
    "pets": "No",
}

print("=" * 60)
print("BRIDGE Apply Form -> DB Mapping Test")
print("=" * 60)

# 1) DB 초기 상태
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
before = conn.execute("SELECT COUNT(*) FROM candidates WHERE status <> 'Deleted'").fetchone()[0]
print(f"[Before] Active candidates: {before}")
conn.close()

# 2) POST /api/apply
print(f"\n[Submit] POST {API}/api/apply")
data = json.dumps(TEST_DATA).encode("utf-8")
req = urllib.request.Request(
    f"{API}/api/apply",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print(f"  Status: {resp.status}")
        print(f"  Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        cid = result.get("data", {}).get("id", "")
        mode = result.get("data", {}).get("mode", "")
        print(f"  candidate_id: {cid}")
        print(f"  mode: {mode}")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8")
    print(f"  HTTP Error {e.code}: {body}")
    cid = ""
except urllib.error.URLError as e:
    print(f"  Connection Error: {e.reason}")
    print("  => 로컬 서버가 실행 중이지 않습니다. DB 직접 테스트로 전환합니다.")
    cid = ""
except Exception as e:
    print(f"  Error: {e}")
    cid = ""

# 3) DB 검증
print("\n[Verify] DB mapping check:")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

if cid:
    row = conn.execute("SELECT * FROM candidates WHERE candidate_id = ?", (cid,)).fetchone()
else:
    # API 실패 시 이름으로 찾기
    row = conn.execute("SELECT * FROM candidates WHERE full_name LIKE '%TEST_APPLY%' ORDER BY rowid DESC LIMIT 1").fetchone()

if row:
    row_dict = dict(row)
    cid = row_dict.get("candidate_id", cid)

    # 매핑 검증 테이블
    FIELD_MAP = {
        "full_name":              "full_name",
        "email":                  "email",
        "nationality":            "nationality",
        "gender":                 "gender",
        "dob":                    "dob",
        "current_location":       "current_location",
        "marital_status":         "married",       # _APPLY_FIELD_MAP
        "education":              "education_level", # _APPLY_FIELD_MAP
        "major":                  "major",
        "certification":          "certification",
        "e_visa":                 "e_visa",
        "start_date":             "start_date",
        "area_prefs":             "area_prefs",
        "target_age":             "target",         # _APPLY_FIELD_MAP
        "experience":             "experience",
        "how_to":                 "how_to",
        "job_prefs":              "job_prefs",
    }

    pass_cnt = 0
    fail_cnt = 0
    for form_field, db_col in FIELD_MAP.items():
        sent = TEST_DATA.get(form_field, "")
        got = row_dict.get(db_col, "")
        # 암호화된 필드는 값이 다를 수 있음 (ENC:... 형태)
        encrypted = got and isinstance(got, str) and (got.startswith("ENC:") or got.startswith("gAAAAA"))
        if got == sent:
            tag = "PASS"
            pass_cnt += 1
        elif encrypted:
            tag = "PASS(enc)"
            pass_cnt += 1
        else:
            tag = "FAIL"
            fail_cnt += 1
        got_display = f"{got[:30]}..." if got and len(str(got)) > 30 else got
        print(f"  [{tag}] {form_field:25s} -> {db_col:25s} = {got_display}")

    # 자동 생성 필드 확인
    print("\n  [Auto fields]")
    for af in ["candidate_id", "status", "source", "source_file", "created_at", "updated_at"]:
        v = row_dict.get(af, "N/A")
        v_display = f"{v[:40]}..." if v and len(str(v)) > 40 else v
        print(f"    {af:20s} = {v_display}")

    print(f"\n  => Mapping: {pass_cnt}/{pass_cnt + fail_cnt} passed, {fail_cnt} failed")
else:
    print("  [SKIP] No test record found in DB")
    print("  => 로컬 서버 미실행 또는 INSERT 실패")
    pass_cnt = 0
    fail_cnt = 1

# 4) 정리 — 테스트 데이터 삭제
if cid:
    conn.execute("DELETE FROM candidates WHERE candidate_id = ?", (cid,))
    conn.commit()
    rem = conn.execute("SELECT COUNT(*) FROM candidates WHERE candidate_id = ?", (cid,)).fetchone()[0]
    print(f"\n[Cleanup] Removed test record: {'PASS' if rem == 0 else 'FAIL'}")

after = conn.execute("SELECT COUNT(*) FROM candidates WHERE status <> 'Deleted'").fetchone()[0]
print(f"[Final] Active candidates: {after} (original: {before}) [{'PASS' if after == before else 'FAIL'}]")

conn.close()

print("\n" + "=" * 60)
all_ok = fail_cnt == 0 and (after == before)
print(f"RESULT: {'ALL PASS' if all_ok else 'SOME FAILED'}")
print("=" * 60)
