"""
sync_google_sheets.py — Google Sheets → Bridge DB 동기화
============================================================
사용법:
  python tools/sync_google_sheets.py --mode candidates|jobs|all [--dry-run]

환경변수 (.env):
  GOOGLE_SHEETS_CANDIDATES_ID  — 교사 신청 시트 ID
  GOOGLE_SHEETS_JOBS_ID        — 채용공고 시트 ID
  GOOGLE_SERVICE_ACCOUNT_JSON  — service account JSON 경로

PII 정책:
  - 모든 개인식별정보는 AES-256-GCM 암호화 후 저장 (security_vault.py 사용)
  - 로그에 PII 값 절대 출력 금지
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_ROOT))

# .env 로드
_ENV_FILE = _ROOT / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

_DB_PATH   = _ROOT / "master.db"
_LOG_DIR   = _ROOT / ".logs"
_LOG_DIR.mkdir(exist_ok=True)

# ── 로그 설정 ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_LOG_DIR / "sheets_sync.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("bridge.sheets_sync")

# ── PII 암호화 ─────────────────────────────────────────────────────────────────
try:
    from security_vault import encrypt_field, is_encrypted
    _VAULT_OK = True
except ImportError:
    log.warning("security_vault 없음 — PII 암호화 비활성화 (개발환경 전용)")
    _VAULT_OK = False
    def encrypt_field(v):  # type: ignore
        return v
    def is_encrypted(v):  # type: ignore
        return False

def _enc(value: str | None, column_name: str = "") -> str | None:
    """PII 암호화 (column_name 포함 필수 — L1 키 분리용)."""
    if not value:
        return value
    if is_encrypted(str(value)):
        return str(value)
    return encrypt_field(str(value), column_name)

# ── Google Sheets 클라이언트 ────────────────────────────────────────────────────
def _get_sheets_service():
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "google-auth, google-api-python-client 패키지가 필요합니다.\n"
            "pip install google-auth google-auth-httplib2 google-api-python-client"
        )

    sa_val = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not sa_val:
        raise ValueError(
            "GOOGLE_SERVICE_ACCOUNT_JSON 환경변수가 설정되지 않았습니다."
        )

    # 파일 경로인지 JSON 문자열인지 판별 (Render는 JSON 문자열 사용)
    sa_path = Path(sa_val)
    if sa_path.exists():
        creds = Credentials.from_service_account_file(
            str(sa_path),
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )
    else:
        # Render 환경: env var에 JSON 내용 직접 저장
        try:
            sa_info = json.loads(sa_val)
        except json.JSONDecodeError:
            raise ValueError(
                "GOOGLE_SERVICE_ACCOUNT_JSON이 유효한 파일 경로도 아니고 "
                "JSON 문자열도 아닙니다."
            )
        creds = Credentials.from_service_account_info(
            sa_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )

    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _read_sheet(service, sheet_id: str, range_: str = "A1:ZZ") -> list[list[str]]:
    """시트 데이터 읽기 — 첫 행을 헤더로 사용"""
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=range_)
        .execute()
    )
    return result.get("values", [])


def _rows_to_dicts(raw: list[list[str]]) -> list[dict[str, str]]:
    if len(raw) < 2:
        return []
    headers = [h.strip() for h in raw[0]]
    records = []
    for row in raw[1:]:
        padded = row + [""] * (len(headers) - len(row))
        records.append({h: padded[i] for i, h in enumerate(headers)})
    return records

# ── Candidates 동기화 ──────────────────────────────────────────────────────────

# PII 컬럼 (암호화 대상)
_CAND_PII_COLS = {"email", "phone", "full_name", "date_of_birth", "address", "passport_number",
                  "kakao_id", "emergency_contact", "emergency_phone", "kakaotalk"}

# 허용 컬럼 (candidates 테이블 기준)
_CAND_ALLOWED = {
    "full_name", "email", "phone", "nationality", "teaching_age",
    "visa_type", "start_date", "source", "created_at",
    "kakao_id", "current_location", "degree", "major",
    "gender", "dob", "religion", "marital_status",
    "korean_criminal_record", "criminal_record", "health_info",
    "e_visa", "area_prefs", "housing", "reference",
}

# 시트 컬럼 → DB 컬럼 매핑
# ★ 실제 시트 헤더(한/영 혼용)에 맞춰 정확히 매핑
_CAND_COL_MAP: dict[str, str] = {
    # ─── 식별자 (필수) ───────────────────────────────────────────────
    "이메일 주소": "email",          # 실제 시트 헤더
    "Email Address": "email",       # 영문 폼 폴백
    "Mobile Phone": "phone",        # 실제 시트 헤더
    "Phone Number": "phone",        # 영문 폼 폴백
    # ─── 기본 정보 ──────────────────────────────────────────────────
    "Full name": "full_name",
    "Full Name": "full_name",
    "Nationality": "nationality",
    "Date of Birth": "dob",
    "Gender": "gender",
    "Current Location": "current_location",
    "KakaoTalk": "kakao_id",         # 실제 시트 헤더
    "KakaoTalk ID": "kakao_id",      # 영문 폼 폴백
    # ─── 지원 정보 ──────────────────────────────────────────────────
    "Target": "teaching_age",        # 실제 시트 헤더 (초/중/고)
    "Teaching Level": "teaching_age",
    "Start date": "start_date",      # 실제 시트 헤더
    "Available Start Date": "start_date",
    "Area prefs": "area_prefs",
    "E visa": "e_visa",
    # ─── 학력/자격 ──────────────────────────────────────────────────
    "Degree": "degree",
    "Major": "major",
    # ─── 기타 정보 ──────────────────────────────────────────────────
    "Religion": "religion",
    "Marital Status": "marital_status",
    "Housing": "housing",
    "Reference": "reference",
    "Criminal Record": "criminal_record",
    "Criminal Record in Korea": "korean_criminal_record",
    "Health Information": "health_info",
    # ─── 타임스탬프 ─────────────────────────────────────────────────
    "타임스탬프": "created_at",       # 실제 시트 헤더
    "Timestamp": "created_at",       # 영문 폼 폴백
}


def sync_candidates(service, dry_run: bool = False) -> dict[str, int]:
    sheet_id = os.getenv("GOOGLE_SHEETS_CANDIDATES_ID", "")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEETS_CANDIDATES_ID 환경변수 없음")

    log.info("Candidates 시트 읽는 중... (PII 암호화 적용)")
    raw = _read_sheet(service, sheet_id)
    records = _rows_to_dicts(raw)
    log.info("시트 행 수: %d", len(records))

    added = updated = skipped = errors = 0
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row

    try:
        for rec in records:
            try:
                # 컬럼명 정규화
                mapped: dict[str, Any] = {}
                for sheet_col, val in rec.items():
                    db_col = _CAND_COL_MAP.get(sheet_col, sheet_col.lower().replace(" ", "_"))
                    if db_col in _CAND_ALLOWED and val:
                        mapped[db_col] = val

                if not mapped.get("email") and not mapped.get("phone"):
                    skipped += 1
                    continue  # 식별자 없으면 스킵

                # PII 암호화 (column_name 전달 → L1 키 분리)
                for col in _CAND_PII_COLS:
                    if col in mapped:
                        mapped[col] = _enc(mapped[col], col)

                mapped.setdefault("source", "google_sheet_import")
                mapped.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                mapped.setdefault("status", "Active")
                mapped.setdefault("resume_status", "pending")
                # candidate_id 자동 생성 (UUID 기반)
                if "candidate_id" not in mapped:
                    import uuid as _uuid_mod
                    mapped["candidate_id"] = f"cnd_{_uuid_mod.uuid4().hex[:12]}"

                if dry_run:
                    added += 1
                    continue

                # 중복 방지: source='google_sheet_import' + created_at 동일 행 스킵
                # (email은 암호화되어 직접 조회 불가)
                created_at_val = mapped.get("created_at", "")
                school_check_val = mapped.get("full_name", "") or mapped.get("email", "")
                if created_at_val:
                    dup = conn.execute(
                        "SELECT 1 FROM candidates WHERE source=? AND created_at=? LIMIT 1",
                        ("google_sheet_import", created_at_val),
                    ).fetchone()
                    if dup:
                        skipped += 1
                        continue

                cols = ", ".join(mapped.keys())
                placeholders = ", ".join("?" * len(mapped))
                cur = conn.execute(
                    "INSERT INTO candidates (" + cols + ") VALUES (" + placeholders + ")",
                    list(mapped.values()),
                )
                if cur.rowcount > 0:
                    added += 1
                else:
                    skipped += 1

            except Exception as e:
                log.error("candidates 행 처리 실패 (행 번호 생략 — PII): %s", str(e)[:80])
                errors += 1

        if not dry_run:
            conn.commit()
    finally:
        conn.close()

    log.info("Candidates 동기화 완료 — 추가: %d, 스킵: %d, 오류: %d", added, skipped, errors)
    return {"added": added, "updated": updated, "skipped": skipped, "errors": errors}

# ── Jobs 동기화 ────────────────────────────────────────────────────────────────

_JOB_PII_COLS = {"contact_name", "phone", "email", "contact_kakao", "business_registration"}

_JOB_ALLOWED = {
    "school_name", "location", "teaching_age", "working_hours", "salary_raw",
    "start_date", "vacation", "housing_type", "benefits", "source",
    "contact_name", "phone", "email",  # → 암호화됨
}

_JOB_COL_MAP: dict[str, str] = {
    "School Name": "school_name",
    "Location": "location",
    "Teaching Level": "teaching_age",
    "Working Hours": "working_hours",
    "Salary": "salary_raw",
    "Start Date": "start_date",
    "Vacation Days": "vacation",
    "Housing": "housing_type",
    "Benefits": "benefits",
    "Contact Name": "contact_name",
    "Phone": "phone",
    "Email": "email",
    "Timestamp": "submitted_at",
}


def sync_jobs(service, dry_run: bool = False) -> dict[str, int]:
    sheet_id = os.getenv("GOOGLE_SHEETS_JOBS_ID", "")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEETS_JOBS_ID 환경변수 없음")

    log.info("Jobs 시트 읽는 중... (PII 암호화 적용)")
    raw = _read_sheet(service, sheet_id)
    records = _rows_to_dicts(raw)
    log.info("시트 행 수: %d", len(records))

    added = updated = skipped = errors = 0
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")

    try:
        for rec in records:
            try:
                mapped: dict[str, Any] = {}
                for sheet_col, val in rec.items():
                    db_col = _JOB_COL_MAP.get(sheet_col, sheet_col.lower().replace(" ", "_"))
                    if db_col in _JOB_ALLOWED and val:
                        mapped[db_col] = val

                if not mapped.get("school_name"):
                    skipped += 1
                    continue

                # PII 암호화
                for col in _JOB_PII_COLS:
                    if col in mapped:
                        mapped[col] = _enc(mapped[col], col)

                # client_inquiries 테이블에 insert (PII 컬럼명 변환)
                inq_map: dict[str, Any] = {}
                for k, v in mapped.items():
                    if k in {"contact_name", "phone", "email"}:
                        inq_map[k] = v  # 이미 암호화됨
                    else:
                        inq_map[k] = v
                inq_map["source"] = "google_sheet_import"
                inq_map["inbox_status"] = "new"
                inq_map.setdefault("submitted_at", datetime.now(timezone.utc).isoformat())

                if dry_run:
                    added += 1
                    continue

                # 중복 방지: source='google_sheet_import' + school_name + submitted_at
                submitted_at_val = inq_map.get("submitted_at", "")
                school_name_val = inq_map.get("school_name", "")
                if submitted_at_val and school_name_val:
                    dup = conn.execute(
                        "SELECT 1 FROM client_inquiries WHERE source=? AND school_name=? AND submitted_at=? LIMIT 1",
                        ("google_sheet_import", school_name_val, submitted_at_val),
                    ).fetchone()
                    if dup:
                        skipped += 1
                        continue

                cols = ", ".join(inq_map.keys())
                placeholders = ", ".join("?" * len(inq_map))
                cur = conn.execute(
                    "INSERT INTO client_inquiries (" + cols + ") VALUES (" + placeholders + ")",
                    list(inq_map.values()),
                )
                if cur.rowcount > 0:
                    added += 1
                else:
                    skipped += 1

            except Exception as e:
                log.error("jobs 행 처리 실패: %s", str(e)[:80])
                errors += 1

        if not dry_run:
            conn.commit()
    finally:
        conn.close()

    log.info("Jobs 동기화 완료 — 추가: %d, 스킵: %d, 오류: %d", added, skipped, errors)
    return {"added": added, "updated": updated, "skipped": skipped, "errors": errors}

# ── 통합 실행 ──────────────────────────────────────────────────────────────────

def run_sync(mode: str = "all", dry_run: bool = False) -> dict[str, Any]:
    """API 엔드포인트에서도 호출 가능한 메인 함수"""
    import time
    t0 = time.time()

    service = _get_sheets_service()
    result: dict[str, Any] = {"mode": mode, "dry_run": dry_run}

    if mode in ("candidates", "all"):
        result["candidates"] = sync_candidates(service, dry_run=dry_run)

    if mode in ("jobs", "all"):
        result["jobs"] = sync_jobs(service, dry_run=dry_run)

    result["duration_ms"] = int((time.time() - t0) * 1000)
    log.info("전체 동기화 완료 — %dms (mode=%s, dry_run=%s)", result["duration_ms"], mode, dry_run)
    return result


# ── CLI 진입점 ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bridge Google Sheets → DB 동기화")
    parser.add_argument("--mode", choices=["candidates", "jobs", "all"], default="all")
    parser.add_argument("--dry-run", action="store_true", help="DB 쓰기 없이 결과만 확인")
    args = parser.parse_args()

    result = run_sync(mode=args.mode, dry_run=args.dry_run)
    print("\n=== 동기화 결과 ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
