import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Teacher Support | BRIDGE Recruitment',
  description: 'Candidate responsibilities, recruitment process, and contact guidelines for BRIDGE teacher placements.',
}

export default function SupportPage() {
  return (
    <div className="max-w-[860px] mx-auto px-4 sm:px-6 py-12 text-[#1d1d1f]">

      {/* Header */}
      <div className="mb-10 pb-6 border-b border-gray-200">
        <span className="inline-block text-[11px] font-semibold text-gray-500 border border-gray-300 rounded px-2 py-0.5 mb-4">For Teachers</span>
        <h1 className="text-3xl font-bold mb-1">Support</h1>
        <p className="text-sm text-gray-500">Candidate guidelines &amp; recruitment process &nbsp;|&nbsp; BRIDGE Recruitment</p>
      </div>

      <div className="space-y-10 text-sm text-gray-700 leading-7">

        {/* Section 1 */}
        <section className="pt-8 border-t border-gray-100">
          <h2 className="text-base font-bold text-[#1d1d1f] mb-3">1. Candidate Responsibilities</h2>
          <ul className="list-disc pl-5 space-y-3">
            <li>
              <strong>Accuracy of information:</strong> All information submitted must be truthful
              and complete. Submission of false information — including falsified academic credentials
              — will result in disqualification and may give rise to legal liability.
            </li>
            <li>
              <strong>Document readiness:</strong> Ensure your CV, photograph, and all supporting
              documents are accurate and up to date prior to submission.
            </li>
            <li>
              <strong>Responsiveness:</strong> You must keep your assigned BRIDGE recruiter informed
              at all stages — including if you decide not to proceed. Recruiters prepare interview
              arrangements on your behalf; failure to respond disrupts the process and may affect
              your access to future services.
            </li>
          </ul>
        </section>

        {/* Section 2 */}
        <section className="pt-8 border-t border-gray-100">
          <h2 className="text-base font-bold text-[#1d1d1f] mb-3">2. Recruitment Process</h2>
          <p className="mb-4 text-gray-600">The standard BRIDGE placement process for teacher candidates proceeds as follows:</p>
          <ol className="space-y-3">
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
                <span className="shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center mt-0.5">
                  {i + 1}
                </span>
                <span className="pt-0.5">{step}</span>
              </li>
            ))}
          </ol>
        </section>

        {/* Section 3 */}
        <section className="pt-8 border-t border-gray-100">
          <h2 className="text-base font-bold text-[#1d1d1f] mb-3">3. No Direct Contact</h2>
          <p className="mb-3">Prior to hiring confirmation, the following are strictly prohibited:</p>
          <ul className="list-disc pl-5 space-y-2">
            <li>Requesting a direct meeting with a prospective employer without going through your assigned BRIDGE recruiter</li>
            <li>Accepting or requesting informal verbal agreements without BRIDGE&rsquo;s prior written consent</li>
            <li>Collecting employer contact details obtained via the BRIDGE platform, or attempting to contact an employer outside the formal process</li>
          </ul>
          <p className="mt-4">
            All communications with prospective employers must be conducted through your assigned
            BRIDGE recruiter (via messenger or email) until the Supply Contract has been executed.
            BRIDGE is unable to provide assistance or protection in respect of any terms or
            arrangements reached through personal contact outside this process. For your own
            protection, please ensure that all proceedings are managed through the BRIDGE team.
          </p>
        </section>

      </div>

      {/* Footer */}
      <div className="mt-14 pt-6 border-t border-gray-200 text-xs text-gray-400 space-y-1">
        <p>BRIDGE Recruitment · <a href="mailto:bridgejobkr@gmail.com" className="underline hover:text-gray-600">bridgejobkr@gmail.com</a></p>
        <p>
          See also:{' '}
          <Link href="/terms" className="underline hover:text-gray-600">Terms of Use</Link>
          {' · '}
          <Link href="/privacy" className="underline hover:text-gray-600">Privacy Policy</Link>
          {' · '}
          <Link href="/contact" className="underline hover:text-gray-600">Contact</Link>
        </p>
      </div>

    </div>
  )
}
