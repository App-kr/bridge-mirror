"""
배포 게이트 — git push 전 텔레그램 승인 대기
=============================================
pre-push 훅에서 자동 호출됨.

예시 메시지:
  "Claude Code에서 '브릿지 홈페이지 네이밍 변경' 배포할까요?"
  → yes / no 로 응답

사용법:
  python tools/deploy_gate.py          ← pre-push 훅 자동 호출
  python tools/deploy_gate.py --force  ← 승인 없이 즉시 통과
"""

import json
import os
import sys
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

TG_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
DB_PATH    = PROJECT_ROOT / "master.db"
STATE_FILE = PROJECT_ROOT / "logs" / "deploy_request.json"
TIMEOUT    = int(os.getenv("DEPLOY_GATE_TIMEOUT", "600"))  # 10분
(PROJECT_ROOT / "logs").mkdir(exist_ok=True)

# 터미널/세션 이름 — .env에 TERMINAL_NAME=터미널1 등으로 설정 가능
TERMINAL_NAME = os.getenv("TERMINAL_NAME", "Claude Code")


def tg_send(chat_id: int, text: str) -> bool:
    if not TG_TOKEN:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4000], "parse_mode": "HTML"},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def get_subscribers() -> list[int]:
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute(
            "SELECT chat_id FROM tg_alert_subscribers WHERE active=1"
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def get_commit_info() -> dict:
    """push할 커밋 정보 수집."""
    def run(cmd):
        return subprocess.run(cmd, capture_output=True, text=True,
                              cwd=str(PROJECT_ROOT), encoding="utf-8").stdout.strip()

    commits  = run(["git", "log", "origin/main..HEAD", "--oneline"]).splitlines()
    files    = run(["git", "diff", "origin/main..HEAD", "--name-only"]).splitlines()
    latest   = run(["git", "log", "-1", "--pretty=%s"])
    branch   = run(["git", "branch", "--show-current"]) or "main"

    return {
        "commits":      commits[:5],
        "files":        files[:8],
        "latest_msg":   latest or "변경사항",
        "branch":       branch,
        "commit_count": len(commits),
        "file_count":   len(files),
    }


def build_msg(info: dict, request_id: str) -> str:
    """자연스러운 한국어 승인 요청 메시지."""
    files_str = "\n".join(f"  • {f}" for f in info["files"]) or "  (없음)"
    time_str  = datetime.now().strftime("%H:%M")

    return (
        f"🟡 [중요] 💬 <b>{TERMINAL_NAME}에서 배포 승인 요청</b> ({time_str})\n\n"
        f"📝 \"{info['latest_msg']}\"\n\n"
        f"📁 변경 파일 {info['file_count']}개:\n{files_str}\n\n"
        f"배포할까요?\n"
        f"✅ <b>yes</b> 또는 <b>/yes</b> — 배포 진행\n"
        f"❌ <b>no</b> 또는 <b>/no</b>   — 취소"
    )


def write_state(request_id: str, info: dict):
    STATE_FILE.write_text(
        json.dumps({
            "request_id": request_id,
            "status":     "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "info":       info,
        }, ensure_ascii=False),
        encoding="utf-8"
    )


def read_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def clear_state():
    try:
        STATE_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def main():
    # --force: 승인 없이 즉시 통과
    if "--force" in sys.argv:
        print("[deploy_gate] --force 통과")
        sys.exit(0)

    subscribers = get_subscribers()
    if not subscribers or not TG_TOKEN:
        print("[deploy_gate] 텔레그램 미설정 — 자동 통과")
        sys.exit(0)

    info = get_commit_info()
    if info["commit_count"] == 0:
        print("[deploy_gate] push할 커밋 없음 — 통과")
        sys.exit(0)

    # 텔레그램으로 승인 요청 전송
    request_id = str(uuid.uuid4())
    clear_state()
    write_state(request_id, info)

    msg = build_msg(info, request_id)
    sent = sum(1 for cid in subscribers if tg_send(cid, msg))

    if sent == 0:
        print("[deploy_gate] 텔레그램 전송 실패 — 자동 통과")
        clear_state()
        sys.exit(0)

    print(f"[deploy_gate] 텔레그램 승인 대기 중 (최대 {TIMEOUT}초) — yes/no 로 응답하세요")

    # 응답 폴링
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        time.sleep(2)
        status = read_state().get("status", "pending")

        if status == "approved":
            print("[deploy_gate] ✅ 승인 — push 진행")
            for cid in subscribers:
                tg_send(cid, f"✅ 배포 시작!\n\"{info['latest_msg'][:80]}\"")
            clear_state()
            sys.exit(0)

        elif status == "rejected":
            print("[deploy_gate] ❌ 거부 — push 취소")
            clear_state()
            sys.exit(1)

        remaining = int(deadline - time.time())
        if remaining % 120 == 0 and remaining > 0:
            print(f"[deploy_gate] 대기 중... {remaining}초 남음")

    # 타임아웃 → 자동 차단
    print(f"[deploy_gate] ⏰ 타임아웃 — push 차단")
    for cid in subscribers:
        tg_send(cid, "⏰ 응답 없음 — 배포 자동 취소됨\n다시 push하면 새로 물어봅니다.")
    clear_state()
    sys.exit(1)


if __name__ == "__main__":
    main()
