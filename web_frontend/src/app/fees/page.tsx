import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: '요금안내 · Fee Disclosure | BRIDGE Recruitment',
  description: 'BRIDGE Recruitment 유료직업소개요금 공시 — 직업안정법 제19조 및 고용노동부고시 제2017-22호 근거.',
}

export default function FeesPage() {
  return (
    <div className="max-w-[860px] mx-auto px-4 sm:px-6 py-12 text-[#1d1d1f]">

      {/* Header */}
      <div className="mb-10 pb-6 border-b border-gray-200">
        <span className="inline-block text-[11px] font-semibold text-gray-500 border border-gray-300 rounded px-2 py-0.5 mb-4">Legal · Fee Disclosure</span>
        <h1 className="text-3xl font-bold mb-2">요금안내</h1>
        <p className="text-sm text-gray-500">Fee Disclosure &nbsp;|&nbsp; 시행일: 2021년 06월</p>
        <p className="mt-4 text-sm text-gray-600 leading-relaxed">
          본 요금표는 <strong>「직업안정법」 제19조</strong> 및{' '}
          <strong>「고용노동부고시 제2017-22호(국내 유료직업소개요금 등 고시)」</strong>에 근거하여 공개합니다.
          모든 금액은 표준 절차 기준이며, 사전 협의 없이 추가 비용이 발생하지 않습니다.
        </p>
      </div>

      <div className="space-y-10 text-sm text-gray-700 leading-7">

        <Article num="제1조" title="적용 법규">
          <p>
            BRIDGE는 「직업안정법」 제19조에 따라 등록된 유료직업소개사업자로서, 같은 법 및
            「고용노동부고시 제2017-22호」에서 정한 상한 범위 내에서 소개요금을 청구합니다.
          </p>
        </Article>

        <Article num="제2조" title="법정 수수료 상한">
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-[13px] border-collapse border border-gray-200 rounded-lg overflow-hidden">
              <thead>
                <tr className="bg-gray-50">
                  <th className="border border-gray-200 px-3 py-2 text-left font-semibold text-gray-700">구분</th>
                  <th className="border border-gray-200 px-3 py-2 text-left font-semibold text-gray-700">고용기간 3개월 미만</th>
                  <th className="border border-gray-200 px-3 py-2 text-left font-semibold text-gray-700">고용기간 3개월 이상</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr>
                  <td className="border border-gray-200 px-3 py-2 font-semibold text-gray-800">구인자 부담</td>
                  <td className="border border-gray-200 px-3 py-2">고용기간 중 지급받기로 한 임금의 <strong>100분의 30 이하</strong></td>
                  <td className="border border-gray-200 px-3 py-2">3개월간 지급받기로 한 임금의 <strong>100분의 30 이하</strong></td>
                </tr>
                <tr>
                  <td className="border border-gray-200 px-3 py-2 font-semibold text-gray-800">구직자 부담</td>
                  <td className="border border-gray-200 px-3 py-2">고용기간 중 지급받기로 한 임금의 <strong>100분의 1 이하</strong></td>
                  <td className="border border-gray-200 px-3 py-2">3개월간 지급받기로 한 임금의 <strong>100분의 1 이하</strong></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-[13px] text-gray-500">
            구직자 수수료는 법령상 청구가 허용되나, 서면 동의 및 근로계약 체결 후에만 부과될 수 있습니다.
          </p>
        </Article>

        <Article num="제3조" title="BRIDGE 표준 요금">
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-[13px] border-collapse border border-gray-200 rounded-lg overflow-hidden">
              <thead>
                <tr className="bg-gray-50">
                  <th className="border border-gray-200 px-3 py-2 text-left font-semibold text-gray-700">기관 구분</th>
                  <th className="border border-gray-200 px-3 py-2 text-left font-semibold text-gray-700">소개요금 (VAT 별도)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr>
                  <td className="border border-gray-200 px-3 py-2">일반 학원 · 영어유치원</td>
                  <td className="border border-gray-200 px-3 py-2 font-semibold">150만원</td>
                </tr>
                <tr>
                  <td className="border border-gray-200 px-3 py-2">영어교육기관 · 학교</td>
                  <td className="border border-gray-200 px-3 py-2 font-semibold">200만원</td>
                </tr>
                <tr>
                  <td className="border border-gray-200 px-3 py-2">국제학교 · 공공기관</td>
                  <td className="border border-gray-200 px-3 py-2">고시요율에 따름</td>
                </tr>
                <tr>
                  <td className="border border-gray-200 px-3 py-2">임원 · 전문인력</td>
                  <td className="border border-gray-200 px-3 py-2 font-semibold">1개월 급여</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-[13px] text-gray-600">
            본 요금은 인재 선발 전 과정 — 소싱, 비자 안내, 담당자 면접 및 면접 조율, 계약 상담 — 을 포함한 서비스 대가입니다.
          </p>
        </Article>

        <Article num="제4조" title="지급 시점 및 방법">
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-[13px] border-collapse border border-gray-200 rounded-lg overflow-hidden">
              <thead>
                <tr className="bg-gray-50">
                  <th className="border border-gray-200 px-3 py-2 text-left font-semibold text-gray-700">기관 구분</th>
                  <th className="border border-gray-200 px-3 py-2 text-left font-semibold text-gray-700">지급 방식</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr>
                  <td className="border border-gray-200 px-3 py-2">학원 · 유치원</td>
                  <td className="border border-gray-200 px-3 py-2">계약 체결 시 <strong>50%</strong> / 근로개시일(트레이닝 포함) <strong>50%</strong></td>
                </tr>
                <tr>
                  <td className="border border-gray-200 px-3 py-2">학교 · 공공기관</td>
                  <td className="border border-gray-200 px-3 py-2">근로개시일 <strong>100%</strong> 또는 사전 계약 협의</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Article>

        <Article num="제5조" title="알선(Matching) 완료의 기준">
          <ol className="list-decimal pl-5 space-y-2">
            <li>소개요금은 인력 관리 비용이 아니라, 적합한 인력을 <strong>알선한 행위</strong>에 대한 대가이다.</li>
            <li>소개된 인력이 <strong>1일이라도 근무</strong>를 시작한 경우 알선이 완료된 것으로 보며, 해당 기간에 대한 소개요금이 발생한다.</li>
            <li>근무 당일이라도 계약 해지(해고) 권리는 구인기관에 있으나, 이미 근무가 이루어진 일자에 대한 소개요금은 지급 대상이다.</li>
            <li>해고 없이 동일 인력을 계속 사용하면서 대체 인력을 별도로 요청하는 경우는 재매칭 지원 대상에서 제외된다.</li>
          </ol>
        </Article>

        <Article num="제6조" title="부가 서비스">
          <p>표준 절차 외 별도 요청에 한하여 제공하며, 요금은 건별 사전 견적으로 안내합니다.</p>
          <ul className="list-disc pl-5 mt-3 space-y-1 text-gray-600">
            <li>1:1 전담 안내 서비스</li>
            <li>긴급 채용 (절차 단축 및 최우선 매칭)</li>
            <li>서류 대행 (기본 제출 서류 외 추가 요청 시)</li>
            <li>통역 서비스</li>
            <li>면접 대행 및 평가서 작성</li>
            <li>채용 기관 영상 촬영 (분 단위 요금 / 원본 미제공)</li>
          </ul>
        </Article>

        <Article num="제7조" title="재매칭">
          <p>
            근로개시일로부터 일정 기간 내 구직자 귀책으로 근로관계가 종료된 경우, 1회에 한하여 대체 인력을
            알선합니다. 적용 기간 및 조건은 개별 계약서에 명시합니다.
          </p>
        </Article>

        <Article num="제8조" title="환불">
          <p>
            근로개시일 이전에 기관의 사정으로 계약이 해지된 경우, 기지급분에서 실제 수행된 업무에 상당하는
            비용을 공제한 후 환불합니다. 세부 조건은 계약서에 따릅니다.
          </p>
        </Article>

        <Article num="제9조" title="사업자 정보">
          <div className="pl-4 border-l-2 border-gray-200 space-y-1 text-gray-600">
            <p>상호: BRIDGE Recruitment</p>
            <p>대표자: Scarlett</p>
            <p>사업자등록번호: 113-94-14997</p>
            <p>유료직업소개사업 등록번호: <span className="text-gray-400">(등록 정보 준비 중)</span></p>
            <p>소재지: <span className="text-gray-400">(공개 주소 준비 중)</span></p>
            <p>이메일: <a href="mailto:bridgejobkr@gmail.com" className="underline hover:text-gray-900">bridgejobkr@gmail.com</a></p>
          </div>
        </Article>

      </div>

      {/* Footer note */}
      <div className="mt-14 pt-6 border-t border-gray-200 text-xs text-gray-400 space-y-1">
        <p>
          관련 문서:{' '}
          <Link href="/terms" className="underline hover:text-gray-600">이용약관</Link>
          {' · '}
          <Link href="/privacy" className="underline hover:text-gray-600">개인정보처리방침</Link>
          {' · '}
          <Link href="/contact" className="underline hover:text-gray-600">문의하기</Link>
        </p>
        <p>본 요금표는 「직업안정법」 및 「고용노동부고시 제2017-22호」에 근거하며, 법령 개정 시 지체 없이 갱신됩니다.</p>
      </div>

    </div>
  )
}

function Article({ num, title, children }: { num: string; title: string; children: React.ReactNode }) {
  return (
    <section className="pt-8 border-t border-gray-100">
      <h2 className="text-base font-bold text-[#1d1d1f] mb-3">{num} ({title})</h2>
      <div className="space-y-3">{children}</div>
    </section>
  )
}
