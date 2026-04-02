"""
Craigslist RPA 수동 로그인 도우미
===================================
RPA가 사용하는 Chrome 프로필로 Craigslist 로그인 페이지를 열어줍니다.
Python이 종료된 후 Chrome은 계속 열려 있으므로 로그인 완료 후 직접 닫으세요.
"""
import subprocess
import sys
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
ACCOUNT  = "gray"
if "--account" in sys.argv:
    idx = sys.argv.index("--account")
    if idx + 1 < len(sys.argv):
        ACCOUNT = sys.argv[idx + 1]

PROFILE_DIR  = str(BASE_DIR / ".chrome_rpa_profile" / ACCOUNT)
CL_LOGIN_URL = "https://accounts.craigslist.org/login/home"

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
    r"D:\Google\ProgramFiles\Chrome\Application\chrome.exe",
]

# ── Chrome 탐색 ───────────────────────────────────────────────────────────────
chrome_bin = None
for p in CHROME_CANDIDATES:
    if Path(p).exists():
        chrome_bin = p
        break

if not chrome_bin:
    print("[ERROR] Chrome을 찾을 수 없습니다. Chrome이 설치되어 있는지 확인하세요.")
    sys.exit(1)

# ── 프로필 디렉토리 생성 ──────────────────────────────────────────────────────
Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)

# ── 안내 출력 ─────────────────────────────────────────────────────────────────
print("=" * 60)
print("  Craigslist 수동 로그인 도우미")
print(f"  계정 프로필: {ACCOUNT}")
print(f"  프로필 경로: {PROFILE_DIR}")
print("=" * 60)
print()
print("  [순서]")
print("  1. 지금 Chrome이 열립니다")
print("  2. Craigslist 로그인 페이지에서 이메일/비밀번호 입력")
print("  3. 'Further verification' 화면이 나오면")
print("     → 이 Chrome 창에서 열린 Gmail을 확인하세요")
print("     → Craigslist 이메일에서 링크를 클릭하세요 (이 Chrome에서!)")
print("  4. 로그인 완료되면 Chrome을 닫으세요")
print("  5. 그 다음 run.bat을 실행하면 자동 로그인됩니다")
print()

# ── Chrome 실행 (detach — Python 즉시 종료, Chrome은 계속 열림) ──────────────
subprocess.Popen(
    [
        chrome_bin,
        f"--user-data-dir={PROFILE_DIR}",
        "--new-window",
        CL_LOGIN_URL,
    ],
    creationflags=0x00000008,  # DETACHED_PROCESS — cmd창 독립 실행
)

print(f"  Chrome 시작됨 → 로그인 완료 후 Chrome을 닫으세요")
print()
print("  ※ 이 창(cmd)은 닫아도 됩니다")
