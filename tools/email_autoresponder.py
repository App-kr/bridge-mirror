"""
email_autoresponder.py — BRIDGE 이메일 자동응답 시스템 v1.0
=============================================================
5분마다 Gmail IMAP 폴링 → 스팸 필터 → 기존 지원자 중복 체크
→ 신규 지원자 패턴 감지 → 확인 후 발송 (또는 자동 발송)

환경변수 (bx 또는 .env):
  GMAIL_USER / GMAIL_ADDRESS    Gmail 주소 (기본: bridgejobkr@gmail.com)
  GMAIL_APP_PASSWORD            Gmail 앱 비밀번호 (bx 관리)
  FORM_URL                      지원 폼 URL
  TELEGRAM_BOT_TOKEN            텔레그램 봇 토큰 (bx 관리)
  TELEGRAM_CHAT_ID              텔레그램 채팅 ID (미설정 시 DB에서 자동 조회)
  EMAIL_AUTO_MODE               false=확인 후 발송 / true=즉시 자동 발송

실행:
  python email_autoresponder.py           # 메인 루프
  python email_autoresponder.py --test    # 단위 테스트
  python email_autoresponder.py --once    # 1회 실행 후 종료
"""

from __future__ import annotations

import email
import email.header
import email.utils
import socket
import imaplib
import json
import logging
import os
import re
import smtplib
import sqlite3
import sys
import threading
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ── 경로 설정 ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_FILE = PROJECT_ROOT / ".claude" / "email_processed.json"
PENDING_FILE   = PROJECT_ROOT / ".claude" / "email_pending.json"
DB_PATH        = PROJECT_ROOT / "master.db"
LOG_PATH       = Path(r"Q:\Claudework\logs\email_autoresponder.log")
POLL_INTERVAL  = 600  # 10분 (Task Scheduler --once 방식이므로 루프 모드 전용)
_KST = timezone(timedelta(hours=9))
_BIZ_START = 9   # KST 09:00
_BIZ_END   = 18  # KST 18:00


def _is_business_hours() -> bool:
    """KST 기준 업무시간(09:00~18:00)이면 True."""
    return _BIZ_START <= datetime.now(_KST).hour < _BIZ_END

# ── 로깅 ─────────────────────────────────────────────────────────────────────
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
_fmt = "[%(asctime)s] [%(levelname)s] %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=_fmt,
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(str(LOG_PATH), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("email_auto")

# ── .env 로딩 ────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


# ── Credential 로더 (bx 우선, .env 폴백) ────────────────────────────────────
def _bx_read(key: str) -> str | None:
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "tools"))
        from bx import _read as bx_read
        v = bx_read(key)
        return v if v else None
    except Exception:
        return None


def _get_cred(key: str, env_fallbacks: list[str] | None = None) -> str:
    """bx → env_fallbacks 순으로 크리덴셜 조회."""
    v = _bx_read(key)
    if v:
        return v
    if env_fallbacks:
        for k in env_fallbacks:
            v = os.getenv(k, "")
            if v:
                return v
    return os.getenv(key, "")


# ── 설정 로딩 ────────────────────────────────────────────────────────────────
def load_config() -> dict:
    gmail_addr = (
        os.getenv("GMAIL_USER")
        or os.getenv("GMAIL_ADDRESS")
        or "bridgejobkr@gmail.com"
    )
    gmail_pass = _get_cred("BRIDGEJOBKR_GMAIL_APPKEY", ["GMAIL_APP_PASSWORD", "BRIDGE_SMTP_PASS"])
    gmail_pass = gmail_pass.replace(" ", "").strip()  # 앱 비밀번호 공백 제거
    form_url   = os.getenv("FORM_URL", "https://bridgejob.co.kr/apply")
    tg_token   = _get_cred("TELEGRAM_BOT_TOKEN")
    auto_mode  = os.getenv("EMAIL_AUTO_MODE", "true").lower() == "true"

    # TELEGRAM_CHAT_ID: env → DB
    tg_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not tg_chat_id:
        try:
            conn = sqlite3.connect(str(DB_PATH))
            row = conn.execute(
                "SELECT chat_id FROM tg_alert_subscribers WHERE active=1 LIMIT 1"
            ).fetchone()
            conn.close()
            if row:
                tg_chat_id = str(row[0])
        except Exception:
            pass

    return {
        "gmail_addr": gmail_addr,
        "gmail_pass": gmail_pass,
        "form_url":   form_url,
        "tg_token":   tg_token,
        "tg_chat_id": tg_chat_id,
        "auto_mode":  auto_mode,
    }


# ── Processed / Pending 캐시 ─────────────────────────────────────────────────
def _load_processed() -> set:
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(PROCESSED_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_processed(ids: set) -> None:
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f)


def _load_pending() -> dict:
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(PENDING_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_pending(pending: dict) -> None:
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)


def _remove_pending(mail_id: str) -> None:
    p = _load_pending()
    p.pop(mail_id, None)
    _save_pending(p)


# ── 텔레그램 ──────────────────────────────────────────────────────────────────
def tg_send(token: str, chat_id: str, text: str) -> bool:
    if not token or not chat_id:
        log.warning("[TG] 토큰/채팅ID 없음 — 알림 건너뜀")
        return False
    try:
        data = json.dumps({
            "chat_id": chat_id,
            "text": text[:4096],
            # parse_mode 제거 — 특수문자 포함 시 HTML 파싱 오류 방지
        }).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
        log.info(f"[TG] 발송 완료: {text[:60]}")
        return True
    except Exception as e:
        log.error(f"[TG] 발송 실패: {e}")
        return False


def tg_get_updates(token: str, offset: int) -> list:
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates?timeout=30&offset={offset}"
        with urllib.request.urlopen(url, timeout=35) as r:
            return json.loads(r.read()).get("result", [])
    except Exception:
        return []


# ── 스팸 필터 ─────────────────────────────────────────────────────────────────
_SPAM_DOMAINS = {
    "noreply", "no-reply", "mailer-daemon", "postmaster",
    "bounce", "bounces", "notifications", "donotreply",
}

# 특정 발신 도메인 전체 차단 (서비스 알림 / 광고성 메일)
_SPAM_SENDER_DOMAINS = {
    # Craigslist 시스템 (RPA 게시 확인)
    "craigslist.org",

    # 개발/호스팅 서비스
    "render.com", "github.com", "vercel.com", "netlify.com",
    "heroku.com", "fly.io", "railway.app", "digitalocean.com",
    "cloudflare.com", "amazonaws.com", "aws.amazon.com",
    "supabase.com", "supabase.io",
    "planetscale.com", "neon.tech", "prisma.io",
    "gitlab.com", "bitbucket.org",

    # Google / 계정 서비스
    "google.com", "accounts.google.com", "googlegroups.com",

    # 이메일·마케팅 서비스 (자동 발송)
    "sendgrid.net", "sendgrid.com", "mailchimp.com",
    "mailgun.org", "mg.mail.com", "sendpulse.com",
    "klaviyo.com", "constantcontact.com",

    # 업무 도구
    "linkedin.com", "notion.so", "slack.com",
    "zoom.us", "dropbox.com", "atlassian.com",
    "trello.com", "asana.com", "monday.com",
    "stripe.com", "paypal.com", "payoneer.com",
    "namecheap.com", "godaddy.com",
    "twilio.com", "intercom.io",

    # ESL 구인 광고 사이트 (지원자는 개인 메일로만 연락)
    "eslgorilla.com", "eslcafe.com", "waygook.org",
    "koreabridge.net",
    # teast.com 제외 — Teast Admin 알림 메일은 국적 필터 후 자동응답 대상
}
# reply.craigslist.org는 실제 지원자 → 차단 금지

# ── Teast Admin 전용 설정 ──────────────────────────────────────────────────────
_TEAST_DOMAINS = {"teast.com", "teast.co.kr"}

# 허용 국적 키워드 (미국·영국·캐나다·호주·아일랜드·뉴질랜드)
_ALLOWED_NATIONALITIES = {
    # 미국
    "american", "usa", "u.s.a", "u.s", "united states",
    # 영국
    "british", "uk", "u.k", "united kingdom",
    "english", "england", "scottish", "scotland", "welsh", "wales",
    # 캐나다
    "canadian", "canada",
    # 호주
    "australian", "australia",
    # 아일랜드
    "irish", "ireland",
    # 뉴질랜드
    "new zealand", "new zealander", "nz",
}


def is_teast_admin(from_addr: str) -> bool:
    """Teast Admin 발신 메일 여부."""
    if "@" not in from_addr:
        return False
    domain = from_addr.split("@")[1].lower()
    return domain in _TEAST_DOMAINS


def teast_allowed_nationality(body: str) -> str | None:
    """Teast 본문에서 허용 국적 키워드 감지 → 감지된 키워드 반환, 없으면 None."""
    body_low = body.lower()
    for nat in _ALLOWED_NATIONALITIES:
        if nat in body_low:
            return nat
    return None


_SPAM_SUBJECT_KW = [
    "unsubscribe", "newsletter", "promotion", "offer", "discount",
    "make money", "crypto", "investment", "casino", "lottery", "winner",
    "click here", "limited time", "act now", "free gift",
]

# 제목 prefix 차단 — 향후 로직 추가 예정
_SPAM_SUBJECT_PREFIX = [
    "cl posting:",   # Craigslist 시스템 메시지 (추후 별도 로직으로 교체 예정)
]


def is_spam(from_addr: str, subject: str, body: str, headers: dict,
            self_addr: str) -> bool:
    # 자기 자신
    if from_addr.lower() == self_addr.lower():
        return True
    # 특정 발신 도메인 전체 차단
    if "@" in from_addr:
        sender_domain = from_addr.split("@")[1].lower()
        if sender_domain in _SPAM_SENDER_DOMAINS:
            return True
    # 발신 로컬파트 도메인 체크
    domain_local = from_addr.split("@")[0].lower() if "@" in from_addr else from_addr.lower()
    if any(sp in domain_local for sp in _SPAM_DOMAINS):
        return True
    if "@" in from_addr:
        domain = from_addr.split("@")[1].lower()
        if any(sp in domain for sp in _SPAM_DOMAINS):
            return True
    # 제목 prefix 차단
    subj_low = subject.lower().strip()
    if any(subj_low.startswith(p) for p in _SPAM_SUBJECT_PREFIX):
        return True
    # 제목 키워드
    if any(kw in subj_low for kw in _SPAM_SUBJECT_KW):
        return True
    # 본문 링크 10개 이상
    links = re.findall(r'https?://', body)
    if len(links) >= 10:
        return True
    # SPF/DKIM 실패 헤더
    auth_results = headers.get("authentication-results", "").lower()
    if auth_results and ("spf=fail" in auth_results or "dkim=fail" in auth_results):
        return True
    return False


# ── 신규 지원자 패턴 감지 ────────────────────────────────────────────────────
_APPLICANT_KW = [
    "apply", "application", "teaching position", "teacher",
    "craigslist", "teast", "korea", "eslcafe",
    "resume", "cv", "curriculum vitae",
    "interested in", "opening", "reaching out",
    "please find", "looking forward", "full-time",
    "part-time", "position", "job posting", "vacancy",
]


def is_applicant(subject: str, body: str) -> bool:
    """제목+본문 합쳐서 키워드 2개 이상 포함 시 True.
    단, 다음 패턴은 명시적으로 제외:
    - "online" 포지션 (온라인 강의, 한국 근무 아님)
    - 이미 지원 완료된 재응답 ("has been received successfully")
    """
    subj_low = subject.lower()
    # 이미 지원한 사람의 재응답 — 폼 링크 재발송 불필요
    if "has been received successfully" in subj_low:
        return False
    # 온라인 전용 포지션 — 한국 근무 아님
    if re.search(r"\bonline\b.*\b(teach|tutor|esl|english)\b", subj_low) or \
       re.search(r"\b(teach|tutor|esl|english)\b.*\bonline\b", subj_low):
        return False
    text = (subj_low + " " + body.lower())
    matched = sum(1 for kw in _APPLICANT_KW if kw in text)
    return matched >= 2


# ── 이미 자동응답 발송 여부 확인 ─────────────────────────────────────────────
def already_replied(email_addr: str) -> bool:
    """email_logs에 해당 주소로 SENT 기록이 있으면 True (대화 중)."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        _ensure_email_logs(conn)
        row = conn.execute(
            "SELECT 1 FROM email_logs WHERE from_email=? AND status='SENT' LIMIT 1",
            (email_addr,),
        ).fetchone()
        conn.close()
        return row is not None
    except Exception as e:
        log.error(f"[DB] email_logs 조회 실패: {e}")
    return False


def has_prior_contact(imap_conn: imaplib.IMAP4_SSL, addr: str,
                      current_uid: str, days: int = 365) -> bool:
    """1년이내 해당 주소와 메일을 주고받은 이력이 있으면 True.

    ① 보낸편지함(TO addr) — 수동 발송 포함 전체
    ② 받은편지함(FROM addr, 현재 UID 제외) — 이전에 먼저 연락 온 경우
    """
    from datetime import timedelta
    since_str = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    _result: list = []

    def _do_check():
        # ① 보낸편지함 확인
        for folder in ('"[Gmail]/Sent Mail"', '"[Gmail]/Sent"', "Sent"):
            try:
                typ, _ = imap_conn.select(folder, readonly=True)
                if typ != "OK":
                    continue
                _, data = imap_conn.search(None, f'TO "{addr}" SINCE {since_str}')
                if data and data[0]:
                    _result.append(True)
                    return
                break
            except Exception:
                continue

        # ② 받은편지함 확인 (현재 처리 중인 UID 제외)
        try:
            imap_conn.select("INBOX")
            _, data = imap_conn.search(None, f'FROM "{addr}" SINCE {since_str}')
            if data and data[0]:
                others = [u for u in data[0].split()
                          if u.decode() != current_uid]
                if others:
                    _result.append(True)
                    return
        except Exception:
            pass

        _result.append(False)

    t = threading.Thread(target=_do_check, daemon=True)
    t.start()
    t.join(timeout=10)

    try:
        imap_conn.select("INBOX")
    except Exception:
        pass

    if not _result:
        log.warning(f"[IMAP] 연락이력 조회 10초 타임아웃 addr={addr} → 발송 진행")
        return False
    return _result[0]


# ── 기존 지원자 DB 조회 ──────────────────────────────────────────────────────
def lookup_candidate(email_addr: str) -> dict | None:
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """SELECT sheet_number, full_name AS name, status, created_at
               FROM candidates WHERE email=? AND is_deleted!=1
               ORDER BY created_at DESC LIMIT 1""",
            (email_addr,),
        ).fetchone()
        conn.close()
        if row:
            return dict(row)
    except Exception as e:
        log.error(f"[DB] candidates 조회 실패: {e}")
    return None


# ── email_logs DB 기록 ────────────────────────────────────────────────────────
def _ensure_email_logs(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          from_email TEXT NOT NULL,
          from_name TEXT,
          subject TEXT,
          received_at DATETIME,
          sent_at DATETIME,
          type TEXT,
          status TEXT,
          mail_uid TEXT UNIQUE,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 혹시 누락된 컬럼 추가 (데이터 삭제 없음)
    existing = {row[1] for row in conn.execute("PRAGMA table_info(email_logs)")}
    for col, defn in [
        ("from_name", "TEXT"),
        ("sent_at",   "DATETIME"),
        ("type",      "TEXT"),
        ("status",    "TEXT"),
        ("mail_uid",  "TEXT"),
    ]:
        if col not in existing:
            try:
                conn.execute(f"ALTER TABLE email_logs ADD COLUMN {col} {defn}")
            except Exception:
                pass
    conn.commit()


def log_email(from_email: str, from_name: str, subject: str,
              received_at: str, sent_at: str | None,
              etype: str, status: str, mail_uid: str) -> None:
    try:
        conn = sqlite3.connect(str(DB_PATH))
        _ensure_email_logs(conn)
        conn.execute(
            """INSERT OR IGNORE INTO email_logs
               (from_email, from_name, subject, received_at, sent_at, type, status, mail_uid)
               VALUES (?,?,?,?,?,?,?,?)""",
            (from_email, from_name, subject, received_at, sent_at, etype, status, mail_uid),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.error(f"[DB] email_logs 기록 실패: {e}")


_APPLY_URL = "https://tinyurl.com/bridgekr"

# ── 답장 초안 생성 ───────────────────────────────────────────────────────────
def build_reply(first_name: str, orig_subject: str, form_url: str) -> tuple[str, str, str]:
    """(subject, plain_text, html) 반환"""
    subject = f"Re: {orig_subject}"

    _link_text = "\U0001f449 \U0001f517 Apply [Link: English Teacher Application(Google form)]"

    plain = (
        "Hello,\n"
        "This is BRIDGE Agency.\n\n"
        "We have received your application!\n"
        "For now, as we don\u2019t have your application on file, please complete our quick registration form (approx. 2-5 mins) to get started:\n"
        f"{_link_text}: {_APPLY_URL}\n\n"
        "Please ensure the following are included:\n\n"
        "\u2022 CV (Workplace Name, Location, Dates in YY/MM format)\n"
        "\u2022 Cover Letter & Photo that taken 1 year\n"
        "\u2022 Scanned Apostilled Documents\n"
        "\u2022 Short Video Intro (1-3 mins)\n\n"
        "This helps us understand your specific needs and find the right match for you. "
        "Once reviewed, we will reach out to schedule a brief 5-minute Google Meet.\n\n"
        "kind regards,\n\nBRIDGE"
    )

    html = (
        "<div style='font-family:Arial,sans-serif;font-size:14px;line-height:1.6'>"
        "<p>Hello,<br>This is BRIDGE Agency.</p>"
        "<p>We have received your application!<br>"
        "For now, as we don\u2019t have your application on file, please complete our quick registration form (approx. 2-5 mins) to get started:<br>"
        f"\U0001f449 \U0001f517 <a href='{_APPLY_URL}'>Apply [Link: English Teacher Application(Google form)]</a></p>"
        "<p>Please ensure the following are included:</p>"
        "<ul style='margin:0;padding-left:20px'>"
        "<li>CV (Workplace Name, Location, Dates in YY/MM format)</li>"
        "<li>Cover Letter &amp; Photo that taken 1 year</li>"
        "<li>Scanned Apostilled Documents</li>"
        "<li>Short Video Intro (1-3 mins)</li>"
        "</ul>"
        "<p>This helps us understand your specific needs and find the right match for you. "
        "Once reviewed, we will reach out to schedule a brief 5-minute Google Meet.</p>"
        "<p>kind regards,<br><br><strong>BRIDGE</strong></p>"
        "</div>"
    )

    return subject, plain, html


# ── SMTP 발송 ─────────────────────────────────────────────────────────────────
def send_reply(cfg: dict, to_addr: str, to_name: str,
               subject: str, body: str, retries: int = 3,
               html: str | None = None) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"BRIDGE Agency <{cfg['gmail_addr']}>"
    msg["To"]      = f"{to_name} <{to_addr}>" if to_name else to_addr
    msg.attach(MIMEText(body, "plain", "utf-8"))
    if html:
        msg.attach(MIMEText(html, "html", "utf-8"))

    for attempt in range(1, retries + 1):
        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as s:
                s.ehlo()
                s.starttls()
                s.login(cfg["gmail_addr"], cfg["gmail_pass"])
                s.sendmail(cfg["gmail_addr"], [to_addr], msg.as_string())
            log.info(f"[SMTP] 발송 완료 → {to_addr}")
            return True
        except Exception as e:
            log.warning(f"[SMTP] 발송 실패 ({attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(30)
    return False


# ── IMAP 연결 ─────────────────────────────────────────────────────────────────
def imap_connect(cfg: dict, retries: int = 3) -> imaplib.IMAP4_SSL | None:
    for attempt in range(1, retries + 1):
        try:
            m = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=30)
            m.login(cfg["gmail_addr"], cfg["gmail_pass"])
            return m
        except Exception as e:
            log.warning(f"[IMAP] 연결 실패 ({attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(30)
    tg_send(cfg["tg_token"], cfg["tg_chat_id"],
            "🚨 BRIDGE 이메일: IMAP 연결 3회 실패 — 점검 필요")
    return None


# ── 메일 파싱 ────────────────────────────────────────────────────────────────
def _decode_header(raw: str) -> str:
    parts = email.header.decode_header(raw or "")
    result = []
    for byt, enc in parts:
        if isinstance(byt, bytes):
            result.append(byt.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(str(byt))
    return "".join(result)


def _get_body(msg: email.message.Message) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                try:
                    body += part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="replace"
            )
        except Exception:
            pass
    return body


def _get_headers(msg: email.message.Message) -> dict:
    return {k.lower(): v for k, v in msg.items()}


# ── 메인 처리 루프 ────────────────────────────────────────────────────────────
def process_inbox(cfg: dict) -> None:
    # KST 09:00~18:00 외에는 실행 안 함
    if not _is_business_hours():
        now_kst = datetime.now(_KST).strftime("%H:%M")
        log.info(f"[SKIP] 업무시간 외 (KST {now_kst}) — 폴링 건너뜀")
        return

    processed = _load_processed()

    imap = imap_connect(cfg)
    if imap is None:
        return

    try:
        imap.select("INBOX")
        # 미읽음 전체 조회
        _, data = imap.search(None, "UNSEEN")
        uid_list = data[0].split() if data[0] else []
        log.info(f"[IMAP] 미읽음 {len(uid_list)}건")

        for uid_b in uid_list:
            uid = uid_b.decode()
            if uid in processed:
                continue

            # 메일 1건 처리 최대 20초 제한
            _fetch_result: list = []
            def _do_fetch(u=uid_b):
                try:
                    r = imap.fetch(u, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
                    _fetch_result.append(r)
                except Exception as e:
                    _fetch_result.append(e)
            _t = threading.Thread(target=_do_fetch, daemon=True)
            _t.start(); _t.join(timeout=20)
            if not _fetch_result:
                log.warning(f"[IMAP] 헤더 fetch 20초 타임아웃 uid={uid} → 강제 재연결")
                try:
                    imap.socket().close()
                except Exception:
                    pass
                _t.join(timeout=3)
                imap = imap_connect(cfg)
                if imap:
                    imap.select("INBOX")
                continue
            _r = _fetch_result[0]
            if isinstance(_r, Exception):
                log.warning(f"[IMAP] 헤더 fetch 오류 uid={uid}: {_r}")
                continue

            try:
                _, hdr_data = _r
                raw_hdr = hdr_data[0][1] if hdr_data and hdr_data[0] else b""
                hdr_msg = email.message_from_bytes(raw_hdr)

                subject     = _decode_header(hdr_msg.get("Subject", "(no subject)"))
                from_raw    = _decode_header(hdr_msg.get("From", ""))
                from_name, from_addr = email.utils.parseaddr(from_raw)
                from_addr   = from_addr.lower().strip()
                received_at = hdr_msg.get("Date", "")

                # ── STEP A: 스팸 필터 (헤더 기반) ────────────────────────────
                if is_spam(from_addr, subject, "", {}, cfg["gmail_addr"]):
                    log.info(f"[SPAM] {from_addr} | {subject}")
                    processed.add(uid)
                    _save_processed(processed)
                    continue

                # ── STEP A-1: Teast Admin 메일 — 국적 필터 전용 처리 ─────────
                if is_teast_admin(from_addr):
                    # Teast는 시스템 발신이므로 연락이력 체크 생략, 본문 국적만 확인
                    _teast_buf: list = []
                    def _do_teast_body(u=uid_b):
                        try:
                            r = imap.fetch(u, "(BODY.PEEK[1]<0.4096>)")
                            _teast_buf.append(r)
                        except Exception as e:
                            _teast_buf.append(e)
                    _tt = threading.Thread(target=_do_teast_body, daemon=True)
                    _tt.start(); _tt.join(timeout=15)
                    teast_body = ""
                    if _teast_buf and not isinstance(_teast_buf[0], Exception):
                        try:
                            teast_body = _teast_buf[0][1][0][1].decode("utf-8", errors="ignore")
                        except Exception:
                            teast_body = ""
                    found_nat = teast_allowed_nationality(teast_body)
                    if not found_nat:
                        log.info(f"[TEAST] 허용 국적 없음 → 스킵: {from_addr} | {subject}")
                        processed.add(uid)
                        _save_processed(processed)
                        continue
                    log.info(f"[TEAST] 허용 국적 감지({found_nat}) → 자동발송 진행: {from_addr} | {subject}")
                    first_name = from_name.split()[0] if from_name else "there"
                    subj, body_reply, html_reply = build_reply(first_name, subject, cfg["form_url"])
                    ok = send_reply(cfg, from_addr, from_name, subj, body_reply, html=html_reply)
                    sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if ok else None
                    status_val = "SENT" if ok else "FAILED"
                    if ok:
                        tg_send(cfg["tg_token"], cfg["tg_chat_id"],
                                f"강사 {from_name} - 메일기록 1회 첫 접수 안내메일 발송완료")
                        imap.store(uid_b, "+FLAGS", "\\Seen")
                    else:
                        tg_send(cfg["tg_token"], cfg["tg_chat_id"],
                                f"🚨 Teast 발송 실패: {from_addr}")
                    log_email(from_addr, from_name, subject, received_at,
                              sent_at, "TEAST", status_val, uid)
                    processed.add(uid)
                    _save_processed(processed)
                    continue  # Teast 처리 완료 — 일반 로직 건너뜀

                # ── STEP B-0: 이미 발송한 주소 → 대화 중, 안읽음 유지 ────────
                # DB 기록(자동발송) + Gmail 보낸편지함(수동발송 포함 전체) 이중 체크
                if already_replied(from_addr):
                    log.info(f"[CONV] DB 발송 이력 있음 → 안읽음 유지: {from_addr} | {subject}")
                    continue
                if has_prior_contact(imap, from_addr, uid):
                    log.info(f"[CONV] 1년이내 연락 이력 있음 → 안읽음 유지: {from_addr} | {subject}")
                    continue

                # ── STEP B: 기존 지원자 중복 체크 (헤더만으로 충분) ────────
                existing = lookup_candidate(from_addr)
                if existing:
                    teacher_id  = existing.get("sheet_number", "?")
                    name        = existing.get("name", "?")
                    status      = existing.get("status", "?")
                    created_at  = existing.get("created_at", "?")
                    tg_send(cfg["tg_token"], cfg["tg_chat_id"],
                            f"⚠️ 기존 지원자 재문의\n"
                            f"📧 {from_addr}\n"
                            f"👤 {name} (ID: {teacher_id})\n"
                            f"📅 등록일: {created_at}\n"
                            f"📋 현재상태: {status}\n"
                            f"💬 제목: {subject}\n"
                            f"→ Gmail 직접 확인 필요")
                    log_email(from_addr, from_name, subject, received_at,
                              None, "RETURNING", "PENDING", uid)
                    continue

                # ── STEP C: 본문 4KB 패치 + BRIDGE 인용 마커 체크 + 지원자 패턴 감지 ─
                # 항상 본문을 가져와 ① BRIDGE 인용(대화중) ② 지원자 패턴 순으로 확인
                body = ""
                _body_buf2: list = []

                def _do_body(u=uid_b):
                    try:
                        r = imap.fetch(u, "(BODY.PEEK[1]<0.4096>)")
                        _body_buf2.append(r)
                    except Exception as e:
                        _body_buf2.append(e)

                _bt = threading.Thread(target=_do_body, daemon=True)
                _bt.start()
                _bt.join(timeout=15)

                if not _body_buf2:
                    # 타임아웃 — 소켓 강제 종료 후 재연결
                    log.warning(f"[IMAP] body fetch 15초 타임아웃 uid={uid} — 강제 재연결")
                    try:
                        imap.socket().close()
                    except Exception:
                        pass
                    _bt.join(timeout=3)  # 스레드 정리 대기
                    imap = imap_connect(cfg)
                    if imap:
                        imap.select("INBOX")
                    continue  # 이 UID는 다음 폴링에서 재시도
                elif not isinstance(_body_buf2[0], Exception):
                    try:
                        body = _body_buf2[0][1][0][1].decode("utf-8", errors="ignore")
                    except Exception:
                        body = ""

                # BRIDGE 자신의 메일이 인용된 경우 → 대화 진행 중, 발송 금지
                _BRIDGE_MARKERS = [
                    "this is bridge agency",
                    "tinyurl.com/bridgekr",
                    "we have received your application",
                    "english teacher application(google form)",
                ]
                if any(m in body.lower() for m in _BRIDGE_MARKERS):
                    log.info(f"[CONV] BRIDGE 회신 인용 감지 → 대화 중, 안읽음 유지: {from_addr} | {subject}")
                    continue

                if not is_applicant(subject, body):
                    log.info(f"[UNKNOWN] 패턴 미해당 → 안읽음 유지: {from_addr} | {subject}")
                    continue

                # ── STEP D: 초안 생성 및 발송 처리 ─────────────────────────
                first_name = (from_name.split()[0] if from_name else "there")
                subj, body_reply, html_reply = build_reply(first_name, subject, cfg["form_url"])

                if cfg["auto_mode"]:
                    # 즉시 자동 발송
                    ok = send_reply(cfg, from_addr, from_name, subj, body_reply, html=html_reply)
                    status_val = "SENT" if ok else "FAILED"
                    sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if ok else None

                    if ok:
                        tg_send(cfg["tg_token"], cfg["tg_chat_id"],
                                f"강사 {from_name} - 메일기록 1회 첫 접수 안내메일 발송완료")
                        # 읽음 처리
                        imap.store(uid_b, "+FLAGS", "\\Seen")
                    else:
                        tg_send(cfg["tg_token"], cfg["tg_chat_id"],
                                f"🚨 발송 실패: {from_addr} — 수동 발송 필요")

                    log_email(from_addr, from_name, subject, received_at,
                              sent_at, "NEW_APPLICANT", status_val, uid)
                    processed.add(uid)
                    _save_processed(processed)

                else:
                    # 확인 후 발송 모드 — pending에 저장
                    pending = _load_pending()
                    # 같은 발신자가 이미 pending에 있으면 중복 추가 금지
                    already = [v for v in pending.values()
                               if v.get("from_addr", "").lower() == from_addr.lower()]
                    if already:
                        log.info(f"[PENDING] 중복 스킵: {from_addr} 이미 대기 중")
                        continue
                    pending[uid] = {
                        "from_addr":   from_addr,
                        "from_name":   from_name,
                        "subject":     subject,
                        "received_at": received_at,
                        "reply_subj":  subj,
                        "reply_body":  body_reply,
                        "reply_html":  html_reply,
                        "imap_uid":    uid,
                    }
                    _save_pending(pending)

                    tg_send(cfg["tg_token"], cfg["tg_chat_id"],
                            f"📧 새 지원자 메일\n"
                            f"👤 발신: {from_name} &lt;{from_addr}&gt;\n"
                            f"💬 제목: {subject}\n"
                            f"📅 수신: {received_at}\n\n"
                            f"✅ 발송하려면: /send_{uid}\n"
                            f"❌ 무시하려면: /skip_{uid}")
                    log.info(f"[PENDING] uid={uid} {from_addr} | {subject}")

            except Exception as e:
                log.error(f"[PROC] uid={uid} 처리 오류: {e}", exc_info=True)
                # 한 메일 오류가 전체 루프 중단 안 함
                continue

    except Exception as e:
        log.error(f"[IMAP] inbox 처리 오류: {e}", exc_info=True)
    finally:
        try:
            imap.logout()
        except Exception:
            pass


# ── 텔레그램 커맨드 폴링 ─────────────────────────────────────────────────────
def _tg_command_loop(cfg: dict, stop_event: threading.Event) -> None:
    offset = 0
    log.info("[TG] 커맨드 폴링 시작")

    while not stop_event.is_set():
        try:
            updates = tg_get_updates(cfg["tg_token"], offset)
            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("channel_post") or {}
                text = msg.get("text", "")

                # /send_{uid}
                m = re.match(r"/send_(\S+)", text)
                if m:
                    uid = m.group(1)
                    pending = _load_pending()
                    if uid in pending:
                        item = pending[uid]
                        ok = send_reply(cfg, item["from_addr"], item["from_name"],
                                        item["reply_subj"], item["reply_body"],
                                        html=item.get("reply_html"))
                        if ok:
                            sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            log_email(item["from_addr"], item["from_name"], item["subject"],
                                      item["received_at"], sent_at,
                                      "NEW_APPLICANT", "SENT", uid)
                            _remove_pending(uid)
                            processed = _load_processed()
                            processed.add(uid)
                            _save_processed(processed)
                            tg_send(cfg["tg_token"], cfg["tg_chat_id"],
                                    f"✅ 발송 완료\n👤 {item['from_name']} &lt;{item['from_addr']}&gt;")
                        else:
                            tg_send(cfg["tg_token"], cfg["tg_chat_id"],
                                    f"🚨 발송 실패: {item['from_addr']} — 재시도 또는 수동 발송 필요")
                    else:
                        tg_send(cfg["tg_token"], cfg["tg_chat_id"],
                                f"⚠️ /send_{uid}: 해당 대기 메일 없음 (이미 처리됐거나 만료)")
                    continue

                # /skip_{uid}
                m = re.match(r"/skip_(\S+)", text)
                if m:
                    uid = m.group(1)
                    pending = _load_pending()
                    if uid in pending:
                        item = pending[uid]
                        log_email(item["from_addr"], item["from_name"], item["subject"],
                                  item["received_at"], None,
                                  "NEW_APPLICANT", "SKIPPED", uid)
                        _remove_pending(uid)
                        processed = _load_processed()
                        processed.add(uid)
                        _save_processed(processed)
                        tg_send(cfg["tg_token"], cfg["tg_chat_id"],
                                f"⏭ 건너뜀 처리: {item['from_addr']}")
                    else:
                        tg_send(cfg["tg_token"], cfg["tg_chat_id"],
                                f"⚠️ /skip_{uid}: 해당 대기 메일 없음")
                    continue

        except Exception as e:
            log.error(f"[TG] 커맨드 폴링 오류: {e}")
            time.sleep(10)

    log.info("[TG] 커맨드 폴링 종료")


# ── 단위 테스트 ───────────────────────────────────────────────────────────────
def run_tests(cfg: dict) -> None:
    print("\n" + "=" * 60)
    print("BRIDGE Email Autoresponder — 단위 테스트")
    print("=" * 60)

    errors = 0

    # 스팸 필터 테스트
    print("\n[1] 스팸 필터 테스트")
    spam_cases = [
        # (from, subj, body, headers, expected_is_spam)
        ("noreply@example.com",    "Newsletter",           "body",   {},                         True),   # noreply 도메인
        ("mailer-daemon@foo.com",  "hi",                   "body",   {},                         True),   # mailer-daemon 도메인
        ("user@gmail.com",         "WIN the LOTTERY now!", "body",   {},                         True),   # LOTTERY 키워드
        ("bridgejobkr@gmail.com",  "self",                 "body",   {},                         True),   # 자기 자신
        ("user@gmail.com",         "I would like to apply","body",   {},                         False),  # 정상 지원 메일
        ("user@gmail.com",         "apply teaching position","a " * 5, {
            "authentication-results": "dkim=fail"
        }, True),   # DKIM fail
    ]
    # (from, subj, body, headers, expected_spam)
    for from_a, subj, body, hdrs, expected in spam_cases:
        result = is_spam(from_a, subj, body, hdrs, "bridgejobkr@gmail.com")
        ok = result == expected
        print(f"  {'OK' if ok else 'FAIL'} from={from_a!r} subj={subj!r} expected={expected} got={result}")
        if not ok:
            errors += 1

    # 신규 지원자 패턴 테스트
    print("\n[2] 신규 지원자 패턴 테스트")
    appl_cases = [
        ("I would like to apply for a teaching position", "Hello", True),
        ("Hello", "I found your resume on craigslist, I have a cv", True),
        ("Re: Invoice", "Please find the invoice attached.", False),
        ("apply", "one keyword only", False),
        ("Teaching Position at our school", "I am looking for a job opening", True),
    ]
    for subj, body, expected in appl_cases:
        result = is_applicant(subj, body)
        ok = result == expected
        print(f"  {'OK' if ok else 'FAIL'} subj={subj!r} expected={expected} got={result}")
        if not ok:
            errors += 1

    # 기존 지원자 DB 조회 테스트 (mock: 없는 이메일)
    print("\n[3] 기존 지원자 중복 체크 테스트")
    result = lookup_candidate("nonexistent_test_12345@example.com")
    ok = result is None
    print(f"  {'OK' if ok else 'FAIL'} 없는 이메일 조회 → {result}")
    if not ok:
        errors += 1

    # 답장 초안 생성
    print("\n[4] 답장 초안 생성 테스트")
    subj, body, html = build_reply("John", "I want to apply", cfg["form_url"])
    ok = "tinyurl.com/bridgekr" in body and "Hello," in body and subj.startswith("Re:") and "<a href=" in html
    print(f"  {'OK' if ok else 'FAIL'} 초안 생성 (tinyurl 포함: {'tinyurl.com/bridgekr' in body}, HTML링크: {'<a href=' in html})")
    if not ok:
        errors += 1

    # 설정 검증
    print("\n[5] 설정 검증")
    missing = []
    if not cfg["gmail_addr"]:
        missing.append("GMAIL_ADDRESS")
    if not cfg["gmail_pass"]:
        missing.append("GMAIL_APP_PASSWORD")
    if not cfg["tg_token"]:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not cfg["tg_chat_id"]:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        print(f"  WARN 누락 설정: {', '.join(missing)}")
    else:
        print(f"  OK  Gmail: {cfg['gmail_addr']}, TG chat: {cfg['tg_chat_id']}, AUTO_MODE: {cfg['auto_mode']}")

    print("\n" + "=" * 60)
    if errors:
        print(f"FAIL: {errors}개 테스트 실패")
        sys.exit(1)
    else:
        print("PASS: 모든 테스트 통과")
    print("=" * 60 + "\n")


# ── 엔트리포인트 ──────────────────────────────────────────────────────────────
def main() -> None:
    args = sys.argv[1:]
    cfg = load_config()

    if "--test" in args:
        run_tests(cfg)
        return

    if not cfg["gmail_pass"]:
        log.error("[CONFIG] GMAIL_APP_PASSWORD 없음 — 종료")
        sys.exit(1)
    if not cfg["tg_token"]:
        log.warning("[CONFIG] TELEGRAM_BOT_TOKEN 없음 — 텔레그램 알림 비활성")

    log.info(f"[START] 이메일 자동응답 시작 | gmail={cfg['gmail_addr']} | auto_mode={cfg['auto_mode']}")

    # 텔레그램 커맨드 폴링 스레드
    stop_ev = threading.Event()
    tg_thread = threading.Thread(
        target=_tg_command_loop, args=(cfg, stop_ev), daemon=True, name="tg-poll"
    )
    tg_thread.start()

    once = "--once" in args

    try:
        while True:
            log.info("[LOOP] inbox 폴링 시작")
            try:
                process_inbox(cfg)
            except Exception as e:
                log.error(f"[LOOP] 예외: {e}", exc_info=True)

            if once:
                break

            log.info(f"[LOOP] {POLL_INTERVAL}초 대기 후 재실행")
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        log.info("[STOP] KeyboardInterrupt — 종료")
    finally:
        stop_ev.set()


if __name__ == "__main__":
    main()
