"""
텔레그램 알림 발송 유틸리티
===========================
Claude Code에서 push 전 작업 내용 알림용.

사용:
  python tools/tg_notify.py "메시지 내용"
  python tools/tg_notify.py --push "커밋 메시지 요약"
"""
import json
import os
import sqlite3
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "master.db"

# bx에서 토큰 복호화
sys.path.insert(0, str(PROJECT_ROOT / "tools"))
try:
    from bx import _read as bx_read
    TOKEN = bx_read("TELEGRAM_BOT_TOKEN")
except Exception:
    TOKEN = None

if not TOKEN:
    print("[tg_notify] TELEGRAM_BOT_TOKEN 없음 — 알림 건너뜀")
    sys.exit(0)


def get_subscribers():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute(
            "SELECT chat_id FROM tg_alert_subscribers WHERE active=1"
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def send(text: str):
    subs = get_subscribers()
    if not subs:
        print("[tg_notify] 구독자 없음")
        return False
    sent = False
    for cid in subs:
        try:
            data = json.dumps({
                "chat_id": cid,
                "text": text[:4000],
                "parse_mode": "HTML",
            }).encode("utf-8")
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=10)
            sent = True
        except Exception as e:
            print(f"[tg_notify] 발송 실패 (chat_id={cid}): {e}")
    return sent


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tg_notify.py \"메시지\"")
        print("       python tg_notify.py --push \"작업 내용\"")
        sys.exit(1)

    if sys.argv[1] == "--push":
        desc = sys.argv[2] if len(sys.argv) > 2 else "작업 내용 미기재"
        msg = (
            f"📦 <b>Push 예정 알림</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{desc}\n\n"
            f"push 진행합니다"
        )
    else:
        msg = " ".join(sys.argv[1:])

    ok = send(msg)
    if ok:
        print("[tg_notify] 발송 완료")
    else:
        print("[tg_notify] 발송 실패")
