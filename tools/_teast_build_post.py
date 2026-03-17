"""Teast 포스팅 내용 생성 + 실제 포스팅 스크립트"""
import sys, sqlite3, os, time, imaplib, email, re
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

load_dotenv(Path(__file__).parent.parent / ".env")

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
1–3 minute self-introduction video (no download links).
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
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT job_code, location, city, district, start_date, teaching_age,
               class_size, working_hours, daily_hours, salary_min, salary_max,
               teach_hrs_week, vacation, housing, native_count, benefits
        FROM jobs
        WHERE is_part_time=0 AND is_deleted=0
          AND salary_min>=2.4
          AND location<>'' AND teaching_age IS NOT NULL
          AND working_hours IS NOT NULL
        ORDER BY id DESC LIMIT 300
    """).fetchall()
    conn.close()

    candidates = [dict(r) for r in rows if is_future_start(r["start_date"])]

    # 지역 다양성 확보
    seen = set()
    selected = []
    for j in candidates:
        loc_key = (j["city"] or j["location"] or "").split()[0].lower()
        if loc_key and loc_key not in seen:
            seen.add(loc_key)
            selected.append(j)
        if len(selected) >= limit:
            break
    return selected


def build_description(jobs: list[dict]) -> str:
    blocks = []
    for j in jobs:
        code = j["job_code"].replace("Job.", "Job. ")
        loc  = (j["location"] or j["city"] or "Korea").strip()
        sd   = clean_start_date(j["start_date"])
        age  = j["teaching_age"] or ""
        cls  = j["class_size"] or ""
        wh   = j["working_hours"] or ""
        # teach_hrs_week: DB 컬럼값만 사용 (daily_hours 계산 금지)
        twh  = j["teach_hrs_week"] or ""
        sal  = format_salary(j["salary_min"], j["salary_max"])
        vac  = j["vacation"] or ""
        house = j["housing"] or ""
        nat  = j["native_count"] or ""
        ben  = (j["benefits"] or "").strip()

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
    return f"{INTRO_TEXT}\n{jobs_text}\n{FOOTER_TEXT}"


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
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    CHROME_BINARY = r"D:\Google\ProgramFiles\Chrome\Application\chrome.exe"
    CHROME_PROFILE = str(TOOLS_DIR / ".chrome_rpa_profile")

    opts = uc.ChromeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    os.makedirs(CHROME_PROFILE, exist_ok=True)
    opts.add_argument(f"--user-data-dir={CHROME_PROFILE}")

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

    try:
        # ── 세션 확인 또는 로그인 ────────────────────────────────────────────
        driver.get("https://teast.co/en/job/post")
        time.sleep(4)
        print(f"URL: {driver.current_url}")

        if "login" in driver.current_url.lower():
            print("로그인 필요 — 매직 링크 요청...")
            # 이메일 입력 후 전송
            driver.get("https://teast.co/en/login")
            time.sleep(3)
            inp = driver.find_element(By.CSS_SELECTOR, "input[type=text],input[type=email]")
            inp.send_keys(GMAIL_USER)
            time.sleep(1)
            btns = driver.find_elements(By.TAG_NAME, "button")
            for b in btns:
                if b.text.strip() == "CONTINUE WITH EMAIL":
                    b.click()
                    print("매직 링크 전송 요청됨")
                    break

            # 최대 60초 대기
            magic = ""
            for _ in range(12):
                time.sleep(5)
                magic = get_magic_link()
                if magic:
                    break
            if not magic:
                print("❌ 매직 링크 미수신")
                return
            driver.get(magic)
            time.sleep(5)
            print(f"로그인 후 URL: {driver.current_url}")
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
            print("★ DRAFT MODE — 실제 제출 안 함")
            print(f"스크린샷: {SHOTS_DIR / 'teast_form_filled.png'}")
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


# ── 실행 ─────────────────────────────────────────────────────────────────────
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
