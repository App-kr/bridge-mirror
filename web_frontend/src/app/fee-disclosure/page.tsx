import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'BRIDGE 수수료 공시 / Fee Disclosure',
  description:
    'BRIDGE 채용 수수료 정책 — 법정 상한 준수 · 구직자 무료 · 90일 보증',
  alternates: { canonical: '/fee-disclosure' },
  openGraph: {
    title: 'BRIDGE Fee Disclosure',
    description: 'Transparent recruitment fees · 90-day guarantee · No fee from candidates',
  },
}

const FEES = [
  {
    type: '초·중·고등학교 (공립·사립)',
    typeEn: 'K-12 Schools (Public & Private)',
    detail: '교육청(SMOE·GEPIK·GOE 등) · 사립학교',
    detailEn: 'Provincial OE, private schools',
    fee: '협의',
    feeEn: 'To be negotiated',
    cap: '연봉의 7.5% (약 1개월 급여) / 7.5% of annual salary',
  },
  {
    type: '어학원 / 영어유치원',
    typeEn: 'Academies / English Kindergartens',
    detail: '사설 교육기관',
    detailEn: 'Private institutes',
    fee: '협의',
    feeEn: 'To be negotiated',
    cap: '연봉의 7.5% (약 1개월 급여) / 7.5% of annual salary',
  },
  {
    type: '국제학교 / 대학교',
    typeEn: 'International Schools / Universities',
    detail: '국제학교 · 대학 · 공공 교육기관',
    detailEn: 'International schools, universities, public education',
    fee: '약 1개월 급여',
    feeEn: '~1 month salary',
    cap: '연봉의 7.5% (약 1개월 급여) / 7.5% of annual salary',
  },
  {
    type: '헤드헌팅 / 특수 프로그램',
    typeEn: 'Headhunting / Special Programs',
    detail: '기업 임원 · 특수 전문인력 · 지자체 특수목적 프로그램',
    detailEn: 'Executives, specialists, regional programs',
    fee: '사례별 협의',
    feeEn: 'Case-by-case',
    cap: '연봉의 10~15% / 10–15% of annual salary',
  },
]

const GUARANTEE_MATRIX = [
  {
    reason: '개인 사유 (가족 사정 등)',
    reasonEn: 'Personal reasons (family, etc.)',
    fault: '교사 / Teacher',
    cost: '무료 재선발 / Free replacement',
  },
  {
    reason: '객관적 업무 능력 부족 (명백한 계약 불이행)',
    reasonEn: 'Demonstrable inability / contract breach',
    fault: '교사 / Teacher',
    cost: '무료 재선발 / Free replacement',
  },
  {
    reason: '건강 문제 (질병·사고 등 불가항력)',
    reasonEn: 'Health (illness, accident — force majeure)',
    fault: '불가항력 / Force majeure',
    cost: '무료 재선발 / Free replacement',
  },
  {
    reason: '근로조건 불이행 (급여 미지급 등)',
    reasonEn: 'Employer breach (unpaid salary, etc.)',
    fault: '기관 / Institution',
    cost: '유료 재선발 / Paid replacement',
  },
  {
    reason: '경영상 필요 (반 폐강·학원 폐업 등)',
    reasonEn: 'Business necessity (class closure, shutdown)',
    fault: '기관 / Institution',
    cost: '유료 재선발 / Paid replacement',
  },
  {
    reason: '근무 환경 문제 (안전·괴롭힘 등)',
    reasonEn: 'Workplace issues (safety, harassment, etc.)',
    fault: '기관 / Institution',
    cost: '유료 재선발 / Paid replacement',
  },
]

const ADD_ONS = [
  { ko: '면접 대행 (기관 대리 면접 진행, 평가서 작성)', en: 'Interview proxy (conducting + evaluation report)' },
  { ko: '통역 서비스 (채용 과정 또는 근무 중 통역)', en: 'Interpretation service (recruitment or on-site)' },
  { ko: '추가 서류 대행 (TB Test, 학위 아포스티유, 제3국 범죄경력 조회 등)', en: 'Additional documents (TB test, apostille, third-country background)' },
  { ko: '긴급 채용 (표준 절차 단축)', en: 'Urgent hiring (expedited process)' },
  { ko: '교육 프로그램 기획 (커리큘럼 컨설팅)', en: 'Curriculum consulting' },
  { ko: '근태·인재 관리 대행 (별도 약정)', en: 'Attendance/talent management (separate agreement)' },
]

export default function FeeDisclosurePage() {
  return (
    <main className="bg-white min-h-screen">
      <div className="max-w-4xl mx-auto px-5 sm:px-8 py-10 sm:py-16">
        {/* Header */}
        <header className="mb-10 text-center">
          <span className="inline-block text-xs font-semibold text-blue-600 bg-blue-50 border border-blue-200 rounded-full px-3 py-1 uppercase tracking-wider">
            Public Disclosure / 공시
          </span>
          <h1 className="mt-3 text-3xl sm:text-4xl font-black text-gray-900 leading-tight">
            BRIDGE 수수료 공시 <span className="block text-xl sm:text-2xl mt-1 text-gray-500 font-bold">Fee Disclosure</span>
          </h1>
          <p className="mt-4 text-base text-gray-600 leading-relaxed">
            투명하고 합리적인 수수료 정책 · 법정 상한선 준수 · 90일 보증
            <br />
            <span className="text-sm text-gray-500">Transparent fees · Statutory cap compliance · 90-day guarantee</span>
          </p>
        </header>

        {/* Legal status */}
        <section className="mb-10 p-6 border border-blue-100 bg-blue-50/40 rounded-2xl">
          <h2 className="text-lg font-bold text-gray-900 mb-3">법인 정보 / Legal Information</h2>
          <dl className="grid sm:grid-cols-2 gap-3 text-sm text-gray-700">
            <div>
              <dt className="font-semibold">상호 / Company</dt>
              <dd>BRIDGE [정식 상호 등록 후 갱신]</dd>
            </div>
            <div>
              <dt className="font-semibold">대표자 / Representative</dt>
              <dd>[대표자명]</dd>
            </div>
            <div>
              <dt className="font-semibold">사업자등록번호 / Business Reg. No.</dt>
              <dd>[XXX-XX-XXXXX]</dd>
            </div>
            <div>
              <dt className="font-semibold">유료직업소개사업자 등록번호 / Paid Job-Placement Reg.</dt>
              <dd>[관할 시·군·구청 등록 후 갱신]</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="font-semibold">소재지 / Address</dt>
              <dd>[사업장 주소]</dd>
            </div>
            <div>
              <dt className="font-semibold">이메일 / Email</dt>
              <dd>
                <a href="mailto:bridgejobkr@gmail.com" className="text-blue-600 underline">
                  bridgejobkr@gmail.com
                </a>
              </dd>
            </div>
            <div>
              <dt className="font-semibold">웹사이트 / Website</dt>
              <dd>bridgejob.co.kr</dd>
            </div>
          </dl>
          <p className="mt-4 text-xs text-gray-500 leading-relaxed">
            ※ BRIDGE는 고용노동부에 정식 등록된 유료직업소개사업자입니다. (직업안정법 §19)
            <br />
            ※ Registered paid job-placement service under the Korean Employment Stability Act §19.
          </p>
        </section>

        {/* Statutory cap */}
        <section className="mb-10 p-6 border border-amber-200 bg-amber-50/40 rounded-2xl">
          <h2 className="text-lg font-bold text-gray-900 mb-3">법정 상한 / Statutory Cap</h2>
          <p className="text-sm text-gray-700 leading-relaxed mb-3">
            고용노동부 「국내유료직업소개요금 등 고시」에 따라, <strong>3개월 이상 근로계약</strong>의 경우 구인자가 부담하는 법정 요금 상한은
            <strong> 3개월 임금의 30% 이하</strong>입니다. 이는 연봉 기준 약 <strong>7.5%</strong>이며, 대략 1개월 급여에 준합니다.
          </p>
          <p className="text-xs text-gray-600 leading-relaxed">
            Per the Korean Ministry of Employment & Labor notice, for employment contracts of 3+ months,
            the employer-borne fee shall not exceed <strong>30% of 3-month wages</strong> (~<strong>7.5% of annual salary</strong>).
          </p>
          <div className="mt-4 p-3 bg-white border border-amber-300 rounded-lg">
            <p className="text-sm font-bold text-gray-900">
              ✓ 구직자(강사)로부터는 어떠한 비용도 받지 않습니다.
            </p>
            <p className="text-xs text-gray-600 mt-1">
              ✓ No fee is charged to job seekers (teachers) — per Employment Stability Act §47.
            </p>
          </div>
        </section>

        {/* Fee table */}
        <section className="mb-10">
          <h2 className="text-lg font-bold text-gray-900 mb-4">기관 유형별 기본 수수료 / Standard Fees by Institution</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
              <thead className="bg-gray-50 text-gray-700">
                <tr>
                  <th className="text-left px-4 py-3 font-semibold">기관 유형 / Type</th>
                  <th className="text-left px-4 py-3 font-semibold">기본 수수료 / Base Fee</th>
                  <th className="text-left px-4 py-3 font-semibold">법정 상한 / Cap</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {FEES.map((f) => (
                  <tr key={f.type} className="bg-white">
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{f.type}</div>
                      <div className="text-xs text-gray-500">{f.typeEn}</div>
                      <div className="mt-1 text-xs text-gray-500">{f.detail}<br /><span className="text-gray-400">{f.detailEn}</span></div>
                    </td>
                    <td className="px-4 py-3 align-top">
                      <div className="font-bold text-blue-700">{f.fee}</div>
                      <div className="text-xs text-gray-500">{f.feeEn}</div>
                    </td>
                    <td className="px-4 py-3 align-top text-xs text-gray-600">{f.cap}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-gray-500">
            모든 수수료는 표준 채용절차 기준이며, 사전 협의 없이 추가 비용이 발생하지 않습니다.
            <br />
            All fees are based on the standard recruitment process. No additional charges without prior agreement.
          </p>
        </section>

        {/* Add-ons */}
        <section className="mb-10">
          <h2 className="text-lg font-bold text-gray-900 mb-3">부가 서비스 / Optional Add-on Services</h2>
          <ul className="space-y-2">
            {ADD_ONS.map((a) => (
              <li key={a.ko} className="flex items-start gap-3 text-sm">
                <span className="text-blue-500 mt-0.5">✓</span>
                <div>
                  <div className="text-gray-800">{a.ko}</div>
                  <div className="text-xs text-gray-500">{a.en}</div>
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-gray-500 leading-relaxed">
            부가 서비스는 전담 매니저와 사전 상담 후 계약서에 명시한 금액으로만 청구됩니다.
            <br />
            Optional services are billed only at amounts specified in the contract after prior consultation.
          </p>
        </section>

        {/* Payment timing */}
        <section className="mb-10 p-6 border border-gray-200 rounded-2xl">
          <h2 className="text-lg font-bold text-gray-900 mb-3">청구 시점 / Payment Schedule</h2>
          <div className="space-y-3 text-sm">
            <div className="flex items-start gap-3">
              <span className="shrink-0 w-20 text-xs font-semibold text-gray-600">일반 / Private</span>
              <p className="text-gray-700">
                분할 (50% + 50%): 채용 확정 시 50% · 입국 및 근무 개시 후 50% 잔금
                <br />
                <span className="text-xs text-gray-500">Split: 50% on confirmation + 50% after work commencement</span>
              </p>
            </div>
            <div className="flex items-start gap-3">
              <span className="shrink-0 w-20 text-xs font-semibold text-gray-600">공공 / Public</span>
              <p className="text-gray-700">
                일시불 (100%): 채용 확정 시 (또는 사전 약정에 따라 근무 개시 후)
                <br />
                <span className="text-xs text-gray-500">Lump sum (100%): on confirmation or per agreement</span>
              </p>
            </div>
          </div>
        </section>

        {/* Payment methods */}
        <section className="mb-10">
          <h2 className="text-lg font-bold text-gray-900 mb-3">결제 수단 및 증빙 / Payment Methods & Documents</h2>
          <ul className="grid sm:grid-cols-2 gap-2 text-sm">
            <li className="flex items-center gap-2"><span className="text-green-600">✅</span> 계좌이체 / Bank transfer</li>
            <li className="flex items-center gap-2"><span className="text-red-500">❌</span> 카드 결제 / Card payment (unavailable)</li>
            <li className="flex items-center gap-2"><span className="text-green-600">✅</span> 현금영수증 즉시 발급 / Cash receipt</li>
            <li className="flex items-center gap-2"><span className="text-green-600">✅</span> 세금계산서 (부가세 면세) / Tax invoice (VAT-exempt)</li>
            <li className="flex items-center gap-2"><span className="text-green-600">✅</span> 조달청 나라장터 (공공) / G2B for public</li>
          </ul>
        </section>

        {/* 90-day guarantee */}
        <section className="mb-10 p-6 border-2 border-blue-200 bg-blue-50/30 rounded-2xl">
          <h2 className="text-lg font-bold text-gray-900 mb-3">90일 보증 정책 / 90-Day Replacement Guarantee</h2>
          <p className="text-sm text-gray-700 leading-relaxed mb-4">
            입국 후 90일 이내 조기 퇴사 발생 시 귀책 사유에 따라 재선발을 지원합니다. 근로기준법상 정상적인 계약 해지 사유에 한합니다.
            <br />
            <span className="text-xs text-gray-500">
              If early departure occurs within 90 days of arrival, replacement is provided based on the cause of separation,
              subject to the Korean Labor Standards Act.
            </span>
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border border-blue-200 rounded-lg overflow-hidden">
              <thead className="bg-blue-100/50 text-gray-700">
                <tr>
                  <th className="text-left px-3 py-2 font-semibold">해지 사유 / Reason</th>
                  <th className="text-left px-3 py-2 font-semibold">귀책 / Fault</th>
                  <th className="text-left px-3 py-2 font-semibold">재선발 / Replacement</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-blue-100 bg-white">
                {GUARANTEE_MATRIX.map((g) => (
                  <tr key={g.reason}>
                    <td className="px-3 py-2">
                      <div className="text-gray-900">{g.reason}</div>
                      <div className="text-xs text-gray-500">{g.reasonEn}</div>
                    </td>
                    <td className="px-3 py-2 text-xs">{g.fault}</td>
                    <td className="px-3 py-2 text-xs font-medium">{g.cost}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Scope */}
        <section className="mb-10 p-6 border border-gray-200 rounded-2xl">
          <h2 className="text-lg font-bold text-gray-900 mb-3">업무 범위 / Scope of Service</h2>
          <p className="text-sm text-gray-700 leading-relaxed">
            BRIDGE는 채용 기관에서 근무할 전문인재(근로자)의 <strong>홍보·모집·선발·채용(서류 취합·검증·체류자격 신청 보조·온보딩)</strong> 업무를 수행합니다.
            실제 근무 시 <strong>근태 관리와 인재 육성은 기관(고용주)이 책임</strong>집니다.
          </p>
          <p className="text-xs text-gray-500 leading-relaxed mt-3">
            BRIDGE performs <strong>recruitment, screening, hiring (document collection/verification, visa assistance, onboarding)</strong>.
            <strong> Attendance management and talent development remain the institution&apos;s (employer&apos;s) responsibility.</strong>
          </p>
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm font-bold text-red-900">
              ⚠️ BRIDGE는 파견사업자가 아닙니다. (근로자파견법 적용 대상 아님)
            </p>
            <p className="text-xs text-red-700 mt-1">
              ⚠️ BRIDGE is NOT a temporary staffing agency under the Worker Dispatch Act.
            </p>
          </div>
        </section>

        {/* Re-selection process */}
        <section className="mb-10">
          <h2 className="text-lg font-bold text-gray-900 mb-4">재선발 신청 절차 / Replacement Request Process</h2>
          <ol className="space-y-3">
            {[
              { step: 1, ko: '즉시 연락 — support@bridgejob.co.kr 또는 고객센터', en: 'Immediate contact via email or support' },
              { step: 2, ko: '귀책 판단 — 5~7 영업일 내 사실관계 검토', en: 'Fault assessment within 5–7 business days' },
              { step: 3, ko: '결과 통보 — 재선발 지원 여부 및 비용 부담 조건 서면 안내', en: 'Written notice of replacement eligibility & cost terms' },
              { step: 4, ko: '재선발 진행 — 동의 시 새로운 후보자 추천 즉시 재개', en: 'Replacement begins upon agreement' },
            ].map((s) => (
              <li key={s.step} className="flex items-start gap-3 text-sm">
                <span className="shrink-0 w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">
                  {s.step}
                </span>
                <div>
                  <div className="text-gray-800">{s.ko}</div>
                  <div className="text-xs text-gray-500">{s.en}</div>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {/* Exceptions */}
        <section className="mb-10 p-6 border border-red-200 bg-red-50/30 rounded-2xl">
          <h2 className="text-lg font-bold text-red-900 mb-3">재선발 불가 / 부분 환불 / Non-Replacement Cases</h2>
          <ul className="space-y-2 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-red-500">•</span>
              <span>
                타 업체를 통해 원어민 강사를 채용하기로 결정한 경우 — <strong>부분 환불 (50%)</strong>
                <br />
                <span className="text-xs text-gray-600">Hiring through another agency — 50% refund</span>
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-red-500">•</span>
              <span>
                채용 조건(급여·근무시간·위치 등) 변경하여 새로운 포지션으로 채용 — <strong>재선발 불가</strong>
                <br />
                <span className="text-xs text-gray-600">Modified job conditions → no replacement</span>
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-red-500">•</span>
              <span>
                포지션 폐쇄·채용 중단 — <strong>재선발 불가</strong>
                <br />
                <span className="text-xs text-gray-600">Position closure → no replacement</span>
              </span>
            </li>
          </ul>
          <p className="mt-4 p-3 bg-white border border-red-300 rounded-lg text-xs text-red-700 leading-relaxed">
            ⚠️ 채용 확정 후 &ldquo;주관적 수업 만족도&rdquo;는 재선발 대상이 아닙니다. BRIDGE는 채용 과정에서 객관적 자격(학위·비자·경력·범죄경력)만 검증합니다.
            <br />
            ⚠️ Subjective lesson satisfaction after hire is not grounds for replacement. BRIDGE verifies only objective qualifications.
          </p>
        </section>

        {/* Footer */}
        <footer className="text-center text-xs text-gray-400 pt-8 border-t border-gray-100">
          최종 갱신 / Last updated: 2026-05-12
          <br />
          본 공시는 직업안정법 및 고용노동부 고시에 따라 게시됩니다.
          <br />
          Published in accordance with the Korean Employment Stability Act and MOEL notices.
        </footer>
      </div>
    </main>
  )
}
