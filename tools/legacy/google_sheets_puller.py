"""
BRIDGE Google Sheets Puller
============================
Google Forms 응답 스프레드시트를 주기적으로 읽어
신규 행을 intake 폴더에 CSV로 저장.

[보안] 외부 포트 개방 없음 -- 로컬에서 Google API 직접 호출 (Pull 방식)
[인증] Google Cloud Service Account JSON 키
[경로] Q:/Claudework/bridge base/

실행: python google_sheets_puller.py
      python google_sheets_puller.py --once
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── 경로 (bridge base 기준) ───────────────────────────────────────────────────
BASE_DIR    = Path("Q:/Claudework/bridge base")
INTAKE_CAND = BASE_DIR / "intake/candidates"
INTAKE_JOBS = BASE_DIR / "intake/jobs"
LOG_PATH    = BASE_DIR / "logs/system.log"
STATE_FILE  = BASE_DIR / "sheets_state.json"
SA_JSON     = BASE_DIR / "google_service_account.json"

sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

SHEETS_CANDIDATES_ID = os.getenv("GOOGLE_SHEETS_CANDIDATES_ID", "")
SHEETS_JOBS_ID       = os.getenv("GOOGLE_SHEETS_JOBS_ID", "")
POLL_INTERVAL        = int(os.getenv("GOOGLE_SHEETS_POLL_INTERVAL", "300"))
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


# ── 유틸 ──────────────────────────────────────────────────────────────────────
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def syslog(msg: str) -> None:
    line = f"[{utc_now()}] [SHEETS] {msg}"
    print(line, flush=True)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_gspread_client():
    try:
        from google.oauth2.service_account import Credentials
        import gspread
    except ImportError:
        syslog("[ERROR] gspread / google-auth 미설치. pip install gspread google-auth")
        return None

    if not SA_JSON.exists():
        syslog(f"[ERROR] 서비스 계정 JSON 없음: {SA_JSON}")
        return None

    try:
        creds = Credentials.from_service_account_file(str(SA_JSON), scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        syslog(f"[ERROR] Google 인증 실패: {e}")
        return None


def rows_to_csv(headers: list, rows: list, dest_dir: Path, prefix: str) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = dest_dir / f"{prefix}_{ts}.csv"
    with open(dest, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    syslog(f"  -> CSV 저장: {dest.name}  ({len(rows)}행)")
    return dest


def poll_sheet(client, sheet_id: str, kind: str, state: dict) -> int:
    if not sheet_id:
        return 0
    label = "구직자" if kind == "candidates" else "구인처"
    try:
        ws         = client.open_by_key(sheet_id).get_worksheet(0)
        all_values = ws.get_all_values()
    except Exception as e:
        syslog(f"[{label}] 시트 읽기 실패: {e}")
        return 0

    if len(all_values) < 2:
        return 0

    headers   = all_values[0]
    data_rows = all_values[1:]
    last_idx  = state.get(sheet_id, 0)
    new_rows  = data_rows[last_idx:]

    if not new_rows:
        return 0

    syslog(f"[{label}] 신규 {len(new_rows)}행 발견 (누계 {len(data_rows)}행)")
    dest_dir = INTAKE_CAND if kind == "candidates" else INTAKE_JOBS
    rows_to_csv(headers, new_rows, dest_dir, f"sheets_{kind}")
    state[sheet_id] = len(data_rows)
    return len(new_rows)


# ── 메인 ──────────────────────────────────────────────────────────────────────
def run_once():
    client = get_gspread_client()
    if client is None:
        syslog("[FAIL] 인증 실패")
        return
    state = load_state()
    total  = 0
    total += poll_sheet(client, SHEETS_CANDIDATES_ID, "candidates", state)
    total += poll_sheet(client, SHEETS_JOBS_ID,       "jobs",       state)
    save_state(state)
    syslog(f"[완료] 신규 {total}행 저장 -> intake 폴더 확인")


def main() -> None:
    syslog("=" * 55)
    syslog("BRIDGE Google Sheets Puller 시작")
    syslog(f"  경로: {BASE_DIR}")
    syslog(f"  SA : {SA_JSON.name}")
    syslog(f"  구직자: {SHEETS_CANDIDATES_ID[:20]}..." if SHEETS_CANDIDATES_ID else "  구직자: 미설정")
    syslog(f"  구인처: {SHEETS_JOBS_ID[:20]}..." if SHEETS_JOBS_ID else "  구인처: 미설정")
    syslog(f"  간격 : {POLL_INTERVAL}초 ({POLL_INTERVAL // 60}분)")
    syslog("  종료 : Ctrl+C")
    syslog("=" * 55)

    while True:
        run_once()
        try:
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            syslog("Sheets Puller 종료")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="1회 실행 후 종료")
    args = parser.parse_args()
    if args.once:
        run_once()
    else:
        main()
