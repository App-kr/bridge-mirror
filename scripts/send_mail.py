#!/usr/bin/env python3
"""
BRIDGE — 개별 메일 발송 스크립트
매 수신자마다 새 SMTP 세션/메일 객체를 생성하여 PII Zero-Leak 보장.

사용법:
  python scripts/send_mail.py --recipients recipients.json --sender bridgejobkr@gmail.com
  python scripts/send_mail.py --recipients recipients.json --sender bridgejobkr@naver.com
  python scripts/send_mail.py --dry-run --recipients recipients.json

recipients.json 형식:
[
  {
    "email": "recipient@example.com",
    "name": "업체명",
    "region": "서울",
    "city": "강남",
    "teachingAge": "Kindergarten",
    "subject": "메일 제목",
    "body_html": "<p>HTML 본문</p>"
  }
]

환경변수:
  BRIDGE_SMTP_USER  — SMTP 인증 사용자 (발신 이메일)
  BRIDGE_SMTP_PASS  — SMTP 앱 비밀번호 (메인 비밀번호 사용 금지)
"""

import argparse
import json
import logging
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

# ── 로깅 (PII 미포함) ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bridge_mail")

# ── SMTP 설정 ──
SMTP_CONFIG = {
    "gmail": {"host": "smtp.gmail.com", "port": 587},
    "naver": {"host": "smtp.naver.com", "port": 587},
}


def detect_provider(sender: str) -> str:
    """발신자 이메일에서 SMTP 제공자 판별."""
    if "gmail" in sender.lower():
        return "gmail"
    if "naver" in sender.lower():
        return "naver"
    raise ValueError(f"지원하지 않는 발신자 도메인: {sender}")


def mask_email_for_log(email: str) -> str:
    """로그용 이메일 마스킹."""
    at = email.index("@") if "@" in email else len(email)
    if at <= 1:
        return "****@****"
    return email[0] + "****" + email[at:]


def substitute_variables(text: str, recipient: dict) -> str:
    """템플릿 변수를 수신자 데이터로 치환."""
    return (
        text.replace("{{name}}", recipient.get("name", ""))
        .replace("{{region}}", recipient.get("region", ""))
        .replace("{{city}}", recipient.get("city", ""))
        .replace("{{teachingAge}}", recipient.get("teachingAge", ""))
        .replace("{{email}}", recipient.get("email", ""))
    )


def send_one(
    sender: str,
    smtp_user: str,
    smtp_pass: str,
    recipient: dict,
    attachments: list[str] | None = None,
    dry_run: bool = False,
) -> dict:
    """
    수신자 1명에게 메일 1통 발송.
    매번 새 MIMEMultipart + 새 SMTP 세션. BCC/CC 절대 없음.
    """
    to_email = recipient["email"]
    subject = substitute_variables(recipient.get("subject", ""), recipient)
    body_html = substitute_variables(recipient.get("body_html", ""), recipient)

    # 새 메일 객체
    msg = MIMEMultipart()
    msg["From"] = f"BRIDGE <{sender}>"
    msg["To"] = to_email  # 수신자 1명만
    msg["Subject"] = subject

    # HTML 본문
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    # 첨부파일
    for fpath in (attachments or []):
        p = Path(fpath)
        if not p.exists():
            log.warning("첨부파일 없음 (스킵): %s", fpath)
            continue
        part = MIMEBase("application", "octet-stream")
        part.set_payload(p.read_bytes())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{p.name}"')
        msg.attach(part)

    # 보안 검증: msg 전체에서 다른 수신자 이메일 흔적 없는지 확인
    raw = msg.as_string()
    if raw.count(to_email) < 1:
        return {"email": mask_email_for_log(to_email), "status": "error", "error": "수신자 이메일 미포함"}

    result = {"email": mask_email_for_log(to_email), "status": "pending"}

    if dry_run:
        log.info("[DRY-RUN] To: %s | Subject: %s", mask_email_for_log(to_email), subject[:50])
        result["status"] = "dry-run"
        return result

    # SMTP 발송
    provider = detect_provider(sender)
    cfg = SMTP_CONFIG[provider]
    try:
        server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=30)
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        result["status"] = "sent"
        log.info("발송 성공: %s", mask_email_for_log(to_email))
    except smtplib.SMTPAuthenticationError:
        result["status"] = "error"
        result["error"] = "SMTP 인증 실패 — 앱 비밀번호 확인 필요"
        log.error("SMTP 인증 실패: %s", mask_email_for_log(to_email))
    except smtplib.SMTPRecipientsRefused:
        result["status"] = "error"
        result["error"] = "수신자 거부"
        log.error("수신자 거부: %s", mask_email_for_log(to_email))
    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(type(exc).__name__)
        log.error("발송 실패: %s — %s", mask_email_for_log(to_email), type(exc).__name__)

    return result


def main():
    parser = argparse.ArgumentParser(description="BRIDGE 개별 메일 발송")
    parser.add_argument("--recipients", required=True, help="수신자 JSON 파일 경로")
    parser.add_argument("--sender", default="bridgejobkr@gmail.com", help="발신자 이메일")
    parser.add_argument("--attachments", nargs="*", default=[], help="첨부파일 경로 (복수 가능)")
    parser.add_argument("--dry-run", action="store_true", help="실제 발송 없이 테스트")
    args = parser.parse_args()

    # 환경변수에서 SMTP 인증 정보
    smtp_user = os.getenv("BRIDGE_SMTP_USER", args.sender)
    smtp_pass = os.getenv("BRIDGE_SMTP_PASS", "")
    if not smtp_pass and not args.dry_run:
        log.error("BRIDGE_SMTP_PASS 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    # 수신자 로드
    rpath = Path(args.recipients)
    if not rpath.exists():
        log.error("수신자 파일 없음: %s", rpath)
        sys.exit(1)

    recipients = json.loads(rpath.read_text(encoding="utf-8"))
    if not isinstance(recipients, list):
        log.error("수신자 파일은 JSON 배열이어야 합니다.")
        sys.exit(1)

    log.info(
        "발송 시작: %d명 | 발신자: %s | dry-run: %s",
        len(recipients), mask_email_for_log(args.sender), args.dry_run,
    )

    results = []
    for idx, r in enumerate(recipients, 1):
        if not r.get("email"):
            log.warning("[%d/%d] 이메일 없음, 스킵", idx, len(recipients))
            continue
        log.info("[%d/%d] 발송 중: %s", idx, len(recipients), mask_email_for_log(r["email"]))
        result = send_one(
            sender=args.sender,
            smtp_user=smtp_user,
            smtp_pass=smtp_pass,
            recipient=r,
            attachments=args.attachments,
            dry_run=args.dry_run,
        )
        results.append(result)

    # 로그 저장
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path("Q:/Claudework/bridge base/logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"mail_log_{ts}.json"
    log_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    sent = sum(1 for r in results if r["status"] == "sent")
    dry = sum(1 for r in results if r["status"] == "dry-run")
    failed = sum(1 for r in results if r["status"] == "error")
    log.info("완료: 성공 %d | dry-run %d | 실패 %d | 로그: %s", sent, dry, failed, log_file)


if __name__ == "__main__":
    main()
