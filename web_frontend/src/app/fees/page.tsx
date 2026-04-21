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
          <strong>「고용노동부고시 제2017-22호(국내 유료직업소개요금 등 고시)」</strong>에 근거함.
          모든 금액은 표준 절차 기준으로 업무에 따라 추가 요금이 발생할 수 있습니다.
        </p>
      </div>

      <div className="space-y-10 text-sm text-gray-700 leading-7">

        <Article num="제1조" title="법정 수수료 상한">
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
        </Article>

        <Article num="제2조" title="소개 요금표">
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
            본 요금은 인재 비자 안내, 담당자 면접 및 면접 조율, 계약 상담을 포함한 서비스 요금입니다.
          </p>
          <p className="mt-2 text-[13px] text-gray-600">
            할인 요금은 지급 기한 등을 준수하는 경우에만 제공 가능하며, 상세 내용은 계약 체결 시 별도 계약서로 안내됩니다.
          </p>
          <p className="mt-2 text-[13px] text-gray-500">
            *원어민 채용 이력이 없고, 사업자 등록이 되지 않은 기관은 서비스 진행료가 선불로 청구됩니다.
          </p>
          <p className="mt-4 text-[13px] text-gray-500">
            근로개시일 이전에 기관의 사정으로 계약이 해지된 경우, 실제 수행된 업무에 해당하는 수수료가 공제된 잔액이 환불됩니다. 세부 조건은 계약서에 따릅니다.
          </p>
        </Article>

        <Article num="제3조" title="지급 시점 및 방법">
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
                  <td className="border border-gray-200 px-3 py-2">
                    계약 체결 시 <strong>50%</strong> / 근로개시일(트레이닝 포함) <strong>50%</strong> / 또는 계약 체결 시 <strong>100%</strong>
                  </td>
                </tr>
                <tr>
                  <td className="border border-gray-200 px-3 py-2">학교 · 공공기관</td>
                  <td className="border border-gray-200 px-3 py-2">근로개시일 <strong>100%</strong> 또는 사전 계약 협의</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Article>

        <Article num="제4조" title="알선 완료의 기준">
          <ol className="list-decimal pl-5 space-y-2">
            <li>소개요금은 인력 관리 비용이 아니라, 적합한 인력을 <strong>알선한 행위</strong>에 대한 대가이다.</li>
            <li>인력이 현장에 배치되어 업무를 시작한 순간부터 알선 서비스의 효력이 발생하며, 이에 따른 수수료 지불 의무가 생긴다.</li>
            <li>근무 당일이라도 계약 해지(해고) 권리는 구인기관에 있으나, 이미 근무가 이루어진 일자에 대한 소개요금은 지급 대상이다.</li>
            <li>해고 없이 동일 인력을 계속 사용하면서 대체 인력이나 환불을 별도로 요청하는 경우는 서비스 지원 대상에서 제외된다.</li>
          </ol>
        </Article>

        <Article num="제5조" title="부가 서비스">
          <p>표준 절차 외 별도 요청에 한하여 제공하며, 요금은 건별 견적으로 안내합니다.</p>
          <ul className="list-disc pl-5 mt-3 space-y-1 text-gray-600">
            <li>통역 서비스</li>
            <li>협업 광고 서비스</li>
            <li>1:1 전담 안내 서비스</li>
            <li>면접 대행 및 평가서 작성</li>
            <li>긴급 채용 (절차 단축 및 최우선 매칭)</li>
            <li>서류 대행 (기본 제출 서류 외 추가 요청 시)</li>
            <li>채용 기관 사진 또는 영상 촬영 (분 단위 요금 / 원본 미제공)</li>
          </ul>
        </Article>

        <Article num="제6조" title="재매칭 서비스">
          <p>
            재매칭 서비스 제공 조건 및 기간 등은 요금의 정상납부, 공급계약서의 회신이 정상적으로 이루어진 경우 제공하는 서비스 항목이며 법적 의무가 아닙니다.
          </p>
          <p className="mt-2 text-gray-500">상세 내용은 개별 인력공급 계약서에 명시합니다.</p>
        </Article>

        <Article num="제7조" title="사업자 정보">
          <div className="pl-4 border-l-2 border-gray-200 space-y-1 text-gray-600">
            <p>상호: BRIDGE</p>
            <p>대표: 김혜신</p>
            <p>사업자등록번호: 113-94-14997</p>
            <p>유료직업소개사업 등록</p>
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
      <h2 className="text-base font-bold text-[#1d1d1f] mb-3">{num} {title}</h2>
      <div className="space-y-3">{children}</div>
    </section>
  )
}
