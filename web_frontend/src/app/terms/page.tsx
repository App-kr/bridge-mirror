import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Terms of Use | BRIDGE Recruitment',
  description: 'BRIDGE Recruitment terms of use — service guidelines for teachers and employers.',
}

export default function TermsPage() {
  return (
    <div className="max-w-[860px] mx-auto px-4 sm:px-6 py-12 text-[#1d1d1f]">

      {/* Header */}
      <div className="mb-10 pb-6 border-b border-gray-200">
        <h1 className="text-3xl font-bold mb-1">Terms of Use</h1>
        <p className="text-sm text-gray-500">이용약관 &nbsp;|&nbsp; Last updated: April 2026 &nbsp;|&nbsp; Version 1.0</p>
        <p className="mt-3 text-sm text-gray-600 leading-relaxed">
          These Terms of Use (&ldquo;Terms&rdquo;) govern your use of the BRIDGE Recruitment website at{' '}
          <strong>bridgejob.co.kr</strong> and the recruitment services provided by BRIDGE Agency
          (&ldquo;BRIDGE&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;). By using our site or services,
          you agree to these Terms.
        </p>
        <p className="mt-3 text-sm text-gray-600 leading-relaxed">
          본 약관은 브릿지 에이전시의 서비스 이용에 관한 기본적인 운영 규정입니다.
          채용 확정 시 발송되는 <strong>인력 공급 계약서</strong>가 법적 효력을 가지는 최종 계약 문서이며,
          본 약관과 상충하는 경우 계약서가 우선합니다.
        </p>

        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
          <strong>Note:</strong> These Terms are basic service guidelines. The binding legal agreement
          is the <strong>Supply Contract (인력 공급 계약서)</strong> issued upon hiring confirmation.
          Please review it carefully before signing, as changes or cancellations are difficult once signed.
        </div>
      </div>

      {/* ── PART A: FOR TEACHERS ── */}
      <SectionHeader>Part A — For Teachers (강사 지원자)</SectionHeader>

      <Article num="1." title="Service Description">
        <p>
          BRIDGE provides ESL teacher recruitment and placement services in South Korea. Our service
          to teacher candidates is provided <strong>free of charge</strong>. This includes profile
          management, employer matching, and partial interview support services.
        </p>
        <p className="mt-2">
          Under Korean employment law, recruitment agencies are permitted to charge fees to job
          seekers in certain circumstances. However, BRIDGE chooses to provide its services to
          foreign teacher candidates entirely free of charge as a courtesy. In return, we ask that
          you use our service — and any Korean work visa obtained through it — solely for the
          purpose of lawful employment. <strong>Abuse of the visa process, misrepresentation of
          qualifications, or use of a placement to circumvent immigration rules will result in
          immediate termination of services and may be reported to the relevant authorities.</strong>
        </p>
        <p className="mt-2">
          Placement is not guaranteed. Results depend on your qualifications, availability,
          employer requirements, and your engagement with the recruitment process. BRIDGE acts as
          an intermediary only — the employment contract is between you and the employer directly.
        </p>
      </Article>

      <Article num="2." title="Candidate Responsibilities">
        <ul className="list-disc pl-5 space-y-2">
          <li>
            <strong>Respond to your recruiter</strong>: Even if you decide not to proceed, you must
            inform your assigned BRIDGE recruiter of your decision. Recruiters prepare for interviews
            on your behalf — failing to respond disrupts the process and affects future service access.
          </li>
          <li>
            <strong>Accurate information</strong>: All information submitted must be truthful and
            complete. Submission of false information — including falsified academic credentials —
            renders you ineligible and may result in legal liability.
          </li>
          <li>
            <strong>Document readiness</strong>: Ensure your CV, photo, and supporting documents
            are accurate and up to date before submitting.
          </li>
        </ul>
      </Article>

      <Article num="3." title="Job Search Process">
        <p>The standard BRIDGE placement process for teacher candidates is as follows:</p>
        <ol className="mt-3 space-y-2">
          {[
            'Resume and application form submitted → Information verified for accuracy',
            'Online meeting with your assigned recruiter; reference checks conducted',
            'Profile introduced to prospective employers; listing posted on the job board',
            'Online and/or in-person interviews arranged between candidate and employer',
            'Employer background check; contract offer reviewed; accommodation confirmed',
            'Contract finalised; training start date coordinated',
            'Relocation assisted; teacher information registered',
            'Employment begins',
          ].map((step, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="shrink-0 w-5 h-5 rounded-full bg-blue-600 text-white text-[11px] font-bold flex items-center justify-center mt-0.5">
                {i + 1}
              </span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </Article>

      <Article num="4." title="No Direct Contact">
        <p>Prior to hiring confirmation, the following are prohibited:</p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>Requesting a direct meeting with an employer without going through your assigned BRIDGE recruiter</li>
          <li>Accepting or requesting unofficial contracts without BRIDGE&rsquo;s prior consent</li>
          <li>Collecting employer contact information obtained through the BRIDGE platform or attempting to contact them outside the process</li>
        </ul>
        <p className="mt-3">
          All communication with prospective employers must go through your assigned BRIDGE recruiter
          (via messenger or email) until hiring is confirmed and the Supply Contract is executed.
          BRIDGE provides no assistance for any terms or arrangements made through personal contact outside this process.
        </p>
        <p className="mt-3 text-gray-500">
          Violation of this rule may result in immediate termination of services and may constitute
          grounds for legal action for business interference (업무 방해).
        </p>
      </Article>

      {/* ── PART B: FOR EMPLOYERS ── */}
      <div className="mt-12">
        <SectionHeader>Part B — For Employers (구인 학교 및 기관)</SectionHeader>
      </div>

      <Article num="5." title="Service & Fees">
        <p>
          BRIDGE provides paid teacher recruitment services to schools and educational institutions
          in South Korea (유료직업소개업). Service fees, payment schedule, and terms are specified
          in the <strong>Supply Contract (인력 공급 계약서)</strong> issued upon hiring confirmation.
        </p>
        <p className="mt-2">
          Standard payment structure: partial fee advance upon contract execution; balance due on
          the teacher&rsquo;s employment start date. Details vary by contract.
        </p>
      </Article>

      <Article num="6." title="No Direct Contact Rule (직접 연락 엄금)">
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-900 mb-3">
          직접 연락 시 서비스 즉시 종료 및 업무 방해에 따른 손해배상 등 법적 책임이 적용될 수 있습니다.
        </div>
        <p>Prior to hiring confirmation and Supply Contract execution, the following are strictly prohibited:</p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>Requesting personal contact information directly from teacher candidates</li>
          <li>Collecting personal information from candidates outside the BRIDGE process</li>
          <li>Sharing your own or your employees&rsquo; direct contact information with candidates</li>
          <li>Arranging direct meetings or sending unofficial contracts without prior agreement</li>
        </ul>
        <p className="mt-3">
          All information about candidates is disclosed transparently upon hiring confirmation.
          Unauthorised collection prior to confirmation is strictly prohibited.
        </p>
      </Article>

      <Article num="7." title="Refund Policy (환불 규정)">
        <Table headers={['Situation', 'Refund Available?']}>
          <tr>
            <td>Teacher deported due to falsified academic credentials or other legal violations by the teacher</td>
            <td className="text-green-700 font-semibold">Yes — within the service period</td>
          </tr>
          <tr>
            <td>Employer-caused issues: staff reduction, assignment of duties outside job scope, or other employer-side breaches</td>
            <td className="text-red-600 font-semibold">No — employer liability</td>
          </tr>
          <tr>
            <td>School closure, bankruptcy, or force majeure events</td>
            <td className="text-red-600 font-semibold">No — outside BRIDGE&rsquo;s control</td>
          </tr>
          <tr>
            <td>Teacher resignation without cause after placement</td>
            <td className="text-gray-500">Subject to Supply Contract terms</td>
          </tr>
        </Table>
        <p className="mt-3 text-[13px] text-gray-500">
          All refund conditions are governed by the Supply Contract (인력 공급 계약서).
          Refund requests must be submitted in writing to bridgejobkr@gmail.com within the
          period specified in your contract.
        </p>
      </Article>

      {/* ── PART C: GENERAL ── */}
      <div className="mt-12">
        <SectionHeader>Part C — General Terms (공통 조항)</SectionHeader>
      </div>

      <Article num="8." title="Disclaimer & Limitation of Liability">
        <p>BRIDGE acts solely as a recruitment intermediary. We are not a party to the employment contract between teacher and employer. Accordingly, BRIDGE assumes no liability for:</p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>Breaches of the employment contract by either party</li>
          <li>School closure, bankruptcy, or restructuring by the employer</li>
          <li>Changes in teaching assignment, hours, or working conditions imposed by the employer</li>
          <li>Travel arrangements, accommodation, or transportation</li>
          <li>Personal injury, property damage, or other losses arising during or after placement</li>
          <li>Actions or omissions of third-party service providers</li>
        </ul>
        <p className="mt-3">
          To the maximum extent permitted by applicable law, BRIDGE&rsquo;s total liability arising
          from any claim related to our services shall not exceed the fees paid to BRIDGE in connection
          with the specific placement giving rise to the claim.
        </p>
      </Article>

      <Article num="9." title="Intellectual Property">
        <p>
          All content on this website — including text, images, logos, and platform design — is the
          property of BRIDGE Recruitment and may not be reproduced, distributed, or used without
          prior written consent.
        </p>
      </Article>

      <Article num="10." title="Prohibited Actions">
        <ul className="list-disc pl-5 space-y-1">
          <li>Attempting to gain unauthorised access to any part of this site or its systems</li>
          <li>Using the platform for any unlawful purpose</li>
          <li>Submitting false, misleading, or fraudulent information</li>
          <li>Circumventing the BRIDGE process to directly engage parties introduced through our service</li>
          <li>Reverse-engineering, scraping, or otherwise copying content or data from this platform</li>
        </ul>
      </Article>

      <Article num="11." title="Amendments">
        <p>
          BRIDGE may amend these Terms at any time. For general changes, we will provide at least
          <strong> 7 days&rsquo; notice</strong> by posting the updated Terms on this page.
          For changes that materially affect your rights, we will provide at least{' '}
          <strong>30 days&rsquo; notice</strong> by email where we hold your contact information.
          Continued use of our services after the effective date constitutes acceptance of the revised Terms.
        </p>
      </Article>

      <Article num="12." title="Governing Law & Disputes">
        <p>
          These Terms are governed by the laws of the <strong>Republic of Korea</strong>.
          Any disputes arising from these Terms or our services shall be subject to the exclusive
          jurisdiction of the courts located in <strong>Seoul, South Korea</strong>.
        </p>
      </Article>

      {/* Footer note */}
      <div className="mt-10 pt-6 border-t border-gray-200 text-xs text-gray-400 space-y-1">
        <p>BRIDGE Recruitment · bridgejob.co.kr · bridgejobkr@gmail.com</p>
        <p>
          See also:{' '}
          <Link href="/privacy" className="underline hover:text-gray-600">Privacy Policy</Link>
        </p>
        <p>These Terms are basic service guidelines only. The Supply Contract (인력 공급 계약서) constitutes the binding legal agreement.</p>
      </div>

    </div>
  )
}

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
