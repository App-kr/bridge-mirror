'use client'

/**
 * InquiryForm.tsx — Employer Hiring Inquiry Form (Client Component)
 * 3-Step Wizard: 기본정보 → 급여 및 복지 → 개인정보 동의
 * config prop: 관리자가 편집한 옵션 (없으면 *_DEFAULT 하드코딩 폴백)
 * Payment: Bank Transfer + PayPal only (no credit card — immutable)
 */

import { useState, useRef, useEffect } from 'react'
import PuzzleCaptcha from '@/components/PuzzleCaptcha'

import { API_URL } from '@/lib/api'
import { INQUIRY_DEFAULTS } from '@/lib/form-defaults'

const API = API_URL

// ── Default Options (form-defaults.ts 공유 참조) ──────────────────────────
const {
  BUSINESS_REG:        BUSINESS_REG_DEFAULT,
  HIRE_HIST:           HIRE_HIST_DEFAULT,
  NATIVE_COUNT:        NATIVE_COUNT_DEFAULT,
  VACANCIES:           VACANCIES_DEFAULT,
  CONTRACT_TYPE:       CONTRACT_TYPE_DEFAULT,
  TEACHING_AGE:        TEACHING_AGE_DEFAULT,
  CLASS_SIZE:          CLASS_SIZE_DEFAULT,
  AVG_LESSONS:         AVG_LESSONS_DEFAULT,
  PREFERRED_CANDIDATE: PREFERRED_CANDIDATE_DEFAULT,
  SALARY_RANGES:       SALARY_RANGES_DEFAULT,
  TRAVEL_SUPPORT:      TRAVEL_SUPPORT_DEFAULT,
  MEAL_OPTS:           MEAL_OPTS_DEFAULT,
  HOUSING_OPTS:        HOUSING_OPTS_DEFAULT,
  BENEFITS_OPTS:       BENEFITS_OPTS_DEFAULT,
  VACATION_INC:        VACATION_INC_DEFAULT,
} = INQUIRY_DEFAULTS

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
    <select className="input" value={value} onChange={(e) => onChange(e.target.value)}>
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
      <div className="border-2 border-dashed border-gray-200 rounded-xl p-4 text-center cursor-pointer
                   hover:border-blue-300 hover:bg-blue-50/30 transition-all"
        onClick={() => inputRef.current?.click()}>
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
  _url: '',   // honeypot — 봇 방어용, 비어있어야 함
  captcha_token: '',   // PuzzleCaptcha 토큰 — onVerified 에서 주입
}

// ── Page ────────────────────────────────────────────────────────────────────
export default function InquiryForm({ config = {} }: { config: Record<string, string[]> }) {
  // ── Dynamic config overrides (DB값 우선, 없으면 하드코딩 기본값) ─────────────
  const BUSINESS_REG        = config.BUSINESS_REG        ?? BUSINESS_REG_DEFAULT
  const HIRE_HIST           = config.HIRE_HIST           ?? HIRE_HIST_DEFAULT
  const NATIVE_COUNT        = config.NATIVE_COUNT        ?? NATIVE_COUNT_DEFAULT
  const VACANCIES           = config.VACANCIES           ?? VACANCIES_DEFAULT
  const CONTRACT_TYPE       = config.CONTRACT_TYPE       ?? CONTRACT_TYPE_DEFAULT
  const TEACHING_AGE        = config.TEACHING_AGE        ?? TEACHING_AGE_DEFAULT
  const CLASS_SIZE          = config.CLASS_SIZE          ?? CLASS_SIZE_DEFAULT
  const AVG_LESSONS         = config.AVG_LESSONS         ?? AVG_LESSONS_DEFAULT
  const PREFERRED_CANDIDATE = config.PREFERRED_CANDIDATE ?? PREFERRED_CANDIDATE_DEFAULT
  const SALARY_RANGES       = config.SALARY_RANGES       ?? SALARY_RANGES_DEFAULT
  const TRAVEL_SUPPORT      = config.TRAVEL_SUPPORT      ?? TRAVEL_SUPPORT_DEFAULT
  const MEAL_OPTS           = config.MEAL_OPTS           ?? MEAL_OPTS_DEFAULT
  const HOUSING_OPTS        = config.HOUSING_OPTS        ?? HOUSING_OPTS_DEFAULT
  const BENEFITS_OPTS       = config.BENEFITS_OPTS       ?? BENEFITS_OPTS_DEFAULT
  const VACATION_INC        = config.VACATION_INC        ?? VACATION_INC_DEFAULT

  const [phase,     setPhase]     = useState<'notice' | 'captcha' | 'form'>('notice')
  const [step,      setStep]      = useState(1)
  const [status,    setStatus]    = useState<'idle' | 'submitting' | 'success' | 'error'>('idle')
  const [errorMsg,  setErrorMsg]  = useState('')
  const [form,      setForm]      = useState(INIT)
  const [inquiryId, setInquiryId] = useState<string | null>(null)

  // 캡차 토큰 sessionStorage 복원 (새로고침 후에도 form 단계 유지)
  useEffect(() => {
    const savedToken = sessionStorage.getItem('bridge_inquiry_captcha_token')
    if (savedToken) {
      setForm((p) => ({ ...p, captcha_token: savedToken }))
      setPhase('form')
    }
  }, [])

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
    // "I agree." 만 통과 — "I do not agree." 또는 미선택은 차단
    const agreed = form.privacy_policy.includes('I agree') || form.privacy_policy.startsWith('동의합니다')
    if (!agreed) {
      setErrorMsg('You must agree to the Privacy Policy to submit. (제출하려면 개인정보처리방침에 동의해야 합니다.)')
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
        captcha_token: form.captcha_token,  // PuzzleCaptcha 토큰 (백엔드 필수)
      }
      if (!form.captcha_token) {
        setStatus('error')
        setErrorMsg('CAPTCHA puzzle is required. Please return to the start and complete it. (보안 인증 필요 — 시작 화면에서 퍼즐 완료)')
        return
      }
      let res: Response
      try {
        res = await fetch(`${API}/api/inquiry`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      } catch (netErr) {
        const m = netErr instanceof Error ? netErr.message : 'Network error'
        throw new Error(`Network error: ${m}. Please check your connection and try again.`)
      }
      let json: { success?: boolean; detail?: unknown; message?: string; error?: unknown; data?: { id?: number } } = {}
      try { json = await res.json() } catch { /* non-JSON */ }
      if (!res.ok || !json.success) {
        const pickMessage = (v: unknown): string => {
          if (!v) return ''
          if (typeof v === 'string') return v
          if (Array.isArray(v)) {
            return v.map((d) => {
              if (typeof d === 'object' && d !== null) {
                const o = d as Record<string, unknown>
                const loc = Array.isArray(o.loc) ? o.loc.slice(1).join('.') : ''
                return loc ? `${loc}: ${o.msg}` : (o.msg ? String(o.msg) : JSON.stringify(d))
              }
              return String(d)
            }).join(' / ')
          }
          if (typeof v === 'object') {
            const o = v as Record<string, unknown>
            return String(o.message ?? o.detail ?? o.context ?? o.error ?? JSON.stringify(v))
          }
          return String(v)
        }
        throw new Error(pickMessage(json.detail) || pickMessage(json.error) || pickMessage(json.message) || `서버 오류 (${res.status} ${res.statusText || ''})`)
      }
      if (json.data?.id) setInquiryId(String(json.data.id))
      setStatus('success')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Submission failed.'
      // CAPTCHA 만료 시 자동으로 captcha 단계로 — 사용자 다시 풀기만 하면 됨
      if (msg.toLowerCase().includes('captcha')) {
        sessionStorage.removeItem('bridge_inquiry_captcha_token')
        setForm((p) => ({ ...p, captcha_token: '' }))
        setErrorMsg('Security verification expired. Please complete the puzzle again. (보안 확인이 만료되었습니다. 퍼즐을 다시 풀어주세요.)')
        setPhase('captcha')
        setStatus('error')
        return
      }
      setErrorMsg(msg)
      setStatus('error')
      // 운영자 알림 (fire-and-forget)
      try {
        fetch(`${API}/api/security/report`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'inquiry_submission_failed',
            error: msg.slice(0, 500),
            email: form.email?.slice(0, 100) || '',
            school: form.school_name?.slice(0, 100) || '',
            user_agent: navigator.userAgent.slice(0, 200),
          }),
        }).catch(() => {})
      } catch { /* ignore */ }
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

  // ── Notice 화면 ─────────────────────────────────────────────────────────
  if (phase === 'notice') {
    return (
      <div className="flex items-center justify-center px-4 py-6 sm:py-10" style={{ minHeight: 'calc(100vh - 44px)' }}>
        <div className="w-full max-w-2xl">
          {/* Header */}
          <div className="text-center mb-7 space-y-3">
            <span className="inline-block text-sm font-bold text-blue-600 bg-blue-50
                             border border-blue-200 rounded-full px-4 py-1.5 uppercase tracking-wider">
              Schools &amp; Employers
            </span>
            <h1 className="text-3xl sm:text-4xl font-black text-gray-900 leading-tight">
              Hiring Request for Native Teachers
            </h1>
            <p className="text-sm text-gray-500">원어민 구인신청</p>
          </div>

          {/* Card */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-md overflow-hidden">
            <div className="px-8 sm:px-10 pt-8 pb-6 space-y-6">
              {/* Notice text — English first, Korean as gray subtitle */}
              <div className="space-y-1.5">
                <p className="text-[15px] sm:text-base text-gray-800 leading-relaxed">
                  All information provided here is required for the recruitment process.
                  Inaccurate or false information may restrict service eligibility.
                </p>
                <p className="text-xs sm:text-sm text-gray-400 leading-relaxed">
                  작성하신 내용은 채용 대행 서비스 진행을 위한 필수 정보입니다.
                  허위 또는 부정확한 정보가 확인될 경우 서비스 진행이 제한될 수 있으니
                  정확하게 입력해 주세요.
                </p>
              </div>

              <div className="border-t border-gray-100" />

              {/* Email notice — English first */}
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <p className="text-[15px] sm:text-base text-gray-800 leading-relaxed">
                    After submission, please email a copy of your{' '}
                    <span className="font-semibold text-gray-900">business registration certificate</span>.
                  </p>
                  <p className="text-xs sm:text-sm text-gray-400 leading-relaxed">
                    접수 완료 후 사업자 등록증 사본을 이메일로 보내주시기 바랍니다.
                  </p>
                </div>
                <a
                  href="mailto:bridgejobkr@gmail.com?subject=사업자등록증 사본 첨부 - 구인신청"
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl
                             bg-gray-50 hover:bg-blue-50 border border-gray-200 hover:border-blue-300
                             text-gray-700 hover:text-blue-700 text-sm font-semibold transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                    <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
                  </svg>
                  Send to Bridge Team / 브릿지팀으로 메일전송
                </a>
              </div>
            </div>

            {/* Footer / CTA */}
            <div className="px-8 sm:px-10 pb-8 pt-5 border-t border-gray-100 space-y-4">
              <p className="text-xs text-gray-500 leading-relaxed">
                By continuing, you confirm and agree to the above. Collected information is used solely for recruitment services.{' '}
                <a
                  href="/privacy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:text-gray-700"
                >
                  Privacy Policy
                </a>
                <br />
                <span className="text-gray-400">
                  계속 진행하시면 위 내용을 확인하고 동의한 것으로 간주됩니다. 수집된 정보는 채용 대행 서비스 목적으로만 사용됩니다.
                </span>
              </p>
              <button
                type="button"
                onClick={() => setPhase('captcha')}
                className="btn-shimmer w-full py-4 bg-blue-500 hover:bg-blue-600 active:bg-blue-700
                           text-white text-base font-semibold rounded-xl transition-colors"
              >
                Agree &amp; Continue / 동의하고 시작하기 →
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── CAPTCHA 화면 (notice → captcha → form) ────────────────────────────
  if (phase === 'captcha') {
    return (
      <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 p-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
          <div className="px-6 pt-6 pb-2">
            <h2 className="text-lg font-bold text-gray-900 mb-1">Security Verification / 보안 확인</h2>
            <p className="text-sm text-gray-500 mb-1">Complete the puzzle to continue with your inquiry.</p>
            <p className="text-xs text-gray-400 mb-4">채용 문의 제출을 계속하려면 아래 퍼즐을 완료해 주세요.</p>
            <PuzzleCaptcha
              onVerified={(token) => {
                sessionStorage.setItem('bridge_inquiry_captcha_token', token)
                setForm((p) => ({ ...p, captcha_token: token }))
                setPhase('form')
              }}
              onError={(error) => alert(`CAPTCHA Error: ${error}`)}
            />
          </div>
        </div>
      </div>
    )
  }

  // ── Page ────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-16">

      <div className="space-y-2">
        <span className="inline-block text-xs font-semibold text-blue-600 bg-blue-50
                         border border-blue-200 rounded-full px-3 py-1 uppercase tracking-wider">
          For Schools & Academies
        </span>
        <h1 className="text-3xl font-black text-gray-900">Hiring Request — Native Teacher</h1>
        <p className="text-sm text-gray-500">강사(교사) 구인신청</p>
        <div className="space-y-1.5 text-[14px] text-gray-700 leading-relaxed">
          <p>
            All information provided here is required for the recruitment process. Inaccurate or false information may restrict service eligibility.
            <br />
            <span className="text-gray-500">작성하신 내용은 채용 대행 서비스 진행을 위한 필수 정보입니다. 허위 또는 부정확한 정보가 확인될 경우 서비스 진행이 제한될 수 있으니 정확하게 입력해 주세요.</span>
          </p>
          <p>
            After submission, please email a copy of your <strong className="text-gray-900 font-semibold">business registration certificate</strong>.
            <br />
            <span className="text-gray-500">접수 완료 후 사업자 등록증 사본을 이메일로 보내주시기 바랍니다.</span>
          </p>
          <a
            href="mailto:bridgejobkr@gmail.com?subject=사업자등록증 사본 첨부 - 구인신청"
            className="inline-flex items-center gap-1.5 mt-0.5 px-3 py-1.5 rounded-lg
                       bg-gray-100 hover:bg-blue-50 border border-gray-200 hover:border-blue-300
                       text-gray-700 hover:text-blue-700 text-xs font-medium transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
              <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
              <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
            </svg>
            bridgejobkr@gmail.com 으로 보내기
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

            <section className="card space-y-4">
              <Sec title="담당자 정보" subtitle="Contact Person" />
              <p className="text-xs text-gray-400 leading-relaxed -mt-2">
                고용주가 아닌 경우, 또는 향후 채용 담당자가 변경될 시 반드시 연락처 변경 사실을 알려 주세요.
                수신자 명단 업데이트가 이루어지지 않을 경우 중요한 안내를 받지 못할 수 있습니다.
              </p>
              {/* Honeypot — 봇만 채움, 사용자 안 보임 */}
              <input
                type="text"
                name="_url"
                tabIndex={-1}
                autoComplete="off"
                aria-hidden="true"
                style={{ position: 'absolute', left: '-10000px', width: '1px', height: '1px', opacity: 0 }}
                value={form._url as string || ''}
                onChange={set('_url' as keyof typeof form)}
              />
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
                <SingleTog value={form.business_registration}
                  onChange={(v) => setForm((p) => ({ ...p, business_registration: v }))}
                  options={BUSINESS_REG} />
              </div>
            </section>

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
                  <SingleTog value={form.hiring_history}
                    onChange={(v) => setForm((p) => ({ ...p, hiring_history: v }))}
                    options={HIRE_HIST} />
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

            <section className="card space-y-5">
              <Sec title="수업 조건" subtitle="Teaching Conditions" />
              <div>
                <Label>계약구분 / Contract Type</Label>
                <SingleTog value={form.contract_type}
                  onChange={(v) => setForm((p) => ({ ...p, contract_type: v }))}
                  options={CONTRACT_TYPE} />
              </div>
              <div>
                <Label required>수업대상</Label>
                <CheckList value={form.teaching_age as string[]}
                  onChange={(arr) => setForm((p) => ({ ...p, teaching_age: arr }))}
                  options={TEACHING_AGE} />
              </div>
              <div>
                <Label required>학생수</Label>
                <Desc text="1강의당 최대 학생수" />
                <SingleTog value={form.class_size}
                  onChange={(v) => setForm((p) => ({ ...p, class_size: v }))}
                  options={CLASS_SIZE} />
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
                <Dropdown value={form.avg_lessons}
                  onChange={(v) => setForm((p) => ({ ...p, avg_lessons: v }))}
                  options={AVG_LESSONS} />
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
                <CheckList value={form.preferred_candidate as string[]}
                  onChange={(arr) => setForm((p) => ({ ...p, preferred_candidate: arr }))}
                  options={PREFERRED_CANDIDATE} />
              </div>
            </section>
          </>
        )}

        {/* ================================================================ */}
        {/*  STEP 2 — 급여 및 복지                                           */}
        {/* ================================================================ */}
        {step === 2 && (
          <>
            <section className="card space-y-4">
              <Sec title="급여조건" subtitle="Salary Range" />
              <Desc text="최저~최고 범위를 모두 선택해 주세요. 좋은 강사에게 지급 가능한 페이를 상한선으로 선택하는 게 좋습니다." />
              <CheckList value={form.salary_raw as string[]}
                onChange={(arr) => setForm((p) => ({ ...p, salary_raw: arr }))}
                options={SALARY_RANGES} />
            </section>

            <section className="card space-y-5">
              <Sec title="이동지원 & 식사" subtitle="Travel & Meals" />
              <div>
                <Label required>이동지원</Label>
                <Dropdown value={form.travel_support}
                  onChange={(v) => setForm((p) => ({ ...p, travel_support: v }))}
                  options={TRAVEL_SUPPORT} />
              </div>
              <div>
                <Label required>식사/식대</Label>
                <CheckList value={form.meal_provided as string[]}
                  onChange={(arr) => setForm((p) => ({ ...p, meal_provided: arr }))}
                  options={MEAL_OPTS} />
              </div>
            </section>

            <section className="card space-y-4">
              <Sec title="Housing" subtitle="숙소제공" />
              <Desc text="Housing support is typically offered in line with local rental market rates near the workplace. (거주비용 지원은 일반적으로 근무처 주변의 숙소 시세에 맞추어 제공하는 것을 추천합니다.)" />
              <Dropdown value={form.housing_provided}
                onChange={(v) => setForm((p) => ({ ...p, housing_provided: v }))}
                options={HOUSING_OPTS} />
              <div>
                <Label>숙소관련</Label>
                <Desc text="옵션이나 월세금 등을 적어주십시오" />
                <input className="input" placeholder="e.g. 풀옵션/ 월세 70만원+보증금 1천만원 지원"
                  value={form.housing_detail} onChange={set('housing_detail')} />
              </div>
            </section>

            <section className="card space-y-4">
              <Sec title="복지" subtitle="Benefits" />
              <Desc text="교육기관별 복지입니다. 해당사항만 체크해주시되 원어민 채용시 필수항목은 반드시 선택" />
              <CheckList value={form.benefits as string[]}
                onChange={(arr) => setForm((p) => ({ ...p, benefits: arr }))}
                options={BENEFITS_OPTS} />
            </section>

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
                  <SingleTog value={form.vacation_includes}
                    onChange={(v) => setForm((p) => ({ ...p, vacation_includes: v }))}
                    options={VACATION_INC} />
                </div>
              </div>
              <div>
                <Label required>보건휴가</Label>
                <Desc text="Sick leave" />
                <input className="input" placeholder="e.g. 3일/년"
                  value={form.sick_leave} onChange={set('sick_leave')} />
              </div>
            </section>

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
              <Sec title="Privacy Policy & Compliance" subtitle="개인정보처리방침" />
              <div className="bg-gray-50 rounded-xl p-4 text-xs text-gray-700 space-y-3 max-h-64 overflow-y-auto border border-gray-200 leading-relaxed">
                <p className="font-semibold text-gray-900">1. Employer Compliance & Anti-Discrimination</p>
                <p><strong>No Direct Contact:</strong> Before a signed contract, unauthorized collection of candidate personal information or any direct contact without prior agreement is strictly prohibited. Violations will result in immediate billing of the full service fee and potential legal liability for trade-secret infringement.</p>
                <p><strong>No Gender / Age Discrimination:</strong> Discrimination by gender or age, or imposing unnecessary physical or age requirements unrelated to job duties, is prohibited. (Up to KRW 5 million fine under the Equal Employment Opportunity Act.)</p>
                <p><strong>No Nationality / Race Discrimination:</strong> Unfair working conditions based on nationality, race, or country of origin are prohibited under Korean human-rights and foreign-worker employment laws.</p>
                <p className="text-gray-600 pl-2 border-l-2 border-amber-300 ml-1">
                  If discriminatory treatment occurs after hiring based on subjective opinions regarding the teacher&apos;s nationality or race, Bridge cannot provide additional mediation or rematching support.
                </p>
                <p className="text-[11px] text-gray-400 pl-2 border-l-2 border-gray-200 ml-1">
                  영업 보호 및 직접 연락 금지 · 성별·연령 차별 금지 · 국적·인종 차별 금지 — 위반 시 정상 서비스 요금 부과 및 관련 법령에 따른 제재가 있을 수 있습니다.
                </p>

                <p className="font-semibold text-gray-900 pt-2">2. Collection & Use of Personal Information</p>
                <p><strong>Collected Items:</strong> Name, contact, business information (registration certificate), hiring conditions, access logs.</p>
                <p><strong>Purpose:</strong> Native teacher matching, interview coordination, employment-contract drafting, and visa administrative support.</p>
                <p><strong>Retention:</strong> Stored securely for the period required by law, then destroyed.</p>
                <p className="text-[11px] text-gray-400 pl-2 border-l-2 border-gray-200 ml-1">
                  수집 항목: 성명·연락처·사업장 정보·채용 조건·접속 로그 / 이용 목적: 강사 매칭·인터뷰 조율·계약서·비자 행정 / 보유 기간: 법령에 따른 기간 안전 보관 후 파기.
                </p>

                <p className="font-semibold text-gray-900 pt-2">3. Security & Your Rights</p>
                <p><strong>Security:</strong> Encryption, restricted access, and technical/administrative safeguards are applied to all personal data.</p>
                <p><strong>Right to Refuse:</strong> You may refuse consent, but service use and interviews may be limited as a result.</p>
                <p className="text-[11px] text-gray-400 pl-2 border-l-2 border-gray-200 ml-1">
                  보안 관리: 암호화·접근 권한 제한·기술적 보호조치 / 동의 거부 시 채용 서비스 이용 및 인터뷰가 제한될 수 있습니다.
                </p>
              </div>

              {/* CAPTCHA는 시작 단계(captcha phase)에서 이미 처리됨 */}
              {form.captcha_token && (
                <div className="rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-2.5 text-sm text-emerald-700">
                  ✓ Security verification completed at the start.
                </div>
              )}

              <div>
                <Label required>Agreement / 동의 여부</Label>
                <SingleTog value={form.privacy_policy}
                  onChange={(v) => {
                    setForm((p) => ({ ...p, privacy_policy: v }))
                    if (v.includes('I agree') || v.startsWith('동의합니다')) setErrorMsg('')
                  }}
                  options={['I agree. 동의합니다.', 'I do not agree. 동의하지 않습니다.']} />
                {form.privacy_policy.includes('do not agree') && (
                  <div className="mt-3 rounded-lg bg-amber-50 border border-amber-200 px-4 py-2.5 text-sm text-amber-800">
                    You must agree to the Privacy Policy in order to submit this inquiry.
                    <br />
                    <span className="text-xs text-amber-700">제출하려면 개인정보처리방침에 동의해야 합니다.</span>
                  </div>
                )}
              </div>
            </section>
          </>
        )}

        {(status === 'error' || errorMsg) && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">{errorMsg}</div>
        )}

        <div className="flex gap-3 pt-2">
          {step > 1 && (
            <button type="button" onClick={handleBack} className="btn-secondary flex-none px-6">&larr; Back</button>
          )}
          {step < 3 && (
            <button type="button" onClick={handleNext} className="btn-primary flex-1 py-3">Next Step &rarr;</button>
          )}
          {step === 3 && (
            <button type="button" onClick={handleSubmit} disabled={status === 'submitting'}
              className="btn-shimmer btn-primary flex-1 text-base py-3">
              <span>{status === 'submitting' ? '제출 중...' : '채용 문의 제출'}</span>
            </button>
          )}
        </div>

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
