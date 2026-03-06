"""Insert 6 email templates into master.db."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'master.db')

SIGNATURE = """<br/><hr style="border:none;border-top:1px solid #ddd;margin:24px 0"/>
<p style="font-size:12px;color:#666">
BRIDGE Recruitment<br/>
Business hours 09:30-18:30 KST<br/>
bridgejobkr@gmail.com
</p>
<p style="font-size:11px;color:#999;margin-top:8px">
Unauthorized sharing or disclosure of this email contents is prohibited.
</p>"""

TEMPLATES = [
    # 1. contract_offer
    {
        "key": "contract_offer",
        "subject": "계약서\U0001f4c3BRIDGE - Agreement Attached \U0001f4c3\U0001f4c3계약서 첨부 || {{date}}",
        "body": """<div style="font-family:'Pretendard Variable',sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#1d1d1f">
<p style="color:#dc2626;font-style:italic;font-size:14px;border:1px solid #dc2626;padding:12px;border-radius:8px">
Warning: Please treat all offer details as strictly confidential. Do not share contract terms, salary details, or school information with anyone, including other teachers or online communities.
</p>

<p style="color:#dc2626;text-decoration:underline;font-size:14px;margin-top:16px">
Any details of the offer or contract terms from any school can be completely different for each teacher. Comparing or sharing may cause issues for all parties involved.
</p>

<p style="font-size:15px;margin-top:20px"><strong>Please read the contents once more very carefully.</strong></p>

<p style="font-size:14px;margin-top:16px">
Please fill in your <strong>full legal name</strong> and <strong>educational background</strong> on the contract, then sign and return it.<br/>
Also, please send copies of the following documents:
</p>
<ul style="font-size:14px">
<li>Passport copy (photo page)</li>
<li>ARC copy (front and back, if applicable)</li>
<li>Degree certificate copy</li>
</ul>

<h3 style="color:#eab308;font-size:16px;margin-top:28px">Key Contract Guidance</h3>

<h4 style="font-size:14px;margin-top:20px">Reviewing the Offer</h4>
<ol style="font-size:14px">
<li><strong>Negotiation</strong> - If you want to discuss any terms, do it now, before signing. Once signed, terms are final.</li>
<li><strong>Do Not Rush</strong> - Take time to review. You can ask for 1-2 days to think it over.</li>
<li><strong>Ask Questions in One List</strong> - Collect all your questions and send them together. This is more professional and efficient.</li>
<li><strong>Decided Not to Sign?</strong> - Let us know as soon as possible so we can inform the school promptly.</li>
</ol>

<h4 style="font-size:14px;margin-top:20px">Housing &amp; Final Steps</h4>
<p style="font-size:14px"><strong>Crucial Housing Check</strong> - Confirm housing details (type, location, key money/deposit) before signing. Moving after contract starts is extremely difficult.</p>
<p style="font-size:14px;color:#dc2626">Housing transitions are very hard once you have started at a school. Make sure you are satisfied with the housing arrangement before you sign.</p>

<p style="font-size:14px;margin-top:12px"><strong>Signing Checklist:</strong></p>
<ol style="font-size:14px">
<li>Read every clause carefully</li>
<li>Confirm start date, salary, and working hours</li>
<li>Check housing details and deposit terms</li>
<li>Sign, scan, and return via email</li>
</ol>

<p style="color:#dc2626;font-weight:bold;font-size:13px;margin-top:24px;border-top:1px solid #dc2626;padding-top:12px">
[Confidentiality Notice] This email contains confidential information intended solely for the named recipient. Any unauthorized use, disclosure, or distribution is strictly prohibited.
</p>
""" + SIGNATURE + "</div>",
    },

    # 2. immigration_guide
    {
        "key": "immigration_guide",
        "subject": "채용 확정 후\U0001f60eImmigration Office Appointment & Visa Document Guide 국내 출입국 사무소 방문 및 서류\U0001f60e",
        "body": """<div style="font-family:'Pretendard Variable',sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#1d1d1f">
<p style="font-size:15px">This guide covers the process for changing your visa status (e.g., D-10 to E-2) and the required documents.</p>
<p style="font-size:14px;color:#6b7280">A health check-up is required for visa change. Please schedule it before your immigration appointment.</p>

<h3 style="font-size:16px;margin-top:24px">1. Before Your Immigration Visit</h3>
<ul style="font-size:14px">
<li><strong>Visit before your ARC expires</strong> - do not wait until the last day.</li>
<li>Reference: <a href="{{link_immigration_guide}}" style="color:#2563eb">Immigration Guide</a></li>
<li>Only visit the immigration office that has jurisdiction over your <strong>registered address</strong>.</li>
<li><span style="color:#dc2626">Do NOT go to a random office</span> - they will turn you away.</li>
</ul>

<div style="background:#f0f9ff;border-radius:8px;padding:16px;margin:16px 0;font-size:14px">
<p><strong>From Nov 2025 (MOJ policy change):</strong></p>
<ul>
<li>You must personally make a reservation</li>
<li>Always consult BRIDGE before booking</li>
<li>Book via <a href="https://www.hikorea.go.kr" style="color:#2563eb">HiKorea</a></li>
</ul>
</div>

<p style="font-size:14px"><strong>Documents to prepare:</strong></p>
<ul style="font-size:14px">
<li>Immigration Visa Application form</li>
<li>New housing documents (if address changed)</li>
<li><a href="{{link_tax_document}}" style="color:#2563eb">Tax document</a> from previous employer</li>
<li><a href="{{link_letter_of_release}}" style="color:#2563eb">Letter of Release</a> from previous employer</li>
</ul>
<p style="font-size:14px"><strong>Always message your BRIDGE recruiter first</strong> before visiting immigration.</p>

<h3 style="font-size:16px;margin-top:24px">2. Documents You Must Request Yourself</h3>
<p style="color:#dc2626;font-size:14px">At the Immigration Office, you must personally request:</p>
<ul style="font-size:14px">
<li>Copy of your degree verification (apostilled)</li>
<li>Copy of your criminal background check</li>
<li><a href="{{link_obtain_copy}}" style="color:#2563eb">How can I obtain a copy?</a></li>
</ul>
<p style="font-size:14px">If you have family members, prepare 1345 documents as well.</p>

<h3 style="font-size:16px;margin-top:24px">3. Reservation Information</h3>
<p style="font-size:14px">You can reschedule if needed. <strong>Do NOT show up without a reservation</strong> (walk-ins are not accepted at most offices).</p>

<h3 style="font-size:16px;margin-top:24px">4. Who Must Visit</h3>
<p style="font-size:14px">If you <strong>do not have an ARC</strong>, you must visit in person.<br/>Do not visit earlier than your scheduled date.</p>

<h3 style="font-size:16px;margin-top:24px">5. Health Check-up</h3>
<p style="font-size:14px"><a href="{{link_health_exam}}" style="color:#2563eb">Medical Check-up for E2/F-visas</a></p>
""" + SIGNATURE + "</div>",
    },

    # 3. overseas_visa_prep
    {
        "key": "overseas_visa_prep",
        "subject": "해외거주 Bridge alarm ! prepare after sending the documents to Korea. 영사준비",
        "body": """<div style="font-family:'Pretendard Variable',sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#1d1d1f">
<p style="font-size:15px">Visa documents have been submitted. Please review the following carefully.</p>
<p style="font-size:14px">Reference: <a href="{{link_after_visa_submitted}}" style="color:#2563eb">After visa documents are submitted</a></p>

<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;padding:16px;margin:20px 0">
<p style="color:#dc2626;font-weight:bold;font-style:italic;font-size:14px">
WARNING: If you do not currently hold a valid work visa, you MUST leave Korea to obtain one. This typically involves traveling to Japan, the US, or your home country to apply at a Korean consulate. The process takes 5-20+ business days.
</p>
</div>

<p style="font-weight:bold;font-style:italic;font-size:14px;margin-top:16px">
After VIN approval (5-14 business days), you must personally visit a Korean consulate abroad. Once your E-visa is approved, you can re-enter Korea and begin work.
</p>

<h3 style="font-size:16px;margin-top:24px">Steps to Follow</h3>
<ol style="font-size:14px">
<li>Wait for VIN approval notification from BRIDGE</li>
<li>Call the Korean consulate in your destination country</li>
<li>Prepare all required documents (passport, photos, VIN number, etc.)</li>
<li>Submit documents at the consulate (some accept expedited/mail applications)</li>
<li>Receive E-2 visa sticker in your passport</li>
<li>Book return flight to Korea</li>
</ol>
""" + SIGNATURE + "</div>",
    },

    # 4. job_transition_guide
    {
        "key": "job_transition_guide",
        "subject": "BRIDGE Job Transition Guide - Final guide / BRIDGE 이직가이드 최종",
        "body": """<div style="font-family:'Pretendard Variable',sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#1d1d1f">
<h2 style="font-size:20px;margin-bottom:20px">BRIDGE Job Transition Guide</h2>

<h3 style="font-size:16px;margin-top:20px">1. Medical Check-up (E2 Visa)</h3>
<p style="font-size:14px">A fasting blood test is required. Schedule your medical exam <strong>after</strong> you have moved to your new school area. Most hospitals require same-day fasting.</p>

<h3 style="font-size:16px;margin-top:20px">2. Immigration Office Appointment</h3>
<p style="font-size:14px">Visit the immigration office with jurisdiction over your <strong>new registered address</strong>. Call 1345 (English available, press 5) for guidance.</p>

<h3 style="font-size:16px;margin-top:20px">3. Tax Documents</h3>
<p style="font-size:14px">Request your withholding tax receipt from your previous employer. If they do not provide it, you can visit the local tax office directly.</p>

<h3 style="font-size:16px;margin-top:20px">4. Immigration or Hospital Visit</h3>
<p style="font-size:14px">Depending on your situation, you or your school manager may need to visit. Confirm who will go with your BRIDGE recruiter.</p>

<h3 style="font-size:16px;margin-top:20px">5. Moving</h3>
<p style="font-size:14px">If you do not have housing information yet, contact your recruiter immediately. Allow 4 weeks to 3 months for adjustment.</p>

<p style="font-size:14px;margin-top:24px;font-weight:600">
Recruiter, {{recruiter_name}}<br/>BRIDGE
</p>
""" + SIGNATURE + "</div>",
    },

    # 5. arrival_guide
    {
        "key": "arrival_guide",
        "subject": "해외 입국 후 기본 가이드 After entering Korea from abroad, what you need to do to obtain an ARC card",
        "body": """<div style="font-family:'Pretendard Variable',sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#1d1d1f">
<p style="font-size:15px">Whether this is your first time in Korea or you have prior experience, please review the following guides carefully.</p>

<div style="background:#f0f9ff;border-radius:12px;padding:20px;margin:20px 0">
<h3 style="font-size:16px;margin-bottom:12px">Essential Guides</h3>
<ul style="font-size:14px;line-height:2">
<li><a href="{{link_basic_things}}" style="color:#2563eb;font-weight:600">BASIC THINGS TO DO</a></li>
<li><a href="{{link_medical_check}}" style="color:#2563eb;font-weight:600">Medical check</a></li>
<li><a href="{{link_immigration_office_visit}}" style="color:#2563eb;font-weight:600">Things to do when visiting the Immigration Office</a></li>
<li><a href="{{link_experience_working}}" style="color:#2563eb;font-weight:600">Have experience working in Korea</a></li>
</ul>
</div>

<p style="font-size:14px">If you have any questions, please contact your BRIDGE recruiter immediately.</p>
""" + SIGNATURE + "</div>",
    },

    # 6. candidate_profile
    {
        "key": "candidate_profile",
        "subject": "안녕하세요, BRIDGE 원어민 강사 프로필을 공유드립니다.",
        "body": """<div style="font-family:'Pretendard Variable',sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#1d1d1f">
<p style="font-size:15px">안녕하세요, BRIDGE 원어민 강사 프로필을 공유드립니다.</p>
<p style="font-size:14px;color:#6b7280">Start date and preferences noted. Reference provided for review only.</p>

<hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0"/>

{{profile_cards}}

<hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0"/>
<p style="font-size:14px">위 후보자에 대해 검토 후 인터뷰 의향이 있으시면 회신 부탁드립니다.</p>

<p style="font-size:12px;color:#999;margin-top:16px">
WARNING: 개인정보 보호 - 프로필에는 이름, 이메일, 전화번호, 카카오톡, 주소가 포함되어 있지 않습니다.
ID번호 + 국적 + 사진으로 식별하며, 이름은 인터뷰 확정 후 별도 공유됩니다.
</p>
""" + SIGNATURE + "</div>",
    },
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout = 5000")

    for t in TEMPLATES:
        conn.execute(
            """INSERT OR REPLACE INTO email_templates (template_key, subject, body_html, updated_at)
               VALUES (?, ?, ?, datetime('now'))""",
            (t["key"], t["subject"], t["body"]),
        )
        print(f"+ {t['key']}")

    conn.commit()
    cnt = conn.execute("SELECT COUNT(*) FROM email_templates").fetchone()[0]
    print(f"\nTotal templates: {cnt}")
    conn.close()


if __name__ == "__main__":
    main()
