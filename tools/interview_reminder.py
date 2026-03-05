"""
BRIDGE Interview Reminder — 자동 알람
=====================================
예정된 인터뷰 30분 전 자동 리마인더 이메일 발송.
Windows Task Scheduler에서 10분 간격으로 실행.

보안: 키/비밀번호 하드코딩 없음. .env + email_templates.py 사용.
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from email_templates import _send_email

# 로깅
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "interview_reminder.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bridge.reminder")

DB_PATH = PROJECT_ROOT / "master.db"
REMINDER_MINUTES = 30  # 인터뷰 30분 전 알림


def _ensure_reminder_column():
    """reminder_sent_at 컬럼이 없으면 추가."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        conn.execute("ALTER TABLE interviews ADD COLUMN reminder_sent_at TEXT")
        conn.commit()
        log.info("Added reminder_sent_at column to interviews table")
    except Exception:
        pass  # 이미 존재
    finally:
        conn.close()


def _build_reminder_html_candidate(name: str, date: str, time: str, meet_link: str) -> str:
    """후보자용 리마인더 HTML."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; line-height: 1.7;">
      <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #1d1d1f;">
        <h1 style="margin: 0; font-size: 24px; color: #1d1d1f; font-weight: 700;">BRIDGE</h1>
      </div>
      <div style="padding: 30px 0;">
        <p>Dear {name},</p>
        <p>This is a friendly reminder that your interview is starting in <strong>30 minutes</strong>.</p>
        <div style="background: #fef3c7; border: 1px solid #fbbf24; padding: 20px; margin: 24px 0; border-radius: 12px; text-align: center;">
          <p style="margin: 0 0 4px; font-size: 14px; color: #92400e; font-weight: 600;">STARTING SOON</p>
          <p style="margin: 0 0 12px; font-size: 20px; font-weight: 700; color: #78350f;">
            {date} at {time} (KST)
          </p>
          <a href="{meet_link}" style="display: inline-block; background: #1d1d1f; color: #fff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">
            Join Google Meet Now
          </a>
          <p style="margin: 12px 0 0; font-size: 12px; color: #6b7280;">
            <a href="{meet_link}" style="color: #0071e3;">{meet_link}</a>
          </p>
        </div>
        <ul style="margin: 16px 0; padding-left: 20px; color: #424245; font-size: 14px;">
          <li>Test your camera and microphone</li>
          <li>Find a quiet, well-lit space</li>
          <li>Join 2-3 minutes early</li>
        </ul>
        <p style="color: #6e6e73; margin-top: 24px;">Good luck!<br><strong>BRIDGE Team</strong></p>
      </div>
      <div style="border-top: 1px solid #e5e7eb; padding-top: 12px; text-align: center; font-size: 11px; color: #86868b;">
        <p>The BRIDGE Team &middot; <a href="https://bridgejob.co.kr" style="color: #0071e3;">bridgejob.co.kr</a></p>
      </div>
    </body>
    </html>
    """


def _build_reminder_html_employer(name: str, date: str, time: str, meet_link: str, candidate: str) -> str:
    """고용주용 리마인더 HTML."""
    candidate_info = f" (후보자: {candidate})" if candidate else ""
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, 'Segoe UI', 'Malgun Gothic', sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; line-height: 1.7;">
      <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #1d1d1f;">
        <h1 style="margin: 0; font-size: 24px; color: #1d1d1f; font-weight: 700;">BRIDGE</h1>
      </div>
      <div style="padding: 30px 0;">
        <p>안녕하세요, {name}님</p>
        <p>인터뷰가 <strong>30분 후</strong> 시작됩니다{candidate_info}.</p>
        <div style="background: #fef3c7; border: 1px solid #fbbf24; padding: 20px; margin: 24px 0; border-radius: 12px; text-align: center;">
          <p style="margin: 0 0 4px; font-size: 14px; color: #92400e; font-weight: 600;">곧 시작</p>
          <p style="margin: 0 0 12px; font-size: 20px; font-weight: 700; color: #78350f;">
            {date} {time} (한국시간)
          </p>
          <a href="{meet_link}" style="display: inline-block; background: #1d1d1f; color: #fff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">
            Google Meet 입장
          </a>
          <p style="margin: 12px 0 0; font-size: 12px; color: #6b7280;">
            <a href="{meet_link}" style="color: #0071e3;">{meet_link}</a>
          </p>
        </div>
        <p style="color: #6e6e73; margin-top: 24px;">감사합니다.<br><strong>BRIDGE Team 드림</strong></p>
      </div>
      <div style="border-top: 1px solid #e5e7eb; padding-top: 12px; text-align: center; font-size: 11px; color: #86868b;">
        <p>The BRIDGE Team &middot; <a href="https://bridgejob.co.kr" style="color: #0071e3;">bridgejob.co.kr</a></p>
      </div>
    </body>
    </html>
    """


def check_and_send_reminders():
    """예정된 인터뷰를 체크하고 30분 전 리마인더 발송."""
    _ensure_reminder_column()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row

    try:
        now = datetime.now()
        target = now + timedelta(minutes=REMINDER_MINUTES)

        # 오늘 날짜의 scheduled 인터뷰 중 리마인더 미발송건
        today_str = now.strftime("%Y-%m-%d")
        rows = conn.execute(
            """SELECT id, candidate_name, candidate_email, employer_name, employer_email,
                      interview_date, interview_time, meet_link
               FROM interviews
               WHERE is_deleted = 0
                 AND status = 'scheduled'
                 AND interview_date = ?
                 AND (reminder_sent_at IS NULL OR reminder_sent_at = '')""",
            (today_str,),
        ).fetchall()

        sent_count = 0
        for row in rows:
            # 인터뷰 시간 파싱
            try:
                interview_dt = datetime.strptime(
                    f"{row['interview_date']} {row['interview_time']}",
                    "%Y-%m-%d %H:%M"
                )
            except ValueError:
                # HH:MM AM/PM 포맷 시도
                try:
                    interview_dt = datetime.strptime(
                        f"{row['interview_date']} {row['interview_time']}",
                        "%Y-%m-%d %I:%M %p"
                    )
                except ValueError:
                    log.warning("Interview #%d: cannot parse time '%s'", row["id"], row["interview_time"])
                    continue

            # 30분 이내 ~ 이미 지난 건 제외
            minutes_until = (interview_dt - now).total_seconds() / 60
            if minutes_until < 0 or minutes_until > REMINDER_MINUTES:
                continue

            log.info("Interview #%d in %.0f min — sending reminders", row["id"], minutes_until)

            # 후보자 리마인더
            if row["candidate_email"]:
                html = _build_reminder_html_candidate(
                    row["candidate_name"] or "Candidate",
                    row["interview_date"], row["interview_time"],
                    row["meet_link"],
                )
                ok = _send_email(
                    row["candidate_email"],
                    f"Reminder: Interview in {int(minutes_until)} minutes!",
                    html,
                )
                if ok:
                    log.info("  Candidate reminder sent → %s", row["candidate_email"])

            # 고용주 리마인더
            if row["employer_email"]:
                html = _build_reminder_html_employer(
                    row["employer_name"] or "담당자",
                    row["interview_date"], row["interview_time"],
                    row["meet_link"],
                    row["candidate_name"] or "",
                )
                ok = _send_email(
                    row["employer_email"],
                    f"알림: 인터뷰 {int(minutes_until)}분 후 시작",
                    html,
                )
                if ok:
                    log.info("  Employer reminder sent → %s", row["employer_email"])

            # 리마인더 발송 기록
            conn.execute(
                "UPDATE interviews SET reminder_sent_at = ? WHERE id = ?",
                (now.strftime("%Y-%m-%d %H:%M:%S"), row["id"]),
            )
            conn.commit()
            sent_count += 1

        if sent_count > 0:
            log.info("Total reminders sent: %d", sent_count)
        else:
            log.info("No upcoming interviews requiring reminders")

    except Exception as e:
        log.error("Reminder check failed: %s", e, exc_info=True)
    finally:
        conn.close()


if __name__ == "__main__":
    check_and_send_reminders()
