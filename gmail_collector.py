"""
Gmail 수집 모듈 — bridgejobkr@gmail.com 수신함 자동 수집
- 이메일 자동 분류 (구글폼/자동포맷/직접지원/학원문의)
- 자동 파싱 (정규식 기반)
- 중복 방지 (gmail_message_id)
- FastAPI 연동 (수동/자동 동기화)

환경변수:
  GMAIL_CREDENTIALS_JSON — OAuth2 credentials 경로
  GMAIL_TOKEN_JSON       — OAuth2 token 경로
  GMAIL_SYNC_INTERVAL    — 자동 동기화 간격 (초, 기본 300)
  GMAIL_SYNC_ENABLED     — 자동 동기화 활성화 (기본 false)
"""
import base64
import json
import logging
import os
import re
import sqlite3
import asyncio
from datetime import datetime, timezone, timedelta
from email.utils import parseaddr
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

_log = logging.getLogger("bridge.gmail")

# ── 설정 ──────────────────────────────────────────────────────────────────────
_ADMIN_DB_PATH = Path(os.getenv("BRIDGE_DB_PATH", "./master.db"))
_ADMIN_KEY = os.getenv("ADMIN_API_KEY", "")
_IS_PROD = os.getenv("BRIDGE_ENV", "") == "production"

_CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_JSON", "")
_TOKEN_PATH = os.getenv("GMAIL_TOKEN_JSON", "")
_SYNC_INTERVAL = int(os.getenv("GMAIL_SYNC_INTERVAL", "300"))
_SYNC_ENABLED = os.getenv("GMAIL_SYNC_ENABLED", "false").lower() == "true"

router = APIRouter(prefix="/api/admin/gmail", tags=["gmail"])

# ── 동기화 상태 ───────────────────────────────────────────────────────────────
_sync_state = {
    "running": False,
    "last_sync": None,
    "last_count": 0,
    "last_error": None,
    "total_collected": 0,
}


# ── 인증 ──────────────────────────────────────────────────────────────────────
def _check_admin(request: Request):
    if not _ADMIN_KEY:
        if _IS_PROD:
            raise HTTPException(status_code=503, detail="관리자 기능 비활성화")
        return
    if request.headers.get("x-admin-key", "") != _ADMIN_KEY:
        raise HTTPException(status_code=403, detail="관리자 키가 올바르지 않습니다.")


def ok(data=None, message: str = "ok"):
    return {"success": True, "message": message, "data": data}


# ── Gmail API 클라이언트 ──────────────────────────────────────────────────────
def _get_gmail_service():
    """Google Gmail API 서비스 객체 생성."""
    if not _CREDENTIALS_PATH or not os.path.exists(_CREDENTIALS_PATH):
        raise HTTPException(400, "Gmail credentials not configured. Set GMAIL_CREDENTIALS_JSON")

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request as GRequest
        from googleapiclient.discovery import build
    except ImportError:
        raise HTTPException(500,
            "Gmail dependencies not installed. Run: pip install google-api-python-client google-auth-oauthlib"
        )

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds = None

    if _TOKEN_PATH and os.path.exists(_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(_TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GRequest())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(_CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        if _TOKEN_PATH:
            with open(_TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ── 이메일 분류 ───────────────────────────────────────────────────────────────
def _classify_email(subject: str, from_addr: str, body: str) -> str:
    """이메일 제목/본문 기반 분류."""
    subj_lower = subject.lower()

    # 구글 폼 응답
    if "양식 application" in subj_lower or "application for teaching" in subj_lower:
        return "google_form"

    # 자동포맷 이메일
    if re.search(r"원어민\s*구직신청접수", subject):
        return "email"

    # 학원/구인 문의
    if any(kw in subj_lower for kw in ["vacancy", "구인", "학원", "hiring", "recruit"]):
        return "inquiry"

    # 교사 지원 (직접 이메일)
    if any(kw in subj_lower for kw in [
        "teaching", "teacher", "esl", "tefl", "tesol",
        "english position", "looking for work", "resume", "cv",
        "application", "apply"
    ]):
        return "email"

    # 기타
    return "email"


# ── 자동 파싱 ─────────────────────────────────────────────────────────────────
def _parse_auto_format(subject: str, body: str) -> dict:
    """자동포맷 이메일 파싱: '미국/00년생/서울/03월'"""
    parsed = {}

    # 제목에서 '국적/생년/지역/시작월' 패턴 추출
    pattern = re.compile(
        r'([가-힣a-zA-Z]+)\s*/\s*(\d{2,4})년생\s*/\s*([가-힣a-zA-Z]+)\s*/\s*(\d{1,2})월'
    )
    match = pattern.search(subject)
    if match:
        parsed["nationality"] = match.group(1)
        birth_year = match.group(2)
        if len(birth_year) == 2:
            birth_year = "19" + birth_year if int(birth_year) > 50 else "20" + birth_year
        parsed["birth_year"] = birth_year
        parsed["preferred_area"] = match.group(3)
        parsed["start_month"] = f"{int(match.group(4)):02d}"

    # 본문에서 추가 정보 추출
    email_match = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', body)
    if email_match:
        parsed["email"] = email_match.group()

    phone_match = re.search(r'01[016789][- ]?\d{3,4}[- ]?\d{4}', body)
    if phone_match:
        parsed["phone"] = phone_match.group()

    return parsed


def _parse_google_form(body: str) -> dict:
    """구글 폼 응답 이메일에서 필드-값 쌍 추출."""
    parsed = {}
    lines = body.split("\n")

    current_field = None
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # "Field Name: Value" 패턴
        colon_match = re.match(r'^([A-Za-z\s/()]+):\s*(.+)', line)
        if colon_match:
            field = colon_match.group(1).strip().lower().replace(" ", "_")
            value = colon_match.group(2).strip()
            parsed[field] = value
            current_field = field
        elif current_field and line and not line.startswith("="):
            # 이전 필드의 연속 값
            parsed[current_field] = parsed.get(current_field, "") + " " + line

    return parsed


def _parse_direct_email(subject: str, body: str, from_name: str, from_email: str) -> dict:
    """비구조화 이메일 파싱: From 헤더에서 이름/이메일 추출."""
    return {
        "name": from_name,
        "email": from_email,
        "subject": subject,
    }


# ── DB 헬퍼 ───────────────────────────────────────────────────────────────────
def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_ADMIN_DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    return conn


def _message_exists(conn: sqlite3.Connection, gmail_message_id: str) -> bool:
    """gmail_message_id로 중복 확인."""
    r = conn.execute(
        "SELECT 1 FROM candidates WHERE gmail_message_id=?", (gmail_message_id,)
    ).fetchone()
    if r:
        return True
    r = conn.execute(
        "SELECT 1 FROM client_inquiries WHERE gmail_message_id=?", (gmail_message_id,)
    ).fetchone()
    return bool(r)


def _recent_duplicate(conn: sqlite3.Connection, email: str) -> bool:
    """동일 이메일 + 24시간 내 중복 접수 확인."""
    if not email:
        return False
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    r = conn.execute(
        "SELECT 1 FROM candidates WHERE email=? AND created_at > ?",
        (email, cutoff)
    ).fetchone()
    return bool(r)


# ── 이메일 수집 로직 ──────────────────────────────────────────────────────────
def _extract_email_data(msg: dict) -> dict:
    """Gmail API 메시지에서 데이터 추출."""
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

    subject = headers.get("subject", "(No Subject)")
    from_header = headers.get("from", "")
    date_header = headers.get("date", "")

    from_name, from_email = parseaddr(from_header)

    # 본문 추출
    body = ""
    payload = msg.get("payload", {})

    if "body" in payload and payload["body"].get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    elif "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(
                    part["body"]["data"]
                ).decode("utf-8", errors="replace")
                break
            elif part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                raw = base64.urlsafe_b64decode(
                    part["body"]["data"]
                ).decode("utf-8", errors="replace")
                # 간단 HTML 태그 제거
                body = re.sub(r'<[^>]+>', '', raw)

    return {
        "message_id": msg["id"],
        "subject": subject,
        "from_name": from_name,
        "from_email": from_email,
        "date": date_header,
        "body": body[:10000],  # 10K 제한
    }


def _save_to_db(conn: sqlite3.Connection, data: dict, source: str, parsed: dict) -> bool:
    """수집된 이메일을 DB에 저장."""
    try:
        now = datetime.now(timezone.utc).isoformat()

        if source == "inquiry":
            conn.execute(
                """INSERT INTO client_inquiries
                   (school_name, email, contact_name, source, inbox_status,
                    gmail_message_id, raw_email_body, parsed_data, created_at)
                   VALUES (?, ?, ?, ?, 'new', ?, ?, ?, ?)""",
                (
                    parsed.get("school_name", data.get("subject", "")),
                    data["from_email"],
                    data["from_name"],
                    source,
                    data["message_id"],
                    data["body"],
                    json.dumps(parsed, ensure_ascii=False),
                    now,
                )
            )
        else:
            conn.execute(
                """INSERT INTO candidates
                   (full_name, email, source, inbox_status,
                    gmail_message_id, raw_email_body, parsed_data, last_activity, created_at)
                   VALUES (?, ?, ?, 'new', ?, ?, ?, ?, ?)""",
                (
                    parsed.get("name", data["from_name"]) or "Unknown",
                    parsed.get("email", data["from_email"]),
                    source,
                    data["message_id"],
                    data["body"],
                    json.dumps(parsed, ensure_ascii=False),
                    now,
                    now,
                )
            )
        conn.commit()
        return True
    except Exception as e:
        _log.error("Failed to save email %s: %s", data.get("message_id"), e)
        return False


# ── 동기화 실행 ───────────────────────────────────────────────────────────────
def sync_emails(max_results: int = 50) -> dict:
    """Gmail에서 이메일을 가져와 DB에 저장."""
    global _sync_state

    if _sync_state["running"]:
        return {"status": "already_running", "collected": 0}

    _sync_state["running"] = True
    _sync_state["last_error"] = None
    collected = 0
    skipped = 0
    errors = 0

    try:
        service = _get_gmail_service()

        # 최근 7일 이메일 조회
        query = "in:inbox newer_than:7d"
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = results.get("messages", [])

        if not messages:
            _sync_state["last_sync"] = datetime.now(timezone.utc).isoformat()
            _sync_state["last_count"] = 0
            return {"status": "ok", "collected": 0, "message": "No new emails"}

        conn = _get_conn()

        try:
            for msg_meta in messages:
                msg_id = msg_meta["id"]

                # 중복 확인
                if _message_exists(conn, msg_id):
                    skipped += 1
                    continue

                # 메시지 상세 가져오기
                msg = service.users().messages().get(
                    userId="me", id=msg_id, format="full"
                ).execute()

                data = _extract_email_data(msg)

                # 분류
                source = _classify_email(data["subject"], data["from_email"], data["body"])

                # 파싱
                if source == "google_form":
                    parsed = _parse_google_form(data["body"])
                elif re.search(r"원어민\s*구직신청접수", data["subject"]):
                    parsed = _parse_auto_format(data["subject"], data["body"])
                else:
                    parsed = _parse_direct_email(
                        data["subject"], data["body"],
                        data["from_name"], data["from_email"]
                    )

                # 24시간 내 중복 경고
                if _recent_duplicate(conn, data["from_email"]):
                    parsed["_duplicate_warning"] = True
                    _log.warning("Duplicate within 24h: %s", data["from_email"])

                # 저장
                if _save_to_db(conn, data, source, parsed):
                    collected += 1
                else:
                    errors += 1
        finally:
            conn.close()

        _sync_state["last_sync"] = datetime.now(timezone.utc).isoformat()
        _sync_state["last_count"] = collected
        _sync_state["total_collected"] += collected

        return {
            "status": "ok",
            "collected": collected,
            "skipped": skipped,
            "errors": errors,
            "total_messages": len(messages),
        }

    except HTTPException:
        raise
    except Exception as e:
        _sync_state["last_error"] = str(e)
        _log.error("Gmail sync error: %s", e, exc_info=True)
        return {"status": "error", "error": str(e), "collected": 0}
    finally:
        _sync_state["running"] = False


# ── 자동 동기화 (BackgroundTasks) ─────────────────────────────────────────────
_auto_sync_task = None


async def _auto_sync_loop():
    """주기적 Gmail 동기화 루프."""
    while _SYNC_ENABLED:
        try:
            result = sync_emails()
            _log.info("Auto-sync: %s", result)
        except Exception as e:
            _log.error("Auto-sync error: %s", e)
        await asyncio.sleep(_SYNC_INTERVAL)


def start_auto_sync():
    """자동 동기화 시작 (GMAIL_SYNC_ENABLED=true일 때만)."""
    global _auto_sync_task
    if not _SYNC_ENABLED:
        _log.info("Gmail auto-sync disabled (GMAIL_SYNC_ENABLED=false)")
        return
    if _auto_sync_task is None:
        _auto_sync_task = asyncio.create_task(_auto_sync_loop())
        _log.info("Gmail auto-sync started (interval: %ds)", _SYNC_INTERVAL)


# ── API 엔드포인트 ────────────────────────────────────────────────────────────

@router.post("/sync")
async def api_gmail_sync(request: Request):
    """수동 Gmail 동기화 트리거."""
    _check_admin(request)

    if _sync_state["running"]:
        return ok(data={"status": "already_running"}, message="동기화 진행 중입니다.")

    result = sync_emails()
    return ok(data=result, message=f"{result.get('collected', 0)}건 새로 수집")


@router.get("/status")
async def api_gmail_status(request: Request):
    """Gmail 동기화 상태 확인."""
    _check_admin(request)

    return ok(data={
        "running": _sync_state["running"],
        "last_sync": _sync_state["last_sync"],
        "last_count": _sync_state["last_count"],
        "last_error": _sync_state["last_error"],
        "total_collected": _sync_state["total_collected"],
        "auto_sync_enabled": _SYNC_ENABLED,
        "sync_interval": _SYNC_INTERVAL,
        "credentials_configured": bool(_CREDENTIALS_PATH and os.path.exists(_CREDENTIALS_PATH)),
    })
