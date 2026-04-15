"""
teast_repost.py — Teast 구인공고 월간 자동 재게시 에이전트

동작:
1. Gmail IMAP → "Your Job Post Has Expired" 이메일 검색
2. HTML 본문에서 repost 링크 추출
3. Selenium → Teast 로그인 → repost URL 접속 → 완료

실행:
  python teast_repost.py              # draft 모드 (스크린샷만, 실제 게시 없음)
  python teast_repost.py --live       # 실제 재게시
  python teast_repost.py --days 30    # 최근 30일 이메일 검색 (기본: 45일)
  python teast_repost.py --force      # 이번 달 이미 게시됐어도 강제 실행

.env 필수:
  GMAIL_USER=bridgejobkr@gmail.com
  GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
  TEAST_EMAIL=your_teast_login_email
  TEAST_PASSWORD=your_teast_password
"""

from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── 감사(Audit) 모듈 ──────────────────────────────────────────────────
_AUDIT_BASE = r"Q:\Claudework"
if _AUDIT_BASE not in sys.path:
    sys.path.insert(0, _AUDIT_BASE)
try:
    from rpa_audit import AuditSession
    _AUDIT_OK = True
except ImportError:
    _AUDIT_OK = False

import argparse
import email
import imaplib
import os
import re
import sqlite3
import time
import traceback
from datetime import date, datetime, timedelta, timezone
from email.header import decode_header
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
TOOLS_DIR   = Path(__file__).parent
PROJECT_DIR = TOOLS_DIR.parent
LOGS_DIR    = TOOLS_DIR / "logs"
SHOTS_DIR   = LOGS_DIR / "screenshots"
DB_PATH     = PROJECT_DIR / "master.db"

LOGS_DIR.mkdir(exist_ok=True)
SHOTS_DIR.mkdir(exist_ok=True)

LOG_FILE = LOGS_DIR / "teast_repost.log"

load_dotenv(dotenv_path=PROJECT_DIR / ".env")

# ── 환경 변수 ──────────────────────────────────────────────────────────────────
GMAIL_USER     = os.environ.get("GMAIL_USER", "").strip()
GMAIL_PASS     = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
TEAST_EMAIL    = os.environ.get("TEAST_EMAIL", "").strip()
TEAST_PASSWORD = os.environ.get("TEAST_PASSWORD", "").strip()

IMAP_HOST      = "imap.gmail.com"
TARGET_SUBJECT = "Your Job Post Has Expired"

CHROME_BINARY      = r"D:\Google\ProgramFiles\Chrome\Application\chrome.exe"
CHROME_RPA_PROFILE = str(TOOLS_DIR / ".chrome_rpa_profile")

WAIT_SHORT = 5
WAIT_LONG  = 15


# ── 로거 ─────────────────────────────────────────────────────────────────────
class Logger:
    def __init__(self, path: Path):
        self._f = open(path, "a", encoding="utf-8", buffering=1)
        header = (f"\n{'='*55}\n"
                  f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Teast Repost Agent 시작\n"
                  f"{'='*55}")
        print(header)
        self._f.write(header + "\n")

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def info(self, msg: str):  self._out("ℹ ", msg)
    def ok(self, msg: str):    self._out("✅", msg)
    def warn(self, msg: str):  self._out("⚠ ", msg)
    def error(self, msg: str): self._out("❌", msg)

    def _out(self, pfx: str, msg: str):
        line = f"[{self._ts()}] {pfx} {msg}"
        print(line)
        self._f.write(line + "\n")

    def divider(self):
        line = "─" * 55
        print(line)
        self._f.write(line + "\n")

    def close(self):
        self._f.close()


# ── DB 초기화 ─────────────────────────────────────────────────────────────────
DDL_TEAST_POSTS = """
CREATE TABLE IF NOT EXISTS teast_posts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    posted_at    TEXT    NOT NULL,
    repost_url   TEXT,
    status       TEXT    NOT NULL DEFAULT 'draft',
    screenshot   TEXT,
    email_date   TEXT,
    error_msg    TEXT
)
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(DDL_TEAST_POSTS)
    conn.commit()


def get_last_posted(conn: sqlite3.Connection) -> Optional[str]:
    """가장 최근 성공 게시 날짜 반환."""
    row = conn.execute(
        "SELECT posted_at FROM teast_posts WHERE status='posted' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else None


def record_post(conn: sqlite3.Connection, repost_url: str, status: str,
                screenshot: str, email_date: str, err: str = "") -> None:
    conn.execute(
        """INSERT INTO teast_posts
               (posted_at, repost_url, status, screenshot, email_date, error_msg)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (datetime.now(timezone.utc).isoformat(), repost_url, status,
         screenshot, email_date, err)
    )
    conn.commit()


# ── Gmail IMAP: 만료 이메일 검색 ──────────────────────────────────────────────

def _decode_header_str(val: str) -> str:
    """RFC2047 인코딩 헤더 디코드."""
    parts = decode_header(val)
    result = []
    for b, charset in parts:
        if isinstance(b, bytes):
            result.append(b.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(b)
    return "".join(result)


class _LinkExtractor(HTMLParser):
    """HTML 본문에서 <a href> 링크 + 텍스트 쌍 추출."""

    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._cur_href: str = ""
        self._cur_text: str = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_d = dict(attrs)
            self._cur_href = attrs_d.get("href", "")
            self._cur_text = ""

    def handle_endtag(self, tag):
        if tag == "a" and self._cur_href:
            self.links.append((self._cur_href, self._cur_text.strip()))
            self._cur_href = ""
            self._cur_text = ""

    def handle_data(self, data):
        if self._cur_href:
            self._cur_text += data


def _extract_repost_url(html_body: str, plain_body: str) -> Optional[str]:
    """
    이메일 본문에서 repost URL 추출.

    전략:
    1. raw HTML에서 "repost" 키워드 뒤 첫 번째 <a href> 추출 (가장 정확)
    2. HTML 파싱: 링크 텍스트에 repost 관련 키워드
    3. fallback: URL 패턴에 repost 키워드
    """
    # html_body 가 없으면 plain_body(실제로 HTML인 경우) 사용
    body = html_body or plain_body

    # ── 전략 1: "repost" 텍스트 뒤 href 직접 추출 (raw HTML) ──────────────────
    # 패턴: "repost" 이후 50자 내 <a href="...">
    m = re.search(
        r'repost[^<]{0,80}<a\s+[^>]*href=["\']([^"\']+)["\']',
        body, re.IGNORECASE
    )
    if m:
        return m.group(1)

    # ── 전략 2: HTML 파싱 → 링크 텍스트 기반 ─────────────────────────────────
    parser = _LinkExtractor()
    try:
        parser.feed(body)
    except Exception:
        pass

    repost_keywords = ["repost", "re-post", "over here"]
    for href, text in parser.links:
        if any(kw in text.lower() for kw in repost_keywords):
            return href

    # ── 전략 3: URL 자체에 repost 패턴 ───────────────────────────────────────
    urls = re.findall(r'https?://[^\s<>"\']+', body)
    for url in urls:
        if any(kw in url.lower() for kw in ["repost", "re-post"]):
            return url

    return None


def find_expired_email(days: int, log: Logger) -> Optional[dict]:
    """
    Gmail IMAP에서 최근 days일 이내
    'Your Job Post Has Expired' 이메일 검색.
    가장 최근 것 반환: {date, subject, repost_url, plain_body}
    """
    if not GMAIL_USER or not GMAIL_PASS:
        log.error("GMAIL_USER / GMAIL_APP_PASSWORD 환경변수 미설정")
        return None

    try:
        log.info(f"Gmail IMAP 연결: {GMAIL_USER}")
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")

        since_str = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        # SUBJECT 검색 (Teast 발신 이메일)
        _, msg_ids_raw = mail.search(
            None, f'(SUBJECT "{TARGET_SUBJECT}" SINCE {since_str})'
        )
        msg_ids = msg_ids_raw[0].split() if msg_ids_raw[0] else []

        if not msg_ids:
            log.warn(f"최근 {days}일 내 만료 이메일 없음 (제목: '{TARGET_SUBJECT}')")
            mail.logout()
            return None

        log.info(f"{len(msg_ids)}개 만료 이메일 발견 — 가장 최근 것 사용")
        latest_id = msg_ids[-1]

        _, msg_data = mail.fetch(latest_id, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        mail.logout()

        subject  = _decode_header_str(msg.get("Subject", ""))
        date_str = msg.get("Date", "")
        log.info(f"이메일 날짜: {date_str}")
        log.info(f"제목: {subject}")

        # 본문 추출
        html_body = ""
        plain_body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == "text/html":
                    charset = part.get_content_charset() or "utf-8"
                    html_body = part.get_payload(decode=True).decode(
                        charset, errors="replace"
                    )
                elif ct == "text/plain" and not plain_body:
                    charset = part.get_content_charset() or "utf-8"
                    plain_body = part.get_payload(decode=True).decode(
                        charset, errors="replace"
                    )
        else:
            charset = msg.get_content_charset() or "utf-8"
            content = msg.get_payload(decode=True).decode(charset, errors="replace")
            # 단일 파트: content-type에 따라 적절한 변수에 할당
            if msg.get_content_type() == "text/html":
                html_body = content
            else:
                plain_body = content

        repost_url = _extract_repost_url(html_body, plain_body)
        if repost_url:
            log.ok(f"Repost URL 추출 성공: {repost_url[:80]}")
        else:
            log.warn("Repost URL 자동 추출 실패 — 이메일 본문 확인 필요")
            log.info("본문 미리보기:")
            for line in plain_body[:500].splitlines():
                log.info(f"  {line}")

        return {
            "date":        date_str,
            "subject":     subject,
            "repost_url":  repost_url,
            "plain_body":  plain_body[:2000],
        }

    except imaplib.IMAP4.error as e:
        log.error(f"Gmail IMAP 오류: {e}")
        return None
    except Exception as e:
        log.error(f"이메일 검색 오류: {e}")
        return None


# ── Selenium: Teast 재게시 ────────────────────────────────────────────────────

def _make_driver(headless: bool) -> uc.Chrome:
    """undetected_chromedriver 생성 (기존 RPA 프로필 재사용)."""
    opts = uc.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    os.makedirs(CHROME_RPA_PROFILE, exist_ok=True)
    opts.add_argument(f"--user-data-dir={CHROME_RPA_PROFILE}")

    return uc.Chrome(
        options=opts,
        browser_executable_path=(
            CHROME_BINARY if os.path.exists(CHROME_BINARY) else None
        ),
    )


def _teast_login_if_needed(driver, log: Logger) -> bool:
    """현재 페이지가 로그인 화면이면 TEAST_EMAIL/PASSWORD 로 로그인."""
    cur = driver.current_url.lower()
    if "login" not in cur and "signin" not in cur:
        return True  # 이미 로그인 상태

    if not TEAST_EMAIL or not TEAST_PASSWORD:
        log.warn("TEAST_EMAIL/TEAST_PASSWORD 미설정 — Chrome 세션 쿠키로 진행")
        return True

    log.info("로그인 페이지 감지 — 자동 로그인 시도")
    selectors = [
        'input[type="email"]',
        'input[name="email"]',
        'input[type="text"]',
    ]
    for sel in selectors:
        try:
            email_el = driver.find_element(By.CSS_SELECTOR, sel)
            email_el.clear()
            email_el.send_keys(TEAST_EMAIL)
            pw_el = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
            pw_el.clear()
            pw_el.send_keys(TEAST_PASSWORD)
            submit = driver.find_element(
                By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]'
            )
            submit.click()
            time.sleep(3)
            log.ok("로그인 완료")
            return True
        except NoSuchElementException:
            continue

    log.warn("로그인 폼 자동 감지 실패 — 기존 세션으로 진행")
    return True


def do_teast_repost(driver, repost_url: str, draft_mode: bool,
                    log: Logger) -> str:
    """
    Teast repost URL 접속 → 확인/제출 버튼 클릭 → 완료.
    draft_mode=True: 스크린샷만 저장, 최종 제출 안 함.
    반환: 최종 스크린샷 경로
    """
    log.info(f"Repost URL 접속 중...")
    driver.get(repost_url)
    time.sleep(3)

    # 로그인 리다이렉트 처리
    _teast_login_if_needed(driver, log)
    time.sleep(2)

    # 로그인 후 repost URL 재접속 (로그인이 필요했던 경우)
    if repost_url not in driver.current_url:
        driver.get(repost_url)
        time.sleep(3)

    # 현재 페이지 스크린샷
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shot = str(SHOTS_DIR / f"teast_repost_{ts}.png")
    driver.save_screenshot(shot)
    log.ok(f"스크린샷 저장: teast_repost_{ts}.png")

    if draft_mode:
        log.warn("★ DRAFT MODE — 실제 게시 없음")
        log.warn("  실제 게시: python teast_repost.py --live")
        return shot

    # ── 실제 모드: Confirm/Repost 버튼 클릭 ──────────────────────────────────
    confirm_keywords = ["repost", "confirm", "submit", "post", "publish", "게시", "재게시"]

    clicked = False
    # 버튼/링크 후보 탐색
    candidates = driver.find_elements(
        By.CSS_SELECTOR,
        "button, input[type='submit'], a[href]"
    )
    for el in candidates:
        el_text = (el.text or el.get_attribute("value") or "").lower().strip()
        el_href = (el.get_attribute("href") or "").lower()
        if any(kw in el_text for kw in confirm_keywords):
            try:
                el.click()
                time.sleep(3)
                log.ok(f"확인 버튼 클릭: '{el_text[:40]}'")
                clicked = True
                break
            except Exception:
                continue
        if not clicked and any(kw in el_href for kw in ["repost", "confirm"]):
            try:
                el.click()
                time.sleep(3)
                log.ok(f"확인 링크 클릭: {el_href[:60]}")
                clicked = True
                break
            except Exception:
                continue

    if not clicked:
        log.warn("확인 버튼 자동 감지 실패 — 수동 확인 필요")
        log.info(f"현재 URL: {driver.current_url}")

    # 완료 스크린샷
    ts2 = datetime.now().strftime("%Y%m%d_%H%M%S")
    shot_done = str(SHOTS_DIR / f"teast_done_{ts2}.png")
    driver.save_screenshot(shot_done)
    log.ok(f"완료 스크린샷: teast_done_{ts2}.png")

    return shot_done


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Teast 구인공고 자동 재게시")
    ap.add_argument("--live",     action="store_true",
                    help="실제 재게시 모드 (기본: Draft — 스크린샷만)")
    ap.add_argument("--headless", action="store_true",
                    help="헤드리스 Chrome (화면 없이 실행)")
    ap.add_argument("--days",     type=int, default=45,
                    help="이메일 검색 범위 일수 (기본: 45일)")
    ap.add_argument("--force",    action="store_true",
                    help="이번 달 이미 게시됐어도 강제 실행")
    args = ap.parse_args()

    DRAFT_MODE = not args.live
    log = Logger(LOG_FILE)

    log.info(f"모드: {'★ LIVE (실제 게시)' if not DRAFT_MODE else 'DRAFT (안전 모드)'}")
    log.info(f"이메일 검색: 최근 {args.days}일")
    log.divider()

    # ── DB 초기화 ─────────────────────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    # ── 이번 달 이미 게시 여부 확인 ───────────────────────────────────────────
    if not args.force:
        last = get_last_posted(conn)
        if last:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if last_dt.year == now.year and last_dt.month == now.month:
                log.ok(f"이번 달 이미 게시 완료: {last[:10]} — 종료 (--force 로 강제 실행)")
                conn.close()
                log.close()
                return

    # ── Gmail에서 만료 이메일 찾기 ────────────────────────────────────────────
    log.info("Gmail에서 만료 이메일 검색 중...")
    email_info = find_expired_email(args.days, log)

    if not email_info:
        log.error("만료 이메일 없음 — 종료")
        conn.close()
        log.close()
        return

    repost_url = email_info.get("repost_url")
    if not repost_url:
        log.error("Repost URL 추출 실패 — 이메일 본문을 수동 확인하세요")
        conn.close()
        log.close()
        return

    log.divider()
    log.info("Chrome 드라이버 초기화 중...")

    # ── Selenium 실행 ─────────────────────────────────────────────────────────
    driver = None
    shot_path = ""
    status    = "error"
    err_msg   = ""

    try:
        driver = _make_driver(headless=args.headless)
        shot_path = do_teast_repost(driver, repost_url, DRAFT_MODE, log)
        status = "draft" if DRAFT_MODE else "posted"

    except WebDriverException as e:
        err_msg = f"드라이버 오류: {e}"
        log.error(err_msg)
    except Exception as e:
        err_msg = str(e)[:500]
        log.error(f"재게시 오류: {e}")
        traceback.print_exc()
        if driver:
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                shot_path = str(SHOTS_DIR / f"teast_error_{ts}.png")
                driver.save_screenshot(shot_path)
            except Exception:
                pass
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # ── DB 기록 ───────────────────────────────────────────────────────────────
    record_post(conn, repost_url, status, shot_path, email_info["date"], err_msg)
    conn.close()

    # ── 결과 출력 ─────────────────────────────────────────────────────────────
    log.divider()
    if status == "posted":
        log.ok("Teast 재게시 완료 ✅")
    elif status == "draft":
        log.warn("Draft 저장 완료 — 실제 게시하려면: python teast_repost.py --live")
    else:
        log.error(f"재게시 실패: {err_msg}")
    log.close()


if __name__ == "__main__":
    if _AUDIT_OK:
        with AuditSession("teast_repost", sites=["teast.com", "gmail.com"]) as audit:
            audit.preflight()
            audit.step("main() 시작")
            main()
            audit.done()
    else:
        main()
