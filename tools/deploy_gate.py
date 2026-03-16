"""
배포 게이트 — git push 전 텔레그램 승인 대기
=============================================
pre-push 훅에서 호출됨.

흐름:
  git push
    → pre-push 훅
      → deploy_gate.py (이 스크립트)
        → 텔레그램: "배포할까요? /yes /no"
        → 최대 10분 대기
        → /yes → exit 0 → push 진행 → 배포됨
        → /no  → exit 1 → push 차단

사용법:
  python tools/deploy_gate.py          ← pre-push 훅에서 자동 호출
  python tools/deploy_gate.py --force  ← 승인 없이 즉시 통과 (긴급용)
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


# ── 헬퍼 ───────────────────────────────────────────────────────────────────────
def tg_send(chat_id: int, text: str, reply_markup=None) -> bool:
    if not TG_TOKEN:
        return False
    payload = {"chat_id": chat_id, "text": text[:4000], "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json=payload, timeout=10,
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
    """현재 push할 커밋 정보 수집."""
    try:
        # 원격과 차이나는 커밋들
        r = subprocess.run(
            ["git", "log", "origin/main..HEAD", "--oneline"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT), encoding="utf-8"
        )
        commits = r.stdout.strip().splitlines()

        # 변경된 파일
        r2 = subprocess.run(
            ["git", "diff", "origin/main..HEAD", "--name-only"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT), encoding="utf-8"
        )
        files = r2.stdout.strip().splitlines()

        # 최신 커밋 메시지
        r3 = subprocess.run(
            ["git", "log", "-1", "--pretty=%s"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT), encoding="utf-8"
        )
        latest_msg = r3.stdout.strip()

        # 브랜치
        r4 = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT), encoding="utf-8"
        )
        branch = r4.stdout.strip() or "main"

        return {
            "commits": commits[:5],
            "files": files[:10],
            "latest_msg": latest_msg,
            "branch": branch,
            "commit_count": len(commits),
            "file_count": len(files),
        }
    except Exception as e:
        return {
            "commits": ["(정보 없음)"],
            "files": [],
            "latest_msg": "알 수 없음",
            "branch": "main",
            "commit_count": 1,
            "file_count": 0,
        }


def build_deploy_msg(info: dict, request_id: str) -> str:
    """텔레그램 배포 승인 요청 메시지."""
    commits_str = "\n".join(f"  • {c}" for c in info["commits"]) or "  • (없음)"
    files_str = "\n".join(f"  {f}" for f in info["files"][:8])
    if info["file_count"] > 8:
        files_str += f"\n  ... 외 {info['file_count'] - 8}개"

    return (
        f"🚀 <b>배포 승인 요청</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌿 브랜치: <code>{info['branch']}</code>\n"
        f"📦 커밋 {info['commit_count']}개:\n{commits_str}\n\n"
        f"📁 변경 파일 {info['file_count']}개:\n{files_str if files_str else '  (없음)'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ 요청: {datetime.now().strftime('%m/%d %H:%M:%S')}\n"
        f"⏳ 10분 내 응답 없으면 자동 차단\n\n"
        f"✅ <code>/yes</code>  — 배포 승인\n"
        f"❌ <code>/no</code>  — 배포 차단\n"
        f"<i>ID: {request_id[:8]}</i>"
    )


def write_state(request_id: str, info: dict, status: str = "pending"):
    STATE_FILE.write_text(
        json.dumps({
            "request_id": request_id,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "info": info,
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


# ── 메인 ───────────────────────────────────────────────────────────────────────
def main():
    # --force: 승인 없이 통과
    if "--force" in sys.argv:
        print("[deploy_gate] --force: 승인 없이 통과")
        sys.exit(0)

    # 구독자 없으면 통과 (설정 안 된 경우 막지 않음)
    subscribers = get_subscribers()
    if not subscribers:
        print("[deploy_gate] 텔레그램 구독자 없음 — 게이트 건너뜀")
        print("  /alerts on 으로 구독 후 게이트 활성화")
        sys.exit(0)

    if not TG_TOKEN:
        print("[deploy_gate] TELEGRAM_BOT_TOKEN 미설정 — 게이트 건너뜀")
        sys.exit(0)

    # 커밋 정보 수집
    info = get_commit_info()
    if info["commit_count"] == 0:
        print("[deploy_gate] push할 커밋 없음 — 통과")
        sys.exit(0)

    # 요청 ID 생성
    request_id = str(uuid.uuid4())

    # 이전 요청 초기화
    clear_state()
    write_state(request_id, info, "pending")

    # 텔레그램 알림 전송
    msg = build_deploy_msg(info, request_id)
    sent = 0
    for cid in subscribers:
        if tg_send(cid, msg):
            sent += 1

    if sent == 0:
        print("[deploy_gate] 텔레그램 전송 실패 — 게이트 건너뜀")
        clear_state()
        sys.exit(0)

    print(f"[deploy_gate] 텔레그램 승인 대기 중... (최대 {TIMEOUT}초)")
    print(f"  봇에서 /yes 또는 /no 로 응답하세요")

    # 폴링 대기
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        time.sleep(2)
        state = read_state()
        status = state.get("status", "pending")

        if status == "approved":
            approver = state.get("approver", "")
            print(f"[deploy_gate] ✅ 승인됨 ({approver}) — push 진행")
            clear_state()
            # 승인 확인 메시지 전송
            for cid in subscribers:
                tg_send(cid, f"✅ <b>배포 시작</b>\n{info['latest_msg'][:80]}\n배포가 진행됩니다...")
            sys.exit(0)

        elif status == "rejected":
            reason = state.get("reason", "")
            print(f"[deploy_gate] ❌ 거부됨 ({reason}) — push 차단")
            clear_state()
            sys.exit(1)

        remaining = int(deadline - time.time())
        if remaining % 60 == 0 and remaining > 0:
            print(f"[deploy_gate] 대기 중... 남은시간 {remaining}초")

    # 타임아웃
    print(f"[deploy_gate] ⏰ {TIMEOUT}초 타임아웃 — push 차단")
    for cid in subscribers:
        tg_send(cid, "⏰ 배포 요청 타임아웃 — 자동 차단됨\n다시 push하면 새 요청이 전송됩니다.")
    clear_state()
    sys.exit(1)


if __name__ == "__main__":
    main()
