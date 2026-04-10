"""
rpa_relogin.py — gray 자격증명 + default 프로필로 Craigslist 재로그인.
쿠키 만료 시 1회 실행하면 세션 복구됨.
"""
import sys, time, random
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from craigslist_auto_rpa import build_driver, cl_login, _load_craigslist_credentials
import craigslist_auto_rpa as rpa

# gray 자격증명 로드
email, password = _load_craigslist_credentials("gray")
rpa.CL_EMAIL    = email
rpa.CL_PASSWORD = password

print(f"[RELOGIN] 계정: {email}")
print(f"[RELOGIN] Chrome 창이 열립니다...")
print(f"[RELOGIN] 이메일 링크가 오면 Gmail에서 클릭하세요. 최대 10분 대기.")

driver = build_driver(headless=False, account="gray")
ok = cl_login(driver)

if ok:
    print("[RELOGIN] ✅ 로그인 성공 — 쿠키 저장됨. 이제 RPA.vbs 실행하세요.")
else:
    print("[RELOGIN] ❌ 로그인 실패 — Gmail 확인 후 다시 시도하세요.")

try:
    driver.quit()
except Exception:
    pass
