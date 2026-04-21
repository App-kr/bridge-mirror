import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Privacy Policy | BRIDGE Recruitment',
  description: 'How BRIDGE Recruitment collects, uses, and protects your personal data.',
}

export default function PrivacyPage() {
  return (
    <div className="max-w-[800px] mx-auto px-4 sm:px-6 py-12 text-[#1d1d1f]">
      <h1 className="text-3xl font-bold mb-2">Privacy Policy</h1>
      <p className="text-sm text-gray-500 mb-10">Last updated: April 2026</p>

      <Section title="1. Who We Are">
        <p>
          BRIDGE Recruitment (&ldquo;BRIDGE&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;) is a Korea-based ESL teacher
          recruitment agency operating at <strong>bridgejob.co.kr</strong>. We match qualified English-language
          teachers with schools and educational institutions across South Korea.
        </p>
        <p className="mt-3">
          Contact: <a href="mailto:bridgejobkr@gmail.com" className="text-blue-600 underline">bridgejobkr@gmail.com</a>
        </p>
      </Section>

      <Section title="2. Data We Collect">
        <p>When you submit an application or inquiry through this site, we may collect:</p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>Full name, date of birth, gender, nationality, and country of residence</li>
          <li>Contact details: email address, phone number, KakaoTalk ID</li>
          <li>Passport details, visa status, and work eligibility documents</li>
          <li>Educational background, teaching certifications, and employment history</li>
          <li>Criminal record check results (Korean and home country)</li>
          <li>Profile photo and CV / cover letter</li>
          <li>Preferences: preferred region, school type, start date, housing requirements</li>
        </ul>
        <p className="mt-3">
          For school and employer inquiries: school name, contact person details, and hiring requirements.
        </p>
      </Section>

      <Section title="3. How We Use Your Data">
        <ul className="list-disc pl-5 space-y-1">
          <li>To assess your suitability for teaching positions and match you with prospective employers</li>
          <li>To communicate with you regarding your application, interviews, and placement offers</li>
          <li>To verify documents and conduct necessary background checks</li>
          <li>To facilitate the visa and work permit application process in South Korea</li>
          <li>To comply with applicable employment and immigration laws</li>
        </ul>
        <p className="mt-3">
          We do not sell your personal data or use it for marketing purposes unrelated to your recruitment.
        </p>
      </Section>

      <Section title="4. Legal Basis for Processing">
        <p>We process your data on the following legal bases:</p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>
            <strong>Performance of a contract</strong> — processing is necessary to take steps at your request
            prior to entering into, or fulfilling, a placement agreement
          </li>
          <li>
            <strong>Legal obligation</strong> — we are required to retain certain records under Korean
            immigration, tax, and employment law
          </li>
          <li>
            <strong>Legitimate interests</strong> — to resolve disputes, enforce agreements, and maintain
            accurate recruitment records
          </li>
        </ul>
      </Section>

      <Section title="5. Data Retention">
        <p>
          Personal data submitted through this platform is retained for a <strong>minimum of three (3) years</strong>{' '}
          following the conclusion of your recruitment process (whether placement, withdrawal, or rejection).
        </p>
        <p className="mt-3">
          Retention beyond this period may be necessary to:
        </p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>Comply with Korean immigration and visa regulations applicable to foreign worker placements</li>
          <li>Resolve disputes or legal claims arising from placement agreements</li>
          <li>Satisfy applicable tax and employment record-keeping obligations</li>
        </ul>
        <p className="mt-3">
          You may request access to or deletion of your data at any time by contacting us at{' '}
          <a href="mailto:bridgejobkr@gmail.com" className="text-blue-600 underline">bridgejobkr@gmail.com</a>.
          Please note that deletion requests may be declined where retention is required by law. We will inform
          you of the specific legal basis if a deletion request cannot be fulfilled.
        </p>
      </Section>

      <Section title="6. International Data Transfers">
        <p>
          Your data is stored on servers operated by our hosting and infrastructure providers. As a Korea-based
          service facilitating international placements, your data may be transferred to and processed in South
          Korea and, where necessary, shared with prospective employers located in South Korea.
        </p>
        <p className="mt-3">
          All data is encrypted in transit (HTTPS/TLS) and at rest (AES-256 encryption). We do not share
          your personal data with third parties outside of the recruitment process without your consent.
        </p>
      </Section>

      <Section title="7. Geographic Service Availability">
        <p>
          This service is intended for individuals currently residing in the following countries:
        </p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>United States</li>
          <li>United Kingdom</li>
          <li>Canada</li>
          <li>Australia</li>
          <li>Ireland</li>
          <li>South Africa</li>
          <li>South Korea</li>
        </ul>
        <p className="mt-3">
          Due to the compliance obligations imposed by the EU General Data Protection Regulation (GDPR) —
          in particular regarding data subject rights and mandatory retention limitations — <strong>we are
          currently unable to process applications from individuals residing in EU/EEA member states</strong>{' '}
          (Ireland excepted, as listed above). If you are currently located in an EU/EEA country other than
          Ireland, we recommend that you do not submit personal information through this platform.
        </p>
        <p className="mt-3 text-sm text-gray-500">
          Note: this restriction is based on your current country of residence, not your nationality.
        </p>
      </Section>

      <Section title="8. Your Rights">
        <p>
          Depending on your country of residence, you may have the following rights regarding your personal data:
        </p>

        <SubSection label="United Kingdom (UK GDPR)">
          Right of access, rectification, erasure (subject to legal retention obligations), restriction,
          portability, and objection. Requests must be fulfilled within one month. Contact us directly or
          lodge a complaint with the ICO (ico.org.uk).
        </SubSection>

        <SubSection label="Canada (PIPEDA)">
          Right to access personal information held about you and to challenge its accuracy. Contact our
          Privacy Officer at bridgejobkr@gmail.com.
        </SubSection>

        <SubSection label="Australia (Privacy Act 1988)">
          Right to access and correct personal information under the Australian Privacy Principles (APPs).
          Complaints may be directed to the OAIC (oaic.gov.au).
        </SubSection>

        <SubSection label="South Africa (POPIA)">
          Right to access, correction, deletion, and objection to processing under the Protection of
          Personal Information Act. Complaints may be directed to the Information Regulator (inforegulator.org.za).
        </SubSection>

        <SubSection label="United States">
          California residents have additional rights under the CCPA, including the right to know about
          and delete personal information. We do not sell personal data.
        </SubSection>

        <p className="mt-4">
          To exercise any of the above rights, contact us at{' '}
          <a href="mailto:bridgejobkr@gmail.com" className="text-blue-600 underline">bridgejobkr@gmail.com</a>.
          We will respond within 30 days.
        </p>
      </Section>

      <Section title="9. Security">
        <p>
          We take appropriate technical and organisational measures to protect your personal data, including:
        </p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>AES-256 encryption of personal data fields at rest</li>
          <li>HTTPS/TLS encryption for all data in transit</li>
          <li>Access controls restricting data to authorised BRIDGE staff only</li>
          <li>Regular security audits</li>
        </ul>
      </Section>

      <Section title="10. Changes to This Policy">
        <p>
          We may update this Privacy Policy from time to time. The &ldquo;Last updated&rdquo; date at the top
          of this page reflects when the most recent changes were made. Continued use of our service after
          changes are posted constitutes acceptance of the revised policy.
        </p>
      </Section>

      <Section title="11. Contact">
        <p>
          For any questions, data requests, or complaints regarding this Privacy Policy, please contact:
        </p>
        <p className="mt-3">
          <strong>BRIDGE Recruitment</strong><br />
          Email: <a href="mailto:bridgejobkr@gmail.com" className="text-blue-600 underline">bridgejobkr@gmail.com</a><br />
          Website: <a href="https://bridgejob.co.kr" className="text-blue-600 underline">bridgejob.co.kr</a>
        </p>
      </Section>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold mb-3 text-[#1d1d1f]">{title}</h2>
      <div className="text-sm text-[#3d3d3f] leading-relaxed">{children}</div>
    </section>
  )
}

function SubSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mt-4">
      <p className="font-semibold text-[#1d1d1f] mb-1">{label}</p>
      <p>{children}</p>
    </div>
  )
}
