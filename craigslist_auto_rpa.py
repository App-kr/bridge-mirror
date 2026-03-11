# -*- coding: utf-8 -*-
import os
import json
import sys

# ── python.exe → pythonw.exe 자동 재시작 (CMD 창 완전 제거) ──────────
if sys.executable.lower().endswith("python.exe") and "--no-relaunch" not in sys.argv:
    import subprocess as _sp
    _pw = sys.executable[:-10] + "pythonw.exe"
    _sp.Popen(
        [_pw, os.path.abspath(__file__), "--no-relaunch"] + sys.argv[1:],
        creationflags=_sp.CREATE_NO_WINDOW | _sp.DETACHED_PROCESS,
    )
    sys.exit(0)

import time
import random
import threading
import subprocess
import pandas as pd
import schedule
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image, ImageDraw, ImageFont

# ── [경로 설정] ───────────────────────────────────────────────────────
BASE_DIR          = Path(r"Q:\Claudework\bridge base")
JOBS_DIR          = BASE_DIR / "original_jobs"
MASTER_FILE       = JOBS_DIR / "JOBS_MASTER_COMBINED.xlsx"
TEMP_IMAGE_PATH   = BASE_DIR / "temp_bridge_logo.jpg"
ACCOUNT_LOG_PATH  = BASE_DIR / "account_usage.json"
OVERLAY_STATE     = BASE_DIR / "overlay_state.json"
OVERLAY_STOP_FLAG = BASE_DIR / "overlay_stop.flag"

# ── [계정 목록] ───────────────────────────────────────────────────────
ACCOUNTS = [
    {"email": "bridgejobkr@gmail.com", "profile": "CraigslistBridge"},
    # {"email": "bridgejobkr2@gmail.com", "profile": "CraigslistBridge2"},
]

# ── [지역명 한→영] ────────────────────────────────────────────────────
CITY_MAP = {
    "서울": "Seoul", "부산": "Busan", "대구": "Daegu", "인천": "Incheon",
    "광주": "Gwangju", "대전": "Daejeon", "울산": "Ulsan", "세종": "Sejong",
    "수원": "Suwon", "성남": "Seongnam", "전주": "Jeonju", "청주": "Cheongju",
    "제주": "Jeju", "안양": "Anyang", "안산": "Ansan", "고양": "Goyang",
    "용인": "Yongin", "의정부": "Uijeongbu", "춘천": "Chuncheon",
    "원주": "Wonju", "천안": "Cheonan", "아산": "Asan", "여수": "Yeosu",
    "창원": "Changwon", "진주": "Jinju", "포항": "Pohang", "경주": "Gyeongju",
    "구미": "Gumi", "강릉": "Gangneung", "속초": "Sokcho",
    "강남": "Seoul Gangnam", "서초": "Seoul Seocho", "마포": "Seoul Mapo",
    "구로": "Seoul Guro", "송파": "Seoul Songpa", "노원": "Seoul Nowon",
    "은평": "Seoul Eunpyeong", "중구": "Seoul Junggu",
}
AGE_MAP = {
    "유치원": "Kindy", "킨더": "Kindy", "kindy": "Kindy",
    "초등": "Elem", "elementary": "Elem",
    "중등": "Middle", "중학": "Middle",
    "고등": "High", "고교": "High",
    "성인": "Adult", "어른": "Adult",
}


def parse_city(raw: str) -> str:
    raw = str(raw)
    for kor, eng in CITY_MAP.items():
        if kor in raw:
            return eng
    return raw.split()[0] if raw.split() else "Korea"


def parse_age(raw: str) -> str:
    raw = str(raw).lower()
    res = []
    for kor, eng in AGE_MAP.items():
        if kor.lower() in raw and eng not in res:
            res.append(eng)
    return " / ".join(res) if res else "Various"


def clean(val) -> str:
    return "" if pd.isna(val) or str(val).strip() in ("nan", "NaN", "") else str(val).strip()


# ── [오버레이 통신 함수] ──────────────────────────────────────────────
def _ov_write(state: dict):
    try:
        OVERLAY_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _ov_launch(account: str, count: int):
    """오버레이 프로세스를 DETACHED로 독립 실행"""
    OVERLAY_STOP_FLAG.unlink(missing_ok=True)
    _ov_write({
        "status": "running",
        "account": account,
        "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": count,
        "done": 0,
        "success": 0,
        "current": "준비 중...",
        "logs": [],
        "updated": datetime.now().isoformat(),
    })
    pythonw = sys.executable if sys.executable.lower().endswith("pythonw.exe") \
              else sys.executable[:-10] + "pythonw.exe"
    overlay_script = BASE_DIR / "rpa_overlay.py"
    if overlay_script.exists():
        subprocess.Popen(
            [pythonw, str(overlay_script), "--account", account, "--total", str(count)],
            creationflags=(
                subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.CREATE_NO_WINDOW
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )


def _ov_update(done: int, total: int, success: int, current: str, log_msg: str):
    """게시 진행 상태 갱신"""
    try:
        state = json.loads(OVERLAY_STATE.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    logs = state.get("logs", [])
    logs.append(f"{datetime.now().strftime('%H:%M:%S')}  {log_msg}")
    logs = logs[-50:]  # 최대 50줄 유지
    state.update({
        "status": "running",
        "done": done,
        "success": success,
        "current": current,
        "logs": logs,
        "updated": datetime.now().isoformat(),
    })
    _ov_write(state)


def _ov_done(success: int, total: int):
    """게시 완료 상태 기록"""
    try:
        state = json.loads(OVERLAY_STATE.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    logs = state.get("logs", [])
    logs.append(f"{datetime.now().strftime('%H:%M:%S')}  ── 완료: {success}/{total}건 성공 ──")
    state.update({
        "status": "done",
        "done": total,
        "success": success,
        "current": f"완료 ({success}/{total}건 성공)",
        "logs": logs,
        "updated": datetime.now().isoformat(),
    })
    _ov_write(state)


def _ov_stop_requested() -> bool:
    """overlay_stop.flag 존재 여부 확인"""
    return OVERLAY_STOP_FLAG.exists()


# ── [포스팅 데이터 생성] ──────────────────────────────────────────────
class SecurityOrchestrator:

    @staticmethod
    def shift_date(date_str: str) -> str:
        s = str(date_str)
        if any(m in s for m in ["Feb", "Mar", "2월", "3월", "2.", "3."]):
            return f"End of {random.choice(['April','May','June','July','August'])}"
        return date_str if date_str else "ASAP"

    @classmethod
    def generate_payload(cls, row) -> dict:
        loc_raw  = clean(row.get("근무처 소재지 Location(시,구,캠퍼스명 등)", "")) or \
                   clean(row.get("근무처소재지", "")) or "Seoul"
        city     = parse_city(loc_raw)
        job_id   = clean(row.get("직업번호", "")) or "N/A"
        date_raw = clean(row.get("희망 시작일 Starting date", "")) or \
                   clean(row.get("희망시작일", "")) or "ASAP"
        date     = cls.shift_date(date_raw)
        age_raw  = clean(row.get("강의대상 Teaching Age group", "")) or \
                   clean(row.get("수업대상", "")) or ""
        age      = parse_age(age_raw) if age_raw else "Various"
        hours    = clean(row.get("근로계약시간 Working hour \n예시: 09:00~17:00 / 개인 점심시간 1시간 포함", "")) or \
                   clean(row.get("근무일정", "")) or "TBD"
        salary   = clean(row.get("월 급여조건 Salary", "")) or \
                   clean(row.get("급여조건", "")) or "Negotiable"
        avg_hrs  = clean(row.get("주당 평균 강의시간 Teaching Hour in A Week", "")) or \
                   clean(row.get("평균강의", "")) or ""
        housing  = clean(row.get("기숙사 Housing or housing allowance", "")) or \
                   clean(row.get("숙소제공", "")) or "Not provided"
        vacation = clean(row.get("휴가일수 Paid Vacations. 기본 11일기준. (ex. 주말 포함 여름 5일/겨울 20일 )", "")) or \
                   clean(row.get("유급휴일", "")) or ""
        sick     = clean(row.get("보건휴가 Sick leaves", "")) or \
                   clean(row.get("보건휴가", "")) or ""
        benefits = clean(row.get("교육기관 개별 복지 Benefits", "")) or \
                   clean(row.get("복지", "")) or ""

        title = f"◾◾◾◾{city} {age} English Teacher Position Open"
        if len(title) > 70:
            title = title[:70]

        housing_in_benefits = "provided accommodation" if (
            "제공" in housing or "provided" in housing.lower()
        ) else ""
        std_benefits = "Visa sponsorship, severance pay, pension, insurance, paid vacation"
        if housing_in_benefits:
            std_benefits += f", {housing_in_benefits}"
        if benefits:
            std_benefits += f", {benefits}"
        std_benefits += ", and airfare support."

        lines = [city, f"Job. {job_id}",
                 f"Starting Date : {date}",
                 f"Teaching Age : {age}"]
        if hours and hours != "TBD":
            lines.append(f"Working Hours : {hours}")
        lines.append(f"Monthly Salary : {salary}")
        if avg_hrs:
            lines.append(f"Average Teaching Hours per Week : {avg_hrs}")
        if vacation:
            vac_line = f"Vacation : {vacation}"
            if sick:
                vac_line += f", plus {sick} for sick leave"
            lines.append(vac_line)
        lines += [
            f"Housing: {housing}",
            f"Employee Benefits : {std_benefits}",
            "",
            "Requirements: Clean record and at least a bachelor's degree.",
            "(UK, US, CA, AUS, NZ, IR, SA or F visa holders preferred)",
            "South Africans: Only those living in Korea can apply due to paperwork issues.",
        ]
        return {"title": title, "city": city, "body": "\n".join(lines),
                "salary": salary, "id": job_id}


# ── [계정 쿨다운 매니저] ──────────────────────────────────────────────
class AccountManager:
    COOLDOWN_HOURS = 2

    def __init__(self):
        self.log_path = ACCOUNT_LOG_PATH
        self.usage = self._load()

    def _load(self):
        if self.log_path.exists():
            with open(self.log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.usage, f, indent=2)

    def _is_on_cooldown(self, email):
        last = self.usage.get(email)
        if not last:
            return False
        return datetime.now() - datetime.fromisoformat(last) < timedelta(hours=self.COOLDOWN_HOURS)

    def pick_account(self):
        available = [a for a in ACCOUNTS if not self._is_on_cooldown(a["email"])]
        if not available:
            info = {a["email"]: self.usage.get(a["email"], "never") for a in ACCOUNTS}
            raise RuntimeError(f"모든 계정이 2시간 쿨다운 중:\n{info}")
        return random.choice(available)

    def mark_used(self, email):
        self.usage[email] = datetime.now().isoformat()
        self._save()


# ── [이미지] ──────────────────────────────────────────────────────────
class ImageWorker:
    @staticmethod
    def create_logo():
        img = Image.new("RGB", (600, 400), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arialbd.ttf", 250)
        except Exception:
            font = ImageFont.load_default()
        draw.text((230, 80), "B", font=font, fill=(255, 255, 255))
        img.save(TEMP_IMAGE_PATH)


# ── [RPA 봇] ──────────────────────────────────────────────────────────
class CraigslistBot:
    def __init__(self, account):
        self.account = account
        options = webdriver.ChromeOptions()
        profile = os.path.join(
            os.environ["USERPROFILE"], "AppData", "Local", "Google", "Chrome",
            "User Data", account["profile"]
        )
        options.add_argument(f"user-data-dir={profile}")
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280,900")
        options.add_argument("--no-sandbox")
        service = Service(
            ChromeDriverManager().install(),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait   = WebDriverWait(self.driver, 25)

    def run_post(self, p) -> bool:
        ImageWorker.create_logo()
        try:
            self.driver.get("https://post.craigslist.org/c/seo")
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='jo']"))).click()
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='13']"))).click()
            self.wait.until(EC.presence_of_element_located((By.NAME, "PostingTitle"))).send_keys(p["title"])
            self.driver.find_element(By.NAME, "geographic_area").send_keys(p["city"])
            self.driver.find_element(By.NAME, "PostingBody").send_keys(p["body"])
            self.driver.find_element(By.NAME, "compensation").send_keys(p["salary"])
            self.driver.find_element(By.NAME, "company_name").send_keys("BRIDGE")
            self.driver.find_element(By.NAME, "go").click()
            f_input = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
            f_input.send_keys(str(TEMP_IMAGE_PATH.resolve()))
            time.sleep(4)
            self.driver.find_element(By.CLASS_NAME, "done").click()
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Publish')]")
            )).click()
            return True
        except Exception as e:
            return False


# ── [게시 루프 — 오버레이 통합] ───────────────────────────────────────
def run_posting(count: int = 5):
    if not MASTER_FILE.exists():
        messagebox.showerror("오류", f"엑셀 파일 없음:\n{MASTER_FILE}")
        return

    df  = pd.read_excel(MASTER_FILE, dtype=str).fillna("")
    mgr = AccountManager()
    try:
        account = mgr.pick_account()
    except RuntimeError as e:
        messagebox.showerror("계정 오류", str(e))
        return

    # 오버레이 독립 프로세스 실행
    _ov_launch(account["email"], count)
    mgr.mark_used(account["email"])
    bot = CraigslistBot(account)

    targets = random.sample(range(len(df)), min(count, len(df)))
    success = 0

    for i, idx in enumerate(targets, 1):
        # 중단 요청 확인
        if _ov_stop_requested():
            _ov_update(i - 1, count, success, "중단됨", "⛔ 사용자 중단 요청")
            break

        payload = SecurityOrchestrator.generate_payload(df.iloc[idx].to_dict())
        _ov_update(i, count, success, payload["title"], f"[{i}/{count}] 게시 중: {payload['title'][:40]}")

        ok = bot.run_post(payload)
        if ok:
            success += 1
            _ov_update(i, count, success, payload["title"], f"✅ Job.{payload['id']} 게시 완료")
        else:
            _ov_update(i, count, success, payload["title"], f"❌ Job.{payload['id']} 게시 실패")

        time.sleep(random.uniform(30, 60))

    _ov_done(success, count)


# ── [오후 4시 팝업] ───────────────────────────────────────────────────
def show_popup_and_run():
    root = tk.Tk()
    root.withdraw()
    answer = messagebox.askyesno(
        "Bridge 광고 자동화",
        "오후 4시입니다!\n크레이그리스트 광고 진행할래요?",
        icon="question",
    )
    root.destroy()
    if answer:
        threading.Thread(target=run_posting, args=(5,), daemon=True).start()


def run_schedule_loop():
    schedule.every().day.at("16:00").do(show_popup_and_run)
    while True:
        schedule.run_pending()
        time.sleep(30)


def _start_schedule(root):
    root.destroy()
    pythonw = sys.executable if sys.executable.lower().endswith("pythonw.exe") \
              else sys.executable[:-10] + "pythonw.exe"
    subprocess.Popen(
        [pythonw, os.path.abspath(__file__), "--schedule", "--no-relaunch"],
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
    )
    messagebox.showinfo("스케줄 시작", "매일 오후 4시 자동 실행 등록 완료!")


# ── [메인 메뉴] ───────────────────────────────────────────────────────
def main():
    if "--schedule" in sys.argv:
        run_schedule_loop()
        return

    root = tk.Tk()
    root.title("BRIDGE Craigslist")
    root.configure(bg="#2b2b2b")
    root.geometry("340x230")
    root.resizable(False, False)

    tk.Label(root, text="BRIDGE  Craigslist RPA",
             bg="#4a235a", fg="white",
             font=("Consolas", 13, "bold")).pack(fill="x", ipady=12)

    btn = dict(bg="#27ae60", fg="white", font=("Consolas", 11, "bold"),
               relief="flat", cursor="hand2", width=28)
    tk.Button(root, text="▶  Random 10건 즉시 게시",
              command=lambda: [root.destroy(),
                               threading.Thread(target=run_posting, args=(10,), daemon=True).start()],
              **btn).pack(pady=(18, 6))
    tk.Button(root, text="▶  Test 1건 테스트",
              command=lambda: [root.destroy(),
                               threading.Thread(target=run_posting, args=(1,), daemon=True).start()],
              **btn).pack(pady=6)

    sched = dict(bg="#7d5a3c", fg="white", font=("Consolas", 10),
                 relief="flat", cursor="hand2", width=28)
    tk.Button(root, text="⏰  매일 오후 4시 자동 실행",
              command=lambda: _start_schedule(root),
              **sched).pack(pady=6)

    root.mainloop()


if __name__ == "__main__":
    main()
