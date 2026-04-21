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
        <span className="inline-block text-[11px] font-semibold text-gray-500 border border-gray-300 rounded px-2 py-0.5 mb-4">Legal</span>
        <h1 className="text-3xl font-bold mb-1">Terms of Use</h1>
        <p className="text-sm text-gray-500">Last updated: May 2026 &nbsp;|&nbsp; Version 3.2</p>
        <p className="mt-3 text-sm text-gray-600 leading-relaxed">
          These Terms of Use (&ldquo;Terms&rdquo;) govern your use of the BRIDGE website at{' '}
          <strong>bridgejob.co.kr</strong> and the recruitment services provided by BRIDGE Agency
          (&ldquo;BRIDGE&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;).
        </p>
      </div>

      <div className="space-y-10 text-sm text-gray-700 leading-7">

        <Article num="1" title="Service Description">
          <p>
            BRIDGE provides ESL teacher recruitment and placement services in South Korea. Under Korean
            employment law, recruitment agencies are permitted to charge fees to job seekers; however,
            BRIDGE provides its services to foreign teacher candidates entirely free of charge as a
            courtesy.
          </p>
          <p>
            In return, we ask that you use our service — and any Korean work visa obtained through it
            — solely for the purpose of lawful employment.{' '}
            <strong>
              Abuse of the visa process, misrepresentation of qualifications, or use of a placement to
              circumvent immigration rules will result in immediate termination of services and may be
              reported to the relevant authorities.
            </strong>
          </p>
          <p>
            Placement is not guaranteed. Outcomes depend on your qualifications, availability, employer
            requirements, and your level of engagement throughout the recruitment process. BRIDGE acts
            solely as an intermediary — the employment contract is concluded directly between you and
            the employer following thorough review and dialogue between both parties.
          </p>
        </Article>

        <Article num="2" title="Candidate Responsibilities">
          <ul className="list-disc pl-5 space-y-2">
            <li>
              <strong>Accuracy of information:</strong> All information submitted must be truthful and
              complete. Submission of false information — including falsified academic credentials —
              will result in disqualification and may give rise to legal liability.
            </li>
            <li>
              <strong>Document readiness:</strong> Ensure your CV, photograph, and all supporting
              documents are accurate and up to date prior to submission.
            </li>
            <li>
              <strong>Responsiveness:</strong> You must keep your assigned BRIDGE recruiter informed
              at all stages — including if you decide not to proceed. Recruiters prepare interview
              arrangements on your behalf; failure to respond disrupts the process and may affect your
              access to future services.
            </li>
          </ul>
        </Article>

        <Article num="3" title="Recruitment Process">
          <p>The standard BRIDGE placement process for teacher candidates proceeds as follows:</p>
          <ol className="mt-3 space-y-2">
            {[
              'CV and application form submitted — information verified for accuracy',
              'Online consultation with your assigned recruiter; reference checks conducted',
              'Profile introduced to prospective employers; position listed on the job board',
              'Online and/or in-person interviews arranged between candidate and employer',
              'Employer background check conducted; contract terms reviewed; accommodation confirmed',
              'Contract executed; commencement date coordinated',
              'Relocation support provided; teacher information registered',
              'Employment commences',
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

        <Article num="4" title="No Direct Contact">
          <p>Prior to hiring confirmation, the following are strictly prohibited:</p>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li>Requesting a direct meeting with a prospective employer without going through your assigned BRIDGE recruiter</li>
            <li>Accepting or requesting informal verbal agreements without BRIDGE&rsquo;s prior written consent</li>
            <li>Collecting employer contact details obtained via the BRIDGE platform, or attempting to contact an employer outside the formal process</li>
          </ul>
          <p className="mt-3">
            All communications with prospective employers must be conducted through your assigned
            BRIDGE recruiter (via messenger or email) until the Supply Contract has been executed.
            BRIDGE is unable to provide assistance or protection in respect of any terms or
            arrangements reached through personal contact outside this process. For your own
            protection, please ensure that all proceedings are managed through the BRIDGE team.
          </p>
        </Article>

        <Article num="5" title="Intellectual Property">
          <p>
            All content on this website — including employer data, contract information, text, images,
            logos, and platform design — is the property of BRIDGE Recruitment and may not be
            reproduced, distributed, or used in any form without prior written consent from BRIDGE.
          </p>
        </Article>

        <Article num="6" title="Prohibited Conduct">
          <ul className="list-disc pl-5 space-y-1">
            <li>Attempting to gain unauthorised access to any part of this site or its underlying systems</li>
            <li>Using the platform for any unlawful purpose</li>
            <li>Submitting false, misleading, or fraudulent information</li>
            <li>Circumventing the BRIDGE process to engage directly with any party introduced through our service</li>
            <li>Reverse-engineering, scraping, or otherwise reproducing content or data from this platform</li>
          </ul>
        </Article>

        <Article num="7" title="Amendments">
          <p>
            BRIDGE reserves the right to amend these Terms at any time. For general updates, the
            revised Terms will be published on this page with reasonable prior notice. Continued use
            of our services following the effective date of any amendment constitutes acceptance of
            the updated Terms.
          </p>
        </Article>

        <Article num="8" title="Governing Law &amp; Dispute Resolution">
          <p>
            These Terms are governed by the laws of the <strong>Republic of Korea</strong>. Any
            disputes arising out of or in connection with these Terms or our services shall be
            subject to the exclusive jurisdiction of the competent courts in the Republic of Korea,
            in accordance with the location of BRIDGE&rsquo;s registered place of business.
          </p>
        </Article>

      </div>

      {/* Footer */}
      <div className="mt-14 pt-6 border-t border-gray-200 text-xs text-gray-400 space-y-1">
        <p>BRIDGE Recruitment · <a href="mailto:bridgejobkr@gmail.com" className="underline hover:text-gray-600">bridgejobkr@gmail.com</a></p>
        <p>
          See also:{' '}
          <Link href="/privacy" className="underline hover:text-gray-600">Privacy Policy</Link>
          {' · '}
          <Link href="/fees" className="underline hover:text-gray-600">Fee Disclosure</Link>
          {' · '}
          <Link href="/contact" className="underline hover:text-gray-600">Contact</Link>
        </p>
      </div>

    </div>
  )
}

function Article({ num, title, children }: { num: string; title: string; children: React.ReactNode }) {
  return (
    <section className="pt-8 border-t border-gray-100">
      <h2 className="text-base font-bold text-[#1d1d1f] mb-3">{num}. {title}</h2>
      <div className="space-y-3 text-sm text-gray-700 leading-7">{children}</div>
    </section>
  )
}
