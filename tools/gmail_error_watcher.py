"""
Gmail 전체 수신 모니터 — koreadobby@gmail.com
================================================================
동작:
  1. Gmail을 60초마다 폴링 (신규 이메일 수집)
  2. 모든 이메일 → inbox_emails 테이블 저장
  3. 에러/알림 이메일 자동 분류:
       Render 배포 실패 / Vercel 배포 실패 / Supabase 알림
       API 크레딧 소진 / GitHub 보안 알림 / 결제 알림 / 일반 에러
  4. 에러 이메일 → 텔레그램 즉시 알림 (ALL_EMAILS=true면 전체 알림)

실행:
  pythonw.exe tools/gmail_error_watcher.py    ← 백그라운드 (창 없음)
  python tools/gmail_error_watcher.py         ← 디버그

환경변수 (.env):
  GMAIL_CREDENTIALS_JSON  — OAuth2 credentials 경로
  GMAIL_TOKEN_JSON        — OAuth2 token 경로
  TELEGRAM_BOT_TOKEN      — 텔레그램 봇 토큰
  GMAIL_POLL_INTERVAL     — 폴링 간격 초 (기본 60)
  GMAIL_ALL_NOTIFY        — true면 모든 이메일 알림 (기본 false, 에러만)
"""

import base64
import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from email.utils import parseaddr
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ── 로깅 ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "gmail_error_watcher.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("gmail_watcher")

# ── 환경변수 ───────────────────────────────────────────────────────────────────
CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_JSON", "")
TOKEN_PATH = os.getenv("GMAIL_TOKEN_JSON", "")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DB_PATH = Path(os.getenv("BRIDGE_DB_PATH", str(PROJECT_ROOT / "master.db")))
POLL_INTERVAL = int(os.getenv("GMAIL_POLL_INTERVAL", "60"))
ALL_NOTIFY = os.getenv("GMAIL_ALL_NOTIFY", "false").lower() == "true"


# ── DB 초기화 ──────────────────────────────────────────────────────────────────
def init_db(conn: sqlite3.Connection):
    conn.executescript("""
        -- 전체 수신 이메일 (모든 이메일 저장)
        CREATE TABLE IF NOT EXISTS inbox_emails (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            gmail_message_id TEXT UNIQUE NOT NULL,
            subject          TEXT,
            from_name        TEXT,
            from_addr        TEXT,
            received_at      TEXT,
            category         TEXT DEFAULT 'general',
            is_error         INTEGER DEFAULT 0,
            error_type       TEXT,
            severity         TEXT DEFAULT 'info',
            body_preview     TEXT,
            full_body        TEXT,
            labels           TEXT,
            notified_tg      INTEGER DEFAULT 0,
            resolved         INTEGER DEFAULT 0,
            resolved_note    TEXT,
            created_at       TEXT NOT NULL
        );

        -- 텔레그램 알림 구독자
        CREATE TABLE IF NOT EXISTS tg_alert_subscribers (
            chat_id    INTEGER PRIMARY KEY,
            username   TEXT,
            added_at   TEXT NOT NULL,
            active     INTEGER DEFAULT 1
        );

        CREATE INDEX IF NOT EXISTS idx_inbox_resolved  ON inbox_emails(resolved);
        CREATE INDEX IF NOT EXISTS idx_inbox_is_error  ON inbox_emails(is_error);
        CREATE INDEX IF NOT EXISTS idx_inbox_created   ON inbox_emails(created_at);
        CREATE INDEX IF NOT EXISTS idx_inbox_from      ON inbox_emails(from_addr);
    """)
    conn.commit()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


# ── 이메일 분류 ────────────────────────────────────────────────────────────────
# (error_type, severity, from_patterns, subject_keywords, body_keywords)
ERROR_RULES = [
    (
        "render_deploy_fail", "critical",
        ["no-reply@render.com", "noreply@render.com"],
        ["error", "failed", "failure", "deploy"],
        ["encountered an error", "deploy didn't complete", "deploy failed", "build failed"],
    ),
    (
        "vercel_deploy_fail", "critical",
        ["notifications@vercel.com", "noreply@vercel.com"],
        ["error", "failed", "failure", "deployment"],
        ["error deploying", "failed to deploy", "deployment failed", "there was an error"],
    ),
    (
        "supabase_alert", "warning",
        ["noreply@supabase.io", "support@supabase.io", "no-reply@supabase.io"],
        ["alert", "warning", "error", "limit", "quota", "billing", "paused"],
        ["project.*paused", "quota exceeded", "billing", "usage limit"],
    ),
    (
        "api_credits", "critical",
        ["support@anthropic.com", "noreply@anthropic.com", "billing@anthropic.com"],
        ["credits", "disabled", "billing", "usage", "out of"],
        ["out of usage credits", "access.*disabled", "add credits", "api.*disabled"],
    ),
    (
        "github_security", "warning",
        ["noreply@github.com", "security@github.com"],
        ["token", "security", "alert", "added", "removed", "suspicious", "sign-in"],
        ["personal access token", "security event", "new sign-in", "two-factor"],
    ),
    (
        "payment_alert", "critical",
        [],
        ["payment", "결제", "invoice", "billing", "charge", "failed payment", "outstanding"],
        ["payment failed", "payment declined", "invoice", "결제 실패", "결제 오류"],
    ),
    (
        "server_error", "critical",
        [],
        ["500", "503", "exception", "traceback", "critical", "down", "outage", "incident"],
        ["traceback", "exception:", "internal server error", "critical error", "service down"],
    ),
    (
        "deploy_success", "info",
        ["no-reply@render.com", "notifications@vercel.com"],
        ["deployed", "deploy", "success", "live"],
        ["successfully deployed", "your deploy is live", "deployment is ready"],
    ),
]

# 알림 카테고리 (에러 아니지만 중요)
INFO_RULES = [
    (
        "new_application", "info",
        [],
        ["application", "지원", "apply", "cv", "resume"],
        [],
    ),
    (
        "inquiry", "info",
        [],
        ["문의", "inquiry", "구인", "hiring", "채용"],
        [],
    ),
]

SEVERITY_EMOJI = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}

ERROR_TYPE_LABEL = {
    "render_deploy_fail": "Render 배포 실패",
    "vercel_deploy_fail": "Vercel 배포 실패",
    "supabase_alert": "Supabase 알림",
    "api_credits": "API 크레딧 부족/비활성화",
    "github_security": "GitHub 보안 알림",
    "payment_alert": "결제 알림",
    "server_error": "서버 에러",
    "deploy_success": "배포 성공",
    "new_application": "새 지원자",
    "inquiry": "문의",
    "general": "일반",
}


def classify_email(from_addr: str, subject: str, body: str) -> tuple[str, str, bool]:
    """
    이메일 분류.
    Returns: (error_type, severity, is_error)
    """
    from_lower = from_addr.lower()
    subj_lower = subject.lower()
    body_lower = body.lower()

    # 에러 규칙 체크
    for error_type, severity, from_pats, subj_kw, body_kw in ERROR_RULES:
        from_match = not from_pats or any(p in from_lower for p in from_pats)
        if not from_match:
            continue
        subj_match = any(k in subj_lower for k in subj_kw) if subj_kw else False
        body_match = any(re.search(k, body_lower) for k in body_kw) if body_kw else False
        if subj_match or body_match:
            is_err = severity in ("critical", "warning")
            return error_type, severity, is_err

    # 정보성 규칙 체크
    for cat, severity, from_pats, subj_kw, body_kw in INFO_RULES:
        from_match = not from_pats or any(p in from_lower for p in from_pats)
        if not from_match and from_pats:
            continue
        if any(k in subj_lower for k in subj_kw):
            return cat, severity, False

    return "general", "info", False


def detect_category(from_addr: str, subject: str) -> str:
    """이메일 카테고리 태그."""
    from_lower = from_addr.lower()
    subj_lower = subject.lower()

    if any(d in from_lower for d in ["render.com", "vercel.com"]):
        return "deploy"
    if "supabase" in from_lower:
        return "supabase"
    if "github.com" in from_lower:
        return "github"
    if "anthropic.com" in from_lower:
        return "api"
    if any(k in subj_lower for k in ["지원", "application", "apply", "cv", "resume"]):
        return "application"
    if any(k in subj_lower for k in ["문의", "inquiry", "hiring"]):
        return "inquiry"
    if any(k in subj_lower for k in ["payment", "결제", "invoice", "billing"]):
        return "billing"
    return "general"


# ── Gmail API ──────────────────────────────────────────────────────────────────
def get_gmail_service():
    """Gmail API 서비스 객체 생성."""
    if not CREDENTIALS_PATH or not os.path.exists(CREDENTIALS_PATH):
        raise RuntimeError(
            f"Gmail credentials 없음: {CREDENTIALS_PATH}\n"
            ".env에 GMAIL_CREDENTIALS_JSON 설정 필요"
        )
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request as GRequest
        from googleapiclient.discovery import build
    except ImportError:
        raise RuntimeError(
            "Gmail 라이브러리 미설치:\n"
            "pip install google-api-python-client google-auth-oauthlib"
        )

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds = None

    if TOKEN_PATH and os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GRequest())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        if TOKEN_PATH:
            Path(TOKEN_PATH).write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def extract_email_data(msg: dict) -> dict:
    """Gmail API 메시지 → 핵심 데이터."""
    headers = {
        h["name"].lower(): h["value"]
        for h in msg.get("payload", {}).get("headers", [])
    }
    subject = headers.get("subject", "(제목 없음)")
    from_header = headers.get("from", "")
    date_header = headers.get("date", "")
    from_name, from_email = parseaddr(from_header)
    labels = ",".join(msg.get("labelIds", []))

    # 본문 추출
    body = _extract_body(msg.get("payload", {}))

    return {
        "message_id": msg["id"],
        "subject": subject,
        "from_name": from_name,
        "from_addr": from_email or from_header,
        "date": date_header,
        "body": body,
        "labels": labels,
    }


def _extract_body(payload: dict) -> str:
    """payload에서 텍스트 본문 추출."""
    def decode(data: str) -> str:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    if payload.get("body", {}).get("data"):
        return decode(payload["body"]["data"])[:8000]

    parts = payload.get("parts", [])
    plain = ""
    html = ""
    for part in parts:
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data", "")
        if not data:
            # 재귀적으로 nested parts 처리
            sub = _extract_body(part)
            if sub:
                return sub
            continue
        raw = decode(data)
        if mime == "text/plain" and not plain:
            plain = raw
        elif mime == "text/html" and not html:
            html = re.sub(r"<[^>]+>", " ", raw)
            html = re.sub(r"\s{2,}", " ", html)

    result = plain or html
    return result[:8000]


# ── 텔레그램 알림 ──────────────────────────────────────────────────────────────
def send_telegram(chat_id: int, text: str) -> bool:
    if not TG_TOKEN:
        return False
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        log.error("텔레그램 전송 실패 chat_id=%d: %s", chat_id, e)
        return False


def format_error_alert(row: dict) -> str:
    emoji = SEVERITY_EMOJI.get(row.get("severity", "info"), "🔔")
    label = ERROR_TYPE_LABEL.get(row.get("error_type", ""), row.get("error_type", ""))
    preview = (row.get("body_preview") or "")[:400].strip()
    row_id = row.get("id", "?")
    return (
        f"{emoji} <b>[Bridge 알림]</b> — {label}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📧 {row.get('from_addr', '')}\n"
        f"📝 {row.get('subject', '')}\n"
        f"⏰ {row.get('received_at', '')}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{preview}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"/errors  /resolve {row_id}"
    )


def format_info_alert(row: dict) -> str:
    label = ERROR_TYPE_LABEL.get(row.get("category", ""), "일반")
    preview = (row.get("body_preview") or "")[:200].strip()
    return (
        f"📬 <b>[새 이메일]</b> — {label}\n"
        f"📧 {row.get('from_addr', '')}\n"
        f"📝 {row.get('subject', '')}\n"
        f"{preview}"
    )


def get_subscribers(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute(
        "SELECT chat_id FROM tg_alert_subscribers WHERE active=1"
    ).fetchall()
    return [r["chat_id"] for r in rows]


def notify_all(conn: sqlite3.Connection, text: str) -> int:
    subscribers = get_subscribers(conn)
    if not subscribers:
        log.info("알림 구독자 없음 — 봇에서 /alerts on 으로 구독")
        return 0
    sent = sum(1 for cid in subscribers if send_telegram(cid, text))
    return sent


# ── 메인 폴링 ──────────────────────────────────────────────────────────────────
def check_once(service) -> dict:
    """Gmail 1회 체크. 처리 통계 반환."""
    stats = {"total": 0, "new": 0, "errors": 0, "notified": 0}

    try:
        results = service.users().messages().list(
            userId="me",
            q="in:inbox newer_than:2d",
            maxResults=100,
        ).execute()
    except Exception as e:
        log.error("Gmail 조회 실패: %s", e)
        return stats

    messages = results.get("messages", [])
    stats["total"] = len(messages)
    if not messages:
        return stats

    conn = get_conn()
    try:
        for meta in messages:
            msg_id = meta["id"]

            # 중복 확인
            if conn.execute(
                "SELECT 1 FROM inbox_emails WHERE gmail_message_id=?", (msg_id,)
            ).fetchone():
                continue

            # 상세 데이터
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_id, format="full"
                ).execute()
            except Exception as e:
                log.warning("메시지 %s 조회 실패: %s", msg_id, e)
                continue

            data = extract_email_data(msg)
            error_type, severity, is_error = classify_email(
                data["from_addr"], data["subject"], data["body"]
            )
            category = detect_category(data["from_addr"], data["subject"])
            now = datetime.now(timezone.utc).isoformat()

            try:
                conn.execute(
                    """INSERT INTO inbox_emails
                       (gmail_message_id, subject, from_name, from_addr,
                        received_at, category, is_error, error_type, severity,
                        body_preview, full_body, labels, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        msg_id,
                        data["subject"],
                        data["from_name"],
                        data["from_addr"],
                        data["date"],
                        category,
                        1 if is_error else 0,
                        error_type,
                        severity,
                        data["body"][:800],
                        data["body"],
                        data["labels"],
                        now,
                    ),
                )
                conn.commit()
                stats["new"] += 1
                if is_error:
                    stats["errors"] += 1
            except Exception as e:
                log.error("DB 저장 실패 %s: %s", msg_id, e)
                continue

            # 저장된 row
            saved = conn.execute(
                "SELECT * FROM inbox_emails WHERE gmail_message_id=?", (msg_id,)
            ).fetchone()
            saved_dict = dict(saved)

            log.info(
                "[%s] %s | %s | %s",
                severity, category, data["from_addr"][:40], data["subject"][:50]
            )

            # 텔레그램 알림
            should_notify = is_error or ALL_NOTIFY
            if should_notify:
                text = format_error_alert(saved_dict) if is_error else format_info_alert(saved_dict)
                sent = notify_all(conn, text)
                if sent > 0:
                    conn.execute(
                        "UPDATE inbox_emails SET notified_tg=1 WHERE id=?", (saved_dict["id"],)
                    )
                    conn.commit()
                    stats["notified"] += sent

    finally:
        conn.close()

    return stats


def resend_pending(conn: sqlite3.Connection):
    """시작 시 미전송 에러 재전송."""
    pending = conn.execute(
        "SELECT * FROM inbox_emails WHERE notified_tg=0 AND is_error=1 AND resolved=0 "
        "ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    if not pending:
        return
    log.info("미전송 에러 %d건 재전송", len(pending))
    for row in pending:
        d = dict(row)
        text = format_error_alert(d)
        sent = notify_all(conn, text)
        if sent > 0:
            conn.execute("UPDATE inbox_emails SET notified_tg=1 WHERE id=?", (d["id"],))
    conn.commit()


def run():
    """메인 루프."""
    log.info("=" * 60)
    log.info("Gmail 전체 수신 모니터 시작")
    log.info("폴링 간격: %ds | DB: %s", POLL_INTERVAL, DB_PATH)
    log.info("전체 알림: %s", "ON" if ALL_NOTIFY else "OFF (에러만)")
    log.info("=" * 60)

    if not CREDENTIALS_PATH:
        log.error("GMAIL_CREDENTIALS_JSON 환경변수 미설정 — 종료")
        return
    if not TG_TOKEN:
        log.warning("TELEGRAM_BOT_TOKEN 미설정 — 텔레그램 알림 비활성")

    try:
        service = get_gmail_service()
        log.info("Gmail API 인증 완료")
    except Exception as e:
        log.error("Gmail 인증 실패: %s", e)
        return

    # 시작 시 미전송 에러 재전송
    conn = get_conn()
    resend_pending(conn)
    conn.close()

    # 폴링 루프
    while True:
        try:
            stats = check_once(service)
            if stats["new"] > 0:
                log.info(
                    "수집 완료: 신규=%d | 에러=%d | 알림전송=%d",
                    stats["new"], stats["errors"], stats["notified"]
                )
        except Exception as e:
            log.error("폴링 에러: %s", e, exc_info=True)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()
