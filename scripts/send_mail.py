"""
BRIDGE 개별 메일 발송 스크립트
- 각 수신자에게 1:1 개별 발송 (BCC 아님, 타인 정보 절대 미노출)
- SMTP over TLS (Gmail)
- 테스트 모드: --dry-run으로 실제 발송 없이 확인

사전 준비:
  Gmail → 2단계 인증 활성화 → 앱 비밀번호 생성
  환경변수 설정:
    set BRIDGE_SMTP_USER=bridgejobkr@gmail.com
    set BRIDGE_SMTP_PASS=앱비밀번호16자리

Usage:
  # 테스트 (발송 안 함, 로그만)
  python send_mail.py --dry-run

  # 실제 발송 테스트 (3명에게)
  python send_mail.py

  # JSON 파일에서 수신자 로드
  python send_mail.py --recipients recipients.json
"""

from __future__ import annotations

import smtplib
import json
import os
import sys
import time
import argparse
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bridge_mail")

# ─── 설정 ───────────────────────────────────────────────
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.environ.get("BRIDGE_SMTP_USER", "")
SMTP_PASS = os.environ.get("BRIDGE_SMTP_PASS", "")
FROM_NAME = "BRIDGE Recruitment"

# ─── 테스트 수신자 ──────────────────────────────────────
TEST_RECIPIENTS = [
    {
        "name": "Test User 1",
        "email": "cnee89@gmail.com",
        "region": "부산",
        "city": "해운대",
        "teachingAge": "Kindy - Elem",
    },
    {
        "name": "Test User 2",
        "email": "bridgejobkr@naver.com",
        "region": "서울",
        "city": "구로",
        "teachingAge": "Elem, Adult",
    },
    {
        "name": "Test User 3",
        "email": "bestpucca@naver.com",
        "region": "경기",
        "city": "수원",
        "teachingAge": "Kinder",
    },
]

# ─── 메일 템플릿 ─────────────────────────────────────────
TEMPLATE_SUBJECT = "[BRIDGE] 개별발송 테스트 — {{name}}님 전용"
TEMPLATE_BODY = """Dear {{name}},

This is a test email from BRIDGE Recruitment System.

This email was sent INDIVIDUALLY to you only.
No other recipients can see this email or your information.

▸ Your Info (verification):
  - Name: {{name}}
  - Email: {{email}}
  - Region: {{region}} {{city}}
  - Teaching Age: {{teachingAge}}

If you received this email, the individual sending system is working correctly.

Best regards,
BRIDGE Recruitment Team
bridgejob.co.kr

---
이 메일은 개별 발송 테스트입니다.
수신자 본인에게만 발송되었으며, 다른 수신자의 정보는 포함되지 않습니다.
"""


def replace_placeholders(text: str, data: dict) -> str:
    """{{key}} 플레이스홀더를 데이터로 치환"""
    result = text
    for key, value in data.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def send_individual_email(
    recipient: dict,
    subject_template: str,
    body_template: str,
    attachments: list[str] | None = None,
    dry_run: bool = False,
) -> bool:
    """단일 수신자에게 1:1 개별 메일 발송

    핵심: To 필드에 수신자 1명만. BCC/CC 없음.
    """
    to_email = recipient["email"]
    subject = replace_placeholders(subject_template, recipient)
    body = replace_placeholders(body_template, recipient)

    msg = MIMEMultipart()
    msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
    msg["To"] = to_email  # 수신자 1명만!
    msg["Subject"] = subject
    # Reply-To 설정
    msg["Reply-To"] = SMTP_USER

    # 본문
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # 첨부파일
    if attachments:
        for filepath in attachments:
            path = Path(filepath)
            if path.exists():
                part = MIMEBase("application", "octet-stream")
                part.set_payload(path.read_bytes())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={path.name}",
                )
                msg.attach(part)
                log.info(f"  첨부: {path.name}")

    if dry_run:
        log.info(f"  [DRY-RUN] To: {to_email} | Subject: {subject[:50]}...")
        log.info(f"  [DRY-RUN] Body preview: {body[:100]}...")
        return True

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        log.info(f"  ✓ 발송 완료: {to_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        log.error(f"  ✗ SMTP 인증 실패 — 앱 비밀번호 확인 필요")
        return False
    except smtplib.SMTPRecipientsRefused:
        log.error(f"  ✗ 수신자 거부: {to_email}")
        return False
    except Exception as e:
        log.error(f"  ✗ 발송 실패 [{to_email}]: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="BRIDGE 개별 메일 발송")
    parser.add_argument("--dry-run", action="store_true", help="실제 발송 없이 테스트")
    parser.add_argument("--recipients", "-r", help="수신자 JSON 파일 경로")
    parser.add_argument("--subject", "-s", help="제목 템플릿 (기본: 테스트)")
    parser.add_argument("--body", "-b", help="본문 템플릿 파일 경로")
    parser.add_argument("--attach", "-a", nargs="*", help="첨부파일 경로들")
    args = parser.parse_args()

    # 수신자 로드
    if args.recipients:
        recipients = json.loads(Path(args.recipients).read_text("utf-8"))
    else:
        recipients = TEST_RECIPIENTS

    # 템플릿
    subject_tpl = args.subject or TEMPLATE_SUBJECT
    if args.body:
        body_tpl = Path(args.body).read_text("utf-8")
    else:
        body_tpl = TEMPLATE_BODY

    # 환경변수 확인
    if not args.dry_run:
        if not SMTP_USER or not SMTP_PASS:
            log.error("환경변수 설정 필요:")
            log.error("  set BRIDGE_SMTP_USER=bridgejobkr@gmail.com")
            log.error("  set BRIDGE_SMTP_PASS=앱비밀번호")
            sys.exit(1)

    log.info("=" * 60)
    log.info(f"BRIDGE 개별 메일 발송 {'[DRY-RUN]' if args.dry_run else '[LIVE]'}")
    log.info(f"수신자: {len(recipients)}명")
    log.info(f"발송 방식: 1:1 개별 (BCC 없음, 타인 미노출)")
    log.info("=" * 60)

    success = 0
    fail = 0
    for i, recipient in enumerate(recipients):
        log.info(f"\n[{i+1}/{len(recipients)}] {recipient['name']} <{recipient['email']}>")
        ok = send_individual_email(
            recipient=recipient,
            subject_template=subject_tpl,
            body_template=body_tpl,
            attachments=args.attach,
            dry_run=args.dry_run,
        )
        if ok:
            success += 1
        else:
            fail += 1
        # Rate limiting — 1초 간격
        if not args.dry_run and i < len(recipients) - 1:
            time.sleep(1)

    log.info("\n" + "=" * 60)
    log.info(f"결과: 성공 {success} / 실패 {fail} / 총 {len(recipients)}")
    log.info("=" * 60)

    # 발송 로그 저장
    log_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "dry-run" if args.dry_run else "live",
        "total": len(recipients),
        "success": success,
        "fail": fail,
        "recipients": [
            {"name": r["name"], "email": r["email"], "status": "sent"}
            for r in recipients
        ],
    }
    log_path = f"mail_log_{time.strftime('%Y%m%d_%H%M%S')}.json"
    Path(log_path).write_text(json.dumps(log_data, ensure_ascii=False, indent=2), "utf-8")
    log.info(f"로그 저장: {log_path}")


if __name__ == "__main__":
    main()
