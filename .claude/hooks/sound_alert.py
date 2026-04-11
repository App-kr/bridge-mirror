#!/usr/bin/env python3
"""
sound_alert.py — 지연 알림 시스템
PreToolUse Bash  → 대기 파일 생성 + 60초 후 알림 백그라운드 실행
PostToolUse Bash → 대기 파일 삭제 (취소)
Stop             → 즉시 알림
"""
import sys
import json
import os
import subprocess
import time
import winsound
import urllib.request
from pathlib import Path

PENDING_FILE = Path(r"Q:\Claudework\bridge base\.claude\bash_pending.json")
DELAY_SECS   = 60
TG_CHAT_ID   = "7057194111"


def _get_tg_token():
    try:
        sys.path.insert(0, r"Q:\Claudework\bridge base\tools")
        from bx import _read
        return _read("TELEGRAM_BOT_TOKEN") or ""
    except Exception:
        return os.environ.get("TELEGRAM_BOT_TOKEN", "")


def play_sound():
    try:
        winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
    except Exception:
        pass
    time.sleep(0.1)
    winsound.Beep(330, 120)
    winsound.Beep(440, 120)
    winsound.Beep(523, 250)


def send_telegram(text: str):
    token = _get_tg_token()
    if not token:
        return
    try:
        payload = json.dumps({"chat_id": TG_CHAT_ID, "text": text}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def mode_pre_bash(cmd: str):
    """PreToolUse Bash: 대기 파일 쓰고 백그라운드로 delayed_alert 실행."""
    ts = time.time()
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    PENDING_FILE.write_text(json.dumps({"ts": ts, "cmd": cmd[:200]}), encoding="utf-8")

    # 60초 후 확인하는 백그라운드 프로세스 실행
    script = Path(__file__).resolve()
    subprocess.Popen(
        [sys.executable, str(script), "delayed", str(ts)],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        close_fds=True,
    )


def mode_post_bash():
    """PostToolUse Bash: 대기 파일 삭제 → 알림 취소."""
    try:
        PENDING_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def mode_delayed(orig_ts: float):
    """60초 대기 후 pending 파일이 같은 ts면 알림."""
    time.sleep(DELAY_SECS)

    if not PENDING_FILE.exists():
        return  # 이미 취소됨

    try:
        data = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
        if abs(data.get("ts", 0) - orig_ts) > 1:
            return  # 다른 bash 명령으로 교체됨
        cmd = data.get("cmd", "")
    except Exception:
        return

    # 1분 이상 응답 없음 → 알림
    play_sound()
    send_telegram(f"⏰ Bash 1분째 대기 중\n승인이 필요합니다\n\n`{cmd}`")


def mode_stop():
    """Stop: 즉시 알림."""
    PENDING_FILE.unlink(missing_ok=True)  # 혹시 남은 pending 정리
    play_sound()
    send_telegram("✅ Claude 작업 완료")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre"

    if mode == "stop":
        mode_stop()

    elif mode == "post":
        mode_post_bash()

    elif mode == "delayed":
        orig_ts = float(sys.argv[2]) if len(sys.argv) > 2 else 0
        mode_delayed(orig_ts)

    else:  # "pre" — PreToolUse Bash
        try:
            raw = sys.stdin.read()
            data = json.loads(raw) if raw.strip() else {}
            cmd = data.get("tool_input", {}).get("command", "")
        except Exception:
            cmd = ""
        mode_pre_bash(cmd)


if __name__ == "__main__":
    main()
