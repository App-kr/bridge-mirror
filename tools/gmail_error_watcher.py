"""
Gmail IMAP 실시간 모니터 — 다중 계정 지원
================================================================
OAuth2 불필요. 앱 비밀번호로 즉시 작동.
두 계정 동시 모니터링 (bridgejobkr + koreadobby)

동작:
  1. IMAP IDLE로 실시간 대기 (새 메일 즉시 감지)
  2. 모든 수신 이메일 → inbox_emails 테이블 저장
  3. 에러/알림 자동 분류:
       Render 배포실패 / Vercel 배포실패 / Supabase 알림
       API 크레딧 소진 / GitHub 보안 알림 / 결제 알림
  4. 에러 이메일 → 텔레그램 구독자에게 즉시 알림

사용 환경변수 (.env):
  GMAIL_USER           — 주 계정 (예: bridgejobkr@gmail.com)
  GMAIL_APP_PASSWORD   — 주 계정 앱 비밀번호 (16자리)
  GMAIL_USER_2         — 보조 계정 (예: koreadobby@gmail.com)
  GMAIL_APP_PASSWORD_2 — 보조 계정 앱 비밀번호
  TELEGRAM_BOT_TOKEN   — 텔레그램 봇 토큰
  GMAIL_POLL_INTERVAL  — 폴링 간격 초 (기본 30)
  GMAIL_ALL_NOTIFY     — true면 모든 이메일 알림 (기본 false)

앱 비밀번호 발급: myaccount.google.com → 보안 → 앱 비밀번호

실행:
  pythonw.exe tools/gmail_error_watcher.py    ← 백그라운드
  python tools/gmail_error_watcher.py         ← 디버그
"""

import email
import email.header
import imaplib
import logging
import os
import re
import select
import socket
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── 경로 / 환경변수 ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "gmail_watcher.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("gmail_watcher")

TG_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
DB_PATH    = PROJECT_ROOT / "master.db"
POLL_SEC   = int(os.getenv("GMAIL_POLL_INTERVAL", "30"))
ALL_NOTIFY = os.getenv("GMAIL_ALL_NOTIFY", "false").lower() == "true"

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

# 모니터링할 계정 목록 (최대 5개)
_ACCOUNTS: list[tuple[str, str]] = []
for _i in ["", "_2", "_3", "_4", "_5"]:
    _u = os.getenv(f"GMAIL_USER{_i}", "")
    _p = os.getenv(f"GMAIL_APP_PASSWORD{_i}", "")
    if _u and _p:
        _ACCOUNTS.append((_u, _p))


# ── DB ─────────────────────────────────────────────────────────────────────────
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS inbox_emails (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            imap_uid         TEXT UNIQUE,
            subject          TEXT,
            from_name        TEXT,
            from_addr        TEXT,
            received_at      TEXT,
            category         TEXT DEFAULT 'general',
            is_error         INTEGER DEFAULT 0,
            error_type       TEXT,
            severity         TEXT DEFAULT 'info',
            body_preview     TEXT,
            notified_tg      INTEGER DEFAULT 0,
            resolved         INTEGER DEFAULT 0,
            resolved_note    TEXT,
            created_at       TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tg_alert_subscribers (
            chat_id    INTEGER PRIMARY KEY,
            username   TEXT,
            added_at   TEXT NOT NULL,
            active     INTEGER DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_inbox_error   ON inbox_emails(is_error);
        CREATE INDEX IF NOT EXISTS idx_inbox_created ON inbox_emails(created_at);
        CREATE INDEX IF NOT EXISTS idx_inbox_uid     ON inbox_emails(imap_uid);
    """)
    conn.commit()
    return conn


# ── 분류 규칙 ──────────────────────────────────────────────────────────────────
# (error_type, severity, from_patterns, subject_keywords, body_keywords)
_RULES: list[tuple] = [
    ("render_deploy_fail", "critical",
        ["no-reply@render.com", "noreply@render.com"],
        ["error", "failed", "failure"],
        ["encountered an error", "deploy.*failed", "build failed", "didn't complete"]),
    ("vercel_deploy_fail", "critical",
        ["notifications@vercel.com", "noreply@vercel.com"],
        ["error", "failed", "failure"],
        ["error deploying", "failed to deploy", "there was an error"]),
    ("supabase_alert", "warning",
        ["noreply@supabase.io", "support@supabase.io", "no-reply@supabase.io"],
        ["alert", "warning", "error", "limit", "paused", "billing"],
        ["paused", "quota exceeded", "billing", "limit reached"]),
    ("api_credits", "critical",
        ["support@anthropic.com", "noreply@anthropic.com", "billing@anthropic.com"],
        ["credits", "disabled", "billing", "out of"],
        ["out of usage credits", "access.*disabled", "add credits", "api.*disabled"]),
    ("github_security", "warning",
        ["noreply@github.com", "security@github.com"],
        ["token", "security", "added", "sign-in", "suspicious"],
        ["personal access token", "security event", "new sign-in"]),
    ("payment_fail", "critical",
        [],
        ["payment failed", "결제 실패", "invoice overdue", "billing"],
        ["payment.*failed", "payment.*declined", "결제.*실패"]),
    ("render_deploy_ok", "info",
        ["no-reply@render.com"],
        ["deployed", "live", "success"],
        ["successfully deployed", "deploy is live", "deploy succeeded"]),
    ("vercel_deploy_ok", "info",
        ["notifications@vercel.com"],
        ["deployed", "ready", "success"],
        ["successfully deployed", "is ready", "deployment.*ready"]),
]

_CATEGORY_MAP = {
    "render.com": "deploy", "vercel.com": "deploy",
    "supabase.io": "supabase", "supabase.com": "supabase",
    "github.com": "github", "anthropic.com": "api",
}

_ERROR_LABEL = {
    "render_deploy_fail": "Render 배포 실패",
    "vercel_deploy_fail": "Vercel 배포 실패",
    "supabase_alert":     "Supabase 알림",
    "api_credits":        "API 크레딧 소진",
    "github_security":    "GitHub 보안 알림",
    "payment_fail":       "결제 실패",
    "render_deploy_ok":   "Render 배포 성공",
    "vercel_deploy_ok":   "Vercel 배포 성공",
    "general":            "일반 메일",
}

_SEVERITY_EMOJI = {"critical": "🚨", "warning": "⚠️", "info": "✅"}


def classify(from_addr: str, subject: str, body: str) -> tuple[str, str, bool]:
    """(error_type, severity, is_error) 반환."""
    fl = from_addr.lower()
    sl = subject.lower()
    bl = body.lower()
    for et, sev, fp, sk, bk in _RULES:
        from_match = not fp or any(p in fl for p in fp)
        if not from_match:
            continue
        s_hit = any(k in sl for k in sk) if sk else False
        b_hit = any(re.search(k, bl) for k in bk) if bk else False
        if s_hit or b_hit:
            is_err = sev in ("critical", "warning")
            return et, sev, is_err
    return "general", "info", False


def get_category(from_addr: str) -> str:
    fl = from_addr.lower()
    for domain, cat in _CATEGORY_MAP.items():
        if domain in fl:
            return cat
    return "general"


# ── 이메일 파싱 ────────────────────────────────────────────────────────────────
def decode_header(raw: str) -> str:
    """RFC2047 헤더 디코딩."""
    parts = email.header.decode_header(raw or "")
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def get_body(msg: email.message.Message) -> str:
    """이메일 본문 추출 (text/plain 우선, html 폴백)."""
    plain = ""
    html = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if "attachment" in cd:
                continue
            try:
                raw = part.get_payload(decode=True)
                if raw is None:
                    continue
                charset = part.get_content_charset() or "utf-8"
                text = raw.decode(charset, errors="replace")
                if ct == "text/plain" and not plain:
                    plain = text
                elif ct == "text/html" and not html:
                    html = re.sub(r"<[^>]+>", " ", text)
                    html = re.sub(r"\s{2,}", " ", html)
            except Exception:
                pass
    else:
        try:
            raw = msg.get_payload(decode=True)
            if raw:
                charset = msg.get_content_charset() or "utf-8"
                text = raw.decode(charset, errors="replace")
                if msg.get_content_type() == "text/plain":
                    plain = text
                else:
                    html = re.sub(r"<[^>]+>", " ", text)
        except Exception:
            pass
    return (plain or html)[:6000]


# ── 텔레그램 알림 ──────────────────────────────────────────────────────────────
def tg_send(chat_id: int, text: str) -> bool:
    if not TG_TOKEN:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4000], "parse_mode": "HTML"},
            timeout=10,
        )
        return r.status_code == 200
    except Exception as e:
        log.warning("TG send fail chat_id=%d: %s", chat_id, e)
        return False


def build_alert(row: dict) -> str:
    emoji = _SEVERITY_EMOJI.get(row.get("severity", "info"), "🔔")
    label = _ERROR_LABEL.get(row.get("error_type", ""), "알림")
    preview = (row.get("body_preview") or "").strip()[:500]
    rid = row.get("id", "?")
    return (
        f"{emoji} <b>{label}</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📧 <b>발신:</b> {row.get('from_addr','')}\n"
        f"📝 <b>제목:</b> {row.get('subject','')}\n"
        f"⏰ <b>수신:</b> {row.get('received_at','')}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"{preview}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"<code>/resolve {rid}</code>  |  <code>/errors</code>"
    )


def notify_all(conn: sqlite3.Connection, text: str) -> int:
    subs = conn.execute(
        "SELECT chat_id FROM tg_alert_subscribers WHERE active=1"
    ).fetchall()
    if not subs:
        log.warning("구독자 없음 — 봇에서 /alerts on 실행 필요")
        return 0
    return sum(1 for r in subs if tg_send(r["chat_id"], text))


# ── IMAP 연결 ──────────────────────────────────────────────────────────────────
def imap_connect(user: str, password: str) -> imaplib.IMAP4_SSL:
    imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    imap.login(user, password)
    imap.select("INBOX")
    log.info("IMAP 연결 완료: %s", user)
    return imap


def fetch_unseen(imap: imaplib.IMAP4_SSL) -> list[tuple[str, email.message.Message]]:
    """미읽음 메일 리스트 (uid, msg) 반환. 읽음 처리 없음."""
    _, data = imap.uid("search", None, "UNSEEN")
    uids = data[0].split() if data[0] else []
    if not uids:
        return []
    result = []
    for uid in uids:
        try:
            _, msg_data = imap.uid("fetch", uid, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            if isinstance(raw, bytes):
                msg = email.message_from_bytes(raw)
                result.append((uid.decode(), msg))
        except Exception as e:
            log.warning("메시지 %s 가져오기 실패: %s", uid, e)
    return result


def fetch_recent(imap: imaplib.IMAP4_SSL, count: int = 20) -> list[tuple[str, email.message.Message]]:
    """최근 N개 메일 반환 (초기 로딩용)."""
    _, data = imap.uid("search", None, "ALL")
    all_uids = data[0].split() if data[0] else []
    recent_uids = all_uids[-count:] if len(all_uids) > count else all_uids
    result = []
    for uid in recent_uids:
        try:
            _, msg_data = imap.uid("fetch", uid, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            if isinstance(raw, bytes):
                msg = email.message_from_bytes(raw)
                result.append((uid.decode(), msg))
        except Exception as e:
            log.warning("메시지 %s 가져오기 실패: %s", uid, e)
    return result


def process_message(
    uid: str,
    msg: email.message.Message,
    conn: sqlite3.Connection,
) -> bool:
    """메시지 처리. 새 에러이면 True."""
    # 중복 확인
    if conn.execute(
        "SELECT 1 FROM inbox_emails WHERE imap_uid=?", (uid,)
    ).fetchone():
        return False

    subject = decode_header(msg.get("Subject", "(제목 없음)"))
    from_raw = decode_header(msg.get("From", ""))
    date_str = msg.get("Date", "")

    # from 파싱
    from_name = ""
    from_addr = from_raw
    if "<" in from_raw:
        parts = from_raw.split("<")
        from_name = parts[0].strip().strip('"')
        from_addr = parts[1].rstrip(">").strip()

    body = get_body(msg)
    error_type, severity, is_error = classify(from_addr, subject, body)
    category = get_category(from_addr)
    now = datetime.now(timezone.utc).isoformat()

    try:
        conn.execute(
            """INSERT INTO inbox_emails
               (imap_uid, subject, from_name, from_addr, received_at,
                category, is_error, error_type, severity, body_preview, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (uid, subject, from_name, from_addr, date_str,
             category, 1 if is_error else 0, error_type,
             severity, body[:800], now),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return False  # 레이스컨디션 중복
    except Exception as e:
        log.error("DB 저장 실패 uid=%s: %s", uid, e)
        return False

    log.info("[%s] %s | %s | %s",
             severity, category, from_addr[:40], subject[:50])

    # 알림 조건
    should_notify = is_error or ALL_NOTIFY
    if should_notify:
        saved = conn.execute(
            "SELECT * FROM inbox_emails WHERE imap_uid=?", (uid,)
        ).fetchone()
        if saved:
            text = build_alert(dict(saved))
            sent = notify_all(conn, text)
            if sent > 0:
                conn.execute(
                    "UPDATE inbox_emails SET notified_tg=1 WHERE imap_uid=?", (uid,)
                )
                conn.commit()
                log.info("텔레그램 알림 전송: %d명", sent)

    return is_error


# ── IMAP IDLE (실시간 대기) ────────────────────────────────────────────────────
def imap_idle_wait(imap: imaplib.IMAP4_SSL, timeout: int = 25) -> bool:
    """
    IMAP IDLE 명령으로 새 메일 대기.
    새 메일 도착 시 True, timeout 시 False 반환.
    """
    try:
        tag = imap._new_tag().decode()
        imap.send(f"{tag} IDLE\r\n".encode())
        # + idling 응답 대기
        resp = imap.readline()
        if b"idling" not in resp.lower() and b"+ " not in resp:
            return False

        # 소켓에서 응답 대기
        sock = imap.socket()
        start = time.time()
        while time.time() - start < timeout:
            try:
                ready = select.select([sock], [], [], 1.0)[0]
                if ready:
                    data = imap.readline()
                    if b"EXISTS" in data or b"RECENT" in data or b"FETCH" in data:
                        imap.send(b"DONE\r\n")
                        imap.readline()  # OK IDLE 응답 소비
                        return True
            except Exception:
                break

        imap.send(b"DONE\r\n")
        imap.readline()
        return False
    except Exception as e:
        log.debug("IDLE 에러 (폴링 폴백): %s", e)
        return False


# ── 단일 계정 워커 ─────────────────────────────────────────────────────────────
def watch_account(user: str, password: str, conn: sqlite3.Connection):
    """한 계정의 IMAP 감시 루프 (재연결 포함)."""
    while True:
        try:
            imap = imap_connect(user, password)

            # 초기 로딩: 최근 30개 (미처리 에러 복구)
            log.info("[%s] 초기 로딩 중...", user)
            recent = fetch_recent(imap, 30)
            err_cnt = sum(1 for uid, msg in recent if process_message(uid, msg, conn))
            log.info("[%s] 초기 로딩 완료 — 에러 %d건", user, err_cnt)

            log.info("[%s] IDLE 대기 중 (실시간 감지)", user)
            fail = 0
            while True:
                try:
                    new_mail = imap_idle_wait(imap, timeout=25)
                    imap.select("INBOX")
                    unseen = fetch_unseen(imap)
                    for uid, msg in unseen:
                        process_message(uid, msg, conn)
                    if not unseen:
                        imap.noop()
                    fail = 0
                except (imaplib.IMAP4.abort, imaplib.IMAP4.error, OSError) as e:
                    fail += 1
                    log.warning("[%s] IMAP 에러 %d회: %s", user, fail, e)
                    if fail >= 3:
                        break
                    time.sleep(5)
                except Exception as e:
                    log.error("[%s] 에러: %s", user, e)
                    time.sleep(10)

        except imaplib.IMAP4.error as e:
            log.error("[%s] 로그인 실패: %s", user, e)
            time.sleep(120)
        except Exception as e:
            log.error("[%s] 연결 실패: %s", user, e)
            time.sleep(30)

        log.info("[%s] 30초 후 재연결...", user)
        time.sleep(30)


# ── 메인 루프 ──────────────────────────────────────────────────────────────────
def run():
    log.info("=" * 60)
    log.info("Gmail 실시간 모니터 시작")
    log.info("DB: %s | 알림모드: %s", DB_PATH, "전체" if ALL_NOTIFY else "에러만")
    log.info("=" * 60)

    if not _ACCOUNTS:
        log.error(
            "계정 미설정!\n"
            ".env에 다음 추가:\n"
            "  GMAIL_USER=koreadobby@gmail.com\n"
            "  GMAIL_APP_PASSWORD=앱비밀번호16자리\n"
            "앱 비밀번호: myaccount.google.com → 보안 → 앱 비밀번호"
        )
        return

    if not TG_TOKEN:
        log.warning("TELEGRAM_BOT_TOKEN 미설정 — 텔레그램 알림 비활성")

    log.info("모니터링 계정 %d개:", len(_ACCOUNTS))
    for u, _ in _ACCOUNTS:
        log.info("  - %s", u)

    conn = get_conn()

    if len(_ACCOUNTS) == 1:
        # 단일 계정: 직접 실행
        watch_account(_ACCOUNTS[0][0], _ACCOUNTS[0][1], conn)
    else:
        # 다중 계정: 스레드로 병렬 실행
        import threading
        threads = []
        for user, password in _ACCOUNTS:
            t = threading.Thread(
                target=watch_account,
                args=(user, password, conn),
                name=f"watcher-{user}",
                daemon=True,
            )
            t.start()
            threads.append(t)
            log.info("스레드 시작: %s", user)

        # 메인 스레드 유지
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            log.info("종료 요청")


if __name__ == "__main__":
    run()
