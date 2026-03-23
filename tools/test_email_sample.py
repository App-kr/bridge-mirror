"""샘플 구인자 확인 이메일 발송 테스트
프로덕션 API로 테스트 inquiry 제출 -> 관리자 이메일로 확인 메일 수신
"""
import json
import urllib.request
import urllib.error
import sqlite3
import time

# 프로덕션 API (Render - 실제 SMTP 연결됨)
PROD_API = "https://bridge-n7hk.onrender.com"
DB = "Q:/Claudework/bridge base/master.db"

# 테스트 데이터 - 관리자 이메일로 발송
TEST_INQUIRY = {
    "school_name": "TEST_SampleAcademy",
    "email": "bridgejobkr@gmail.com",     # 관리자 이메일로 수신
    "contact_name": "테스트",
    "phone": "010-0000-0000",
    "school_location": "Seoul, Gangnam",
    "location": "Seoul, Gangnam",
    "vacancies": "1",
    "teaching_age": "Elementary",
    "start_date": "2026-05-01",
    "salary_raw": "2,500,000 KRW",
    "working_hours": "09:00 ~ 18:00",
    "schedule": "Mon-Fri",
    "housing_type": "Single apartment",
    "benefits": "Health insurance",
    "vacation": "10 days",
    "memo": "EMAIL TEMPLATE TEST - 삭제 예정",
    "source": "web_form",
}

print("=" * 60)
print("BRIDGE Employer Confirmation Email - Sample Send Test")
print("=" * 60)

# 1) 제출 전 inquiry 수 확인
conn = sqlite3.connect(DB)
before = conn.execute("SELECT COUNT(*) FROM client_inquiries").fetchone()[0]
conn.close()
print(f"[Before] client_inquiries: {before}")

# 2) POST /api/inquiry (프로덕션)
print(f"\n[Submit] POST {PROD_API}/api/inquiry")
print(f"  to: {TEST_INQUIRY['email']} (admin)")
data = json.dumps(TEST_INQUIRY).encode("utf-8")
req = urllib.request.Request(
    f"{PROD_API}/api/inquiry",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print(f"  Status: {resp.status}")
        print(f"  Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        new_id = result.get("data", {}).get("id")
        print(f"\n  [PASS] Inquiry submitted (id={new_id})")
        print(f"  => Confirmation email should arrive at bridgejobkr@gmail.com")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8")
    print(f"  HTTP Error {e.code}: {body}")
    new_id = None
except urllib.error.URLError as e:
    print(f"  Connection Error: {e.reason}")
    new_id = None
except Exception as e:
    print(f"  Error: {e}")
    new_id = None

# 3) Render DB에는 직접 접근 불가하므로 로컬 cleanup 불필요
# 프로덕션 DB에서 테스트 데이터는 나중에 admin에서 삭제
if new_id:
    print(f"\n[Note] Test inquiry id={new_id} created in production DB")
    print(f"  => Admin panel에서 'TEST_SampleAcademy' 검색 후 삭제하세요")

print("\n" + "=" * 60)
print("DONE - Check bridgejobkr@gmail.com for confirmation email")
print("=" * 60)
