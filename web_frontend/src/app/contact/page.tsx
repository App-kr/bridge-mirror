import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: '문의하기 · Contact Us | BRIDGE Recruitment',
  description: 'BRIDGE Recruitment 문의 창구 — 이메일, 채용 의뢰, 강사 지원, 일반 문의 안내.',
}

export default function ContactPage() {
  return (
    <div className="max-w-[860px] mx-auto px-4 sm:px-6 py-12 text-[#1d1d1f]">

      {/* Header */}
      <div className="mb-10 pb-6 border-b border-gray-200">
        <span className="inline-block text-[11px] font-semibold text-gray-500 border border-gray-300 rounded px-2 py-0.5 mb-4">Support · Contact</span>
        <h1 className="text-3xl font-bold mb-2">문의하기</h1>
        <p className="text-sm text-gray-500">Contact Us &nbsp;|&nbsp; BRIDGE Recruitment</p>
        <p className="mt-4 text-sm text-gray-600 leading-relaxed">
          BRIDGE에 대한 문의는 아래 창구를 이용해 주시기 바랍니다. 용도에 맞는 창구를 선택하시면
          가장 빠르게 응대드릴 수 있습니다.
        </p>
      </div>

      {/* ── Quick Routes ── */}
      <div className="grid sm:grid-cols-3 gap-4 mb-12">
        <RouteCard
          href="/apply"
          badge="For Teachers"
          title="강사 지원"
          desc="원어민 강사 지원서 제출. 이력서·사진 업로드 및 프로필 등록."
        />
        <RouteCard
          href="/inquiry"
          badge="For Employers"
          title="채용 의뢰"
          desc="학원·학교·기관 채용 담당자용. 포지션 상세 및 조건 제출."
        />
        <RouteCard
          href="mailto:bridgejobkr@gmail.com"
          badge="General"
          title="일반 문의"
          desc="제휴·언론·기타 문의. 영업일 기준 1~2일 내 회신."
          external
        />
      </div>

      <div className="space-y-10 text-sm text-gray-700 leading-7">

        <Article num="제1조" title="연락처">
          <div className="pl-4 border-l-2 border-gray-200 space-y-1 text-gray-600">
            <p>
              이메일:{' '}
              <a href="mailto:bridgejobkr@gmail.com" className="underline hover:text-gray-900">
                bridgejobkr@gmail.com
              </a>
            </p>
            <p>웹사이트: <a href="https://bridgejob.co.kr" className="underline hover:text-gray-900">bridgejob.co.kr</a></p>
            <p>소재지: <span className="text-gray-400">(공개 주소 준비 중)</span></p>
          </div>
          <p className="mt-4 text-[13px] text-gray-500">
            전화·카카오톡 상담은 채용 의뢰 접수 또는 강사 지원 등록 후, 담당 매니저가 개별 배정되어 안내드립니다.
            사전 접수 없는 직접 연락은 「이용약관」 제4·6조에 따라 지원되지 않습니다.
          </p>
        </Article>

        <Article num="제2조" title="응대 시간">
          <div className="pl-4 border-l-2 border-gray-200 space-y-1 text-gray-600">
            <p>평일: 09:00 — 18:00 (KST)</p>
            <p>점심시간: 12:30 — 13:30</p>
            <p>주말·공휴일: 응대하지 않음 (다음 영업일 순차 회신)</p>
          </div>
          <p className="mt-3 text-[13px] text-gray-500">
            채용 확정 단계의 긴급 건은 담당 매니저 직통으로 별도 안내됩니다.
          </p>
        </Article>

        <Article num="제3조" title="문의 유형별 안내">
          <SubItem title="강사 지원 (Teacher Applications)">
            <Link href="/apply" className="underline hover:text-gray-900">/apply</Link>에서 지원서를 제출해 주십시오.
            이메일 개별 회신은 제공되지 않으며, 담당 매니저가 서류 검토 후 직접 연락드립니다.
          </SubItem>
          <SubItem title="채용 의뢰 (Employer Inquiries)">
            <Link href="/inquiry" className="underline hover:text-gray-900">/inquiry</Link>에서 채용 포지션 정보를 등록해 주십시오.
            영업일 기준 1일 내 담당자 배정이 이루어집니다.
          </SubItem>
          <SubItem title="요금 관련 문의">
            표준 요금 및 지급 시점은{' '}
            <Link href="/fees" className="underline hover:text-gray-900">요금안내</Link> 페이지에 공시되어 있습니다.
            비표준 건에 한하여 이메일로 문의 주십시오.
          </SubItem>
          <SubItem title="개인정보 관련">
            개인정보 열람·정정·삭제·처리정지 요청은{' '}
            <a href="mailto:bridgejobkr@gmail.com" className="underline hover:text-gray-900">bridgejobkr@gmail.com</a>{' '}
            으로 접수해 주십시오. 자세한 내용은{' '}
            <Link href="/privacy" className="underline hover:text-gray-900">개인정보처리방침</Link> 제4조를 참조 바랍니다.
          </SubItem>
          <SubItem title="제휴·언론·기타">
            <a href="mailto:bridgejobkr@gmail.com" className="underline hover:text-gray-900">bridgejobkr@gmail.com</a>{' '}
            으로 용건을 명시하여 발송해 주십시오.
          </SubItem>
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
          <Link href="/fees" className="underline hover:text-gray-600">요금안내</Link>
        </p>
      </div>

    </div>
  )
}

function RouteCard({
  href, badge, title, desc, external = false,
}: {
  href: string; badge: string; title: string; desc: string; external?: boolean
}) {
  const content = (
    <div className="h-full p-5 border border-gray-200 rounded-xl hover:border-gray-900 hover:shadow-sm transition-all">
      <span className="inline-block text-[10px] font-semibold text-gray-500 border border-gray-300 rounded px-1.5 py-0.5 mb-3">
        {badge}
      </span>
      <h3 className="text-[15px] font-bold text-[#1d1d1f] mb-1.5">{title}</h3>
      <p className="text-[13px] text-gray-500 leading-relaxed">{desc}</p>
    </div>
  )
  return external ? (
    <a href={href}>{content}</a>
  ) : (
    <Link href={href}>{content}</Link>
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
