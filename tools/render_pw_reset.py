"""Render 서버 비밀번호 직접 변경 — 배포 없이 API로 처리"""
import getpass, urllib.request, urllib.error, json, os, ssl
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
key = os.getenv("ADMIN_API_KEY", "")

print("=" * 50)
print("  Render 관리자 비밀번호 변경 (배포 불필요)")
print("=" * 50)

pw = getpass.getpass("새 비밀번호 (화면에 안 보임): ")
pw2 = getpass.getpass("비밀번호 확인: ")

if pw != pw2:
    print("[ERROR] 비밀번호가 일치하지 않습니다.")
    exit(1)
if len(pw) < 8:
    print("[ERROR] 8자 이상이어야 합니다.")
    exit(1)

body = json.dumps({"new_password": pw}).encode()
req = urllib.request.Request(
    "https://bridge-n7hk.onrender.com/api/admin/change-password",
    data=body,
    headers={"Content-Type": "application/json", "x-admin-key": key},
    method="POST",
)
ctx = ssl.create_default_context()
try:
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        res = json.loads(r.read())
        print(f"[OK] {res.get('message', '변경 완료')}")
        print("로그인 가능합니다: https://bridge-chi-lime.vercel.app/admin")
except urllib.error.HTTPError as e:
    print(f"[ERROR] {e.code}: {e.read().decode()}")
