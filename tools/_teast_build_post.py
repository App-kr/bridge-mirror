"""Teast 포스팅 내용 생성 + 실제 포스팅 스크립트

데이터 소스 (LOCKED 2026-04-20):
- ad_only.loader 만 사용. master.db.jobs 직접 접근 금지 (PII 유출 방지).
- 원본 갱신: python ad_only/sync_from_source.py
"""
import sys, sqlite3, os, time, imaplib, email, re
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

# ad_only 패키지를 import 가능하게 project root 를 sys.path 에 추가
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ad_only.loader import (
    select_jobs as _ad_select_jobs,
    is_future_start as _ad_is_future_start,
)
from ad_only.pii_guard import assert_clean, PIIContaminationError

load_dotenv(Path(__file__).parent.parent / ".env")

# DB_PATH 는 ad_posts 기록 전용 (잡 데이터 읽기 금지)
DB_PATH = Path(__file__).parent.parent / "master.db"
TOOLS_DIR = Path(__file__).parent
SHOTS_DIR = TOOLS_DIR / "logs" / "screenshots"
SHOTS_DIR.mkdir(parents=True, exist_ok=True)

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_PASS = os.environ.get("GMAIL_APP_PASSWORD", "")

# ── 현재 월 기준 미래 월 필터 ────────────────────────────────────────────────
NOW_MONTH = datetime.now().month  # 3 = March

MONTH_NAMES = {
    1:"January", 2:"February", 3:"March", 4:"April",
    5:"May", 6:"June", 7:"July", 8:"August",
    9:"September", 10:"October", 11:"November", 12:"December"
}
FUTURE_MONTH_KEYS = [MONTH_NAMES[m].lower() for m in range(NOW_MONTH+1, 13)]
FUTURE_MONTH_KEYS += ["asap", "year-round", "year round", "flexible"]


def is_future_start(sd: str) -> bool:
    if not sd:
        return False
    sl = sd.lower()
    # 현재 월만 있고 미래 월 없으면 False
    cur_month_name = MONTH_NAMES[NOW_MONTH].lower()
    has_future = any(m in sl for m in FUTURE_MONTH_KEYS)
    has_only_current = cur_month_name in sl and not has_future
    return has_future and not has_only_current


def clean_start_date(sd: str) -> str:
    """현재 월 제거, 미래 월만 유지. 불필요한 특수문자 정리."""
    if not sd:
        return "ASAP"
    cur = MONTH_NAMES[NOW_MONTH]
    # "March, June" → "June"  /  "March - December" → "December"
    cleaned = re.sub(rf'\b{cur}\b', '', sd, flags=re.IGNORECASE)
    # 앞뒤 쓰레기 제거: "- December" → "December"
    cleaned = re.sub(r'^[\s,\-/]+|[\s,\-/]+$', '', cleaned).strip()
    # 연속 공백 정리
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # "/" → ", " 정리
    cleaned = cleaned.replace("/", ", ").strip(", ")
    # 이어붙은 단어 사이 공백 삽입 (예: "hiringASAP" → "hiring ASAP")
    cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
    # "year-round hiring" 류는 ASAP으로 단순화
    if re.search(r'year.?round|year round', cleaned, re.IGNORECASE):
        cleaned = "ASAP"
    return cleaned if cleaned else "ASAP"


DIVIDER = "_" * 52

INTRO_TEXT = """BRIDGE places qualified teachers in reputable schools, academies, English villages, and companies nationwide.

1. Eligibility
Native English speakers from US, Canada, UK, Ireland, Australia, New Zealand, South Africa.
F-visa holders with a degree from an English-speaking country are also welcome.
Overseas teachers who have completed all required documents are welcome.
A cheerful, responsible teacher who values reliability and shows genuine passion for education.

2. Required Documents
Updated résumé (CV) reflecting your latest experience.
Cover letter that genuinely represents who you are as a teacher.
Recent, bright photo with a clear front-facing smile.
1-3 minute self-introduction video (no download links).
``SOUTH AFRICANS MUST CURRENTLY RESIDE IN SOUTH KOREA (There are far too many issues).
https://tinyurl.com/bridgekr
""" + DIVIDER

FOOTER_TEXT = "https://tinyurl.com/bridgekr\n" + DIVIDER


def _fmt_m(val: float) -> str:
    """2.6 → '2,60m', 3.1 → '3,10m'"""
    whole = int(val)
    frac = int(round((val - whole) * 100))
    return f"{whole},{frac:02d}m"


def format_salary(smin, smax) -> str:
    if smin and smax and abs(smin - smax) > 0.05:
        return f"{_fmt_m(smin)} - {_fmt_m(smax)} KRW"
    if smin:
        return f"{_fmt_m(smin)} KRW"
    return "Negotiable"


def select_jobs(limit: int = 8) -> list[dict]:
    """ad_only 클린 소스에서 선택. master.db 직접 접근 금지."""
    return _ad_select_jobs(
        limit=limit,
        future_only=True,
        min_salary_m=2.4,
        diverse_cities=True,
    )


def build_description(jobs: list[dict]) -> str:
    """ad_only 클린 잡 리스트로 포스팅 본문 생성 -- PII 최종 재검증 포함."""
    blocks = []
    for j in jobs:
        code = j["job_code"].replace("Job.", "Job. ")
        loc  = (j.get("location") or "Korea").strip()
        sd   = clean_start_date(j.get("start_date", ""))
        age  = j.get("teaching_age") or ""
        cls  = j.get("class_size") or ""
        wh   = j.get("working_hours") or ""
        twh  = j.get("teach_hrs_week") or ""
        sal  = (j.get("monthly_salary") or "Negotiable").strip()
        vac  = j.get("vacation") or ""
        house = j.get("housing") or ""
        nat  = j.get("native_count") or ""
        ben  = (j.get("benefits") or "").strip()

        block = [loc, code]
        block.append(f"`Starting Date: {sd}")
        if age:
            block.append(f"`Teaching Age : {age}")
        if cls:
            block.append(f"`Class size : {cls}")
        if wh:
            block.append(f"`Working Hours : {wh}")
        block.append(f"``Monthly Salary : {sal}")
        if vac:
            block.append(f"`Vacation : {vac}")
        if house:
            block.append(f"`Housing: {house}")
        if twh:
            block.append(f"`Average Teaching Hours per Week : {twh}")
        if nat:
            block.append(f"`Native Teacher (Numbers can change) : {nat}")
        if ben:
            block.append(f"`Employee Benefits : {ben}")
        block.append(DIVIDER)
        blocks.append("\n".join(block))

    jobs_text = "\n".join(blocks)
    full_body = f"{INTRO_TEXT}\n{jobs_text}\n{FOOTER_TEXT}"

    # Fail-closed: 최종 본문에서 PII 1건이라도 감지되면 포스팅 전체 중단
    try:
        assert_clean(full_body, context='teast_build_description', strict_brand=True)
    except PIIContaminationError as e:
        # URL 감지는 INTRO/FOOTER 의 tinyurl 때문이므로 해당 예외만 허용
        err_msg = str(e)
        if 'URL' in err_msg and 'tinyurl.com/bridgekr' in full_body:
            # URL 제거 후 재검증
            stripped = full_body.replace('https://tinyurl.com/bridgekr', '')
            assert_clean(stripped, context='teast_build_description/stripped', strict_brand=True)
        else:
            raise
    return full_body


def get_magic_link() -> str:
    """Gmail에서 Teast 매직 링크 가져오기."""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("[Gmail]/&yATMtLz0rQDVaA-", readonly=True)
        _, ids = mail.search(None, "UNSEEN")
        for mid in reversed(ids[0].split()[-30:]):
            _, data = mail.fetch(mid, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            if "teast" not in msg.get("From", "").lower():
                continue
            subj = msg.get("Subject", "").lower()
            if not any(k in subj for k in ["sign in", "login", "magic"]):
                continue
            for part in ([msg] if not msg.is_multipart() else list(msg.walk())):
                raw = part.get_payload(decode=True)
                if not raw:
                    continue
                txt = raw.decode(part.get_content_charset() or "utf-8", errors="replace")
                m = re.search(r"href='([^']+)'", txt)
                if m:
                    mail.logout()
                    return m.group(1)
        mail.logout()
    except Exception as e:
        print(f"Gmail error: {e}")
    return ""


def do_login_and_post(description: str, draft: bool = True):
    import pickle
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    CHROME_BINARY = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    COOKIE_FILE   = TOOLS_DIR / ".teast_cookies.pkl"

    opts = uc.ChromeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")

    driver = uc.Chrome(
        options=opts,
        browser_executable_path=CHROME_BINARY if os.path.exists(CHROME_BINARY) else None
    )
    wait = WebDriverWait(driver, 20)

    def js_set(el, val):
        """React 관리 input/textarea 값 설정."""
        tag = el.tag_name.lower()
        if tag == "textarea":
            proto = "window.HTMLTextAreaElement.prototype"
        else:
            proto = "window.HTMLInputElement.prototype"
        driver.execute_script(f"""
            var setter = Object.getOwnPropertyDescriptor({proto}, 'value').set;
            setter.call(arguments[0], arguments[1]);
            arguments[0].dispatchEvent(new Event('input', {{bubbles: true}}));
            arguments[0].dispatchEvent(new Event('change', {{bubbles: true}}));
        """, el, val)

    def _is_logged_in():
        return "teast.co" in driver.current_url and "login" not in driver.current_url.lower()

    def _save_cookies():
        cookies = driver.get_cookies()
        with open(COOKIE_FILE, "wb") as f:
            pickle.dump(cookies, f)
        print(f"✓ 쿠키 저장 완료 ({len(cookies)}개) → {COOKIE_FILE}")

    def _load_cookies():
        if not COOKIE_FILE.exists():
            return False
        driver.get("https://teast.co")
        time.sleep(2)
        with open(COOKIE_FILE, "rb") as f:
            cookies = pickle.load(f)
        for c in cookies:
            try:
                driver.add_cookie(c)
            except Exception:
                pass
        print(f"쿠키 로드 완료 ({len(cookies)}개)")
        return True

    try:
        # ── 1단계: 쿠키로 세션 복원 시도 ────────────────────────────────────
        if COOKIE_FILE.exists():
            print("저장된 세션 쿠키 로드 중...")
            _load_cookies()
            driver.get("https://teast.co/en/job/post")
            time.sleep(4)
            print(f"URL: {driver.current_url}")

        # ── 2단계: 로그인 필요 시 Google 로그인 ─────────────────────────────
        if not COOKIE_FILE.exists() or "login" in driver.current_url.lower():
            print("로그인 필요 -- Chrome 창에서 Google 계정으로 직접 로그인해주세요 (최대 5분)")
            driver.get("https://teast.co/en/login")
            time.sleep(3)
            driver.save_screenshot(str(SHOTS_DIR / "teast_login_open.png"))

            logged_in = False
            for i in range(150):
                time.sleep(2)
                if _is_logged_in():
                    logged_in = True
                    print(f"✓ 로그인 완료 ({(i+1)*2}초 후)")
                    break
                if i % 15 == 0:
                    print(f"  ... 대기 중 ({(i+1)*2}초) -- Chrome 창에서 Google 계정 선택하세요")

            if not logged_in:
                print("❌ 로그인 실패 (5분 초과)")
                driver.save_screenshot(str(SHOTS_DIR / "teast_login_fail.png"))
                return

            _save_cookies()
            driver.get("https://teast.co/en/job/post")
            time.sleep(4)

        print(f"Post Job 페이지: {driver.current_url}")

        # ── 폼 필드 탐색 ─────────────────────────────────────────────────────
        # 현재 날짜 기준 타이틀
        latest_month = MONTH_NAMES[min(NOW_MONTH + 6, 12)]
        post_title = f"Official BRIDGE Korea ESL Teaching Jobs ASAP-{latest_month} 2026"

        inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type=hidden])")
        textareas = driver.find_elements(By.TAG_NAME, "textarea")
        print(f"Inputs: {len(inputs)}, Textareas: {len(textareas)}")

        # Job Title (첫 번째 보이는 text input)
        title_filled = False
        for inp in inputs:
            placeholder = (inp.get_attribute("placeholder") or "").lower()
            if inp.is_displayed() and inp.is_enabled():
                if not title_filled and ("title" in placeholder or not placeholder):
                    js_set(inp, post_title)
                    title_filled = True
                    print(f"Title 입력: {post_title[:50]}")
                    break

        # 스크린샷: 폼 초기 상태
        driver.save_screenshot(str(SHOTS_DIR / "teast_form_start.png"))

        # Job Description textarea (가장 큰 textarea)
        desc_filled = False
        for ta in textareas:
            if ta.is_displayed() and ta.is_enabled():
                # description textarea는 placeholder에 "description" 포함 가능
                ph = (ta.get_attribute("placeholder") or "").lower()
                js_set(ta, description)
                desc_filled = True
                print(f"Description 입력 완료 ({len(description)} chars)")
                break

        time.sleep(2)
        driver.save_screenshot(str(SHOTS_DIR / "teast_form_filled.png"))

        if draft:
            print("★ DRAFT MODE -- 폼 입력 완료, Chrome 열어둠 (점검 후 닫아주세요)")
            print(f"스크린샷: {SHOTS_DIR / 'teast_form_filled.png'}")
            # Chrome 창 유지 -- driver.quit() 호출 안 함
            try:
                while True:
                    time.sleep(5)
                    _ = driver.current_url  # 창 닫히면 예외 발생 → 루프 종료
            except Exception:
                pass
            return

        # ── 실제 제출 ────────────────────────────────────────────────────────
        # Submit 버튼 찾기
        submit_keywords = ["post job", "submit", "publish", "post"]
        submitted = False
        btns = driver.find_elements(By.TAG_NAME, "button")
        for b in btns:
            if b.is_displayed() and any(k in b.text.lower() for k in submit_keywords):
                print(f"제출 버튼 클릭: '{b.text}'")
                b.click()
                time.sleep(5)
                submitted = True
                break

        print(f"After submit URL: {driver.current_url}")
        driver.save_screenshot(str(SHOTS_DIR / "teast_submitted.png"))
        if submitted:
            print("✅ 포스팅 제출 완료")
        else:
            print("⚠ 제출 버튼 미발견")

    finally:
        time.sleep(3)
        driver.quit()


# ── 실행 (CLI 전용 -- import 시 자동실행 금지) ────────────────────────────────
def _cli_main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--show", action="store_true", help="포스팅 내용만 출력")
    args = ap.parse_args()

    jobs = select_jobs(8)
    print(f"\n선택된 잡 {len(jobs)}개:")
    for j in jobs:
        print(f"  {j['job_code']} | {j['location']} | {j['start_date']}")

    description = build_description(jobs)

    if args.show:
        print("\n─── 포스팅 내용 미리보기 ───\n")
        print(description)
    else:
        print("\n포스팅 시작...")
        do_login_and_post(description, draft=not args.live)


if __name__ == "__main__":
    _cli_main()
