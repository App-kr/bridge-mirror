# -*- coding: utf-8 -*-
import os
import json
import sys

# ── python.exe → pythonw.exe 자동 재시작 (Job Object 완전 탈출) ──
if sys.executable.lower().endswith("python.exe") and "--no-relaunch" not in sys.argv:
    import subprocess as _sp, pathlib as _pl, uuid as _uuid, threading as _thr
    _pw = _pl.Path(sys.executable).with_name("pythonw.exe")
    if _pw.exists():
        _task = f"BridgeCrRL_{_uuid.uuid4().hex[:8]}"
        _cmd  = f'"{_pw}" "{os.path.abspath(__file__)}" --no-relaunch'
        _sp.run(['schtasks', '/create', '/f', '/tn', _task,
                 '/tr', _cmd, '/sc', 'once', '/st', '00:00'],
                creationflags=_sp.CREATE_NO_WINDOW, capture_output=True)
        _sp.run(['schtasks', '/run', '/tn', _task],
                creationflags=_sp.CREATE_NO_WINDOW, capture_output=True)
        def _del_task():
            import time as _t; _t.sleep(30)
            _sp.run(['schtasks', '/delete', '/tn', _task, '/f'],
                    creationflags=_sp.CREATE_NO_WINDOW, capture_output=True)
        _thr.Thread(target=_del_task, daemon=True).start()
        os._exit(0)

import math
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
# label = UI 표시용 (이메일 절대 노출 금지)
ACCOUNTS = [
    {"email": "bridgejobkr@gmail.com",  "profile": "CraigslistBridge",  "label": "Bridge · A"},
    {"email": "bridgejobkr2@gmail.com", "profile": "CraigslistBridge2", "label": "Bridge · B"},
    {"email": "bridgejobkr3@gmail.com", "profile": "CraigslistBridge3", "label": "Bridge · C"},
    {"email": "bridgejobkr4@gmail.com", "profile": "CraigslistBridge4", "label": "Bridge · D"},
]

def _mask_email(email: str) -> str:
    """이메일 부분 마스킹 — 운영자 식별 가능, PII 완전노출 방지 (CLAUDE.md 규칙)"""
    try:
        local, domain = email.split("@", 1)
        if len(local) <= 3:
            masked = local[0] + "*" * (len(local) - 1)
        else:
            masked = local[:2] + "*" * (len(local) - 4) + local[-2:]
        return f"{masked}@{domain}"
    except Exception:
        return "****@****"


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
    """오버레이 프로세스를 Task Scheduler 경유로 실행 — svchost 자식, Job Object 완전 탈출"""
    import uuid
    OVERLAY_STOP_FLAG.unlink(missing_ok=True)
    _now = datetime.now()
    _ov_write({
        "status": "running",
        "account": account,
        "started": _now.strftime("%Y-%m-%d %H:%M:%S"),
        "launched_at": _now.isoformat(),
        "total": count,
        "done": 0,
        "success": 0,
        "current": "준비 중...",
        "logs": [],
        "updated": _now.isoformat(),
    })
    overlay_script = BASE_DIR / "rpa_overlay.py"
    if not overlay_script.exists():
        return
    pythonw = sys.executable if sys.executable.lower().endswith("pythonw.exe") \
              else sys.executable[:-10] + "pythonw.exe"
    task_name = f"BridgeOverlay_{uuid.uuid4().hex[:8]}"
    cmd_tr = f'"{pythonw}" "{overlay_script}" --no-relaunch'
    subprocess.run(
        ['schtasks', '/create', '/f', '/tn', task_name,
         '/tr', cmd_tr, '/sc', 'once', '/st', '00:00'],
        creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True,
    )
    subprocess.run(
        ['schtasks', '/run', '/tn', task_name],
        creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True,
    )
    # 30초 후 작업 항목 자동 삭제
    def _cleanup_task():
        time.sleep(30)
        subprocess.run(
            ['schtasks', '/delete', '/tn', task_name, '/f'],
            creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True,
        )
    threading.Thread(target=_cleanup_task, daemon=True).start()


def _ov_update(done: int, total: int, success: int, current: str, log_msg: str, step: str = ""):
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
        "step": step,
        "logs": logs,
        "updated": datetime.now().isoformat(),
    })
    _ov_write(state)


def _ov_step(step_msg: str):
    """작업 단계만 갱신 (done/success 불변) — 세부 진행 상태 표시용"""
    try:
        state = json.loads(OVERLAY_STATE.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    state.update({
        "step": step_msg,
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

    def run_post(self, p, step_cb=None) -> bool:
        def _step(msg):
            if step_cb:
                step_cb(msg)

        ImageWorker.create_logo()
        try:
            _step("📂 페이지 로딩 중...")
            self.driver.get("https://post.craigslist.org/c/seo")
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='jo']"))).click()
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='13']"))).click()
            _step("✏️ 제목 작성 중...")
            self.wait.until(EC.presence_of_element_located((By.NAME, "PostingTitle"))).send_keys(p["title"])
            self.driver.find_element(By.NAME, "geographic_area").send_keys(p["city"])
            _step("📝 본문 작성 중...")
            self.driver.find_element(By.NAME, "PostingBody").send_keys(p["body"])
            self.driver.find_element(By.NAME, "compensation").send_keys(p["salary"])
            self.driver.find_element(By.NAME, "company_name").send_keys("BRIDGE")
            self.driver.find_element(By.NAME, "go").click()
            _step("🖼️ 이미지 업로드 중...")
            f_input = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
            f_input.send_keys(str(TEMP_IMAGE_PATH.resolve()))
            time.sleep(4)
            self.driver.find_element(By.CLASS_NAME, "done").click()
            _step("🚀 게시 제출 중...")
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Publish')]")
            )).click()
            _step("✅ 게시 완료!")
            return True
        except Exception:
            _step("❌ 오류 — 다음 항목으로")
            return False


# ── [게시 루프 — 오버레이 통합] ───────────────────────────────────────
def run_posting(count: int = 5, acct_idx: int = None):
    if not MASTER_FILE.exists():
        print(f"[ERROR] 엑셀 파일 없음: {MASTER_FILE}")
        return

    df  = pd.read_excel(MASTER_FILE, dtype=str).fillna("")
    mgr = AccountManager()
    try:
        if acct_idx is not None and 0 <= acct_idx < len(ACCOUNTS):
            account = ACCOUNTS[acct_idx]
        else:
            account = mgr.pick_account()
    except RuntimeError as e:
        print(f"[ERROR] 계정 오류: {e}")
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
        _ov_update(i, count, success, payload["title"],
                   f"[{i}/{count}] 게시 중: {payload['title'][:40]}", step="⏳ 작성 준비 중...")

        ok = bot.run_post(payload, step_cb=_ov_step)
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
        threading.Thread(target=run_posting, args=(5,), daemon=False).start()


def run_schedule_loop():
    schedule.every().day.at("16:00").do(show_popup_and_run)
    while True:
        schedule.run_pending()
        time.sleep(30)


def _start_schedule(root):
    root.destroy()
    pythonw = sys.executable if sys.executable.lower().endswith("pythonw.exe") \
              else sys.executable[:-10] + "pythonw.exe"
    _sc_env = os.environ.copy()
    _sc_env['_SC_EXE']  = pythonw
    _sc_env['_SC_ARGS'] = f'"{os.path.abspath(__file__)}" --schedule --no-relaunch'
    _sc_env['_SC_DIR']  = str(BASE_DIR)
    subprocess.Popen(
        ['powershell', '-NonInteractive', '-NoProfile', '-WindowStyle', 'Hidden',
         '-Command',
         '(New-Object -ComObject Shell.Application)'
         '.ShellExecute($env:_SC_EXE,$env:_SC_ARGS,$env:_SC_DIR,"open",1)'],
        creationflags=subprocess.CREATE_NO_WINDOW, env=_sc_env,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    messagebox.showinfo("스케줄 시작", "매일 오후 4시 자동 실행 등록 완료!")


# ── [메인 메뉴] ───────────────────────────────────────────────────────
def main():
    if "--schedule" in sys.argv:
        run_schedule_loop()
        return

    # ── Worker 모드: 메뉴 없이 직접 게시 실행 ────────────────────────
    if "--worker" in sys.argv:
        limit = 10
        acct_idx = None
        for arg in sys.argv:
            if arg.startswith("--limit="):
                try: limit = int(arg.split("=", 1)[1])
                except ValueError: pass
            if arg.startswith("--account-idx="):
                try: acct_idx = int(arg.split("=", 1)[1])
                except ValueError: pass
        run_posting(limit, acct_idx)
        return

    # ── Launcher 모드: Apple-style UI ────────────────────────────────
    pythonw = (sys.executable if sys.executable.lower().endswith("pythonw.exe")
               else Path(sys.executable).with_name("pythonw.exe"))

    # Apple dark palette
    BG    = "#1C1C1E"
    CARD  = "#2C2C2E"
    BLUE  = "#0A84FF"
    GREEN = "#30D158"
    RED   = "#FF453A"
    WHITE = "#FFFFFF"
    GRAY1 = "#8E8E93"
    GRAY2 = "#3A3A3C"
    FONT  = "Segoe UI"

    # 계정별 고유 색상 (1→파랑, 2→초록, 3→오렌지, 4→보라)
    ACCT_COLORS = ["#0A84FF", "#30D158", "#FF9F0A", "#BF5AF2"]

    W, H = 460, 580
    root = tk.Tk()
    root.title("BRIDGE RPA")
    root.configure(bg=BG)
    root.resizable(False, False)
    root.update_idletasks()
    sx = (root.winfo_screenwidth()  - W) // 2
    sy = (root.winfo_screenheight() - H) // 2
    root.geometry(f"{W}x{H}+{sx}+{sy}")

    acct_var = tk.IntVar(value=0)
    cnt_var  = tk.IntVar(value=10)

    PAD = 28
    main_frame = tk.Frame(root, bg=BG)
    main_frame.pack(fill="both", expand=True, padx=PAD, pady=22)

    # ── Helper: 계정 컬러 카드 그리드 ──────────────────────────────
    def make_account_cards(parent):
        card_frames = []

        def refresh():
            sel = acct_var.get()
            for idx, (outer, inner, num_lbl, tag_lbl, email_lbl) in enumerate(card_frames):
                color = ACCT_COLORS[idx]
                if sel == idx:
                    # 선택됨: 색상 배경 + 마스킹 이메일 표시
                    outer.configure(bg=color)
                    inner.configure(bg=color)
                    num_lbl.configure(bg=color, fg=WHITE)
                    tag_lbl.configure(bg=color, fg=WHITE)
                    email_lbl.configure(bg=color, fg=WHITE,
                                        text=_mask_email(ACCOUNTS[idx]["email"]))
                else:
                    # 미선택: 어두운 카드 + 왼쪽 컬러 바만
                    outer.configure(bg=color)
                    inner.configure(bg=CARD)
                    num_lbl.configure(bg=CARD, fg=GRAY1)
                    tag_lbl.configure(bg=CARD, fg=GRAY2)
                    email_lbl.configure(bg=CARD, fg=GRAY2, text="")

        def select(val):
            acct_var.set(val)
            refresh()

        grid = tk.Frame(parent, bg=BG)
        grid.pack(fill="x")
        for idx, acct in enumerate(ACCOUNTS):
            r, c = divmod(idx, 2)
            color = ACCT_COLORS[idx]
            num   = str(idx + 1)
            label = acct["label"]

            # outer = 컬러 테두리(왼쪽 4px 바 역할)
            outer = tk.Frame(grid, bg=color, padx=4, pady=0)
            outer.grid(row=r, column=c, padx=4, pady=4, sticky="ew")

            # inner = 카드 본체
            inner = tk.Frame(outer, bg=CARD, padx=10, pady=8)
            inner.pack(fill="both")

            num_lbl = tk.Label(inner, text=num, bg=CARD, fg=GRAY1,
                               font=(FONT, 20, "bold"), anchor="w")
            num_lbl.pack(fill="x")

            tag_lbl = tk.Label(inner, text=label, bg=CARD, fg=GRAY2,
                               font=(FONT, 9), anchor="w")
            tag_lbl.pack(fill="x")

            # 선택 시 마스킹 이메일 표시
            email_lbl = tk.Label(inner, text="", bg=CARD, fg=GRAY2,
                                 font=(FONT, 8), anchor="w")
            email_lbl.pack(fill="x")

            card_frames.append((outer, inner, num_lbl, tag_lbl, email_lbl))

            # 클릭 바인딩 (프레임 + 레이블 모두)
            for widget in (outer, inner, num_lbl, tag_lbl, email_lbl):
                widget.bind("<Button-1>", lambda e, v=idx: select(v))
                widget.configure(cursor="hand2")

        for col in range(2):
            grid.columnconfigure(col, weight=1)

        refresh()

    # ── Helper: pill-button grid (게시 수 선택용) ───────────────────
    def make_pill_grid(parent, items, var, cols=4):
        buttons = []

        def refresh():
            for btn, val in buttons:
                if var.get() == val:
                    btn.configure(bg=BLUE, fg=WHITE)
                else:
                    btn.configure(bg=CARD, fg=GRAY1)

        def select(val):
            var.set(val)
            refresh()

        grid = tk.Frame(parent, bg=BG)
        grid.pack(fill="x")
        for i, (lbl, val) in enumerate(items):
            r, c = divmod(i, cols)
            btn = tk.Button(
                grid, text=lbl,
                bg=CARD, fg=GRAY1,
                font=(FONT, 10), relief="flat", bd=0,
                cursor="hand2", pady=10, padx=6,
                activebackground=BLUE, activeforeground=WHITE,
                command=lambda v=val: select(v),
            )
            btn.grid(row=r, column=c, padx=4, pady=4, sticky="ew")
            buttons.append((btn, val))
        for c in range(cols):
            grid.columnconfigure(c, weight=1)
        refresh()
        return buttons, refresh

    # ── Selection screen ─────────────────────────────────────────────
    def show_selection():
        for w in main_frame.winfo_children():
            w.destroy()

        # Header
        hf = tk.Frame(main_frame, bg=BG)
        hf.pack(fill="x", pady=(0, 20))
        tk.Label(hf, text="BRIDGE", bg=BG, fg=WHITE,
                 font=(FONT, 22, "bold")).pack(side="left")
        tk.Label(hf, text="  RPA", bg=BG, fg=GRAY1,
                 font=(FONT, 22)).pack(side="left")

        # Account section — 컬러 카드
        tk.Label(main_frame, text="ACCOUNT", bg=BG, fg=GRAY1,
                 font=(FONT, 10)).pack(anchor="w", pady=(0, 6))
        make_account_cards(main_frame)

        tk.Frame(main_frame, bg=GRAY2, height=1).pack(fill="x", pady=16)

        # Count section
        tk.Label(main_frame, text="POSTS", bg=BG, fg=GRAY1,
                 font=(FONT, 10)).pack(anchor="w", pady=(0, 6))
        make_pill_grid(
            main_frame,
            [("1  (test)", 1), ("5", 5), ("10", 10), ("20", 20)],
            cnt_var, cols=4,
        )

        tk.Frame(main_frame, bg=GRAY2, height=1).pack(fill="x", pady=16)

        # Start 버튼 — 선택된 계정 색상으로
        def _start():
            color = ACCT_COLORS[acct_var.get()]
            _spawn_worker(cnt_var.get(), acct_var.get())

        start_btn = tk.Button(
            main_frame, text="▶  Start Posting",
            bg=ACCT_COLORS[acct_var.get()], fg=WHITE, font=(FONT, 13, "bold"),
            relief="flat", bd=0, cursor="hand2", pady=14,
            activeforeground=WHITE,
            command=_start,
        )
        start_btn.pack(fill="x", pady=(0, 8))

        # 계정 선택 시 버튼 색상도 갱신
        def _on_acct_change(*_):
            start_btn.configure(bg=ACCT_COLORS[acct_var.get()])
        acct_var.trace_add("write", _on_acct_change)

        tk.Button(
            main_frame, text="⏰  Schedule Daily  (4:00 PM)",
            bg=CARD, fg=GRAY1, font=(FONT, 10),
            relief="flat", bd=0, cursor="hand2", pady=10,
            activebackground=GRAY2, activeforeground=WHITE,
            command=lambda: _start_schedule(root),
        ).pack(fill="x")

    # ── Working screen ───────────────────────────────────────────────
    _anim_id = [None]
    _poll_id = [None]

    def show_working(acct_label: str, total: int, acct_idx: int = 0):
        acct_color = ACCT_COLORS[acct_idx] if 0 <= acct_idx < len(ACCT_COLORS) else BLUE
        if _anim_id[0]:
            root.after_cancel(_anim_id[0])
        if _poll_id[0]:
            root.after_cancel(_poll_id[0])
        for w in main_frame.winfo_children():
            w.destroy()

        # Header — 계정 색상 왼쪽 바
        hf = tk.Frame(main_frame, bg=BG)
        hf.pack(fill="x", pady=(0, 4))
        tk.Frame(hf, bg=acct_color, width=5).pack(side="left", fill="y", padx=(0, 10))
        tk.Label(hf, text="BRIDGE", bg=BG, fg=WHITE,
                 font=(FONT, 22, "bold")).pack(side="left")
        tk.Label(hf, text="  RPA", bg=BG, fg=GRAY1,
                 font=(FONT, 22)).pack(side="left")

        tk.Label(main_frame, text=f"{acct_label}  ·  {total} posts",
                 bg=BG, fg=acct_color, font=(FONT, 11, "bold")).pack(anchor="w", pady=(2, 20))

        tk.Frame(main_frame, bg=GRAY2, height=1).pack(fill="x", pady=(0, 28))

        # Bouncing dots canvas
        CW, CH = W - PAD * 2, 56
        dot_cv = tk.Canvas(main_frame, bg=BG, highlightthickness=0,
                           width=CW, height=CH)
        dot_cv.pack()

        DOT_R  = 9
        N_DOTS = 5
        SPACING = 32
        CX = CW // 2
        CY = CH // 2
        dot_ids = []
        for i in range(N_DOTS):
            dx = CX - (N_DOTS - 1) * SPACING // 2 + i * SPACING
            oid = dot_cv.create_oval(dx - DOT_R, CY - DOT_R,
                                     dx + DOT_R, CY + DOT_R,
                                     fill=acct_color, outline="")
            dot_ids.append((dx, oid))

        phase = [0.0]

        def animate():
            phase[0] += 0.18
            for i, (dx, oid) in enumerate(dot_ids):
                amp = 10 + 2 * i
                oy  = math.sin(phase[0] + i * 1.1) * amp
                dot_cv.coords(oid,
                              dx - DOT_R, CY - DOT_R + oy,
                              dx + DOT_R, CY + DOT_R + oy)
            _anim_id[0] = root.after(35, animate)

        animate()

        # Progress number
        prog_lbl = tk.Label(main_frame, text=f"0 / {total}",
                            bg=BG, fg=WHITE, font=(FONT, 36, "bold"))
        prog_lbl.pack(pady=(14, 2))

        tk.Label(main_frame, text="posts completed",
                 bg=BG, fg=GRAY1, font=(FONT, 11)).pack()

        # 현재 제목 (공고명)
        curr_lbl = tk.Label(main_frame, text="시작 중...",
                            bg=BG, fg=GRAY1, font=(FONT, 10),
                            wraplength=W - PAD * 2 - 10)
        curr_lbl.pack(pady=(6, 0))

        # 세부 작업 단계 표시 (페이지 로딩 / 제목 작성 / 본문 작성 등)
        step_lbl = tk.Label(main_frame, text="⏳ 작성 준비 중...",
                            bg=BG, fg=acct_color, font=(FONT, 10, "bold"),
                            wraplength=W - PAD * 2 - 10)
        step_lbl.pack(pady=(2, 0))

        tk.Frame(main_frame, bg=GRAY2, height=1).pack(fill="x", pady=14)

        # 중단 버튼 — 확인 팝업
        def _request_stop():
            if messagebox.askyesno(
                "중단 확인",
                "게시를 중단할까요?\n현재 항목 완료 후 중단됩니다.",
                icon="warning", parent=root,
            ):
                OVERLAY_STOP_FLAG.touch()
                stop_btn.configure(text="⛔  중단 요청됨...", state="disabled",
                                   fg=GRAY1, cursor="arrow")

        stop_btn = tk.Button(
            main_frame, text="⏹  Stop",
            bg=CARD, fg=RED, font=(FONT, 12),
            relief="flat", bd=0, cursor="hand2", pady=12,
            activebackground=GRAY2, activeforeground=RED,
            command=_request_stop,
        )
        stop_btn.pack(fill="x")

        # Poll overlay_state.json for progress
        _done_fired = [False]

        def poll():
            try:
                state   = json.loads(OVERLAY_STATE.read_text(encoding="utf-8"))
                done    = state.get("done", 0)
                success = state.get("success", 0)
                status  = state.get("status", "running")
                current = state.get("current", "")
                step    = state.get("step", "")
                prog_lbl.configure(text=f"{done} / {total}")
                if current:
                    curr_lbl.configure(text=current)
                if step:
                    step_lbl.configure(text=step)
                if status == "done" and not _done_fired[0]:
                    _done_fired[0] = True
                    if _anim_id[0]:
                        root.after_cancel(_anim_id[0])
                    dot_cv.delete("all")
                    dot_cv.create_text(CX, CY, text="✓", fill=acct_color,
                                       font=(FONT, 32, "bold"))
                    prog_lbl.configure(text=f"{success} / {total}", fg=acct_color)
                    curr_lbl.configure(text=f"완료!  성공 {success} / 전체 {total}")
                    step_lbl.configure(text="")
                    stop_btn.pack_forget()
                    # 완료 후 추가 게시 여부 팝업
                    def _ask_more():
                        ans = messagebox.askyesno(
                            "게시 완료",
                            f"✅  {success}/{total}건 게시 완료!\n\n추가로 게시하시겠습니까?",
                            icon="question", parent=root,
                        )
                        if ans:
                            show_selection()
                        else:
                            root.destroy()
                            os._exit(0)
                    root.after(600, _ask_more)
                    return
            except Exception:
                pass
            _poll_id[0] = root.after(1500, poll)

        _poll_id[0] = root.after(3000, poll)

    # ── Spawn worker & switch to working screen ──────────────────────
    def _spawn_worker(limit: int, acct_idx: int):
        DETACHED = 0x00000008
        NO_WIN   = 0x08000000
        acct_label = (ACCOUNTS[acct_idx]["label"]
                      if 0 <= acct_idx < len(ACCOUNTS) else "Account")
        subprocess.Popen(
            [str(pythonw), os.path.abspath(__file__),
             "--worker", f"--limit={limit}",
             f"--account-idx={acct_idx}", "--no-relaunch"],
            creationflags=DETACHED | NO_WIN, close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        show_working(acct_label, limit, acct_idx)

    show_selection()
    root.mainloop()


if __name__ == "__main__":
    main()
