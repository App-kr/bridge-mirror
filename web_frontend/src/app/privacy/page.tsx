'use client'

import { useState } from 'react'
import type { Metadata } from 'next'
import Link from 'next/link'

// Metadata can't be exported from 'use client' — set via layout or head
// export const metadata: Metadata = { title: 'Privacy Policy | BRIDGE' }

export default function PrivacyPage() {
  return (
    <div className="max-w-[800px] mx-auto px-4 sm:px-6 py-12 text-[#1d1d1f]">

      {/* ── HEADER ── */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">Privacy Policy <span className="text-gray-400 font-normal text-base">/ 개인정보 처리방침</span></h1>
        <p className="text-xs text-gray-400">Last updated: April 2026 &nbsp;·&nbsp; Governed by the laws of the Republic of Korea</p>
      </div>

      {/* ── SUMMARY CARDS (항상 표시) ── */}
      <div className="grid sm:grid-cols-2 gap-3 mb-8">
        <SummaryCard icon="📋" title="What we collect">
          Name, DOB, nationality, passport, contact details, CV, photo, teaching certifications, criminal check results
        </SummaryCard>
        <SummaryCard icon="🎯" title="Why">
          ESL teacher placement in South Korea — matching, visa processing, employer communication
        </SummaryCard>
        <SummaryCard icon="🗓️" title="How long">
          Minimum <strong>3 years</strong> after recruitment ends. Deletion requests may be declined where Korean immigration/employment law requires retention.
        </SummaryCard>
        <SummaryCard icon="✉️" title="Your rights / Contact">
          Access, correct, or request deletion: <a href="mailto:bridgejobkr@gmail.com" className="underline">bridgejobkr@gmail.com</a> — responded within 10 business days
        </SummaryCard>
      </div>

      {/* ── EU RESTRICTION NOTICE (항상 표시) ── */}
      <div className="mb-8 p-4 bg-amber-50 border border-amber-300 rounded-xl text-sm text-amber-900 leading-relaxed">
        <p className="font-semibold mb-1">Geographic Service Availability</p>
        <p>
          This service is available to applicants currently residing in: <strong>US, UK, Canada, Australia, Ireland, South Africa, South Korea</strong>.
        </p>
        <p className="mt-1">
          Due to a conflict between GDPR mandatory erasure rights and our legal retention obligations under Korean immigration law,
          we are unable to process applications from individuals <strong>currently residing in EU/EEA member states</strong> (Ireland excepted).
          This restriction is based on <em>residence</em>, not nationality.
        </p>
      </div>

      {/* ── ACCORDION SECTIONS ── */}

      <Accordion title="한국 개인정보보호법 — 수집 항목 및 처리 목적" subtitle="제1조">
        <p className="mb-3 text-gray-500">「개인정보 보호법」 제30조에 따른 처리 목적 및 수집 항목입니다.</p>
        <Table headers={['목적', '수집 항목', '보유 기간']}>
          <tr>
            <td>강사 채용 서비스</td>
            <td>성명, 생년월일, 성별, 국적, 거주국, 여권번호, 이메일, 전화, 카카오톡 ID, 학력, 경력, 자격증, 비자정보, 범죄경력조회, 사진, 이력서</td>
            <td>채용 완료 후 3년</td>
          </tr>
          <tr>
            <td>구인 학교 서비스</td>
            <td>학교명, 담당자 성명, 이메일, 전화, 사업자등록번호, 구인 요건</td>
            <td>계약 종료 후 3년</td>
          </tr>
        </Table>
      </Accordion>

      <Accordion title="법령에 따른 보유 기간" subtitle="제2조">
        <Table headers={['관련 법령', '보유 항목', '보유 기간']}>
          <tr><td>출입국관리법 / 고용허가제</td><td>외국인 강사 계약·비자 관련 기록</td><td>3년</td></tr>
          <tr><td>근로기준법 제42조</td><td>근로자명부, 계약 서류</td><td>3년</td></tr>
          <tr><td>국세기본법 제85조의3</td><td>세금계산서, 거래 기록</td><td>5년</td></tr>
          <tr><td>전자상거래법 제6조</td><td>계약·청약 기록, 대금결제 기록</td><td>5년</td></tr>
        </Table>
        <p className="mt-3">위 법령에 해당하지 않는 개인정보는 목적 달성 시 지체 없이 파기합니다 (전자 파일: 복원 불가 영구삭제 / 종이: 분쇄·소각).</p>
      </Accordion>

      <Accordion title="제3자 제공 및 처리 위탁" subtitle="제3조·제4조">
        <p className="font-medium text-gray-700 mb-2">제3자 제공</p>
        <Table headers={['제공받는 자', '목적', '제공 항목']}>
          <tr><td>채용 구인 학교·기관</td><td>강사 채용 및 근로계약 체결</td><td>성명, 국적, 비자, 학력, 경력, 자격증 (동의 항목)</td></tr>
          <tr><td>정부 기관 (법원, 수사기관)</td><td>법령에 따른 제출 요구</td><td>요청 항목</td></tr>
        </Table>
        <p className="font-medium text-gray-700 mt-4 mb-2">처리 위탁</p>
        <Table headers={['수탁업체', '위탁 업무']}>
          <tr><td>Amazon Web Services (AWS)</td><td>파일 저장 (이력서, 사진)</td></tr>
          <tr><td>Render Inc.</td><td>서버 운영 및 데이터베이스 호스팅</td></tr>
          <tr><td>Vercel Inc.</td><td>웹 프론트엔드 서비스 제공</td></tr>
        </Table>
        <p className="mt-3">위 제공·위탁 외에는 동의 없이 개인정보를 외부에 제공하지 않습니다.</p>
      </Accordion>

      <Accordion title="정보주체의 권리 행사 방법" subtitle="제5조">
        <p>정보주체는 언제든지 <strong>열람 · 정정 · 삭제 · 처리정지</strong>를 요구할 수 있습니다.</p>
        <ul className="list-disc pl-5 mt-2 space-y-1">
          <li>요청 방법: <a href="mailto:bridgejobkr@gmail.com" className="text-blue-600 underline">bridgejobkr@gmail.com</a> 이메일 접수</li>
          <li>처리 기한: 접수 후 10일 이내 회신</li>
          <li>본인 확인을 위한 신분증 사본 제출 요청 가능</li>
        </ul>
        <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
          비자·취업 법령에 따른 보유 의무가 있는 경우 삭제 요구가 거절될 수 있습니다. 이 경우 해당 법령 근거를 안내합니다. (「개인정보 보호법」 제37조 제2항)
        </div>
      </Accordion>

      <Accordion title="안전성 확보조치 및 쿠키" subtitle="제7조·제8조">
        <p className="font-medium text-gray-700 mb-2">안전성 확보조치</p>
        <ul className="list-disc pl-5 space-y-1">
          <li>개인정보 저장 시 AES-256 암호화</li>
          <li>전송 시 TLS/HTTPS 암호화</li>
          <li>접근 권한 최소화 — 권한 있는 담당자만 접근</li>
          <li>비밀번호 단방향 암호화(PBKDF2) 저장</li>
          <li>정기 보안 점검</li>
        </ul>
        <p className="font-medium text-gray-700 mt-4 mb-2">쿠키</p>
        <ul className="list-disc pl-5 space-y-1">
          <li><strong>목적</strong>: 로그인 세션 유지, 보안(CSRF 방지)</li>
          <li><strong>기간</strong>: 세션 쿠키(브라우저 종료 시 삭제) / 영속 쿠키(최대 7일)</li>
          <li><strong>거부</strong>: 브라우저 설정 &gt; 쿠키 차단 (일부 기능 제한될 수 있음)</li>
        </ul>
      </Accordion>

      <Accordion title="개인정보보호책임자 및 권익 침해 구제" subtitle="제9조·제10조">
        <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 text-sm space-y-1 mb-4">
          <p className="font-semibold">개인정보보호책임자 (Privacy Officer)</p>
          <p>성명: Scarlett &nbsp;|&nbsp; 소속: BRIDGE Recruitment 대표</p>
          <p>이메일: <a href="mailto:bridgejobkr@gmail.com" className="text-blue-600 underline">bridgejobkr@gmail.com</a></p>
        </div>
        <p className="text-sm text-gray-600 mb-2">개인정보 침해 관련 신고·상담 기관:</p>
        <Table headers={['기관', '연락처']}>
          <tr><td>개인정보보호위원회</td><td>privacy.go.kr &nbsp;|&nbsp; ☎ 182</td></tr>
          <tr><td>한국인터넷진흥원 (KISA)</td><td>privacy.kisa.or.kr &nbsp;|&nbsp; ☎ 118</td></tr>
          <tr><td>대검찰청 사이버범죄수사단</td><td>spo.go.kr &nbsp;|&nbsp; 02-3480-3573</td></tr>
          <tr><td>경찰청 사이버안전국</td><td>cyberbureau.police.go.kr &nbsp;|&nbsp; ☎ 182</td></tr>
        </Table>
      </Accordion>

      <Accordion title="국제 이용자 권리 (International Users)" subtitle="§ Global">
        <p className="mb-3">
          Depending on your country of residence, you may have rights to access, correct, restrict, or
          request deletion of your personal data. To exercise any right, contact{' '}
          <a href="mailto:bridgejobkr@gmail.com" className="text-blue-600 underline">bridgejobkr@gmail.com</a>.
          We respond within 30 calendar days.
        </p>
        <Table headers={['Country', 'Regulator / Complaint Body']}>
          <tr><td>United Kingdom</td><td>Information Commissioner's Office — ico.org.uk</td></tr>
          <tr><td>Canada</td><td>Office of the Privacy Commissioner — priv.gc.ca</td></tr>
          <tr><td>Australia</td><td>Office of the Australian Information Commissioner — oaic.gov.au</td></tr>
          <tr><td>South Africa</td><td>Information Regulator — inforegulator.org.za</td></tr>
          <tr><td>United States (CA)</td><td>CCPA rights apply. We do not sell personal data.</td></tr>
          <tr><td>South Korea</td><td>개인정보보호위원회 — privacy.go.kr</td></tr>
        </Table>
        <p className="mt-3 text-xs text-gray-400">
          Data is stored in South Korea and processed by AWS/Render/Vercel infrastructure providers.
          All transfers are protected by TLS encryption. We do not transfer data outside Korea except
          as necessary for the infrastructure providers listed above.
        </p>
      </Accordion>

      <Accordion title="방침 변경 고지" subtitle="개정 안내">
        <ul className="list-disc pl-5 space-y-1">
          <li>일반 변경: 시행 <strong>7일 전</strong> 이 페이지에 고지</li>
          <li>권리에 영향을 미치는 중요한 변경: 시행 <strong>30일 전</strong> 이메일 고지 (연락처 보유 시)</li>
        </ul>
      </Accordion>

      {/* ── FOOTER ── */}
      <div className="mt-10 pt-6 border-t border-gray-200 text-xs text-gray-400 space-y-1">
        <p>BRIDGE Recruitment · bridgejob.co.kr · bridgejobkr@gmail.com</p>
        <p>「개인정보 보호법」 제30조에 따른 개인정보 처리방침 &nbsp;·&nbsp; Governed by the laws of the Republic of Korea</p>
        <p><Link href="/terms" className="underline hover:text-gray-600">Terms of Use</Link></p>
      </div>

    </div>
  )
}

/* ── Sub-components ── */

function SummaryCard({ icon, title, children }: { icon: string; title: string; children: React.ReactNode }) {
  return (
    <div className="p-4 bg-gray-50 border border-gray-200 rounded-xl">
      <p className="text-xs font-semibold text-gray-500 mb-1">{icon} {title}</p>
      <p className="text-sm text-[#3d3d3f] leading-relaxed">{children}</p>
    </div>
  )
}

function Accordion({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mb-2 border border-gray-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3.5 bg-white hover:bg-gray-50 transition-colors text-left"
      >
        <div>
          <span className="text-[11px] font-semibold text-blue-500 mr-2">{subtitle}</span>
          <span className="text-sm font-medium text-gray-800">{title}</span>
        </div>
        <span className="text-gray-400 text-sm ml-4 shrink-0">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="px-5 py-4 border-t border-gray-100 bg-white text-sm text-[#3d3d3f] leading-relaxed space-y-2">
          {children}
        </div>
      )}
    </div>
  )
}

function Table({ headers, children }: { headers: string[]; children: React.ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[12px] border-collapse border border-gray-200 rounded-lg overflow-hidden">
        <thead>
          <tr className="bg-gray-50">
            {headers.map((h) => (
              <th key={h} className="border border-gray-200 px-3 py-2 text-left font-semibold text-gray-600">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">{children}</tbody>
      </table>
    </div>
  )
}
