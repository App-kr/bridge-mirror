import Link from 'next/link'

export default function PrivacyPage() {
  return (
    <div className="max-w-[860px] mx-auto px-4 sm:px-6 py-12 text-[#1d1d1f]">

      {/* Header */}
      <div className="mb-10">
        <span className="inline-block text-[11px] font-semibold text-gray-500 border border-gray-300 rounded px-2 py-0.5 mb-4">Legal</span>
        <h1 className="text-3xl font-bold text-[#1d1d1f] mb-2">개인정보처리방침</h1>
        <p className="text-sm text-gray-400">시행일: 2021년 06월 21일 · BRIDGE Recruitment</p>
      </div>

      {/* Intro */}
      <p className="text-sm text-gray-700 leading-7 mb-10">
        본 방침은 「개인정보 보호법」 제30조에 따라 이용자의 개인정보가 어떻게 수집·이용·보관되는지 안내합니다.
      </p>

      <div className="space-y-10 text-sm text-gray-700 leading-7">

        <Article num="제1조" title="처리하는 개인정보 항목">
          <SubItem title="구인자 학교·기관 등">
            업체명, 설립정보, 주소, 고용주 성명, 담당자 성명, 연락처, SNS 연락처, 사업자등록번호, 계약정보, 상세 채용 요건 등 채용에 필요한 정보
          </SubItem>
        </Article>

        <Article num="제2조" title="개인정보의 처리 목적">
          <SubItem title="강사 채용 서비스">
            「직업안정법」에 따른 유료직업소개업 수행을 위하여 구직자 및 구인자의 정보를 수집·관리하고, 채용 절차 진행, 비자 및 취업 관련 서류 처리, 이메일 및 연락 발송을 목적으로 처리합니다.
          </SubItem>
          <SubItem title="구인 학교·기관 서비스">
            채용 의뢰 접수, 강사 소개, 계약 체결 지원 등 채용 서비스 전반의 업무 수행을 목적으로 처리합니다.
          </SubItem>
          <SubItem title="고충처리 및 분쟁 대응">
            민원 접수 및 처리, 분쟁 조정을 위한 기록 보존 등을 목적으로 처리합니다.
          </SubItem>
        </Article>

        <Article num="제3조" title="개인정보의 처리 및 보유 기간">
          <SubItem title="강사 채용 서비스">
            채용 서비스 계약 종료일로부터 관련 법령이 정하는 기간 동안 보유합니다.
          </SubItem>
          <SubItem title="구인 학교·기관 서비스">
            서비스 계약 종료 시까지 보유합니다.
          </SubItem>
          <SubItem title="법령에 따른 보유">
            관계 법령에서 보존 의무를 부과하는 경우, 해당 기간 동안 보관 후 파기합니다.
          </SubItem>
        </Article>

        <Article num="제4조" title="정보주체의 권리·의무 및 행사 방법">
          <p>이용자는 언제든지 개인정보 열람·정정·삭제·처리정지를 요청할 수 있으며, 이메일로 접수 시 지체 없이 처리합니다. 다만, 법령에 따라 보존이 필요한 정보의 삭제 요청은 거절될 수 있으며 해당 사유를 안내합니다.</p>
        </Article>

        <Article num="제5조" title="개인정보의 제3자 제공">
          <p>채용이 확정되는 경우, 근로계약 체결에 필요한 범위 내에서 해당 구인 학교·기관에 관련 정보를 제공합니다. 법령에 따른 요청이 있는 경우는 예외로 하며, 그 외에는 동의 없이 제3자에게 제공하지 않습니다.</p>
        </Article>

        <Article num="제6조" title="개인정보의 파기 절차 및 방법">
          <p>보유 기간이 경과하거나 처리 목적이 달성된 개인정보는 지체 없이 파기합니다. 전자적 파일은 복원 불가능한 방법으로 영구 삭제하며, 종이 문서는 분쇄 또는 소각합니다.</p>
        </Article>

        <Article num="제7조" title="개인정보의 안전성 확보 조치">
          <SubItem title="개인정보 취급 직원의 최소화 및 교육">
            개인정보를 취급하는 직원을 지정하고 담당자에 한정시켜 최소화하여 관리하고 있습니다.
          </SubItem>
          <SubItem title="해킹 등에 대비한 기술적 대책">
            해킹이나 컴퓨터 바이러스 등에 의한 개인정보 유출 및 훼손을 막기 위하여 보안프로그램을 설치하고 주기적인 갱신·점검을 하고 있습니다.
          </SubItem>
          <SubItem title="개인정보의 암호화">
            중요한 데이터는 암호화하여 저장·관리되며, 전송 시에도 별도의 보안 기능을 사용하고 있습니다.
          </SubItem>
          <SubItem title="개인정보에 대한 접근 제한">
            개인정보를 처리하는 시스템에 대한 접근권한을 최소화하고 외부로부터의 무단 접근을 통제하고 있습니다.
          </SubItem>
        </Article>

        <Article num="제8조" title="개인정보보호책임자">
          <p>개인정보 침해에 대한 신고나 상담이 필요하신 경우 아래 기관에 문의하시기 바랍니다.</p>
          <ul className="mt-2 space-y-1 pl-4 text-gray-500">
            <li>개인정보 침해신고센터 (한국인터넷진흥원): (국번없이) 118, privacy.kisa.or.kr</li>
            <li>개인정보 분쟁조정위원회: (국번없이) 1833-6972, www.kopico.go.kr</li>
            <li>대검찰청 사이버수사과: (국번없이) 1301, www.spo.go.kr</li>
            <li>경찰청 사이버안전국: (국번없이) 182, cyberbureau.police.go.kr</li>
          </ul>
<div className="mt-3 pl-4 border-l-2 border-gray-200 space-y-0.5 text-gray-600">
            <p>성명: 김혜신 &nbsp;·&nbsp; 직책: BRIDGE 보안관리자</p>
            <p>이메일: <a href="mailto:bridgejobkr@gmail.com" className="underline hover:text-gray-900">bridgejobkr@gmail.com</a></p>
          </div>
        </Article>

        <Article num="제9조" title="개인정보 처리의 위탁">
          <p>서비스 제공에 필요한 서버 운영, 데이터베이스 관리, 파일 저장 등의 업무를 인프라 업체에 위탁하여 처리합니다.</p>
        </Article>

        <Article num="제10조" title="쿠키(Cookie)의 운용">
          <p>유지 및 보안 목적으로 쿠키를 사용합니다. 이용자는 웹브라우저 설정을 통해 쿠키 저장을 거부할 수 있으나, 일부 서비스 이용에 어려움이 발생할 수 있습니다.</p>
        </Article>

        <Article num="제11조" title="개인정보 처리방침 변경">
          <div className="pl-4 space-y-2 text-gray-600">
            <p>이 개인정보처리방침은 2021년 06월 21일부터 적용됩니다.</p>
            <p>내용 변경 시 충분한 일정을 두고 홈페이지를 통해 고지합니다.</p>
          </div>
        </Article>

      </div>

      {/* Patent notice */}
      <p className="mt-14 text-xs text-gray-400 leading-relaxed">
        BRIDGE는 원어민 강사 채용에 특화된 독자적인 매칭 시스템(특허출원번호 제10-2024-0110155호)을 운영합니다.
      </p>

      {/* Footer */}
      <div className="mt-4 pt-5 border-t border-gray-200 text-xs text-gray-400 flex flex-wrap gap-x-4 gap-y-1">
        <span>BRIDGE Recruitment</span>
        <span>대표: Scarlett</span>
        <span>bridgejob.co.kr</span>
        <span><a href="mailto:bridgejobkr@gmail.com" className="underline hover:text-gray-600">bridgejobkr@gmail.com</a></span>
        <span><Link href="/terms" className="underline hover:text-gray-600">이용약관</Link></span>
        <span><Link href="/fees" className="underline hover:text-gray-600">요금안내</Link></span>
        <span><Link href="/contact" className="underline hover:text-gray-600">문의하기</Link></span>
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

function SubItem({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="pl-4">
      <p className="font-semibold text-gray-800 mb-0.5">{title}</p>
      <p className="text-gray-600">{children}</p>
    </div>
  )
}
