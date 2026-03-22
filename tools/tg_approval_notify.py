"""
Claude Code 도구 승인 대기 시 텔레그램 알림
============================================
PreToolUse 훅에서 호출됨 — Bash 명령이 auto-allow 패턴에
없으면 텔레그램으로 "승인 대기 중" 알림 전송

환경변수 (Claude Code 자동 설정):
  CLAUDE_TOOL_NAME   — 도구 이름 (Bash, Edit, Read 등)
  CLAUDE_TOOL_INPUT  — JSON 형태 도구 입력

사용: pre_hook.bat 에서 호출
"""

import json
import os
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

# ── 빠른 종료: Bash 아니면 즉시 exit ──
tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
if tool_name != "Bash":
    sys.exit(0)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
RATE_FILE = LOGS_DIR / "tg_notify_last.txt"
DB_PATH = PROJECT_ROOT / "master.db"

# ── 명령어 파싱 ──
try:
    inp = json.loads(os.environ.get("CLAUDE_TOOL_INPUT", "{}"))
    command = inp.get("command", "")
except Exception:
    sys.exit(0)

if not command:
    sys.exit(0)

# ── auto-allow 패턴 체크 ──
# settings.local.json에서 Bash(prefix:*) 패턴의 prefix 추출
SETTINGS_FILE = PROJECT_ROOT / ".claude" / "settings.local.json"
try:
    settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    allows = settings.get("permissions", {}).get("allow", [])
except Exception:
    allows = []

prefixes = []
for pat in allows:
    if not pat.startswith("Bash("):
        continue
    inner = pat[5:]  # "Bash(" 제거
    if inner.endswith(":*)"):
        prefix = inner[:-3]  # ":*)" 제거
        prefixes.append(prefix)

# 명령어가 auto-allow 패턴에 매칭되면 알림 불필요
cmd_stripped = command.strip()
for p in prefixes:
    if cmd_stripped.startswith(p):
        sys.exit(0)

# ── 레이트 리밋: 60초에 1회 ──
LOGS_DIR.mkdir(exist_ok=True)
try:
    last = float(RATE_FILE.read_text(encoding="utf-8").strip())
    if time.time() - last < 60:
        sys.exit(0)
except Exception:
    pass

# ── BX에서 토큰 복호화 ──
sys.path.insert(0, str(PROJECT_ROOT / "tools"))
try:
    from bx import _read as bx_read
    token = bx_read("TELEGRAM_BOT_TOKEN")
except Exception:
    sys.exit(0)

if not token:
    sys.exit(0)

# ── 구독자 조회 ──
try:
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT chat_id FROM tg_alert_subscribers WHERE active=1"
    ).fetchall()
    conn.close()
    subs = [r[0] for r in rows]
except Exception:
    sys.exit(0)

if not subs:
    sys.exit(0)

# ── 알림 전송 ──
cmd_short = command[:300] + ("..." if len(command) > 300 else "")
now = time.strftime("%H:%M")
msg = (
    f"🔔 Claude Code 승인 대기 ({now})\n"
    f"━━━━━━━━━━━━━━━━━━━━━━\n"
    f"$ {cmd_short}\n\n"
    f"터미널에서 Allow/Deny 선택 필요"
)

sent = False
for cid in subs:
    try:
        data = json.dumps({"chat_id": cid, "text": msg}).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
        sent = True
    except Exception:
        pass

if sent:
    RATE_FILE.write_text(str(time.time()), encoding="utf-8")
