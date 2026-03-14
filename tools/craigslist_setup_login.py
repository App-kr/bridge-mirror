"""
craigslist_setup_login.py — Craigslist 세션 초기 설정 도구

사용법:
  py -3.13 -X utf8 craigslist_setup_login.py

이 스크립트는 RPA 전용 Chrome 프로필을 열고 Craigslist 로그인 페이지로 이동합니다.
창에서 직접 로그인하면 세션이 저장됩니다.
이후 agent_ad_poster.py는 이 세션을 재사용합니다.
"""
import os, time
from pathlib import Path

TOOLS_DIR        = Path(__file__).parent
CHROME_BINARY    = r"D:\Google\ProgramFiles\Chrome\Application\chrome.exe"
CHROME_RPA_PROFILE = str(TOOLS_DIR / ".chrome_rpa_profile")

try:
    import undetected_chromedriver as uc
except ImportError:
    print("설치 필요: py -3.13 -m pip install undetected-chromedriver")
    raise

os.makedirs(CHROME_RPA_PROFILE, exist_ok=True)

opts = uc.ChromeOptions()
opts.add_argument(f"--user-data-dir={CHROME_RPA_PROFILE}")
opts.add_argument("--window-size=1280,900")

driver = uc.Chrome(
    options=opts,
    browser_executable_path=CHROME_BINARY if os.path.exists(CHROME_BINARY) else None,
)

print("\n" + "="*55)
print("Craigslist 로그인 창이 열렸습니다.")
print("→ bridgejobkr@gmail.com 으로 직접 로그인하세요.")
print("→ 로그인 완료 후 이 터미널에서 Enter를 누르세요.")
print("="*55)

driver.get("https://accounts.craigslist.org/login")
input("\n로그인 완료 후 Enter 키...")

print("세션 저장 중...")
time.sleep(2)
driver.quit()
print("완료! 이제 agent_ad_poster.py를 실행하면 로그인 없이 작동합니다.")
