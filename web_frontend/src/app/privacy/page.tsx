'use client'

import { useState } from 'react'
import Link from 'next/link'

export default function PrivacyPage() {
  return (
    <div className="max-w-[720px] mx-auto px-4 sm:px-6 py-14 text-[#1d1d1f]">

      {/* Header */}
      <h1 className="text-2xl font-semibold mb-1">Privacy Policy</h1>
      <p className="text-xs text-gray-400 mb-10">개인정보 처리방침 · Last updated April 2026 · Republic of Korea</p>

      {/* Quick facts */}
      <div className="text-sm text-gray-700 space-y-2 mb-8 leading-relaxed">
        <p><span className="text-gray-400 w-28 inline-block">Operator</span>BRIDGE Recruitment · bridgejob.co.kr</p>
        <p><span className="text-gray-400 w-28 inline-block">Data collected</span>Name, DOB, nationality, passport, contact, CV, photo, certifications, criminal check</p>
        <p><span className="text-gray-400 w-28 inline-block">Purpose</span>ESL teacher placement in South Korea</p>
        <p><span className="text-gray-400 w-28 inline-block">Retention</span>Minimum 3 years · deletion may be declined where Korean law requires retention</p>
        <p><span className="text-gray-400 w-28 inline-block">Contact</span><a href="mailto:bridgejobkr@gmail.com" className="underline">bridgejobkr@gmail.com</a> · replied within 10 business days</p>
      </div>

      {/* EU notice */}
      <div className="mb-10 pl-4 border-l-2 border-gray-300 text-sm text-gray-500 leading-relaxed">
        <p className="font-medium text-gray-700 mb-1">Geographic restriction</p>
        <p>
          This service is available to applicants currently residing in the US, UK, Canada, Australia, Ireland, South Africa, or South Korea.
          Due to a conflict between GDPR mandatory erasure rights and Korean immigration law retention obligations,
          we cannot process applications from individuals residing in <strong className="text-gray-700">EU/EEA member states</strong> (Ireland excepted).
          Restriction is based on current residence, not nationality.
        </p>
      </div>

      {/* Accordion sections */}
      <div className="divide-y divide-gray-200 border-y border-gray-200">

        <Accordion title="수집 항목 및 처리 목적" sub="제1조">
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

        <Accordion title="법령에 따른 보유 기간" sub="제2조">
          <Table headers={['관련 법령', '보유 항목', '보유 기간']}>
            <tr><td>출입국관리법 / 고용허가제</td><td>외국인 강사 계약·비자 관련 기록</td><td>3년</td></tr>
            <tr><td>근로기준법 제42조</td><td>근로자명부, 계약 서류</td><td>3년</td></tr>
            <tr><td>국세기본법 제85조의3</td><td>세금계산서, 거래 기록</td><td>5년</td></tr>
            <tr><td>전자상거래법 제6조</td><td>계약·청약 기록, 대금결제 기록</td><td>5년</td></tr>
          </Table>
          <p className="mt-3">위 법령에 해당하지 않는 개인정보는 목적 달성 시 지체 없이 파기합니다. 전자 파일은 복원 불가 방식으로 영구 삭제, 종이 문서는 분쇄 또는 소각합니다.</p>
        </Accordion>

        <Accordion title="제3자 제공 및 처리 위탁" sub="제3조·제4조">
          <p className="font-medium text-gray-700 mb-2">제3자 제공</p>
          <Table headers={['제공받는 자', '목적', '제공 항목']}>
            <tr><td>채용 구인 학교·기관</td><td>강사 채용 및 근로계약 체결</td><td>성명, 국적, 비자, 학력, 경력, 자격증 (동의 항목)</td></tr>
            <tr><td>정부 기관 (법원, 수사기관)</td><td>법령에 따른 제출 요구</td><td>요청 항목</td></tr>
          </Table>
          <p className="font-medium text-gray-700 mt-4 mb-2">처리 위탁</p>
          <Table headers={['수탁업체', '위탁 업무']}>
            <tr><td>Amazon Web Services</td><td>파일 저장 (이력서, 사진)</td></tr>
            <tr><td>Render Inc.</td><td>서버 운영 및 데이터베이스</td></tr>
            <tr><td>Vercel Inc.</td><td>웹 프론트엔드 서비스</td></tr>
          </Table>
        </Accordion>

        <Accordion title="정보주체의 권리 행사" sub="제5조">
          <p>열람 · 정정 · 삭제 · 처리정지 요청: <a href="mailto:bridgejobkr@gmail.com" className="underline">bridgejobkr@gmail.com</a> · 접수 후 10일 이내 처리</p>
          <p className="mt-2 text-gray-500 text-xs">비자·취업 법령에 따른 보유 의무가 있는 경우 삭제 요구가 거절될 수 있으며, 해당 법령 근거를 안내합니다. (개인정보 보호법 제37조 제2항)</p>
        </Accordion>

        <Accordion title="안전성 확보조치 및 쿠키" sub="제7조·제8조">
          <p className="font-medium text-gray-700 mb-1">안전성 확보조치</p>
          <p className="text-gray-500">AES-256 저장 암호화 · TLS 전송 암호화 · 접근 권한 최소화 · PBKDF2 비밀번호 저장 · 정기 보안 점검</p>
          <p className="font-medium text-gray-700 mt-3 mb-1">쿠키</p>
          <p className="text-gray-500">로그인 세션 유지 및 보안(CSRF 방지) 목적. 세션 쿠키(브라우저 종료 시 삭제) 및 영속 쿠키(최대 7일). 브라우저 설정에서 거부 가능.</p>
        </Accordion>

        <Accordion title="개인정보보호책임자 및 권익 침해 구제" sub="제9조·제10조">
          <p>책임자: <strong>Scarlett</strong> (BRIDGE Recruitment 대표) · <a href="mailto:bridgejobkr@gmail.com" className="underline">bridgejobkr@gmail.com</a></p>
          <p className="mt-3 font-medium text-gray-700 mb-1">침해 신고·상담 기관</p>
          <Table headers={['기관', '연락처']}>
            <tr><td>개인정보보호위원회</td><td>privacy.go.kr · ☎ 182</td></tr>
            <tr><td>한국인터넷진흥원 (KISA)</td><td>privacy.kisa.or.kr · ☎ 118</td></tr>
            <tr><td>대검찰청 사이버범죄수사단</td><td>spo.go.kr · 02-3480-3573</td></tr>
            <tr><td>경찰청 사이버안전국</td><td>cyberbureau.police.go.kr · ☎ 182</td></tr>
          </Table>
        </Accordion>

        <Accordion title="International users — rights by country" sub="§ Global">
          <p className="mb-3">To access, correct, restrict, or request deletion of your data: <a href="mailto:bridgejobkr@gmail.com" className="underline">bridgejobkr@gmail.com</a> · responded within 30 days.</p>
          <Table headers={['Country', 'Regulator']}>
            <tr><td>United Kingdom</td><td>ICO — ico.org.uk</td></tr>
            <tr><td>Canada</td><td>OPC — priv.gc.ca</td></tr>
            <tr><td>Australia</td><td>OAIC — oaic.gov.au</td></tr>
            <tr><td>South Africa</td><td>Information Regulator — inforegulator.org.za</td></tr>
            <tr><td>United States (CA)</td><td>CCPA rights apply · we do not sell personal data</td></tr>
          </Table>
        </Accordion>

        <Accordion title="방침 변경 고지" sub="개정">
          <p>일반 변경: 시행 7일 전 이 페이지에 고지</p>
          <p>권리에 영향을 미치는 변경: 시행 30일 전 이메일 고지</p>
        </Accordion>

      </div>

      {/* Footer */}
      <p className="mt-10 text-xs text-gray-400">
        BRIDGE Recruitment · bridgejob.co.kr · bridgejobkr@gmail.com ·{' '}
        <Link href="/terms" className="underline hover:text-gray-600">Terms of Use</Link>
      </p>

    </div>
  )
}

function Accordion({ title, sub, children }: { title: string; sub: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-3.5 text-left hover:opacity-70 transition-opacity"
      >
        <span className="text-sm text-gray-800">
          <span className="text-gray-400 text-xs mr-2">{sub}</span>
          {title}
        </span>
        <span className="text-gray-400 text-xs ml-4 shrink-0">{open ? '접기' : '펼치기'}</span>
      </button>
      {open && (
        <div className="pb-5 text-sm text-gray-600 leading-relaxed space-y-2">
          {children}
        </div>
      )}
    </div>
  )
}

function Table({ headers, children }: { headers: string[]; children: React.ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[12px] border-collapse">
        <thead>
          <tr className="border-b border-gray-200">
            {headers.map((h) => (
              <th key={h} className="px-2 py-1.5 text-left font-medium text-gray-500">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {children}
        </tbody>
      </table>
    </div>
  )
}
