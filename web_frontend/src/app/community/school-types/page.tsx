import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'School Types & Pay in Korea | BRIDGE Recruitment',
  description:
    'EPIK (public schools) vs private hagwon — salary, housing, benefits, work schedule, and pros & cons compared side by side.',
}

/* ── Small helper components ─────────────────────────────── */
function Badge({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span
      className={`inline-block text-[11px] font-semibold px-2 py-0.5 rounded border ${color}`}
    >
      {children}
    </span>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-12">
      <h2 className="text-xl font-bold text-[#1d1d1f] mb-5 pb-3 border-b border-gray-200">
        {title}
      </h2>
      {children}
    </section>
  )
}

function Row({
  label,
  epik,
  hagwon,
  highlight,
}: {
  label: string
  epik: React.ReactNode
  hagwon: React.ReactNode
  highlight?: 'epik' | 'hagwon' | 'both'
}) {
  return (
    <tr className="border-b border-gray-100 last:border-0">
      <td className="py-3 pr-4 text-[13px] font-medium text-gray-600 w-[160px] align-top">
        {label}
      </td>
      <td
        className={`py-3 pr-4 text-[13px] text-gray-800 align-top ${
          highlight === 'epik' || highlight === 'both' ? 'font-semibold text-[#1B3A6B]' : ''
        }`}
      >
        {epik}
      </td>
      <td
        className={`py-3 text-[13px] text-gray-800 align-top ${
          highlight === 'hagwon' || highlight === 'both' ? 'font-semibold text-[#7c3aed]' : ''
        }`}
      >
        {hagwon}
      </td>
    </tr>
  )
}

/* ── Page ─────────────────────────────────────────────────── */
export default function SchoolTypesPage() {
  return (
    <div className="max-w-[900px] mx-auto px-4 sm:px-6 py-12 text-[#1d1d1f]">

      {/* Header */}
      <div className="mb-10 pb-6 border-b border-gray-200">
        <div className="flex flex-wrap gap-2 mb-4">
          <Badge color="text-gray-500 border-gray-300">Korea Guide</Badge>
          <Badge color="text-blue-600 border-blue-200 bg-blue-50">Updated 2026</Badge>
        </div>
        <h1 className="text-3xl font-bold mb-2">School Types &amp; Pay</h1>
        <p className="text-sm text-gray-500">
          EPIK (Public School) vs Private Hagwon — 학교 유형 & 조건 비교
        </p>
        <p className="mt-4 text-sm text-gray-600 leading-relaxed max-w-[720px]">
          Teaching English in Korea means choosing between a{' '}
          <strong>government-funded public school program (EPIK/GEPIK/SMOE)</strong> and a{' '}
          <strong>private language academy (hagwon)</strong>. Both come with an E-2 visa, but the
          salary, schedule, and lifestyle differ significantly. Use this guide to decide which fits
          you best.
        </p>
      </div>

      {/* Quick-glance cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-12">

        {/* EPIK card */}
        <div className="rounded-xl border border-[#1B3A6B]/20 bg-[#f0f4ff] p-6">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">🏫</span>
            <span className="text-[11px] font-bold uppercase tracking-widest text-[#1B3A6B]">
              EPIK · GEPIK · SMOE
            </span>
          </div>
          <p className="text-xs text-gray-500 mb-4">Ministry of Education — Public Schools</p>
          <div className="space-y-2 text-[13px]">
            <p>
              <span className="text-gray-500">Monthly salary</span>{' '}
              <strong className="text-[#1B3A6B]">₩2,100,000 – ₩3,000,000</strong>
            </p>
            <p>
              <span className="text-gray-500">Entry bonus</span>{' '}
              <strong>₩1,800,000</strong>
            </p>
            <p>
              <span className="text-gray-500">Housing</span>{' '}
              <strong>Provided by school/province</strong>
            </p>
            <p>
              <span className="text-gray-500">Holidays</span>{' '}
              <strong>School calendar + national holidays</strong>
            </p>
            <p>
              <span className="text-gray-500">Hours</span>{' '}
              <strong>Daytime only · Mon–Fri</strong>
            </p>
          </div>
          <div className="mt-4 pt-4 border-t border-[#1B3A6B]/10 text-[12px] text-gray-500">
            Best for: stability, work-life balance, genuine school experience
          </div>
        </div>

        {/* Hagwon card */}
        <div className="rounded-xl border border-purple-200 bg-purple-50 p-6">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">📚</span>
            <span className="text-[11px] font-bold uppercase tracking-widest text-purple-700">
              Private Hagwon
            </span>
          </div>
          <p className="text-xs text-gray-500 mb-4">사립 학원 — Private Language Academy</p>
          <div className="space-y-2 text-[13px]">
            <p>
              <span className="text-gray-500">Monthly salary</span>{' '}
              <strong className="text-purple-700">₩2,200,000 – ₩3,200,000+</strong>
            </p>
            <p>
              <span className="text-gray-500">Entry bonus</span>{' '}
              <strong>₩0 – ₩1,000,000 (varies)</strong>
            </p>
            <p>
              <span className="text-gray-500">Housing</span>{' '}
              <strong>Allowance or provided (varies)</strong>
            </p>
            <p>
              <span className="text-gray-500">Holidays</span>{' '}
              <strong>10 days paid + national holidays</strong>
            </p>
            <p>
              <span className="text-gray-500">Hours</span>{' '}
              <strong>Afternoon–Evening · Sat possible</strong>
            </p>
          </div>
          <div className="mt-4 pt-4 border-t border-purple-200 text-[12px] text-gray-500">
            Best for: higher earning potential, flexible negotiation, smaller classes
          </div>
        </div>
      </div>

      {/* Detailed comparison table */}
      <Section title="Salary & Financial Benefits">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-gray-200">
                <th className="py-2 pr-4 text-left text-[12px] text-gray-400 font-medium w-[160px]" />
                <th className="py-2 pr-4 text-left text-[13px] font-bold text-[#1B3A6B]">
                  🏫 EPIK / GEPIK
                </th>
                <th className="py-2 text-left text-[13px] font-bold text-purple-700">
                  📚 Hagwon
                </th>
              </tr>
            </thead>
            <tbody>
              <Row
                label="Base Monthly"
                epik={
                  <span>
                    ₩2,100,000 – ₩3,000,000
                    <br />
                    <span className="text-[11px] text-gray-400">
                      Grade 3 → Grade 1++ (experience-based)
                    </span>
                  </span>
                }
                hagwon={
                  <span>
                    ₩2,200,000 – ₩3,200,000+
                    <br />
                    <span className="text-[11px] text-gray-400">
                      Negotiable; premium pay at leading academies
                    </span>
                  </span>
                }
              />
              <Row
                label="Entry Bonus"
                epik="₩1,800,000 (paid end of 1st month)"
                hagwon="₩0 – ₩1,000,000 (varies by school)"
                highlight="epik"
              />
              <Row
                label="Completion Bonus"
                epik="₩1,300,000 per contract"
                hagwon="Usually none — check contract"
                highlight="epik"
              />
              <Row
                label="Renewal Bonus"
                epik={
                  <span>
                    ₩700,000/yr (up to ₩2,000,000 in Gyeonggi)
                  </span>
                }
                hagwon="Salary increase only (no fixed bonus)"
                highlight="epik"
              />
              <Row
                label="Severance Pay"
                epik="~1 month salary (legally required)"
                hagwon="1 month / year worked (legally required)"
                highlight="both"
              />
              <Row
                label="Settlement Allow."
                epik="₩300,000 (one-time, on arrival)"
                hagwon="Rare"
                highlight="epik"
              />
              <Row
                label="Rural Allowance"
                epik="₩100,000/mo (township schools)"
                hagwon="N/A"
              />
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Housing & Daily Life">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-gray-200">
                <th className="py-2 pr-4 text-left text-[12px] text-gray-400 font-medium w-[160px]" />
                <th className="py-2 pr-4 text-left text-[13px] font-bold text-[#1B3A6B]">
                  🏫 EPIK / GEPIK
                </th>
                <th className="py-2 text-left text-[13px] font-bold text-purple-700">
                  📚 Hagwon
                </th>
              </tr>
            </thead>
            <tbody>
              <Row
                label="Housing"
                epik="Free apartment provided by school/MOE (utilities excluded)"
                hagwon="Provided or monthly allowance ₩200,000–₩500,000"
              />
              <Row
                label="Health Insurance"
                epik="50% employer-paid (National Health Insurance)"
                hagwon="50% employer-paid (National Health Insurance)"
                highlight="both"
              />
              <Row
                label="Pension"
                epik="National Pension — employer matches 4.5%"
                hagwon="National Pension — employer matches 4.5%"
                highlight="both"
              />
              <Row
                label="Work Hours"
                epik={
                  <span>
                    ~22 teaching hrs/wk · 8-hour day
                    <br />
                    <span className="text-[11px] text-gray-400">No evenings or weekends</span>
                  </span>
                }
                hagwon={
                  <span>
                    ~30 teaching hrs/wk
                    <br />
                    <span className="text-[11px] text-gray-400">
                      Afternoon–evening; Saturday possible
                    </span>
                  </span>
                }
              />
              <Row
                label="Paid Leave"
                epik="School holidays — winter/summer vacation included"
                hagwon="10 days paid vacation + national holidays"
                highlight="epik"
              />
              <Row
                label="Class Size"
                epik="20–35 students per class"
                hagwon={
                  <span>
                    6–20 students (small group or 1-on-1)
                    <br />
                    <span className="text-[11px] text-gray-400">
                      Smaller = more interaction, easier management
                    </span>
                  </span>
                }
              />
              <Row
                label="Lesson Planning"
                epik="Flexible — co-teach with Korean English teacher"
                hagwon="Provided curriculum; some autonomy"
              />
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Requirements & Eligibility">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-gray-200">
                <th className="py-2 pr-4 text-left text-[12px] text-gray-400 font-medium w-[160px]" />
                <th className="py-2 pr-4 text-left text-[13px] font-bold text-[#1B3A6B]">
                  🏫 EPIK / GEPIK
                </th>
                <th className="py-2 text-left text-[13px] font-bold text-purple-700">
                  📚 Hagwon
                </th>
              </tr>
            </thead>
            <tbody>
              <Row
                label="Degree"
                epik="Bachelor's degree (any field)"
                hagwon="Bachelor's degree (any field)"
                highlight="both"
              />
              <Row
                label="Citizenship"
                epik="7 English-speaking countries only (US, UK, CA, AU, NZ, SA, IE)"
                hagwon={
                  <span>
                    Same E-2 countries — or F-visa holders
                    <br />
                    <span className="text-[11px] text-gray-400">
                      F-2 / F-4 / F-6 welcome at most hagwon
                    </span>
                  </span>
                }
              />
              <Row
                label="TEFL/TESOL"
                epik="Required for Grade advancement (100+ hrs)"
                hagwon="Helpful but not always required"
              />
              <Row
                label="Experience"
                epik="1–2 yrs for higher salary grade (Grade 1+)"
                hagwon="Preferred; affects negotiated salary"
              />
              <Row
                label="Criminal Check"
                epik="FBI/police clearance required"
                hagwon="FBI/police clearance required"
                highlight="both"
              />
              <Row
                label="Medical Check"
                epik="Required before placement"
                hagwon="Required (E-2 visa process)"
                highlight="both"
              />
              <Row
                label="Application Window"
                epik={
                  <span>
                    Mar–Apr (fall intake) · Aug–Oct (spring intake)
                    <br />
                    <span className="text-[11px] text-gray-400">
                      Apply 3–6 months in advance
                    </span>
                  </span>
                }
                hagwon="Year-round openings"
                highlight="hagwon"
              />
              <Row
                label="Contract Length"
                epik="1 year (renewable up to 3 yrs)"
                hagwon="1 year standard (renewable)"
                highlight="both"
              />
            </tbody>
          </table>
        </div>
      </Section>

      {/* Pros / Cons */}
      <Section title="Pros &amp; Cons at a Glance">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">

          {/* EPIK pros/cons */}
          <div className="rounded-xl border border-gray-200 overflow-hidden">
            <div className="bg-[#1B3A6B] text-white px-4 py-3 text-[13px] font-semibold">
              🏫 EPIK / Public School
            </div>
            <div className="p-4 space-y-2 text-[13px]">
              <p className="font-semibold text-gray-500 text-[11px] uppercase tracking-wide mb-1">
                Pros
              </p>
              {[
                'Generous entry & completion bonuses',
                'Free housing (big financial advantage)',
                'School hours only — no evenings/weekends',
                'Long vacation: summer, winter, national holidays',
                'Orientation & support provided',
                'Transparent, standardized contracts',
              ].map((p) => (
                <p key={p} className="flex gap-2 text-gray-700">
                  <span className="text-green-500 mt-0.5 shrink-0">✓</span> {p}
                </p>
              ))}
              <p className="font-semibold text-gray-500 text-[11px] uppercase tracking-wide mt-3 mb-1">
                Cons
              </p>
              {[
                'Competitive application (limited spots)',
                'Placement region not always your choice',
                'Lower base salary than top hagwon',
                'Class sizes can be large (25–35)',
                'Application window twice a year only',
              ].map((c) => (
                <p key={c} className="flex gap-2 text-gray-600">
                  <span className="text-red-400 mt-0.5 shrink-0">✗</span> {c}
                </p>
              ))}
            </div>
          </div>

          {/* Hagwon pros/cons */}
          <div className="rounded-xl border border-gray-200 overflow-hidden">
            <div className="bg-purple-700 text-white px-4 py-3 text-[13px] font-semibold">
              📚 Private Hagwon
            </div>
            <div className="p-4 space-y-2 text-[13px]">
              <p className="font-semibold text-gray-500 text-[11px] uppercase tracking-wide mb-1">
                Pros
              </p>
              {[
                'Higher base salary possible at premium schools',
                'Year-round hiring — start when ready',
                'Smaller classes, more teacher–student interaction',
                'Choose your city / school type',
                'Faster to negotiate and start',
              ].map((p) => (
                <p key={p} className="flex gap-2 text-gray-700">
                  <span className="text-green-500 mt-0.5 shrink-0">✓</span> {p}
                </p>
              ))}
              <p className="font-semibold text-gray-500 text-[11px] uppercase tracking-wide mt-3 mb-1">
                Cons
              </p>
              {[
                'Evening/weekend hours common',
                'Housing not always included',
                'No guaranteed entry/completion bonus',
                'Quality varies widely — vet the school',
                'Only 10 days vacation (vs school calendar)',
              ].map((c) => (
                <p key={c} className="flex gap-2 text-gray-600">
                  <span className="text-red-400 mt-0.5 shrink-0">✗</span> {c}
                </p>
              ))}
            </div>
          </div>
        </div>
      </Section>

      {/* EPIK salary grade table */}
      <Section title="EPIK Salary Grade Table (2026)">
        <p className="text-[13px] text-gray-500 mb-4">
          Based on the official EPIK/GEPIK schedule. Grade is determined by education, experience,
          and certification at the time of application.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-[13px] border-collapse">
            <thead>
              <tr className="bg-gray-50 border-y border-gray-200">
                <th className="py-2 px-3 text-left font-semibold text-gray-600">Grade</th>
                <th className="py-2 px-3 text-left font-semibold text-gray-600">Monthly (KRW)</th>
                <th className="py-2 px-3 text-left font-semibold text-gray-600">Typical qualifier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {[
                ['1++ (S/A)', '₩2,600,000 – ₩3,000,000', 'Master\'s + 3+ yrs exp, or teaching license'],
                ['1+ (B)', '₩2,500,000 – ₩2,600,000', 'TEFL 100hrs + 1–2 yrs exp + degree in Education'],
                ['1 (C)', '₩2,400,000 – ₩2,600,000', 'TEFL 100hrs + 1+ yr exp'],
                ['2+ (D)', '₩2,300,000 – ₩2,400,000', 'TEFL 100hrs or relevant teaching exp'],
                ['2 (E)', '₩2,200,000 – ₩2,350,000', 'Bachelor\'s, no prior teaching req.'],
                ['3', '₩2,100,000 – ₩2,200,000', 'Entry level'],
              ].map(([grade, pay, note]) => (
                <tr key={grade}>
                  <td className="py-2.5 px-3 font-semibold text-[#1B3A6B]">{grade}</td>
                  <td className="py-2.5 px-3 font-semibold">{pay}</td>
                  <td className="py-2.5 px-3 text-gray-500">{note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[12px] text-gray-400 mt-3">
          * Ranges reflect national EPIK + GEPIK (Gyeonggi) variance. Seoul (SMOE) may differ slightly.
          Always verify with the official EPIK website before applying.
        </p>
      </Section>

      {/* Quick tips */}
      <Section title="Quick Tips for Choosing">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-[13px]">
          {[
            {
              icon: '🏖',
              title: 'Want max vacation & stability?',
              body: 'Go EPIK. School holidays add up to 3–4 months/year of downtime.',
            },
            {
              icon: '💰',
              title: 'Want to maximize take-home pay?',
              body: 'Target a premium hagwon — higher base + free housing can beat EPIK total.',
            },
            {
              icon: '📍',
              title: 'Want to choose your city?',
              body: 'Hagwon gives you full flexibility. EPIK places you within a province.',
            },
          ].map((tip) => (
            <div key={tip.title} className="rounded-lg bg-gray-50 border border-gray-200 p-4">
              <p className="text-2xl mb-2">{tip.icon}</p>
              <p className="font-semibold text-gray-800 mb-1">{tip.title}</p>
              <p className="text-gray-600 leading-relaxed">{tip.body}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* CTA */}
      <div className="rounded-xl bg-[#1B3A6B] text-white p-6 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex-1">
          <p className="font-semibold text-base mb-1">Ready to find your school?</p>
          <p className="text-sm text-white/70">
            BRIDGE connects teachers with vetted schools — both public programs and premium hagwon
            across Korea.
          </p>
        </div>
        <div className="flex gap-3 shrink-0">
          <Link
            href="/jobs"
            className="inline-block bg-white text-[#1B3A6B] font-semibold text-sm px-5 py-2.5 rounded-lg hover:bg-gray-100 transition"
          >
            Browse Jobs
          </Link>
          <Link
            href="/apply"
            className="inline-block border border-white/40 text-white font-semibold text-sm px-5 py-2.5 rounded-lg hover:bg-white/10 transition"
          >
            Apply Now
          </Link>
        </div>
      </div>

      {/* Disclaimer */}
      <p className="mt-8 text-[11px] text-gray-400 leading-relaxed">
        Salary figures are based on 2026 EPIK/GEPIK official schedules and BRIDGE market data.
        Hagwon figures represent industry averages and vary by school, location, and experience.
        Always review your contract carefully.{' '}
        <a
          href="https://www.epik.go.kr"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-gray-600"
        >
          Official EPIK site →
        </a>
      </p>
    </div>
  )
}
