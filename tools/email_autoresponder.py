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
POLL_INTERVAL  = 300  # 5분

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
    auto_mode  = os.getenv("EMAIL_AUTO_MODE", "false").lower() == "true"

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
            "parse_mode": "HTML",
        }).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
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
_SPAM_SUBJECT_KW = [
    "unsubscribe", "newsletter", "promotion", "offer", "discount",
    "make money", "crypto", "investment", "casino", "lottery", "winner",
    "click here", "limited time", "act now", "free gift",
]


def is_spam(from_addr: str, subject: str, body: str, headers: dict,
            self_addr: str) -> bool:
    # 자기 자신
    if from_addr.lower() == self_addr.lower():
        return True
    # 발신 도메인 체크
    domain_local = from_addr.split("@")[0].lower() if "@" in from_addr else from_addr.lower()
    if any(sp in domain_local for sp in _SPAM_DOMAINS):
        return True
    if "@" in from_addr:
        domain = from_addr.split("@")[1].lower()
        if any(sp in domain for sp in _SPAM_DOMAINS):
            return True
    # 제목 키워드
    subj_low = subject.lower()
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
    "craigslist", "teast", "koreabridge", "eslcafe",
    "resume", "cv", "curriculum vitae",
    "interested in", "opening", "reaching out",
    "cover letter", "looking forward", "full-time",
    "part-time", "position", "job posting", "vacancy",
]


def is_applicant(subject: str, body: str) -> bool:
    """제목+본문 합쳐서 키워드 2개 이상 포함 시 True."""
    text = (subject + " " + body).lower()
    matched = sum(1 for kw in _APPLICANT_KW if kw in text)
    return matched >= 2


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


# ── 답장 초안 생성 ───────────────────────────────────────────────────────────
def build_reply(first_name: str, orig_subject: str, form_url: str) -> tuple[str, str]:
    subject = f"Re: {orig_subject}"
    body = f"""Hello {first_name},

Thank you for reaching out to BRIDGE Agency.

We have received your inquiry. To get started, please complete our quick registration form (approx. 2-5 mins):

{form_url}

Please ensure the following are included:
- CV (Workplace Name, Location, Dates in YY/MM format)
- Cover Letter & Photo taken within 1 year
- Scanned Apostilled Documents
- Short Video Intro (1-3 mins)

Once reviewed, we will reach out to schedule a brief 5-minute Google Meet.

Kind regards,
BRIDGE Agency
www.bridgejob.co.kr"""
    return subject, body


# ── SMTP 발송 ─────────────────────────────────────────────────────────────────
def send_reply(cfg: dict, to_addr: str, to_name: str,
               subject: str, body: str, retries: int = 3) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"BRIDGE Agency <{cfg['gmail_addr']}>"
    msg["To"]      = f"{to_name} <{to_addr}>" if to_name else to_addr
    msg.attach(MIMEText(body, "plain", "utf-8"))

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
            m = imaplib.IMAP4_SSL("imap.gmail.com", 993)
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

            try:
                _, msg_data = imap.fetch(uid_b, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                subject     = _decode_header(msg.get("Subject", "(no subject)"))
                from_raw    = _decode_header(msg.get("From", ""))
                from_name, from_addr = email.utils.parseaddr(from_raw)
                from_addr   = from_addr.lower().strip()
                received_at = msg.get("Date", "")
                body        = _get_body(msg)
                headers     = _get_headers(msg)

                # ── STEP A: 스팸 필터 ────────────────────────────────────────
                if is_spam(from_addr, subject, body, headers, cfg["gmail_addr"]):
                    log.info(f"[SPAM] {from_addr} | {subject}")
                    processed.add(uid)
                    _save_processed(processed)
                    continue

                # ── STEP B: 기존 지원자 중복 체크 ───────────────────────────
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
                    processed.add(uid)
                    _save_processed(processed)
                    continue

                # ── STEP C: 신규 지원자 패턴 감지 ───────────────────────────
                if not is_applicant(subject, body):
                    log.info(f"[UNKNOWN] 패턴 미해당 → 보류: {from_addr} | {subject}")
                    log_email(from_addr, from_name, subject, received_at,
                              None, "UNKNOWN", "SKIPPED", uid)
                    processed.add(uid)
                    _save_pending({**_load_pending()})  # 변경 없음, 읽음 처리 안 함
                    _save_processed(processed)
                    continue

                # ── STEP D: 초안 생성 및 발송 처리 ─────────────────────────
                first_name = (from_name.split()[0] if from_name else "there")
                subj, body_reply = build_reply(first_name, subject, cfg["form_url"])

                if cfg["auto_mode"]:
                    # 즉시 자동 발송
                    ok = send_reply(cfg, from_addr, from_name, subj, body_reply)
                    status_val = "SENT" if ok else "FAILED"
                    sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if ok else None

                    if ok:
                        tg_send(cfg["tg_token"], cfg["tg_chat_id"],
                                f"✅ 자동발송 완료\n👤 {from_name} &lt;{from_addr}&gt;")
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
                    pending[uid] = {
                        "from_addr":   from_addr,
                        "from_name":   from_name,
                        "subject":     subject,
                        "received_at": received_at,
                        "reply_subj":  subj,
                        "reply_body":  body_reply,
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
                                        item["reply_subj"], item["reply_body"])
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
    subj, body = build_reply("John", "I want to apply", cfg["form_url"])
    ok = "John" in body and cfg["form_url"] in body and subj.startswith("Re:")
    print(f"  {'OK' if ok else 'FAIL'} 초안 생성 (form_url 포함: {cfg['form_url'] in body})")
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
