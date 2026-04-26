"""
email_reporter.py — BRIDGE 이메일 처리 현황 텔레그램 보고
=============================================================
매 3시간마다 Task Scheduler로 실행.
오늘(KST) 처리된 메일 현황을 텔레그램으로 보고.

실행:
  python tools/email_reporter.py          # 오늘 현황 보고
  python tools/email_reporter.py --date 2026-04-24  # 특정일 보고
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
DB_PATH = PROJECT_ROOT / "master.db"
_KST = timezone(timedelta(hours=9))


# ── 토큰 ─────────────────────────────────────────────────────────────────────

def _get_token() -> str:
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "tools"))
        from bx import _read as bx_read
        t = bx_read("TELEGRAM_BOT_TOKEN")
        if t:
            return t
    except Exception:
        pass
    return os.getenv("TELEGRAM_BOT_TOKEN", "")


def _get_chat_ids() -> list[int]:
    try:
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute(
            "SELECT chat_id FROM tg_alert_subscribers WHERE active=1"
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def _tg_send(token: str, chat_id: int, text: str) -> bool:
    if not token:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4000], "parse_mode": "HTML"},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


# ── DB 조회 ───────────────────────────────────────────────────────────────────

def _fetch_logs(date_str: str) -> list[dict]:
    """해당 날짜(KST YYYY-MM-DD)의 email_logs 조회."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        # created_at은 UTC로 저장됨 → KST 날짜로 변환 후 필터
        rows = conn.execute("""
            SELECT from_email, from_name, subject, type, status,
                   sent_at, received_at, created_at
            FROM email_logs
            WHERE DATE(created_at, '+9 hours') = ?
            ORDER BY created_at ASC
        """, (date_str,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB] 조회 실패: {e}")
        return []


def _fetch_logs_range(start_dt: datetime, end_dt: datetime) -> list[dict]:
    """UTC 범위로 email_logs 조회 (3시간 구간 보고용)."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT from_email, from_name, subject, type, status,
                   sent_at, received_at, created_at
            FROM email_logs
            WHERE created_at >= ? AND created_at < ?
            ORDER BY created_at ASC
        """, (
            start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        )).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB] 조회 실패: {e}")
        return []


# ── 보고 메시지 생성 ──────────────────────────────────────────────────────────

def _fmt_time(ts_str: str | None) -> str:
    """created_at(UTC) → KST HH:MM"""
    if not ts_str:
        return "??"
    try:
        dt = datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S")
        dt_kst = dt.replace(tzinfo=timezone.utc).astimezone(_KST)
        return dt_kst.strftime("%H:%M")
    except Exception:
        return "??"


def build_report(logs: list[dict], report_date: str, period_label: str = "") -> str:
    """email_logs 리스트로 보고 메시지 생성."""
    sent     = [r for r in logs if r["status"] == "SENT"]
    failed   = [r for r in logs if r["status"] == "FAILED"]
    conv     = [r for r in logs if r["type"] in ("CONV", "RETURNING")]
    spam     = [r for r in logs if r["type"] == "SPAM"]
    unknown  = [r for r in logs if r["type"] == "UNKNOWN" and r["status"] == "SKIPPED"]

    now_kst = datetime.now(_KST).strftime("%H:%M")
    header  = f"[BRIDGE 메일 보고] {report_date} {now_kst} KST"
    if period_label:
        header += f" ({period_label})"

    lines = [f"<b>{header}</b>\n"]

    # 회신 발송
    if sent:
        lines.append(f"📨 <b>회신 발송 {len(sent)}건</b>")
        for r in sent:
            t     = _fmt_time(r["created_at"])
            name  = r["from_name"] or "(이름없음)"
            email = r["from_email"]
            subj  = r["subject"] or ""
            # 접수자 유형 태그
            tag = "신규" if r["type"] == "NEW_APPLICANT" else r["type"]
            lines.append(f"  {t} {name} — {email}")
            lines.append(f"       ({tag}) {subj[:40]}")
    else:
        lines.append("📨 회신 발송 없음")

    # 발송 실패
    if failed:
        lines.append(f"\n🚨 <b>발송 실패 {len(failed)}건</b>")
        for r in failed:
            lines.append(f"  {r['from_email']} | {r['subject'][:40]}")

    # 기존 연락자 건너뜀
    if conv:
        lines.append(f"\n📋 기존 연락자 건너뜀 {len(conv)}건")
        for r in conv:
            t    = _fmt_time(r["created_at"])
            tag  = "연락이력" if r["type"] == "CONV" else "기존접수자"
            lines.append(f"  {t} {r['from_email']} ({tag})")

    # 스팸
    if spam:
        lines.append(f"\n🗑️ 스팸 차단 {len(spam)}건")
        for r in spam:
            lines.append(f"  {r['from_email']}")

    # 패턴 미해당
    if unknown:
        lines.append(f"\n❓ 패턴 미해당 {len(unknown)}건")
        for r in unknown:
            lines.append(f"  {r['from_email']} | {r['subject'][:35]}")

    # 합계
    lines.append(
        f"\n📊 합계: 발송 {len(sent)} / 기존 {len(conv)} "
        f"/ 스팸 {len(spam)} / 미해당 {len(unknown)}"
    )

    if not logs:
        lines = [f"<b>{header}</b>\n", "처리된 메일 없음"]

    return "\n".join(lines)


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    # 날짜 인수 파싱
    date_arg = None
    mode = "daily"
    for arg in sys.argv[1:]:
        if arg == "--3h":
            mode = "3h"
        elif arg.startswith("--date"):
            parts = arg.split("=")
            if len(parts) == 2:
                date_arg = parts[1]
            elif len(sys.argv) > sys.argv.index(arg) + 1:
                date_arg = sys.argv[sys.argv.index(arg) + 1]

    now_kst  = datetime.now(_KST)
    date_str = date_arg or now_kst.strftime("%Y-%m-%d")

    if mode == "3h":
        # 지난 3시간 구간 (UTC)
        end_utc   = datetime.now(timezone.utc).replace(tzinfo=None)
        start_utc = end_utc - timedelta(hours=3)
        logs = _fetch_logs_range(start_utc, end_utc)
        h    = now_kst.hour
        period = f"{h-3 if h >= 3 else 24+h-3:02d}:00~{h:02d}:00"
        msg  = build_report(logs, date_str, period_label=period)
    else:
        logs = _fetch_logs(date_str)
        msg  = build_report(logs, date_str)

    token    = _get_token()
    chat_ids = _get_chat_ids()

    if not token or not chat_ids:
        print("[reporter] 텔레그램 미설정 — 콘솔 출력만")
        print(msg)
        return

    for cid in chat_ids:
        ok = _tg_send(token, cid, msg)
        print(f"[reporter] {'✅' if ok else '❌'} chat_id={cid}")

    print(msg)


if __name__ == "__main__":
    main()
