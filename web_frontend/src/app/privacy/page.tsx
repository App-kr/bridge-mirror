import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Privacy Policy | BRIDGE Recruitment',
  description: 'BRIDGE Recruitment privacy policy — Korean PIPA compliant, international data protection.',
}

export default function PrivacyPage() {
  return (
    <div className="max-w-[860px] mx-auto px-4 sm:px-6 py-12 text-[#1d1d1f]">

      {/* Header */}
      <div className="mb-10 pb-6 border-b border-gray-200">
        <h1 className="text-3xl font-bold mb-1">Privacy Policy</h1>
        <p className="text-sm text-gray-500">개인정보 처리방침 &nbsp;|&nbsp; Last updated: April 2026 &nbsp;|&nbsp; Version 1.0</p>
        <p className="mt-3 text-sm text-gray-600 leading-relaxed">
          BRIDGE Recruitment (&ldquo;BRIDGE&rdquo;, &ldquo;Company&rdquo;, &ldquo;we&rdquo;) operates{' '}
          <strong>bridgejob.co.kr</strong> — a Korea-based ESL teacher recruitment platform.
          This Privacy Policy explains how we collect, use, retain, and protect your personal information,
          and describes your rights under applicable law. This policy applies to all users of our website
          and services, including job applicants and school/employer clients.
        </p>
        <p className="mt-3 text-sm text-gray-600 leading-relaxed">
          본 개인정보 처리방침은 「개인정보 보호법」 제30조에 따라 정보주체의 개인정보를 보호하고
          이와 관련한 고충을 신속하고 원활하게 처리하기 위하여 작성되었습니다.
        </p>
      </div>

      {/* ── PART 1: KOREAN LAW (PIPA) ── */}
      <SectionHeader>Part 1 — 한국 개인정보보호법 (Korean PIPA)</SectionHeader>

      <Article num="제1조" title="개인정보의 처리 목적 및 수집 항목">
        <p>BRIDGE는 다음의 목적으로 개인정보를 처리합니다. 처리한 개인정보는 다음의 목적 이외의 용도로는 이용되지 않으며 이용 목적이 변경될 경우에는 별도의 동의를 받는 등 필요한 조치를 이행할 예정입니다.</p>

        <Table headers={['목적', '수집 항목', '보유 기간']}>
          <tr>
            <td>강사 채용 서비스 제공</td>
            <td>성명, 생년월일, 성별, 국적, 거주국, 여권번호, 이메일, 전화번호, 카카오톡 ID, 학력, 경력, 자격증, 비자 정보, 범죄경력조회 결과, 사진, 이력서, 자기소개서</td>
            <td>채용 완료 후 3년 (법령 의무 보유)</td>
          </tr>
          <tr>
            <td>구인 학교 서비스 제공</td>
            <td>학교명, 담당자 성명, 이메일, 전화번호, 사업자등록번호, 구인 요건</td>
            <td>계약 종료 후 3년</td>
          </tr>
          <tr>
            <td>서비스 부정이용 방지 및 법적 분쟁 대응</td>
            <td>접속 IP, 접속 일시, 서비스 이용 기록</td>
            <td>3개월 (통신비밀보호법)</td>
          </tr>
        </Table>

        <Notice>
          채용 및 비자 관련 법령(「출입국관리법」, 「근로기준법」 등)에 따라 일부 기록은
          위 기간 이후에도 추가 보유될 수 있습니다. 이 경우 해당 법령의 근거와 보유 기간을
          별도로 고지합니다.
        </Notice>
      </Article>

      <Article num="제2조" title="개인정보의 처리 및 보유 기간">
        <p>BRIDGE는 법령에 따른 개인정보 보유·이용기간 또는 정보주체로부터 개인정보를 수집 시에 동의 받은 개인정보 보유·이용기간 내에서 개인정보를 처리·보유합니다.</p>

        <Table headers={['관련 법령', '보유 항목', '보유 기간']}>
          <tr>
            <td>출입국관리법 / 고용허가제</td>
            <td>외국인 강사 계약·비자 관련 기록</td>
            <td>계약 종료 후 3년</td>
          </tr>
          <tr>
            <td>근로기준법 제42조</td>
            <td>근로자명부, 계약 서류</td>
            <td>3년</td>
          </tr>
          <tr>
            <td>국세기본법 제85조의3</td>
            <td>세금계산서, 거래 기록</td>
            <td>5년</td>
          </tr>
          <tr>
            <td>전자상거래법 제6조</td>
            <td>계약·청약 기록, 대금결제 기록</td>
            <td>5년</td>
          </tr>
          <tr>
            <td>통신비밀보호법 제15조의2</td>
            <td>접속 로그, IP 기록</td>
            <td>3개월</td>
          </tr>
          <tr>
            <td>개인정보보호법 제39조의6</td>
            <td>이용자 불만·분쟁 처리 기록</td>
            <td>3년</td>
          </tr>
        </Table>

        <p className="mt-3">위 법령에 해당하지 않는 개인정보는 서비스 이용 목적 달성(채용 완료, 서비스 해지, 계약 종료) 시 지체 없이 파기합니다.</p>
      </Article>

      <Article num="제3조" title="개인정보의 제3자 제공">
        <p>BRIDGE는 정보주체의 개인정보를 수집 목적 범위 내에서만 처리하며, 다음의 경우에 한하여 제3자에게 제공합니다.</p>

        <Table headers={['제공받는 자', '제공 목적', '제공 항목', '보유·이용 기간']}>
          <tr>
            <td>채용 구인 학교·기관</td>
            <td>강사 채용 및 근로계약 체결</td>
            <td>성명, 국적, 비자 종류, 학력, 경력, 자격증 (정보주체 동의 항목)</td>
            <td>채용 목적 달성 시까지</td>
          </tr>
          <tr>
            <td>정부 기관 (법원, 수사기관 등)</td>
            <td>법령에 따른 제출 요구</td>
            <td>요청 항목</td>
            <td>해당 법령에서 정한 기간</td>
          </tr>
        </Table>

        <p className="mt-3">위의 경우 외에는 정보주체의 동의 없이 개인정보를 제3자에게 제공하지 않습니다.</p>
      </Article>

      <Article num="제4조" title="개인정보 처리의 위탁">
        <p>BRIDGE는 서비스 이행을 위하여 아래와 같이 개인정보 처리 업무를 위탁합니다.</p>

        <Table headers={['수탁업체', '위탁 업무', '보유 기간']}>
          <tr>
            <td>Amazon Web Services (AWS)</td>
            <td>파일 저장 (이력서, 사진) — S3</td>
            <td>위탁 계약 종료 시까지</td>
          </tr>
          <tr>
            <td>Render Inc.</td>
            <td>서버 운영 및 데이터베이스 호스팅</td>
            <td>위탁 계약 종료 시까지</td>
          </tr>
          <tr>
            <td>Vercel Inc.</td>
            <td>웹 프론트엔드 서비스 제공</td>
            <td>위탁 계약 종료 시까지</td>
          </tr>
        </Table>

        <p className="mt-3">위탁업체에 대해서는 개인정보보호 관련 법규의 준수, 개인정보에 관한 비밀유지, 제3자 제공 금지 및 사고 시 즉각 보고·조치 등을 계약서에 명시합니다.</p>
      </Article>

      <Article num="제5조" title="정보주체의 권리·의무 및 행사 방법">
        <p>정보주체는 BRIDGE에 대해 언제든지 다음의 권리를 행사할 수 있습니다.</p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>개인정보 열람 요구</li>
          <li>오류 등이 있을 경우 정정 요구</li>
          <li>삭제 요구 (단, 법령에 의한 보유 의무가 있는 경우 거부될 수 있음)</li>
          <li>처리 정지 요구</li>
        </ul>
        <p className="mt-3">위의 권리 행사는 이메일(<a href="mailto:bridgejobkr@gmail.com" className="text-blue-600 underline">bridgejobkr@gmail.com</a>)을 통하여 하실 수 있으며 BRIDGE는 요청일로부터 <strong>10일 이내</strong>에 처리 결과를 회신합니다.</p>
        <p className="mt-3">권리 행사 요청 시 본인 확인을 위한 신분증 사본 제출을 요청할 수 있습니다. 법정대리인이 행사하는 경우 위임장을 제출하여야 합니다.</p>

        <Notice>
          비자·취업 법령에 따른 보유 의무가 있는 경우, 삭제 및 처리 정지 요구가 거절될 수 있습니다.
          이 경우 해당 법령의 구체적 근거를 이메일로 안내해 드립니다.
          (「개인정보 보호법」 제37조 제2항)
        </Notice>
      </Article>

      <Article num="제6조" title="개인정보의 파기 절차 및 방법">
        <p>BRIDGE는 보유 기간이 경과하거나 처리 목적이 달성된 개인정보는 지체 없이 파기합니다.</p>
        <ul className="list-disc pl-5 mt-2 space-y-2">
          <li><strong>전자적 파일 형태</strong>: 복원이 불가능한 방법으로 영구 삭제 (AES-256 암호화 키 파기 포함)</li>
          <li><strong>종이 문서</strong>: 분쇄기 파쇄 또는 소각</li>
        </ul>
        <p className="mt-3">보유 기간이 경과하였음에도 법령에 따라 보존이 필요한 경우에는 해당 개인정보를 별도 데이터베이스로 분리하여 저장·관리합니다.</p>
      </Article>

      <Article num="제7조" title="개인정보의 안전성 확보 조치">
        <p>BRIDGE는 「개인정보 보호법」 제29조에 따라 다음과 같은 안전성 확보 조치를 취하고 있습니다.</p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>개인정보에 대한 접근 권한 최소화 — 권한 있는 담당자만 접근 가능</li>
          <li>개인정보 저장 시 AES-256 암호화 적용</li>
          <li>전송 시 TLS/HTTPS 암호화 적용</li>
          <li>접속 기록 보관 및 위·변조 방지 조치</li>
          <li>해킹·악성코드 등 침해사고 방지를 위한 정기 보안 점검</li>
          <li>비밀번호 단방향 암호화(PBKDF2) 저장</li>
        </ul>
      </Article>

      <Article num="제8조" title="쿠키(Cookie)의 운용">
        <p>BRIDGE는 이용자에게 개별적인 맞춤 서비스를 제공하기 위해 이용 정보를 저장하고 수시로 불러오는 쿠키(cookie)를 사용합니다.</p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li><strong>사용 목적</strong>: 로그인 세션 유지, 서비스 이용 현황 파악, 보안(CSRF 방지)</li>
          <li><strong>저장 기간</strong>: 세션 쿠키(브라우저 종료 시 자동 삭제) 및 영속 쿠키(최대 7일)</li>
          <li><strong>거부 방법</strong>: 브라우저 설정 &gt; 쿠키 차단 (단, 일부 서비스 이용이 제한될 수 있음)</li>
        </ul>
      </Article>

      <Article num="제9조" title="개인정보보호책임자 및 고충처리">
        <p>BRIDGE는 개인정보 처리에 관한 업무를 총괄해서 책임지고, 정보주체의 불만처리 및 피해구제 등을 위하여 아래와 같이 개인정보보호책임자를 지정하고 있습니다.</p>

        <div className="mt-3 p-4 bg-gray-50 rounded-lg border border-gray-200 text-sm space-y-1">
          <p><strong>개인정보보호책임자 (Privacy Officer)</strong></p>
          <p>소속/직책: BRIDGE Recruitment 대표</p>
          <p>이메일: <a href="mailto:bridgejobkr@gmail.com" className="text-blue-600 underline">bridgejobkr@gmail.com</a></p>
          <p>처리 기한: 접수 후 10일 이내</p>
        </div>

        <p className="mt-4">정보주체는 BRIDGE의 서비스를 이용하시면서 발생한 모든 개인정보보호 관련 문의, 불만처리, 피해구제 등에 관한 사항을 개인정보보호책임자에게 문의하실 수 있습니다.</p>
      </Article>

      <Article num="제10조" title="권익 침해 구제 방법">
        <p>정보주체는 아래 기관에 대해 개인정보 침해에 대한 신고 또는 상담을 신청할 수 있습니다.</p>

        <Table headers={['기관', '연락처 / 주소']}>
          <tr>
            <td><strong>개인정보보호위원회</strong> (Personal Information Protection Commission)</td>
            <td>privacy.go.kr &nbsp;|&nbsp; 국번없이 182</td>
          </tr>
          <tr>
            <td><strong>한국인터넷진흥원 개인정보침해신고센터</strong> (KISA)</td>
            <td>privacy.kisa.or.kr &nbsp;|&nbsp; 국번없이 118</td>
          </tr>
          <tr>
            <td><strong>대검찰청 사이버범죄수사단</strong></td>
            <td>spo.go.kr &nbsp;|&nbsp; 02-3480-3573</td>
          </tr>
          <tr>
            <td><strong>경찰청 사이버안전국</strong></td>
            <td>cyberbureau.police.go.kr &nbsp;|&nbsp; 국번없이 182</td>
          </tr>
        </Table>
      </Article>

      {/* ── PART 2: INTERNATIONAL ── */}
      <div className="mt-12">
        <SectionHeader>Part 2 — International Data Protection</SectionHeader>
      </div>

      <Article num="§11" title="Who We Are & Contact">
        <p>
          BRIDGE Recruitment is a Korea-based company operating under Korean law. Our primary data protection
          obligation is to the Korean Personal Information Protection Act (PIPA / 개인정보보호법).
          In addition, where applicable, we comply with the data protection laws of our applicants&rsquo;
          countries of residence, as described in this Part 2.
        </p>
        <p className="mt-3">
          Contact for all data requests:{' '}
          <a href="mailto:bridgejobkr@gmail.com" className="text-blue-600 underline">bridgejobkr@gmail.com</a>
          &nbsp;— We respond within 10 business days (Korean law) or 30 days (where GDPR/UK GDPR applies).
        </p>
      </Article>

      <Article num="§12" title="Data We Collect">
        <p>In the course of providing recruitment services, we may collect the following categories of personal data:</p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li><strong>Identity data</strong>: full name, date of birth, gender, nationality, passport details</li>
          <li><strong>Contact data</strong>: email address, phone number, KakaoTalk ID, country of residence</li>
          <li><strong>Professional data</strong>: educational background, teaching certifications, employment history, CV, cover letter</li>
          <li><strong>Compliance data</strong>: visa status, criminal record check results (home country and Korean)</li>
          <li><strong>Preference data</strong>: preferred teaching region, school type, start date, housing/family requirements</li>
          <li><strong>Media</strong>: profile photo, self-introduction video</li>
          <li><strong>Technical data</strong>: IP address, browser type, access logs (retained 3 months per Korean law)</li>
        </ul>
        <p className="mt-3">We do not collect special category data beyond what is required by Korean immigration and employment law (e.g., criminal records required for E-2 visa processing).</p>
      </Article>

      <Article num="§13" title="Legal Basis for Processing">
        <Table headers={['Purpose', 'Legal Basis']}>
          <tr>
            <td>Matching applicants with teaching positions</td>
            <td>Performance of contract (pre-contractual steps at applicant&rsquo;s request)</td>
          </tr>
          <tr>
            <td>Visa and immigration document handling</td>
            <td>Legal obligation (Korean Immigration Act, E-2 visa requirements)</td>
          </tr>
          <tr>
            <td>Maintaining recruitment records</td>
            <td>Legal obligation (Labour Standards Act, National Tax Act) + Legitimate interests</td>
          </tr>
          <tr>
            <td>Resolving disputes or legal claims</td>
            <td>Legitimate interests</td>
          </tr>
          <tr>
            <td>Service communications</td>
            <td>Performance of contract</td>
          </tr>
        </Table>
      </Article>

      <Article num="§14" title="Data Retention">
        <p>
          Personal data is retained for a <strong>minimum of three (3) years</strong> following the conclusion
          of your recruitment process (whether placement, withdrawal, or rejection). This retention period
          reflects our obligations under Korean law, including the Labour Standards Act (근로기준법), the
          Immigration Control Act (출입국관리법), and related E-2 visa regulations.
        </p>
        <p className="mt-3">
          <strong>Effect on deletion requests:</strong> You may request deletion of your personal data at any
          time. However, deletion requests may be declined where retention is required by the above-mentioned
          Korean statutes. In such cases, we will inform you of the specific legal basis and the applicable
          retention period.
        </p>
        <p className="mt-3">
          Upon expiry of all applicable retention periods, data is securely destroyed (permanent deletion of
          encrypted files; shredding of any paper documents).
        </p>
      </Article>

      <Article num="§15" title="Geographic Service Availability — EU/EEA">
        <p>This service is intended for individuals currently residing in:</p>
        <ul className="list-disc pl-4 mt-2 columns-2 space-y-1">
          <li>United States</li>
          <li>United Kingdom</li>
          <li>Canada</li>
          <li>Australia</li>
          <li>Ireland</li>
          <li>South Africa</li>
          <li>South Korea</li>
        </ul>
        <p className="mt-4">
          Due to the additional compliance obligations imposed by the{' '}
          <strong>EU General Data Protection Regulation (GDPR)</strong> — in particular the mandatory
          right to erasure (Article 17) and associated restrictions that conflict with our legal retention
          obligations under Korean immigration and employment law — <strong>we are currently unable to
          process applications from individuals residing in EU/EEA member states</strong> (Ireland excepted,
          as listed above).
        </p>
        <p className="mt-3">
          If you are currently located in an EU/EEA country other than Ireland, we recommend that you do not
          submit personal information through this platform.
        </p>
        <p className="mt-2 text-xs text-gray-500">
          Note: this restriction is based on your current country of residence, not your citizenship or nationality.
          An Irish citizen residing in Germany would be subject to this restriction; a German citizen currently
          residing in Ireland would not.
        </p>
      </Article>

      <Article num="§16" title="International Data Transfers">
        <p>
          Your data is stored and processed in South Korea (primary database) and on servers operated by
          AWS, Render, and Vercel (see §4 / Article 4 for details). Where necessary for your placement,
          data is shared with prospective employers located in South Korea only.
        </p>
        <p className="mt-3">
          All data is encrypted in transit (TLS/HTTPS) and at rest (AES-256). We do not transfer personal
          data to countries outside Korea except where necessary to use the infrastructure providers listed
          above, or where required by law.
        </p>
      </Article>

      <Article num="§17" title="Your Rights by Country of Residence">

        <SubSection label="United Kingdom — UK GDPR">
          You have the right to: access, rectification, erasure (subject to legal retention obligations),
          restriction of processing, data portability, and objection. We will respond within <strong>one calendar
          month</strong>. You may lodge a complaint with the{' '}
          <strong>Information Commissioner&rsquo;s Office (ICO)</strong> at ico.org.uk.
        </SubSection>

        <SubSection label="Canada — PIPEDA">
          You have the right to access personal information held about you, to challenge its accuracy, and to
          request correction. Contact our Privacy Officer at bridgejobkr@gmail.com. Complaints may be
          directed to the <strong>Office of the Privacy Commissioner of Canada</strong> at priv.gc.ca.
        </SubSection>

        <SubSection label="Australia — Privacy Act 1988 (APPs)">
          You have the right to access and correct personal information held about you under the Australian
          Privacy Principles. Complaints may be directed to the{' '}
          <strong>Office of the Australian Information Commissioner (OAIC)</strong> at oaic.gov.au.
        </SubSection>

        <SubSection label="South Africa — POPIA">
          You have the right to access, correct, delete, and object to processing of your personal information
          under the Protection of Personal Information Act. Complaints may be directed to the{' '}
          <strong>Information Regulator of South Africa</strong> at inforegulator.org.za.
        </SubSection>

        <SubSection label="United States — CCPA (California residents)">
          California residents have the right to know about, delete, and opt out of the sale of personal
          information under the California Consumer Privacy Act. We do not sell personal data to third parties.
          Submit requests to bridgejobkr@gmail.com.
        </SubSection>

        <SubSection label="South Korea — PIPA (개인정보보호법)">
          See Part 1 (Articles 제1조–제10조) above for your full rights under Korean law, including the
          right to access, correct, delete, and restrict processing, and how to contact the{' '}
          개인정보보호위원회 (Personal Information Protection Commission).
        </SubSection>

        <p className="mt-4">
          To exercise any of the above rights, contact:{' '}
          <a href="mailto:bridgejobkr@gmail.com" className="text-blue-600 underline">bridgejobkr@gmail.com</a>.
          We will respond within 10 business days (Korean law) or 30 calendar days (UK/international requests).
        </p>
      </Article>

      <Article num="§18" title="Changes to This Policy">
        <p>
          We may update this Privacy Policy from time to time. The &ldquo;Last updated&rdquo; date at the
          top reflects the most recent revision. For material changes, we will notify active applicants by
          email. Continued use of our services after changes are posted constitutes acceptance of the
          revised policy.
        </p>
      </Article>

      {/* Footer note */}
      <div className="mt-10 pt-6 border-t border-gray-200 text-xs text-gray-400 space-y-1">
        <p>BRIDGE Recruitment · bridgejob.co.kr · bridgejobkr@gmail.com</p>
        <p>This policy is governed by the laws of the Republic of Korea.</p>
        <p>「개인정보 보호법」 제30조에 따른 개인정보 처리방침입니다.</p>
      </div>

    </div>
  )
}

/* ── Sub-components ── */

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-10 mb-6 pb-2 border-b-2 border-blue-600">
      <h2 className="text-xl font-bold text-blue-700">{children}</h2>
    </div>
  )
}

function Article({ num, title, children }: { num: string; title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h3 className="text-base font-bold mb-3 text-[#1d1d1f]">
        <span className="text-blue-600 mr-2">{num}</span>{title}
      </h3>
      <div className="text-sm text-[#3d3d3f] leading-relaxed space-y-2">{children}</div>
    </section>
  )
}

function SubSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mt-4 pl-3 border-l-2 border-gray-200">
      <p className="font-semibold text-[#1d1d1f] mb-1 text-[13px]">{label}</p>
      <p className="text-[13px]">{children}</p>
    </div>
  )
}

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-[13px] text-amber-800 leading-relaxed">
      {children}
    </div>
  )
}

function Table({ headers, children }: { headers: string[]; children: React.ReactNode }) {
  return (
    <div className="mt-3 overflow-x-auto">
      <table className="w-full text-[12px] border-collapse border border-gray-200 rounded-lg overflow-hidden">
        <thead>
          <tr className="bg-gray-50">
            {headers.map((h) => (
              <th key={h} className="border border-gray-200 px-3 py-2 text-left font-semibold text-gray-700">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">{children}</tbody>
      </table>
    </div>
  )
}
