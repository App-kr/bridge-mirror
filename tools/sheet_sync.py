"""
sheet_sync.py — DB → Google Sheet 일방향 동기화 (Source 시트)
BRIDGE ATS Phase 3

사용법:
  python tools/sheet_sync.py test             # 연결 테스트 (읽기만)
  python tools/sheet_sync.py sync             # 최근 24시간 동기화
  python tools/sheet_sync.py sync --hours 72  # 최근 72시간
  python tools/sheet_sync.py retry            # 실패건 재시도
  python tools/sheet_sync.py status           # 동기화 상태 확인
"""

import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── 경로 ─────────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent          # bridge base
DB_PATH = BASE / "master.db"
PENDING_PATH = BASE / "tools" / "pending_sync.json"
LOCK_PATH = BASE / "tools" / ".sheet_sync.lock"
LOG_PATH = BASE / "tools" / "sheet_sync.log"
ENV_PATH = BASE / ".env"

# ── 로깅 ─────────────────────────────────────────────────────────────────────
_log = logging.getLogger("sheet_sync")
_log.setLevel(logging.INFO)
_fh = RotatingFileHandler(str(LOG_PATH), maxBytes=100_000, backupCount=2, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
_log.addHandler(_fh)
_sh = logging.StreamHandler()
_sh.setFormatter(logging.Formatter("%(message)s"))
_log.addHandler(_sh)

# ── .env 로드 ────────────────────────────────────────────────────────────────
def _load_env():
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

_load_env()

# ── DB → Sheet 컬럼 매핑 (admin sheet defaultCols 순서) ──────────────────────
# Sheet 컬럼 헤더 + DB 컬럼 매핑 (rowNum/photo/mailAction 등 계산 컬럼 제외)
SHEET_COLUMNS = [
    # (sheet_header, db_column)
    ("Email", "email"),
    ("Name", "full_name"),
    ("Sheet#", "sheet_number"),
    ("ARC", "arc_holders"),
    ("Nationality", "nationality"),
    ("Background", "ancestry"),
    ("DOB", "dob"),
    ("Gender", "gender"),
    ("Location", "current_location"),
    ("Start Date", "start_date"),
    ("Target", "target"),
    ("Area Prefs", "area_prefs"),
    ("Reference", "reference"),
    ("Experience", "experience"),
    ("Employment", "employment"),
    ("Preferences", "preferences"),
    ("Job Prefs", "job_prefs"),
    ("Contract Offered", "contract_offered"),
    ("Recruiter Memo", "recruiter_memo"),
    ("Stage", "stage"),
    ("Current Salary", "current_salary"),
    ("Desired Salary", "desired_salary"),
    ("Interview Time", "interview_time"),
    ("Education", "education_level"),
    ("Major", "major"),
    ("Certification", "certification"),
    ("Doc Status", "doc_status"),
    ("Health", "health_info"),
    ("Personal Note", "personal_consideration"),
    ("Tattoo", "tattoo"),
    ("Dependents", "dependents"),
    ("Married", "married"),
    ("Housing", "housing"),
    ("Religion", "religion"),
    ("Visa", "e_visa"),
    ("KakaoTalk", "kakaotalk"),
    ("Phone", "mobile_phone"),
    ("Criminal Check", "criminal_record_check"),
    ("KR Criminal", "korean_criminal_record"),
    ("Consent", "consent"),
    ("Fact Check", "fact_check"),
    ("Source", "how_to"),
    ("Created", "created_at"),
    ("Placed Company", "placed_company"),
    ("Placed Salary", "placed_salary"),
    ("Start Month", "start_month"),
    ("Housing Detail", "housing_detail"),
    ("Referral Fee", "referral_fee"),
    ("Process Date", "process_date"),
    ("Past Placement", "past_placement"),
    ("Candidate ID", "candidate_id"),
]

HEADERS = [h for h, _ in SHEET_COLUMNS]
DB_COLS = [c for _, c in SHEET_COLUMNS]


class SheetSync:
    """DB → Google Sheet 일방향 동기화."""

    def __init__(self, credentials_file=None, spreadsheet_id=None):
        self._cred_file = credentials_file or os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_FILE", str(BASE / "gcp_service_account.json")
        )
        if not Path(self._cred_file).is_absolute():
            self._cred_file = str(BASE / self._cred_file)
        self._sheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEETS_CANDIDATES_ID", "")
        self._service = None

    # ── Google Sheets API 연결 ───────────────────────────────────────────────
    def _connect(self):
        if self._service:
            return self._service
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        if not Path(self._cred_file).exists():
            raise FileNotFoundError(f"Service account file not found: {self._cred_file}")
        if not self._sheet_id:
            raise ValueError("GOOGLE_SHEETS_CANDIDATES_ID not set")

        creds = Credentials.from_service_account_file(
            self._cred_file,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        self._service = build("sheets", "v4", credentials=creds)
        return self._service

    # ── Source 시트에서 기존 ID 수집 ─────────────────────────────────────────
    def get_existing_ids(self, sheet_name="Source") -> set:
        svc = self._connect()
        # Candidate ID 컬럼 (마지막 컬럼)
        id_col_idx = HEADERS.index("Candidate ID")
        col_letter = chr(ord("A") + id_col_idx) if id_col_idx < 26 else "A"
        range_str = f"{sheet_name}!{col_letter}:{col_letter}"
        try:
            result = svc.spreadsheets().values().get(
                spreadsheetId=self._sheet_id, range=range_str
            ).execute()
            values = result.get("values", [])
            return {row[0] for row in values if row and row[0] != "Candidate ID"}
        except Exception as e:
            _log.warning("get_existing_ids failed: %s", e)
            return set()

    # ── DB에서 후보자 조회 ───────────────────────────────────────────────────
    def _query_candidates(self, since_hours=24, candidate_id=None):
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            if candidate_id:
                rows = conn.execute(
                    f"SELECT {', '.join(DB_COLS)} FROM candidates WHERE candidate_id = ?",
                    (candidate_id,),
                ).fetchall()
            else:
                cutoff = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
                rows = conn.execute(
                    f"SELECT {', '.join(DB_COLS)} FROM candidates "
                    f"WHERE created_at >= ? AND is_deleted = 0 "
                    f"ORDER BY created_at DESC",
                    (cutoff,),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ── Sheet에 행 추가 ──────────────────────────────────────────────────────
    def _append_rows(self, sheet_name, rows, retry=3):
        svc = self._connect()
        values = []
        for row in rows:
            values.append([str(row.get(col, "") or "") for col in DB_COLS])

        body = {"values": values}
        for attempt in range(retry):
            try:
                svc.spreadsheets().values().append(
                    spreadsheetId=self._sheet_id,
                    range=f"{sheet_name}!A1",
                    valueInputOption="USER_ENTERED",
                    insertDataOption="INSERT_ROWS",
                    body=body,
                ).execute()
                _log.info("Appended %d rows to %s", len(values), sheet_name)
                return True
            except Exception as e:
                _log.warning("Append attempt %d failed: %s", attempt + 1, e)
                if attempt < retry - 1:
                    time.sleep(2 ** attempt)
        # 모든 재시도 실패 → pending에 저장
        self._save_pending(rows)
        return False

    # ── 최근 N시간 동기화 ────────────────────────────────────────────────────
    def sync_new_candidates(self, since_hours=24):
        from filelock import FileLock
        lock = FileLock(str(LOCK_PATH), timeout=10)
        try:
            with lock:
                candidates = self._query_candidates(since_hours=since_hours)
                if not candidates:
                    _log.info("No new candidates in last %d hours", since_hours)
                    return 0

                existing_ids = self.get_existing_ids()
                new_rows = [c for c in candidates if c.get("candidate_id") not in existing_ids]

                if not new_rows:
                    _log.info("All %d candidates already in Sheet", len(candidates))
                    return 0

                # 헤더 확인/추가
                self._ensure_headers("Source")

                if self._append_rows("Source", new_rows):
                    _log.info("Synced %d new candidates (skipped %d existing)",
                              len(new_rows), len(candidates) - len(new_rows))
                    return len(new_rows)
                return 0
        except Exception as e:
            _log.error("sync_new_candidates failed: %s", e)
            return 0

    # ── 단일 후보자 즉시 동기화 ──────────────────────────────────────────────
    def sync_single(self, candidate_id):
        try:
            rows = self._query_candidates(candidate_id=candidate_id)
            if not rows:
                _log.warning("Candidate %s not found in DB", candidate_id)
                return False
            existing = self.get_existing_ids()
            if candidate_id in existing:
                _log.info("Candidate %s already in Sheet, skipping", candidate_id)
                return True
            self._ensure_headers("Source")
            return self._append_rows("Source", rows)
        except Exception as e:
            _log.warning("sync_single(%s) failed: %s", candidate_id, e)
            self._save_pending(rows if 'rows' in dir() else [{"candidate_id": candidate_id}])
            return False

    # ── 헤더 보장 ────────────────────────────────────────────────────────────
    def _ensure_headers(self, sheet_name):
        svc = self._connect()
        try:
            result = svc.spreadsheets().values().get(
                spreadsheetId=self._sheet_id, range=f"{sheet_name}!1:1"
            ).execute()
            existing = result.get("values", [[]])[0]
            if not existing or existing[0] != HEADERS[0]:
                svc.spreadsheets().values().update(
                    spreadsheetId=self._sheet_id,
                    range=f"{sheet_name}!A1",
                    valueInputOption="USER_ENTERED",
                    body={"values": [HEADERS]},
                ).execute()
                _log.info("Headers written to %s", sheet_name)
        except Exception as e:
            _log.warning("_ensure_headers failed: %s", e)

    # ── Pending 저장/로드/재시도 ─────────────────────────────────────────────
    def _save_pending(self, rows):
        pending = self._load_pending()
        for row in rows:
            cid = row.get("candidate_id", "")
            if cid and not any(p.get("candidate_id") == cid for p in pending):
                pending.append(row)
        if len(pending) > 1000:
            _log.warning("Pending queue exceeds 1000 entries!")
            pending = pending[-1000:]
        PENDING_PATH.write_text(json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8")
        _log.info("Saved %d entries to pending_sync.json", len(pending))

    def _load_pending(self):
        if PENDING_PATH.exists():
            try:
                return json.loads(PENDING_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return []
        return []

    def retry_pending(self):
        pending = self._load_pending()
        if not pending:
            _log.info("No pending entries to retry")
            return 0
        _log.info("Retrying %d pending entries", len(pending))
        existing = self.get_existing_ids()
        to_sync = [p for p in pending if p.get("candidate_id") not in existing]
        if not to_sync:
            PENDING_PATH.write_text("[]", encoding="utf-8")
            _log.info("All pending entries already in Sheet")
            return 0

        self._ensure_headers("Source")
        if self._append_rows("Source", to_sync, retry=3):
            PENDING_PATH.write_text("[]", encoding="utf-8")
            return len(to_sync)
        return 0

    # ── 상태 확인 ────────────────────────────────────────────────────────────
    def status(self):
        print("=" * 50)
        print("BRIDGE Sheet Sync Status")
        print("=" * 50)
        print(f"  DB: {DB_PATH} ({'EXISTS' if DB_PATH.exists() else 'MISSING'})")
        print(f"  Sheet ID: {self._sheet_id[:20]}..." if self._sheet_id else "  Sheet ID: NOT SET")
        print(f"  Credentials: {Path(self._cred_file).name} ({'EXISTS' if Path(self._cred_file).exists() else 'MISSING'})")

        # DB count
        if DB_PATH.exists():
            conn = sqlite3.connect(str(DB_PATH))
            total = conn.execute("SELECT COUNT(*) FROM candidates WHERE is_deleted=0").fetchone()[0]
            conn.close()
            print(f"  DB candidates: {total}")

        # Sheet count
        try:
            existing = self.get_existing_ids()
            print(f"  Sheet rows: {len(existing)}")
        except Exception as e:
            print(f"  Sheet: ERROR ({e})")

        # Pending
        pending = self._load_pending()
        print(f"  Pending sync: {len(pending)} entries")
        print()

    # ── 연결 테스트 ──────────────────────────────────────────────────────────
    def test(self):
        print("Testing Google Sheets connection...")
        try:
            svc = self._connect()
            meta = svc.spreadsheets().get(spreadsheetId=self._sheet_id).execute()
            title = meta.get("properties", {}).get("title", "?")
            sheets = [s["properties"]["title"] for s in meta.get("sheets", [])]
            print(f"  Spreadsheet: {title}")
            print(f"  Sheets: {', '.join(sheets)}")
            if "Source" in sheets:
                existing = self.get_existing_ids()
                print(f"  Source sheet rows: {len(existing)}")
            else:
                print("  WARNING: 'Source' sheet not found!")
            print("  Connection: OK")
            return True
        except Exception as e:
            print(f"  Connection FAILED: {e}")
            return False


# ── CLI ──────────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="BRIDGE DB → Google Sheet sync")
    parser.add_argument("command", choices=["test", "sync", "retry", "status"])
    parser.add_argument("--hours", type=int, default=24, help="Sync window (hours)")
    args = parser.parse_args()

    syncer = SheetSync()

    if args.command == "test":
        syncer.test()
    elif args.command == "sync":
        count = syncer.sync_new_candidates(since_hours=args.hours)
        print(f"Synced: {count} rows")
    elif args.command == "retry":
        count = syncer.retry_pending()
        print(f"Retried: {count} rows")
    elif args.command == "status":
        syncer.status()


if __name__ == "__main__":
    main()
