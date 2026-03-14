"""
agent_ad_poster.py — Bridge Base: 구인광고 자동화 에이전트

동작 흐름
---------
1. master.db → 오늘 아직 포스팅되지 않은 Job 데이터 조회 (최대 MAX_POSTS건)
2. 각 Job에 대해 Obsidian 템플릿 형식으로 제목/본문 생성
3. Selenium으로 Craigslist 로그인 → 포스팅 폼 작성
4. ★ DRAFT_MODE = True (기본값) → Preview 단계에서 반드시 중지 (실제 전송 없음)
5. 스크린샷 저장 → master.db ad_posts 테이블에 'draft' 상태로 기록

안전장치
---------
  * DRAFT_MODE = True 이면 최종 Submit 버튼을 절대 클릭하지 않는다.
  * Submit 버튼이 감지되면 스크린샷 후 브라우저를 닫는다.
  * .env 에 CRAIGSLIST_EMAIL / CRAIGSLIST_PASSWORD 미설정 시 즉시 종료.

실행
----
  python agent_ad_poster.py              # draft 모드 (기본)
  python agent_ad_poster.py --live       # ★ 실제 전송 (신중히 사용)
  python agent_ad_poster.py --headless   # 헤드리스 모드 (화면 없음)
  python agent_ad_poster.py --limit 3   # 최대 3건만 처리

의존성
------
  pip install selenium webdriver-manager python-dotenv
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
import traceback
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
TOOLS_DIR    = Path(__file__).parent
PROJECT_DIR  = TOOLS_DIR.parent          # Q:\Claudework\bridge base
LOGS_DIR     = TOOLS_DIR / "logs"
SHOTS_DIR    = TOOLS_DIR / "logs" / "screenshots"
DB_PATH      = PROJECT_DIR / "master.db"  # 프로젝트 루트 master.db

LOGS_DIR.mkdir(exist_ok=True)
SHOTS_DIR.mkdir(exist_ok=True)

LOG_FILE = LOGS_DIR / "ad_poster.log"

load_dotenv(dotenv_path=PROJECT_DIR / ".env")  # 프로젝트 루트 .env

# ── 환경 변수 ──────────────────────────────────────────────────────────────────
CL_EMAIL    = os.environ.get("CRAIGSLIST_EMAIL",    "").strip()
CL_PASSWORD = os.environ.get("CRAIGSLIST_PASSWORD", "").strip()
CL_CITY     = os.environ.get("CRAIGSLIST_CITY",     "seoul").strip()   # 기본: 서울

# Craigslist URL
CL_LOGIN_URL = "https://accounts.craigslist.org/login"
CL_POST_URL  = f"https://post.craigslist.org/"

# ── 상수 ───────────────────────────────────────────────────────────────────────
MAX_POSTS  = 5          # 1회 실행에 처리할 최대 건수
WAIT_SHORT = 5          # 짧은 대기 (초)
WAIT_LONG  = 15         # 긴 대기 (초)
PLATFORM   = "craigslist"

NOW_ISO = datetime.now(timezone.utc).isoformat()
TODAY   = date.today().isoformat()         # e.g. "2026-02-21"

# ── 로그 유틸 ─────────────────────────────────────────────────────────────────

class Logger:
    """파일 + stdout 동시 출력."""
    def __init__(self, path: Path):
        self._f = open(path, "a", encoding="utf-8", buffering=1)
        self._ts()

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def info(self, msg: str):
        line = f"[{self._ts()}] ℹ  {msg}"
        print(line); self._f.write(line + "\n")

    def ok(self, msg: str):
        line = f"[{self._ts()}] ✅ {msg}"
        print(line); self._f.write(line + "\n")

    def warn(self, msg: str):
        line = f"[{self._ts()}] ⚠  {msg}"
        print(line); self._f.write(line + "\n")

    def error(self, msg: str):
        line = f"[{self._ts()}] ❌ {msg}"
        print(line); self._f.write(line + "\n")

    def divider(self):
        line = "─" * 55
        print(line); self._f.write(line + "\n")

    def close(self):
        self._f.close()


# ── DB 초기화 ─────────────────────────────────────────────────────────────────

DDL_AD_POSTS = """
CREATE TABLE IF NOT EXISTS ad_posts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_code        TEXT    NOT NULL,
    seq             INTEGER NOT NULL DEFAULT 1,
    platform        TEXT    NOT NULL DEFAULT 'craigslist',
    status          TEXT    NOT NULL DEFAULT 'draft',
    ad_title        TEXT,
    ad_body         TEXT,
    draft_at        TEXT,
    posted_at       TEXT,
    screenshot_path TEXT,
    error_msg       TEXT,
    UNIQUE(job_code, seq, platform)
)
"""

def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(DDL_AD_POSTS)
    conn.commit()


def fetch_unposted_jobs(conn: sqlite3.Connection, limit: int) -> list[dict]:
    """오늘 날짜에 아직 포스팅되지 않은(혹은 실패한) 최신 Job 조회."""
    sql = """
        SELECT j.id, j.job_code, j.seq, j.location, j.city, j.district,
               j.start_date, j.teaching_age, j.class_size, j.working_hours,
               j.daily_hours, j.salary_min, j.salary_max, j.salary_raw,
               j.teach_hrs_week, j.vacation, j.housing,
               j.native_count, j.benefits, j.is_part_time
        FROM jobs j
        LEFT JOIN ad_posts ap
               ON j.job_code = ap.job_code
              AND j.seq       = ap.seq
              AND ap.platform = ?
              AND ap.status   = 'posted'
              AND DATE(ap.posted_at) = DATE('now','localtime')
        WHERE ap.id IS NULL          -- 오늘 게시 이력 없음
          AND j.salary_min IS NOT NULL
          AND j.is_part_time = 0
        ORDER BY j.id DESC
        LIMIT ?
    """
    rows = conn.execute(sql, (PLATFORM, limit)).fetchall()
    cols = [d[0] for d in conn.execute(sql, (PLATFORM, 0)).description
            ] if False else [
        "id","job_code","seq","location","city","district",
        "start_date","teaching_age","class_size","working_hours",
        "daily_hours","salary_min","salary_max","salary_raw",
        "teach_hrs_week","vacation","housing",
        "native_count","benefits","is_part_time",
    ]
    return [dict(zip(cols, r)) for r in rows]


# ── 광고 텍스트 생성 ───────────────────────────────────────────────────────────

def _salary_str(row: dict) -> str:
    smin, smax = row.get("salary_min"), row.get("salary_max")
    if smin and smax and abs(smin - smax) > 0.01:
        return f"{smin:.2f}m ~ {smax:.2f}m KRW"
    if smin:
        return f"{smin:.2f}m KRW"
    return row.get("salary_raw", "Negotiable")

def build_ad(row: dict) -> tuple[str, str]:
    """
    (title, body) 반환.
    Obsidian 마크다운 Craigslist Ad 섹션과 동일한 포맷.
    """
    code   = row["job_code"]
    loc    = row.get("location") or f"{row.get('city','')} {row.get('district','')}".strip()
    sd     = row.get("start_date") or "ASAP"
    age    = row.get("teaching_age") or ""
    cls    = row.get("class_size") or ""
    wh     = row.get("working_hours") or ""
    dh     = row.get("daily_hours")
    sal    = _salary_str(row)
    vac    = row.get("vacation") or "Negotiable"
    house  = row.get("housing") or ""
    ben    = row.get("benefits") or ""
    nat    = row.get("native_count") or ""

    wh_disp = f"{wh} ({dh:.1f}h/day)" if dh else wh

    title = f"[{code}] Native English Teacher — {loc} | {sal} | {sd}"

    body = f"""English Teaching Position in {loc}

We are currently seeking a qualified Native English Teacher.

POSITION DETAILS
----------------
• Reference Code : {code}
• Location       : {loc}
• Start Date     : {sd}
• Teaching Age   : {age}
• Class Size     : {cls}
• Working Hours  : {wh_disp}
• Monthly Salary : {sal}
• Vacation       : {vac}
• Housing        : {house}
• Native Teachers: {nat}

BENEFITS
--------
{ben}

REQUIREMENTS
------------
• Native English speaker: USA, UK, Canada, Australia, NZ, South Africa, or Ireland
• Bachelor's degree or higher (any field)
• TEFL/TESOL/CELTA certification preferred
• Clean criminal background check required

HOW TO APPLY
------------
Send your CV, photo, and cover letter to:
  bridge.recruiting@email.com

Reference Code: {code}

---
Posted by Bridge Recruiting Agency | Korea ESL Specialists
"""
    return title.strip(), body.strip()


# ── Selenium 드라이버 초기화 ───────────────────────────────────────────────────

CHROME_BINARY      = r"D:\Google\ProgramFiles\Chrome\Application\chrome.exe"
# RPA 전용 프로필 — 메인 Chrome과 충돌 없음 / 최초 1회 수동 로그인 후 세션 유지
CHROME_RPA_PROFILE = str(TOOLS_DIR / ".chrome_rpa_profile")

def make_driver(headless: bool) -> uc.Chrome:
    """
    undetected_chromedriver 사용 → Craigslist 봇 감지 우회.
    RPA 전용 프로필로 세션 쿠키 유지.
    """
    opts = uc.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    # RPA 전용 프로필 사용 (세션 쿠키 유지 → 로그인 유지)
    os.makedirs(CHROME_RPA_PROFILE, exist_ok=True)
    opts.add_argument(f"--user-data-dir={CHROME_RPA_PROFILE}")

    driver = uc.Chrome(
        options=opts,
        browser_executable_path=CHROME_BINARY if os.path.exists(CHROME_BINARY) else None,
    )
    return driver


def wait_for(driver, by, selector, timeout=WAIT_LONG):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )

def click(driver, by, selector, timeout=WAIT_SHORT):
    el = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, selector))
    )
    el.click()
    return el

def fill(driver, by, selector, text: str, timeout=WAIT_SHORT, clear=True):
    el = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, selector))
    )
    if clear:
        el.clear()
    el.send_keys(text)
    return el


# ── Craigslist 로그인 ──────────────────────────────────────────────────────────

def craigslist_login(driver: webdriver.Chrome, log: Logger) -> bool:
    """
    Craigslist 계정 로그인.
    성공 시 True, 실패 시 False.
    """
    log.info(f"로그인 페이지 접속: {CL_LOGIN_URL}")
    driver.get(CL_LOGIN_URL)
    time.sleep(2)

    try:
        fill(driver, By.ID, "inputEmailHandle", CL_EMAIL)
        fill(driver, By.ID, "inputPassword",    CL_PASSWORD)
        click(driver, By.ID, "login")
        time.sleep(5)  # 로그인 처리 대기 (5초)

        cur_url = driver.current_url.lower()
        log.info(f"로그인 후 URL: {driver.current_url[:80]}")

        # 성공 판정 1: URL에 'login' 없음
        if "login" not in cur_url:
            log.ok("Craigslist 로그인 성공 (URL 변경 확인)")
            return True

        # 성공 판정 2: 계정 메뉴 존재
        try:
            driver.find_element(By.PARTIAL_LINK_TEXT, "account")
            log.ok("Craigslist 로그인 성공 (account 링크 확인)")
            return True
        except NoSuchElementException:
            pass

        # 실패 — 스크린샷 저장해서 원인 파악
        shot = str(SHOTS_DIR / f"login_fail_{datetime.now().strftime('%H%M%S')}.png")
        driver.save_screenshot(shot)
        page_text = driver.find_element(By.TAG_NAME, "body").text[:300]
        log.error(f"로그인 실패. 스크린샷: {shot}")
        log.error(f"페이지 내용 일부: {page_text}")
        return False

    except (NoSuchElementException, TimeoutException) as exc:
        log.error(f"로그인 오류: {exc}")
        return False


# ── Craigslist 포스팅 플로우 ───────────────────────────────────────────────────

class DraftSafetyStop(Exception):
    """DRAFT_MODE에서 Submit 직전에 발생시켜 전송을 차단하는 예외."""
    pass


def craigslist_post(
    driver: webdriver.Chrome,
    title:  str,
    body:   str,
    log:    Logger,
    draft_mode: bool,
    job_code:   str,
) -> str:
    """
    Craigslist 포스팅 폼 작성.
    draft_mode=True → Preview 화면에서 중지, 스크린샷 경로 반환.
    draft_mode=False → 실제 게시 진행.
    """
    log.info(f"포스팅 페이지 접속: {CL_POST_URL}")
    driver.get(CL_POST_URL)
    time.sleep(2)

    # ── Step 1: 포스팅 타입 선택 → "job offered" ──────────────────────────────
    try:
        # Craigslist: "I want to post a job" or radio "jo"
        offered = driver.find_element(By.CSS_SELECTOR, "input[value='jo']")  # job offered
        offered.click()
        log.info("포스팅 타입 선택: Job Offered")
    except NoSuchElementException:
        try:
            driver.find_element(By.PARTIAL_LINK_TEXT, "job offered").click()
        except NoSuchElementException:
            log.warn("포스팅 타입 자동 선택 불가 — 수동 확인 필요")

    # Continue 버튼 클릭
    try:
        click(driver, By.CSS_SELECTOR, "button.continue, input[value='continue'], "
              "button[type='submit']", timeout=WAIT_SHORT)
        time.sleep(1.5)
    except TimeoutException:
        pass

    # ── Step 2: 카테고리 선택 → Education / Teaching ──────────────────────────
    try:
        driver.find_element(By.PARTIAL_LINK_TEXT, "education").click()
        log.info("카테고리: education/teaching 선택")
        time.sleep(1)
    except NoSuchElementException:
        try:
            driver.find_element(By.PARTIAL_LINK_TEXT, "teach").click()
        except NoSuchElementException:
            log.warn("카테고리 자동 선택 불가")

    # ── Step 3: 지역 선택 ─────────────────────────────────────────────────────
    try:
        area_links = driver.find_elements(By.CSS_SELECTOR, "a[data-value]")
        for lnk in area_links:
            if CL_CITY.lower() in lnk.text.lower():
                lnk.click()
                log.info(f"지역 선택: {lnk.text}")
                time.sleep(1)
                break
    except Exception:
        log.warn("지역 자동 선택 불가 — 기본값 유지")

    # ── Step 4: 포스팅 상세 폼 입력 ──────────────────────────────────────────
    log.info("제목 / 본문 입력 중...")

    # 제목
    title_selectors = ["#PostingTitle", "input[name='PostingTitle']",
                       "input[placeholder*='title' i]", "input[id*='title' i]"]
    title_filled = False
    for sel in title_selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            el.clear()
            el.send_keys(title)
            title_filled = True
            log.info(f"제목 입력 완료 ({sel})")
            break
        except NoSuchElementException:
            continue
    if not title_filled:
        log.warn("제목 입력 필드 자동 탐지 실패")

    # 본문
    body_selectors = ["#postingBody", "textarea[name='PostingBody']",
                      "textarea[id*='body' i]", "textarea[placeholder*='description' i]"]
    body_filled = False
    for sel in body_selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            el.clear()
            el.send_keys(body)
            body_filled = True
            log.info(f"본문 입력 완료 ({sel})")
            break
        except NoSuchElementException:
            continue
    if not body_filled:
        log.warn("본문 입력 필드 자동 탐지 실패")

    time.sleep(1)

    # ── Step 5: 이메일 검증 / 지역 상세 입력 (있으면) ────────────────────────
    try:
        email_field = driver.find_element(By.CSS_SELECTOR,
                                          "input[name='FromEMail'], input[type='email']")
        if not email_field.get_attribute("value"):
            email_field.send_keys(CL_EMAIL)
            log.info("이메일 입력 완료")
    except NoSuchElementException:
        pass

    # ── Step 6: Continue → Preview ────────────────────────────────────────────
    continue_selectors = [
        "button.continue", "input.continue",
        "button[type='submit']", "input[type='submit']",
        "button[value='continue']",
    ]
    log.info("Continue 버튼 클릭 → Preview 페이지로 이동...")
    for sel in continue_selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            btn_text = btn.text or btn.get_attribute("value") or ""
            if "publish" in btn_text.lower() or "submit" in btn_text.lower():
                # 이미 최종 Submit 버튼이 보임 → DRAFT_MODE에서는 중지
                if draft_mode:
                    raise DraftSafetyStop("Submit 버튼 감지 — DRAFT_MODE로 인해 전송 차단")
            btn.click()
            time.sleep(3)
            break
        except (NoSuchElementException, ElementNotInteractableException):
            continue

    # ── Step 7: 현재 상태 확인 ────────────────────────────────────────────────
    page_src = driver.page_source.lower()

    # Preview 화면 진입 확인
    on_preview = any(kw in page_src for kw in
                     ["preview", "review your post", "check your posting"])

    # Submit 버튼이 있는지 검사
    submit_els = driver.find_elements(
        By.XPATH,
        "//button[contains(translate(.,'SUBMIT','submit'),'submit')] | "
        "//input[@type='submit' and contains("
        "translate(@value,'SUBMIT','submit'),'submit')]"
    )

    if submit_els and draft_mode:
        raise DraftSafetyStop(
            "Preview/Submit 버튼 감지 — DRAFT_MODE: 전송 차단, 스크린샷 저장"
        )

    if on_preview:
        log.info("Preview 화면 진입 확인")

    # ── Step 8: 스크린샷 저장 ─────────────────────────────────────────────────
    shot_name = f"{job_code}_draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    shot_path = str(SHOTS_DIR / shot_name)
    driver.save_screenshot(shot_path)
    log.ok(f"스크린샷 저장: {shot_name}")

    if draft_mode:
        log.warn("★ DRAFT_MODE — 최종 전송 없이 Draft 상태로 저장됩니다.")

    return shot_path


# ── DB 기록 ───────────────────────────────────────────────────────────────────

def record_draft(conn: sqlite3.Connection, row: dict, title: str, body: str,
                 shot_path: str, status: str = "draft", err: str = "") -> None:
    conn.execute("""
        INSERT INTO ad_posts
            (job_code, seq, platform, status, ad_title, ad_body,
             draft_at, screenshot_path, error_msg)
        VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(job_code, seq, platform) DO UPDATE SET
            status=excluded.status,
            ad_title=excluded.ad_title,
            ad_body=excluded.ad_body,
            draft_at=excluded.draft_at,
            screenshot_path=excluded.screenshot_path,
            error_msg=excluded.error_msg
    """, (
        row["job_code"], row.get("seq", 1), PLATFORM,
        status, title, body, NOW_ISO, shot_path, err,
    ))
    conn.commit()


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Bridge Ad Poster Agent")
    ap.add_argument("--live",     action="store_true",
                    help="실제 게시 모드 (기본: Draft 모드)")
    ap.add_argument("--headless", action="store_true",
                    help="헤드리스 브라우저 (화면 없이 실행)")
    ap.add_argument("--limit",    type=int, default=MAX_POSTS,
                    help=f"최대 처리 건수 (기본: {MAX_POSTS})")
    args = ap.parse_args()

    DRAFT_MODE = not args.live
    log = Logger(LOG_FILE)

    log.divider()
    log.info(f"Ad Poster Agent 시작  ({TODAY})")
    log.info(f"모드: {'★ LIVE (실제전송)' if not DRAFT_MODE else 'DRAFT (안전모드)'}")
    log.info(f"최대 처리 건수: {args.limit}")
    log.divider()

    # ── 자격증명 검사 ─────────────────────────────────────────────────────────
    if not CL_EMAIL or not CL_PASSWORD:
        log.error(".env 에 CRAIGSLIST_EMAIL / CRAIGSLIST_PASSWORD 가 설정되지 않았습니다.")
        log.warn("→ .env 파일에 다음 항목을 추가하세요:")
        log.warn("    CRAIGSLIST_EMAIL=your@email.com")
        log.warn("    CRAIGSLIST_PASSWORD=yourpassword")
        log.info("")
        log.info("[DEMO 모드] 자격증명 없이 광고 텍스트 생성 미리보기를 실행합니다.")

        # 자격증명 없어도 DB 조회 + 텍스트 생성은 시연
        conn = sqlite3.connect(DB_PATH)
        init_db(conn)
        jobs = fetch_unposted_jobs(conn, args.limit)
        log.info(f"미포스팅 Job: {len(jobs)}건 조회됨")
        for row in jobs[:3]:
            t, b = build_ad(row)
            log.info(f"  [{row['job_code']}] 제목: {t[:60]}…")
            log.info(f"  본문 미리보기 ({len(b)}자):")
            for line in b.splitlines()[:6]:
                log.info(f"    {line}")
            log.info("")
        conn.close()
        log.warn("실제 게시를 위해 .env에 Craigslist 자격증명을 추가 후 재실행하세요.")
        log.divider()
        return

    # ── DB 연결 ───────────────────────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    jobs = fetch_unposted_jobs(conn, args.limit)
    log.info(f"오늘 미포스팅 Job: {len(jobs)}건")

    if not jobs:
        log.ok("오늘 포스팅할 새 Job이 없습니다. 종료합니다.")
        conn.close()
        log.divider()
        return

    # ── 드라이버 초기화 ───────────────────────────────────────────────────────
    log.info("Chrome 드라이버 초기화 중...")
    try:
        driver = make_driver(headless=args.headless)
    except WebDriverException as exc:
        log.error(f"드라이버 초기화 실패: {exc}")
        conn.close()
        return

    try:
        # ── 로그인 ────────────────────────────────────────────────────────────
        logged_in = craigslist_login(driver, log)
        if not logged_in:
            log.error("로그인 실패 — 자격증명 확인 후 재시도하세요.")
            driver.quit()
            conn.close()
            return

        # ── Job 순회 포스팅 ──────────────────────────────────────────────────
        success = error = 0
        for row in jobs:
            log.divider()
            log.info(f"처리 중: {row['job_code']} (seq={row.get('seq',1)}) "
                     f"— {row.get('location','')}")

            title, body = build_ad(row)
            shot_path = ""

            try:
                shot_path = craigslist_post(
                    driver, title, body, log,
                    draft_mode=DRAFT_MODE,
                    job_code=row["job_code"],
                )
                status = "draft" if DRAFT_MODE else "posted"
                record_draft(conn, row, title, body, shot_path, status=status)
                log.ok(f"{row['job_code']} → {status} 상태로 저장 완료")
                success += 1

            except DraftSafetyStop as dss:
                log.warn(str(dss))
                if driver:
                    shot_name = (f"{row['job_code']}_safestop_"
                                 f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    shot_path = str(SHOTS_DIR / shot_name)
                    driver.save_screenshot(shot_path)
                record_draft(conn, row, title, body, shot_path,
                             status="draft", err="DraftSafetyStop")
                success += 1   # Draft 저장 성공으로 집계

            except Exception as exc:
                err_msg = traceback.format_exc()
                log.error(f"포스팅 오류: {exc}")
                record_draft(conn, row, title, body, shot_path,
                             status="error", err=str(exc)[:500])
                error += 1

            # 게시 간격 (서버 부하 방지)
            if row != jobs[-1]:
                log.info("다음 게시 전 대기 (5초)…")
                time.sleep(5)

    finally:
        driver.quit()
        conn.close()

    log.divider()
    log.ok(f"완료 — 성공: {success}건  오류: {error}건")
    if DRAFT_MODE:
        log.warn("★ DRAFT 모드로 실행됨 — 실제 게시된 광고 없음")
        log.warn("  실제 게시: python agent_ad_poster.py --live")
    log.divider()


if __name__ == "__main__":
    main()
