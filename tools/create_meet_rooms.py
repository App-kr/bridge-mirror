"""
Google Meet 영구 회의실 10개 생성
=================================
서비스 계정으로 Google Calendar에 반복 없는 이벤트를 생성하여
Meet 링크를 발급받습니다. "항상 열기" 설정은 Google Admin에서 별도 필요.

사용: python tools/create_meet_rooms.py
"""
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

# dotenv 로드
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

# 서비스 계정 JSON 로드 (파일 경로 또는 JSON 문자열)
sa_json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
if not sa_json_str:
    # bx vault 시도
    try:
        from bx import _read as bx_read
        sa_json_str = bx_read("GOOGLE_SERVICE_ACCOUNT_JSON") or ""
    except Exception:
        pass

if not sa_json_str:
    print("[ERROR] GOOGLE_SERVICE_ACCOUNT_JSON not found")
    sys.exit(1)

# 파일 경로인 경우 파일 내용 읽기
sa_path = Path(sa_json_str.strip())
if sa_path.is_file():
    with open(sa_path, "r", encoding="utf-8") as f:
        sa_json_str = f.read()
elif not sa_json_str.startswith("{"):
    # 경로가 잘못되었을 수 있음 — 프로젝트 루트에서 찾기
    fallback = PROJECT_ROOT / "google_service_account.json"
    alt = PROJECT_ROOT / "archive" / "old_configs" / "google_service_account.json"
    for p in [fallback, alt]:
        if p.is_file():
            print(f"[INFO] Found SA at: {p}")
            with open(p, "r", encoding="utf-8") as f:
                sa_json_str = f.read()
            break
    else:
        print(f"[ERROR] Cannot find service account file: {sa_json_str}")
        sys.exit(1)

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError as e:
    print(f"[ERROR] Google API package missing: {e}")
    print("  pip install google-api-python-client google-auth")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
sa_info = json.loads(sa_json_str)
creds = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)
service = build("calendar", "v3", credentials=creds)

calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
kst = timezone(timedelta(hours=9))

print(f"Calendar ID: {calendar_id}")
print("Creating 10 Meet rooms...\n")

meet_links = []
for i in range(1, 11):
    # 먼 미래 날짜 (영구 룸 용도)
    start = datetime(2099, 1, i, 10, 0, tzinfo=kst)
    end = start + timedelta(hours=1)

    event = {
        "summary": f"BRIDGE Interview Room {i}",
        "description": "Bridge Recruitment permanent interview room.\nAccess: Open (no permission needed)",
        "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Seoul"},
        "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Seoul"},
        "conferenceData": {
            "createRequest": {
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
                "requestId": f"bridge-room-{i}-{uuid.uuid4().hex[:8]}",
            }
        },
        "guestsCanModify": False,
        "guestsCanInviteOthers": False,
    }

    try:
        result = service.events().insert(
            calendarId=calendar_id,
            body=event,
            conferenceDataVersion=1,
        ).execute()

        meet_link = ""
        for ep in result.get("conferenceData", {}).get("entryPoints", []):
            if ep.get("entryPointType") == "video":
                meet_link = ep.get("uri", "")
                break
        if not meet_link:
            meet_link = result.get("hangoutLink", "")

        if meet_link:
            meet_links.append(meet_link)
            print(f"  Room {i}: {meet_link}")
        else:
            print(f"  Room {i}: [WARNING] No Meet link returned")
    except Exception as e:
        print(f"  Room {i}: [ERROR] {e}")

print(f"\n{'='*60}")
print(f"Created {len(meet_links)} / 10 rooms")
print(f"{'='*60}")

if meet_links:
    print("\n// Copy this to DEFAULT_MEET_POOL:")
    print("const DEFAULT_MEET_POOL = [")
    for link in meet_links:
        print(f"  '{link}',")
    print("]")

    print("\n// JSON format:")
    print(json.dumps(meet_links, indent=2))
