"""
BRIDGE Email Templates & Sender
================================
확인 이메일 발송 — api_server._smtp_send() 위임
구직자: English / 구인자: Korean

SMTP 설정은 .env의 BRIDGE_SMTP_USER / BRIDGE_SMTP_PASS 사용.
이 파일은 템플릿만 관리. 실제 발송은 api_server._smtp_send() 단일 경로.
"""

import os
import ssl
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

log = logging.getLogger("bridge.email")

# SMTP 설정 — api_server.py와 동일 우선순위 체인
_SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
_SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
_SMTP_USER = os.getenv("BRIDGE_SMTP_USER", os.getenv("SMTP_USER", os.getenv("GMAIL_USER", "")))
_SMTP_PASS = os.getenv("BRIDGE_SMTP_PASS", os.getenv("SMTP_PASS", os.getenv("GMAIL_APP_PASSWORD", "")))


def _send_email(to: str, subject: str, html_body: str) -> bool:
    """Gmail SMTP로 이메일 발송. 실패 시 False 반환 (예외 미전파).
    SECURITY: CC/BCC 없음, Reply-To bridgejobkr@gmail.com 고정."""
    if not _SMTP_USER or not _SMTP_PASS:
        log.warning("SMTP 미설정 — 이메일 발송 스킵 (to=%s)", to)
        return False

    try:
        msg = MIMEMultipart("alternative")
        # SECURITY: From/Reply-To 고정
        msg["From"] = f"BRIDGE <{_SMTP_USER}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg["Reply-To"] = "bridgejobkr@gmail.com"
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        ctx = ssl.create_default_context()
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
            server.login(_SMTP_USER, _SMTP_PASS)
            # SECURITY: 수신자 1명만 전달
            server.sendmail(_SMTP_USER, [to], msg.as_string())

        log.info("이메일 발송 성공: %s → %s", subject, to)
        return True

    except Exception as e:
        log.error("이메일 발송 실패 (to=%s): %s", to, e, exc_info=True)
        return False


# ── 구직자 확인 이메일 (English) ─────────────────────────────────────────────

def send_applicant_confirmation(to_email: str, full_name: str) -> bool:
    """구직자 지원 접수 확인 이메일 (English) — Claude.ai 확정 템플릿"""
    subject = f"{full_name}, your application has been received!"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; line-height: 1.7;">
      <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #1d1d1f;">
        <h1 style="margin: 0; font-size: 24px; color: #1d1d1f; font-weight: 700;">BRIDGE</h1>
      </div>

      <div style="padding: 30px 0;">
        <p>Dear {full_name},</p>

        <p>Thank you for reaching out to us! We have received your application.
        Our team is now carefully reviewing your documents.</p>

        <p>If any files (CV, photos, or intro video) were missed in the initial form,
        feel free to reply to this email and attach them.</p>

        <div style="background: #f5f5f7; padding: 20px; margin: 24px 0; border-radius: 12px;">
          <p style="margin: 0 0 12px; font-weight: 600; color: #1d1d1f;">채용 절차</p>
          <ul style="margin: 0; padding-left: 20px; color: #424245; line-height: 1.9;">
            <li><strong>매칭 상담:</strong> 카카오톡을 통해 상세 조건 확인 및 인재 매칭</li>
            <li><strong>정보 제공:</strong> 채용 시장 동향 소식지 발송</li>
            <li><strong>인터뷰:</strong> 접수해주신 연락처(카카오톡)으로 의사소통 및 이메일로 Google Meet 인터뷰 링크 전송</li>
          </ul>
        </div>

        <p>틀린 정보가 있다면 이 이메일로 회신주세요.</p>

        <p style="color: #6e6e73; margin-top: 30px;">
          Warm regards,<br>
          <strong>BRIDGE Team</strong>
        </p>
      </div>

      <div style="border-top: 1px solid #e5e7eb; padding-top: 16px; text-align: center; font-size: 12px; color: #86868b;">
        <p>The BRIDGE Team · <a href="https://bridgejob.co.kr" style="color: #0071e3;">bridgejob.co.kr</a></p>
      </div>
    </body>
    </html>
    """
    return _send_email(to_email, subject, html)


# ── 인터뷰 초대 이메일 (English — 구직자용) ──────────────────────────────────

def send_interview_invitation(
    to_email: str,
    name: str,
    interview_date: str,
    interview_time: str,
    meet_link: str,
    employer_name: str = "",
) -> bool:
    """인터뷰 초대 이메일 (English) — Google Meet 링크 포함"""
    subject = f"Interview Scheduled — {interview_date} at {interview_time}"
    school_info = f" with <strong>{employer_name}</strong>" if employer_name else ""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; line-height: 1.7;">
      <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #1d1d1f;">
        <h1 style="margin: 0; font-size: 24px; color: #1d1d1f; font-weight: 700;">BRIDGE</h1>
      </div>

      <div style="padding: 30px 0;">
        <p>Dear {name},</p>

        <p>Great news! Your interview{school_info} has been scheduled.</p>

        <div style="background: #f0fdf4; border: 1px solid #86efac; padding: 20px; margin: 24px 0; border-radius: 12px; text-align: center;">
          <p style="margin: 0 0 8px; font-size: 18px; font-weight: 700; color: #166534;">
            {interview_date} at {interview_time} (KST)
          </p>
          <a href="{meet_link}" style="display: inline-block; background: #1d1d1f; color: #fff; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 12px;">
            Join Google Meet
          </a>
          <p style="margin: 12px 0 0; font-size: 12px; color: #6b7280;">
            Link: <a href="{meet_link}" style="color: #0071e3;">{meet_link}</a>
          </p>
        </div>

        <div style="background: #f5f5f7; padding: 20px; margin: 24px 0; border-radius: 12px;">
          <p style="margin: 0 0 12px; font-weight: 600; color: #1d1d1f;">Before the Interview</p>
          <ul style="margin: 0; padding-left: 20px; color: #424245; line-height: 1.9;">
            <li>Test your camera and microphone beforehand</li>
            <li>Find a quiet, well-lit space</li>
            <li>Dress professionally (business casual or above)</li>
            <li>Have your resume and any documents ready</li>
            <li>Join the meeting 2-3 minutes early</li>
          </ul>
        </div>

        <p>If you need to reschedule, please reply to this email as soon as possible.</p>

        <p style="color: #6e6e73; margin-top: 30px;">
          Good luck!<br>
          <strong>BRIDGE Team</strong>
        </p>
      </div>

      <div style="border-top: 1px solid #e5e7eb; padding-top: 16px; text-align: center; font-size: 12px; color: #86868b;">
        <p>The BRIDGE Team &middot; <a href="https://bridgejob.co.kr" style="color: #0071e3;">bridgejob.co.kr</a></p>
      </div>
    </body>
    </html>
    """
    return _send_email(to_email, subject, html)


# ── 인터뷰 초대 이메일 (Korean — 구인자용) ───────────────────────────────────

def send_interview_invitation_employer(
    to_email: str,
    contact_name: str,
    interview_date: str,
    interview_time: str,
    meet_link: str,
    candidate_name: str = "",
) -> bool:
    """인터뷰 초대 이메일 (Korean) — 구인자에게 Google Meet 링크 발송"""
    name_display = contact_name if contact_name else "담당자"
    candidate_info = f" — 후보자: <strong>{candidate_name}</strong>" if candidate_name else ""
    subject = f"인터뷰 일정 안내 — {interview_date} {interview_time}"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, 'Segoe UI', 'Malgun Gothic', sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; line-height: 1.7;">
      <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #1d1d1f;">
        <h1 style="margin: 0; font-size: 24px; color: #1d1d1f; font-weight: 700;">BRIDGE</h1>
      </div>

      <div style="padding: 30px 0;">
        <p>안녕하세요, {name_display}님</p>

        <p>인터뷰 일정이 확정되었습니다{candidate_info}.</p>

        <div style="background: #f0fdf4; border: 1px solid #86efac; padding: 20px; margin: 24px 0; border-radius: 12px; text-align: center;">
          <p style="margin: 0 0 8px; font-size: 18px; font-weight: 700; color: #166534;">
            {interview_date} {interview_time} (한국시간)
          </p>
          <a href="{meet_link}" style="display: inline-block; background: #1d1d1f; color: #fff; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 12px;">
            Google Meet 입장
          </a>
          <p style="margin: 12px 0 0; font-size: 12px; color: #6b7280;">
            링크: <a href="{meet_link}" style="color: #0071e3;">{meet_link}</a>
          </p>
        </div>

        <p>일정 변경이 필요하시면 이 이메일로 회신해 주세요.</p>

        <p style="color: #6e6e73; margin-top: 30px;">
          감사합니다.<br>
          <strong>BRIDGE Team 드림</strong>
        </p>
      </div>

      <div style="border-top: 1px solid #e5e7eb; padding-top: 16px; text-align: center; font-size: 12px; color: #86868b;">
        <p>The BRIDGE Team &middot; <a href="https://bridgejob.co.kr" style="color: #0071e3;">bridgejob.co.kr</a></p>
      </div>
    </body>
    </html>
    """
    return _send_email(to_email, subject, html)


# ── 구인자 확인 이메일 (Korean) ──────────────────────────────────────────────

def send_employer_confirmation(to_email: str, school_name: str, contact_name: str = "") -> bool:
    """구인자 채용 문의 접수 확인 이메일 (Korean) — Claude.ai 확정 템플릿"""
    name_display = contact_name if contact_name else "담당자"
    subject = f"{name_display}님, BRIDGE 채용 신청이 완료되었습니다."
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, 'Segoe UI', 'Malgun Gothic', sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; line-height: 1.7;">
      <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #1d1d1f;">
        <h1 style="margin: 0; font-size: 24px; color: #1d1d1f; font-weight: 700;">BRIDGE</h1>
      </div>

      <div style="padding: 30px 0;">
        <p>안녕하세요, {name_display}님</p>

        <p>귀하의 BRIDGE 원어민 채용 신청서가 접수되었습니다.</p>

        <div style="background: #f5f5f7; padding: 20px; margin: 24px 0; border-radius: 12px;">
          <p style="margin: 0 0 12px; font-weight: 600; color: #1d1d1f;">채용 절차</p>
          <ul style="margin: 0; padding-left: 20px; color: #424245; line-height: 1.9;">
            <li><strong>매칭 상담:</strong> 카카오톡을 통해 상세 조건 확인 및 인재 매칭</li>
            <li><strong>정보 제공:</strong> 채용 시장 동향 소식지 발송</li>
            <li><strong>인터뷰:</strong> 접수해주신 연락처(카카오톡)으로 의사소통 및 이메일로 인터뷰 링크 전송</li>
          </ul>
        </div>

        <p>틀린 정보가 있다면 이 이메일로 회신주세요.</p>

        <div style="background: #fef3c7; border: 1px solid #fbbf24; padding: 16px 20px; margin: 24px 0; border-radius: 12px;">
          <p style="margin: 0; font-weight: 600; color: #92400e; font-size: 13px;">⚠️ 유의사항</p>
          <p style="margin: 8px 0 0; color: #78350f; font-size: 13px; line-height: 1.7;">
            불투명한 중개 경로를 통한 피해 사례가 보고되고 있습니다.
            모든 공식 절차는 BRIDGE Team 안내에 따라 진행하시기 바랍니다.
          </p>
        </div>

        <p style="color: #6e6e73; margin-top: 30px;">
          감사합니다.<br>
          <strong>BRIDGE Team 드림</strong>
        </p>
      </div>

      <div style="border-top: 1px solid #e5e7eb; padding-top: 16px; text-align: center; font-size: 12px; color: #86868b;">
        <p>The BRIDGE Team · <a href="https://bridgejob.co.kr" style="color: #0071e3;">bridgejob.co.kr</a></p>
      </div>
    </body>
    </html>
    """
    return _send_email(to_email, subject, html)


# ── 새 채용의뢰 접수 → 관리자 알림 ──────────────────────────────────────────

def send_new_job_pending_alert(admin_email: str, school_name: str, inquiry_id: int, job_code: str) -> bool:
    """새 채용의뢰 접수 시 관리자에게 검토 요청 이메일"""
    subject = f"[BRIDGE] 새 채용의뢰 접수 — {school_name} 검토 필요"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, 'Segoe UI', 'Malgun Gothic', sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; line-height: 1.7;">
      <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #1d1d1f;">
        <h1 style="margin: 0; font-size: 24px; color: #1d1d1f; font-weight: 700;">BRIDGE</h1>
        <p style="margin: 4px 0 0; font-size: 13px; color: #6e6e73;">Admin Notification</p>
      </div>
      <div style="padding: 30px 0;">
        <p>새 채용의뢰가 접수되었습니다. 검토 후 승인해주세요.</p>
        <div style="background: #f0f9ff; border-left: 4px solid #0071e3; padding: 16px 20px; margin: 20px 0; border-radius: 0 8px 8px 0;">
          <p style="margin: 0 0 8px; font-weight: 600; color: #1d1d1f;">접수 정보</p>
          <p style="margin: 0; font-size: 14px; color: #374151;">
            학교명: <strong>{school_name}</strong><br>
            문의 ID: #{inquiry_id}<br>
            공고 코드: {job_code}<br>
            상태: <span style="color: #d97706; font-weight: 600;">검토 대기 (pending_review)</span>
          </p>
        </div>
        <a href="https://bridge-chi-lime.vercel.app/admin/jobs?status=pending_review"
           style="display: inline-block; background: #1d1d1f; color: #fff; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; margin-top: 8px;">
          어드민에서 검토하기 →
        </a>
      </div>
      <div style="border-top: 1px solid #e5e7eb; padding-top: 16px; text-align: center; font-size: 12px; color: #86868b;">
        <p>The BRIDGE Team · <a href="https://bridgejob.co.kr" style="color: #0071e3;">bridgejob.co.kr</a></p>
      </div>
    </body>
    </html>
    """
    return _send_email(admin_email, subject, html)
