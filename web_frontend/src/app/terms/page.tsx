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

        <Article num="2" title="Candidate Guidelines">
          <p>
            Detailed candidate responsibilities, the step-by-step recruitment process, and our
            direct contact policy are available on the{' '}
            <a href="/community/support" className="underline text-blue-700 hover:text-blue-900">
              Support page
            </a>.
          </p>
        </Article>

        <Article num="3" title="Intellectual Property">
          <p>
            All content on this website — including employer data, contract information, text, images,
            logos, and platform design — is the property of BRIDGE Recruitment and may not be
            reproduced, distributed, or used in any form without prior written consent from BRIDGE.
          </p>
        </Article>

        <Article num="4" title="Prohibited Conduct">
          <ul className="list-disc pl-5 space-y-1">
            <li>Attempting to gain unauthorised access to any part of this site or its underlying systems</li>
            <li>Using the platform for any unlawful purpose</li>
            <li>Submitting false, misleading, or fraudulent information</li>
            <li>Circumventing the BRIDGE process to engage directly with any party introduced through our service</li>
            <li>Reverse-engineering, scraping, or otherwise reproducing content or data from this platform</li>
          </ul>
        </Article>

        <Article num="5" title="Amendments">
          <p>
            BRIDGE reserves the right to amend these Terms at any time. For general updates, the
            revised Terms will be published on this page with reasonable prior notice. Continued use
            of our services following the effective date of any amendment constitutes acceptance of
            the updated Terms.
          </p>
        </Article>

        <Article num="6" title="Governing Law &amp; Dispute Resolution">
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
