'use client'

/**
 * /inquiry — Employer Hiring Inquiry Form · 3-Step Wizard
 * Mapped 1:1 from Google Form (구인자 구인신청)
 * Step 1: 기본정보 (17 fields)
 * Step 2: 급여 및 복지 (10 fields)
 * Step 3: 개인정보 동의 (1 field)
 * Payment: Bank Transfer + PayPal only (no credit card — immutable)
 */

import { useState, useRef } from 'react'
import GuidePopup from '@/components/GuidePopup'
import PuzzleCaptcha from '@/components/PuzzleCaptcha'

import { API_URL } from '@/lib/api'

const API = API_URL

// ── Options (Google Form 1:1 매핑) ──────────────────────────────────────────

const BUSINESS_REG = [
  '등록기관 Registered Institution',
  '현시간 미등록 Unregistered Institution',
]

const HIRE_HIST = ['채용이력O', '채용이력X']

const NATIVE_COUNT = [
  '없음','1명','2명','3명','4명','5명','6명',
  '7~9명','10~14명','15~20명','20명이상','30명이상',
]

const VACANCIES = ['1명','2명','3명','4명','5명','6명','7명','8명','9명','10명']

const CONTRACT_TYPE = ['Full time', 'Part time']

const TEACHING_AGE = [
  '48개월 미만 baby','영유아 Pre-K, ~5세미만','유치원 Kindergarten',
  '초등학생 Elementary','중학생 Middle School',
  '고등학생 High School','대학생/ 성인 Adult',
]

const CLASS_SIZE = ['~5명 이내','~8명 이내','~12명 이내','12명 이상','20명이상']

const AVG_LESSONS = [
  '주 10-15시간','주 15-20시간','주 20-25시간',
  '주 25-30시간','주 30-35시간','주 35시간 이상',
]

const PREFERRED_CANDIDATE = [
  '영어권 원어민 Native Teachers','교포 Kyopo',
  'F비자 소지자 F Visa','한국인 Koreans','무관 No Preference',
]

const SALARY_RANGES = [
  '2,20 KRW - 2,30 KRW','2,30 KRW - 2,40 KRW','2,40 KRW - 2,50 KRW',
  '2,50 KRW - 2,60 KRW','2,60 KRW - 2,70 KRW','2,70 KRW - 2,80 KRW',
  '2,80 KRW - 2,90 KRW','2,90 KRW - 3,00 KRW','3,00 KRW - 3,20 KRW',
  '3,20 KRW - 3,50 KRW','3,50 KRW - 4,50 KRW','4,50 KRW - 6,50 KRW',
  '시급제 또는 기타',
]

const TRAVEL_SUPPORT = [
  '국내교통비지원 Domestic allowance',
  '왕복항공지원 Round trip support',
  '입국만지원 Entry','출국만지원 Departure',
  '규정에따른비용지원 Travel expenses',
  '제공없음 Not provided',
]

const MEAL_OPTS = ['식사제공','식대제공','식사식대제공없음']

const HOUSING_OPTS = [
  '풀옵션 하우징 Fully furnished housing',
  '개인기숙사 Dormitory',
  '월세지원 Housing allowance',
  '월세 및 보증금지원 Allowance and deposit support',
  '다양한 지원가능 Negotiable',
  '숙소미제공 No housing provided',
]

const BENEFITS_OPTS = [
  '비자스폰 (E) Working Visa sponsorship',
  '퇴직금 Severance Pay (월급제 필수*)',
  '교통비 Transportation expenses',
  '국민연금 National Pension (SA제외 월급제 필수*)',
  '건강보험 Medical Insurance',
  '비자 건강검진 Medical check support',
  '정착 지원금 Settlement Allowance',
  '재계약 보너스 Renewal Bonus',
  '계약완료 보너스 Contract Completion Bonus',
  '본인/자녀 교육지원 Education support',
  '기타 Bonus (연휴, 생일, 성과금등)',
]

const VACATION_INC = [
  '포함 Including weekends',
  '주말,공휴일제외 Excluding weekends',
]

const STEP_LABELS = ['기본정보', '급여 및 복지', '개인정보 동의']

// ── Step Indicator ─────────────────────────────────────────────────────────
function StepIndicator({ step }: { step: number }) {
  return (
    <div className="card !p-4">
      <div className="flex items-center">
        {STEP_LABELS.map((label, i) => {
          const n     = i + 1
          const done  = n < step
          const active = n === step
          return (
            <div key={n} className="flex items-center flex-1 last:flex-none">
              <div className="flex items-center gap-2.5 shrink-0">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all
                  ${done   ? 'bg-blue-600 text-white'
                  : active ? 'bg-blue-600 text-white ring-2 ring-blue-200 ring-offset-1'
                  :          'bg-gray-100 text-gray-400'}`}>
                  {done ? '\u2713' : n}
                </div>
                <span className={`text-sm font-medium hidden sm:block
                  ${active ? 'text-gray-900' : done ? 'text-gray-500' : 'text-gray-400'}`}>
                  {label}
                </span>
              </div>
              {i < STEP_LABELS.length - 1 && (
                <div className={`flex-1 h-px mx-3 ${n < step ? 'bg-blue-400' : 'bg-gray-200'}`} />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Helpers ─────────────────────────────────────────────────────────────────
function Sec({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="text-lg font-bold text-gray-900 uppercase tracking-wide border-b border-gray-100 pb-2 mb-1">
      {title}
      {subtitle && <span className="ml-2 text-gray-300 normal-case font-normal tracking-normal">{subtitle}</span>}
    </div>
  )
}

function Label({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <label className="block text-[15px] font-semibold text-gray-800 mb-1">
      {children}{required && <span className="text-red-400 ml-0.5">*</span>}
    </label>
  )
}

function Desc({ text }: { text: string }) {
  return <p className="text-sm text-gray-400 -mt-0.5 mb-2 leading-relaxed">{text}</p>
}

function SingleTog({
  value, onChange, options,
}: { value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((o) => (
        <button key={o} type="button" onClick={() => onChange(o)}
          className={value === o ? 'tog-on' : 'tog'}>
          {o}
        </button>
      ))}
    </div>
  )
}

function Dropdown({
  value, onChange, options, placeholder = '선택...',
}: { value: string; onChange: (v: string) => void; options: string[]; placeholder?: string }) {
  return (
    <select
      className="input"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="">{placeholder}</option>
      {options.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  )
}

function CheckList({
  value, onChange, options,
}: { value: string[]; onChange: (v: string[]) => void; options: string[] }) {
  return (
    <div className="space-y-2">
      {options.map((o) => (
        <label key={o} className="flex items-center gap-3 cursor-pointer group">
          <input
            type="checkbox"
            checked={value.includes(o)}
            onChange={() => onChange(value.includes(o) ? value.filter((x) => x !== o) : [...value, o])}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700 group-hover:text-gray-900">{o}</span>
        </label>
      ))}
    </div>
  )
}

// ── File Upload Component ─────────────────────────────────────────────────
interface UploadedFile { name: string; file_url?: string; uploading?: boolean; error?: string }

function FileUpload({
  label, accept, fileType, entityType, entityId,
}: {
  label: string; accept: string; fileType: string
  entityType: string; entityId: string | null
}) {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFiles(fileList: FileList | null) {
    if (!fileList || !entityId) return
    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i]
      const entry: UploadedFile = { name: file.name, uploading: true }
      setFiles(prev => [...prev, entry])

      try {
        const fd = new FormData()
        fd.append('file', file)
        const res = await fetch(`${API}/api/upload/${entityType}/${entityId}?file_type=${fileType}`, {
          method: 'POST', body: fd,
        })
        const json = await res.json()
        if (!res.ok) throw new Error(json.detail ?? 'Upload failed')
        setFiles(prev => prev.map(f => f.name === entry.name && f.uploading
          ? { name: entry.name, file_url: json.data?.file_url } : f))
      } catch (err) {
        setFiles(prev => prev.map(f => f.name === entry.name && f.uploading
          ? { name: entry.name, error: err instanceof Error ? err.message : 'Failed' } : f))
      }
    }
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div>
      <div
        className="border-2 border-dashed border-gray-200 rounded-xl p-4 text-center cursor-pointer
                   hover:border-blue-300 hover:bg-blue-50/30 transition-all"
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept={accept} className="hidden"
          multiple onChange={(e) => handleFiles(e.target.files)} />
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-xs text-gray-400 mt-1">Click to browse</p>
      </div>
      {files.length > 0 && (
        <div className="mt-2 space-y-1">
          {files.map((f, i) => (
            <div key={i} className="flex items-center gap-2 text-xs px-2 py-1 bg-gray-50 rounded">
              {f.uploading && <span className="text-blue-500 animate-pulse">Uploading...</span>}
              {f.file_url && <span className="text-green-600">Uploaded</span>}
              {f.error && <span className="text-red-500">{f.error}</span>}
              <span className="text-gray-600 truncate">{f.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Initial state ──────────────────────────────────────────────────────────
const INIT = {
  /* Step 1 — 기본정보 */
  email: '', contact_name: '', phone: '',
  business_registration: '',
  school_name: '', school_location: '', hiring_history: '',
  native_count: '', vacancies: '',
  start_date: '', contract_type: '',
  teaching_age: [] as string[], class_size: '',
  schedule: '', break_time: '', avg_lessons: '',
  job_responsibilities: '', preferred_candidate: [] as string[],

  /* Step 2 — 급여 및 복지 */
  salary_raw: [] as string[], travel_support: '',
  meal_provided: [] as string[],
  housing_provided: '', housing_detail: '',
  benefits: [] as string[],
  paid_vacation: '', vacation_includes: '', sick_leave: '',
  memo: '',

  /* Step 3 — 개인정보 동의 */
  privacy_policy: '',
}

// ── Page ────────────────────────────────────────────────────────────────────
export default function InquiryPage() {
  const [step,      setStep]      = useState(1)
  const [status,    setStatus]    = useState<'idle' | 'submitting' | 'success' | 'error'>('idle')
  const [errorMsg,  setErrorMsg]  = useState('')
  const [form,      setForm]      = useState(INIT)
  const [inquiryId, setInquiryId] = useState<string | null>(null)

  const set = (field: keyof typeof INIT) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((p) => ({ ...p, [field]: e.target.value }))

  function handleNext() {
    setErrorMsg('')
    if (step === 1 && !form.school_name.trim()) {
      setErrorMsg('학교/기관명은 필수입니다. (School name is required.)')
      return
    }
    setStep((s) => Math.min(s + 1, 3))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function handleBack() {
    setErrorMsg('')
    setStep((s) => Math.max(s - 1, 1))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function handleSubmit() {
    if (!form.privacy_policy.includes('동의')) {
      setErrorMsg('개인정보처리방침에 동의해 주세요.')
      return
    }
    setStatus('submitting')
    try {
      const payload = {
        email: form.email,
        contact_name: form.contact_name,
        phone: form.phone,
        business_registration: form.business_registration,
        school_name: form.school_name,
        school_location: form.school_location,
        hiring_history: form.hiring_history,
        native_count: form.native_count,
        vacancies: form.vacancies,
        start_date: form.start_date,
        contract_type: form.contract_type,
        teaching_age: (form.teaching_age as string[]).join(', '),
        class_size: form.class_size,
        schedule: form.schedule,
        break_time: form.break_time,
        avg_lessons: form.avg_lessons,
        job_responsibilities: form.job_responsibilities,
        preferred_candidate: (form.preferred_candidate as string[]).join(', '),
        salary_raw: (form.salary_raw as string[]).join(', '),
        travel_support: form.travel_support,
        meal_provided: (form.meal_provided as string[]).join(', '),
        housing_provided: form.housing_provided,
        housing_detail: form.housing_detail,
        benefits: (form.benefits as string[]).join(', '),
        paid_vacation: form.paid_vacation,
        vacation_includes: form.vacation_includes,
        sick_leave: form.sick_leave,
        memo: form.memo,
        privacy_policy: form.privacy_policy,
        location: form.school_location,
        source: 'web_form',
      }
      const res  = await fetch(`${API}/api/inquiry`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Error')
      if (json.data?.id) setInquiryId(json.data.id)
      setStatus('success')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Submission failed.')
      setStatus('error')
    }
  }

  // ── Success ─────────────────────────────────────────────────────────────
  if (status === 'success') {
    return (
      <div className="max-w-lg mx-auto text-center py-24 space-y-5">
        <div className="text-6xl">{'\u2705'}</div>
        <h2 className="text-2xl font-bold text-gray-900">문의가 접수되었습니다</h2>
        <p className="text-gray-500">담당자가 확인 후 1~2 영업일 내에 연락드리겠습니다.</p>
        <p className="text-gray-400 text-sm">접수를 완료하셨으면 사업자 등록증 사본을 이메일로 보내주시기 바랍니다.</p>

        {/* Post-submission file upload */}
        {inquiryId && (
          <div className="text-left space-y-4 mt-8 p-6 bg-gray-50 rounded-2xl border">
            <p className="text-sm font-semibold text-gray-700">첨부 파일 업로드 (선택)</p>
            <p className="text-xs text-gray-500">사업자등록증, 학원사진 등 관련 서류를 첨부할 수 있습니다.</p>
            <FileUpload label="파일 첨부 (PDF, Word, 이미지)" accept="application/pdf,.pdf,application/msword,.doc,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx,image/jpeg,.jpg,.jpeg,image/png,.png"
              fileType="attachment" entityType="inquiry" entityId={inquiryId} />
          </div>
        )}

        <button type="button" onClick={() => { setStatus('idle'); setStep(1); setForm(INIT); setInquiryId(null) }} className="btn-primary mt-4">
          추가 문의 제출
        </button>
      </div>
    )
  }

  // ── Page ────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-16">
      <GuidePopup
        storageKey="bridge_inquiry_guide_seen"
        title="구인신청 안내"
        items={[
          '사업자 등록증 사본을 이메일(bridgejobkr@gmail.com)로 보내주세요.',
          '급여, 복지, 근무 조건을 미리 정리해 두시면 빠르게 진행됩니다.',
          '서비스 수수료 결제 후 공고가 게시됩니다 (계좌이체 또는 PayPal).',
          '* 표시 항목은 필수입니다. 정확한 정보를 입력해 주세요.',
        ]}
        cta="시작하기"
      />

      <div className="space-y-2">
        <span className="inline-block text-xs font-semibold text-blue-600 bg-blue-50
                         border border-blue-200 rounded-full px-3 py-1 uppercase tracking-wider">
          For Schools & Academies
        </span>
        <h1 className="text-3xl font-black text-gray-900">강사(교사) 구인신청</h1>
        <p className="text-gray-500 text-sm leading-relaxed">
          해당 항목은 지원자의 실제 지원 의향을 확인하기 위한 필수 정보입니다.
          정확하지 않거나 허위 정보를 입력할 경우, 절차가 진행되지 않을 수 있습니다.<br />
          접수를 완료하신 후 사업자 등록증 사본을 이메일로 보내주시기 바랍니다.
        </p>
      </div>

      {/* ── Payment Section (always visible, above wizard) ── */}
      <div className="space-y-3">
        <p className="text-sm font-semibold text-gray-700">Service Fee & Payment</p>
        <p className="text-xs text-gray-500">채용 공고 게시 전 서비스 수수료를 먼저 결제해 주세요.</p>
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="card !p-6 flex flex-col gap-3
                          border-2 border-gray-200 hover:border-blue-400 transition-all">
            <div className="flex items-center gap-2">
              <span className="text-2xl">&#127974;</span>
              <span className="font-bold text-gray-900">Bank Transfer</span>
            </div>
            <div className="space-y-0.5 text-sm">
              <p className="font-mono text-gray-800 font-semibold">계좌 정보는 문의 시 안내드립니다</p>
              <p className="text-gray-500">bridgejobkr@gmail.com</p>
            </div>
            <p className="text-xs text-gray-400">무통장 입금 후 이메일로 입금 확인 요청</p>
          </div>
          <a
            href="https://www.paypal.com/paypalme/bridgejob"
            target="_blank"
            rel="noopener noreferrer"
            className="card !p-6 flex flex-col gap-3 border-2 border-[#009cde]/30
                       hover:border-[#009cde] hover:!shadow-lg transition-all
                       !bg-[#003087] text-white hover:!bg-[#002070]"
          >
            <div className="flex items-center gap-3">
              <svg viewBox="0 0 24 24" className="w-8 h-8 fill-[#009cde] shrink-0">
                <path d="M7.076 21.337H2.47a.641.641 0 0 1-.633-.74L4.944.901C5.026.382 5.474 0 5.998 0h7.46c2.57 0 4.578.543 5.69 1.81 1.01 1.15 1.304 2.42 1.012 4.287-.023.143-.047.288-.077.437-.983 5.05-4.349 6.797-8.647 6.797h-2.19c-.524 0-.968.382-1.05.9l-1.12 7.106zm14.146-14.42a3.35 3.35 0 0 0-.607-.541c-.013.076-.026.175-.041.254-.59 3.025-2.566 6.082-8.558 6.082H9.825c-.524 0-.968.382-1.05.9l-1.332 8.445-.373 2.368a.533.533 0 0 0 .525.632h3.688c.458 0 .849-.334.92-.789l.038-.196.731-4.63.047-.254c.071-.455.462-.789.92-.789h.58c3.75 0 6.687-1.525 7.545-5.932.357-1.835.173-3.368-.822-4.55z"/>
              </svg>
              <div>
                <p className="text-xs text-blue-200 uppercase tracking-wider">PayPal</p>
                <p className="font-bold text-white text-lg">Pay via PayPal</p>
              </div>
            </div>
            <p className="text-xs text-blue-200">Instant payment &middot; International cards accepted</p>
          </a>
        </div>
      </div>

      <StepIndicator step={step} />

      <div className="space-y-6">

        {/* ================================================================ */}
        {/*  STEP 1 — 기본정보                                               */}
        {/* ================================================================ */}
        {step === 1 && (
          <>
            <section className="card !border-blue-100 bg-blue-50/30">
              <p className="text-xs text-blue-700 leading-relaxed">
                정보는 최대한 정확하게 작성해 주십시오. 변경 사항이 발생할 경우 메모란에 기재해 주시기 바랍니다.
              </p>
            </section>

            {/* 담당자 정보 */}
            <section className="card space-y-4">
              <Sec title="담당자 정보" subtitle="Contact Person" />
              <div>
                <Label required>이메일 주소 / Email</Label>
                <input type="email" className="input" placeholder="school@example.com"
                  value={form.email} onChange={set('email')} />
              </div>
              <div>
                <Label required>성함 / 직책</Label>
                <Desc text="업체명이 아닌 담당자 성함 및 직책 (Name / Position)" />
                <input className="input" placeholder="e.g. 홍길동 / 원장"
                  value={form.contact_name} onChange={set('contact_name')} />
              </div>
              <div>
                <Label required>휴대전화</Label>
                <Desc text="카카오톡이 가능한 대표님 또는 원어민 담당자 휴대전화번호. 인터뷰 등 필수 사항 연락 외 일절 하지 않습니다. 대표 번호만 기재하거나 잘못된 번호를 제공할 경우 진행이 불가능합니다." />
                <input className="input" placeholder="010-xxxx-xxxx"
                  value={form.phone} onChange={set('phone')} />
              </div>
              <div>
                <Label required>사업자</Label>
                <SingleTog
                  value={form.business_registration}
                  onChange={(v) => setForm((p) => ({ ...p, business_registration: v }))}
                  options={BUSINESS_REG}
                />
              </div>
            </section>

            {/* 학교 / 기관 정보 */}
            <section className="card space-y-4">
              <Sec title="학교 / 기관 정보" subtitle="School Information" />
              <div>
                <Label required>학교이름 / Name</Label>
                <Desc text="예시) 브릿지영어 1캠퍼스" />
                <input className="input" placeholder="e.g. 선샤인 영어학원"
                  value={form.school_name} onChange={set('school_name')} />
              </div>
              <div>
                <Label required>근무처소재지</Label>
                <Desc text="네이버 맵 등에 명시된 실제 근무처 장소 주소를 기재해주세요" />
                <input className="input" placeholder="e.g. 서울 강남구 역삼동 123-45"
                  value={form.school_location} onChange={set('school_location')} />
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <Label required>채용이력</Label>
                  <Desc text="현재 사업자로 원어민 E비자 채용여부" />
                  <SingleTog
                    value={form.hiring_history}
                    onChange={(v) => setForm((p) => ({ ...p, hiring_history: v }))}
                    options={HIRE_HIST}
                  />
                </div>
                <div>
                  <Label required>원어민강사</Label>
                  <Desc text='근무중인 "E"비자 원어민수 (교포/한인교사 제외)' />
                  <select className="input" value={form.native_count} onChange={set('native_count')}>
                    <option value="">선택...</option>
                    {NATIVE_COUNT.map((n) => <option key={n}>{n}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <Label required>채용인원</Label>
                  <Desc text="총 몇명의 원어민 채용을 계획하시나요?" />
                  <select className="input" value={form.vacancies} onChange={set('vacancies')}>
                    <option value="">선택...</option>
                    {VACANCIES.map((v) => <option key={v}>{v}</option>)}
                  </select>
                </div>
                <div>
                  <Label required>희망시작일</Label>
                  <input type="date" className="input" value={form.start_date} onChange={set('start_date')} />
                </div>
              </div>
            </section>

            {/* 수업 조건 */}
            <section className="card space-y-5">
              <Sec title="수업 조건" subtitle="Teaching Conditions" />
              <div>
                <Label>계약구분 / Contract Type</Label>
                <SingleTog
                  value={form.contract_type}
                  onChange={(v) => setForm((p) => ({ ...p, contract_type: v }))}
                  options={CONTRACT_TYPE}
                />
              </div>
              <div>
                <Label required>수업대상</Label>
                <CheckList
                  value={form.teaching_age as string[]}
                  onChange={(arr) => setForm((p) => ({ ...p, teaching_age: arr }))}
                  options={TEACHING_AGE}
                />
              </div>
              <div>
                <Label required>학생수</Label>
                <Desc text="1강의당 최대 학생수" />
                <SingleTog
                  value={form.class_size}
                  onChange={(v) => setForm((p) => ({ ...p, class_size: v }))}
                  options={CLASS_SIZE}
                />
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <Label required>근무일정</Label>
                  <Desc text="수업 시작 시각이 아닌, 실제 출근 시각을 기재해 주세요" />
                  <input className="input" placeholder="e.g. M~F 09:00~17:00"
                    value={form.schedule} onChange={set('schedule')} />
                </div>
                <div>
                  <Label>휴게시간</Label>
                  <Desc text="e.g. 점심시간 60분 자유, 외출가능" />
                  <input className="input" placeholder="e.g. 60분 lunch, free to go out"
                    value={form.break_time} onChange={set('break_time')} />
                </div>
              </div>
              <div>
                <Label required>평균강의</Label>
                <Desc text="계약서에 명시될 주당 수업 시간 (Actual weekly teaching hours)" />
                <Dropdown
                  value={form.avg_lessons}
                  onChange={(v) => setForm((p) => ({ ...p, avg_lessons: v }))}
                  options={AVG_LESSONS}
                />
              </div>
              <div>
                <Label required>업무책임</Label>
                <Desc text="Job Responsibilities and Duties" />
                <textarea className="textarea h-20" placeholder="e.g. 수업 + 교재 준비 + 학부모 상담..."
                  value={form.job_responsibilities} onChange={set('job_responsibilities')} />
              </div>
              <div>
                <Label required>선호대상</Label>
                <Desc text="현재 채용 타겟이 아닌, 실제 채용 가능한 대상을 선택해 주세요. E 비자 채용 이력이 없다면 메모 칸에 반드시 기재해야 합니다." />
                <CheckList
                  value={form.preferred_candidate as string[]}
                  onChange={(arr) => setForm((p) => ({ ...p, preferred_candidate: arr }))}
                  options={PREFERRED_CANDIDATE}
                />
              </div>
            </section>
          </>
        )}

        {/* ================================================================ */}
        {/*  STEP 2 — 급여 및 복지                                           */}
        {/* ================================================================ */}
        {step === 2 && (
          <>
            {/* 급여 → CheckList (최저~최고 복수선택) */}
            <section className="card space-y-4">
              <Sec title="급여조건" subtitle="Salary Range" />
              <Desc text="최저~최고 범위를 모두 선택해 주세요. 좋은 강사에게 지급 가능한 페이를 상한선으로 선택하는 게 좋습니다." />
              <CheckList
                value={form.salary_raw as string[]}
                onChange={(arr) => setForm((p) => ({ ...p, salary_raw: arr }))}
                options={SALARY_RANGES}
              />
            </section>

            {/* 이동 & 식사 */}
            <section className="card space-y-5">
              <Sec title="이동지원 & 식사" subtitle="Travel & Meals" />
              <div>
                <Label required>이동지원</Label>
                <Dropdown
                  value={form.travel_support}
                  onChange={(v) => setForm((p) => ({ ...p, travel_support: v }))}
                  options={TRAVEL_SUPPORT}
                />
              </div>
              <div>
                <Label required>식사/식대</Label>
                <CheckList
                  value={form.meal_provided as string[]}
                  onChange={(arr) => setForm((p) => ({ ...p, meal_provided: arr }))}
                  options={MEAL_OPTS}
                />
              </div>
            </section>

            {/* 숙소 → Dropdown (6 options) */}
            <section className="card space-y-4">
              <Sec title="숙소제공" subtitle="Housing" />
              <Desc text="거주비용 지원은 일반적으로 근무처 주변의 숙소 시세에 맞추어 측정합니다. 그보다 낮은 가격을 제공하는 것은 권장되지 않습니다." />
              <Dropdown
                value={form.housing_provided}
                onChange={(v) => setForm((p) => ({ ...p, housing_provided: v }))}
                options={HOUSING_OPTS}
              />
              <div>
                <Label>숙소관련</Label>
                <Desc text="옵션이나 월세금 등을 적어주십시오" />
                <input className="input" placeholder="e.g. 풀옵션/ 월세 70만원+보증금 1천만원 지원"
                  value={form.housing_detail} onChange={set('housing_detail')} />
              </div>
            </section>

            {/* 복지 → CheckList (11 options) */}
            <section className="card space-y-4">
              <Sec title="복지" subtitle="Benefits" />
              <Desc text="교육기관별 복지입니다. 해당사항만 체크해주시되 원어민 채용시 필수항목은 반드시 선택" />
              <CheckList
                value={form.benefits as string[]}
                onChange={(arr) => setForm((p) => ({ ...p, benefits: arr }))}
                options={BENEFITS_OPTS}
              />
            </section>

            {/* 휴가 */}
            <section className="card space-y-4">
              <Sec title="휴가" subtitle="Vacation & Leave" />
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <Label required>유급휴일</Label>
                  <Desc text="A minimum of 11 days must be guaranteed." />
                  <input className="input" placeholder="e.g. 15일/년"
                    value={form.paid_vacation} onChange={set('paid_vacation')} />
                </div>
                <div>
                  <Label required>휴일 포함여부</Label>
                  <Desc text="Does this include weekends and holidays?" />
                  <SingleTog
                    value={form.vacation_includes}
                    onChange={(v) => setForm((p) => ({ ...p, vacation_includes: v }))}
                    options={VACATION_INC}
                  />
                </div>
              </div>
              <div>
                <Label required>보건휴가</Label>
                <Desc text="Sick leave" />
                <input className="input" placeholder="e.g. 3일/년"
                  value={form.sick_leave} onChange={set('sick_leave')} />
              </div>
            </section>

            {/* 메모 */}
            <section className="card space-y-4">
              <Sec title="메모" subtitle="Memo" />
              <textarea className="textarea h-28" placeholder="추가 사항, 특이 조건, 기타 메모..."
                value={form.memo} onChange={set('memo')} />
            </section>
          </>
        )}

        {/* ================================================================ */}
        {/*  STEP 3 — 개인정보 동의                                          */}
        {/* ================================================================ */}
        {step === 3 && (
          <>
            <section className="card space-y-4">
              <Sec title="개인정보처리방침" subtitle="Privacy Policy & Compliance" />
              <div className="bg-gray-50 rounded-xl p-4 text-xs text-gray-600 space-y-3 max-h-64 overflow-y-auto border border-gray-200 leading-relaxed">
                <p className="font-semibold text-gray-800">1. 고용주 준수 사항 및 차별 금지 (Compliance)</p>
                <p><strong>영업 보호 및 직접 연락 금지:</strong> 공식 계약 체결 전, 당사가 소개한 인력의 개인정보를 무단 수집하거나 사전 협의 없이 직접 접촉하는 행위는 엄격히 금지됩니다. 위반 시 정상 서비스 요금이 즉시 부과되며, 영업 비밀 침해에 따른 법적 책임이 청구될 수 있습니다.</p>
                <p><strong>성별·연령 차별 금지:</strong> 모집 및 채용 시 남녀를 차별하거나, 직무 수행에 불필요한 신체 조건 또는 연령 제한을 둘 수 없습니다. (위반 시 남녀고용평등법 등에 의거 500만 원 이하의 벌금 부과)</p>
                <p><strong>국적·인종 차별 금지:</strong> 국적, 인종, 출신 국가를 이유로 근로 조건에서 불합리한 차별을 할 수 없으며, 위반 시 국가인권위원회법 및 외국인근로자 고용법에 따른 시정 권고 및 제재를 받을 수 있습니다.</p>

                <p className="font-semibold text-gray-800 pt-2">2. 개인정보의 수집 및 이용 (Privacy Policy)</p>
                <p><strong>수집 항목:</strong> 성명, 연락처, 사업장 정보(사업자등록증), 채용 조건, 접속 로그 등</p>
                <p><strong>이용 목적:</strong> 원어민 강사 매칭, 인터뷰 조율, 고용계약서 작성 및 사증(비자) 발급 행정 지원</p>
                <p><strong>보유 기간:</strong> 관련 법령에 명시된 기간 동안 안전하게 보관, 목적 달성 후 파기</p>

                <p className="font-semibold text-gray-800 pt-2">3. 안전성 확보 및 정보주체의 권리</p>
                <p><strong>보안 관리:</strong> 개인정보의 암호화, 접근 권한 제한, 보안 프로그램 설치 등 기술적/관리적 보호 조치 수행</p>
                <p><strong>동의 거부 권리:</strong> 개인정보 수집에 대한 동의를 거부할 수 있으나, 이 경우 채용 서비스 이용 및 인터뷰 진행이 제한될 수 있습니다.</p>

                <p className="font-semibold text-gray-800 pt-2">Summary of Recruitment Compliance</p>
                <p><strong>Direct Contact Prohibited:</strong> Any unauthorized contact or collection of candidate info before a signed contract is strictly forbidden.</p>
                <p><strong>Anti-Discrimination:</strong> Discrimination based on gender, age, race, or nationality is illegal under Korean Labor Law.</p>
                <p><strong>Data Privacy:</strong> Your information is securely stored for recruitment and visa support purposes only.</p>
              </div>

              {/* CAPTCHA Verification */}
              <PuzzleCaptcha
                onVerified={(token) => setForm((p) => ({ ...p, captcha_token: token }))}
                onError={(error) => alert(`CAPTCHA Error: ${error}`)}
              />

              <div>
                <Label required>동의 여부</Label>
                <SingleTog
                  value={form.privacy_policy}
                  onChange={(v) => setForm((p) => ({ ...p, privacy_policy: v }))}
                  options={['동의합니다. I agree.', '동의하지 않습니다. I do not agree.']}
                />
              </div>
            </section>
          </>
        )}

        {/* Error */}
        {(status === 'error' || errorMsg) && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
            {errorMsg}
          </div>
        )}

        {/* Navigation */}
        <div className="flex gap-3 pt-2">
          {step > 1 && (
            <button type="button" onClick={handleBack} className="btn-secondary flex-none px-6">
              &larr; Back
            </button>
          )}
          {step < 3 && (
            <button type="button" onClick={handleNext} className="btn-primary flex-1 py-3">
              Next Step &rarr;
            </button>
          )}
          {step === 3 && (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={status === 'submitting'}
              className="btn-primary flex-1 text-base py-3"
            >
              {status === 'submitting' ? '제출 중...' : '채용 문의 제출'}
            </button>
          )}
        </div>

        {/* Trust badge (simplified — no inline Lock badges) */}
        {step === 3 && (
          <div className="trust-badge">
            <span>All personal data is AES-256 encrypted and securely protected.</span>
            <span className="text-gray-300">&middot;</span>
            <span>모든 연락처 정보는 암호화 저장됩니다.</span>
          </div>
        )}

      </div>
    </div>
  )
}
