import Link from 'next/link'

export default function PrivacyPage() {
  return (
    <div className="max-w-[760px] mx-auto px-4 sm:px-6 py-14">

      {/* Header */}
      <div className="mb-10">
        <span className="inline-block text-[11px] font-semibold text-gray-500 border border-gray-300 rounded px-2 py-0.5 mb-4">Legal</span>
        <h1 className="text-3xl font-bold text-[#1d1d1f] mb-2">개인정보처리방침</h1>
        <p className="text-sm text-gray-400">시행일: 2021년 06월 21일 · BRIDGE Recruitment</p>
      </div>

      {/* Intro */}
      <p className="text-sm text-gray-700 leading-7 mb-10">
        BRIDGE(이하 &ldquo;회사&rdquo;)는 정보주체의 자유와 권리 보호를 위해 「개인정보 보호법」 및 관계 법령이 정한 바를 준수하며, 적법하게 개인정보를 처리하고 안전하게 관리하고 있습니다. 이에 법 제30조에 따라 정보주체에게 개인정보 처리에 관한 절차 및 기준을 안내하고, 이와 관련한 고충을 신속하고 원활하게 처리할 수 있도록 하기 위하여 다음과 같이 개인정보처리방침을 수립·공개합니다.
      </p>

      <div className="space-y-10 text-sm text-gray-700 leading-7">

        <Article num="제1조" title="개인정보의 처리 목적">
          <p>회사는 다음의 목적을 위하여 개인정보를 처리합니다. 처리하고 있는 개인정보는 다음의 목적 이외의 용도로는 이용되지 않으며, 이용 목적이 변경되는 경우에는 별도의 동의를 받는 등 필요한 조치를 이행합니다.</p>
          <SubItem title="강사 채용 서비스 제공">
            「직업안정법」에 따른 유료직업소개업 수행을 위하여 구직자 및 구인자의 정보를 수집·관리하고, 채용 절차 진행, 비자 및 취업 관련 서류 처리, 이메일 및 연락 등을 목적으로 개인정보를 처리합니다.
          </SubItem>
          <SubItem title="구인 학교·기관 서비스">
            채용 의뢰 접수, 강사 소개, 계약 체결 지원 등 채용 서비스 전반의 업무 수행을 목적으로 개인정보를 처리합니다.
          </SubItem>
          <SubItem title="고충처리 및 분쟁 대응">
            민원 접수 및 처리, 분쟁 조정을 위한 기록 보존 등을 목적으로 개인정보를 처리합니다.
          </SubItem>
        </Article>

        <Article num="제2조" title="처리하는 개인정보 항목">
          <SubItem title="구직자 (강사)">
            성명, 생년월일, 성별, 국적, 현재 거주국, 여권정보, 이메일 주소, 전화번호, 카카오톡 ID, 학력사항, 경력사항, 자격증, 비자정보, 범죄경력조회 결과, 사진, 이력서 및 자기소개서, 기타 채용에 필요한 개인정보
          </SubItem>
          <SubItem title="구인자 (학교·기관)">
            담당자 성명, 연락처, 사업자등록번호, 계약정보, 채용 요건 등 채용에 필요한 정보
          </SubItem>
        </Article>

        <Article num="제3조" title="개인정보의 처리 및 보유 기간">
          <p>회사는 법령에 따른 개인정보 보유·이용기간 또는 정보주체로부터 개인정보를 수집 시 동의받은 보유·이용기간 내에서 개인정보를 처리·보유합니다. 각각의 개인정보 처리 및 보유 기간은 다음과 같습니다.</p>
          <SubItem title="강사 채용 서비스">
            채용 서비스 계약 종료일로부터 관련 법령이 정하는 기간 동안 보유합니다.
          </SubItem>
          <SubItem title="구인 학교·기관 서비스">
            서비스 계약 종료 시까지 보유합니다.
          </SubItem>
          <SubItem title="법령에 따른 보유">
            관계 법령에서 일정 기간 정보 보존 의무를 부과하는 경우, 해당 기간 동안 보관 후 파기합니다.
          </SubItem>
        </Article>

        <Article num="제4조" title="개인정보의 제3자 제공">
          <p>회사는 정보주체의 개인정보를 수집 목적 범위 내에서만 처리하며, 정보주체의 동의, 법률의 특별한 규정 등 「개인정보 보호법」 제17조 및 제18조에 해당하는 경우에만 개인정보를 제3자에게 제공합니다.</p>
          <SubItem title="채용 확정 시 구인 학교·기관">
            근로계약 체결에 필요한 범위 내에서 해당 기관에 관련 정보를 제공합니다. 채용 결정 시까지 보유하며, 목적 달성 후 파기합니다.
          </SubItem>
        </Article>

        <Article num="제5조" title="개인정보 처리의 위탁">
          <p>회사는 원활한 서비스 제공을 위하여 다음과 같이 개인정보 처리 업무를 위탁하고 있습니다. 수탁업체에 대해서는 개인정보 보호 관련 법규 준수 및 제3자 제공 금지 등을 계약서에 명시하고 있습니다.</p>
          <SubItem title="서버 운영 및 파일 저장">
            서비스 제공에 필요한 서버 운영, 데이터베이스 관리, 파일 저장 등의 업무를 외부 클라우드 인프라 업체에 위탁하여 처리합니다.
          </SubItem>
        </Article>

        <Article num="제6조" title="개인정보의 파기 절차 및 방법">
          <p>회사는 개인정보 보유 기간의 경과, 처리 목적 달성 등 개인정보가 불필요하게 되었을 때에는 지체 없이 해당 개인정보를 파기합니다.</p>
          <SubItem title="전자적 파일 형태">
            복원이 불가능한 방법으로 영구 삭제합니다.
          </SubItem>
          <SubItem title="종이 문서">
            분쇄하거나 소각하여 파기합니다.
          </SubItem>
        </Article>

        <Article num="제7조" title="정보주체의 권리·의무 및 행사 방법">
          <p>정보주체는 회사에 대해 언제든지 개인정보 열람·정정·삭제·처리정지 요구 등의 권리를 행사할 수 있습니다. 권리 행사는 이메일을 통해 하실 수 있으며, 회사는 이에 대해 지체 없이 조치합니다.</p>
          <p className="mt-2">다만, 법령에 따라 보존이 필요한 정보에 대한 삭제 요청은 거절될 수 있으며, 이 경우 해당 사유를 안내해 드립니다.</p>
        </Article>

        <Article num="제8조" title="개인정보의 안전성 확보 조치">
          <SubItem title="개인정보 취급 직원의 최소화 및 교육">
            개인정보를 취급하는 직원을 지정하고 담당자에 한정시켜 최소화하여 개인정보를 관리하는 대책을 시행하고 있습니다.
          </SubItem>
          <SubItem title="내부관리계획의 수립 및 시행">
            개인정보의 안전한 처리를 위하여 내부관리계획을 수립하고 시행하고 있습니다.
          </SubItem>
          <SubItem title="해킹 등에 대비한 기술적 대책">
            해킹이나 컴퓨터 바이러스 등에 의한 개인정보 유출 및 훼손을 막기 위하여 보안프로그램을 설치하고 주기적인 갱신·점검을 하고 있습니다.
          </SubItem>
          <SubItem title="개인정보의 암호화">
            이용자의 개인정보 중 중요한 데이터는 암호화하여 저장 및 관리되고 있으며, 파일 전송 시에도 별도의 보안 기능을 사용하고 있습니다.
          </SubItem>
          <SubItem title="개인정보에 대한 접근 제한">
            개인정보를 처리하는 시스템에 대한 접근권한을 최소화하고 외부로부터의 무단 접근을 통제하고 있습니다.
          </SubItem>
        </Article>

        <Article num="제9조" title="쿠키(Cookie)의 운용">
          <SubItem title="쿠키 사용">
            회사는 이용자에게 적합한 서비스를 제공하기 위해 이용 정보를 저장하고 수시로 불러오는 쿠키(cookie)를 사용합니다. 쿠키는 웹사이트 서버가 이용자의 브라우저에 전송하는 소량의 정보로, 로그인 유지 및 보안 목적으로 활용됩니다.
          </SubItem>
          <SubItem title="쿠키 저장 거부 방법">
            이용자는 웹브라우저 설정을 통해 쿠키 저장을 허용하거나 거부할 수 있습니다. 단, 쿠키를 거부할 경우 일부 서비스 이용에 어려움이 발생할 수 있습니다.
          </SubItem>
        </Article>

        <Article num="제10조" title="개인정보보호책임자">
          <p>회사는 개인정보 처리에 관한 업무를 총괄하고, 정보주체의 불만처리 및 피해구제 등을 위하여 개인정보보호책임자를 지정하고 있습니다.</p>
          <div className="mt-3 pl-4 border-l-2 border-gray-200 space-y-0.5 text-gray-600">
            <p>성명: Scarlett</p>
            <p>직책: BRIDGE Recruitment 대표</p>
            <p>이메일: <a href="mailto:bridgejobkr@gmail.com" className="underline hover:text-gray-900">bridgejobkr@gmail.com</a></p>
          </div>
          <p className="mt-3">정보주체는 서비스를 이용하면서 발생한 모든 개인정보보호 관련 문의, 불만처리, 피해구제 등에 관한 사항을 개인정보보호책임자에게 문의하실 수 있습니다. 회사는 정보주체의 문의에 대해 지체 없이 답변 및 처리해 드릴 것입니다.</p>
          <p className="mt-3">개인정보 침해에 대한 신고나 상담이 필요하신 경우에는 아래 기관에 문의하시기 바랍니다.</p>
          <ul className="mt-2 space-y-1 pl-4 text-gray-500">
            <li>개인정보 침해신고센터 (한국인터넷진흥원 운영): (국번없이) 118, privacy.kisa.or.kr</li>
            <li>개인정보 분쟁조정위원회: (국번없이) 1833-6972, www.kopico.go.kr</li>
            <li>대검찰청 사이버수사과: (국번없이) 1301, www.spo.go.kr</li>
            <li>경찰청 사이버안전국: (국번없이) 182, cyberbureau.police.go.kr</li>
          </ul>
        </Article>

        <Article num="제11조" title="개인정보 처리방침 변경">
          <div className="pl-4 space-y-2 text-gray-600">
            <p>이 개인정보처리방침은 2021년 06월 21일부터 적용됩니다.</p>
            <p>법령 또는 회사 정책 변경 등으로 인하여 내용의 추가·삭제 및 수정이 있을 시에는 변경사항의 시행 최소 7일 전부터 홈페이지의 공지사항을 통하여 고지합니다. 다만, 정보주체의 권리·의무에 중대한 영향을 미치는 사항은 최소 30일 전부터 고지합니다.</p>
          </div>
        </Article>

      </div>

      {/* Footer */}
      <div className="mt-14 pt-6 border-t border-gray-200 text-xs text-gray-400 flex flex-wrap gap-x-4 gap-y-1">
        <span>BRIDGE Recruitment</span>
        <span>대표: Scarlett</span>
        <span>bridgejob.co.kr</span>
        <span><a href="mailto:bridgejobkr@gmail.com" className="underline hover:text-gray-600">bridgejobkr@gmail.com</a></span>
        <span><Link href="/terms" className="underline hover:text-gray-600">Terms of Use</Link></span>
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

function SubItem({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="pl-4">
      <p className="font-semibold text-gray-800 mb-0.5">{title}</p>
      <p className="text-gray-600">{children}</p>
    </div>
  )
}
