'use client'

import Link from 'next/link'

export default function PrivacyPage() {
  return (
    <div className="max-w-[680px] mx-auto px-4 sm:px-6 py-14 text-[#1d1d1f] text-sm leading-7">

      <h1 className="text-xl font-semibold mb-1">개인정보 처리방침</h1>
      <p className="text-xs text-gray-400 mb-10">Privacy Policy</p>

      <Section title="수집하는 개인정보 항목 및 수집 방법">
        <p>BRIDGE는 강사 채용 서비스 및 구인 학교 지원 업무를 위해 지원서 작성, 문의 양식, 이메일 등을 통해 다음의 정보를 수집합니다.</p>
        <p className="mt-2">성명, 생년월일, 성별, 국적, 현재 거주국, 여권정보, 이메일 주소, 전화번호, 카카오톡 ID, 학력사항, 경력사항, 자격증, 비자정보, 범죄경력조회 결과, 사진, 이력서 및 자기소개서</p>
        <p className="mt-2">구인 학교·기관의 경우 담당자 성명, 연락처, 사업자등록번호, 채용 요건 등을 수집합니다.</p>
      </Section>

      <Section title="개인정보의 수집 및 이용 목적">
        <p>수집된 정보는 강사와 구인 학교·기관 간의 채용 연결, 인터뷰 진행, 계약 체결 및 비자·취업 관련 절차 지원의 목적으로만 사용됩니다. 수집 목적 외의 용도로 사용하거나 동의 없이 제3자에게 제공하지 않습니다.</p>
      </Section>

      <Section title="개인정보의 보유 및 이용 기간">
        <p>수집된 개인정보는 채용 서비스 제공 기간 동안 보유하며, 서비스 이용 목적이 달성된 경우 지체 없이 파기합니다. 다만 관련 법령에 의해 일정 기간 보존이 필요한 경우에는 해당 기간 동안 별도 보관 후 파기합니다.</p>
        <p className="mt-2">구인 학교·기관의 정보는 계약 관계 종료 시까지 보유합니다.</p>
      </Section>

      <Section title="개인정보의 제3자 제공">
        <p>채용이 확정되는 경우, 근로계약 체결에 필요한 범위 내에서 해당 구인 학교·기관에 정보를 제공합니다. 이 외에는 이용자의 동의 없이 개인정보를 외부에 제공하지 않으며, 법령에 따른 요청이 있는 경우는 예외로 합니다.</p>
      </Section>

      <Section title="서비스 이용 가능 지역">
        <p>본 서비스는 미국, 영국, 캐나다, 호주, 아일랜드, 남아프리카공화국, 대한민국 거주자를 대상으로 합니다. 아일랜드를 제외한 EU/EEA 회원국 거주자는 EU 개인정보보호법(GDPR)과 한국 관련 법령 간 충돌로 인해 서비스 이용이 제한될 수 있습니다.</p>
      </Section>

      <Section title="개인정보의 파기 절차 및 방법">
        <p>보유 기간이 종료되거나 수집 목적이 달성된 개인정보는 지체 없이 파기합니다. 전자적 형태의 파일은 복원이 불가능한 방법으로 영구 삭제하며, 종이 문서는 분쇄 또는 소각합니다.</p>
      </Section>

      <Section title="이용자의 권리">
        <p>이용자는 언제든지 자신의 개인정보에 대한 열람, 정정, 삭제, 처리 정지를 요청할 수 있습니다. 요청은 아래 개인정보보호책임자 이메일을 통해 접수되며, 접수 후 지체 없이 처리됩니다.</p>
        <p className="mt-2">단, 법령에 따라 보존이 필요한 정보에 대한 삭제 요청은 거절될 수 있으며, 이 경우 해당 사유를 안내해 드립니다.</p>
      </Section>

      <Section title="개인정보의 안전성 확보 조치">
        <p>개인정보를 취급하는 직원을 지정하고 담당자에 한정시켜 최소화하여 개인정보를 관리하는 대책을 시행하고 있습니다.</p>
        <p className="mt-2">개인정보의 안전한 처리를 위하여 내부관리계획을 수립하고 시행하고 있습니다.</p>
        <p className="mt-2">해킹이나 컴퓨터 바이러스 등에 의한 개인정보 유출 및 훼손을 막기 위하여 보안프로그램을 설치하고 주기적인 갱신·점검을 하고 있습니다.</p>
        <p className="mt-2">이용자의 개인정보 중 중요한 데이터는 암호화하여 저장 및 관리되고 있으며, 파일 전송 시에도 별도의 보안 기능을 사용하고 있습니다.</p>
        <p className="mt-2">개인정보를 처리하는 시스템에 대한 접근권한을 최소화하고 외부로부터의 무단 접근을 통제하고 있습니다.</p>
      </Section>

      <Section title="쿠키(Cookie) 운용">
        <p>BRIDGE는 이용자에게 적합한 서비스를 제공하기 위해 쿠키를 사용합니다. 쿠키는 웹사이트 서버가 이용자의 브라우저에 전송하는 소량의 정보로, 로그인 유지 및 보안 목적으로 활용됩니다.</p>
        <p className="mt-2">이용자는 웹브라우저 설정을 통해 쿠키 저장을 거부할 수 있습니다. 단, 쿠키를 거부할 경우 일부 서비스 이용에 어려움이 발생할 수 있습니다.</p>
      </Section>

      <Section title="개인정보보호책임자">
        <p>성명: Scarlett &nbsp;|&nbsp; 직책: 대표 &nbsp;|&nbsp; 이메일: <a href="mailto:bridgejobkr@gmail.com" className="underline">bridgejobkr@gmail.com</a></p>
        <p className="mt-2 text-gray-400 text-xs">개인정보 침해 관련 신고·상담: 개인정보보호위원회 privacy.go.kr &nbsp;|&nbsp; KISA 국번없이 118</p>
      </Section>

      <div className="mt-12 pt-6 border-t border-gray-200 text-xs text-gray-400 space-y-1">
        <p>본 개인정보 처리방침은 2021년 06월 21일부터 적용됩니다.</p>
        <p className="mt-2">
          <Link href="/terms" className="underline hover:text-gray-600">Terms of Use</Link>
          {' '}·{' '}
          <a href="mailto:bridgejobkr@gmail.com" className="underline hover:text-gray-600">bridgejobkr@gmail.com</a>
        </p>
      </div>

    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-8">
      <p className="font-semibold text-gray-900 mb-2">{title}</p>
      <div className="text-gray-600">{children}</div>
    </div>
  )
}
