'use client'

/**
 * ApplyForm.tsx — Candidate Application Form (Client Component)
 * 3-Step Wizard: Basic Info → Preferences → Contact & Agreement
 * config prop: 관리자가 편집한 옵션 (없으면 *_DEFAULT 하드코딩 폴백)
 */

import { useState, useRef, useEffect } from 'react'
import { resizeImage } from '@/lib/image-resize'
import PuzzleCaptcha from '@/components/PuzzleCaptcha'

import { API_URL } from '@/lib/api'
import { APPLY_DEFAULTS } from '@/lib/form-defaults'

const API       = API_URL
const TOKEN_KEY = 'bridge_apply_token'

// ── Default Options (form-defaults.ts 공유 참조) ──────────────────────────
const {
  HOW_TO:          HOW_TO_DEFAULT,
  NATIONALITIES:   NATIONALITIES_DEFAULT,
  ANCESTRY:        ANCESTRY_DEFAULT,
  EDUCATION:       EDUCATION_DEFAULT,
  CERTIFICATION:   CERTIFICATION_DEFAULT,
  E_VISA:          E_VISA_DEFAULT,
  PASSPORT:        PASSPORT_DEFAULT,
  CRIMINAL_RECORD: CRIMINAL_RECORD_DEFAULT,
  DOC_STATUS:      DOC_STATUS_DEFAULT,
  TARGET_AGE:      TARGET_AGE_DEFAULT,
  AREA_PREFS:      AREA_PREFS_DEFAULT,
  EXPERIENCE:      EXPERIENCE_DEFAULT,
  EMPLOYMENT:      EMPLOYMENT_DEFAULT,
  MARITAL:         MARITAL_DEFAULT,
  HOUSING:         HOUSING_DEFAULT,
  DEPENDENTS_PETS: DEPENDENTS_PETS_DEFAULT,
  PERSONAL:        PERSONAL_DEFAULT,
  RELIGION:        RELIGION_DEFAULT,
  HEALTH:          HEALTH_DEFAULT,
  CRC:             CRC_DEFAULT,
  KR_CRC:          KR_CRC_DEFAULT,
} = APPLY_DEFAULTS

const STEP_LABELS = ['Basic Info', 'Preferences', 'Contact & Agreement']

// ── Date helpers ──────────────────────────────────────────────────────────
const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
const currentYear = new Date().getFullYear()
const DOB_YEARS   = Array.from({ length: 60 }, (_, i) => currentYear - 18 - i)
const START_YEARS = [currentYear, currentYear + 1, currentYear + 2]
const DAYS        = Array.from({ length: 31 }, (_, i) => i + 1)

// ── Step Indicator ─────────────────────────────────────────────────────────
function StepIndicator({ step }: { step: number }) {
  return (
    <div className="card !p-4">
      <div className="flex items-center">
        {STEP_LABELS.map((label, i) => {
          const n    = i + 1
          const done = n < step
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
    <div className="text-[22px] font-bold text-[#1a1a2e] uppercase tracking-wide border-b border-gray-100 pb-2 mb-2">
      {title}
      {subtitle && <span className="ml-2 text-gray-400 normal-case font-normal tracking-normal text-base">{subtitle}</span>}
    </div>
  )
}

function Label({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <label className="block text-[16px] font-semibold text-[#111] mb-1">
      {children}{required && <span className="text-[#d32f2f] ml-0.5">*</span>}
    </label>
  )
}

function Desc({ text }: { text: string }) {
  return <p className="text-[15px] text-[#333] -mt-0.5 mb-2 leading-relaxed">{text}</p>
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
  value, onChange, options, placeholder = 'Select...',
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

/** Nationality — radio-style list */
function RadioList({
  value, onChange, options,
}: { value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <div className="grid sm:grid-cols-2 gap-x-6 gap-y-2">
      {options.map((o) => (
        <label key={o} className="flex items-center gap-3 cursor-pointer group">
          <input
            type="radio"
            name="nationality_radio"
            checked={value === o}
            onChange={() => onChange(o)}
            className="w-4 h-4 border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700 group-hover:text-gray-900">{o}</span>
        </label>
      ))}
    </div>
  )
}

/** Date picker with Year / Month / Day dropdowns */
function EasyDate({
  value, onChange, years,
}: { value: string; onChange: (v: string) => void; years: number[] }) {
  const parts = value ? value.split('-') : ['', '', '']
  const y = parts[0] || ''
  const m = parts[1] || ''
  const d = parts[2] || ''

  function update(yr: string, mo: string, dy: string) {
    if (yr && mo && dy) {
      onChange(`${yr}-${mo.padStart(2,'0')}-${dy.padStart(2,'0')}`)
    } else {
      const partial = [yr, mo.padStart(2,'0'), dy.padStart(2,'0')].join('-')
      onChange(partial)
    }
  }

  return (
    <div className="grid grid-cols-3 gap-1 sm:gap-2">
      <select className="input text-sm" value={y}
        onChange={(e) => update(e.target.value, m, d)}>
        <option value="">Year</option>
        {years.map((yr) => <option key={yr} value={String(yr)}>{yr}</option>)}
      </select>
      <select className="input text-sm" value={String(parseInt(m) || '')}
        onChange={(e) => update(y, e.target.value, d)}>
        <option value="">Month</option>
        {MONTHS.map((label, i) => <option key={i} value={String(i+1)}>{label}</option>)}
      </select>
      <select className="input text-sm" value={String(parseInt(d) || '')}
        onChange={(e) => update(y, m, e.target.value)}>
        <option value="">Day</option>
        {DAYS.map((day) => <option key={day} value={String(day)}>{day}</option>)}
      </select>
    </div>
  )
}

// ── Single-type Queue Upload Zone ─────────────────────────────────────────
function QueueZone({
  fileType, icon, hint, accept, queuedFiles, setQueuedFiles, maxFiles,
}: {
  fileType: string; icon: string; hint: string; accept: string
  queuedFiles: { type: string; file: File }[]
  setQueuedFiles: React.Dispatch<React.SetStateAction<{ type: string; file: File }[]>>
  maxFiles: number
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const typeCount = queuedFiles.filter(q => q.type === fileType).length
  const totalCount = queuedFiles.length
  const canAdd = totalCount < maxFiles

  function addFiles(fileList: File[]) {
    const remaining = maxFiles - totalCount
    fileList.slice(0, remaining).forEach(f => {
      setQueuedFiles(prev => [...prev, { type: fileType, file: f }])
    })
  }

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept={accept}
        multiple={fileType === 'certificate'}
        onChange={e => {
          if (e.target.files?.length) addFiles(Array.from(e.target.files))
          e.target.value = ''
        }}
      />
      <div
        role="button"
        tabIndex={canAdd ? 0 : -1}
        aria-disabled={!canAdd}
        onClick={() => canAdd && inputRef.current?.click()}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
        onDragOver={e => { e.preventDefault(); e.stopPropagation() }}
        onDrop={e => {
          e.preventDefault(); e.stopPropagation()
          if (!canAdd) return
          const files: File[] = []
          if (e.dataTransfer.items) {
            for (let i = 0; i < e.dataTransfer.items.length; i++) {
              const f = e.dataTransfer.items[i].getAsFile()
              if (f) files.push(f)
            }
          } else {
            Array.from(e.dataTransfer.files).forEach(f => files.push(f))
          }
          addFiles(files)
        }}
        className={`flex items-center gap-3 w-full border-2 border-dashed rounded-xl px-4 py-4 cursor-pointer
                    transition-all select-none text-left
                    ${!canAdd
                      ? 'border-gray-200 opacity-40 cursor-not-allowed'
                      : typeCount > 0
                        ? 'border-green-400 bg-green-50/40 hover:border-green-500'
                        : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50/30'}`}
      >
        <span className="text-2xl">{icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-700">{hint}</p>
          <p className="text-xs text-gray-400 mt-0.5">
            {typeCount > 0 ? `${typeCount} file${typeCount > 1 ? 's' : ''} selected` : 'Click or drag here'}
          </p>
        </div>
        {typeCount > 0 && (
          <span className="text-green-600 text-xs font-medium shrink-0">✓ Ready</span>
        )}
      </div>
    </div>
  )
}

// ── File Upload Component ──────────────────────────────────────────────────
interface UploadedFile { name: string; file_url?: string; uploading?: boolean; error?: string }

const MAX_FILES = 6

function FileUpload({
  label, accept, fileType, entityType, entityId, onUploaded,
}: {
  label: string; accept: string; fileType: string
  entityType: string; entityId: string | null
  onUploaded?: (url: string) => void
}) {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFiles(fileList: FileList | null) {
    if (!fileList || !entityId) return
    for (let i = 0; i < fileList.length; i++) {
      let file = fileList[i]
      const entry: UploadedFile = { name: file.name, uploading: true }
      setFiles(prev => [...prev, entry])

      try {
        if (file.type.startsWith('image/')) file = await resizeImage(file)
        const fd = new FormData()
        fd.append('file', file)
        const token = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null
        const res = await fetch(`${API}/api/upload/${entityType}/${entityId}?file_type=${fileType}`, {
          method: 'POST', body: fd,
          headers: token ? { 'X-Apply-Token': token } : {},
        })
        const json = await res.json()
        if (!res.ok) throw new Error(json.detail ?? 'Upload failed')
        setFiles(prev => prev.map(f => f.name === entry.name && f.uploading
          ? { name: entry.name, file_url: json.data?.file_url } : f))
        if (json.data?.file_url && onUploaded) onUploaded(json.data.file_url)
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
          multiple={fileType === 'certificate' || fileType === 'attachment'}
          onChange={(e) => handleFiles(e.target.files)} />
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-xs text-blue-500 mt-1">Click to browse</p>
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

// ── Initial form state ─────────────────────────────────────────────────────
const INIT = {
  /* Step 1 — Basic Info */
  email: '', how_to: '', full_name: '',
  nationality: '', ancestry: '', dob: '', gender: '',
  current_location: '',
  education: '', major: '', certification: '',
  e_visa: '', arc_holders: '', passport: '', criminal_record: '', doc_status: '',

  /* Step 2 — Preferences */
  start_date: '', target_age: [] as string[], area_prefs: [] as string[],
  job_prefs: '', experience: '', employment: '', reference: '',
  current_salary: '', desired_salary: '',
  marital_status: '', housing: '', dependents_pets: [] as string[],
  personal_considerations: '', religion: '',

  /* Step 3 — Contact & Agreement */
  health_info: '', criminal_record_check: '', korean_criminal_record: '',
  interview_time: '', kakaotalk: '', mobile_phone: '',
  agreement: '', facts: '',
  _url: '',   // honeypot — 봇 방어용, 비어있어야 함
}

// ── Page ────────────────────────────────────────────────────────────────────
export default function ApplyForm({ config = {} }: { config: Record<string, string[]> }) {
  // ── Dynamic config overrides (DB값 우선, 없으면 하드코딩 기본값) ─────────────
  const HOW_TO          = config.HOW_TO          ?? HOW_TO_DEFAULT
  const NATIONALITIES   = config.NATIONALITIES   ?? NATIONALITIES_DEFAULT
  const ANCESTRY        = config.ANCESTRY        ?? ANCESTRY_DEFAULT
  const EDUCATION       = config.EDUCATION       ?? EDUCATION_DEFAULT
  const CERTIFICATION   = config.CERTIFICATION   ?? CERTIFICATION_DEFAULT
  const E_VISA          = config.E_VISA          ?? E_VISA_DEFAULT
  const PASSPORT        = config.PASSPORT        ?? PASSPORT_DEFAULT
  const CRIMINAL_RECORD = config.CRIMINAL_RECORD ?? CRIMINAL_RECORD_DEFAULT
  const DOC_STATUS      = config.DOC_STATUS      ?? DOC_STATUS_DEFAULT
  const TARGET_AGE      = config.TARGET_AGE      ?? TARGET_AGE_DEFAULT
  const AREA_PREFS      = config.AREA_PREFS      ?? AREA_PREFS_DEFAULT
  const EXPERIENCE      = config.EXPERIENCE      ?? EXPERIENCE_DEFAULT
  const EMPLOYMENT      = config.EMPLOYMENT      ?? EMPLOYMENT_DEFAULT
  const MARITAL         = config.MARITAL         ?? MARITAL_DEFAULT
  const HOUSING         = config.HOUSING         ?? HOUSING_DEFAULT
  const DEPENDENTS_PETS = config.DEPENDENTS_PETS ?? DEPENDENTS_PETS_DEFAULT
  const PERSONAL        = config.PERSONAL        ?? PERSONAL_DEFAULT
  const RELIGION        = config.RELIGION        ?? RELIGION_DEFAULT
  const HEALTH          = config.HEALTH          ?? HEALTH_DEFAULT
  const CRC             = config.CRC             ?? CRC_DEFAULT
  const KR_CRC          = config.KR_CRC          ?? KR_CRC_DEFAULT

  // ── 흐름: notice → captcha → form ──────────────────────────────────────
  const [phase, setPhase] = useState<'notice' | 'captcha' | 'form'>('notice')

  useEffect(() => {
    // 같은 세션에서 이미 캡차 통과했으면 토큰 복원 + form 단계로
    // (이전 버그: 'ok' 플래그만 저장 → 토큰 비어있는데 form 점프 → submit 실패)
    const savedToken = sessionStorage.getItem('bridge_captcha_token')
    if (savedToken) {
      setForm((p) => ({ ...p, captcha_token: savedToken }))
      setPhase('form')
    }
  }, [])

  function handleCaptchaVerified(token: string) {
    sessionStorage.setItem('bridge_captcha_token', token)
    setForm((p) => ({ ...p, captcha_token: token }))
    setPhase('form')
  }

  const [step,        setStep]        = useState(1)
  const [status,      setStatus]      = useState<'idle' | 'submitting' | 'success' | 'error'>('idle')
  const [errorMsg,    setErrorMsg]    = useState('')
  const [form,        setForm]        = useState(INIT)
  const [candidateId, setCandidateId] = useState<string | null>(null)

  const [queuedFiles, setQueuedFiles] = useState<{ type: string; file: File }[]>([])

  const set = (field: keyof typeof INIT) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((p) => ({ ...p, [field]: e.target.value }))

  function handleNext() {
    setErrorMsg('')
    if (step === 1 && !form.full_name.trim()) {
      setErrorMsg('Full name is required before continuing.')
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

  const [uploadResults, setUploadResults] = useState<{ name: string; ok: boolean; error?: string }[]>([])

  async function uploadQueuedFiles(cid: string) {
    const results: { name: string; ok: boolean; error?: string }[] = []
    for (const item of queuedFiles) {
      try {
        let file = item.file
        if (file.type.startsWith('image/')) file = await resizeImage(file)
        const fd = new FormData()
        fd.append('file', file)
        const token = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null
        const res = await fetch(`${API}/api/upload/candidate/${cid}?file_type=${item.type}`, {
          method: 'POST', body: fd,
          headers: token ? { 'X-Apply-Token': token } : {},
        })
        if (!res.ok) {
          const json = await res.json().catch(() => ({ detail: 'Upload failed' }))
          results.push({ name: item.file.name, ok: false, error: json.detail ?? 'Upload failed' })
        } else {
          results.push({ name: item.file.name, ok: true })
        }
      } catch (e) {
        results.push({ name: item.file.name, ok: false, error: e instanceof Error ? e.message : 'Upload failed' })
      }
    }
    setUploadResults(results)
  }

  async function handleSubmit() {
    if (form.agreement !== 'I Agree') {
      setErrorMsg('Please select "I Agree" before submitting.')
      return
    }
    setStatus('submitting')
    try {
      const existingToken = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { dependents_pets, ...rest } = form
      const payload = {
        ...rest,
        target_age: (form.target_age as string[]).join(', '),
        area_prefs: (form.area_prefs as string[]).join(', '),
        dependents: (dependents_pets as string[]).join(', '),
        personal_considerations: form.personal_considerations,
        source: 'web_form',
        ...(existingToken ? { apply_token: existingToken } : {}),
      }
      let res: Response
      try {
        res = await fetch(`${API}/api/apply`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      } catch (netErr) {
        const msg = netErr instanceof Error ? netErr.message : 'Network error'
        throw new Error(`Network error: ${msg}. Please check your connection and try again.`)
      }

      let json: { success?: boolean; detail?: unknown; message?: string; error?: unknown; data?: { id?: number; apply_token?: string } } = {}
      try { json = await res.json() } catch { /* non-JSON response */ }

      if (!res.ok || !json.success) {
        // 모든 에러 객체/문자열/배열 처리 — 절대 [object Object] 노출 안 함
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
            // BRIDGE bridge_error 구조: {code, message, status} 또는 {detail, context}
            return String(o.message ?? o.detail ?? o.context ?? o.error ?? JSON.stringify(v))
          }
          return String(v)
        }
        const msg = pickMessage(json.detail) || pickMessage(json.error) || pickMessage(json.message) || `서버 오류 (${res.status} ${res.statusText || ''})`
        throw new Error(msg)
      }

      if (json.data?.apply_token && typeof window !== 'undefined') {
        localStorage.setItem(TOKEN_KEY, json.data.apply_token)
      }
      const newId = json.data?.id
      if (newId) {
        const cid = String(newId)
        setCandidateId(cid)
        if (queuedFiles.length > 0) uploadQueuedFiles(cid)
      }
      setStatus('success')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Submission failed.'
      // CAPTCHA 실패 시 자동으로 captcha 단계로 돌려보냄 — 만료/누락 자동 복구
      if (msg.toLowerCase().includes('captcha')) {
        sessionStorage.removeItem('bridge_captcha_token')
        setForm((p) => ({ ...p, captcha_token: '' }))
        setErrorMsg('Security verification expired. Please complete the puzzle again. (보안 확인이 만료되었습니다. 퍼즐을 다시 풀어주세요.)')
        setPhase('captcha')
        setStatus('error')
        return
      }
      setErrorMsg(msg)
      setStatus('error')
      // 운영자 텔레그램/이메일 알림 (백엔드 endpoint, fire-and-forget)
      try {
        fetch(`${API}/api/security/report`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'apply_submission_failed',
            error: msg.slice(0, 500),
            email: form.email?.slice(0, 100) || '',
            full_name: form.full_name?.slice(0, 100) || '',
            user_agent: navigator.userAgent.slice(0, 200),
          }),
        }).catch(() => {})
      } catch { /* ignore */ }
    }
  }

  // ── Success ─────────────────────────────────────────────────────────────
  if (status === 'success') {
    const isUpdate = typeof window !== 'undefined' && Boolean(localStorage.getItem(TOKEN_KEY))
    return (
      <div className="max-w-lg mx-auto text-center py-24 space-y-5">
        <div className="text-6xl">{isUpdate ? '\u2705' : '\uD83C\uDF89'}</div>
        <h2 className="text-2xl font-bold text-gray-900">
          {isUpdate ? 'Profile Updated!' : 'Your profile has been updated!'}
        </h2>
        <p className="text-gray-600 leading-relaxed">
          We will review and contact you via <strong className="text-gray-900">Google Meet</strong>.
          <br />
          Please make sure to turn on your email notifications.
        </p>

        {uploadResults.length > 0 && (
          <div className="text-left mt-6 p-4 bg-gray-50 rounded-xl border space-y-1">
            <p className="text-sm font-semibold text-gray-700 mb-2">File Upload Results</p>
            {uploadResults.map((r, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span className={r.ok ? 'text-green-600' : 'text-red-500'}>{r.ok ? 'Uploaded' : 'Failed'}</span>
                <span className="text-gray-600 truncate">{r.name}</span>
                {r.error && <span className="text-red-400">({r.error})</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // ── Notice 화면 ─────────────────────────────────────────────────────────
  if (phase === 'notice') {
    return (
      <div className="flex items-center justify-center px-4 py-6" style={{ minHeight: 'calc(100vh - 44px)' }}>
        <div className="w-full max-w-2xl">
          {/* Header */}
          <div className="text-center mb-8 space-y-2">
            <span className="inline-block text-xs font-semibold text-blue-600 bg-blue-50
                             border border-blue-200 rounded-full px-3 py-1 uppercase tracking-wider">
              For Teachers
            </span>
            <h1 className="text-3xl sm:text-4xl font-black text-gray-900 leading-tight">
              Before You Apply
            </h1>
            <p className="text-base text-gray-500">Please read before continuing.</p>
          </div>

          {/* Card */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-md overflow-hidden">
            <div className="px-8 sm:px-10 pt-8 pb-6 space-y-5">
              {[
                'Age 19–59.',
                'Citizens of USA, UK, Canada, Ireland, Australia, New Zealand, South Africa, or Korea (F-visa).',
                'Bachelor\'s degree or higher, no criminal record, and in good physical and mental health.',
                'Prepare your original resume as a Word or PDF file (no screenshots).',
                'Ensure employment dates and locations are accurate and up to date.',
                'Attach a clear, recent photo (no hats, sunglasses or photoshop) and a short self-introduction video.',
              ].map((item, i) => (
                <div key={i} className="flex items-start gap-4 text-[15px] sm:text-base text-gray-700 leading-relaxed">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-blue-50 text-blue-600 text-xs font-bold flex items-center justify-center mt-0.5 border border-blue-200">
                    {i + 1}
                  </span>
                  <span>{item}</span>
                </div>
              ))}
            </div>

            <div className="px-8 sm:px-10 pb-8 pt-5 border-t border-gray-100 space-y-4">
              <p className="text-xs text-gray-400 text-center">
                By continuing you agree to our{' '}
                <a href="/terms" className="underline hover:text-gray-600" target="_blank" rel="noopener noreferrer">Terms of Use</a>.
              </p>
              <button
                type="button"
                onClick={() => setPhase('captcha')}
                className="btn-shimmer w-full py-4 bg-blue-500 hover:bg-blue-600 active:bg-blue-700
                           text-white text-base font-semibold rounded-xl transition-colors"
              >
                I Agree &amp; Continue →
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── Captcha 팝업 ─────────────────────────────────────────────────────────
  if (phase === 'captcha') {
    return (
      <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 p-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
          <div className="px-6 pt-6 pb-2">
            <h2 className="text-lg font-bold text-gray-900 mb-1">Security Verification / 보안 확인</h2>
            <p className="text-sm text-gray-500 mb-1">Complete the puzzle to continue with your application.</p>
            <p className="text-xs text-gray-400 mb-4">지원서 제출을 계속하려면 아래 퍼즐을 완료해 주세요.</p>
            <PuzzleCaptcha
              onVerified={handleCaptchaVerified}
              onError={(err) => alert(`CAPTCHA Error: ${err}`)}
            />
          </div>
        </div>
      </div>
    )
  }

  // ── Form ────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-16">


      <div className="space-y-2">
        <span className="inline-block text-xs font-semibold text-blue-600 bg-blue-50
                         border border-blue-200 rounded-full px-3 py-1 uppercase tracking-wider">
          For Teachers
        </span>
        <h1 className="text-3xl font-black text-gray-900">Application for Teaching Positions in Korea</h1>
        <p className="text-gray-500 text-sm leading-relaxed">
          A national criminal background check (issued within 4 months + apostille) is required.<br />
          US, UK, CA, IE, AU, NZ, KR citizens and approved F-visa holders with a BA/BS or higher
          from one of the 7 countries. ZA eligible only if residing in Korea.
        </p>
      </div>

      <StepIndicator step={step} />

      <div className="space-y-6">

        {/* ================================================================ */}
        {/*  STEP 1 — Basic Info                                             */}
        {/* ================================================================ */}
        {step === 1 && (
          <>
            <section className="card space-y-4">
              <Sec title="How did you know about BRIDGE?" />
              <Dropdown
                value={form.how_to}
                onChange={(v) => setForm((p) => ({ ...p, how_to: v }))}
                options={HOW_TO}
              />
            </section>

            <section className="card space-y-5">
              <Sec title="Attach Your Files" />
              <Desc text="Please upload your file to the correct category. Please ensure you upload the original file, rather than a screenshot, Canva link, or AI-generated file." />

              {/* ── 1. Photo ── */}
              <QueueZone fileType="photo" icon="📷" hint="Recent Photo (PNG / JPG)" accept="image/jpeg,image/png,image/webp" queuedFiles={queuedFiles} setQueuedFiles={setQueuedFiles} maxFiles={MAX_FILES} />

              {/* ── 2. CV / Resume (required) ── */}
              <QueueZone fileType="cv" icon="📄" hint="CV / Resume (PDF or Word) *" accept="application/pdf,.pdf,application/msword,.doc,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx" queuedFiles={queuedFiles} setQueuedFiles={setQueuedFiles} maxFiles={MAX_FILES} />

              {/* ── 3. Cover Letter ── */}
              <QueueZone fileType="cover_letter" icon="📝" hint="Cover Letter (PDF or Word)" accept="application/pdf,.pdf,application/msword,.doc,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx" queuedFiles={queuedFiles} setQueuedFiles={setQueuedFiles} maxFiles={MAX_FILES} />

              {/* ── 4. Other Docs ── */}
              <QueueZone fileType="certificate" icon="📎" hint="Other Docs (PDF or Image)" accept="application/pdf,.pdf,image/jpeg,.jpg,.jpeg,image/png,.png" queuedFiles={queuedFiles} setQueuedFiles={setQueuedFiles} maxFiles={MAX_FILES} />

              {/* ── 업로드 대기 파일 목록 ── */}
              {queuedFiles.length > 0 && (
                <div className="space-y-1.5 pt-2 border-t border-gray-100">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Files ready to upload</p>
                  {queuedFiles.map((q, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm px-3 py-2 bg-green-50 border border-green-100 rounded-lg">
                      <span className="text-gray-400 text-xs w-20 shrink-0">
                        {q.type === 'cover_letter' ? 'Cover Letter' : q.type === 'cv' ? 'CV' : q.type === 'photo' ? 'Photo' : 'Certificate'}
                      </span>
                      <span className="text-gray-700 truncate flex-1">{q.file.name}</span>
                      <span className="text-gray-400 text-xs">{(q.file.size / 1024).toFixed(0)} KB</span>
                      <button type="button"
                        className="text-gray-300 hover:text-red-400 text-xs ml-1"
                        onClick={() => setQueuedFiles((prev) => prev.filter((_, j) => j !== i))}>
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="card space-y-4">
              <Sec title="Basic Information" />
              {/* Honeypot 필드 — 봇만 채움. 사용자 눈에 보이지 않음 */}
              <input
                type="text"
                name="_url"
                tabIndex={-1}
                autoComplete="off"
                aria-hidden="true"
                style={{ position: 'absolute', left: '-10000px', width: '1px', height: '1px', opacity: 0 }}
                value={(form as Record<string, unknown>)._url as string || ''}
                onChange={set('_url' as keyof typeof form)}
              />
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <Label required>Full Name</Label>
                  <Desc text="Exactly as on your passport. Add nickname after if applicable. (e.g. Catherine Mill ; Cathy)" />
                  <input className="input" placeholder="e.g. John Smith"
                    value={form.full_name} onChange={set('full_name')} />
                </div>
                <div>
                  <Label required>Email Address</Label>
                  <Desc text="Double-check for typos." />
                  <input type="email" className="input" placeholder="you@example.com"
                    value={form.email} onChange={set('email')} />
                </div>
              </div>
            </section>

            <section className="card space-y-5">
              <Sec title="Personal Information" />
              <div>
                <Label required>Nationality</Label>
                <div className="mb-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600 font-medium">
                  If your nationality is not listed below, please do not apply.
                </div>
                <RadioList
                  value={form.nationality}
                  onChange={(v) => setForm((p) => ({ ...p, nationality: v }))}
                  options={NATIONALITIES}
                />
              </div>
              <div>
                <Label required>Family Ancestry Background</Label>
                <Desc text='For reference only — will not affect your application. Select "Prefer not to disclose" if preferred.' />
                <Dropdown
                  value={form.ancestry}
                  onChange={(v) => setForm((p) => ({ ...p, ancestry: v }))}
                  options={ANCESTRY}
                />
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <Label required>Date of Birth</Label>
                  <input
                    type="date"
                    lang="en"
                    className="input cursor-pointer"
                    style={{ width: '220px', maxWidth: '100%' }}
                    value={form.dob}
                    min={`${new Date().getFullYear() - 80}-01-01`}
                    max={`${new Date().getFullYear() - 18}-12-31`}
                    onChange={(e) => setForm((p) => ({ ...p, dob: e.target.value }))}
                    placeholder="YYYY-MM-DD"
                  />
                </div>
                <div>
                  <Label required>Current Location</Label>
                  <Desc text="Country if abroad, or city/district if in Korea. (e.g. Seoul/Gangnam)" />
                  <input className="input" placeholder="e.g. Seoul/Gangnam or USA"
                    value={form.current_location} onChange={set('current_location')} />
                </div>
              </div>
              <div>
                <Label required>Gender</Label>
                <SingleTog
                  value={form.gender}
                  onChange={(v) => setForm((p) => ({ ...p, gender: v }))}
                  options={['Male', 'Female', 'Other', 'Prefer not to respond']}
                />
              </div>
            </section>

            <section className="card space-y-4">
              <Sec title="Education & Qualifications" />
              <div>
                <Label required>Educational Background</Label>
                <Desc text="Do you hold a Bachelor's degree or higher from a government-approved institution in one of the eligible countries?" />
                <Dropdown value={form.education} onChange={(v) => setForm((p) => ({ ...p, education: v }))} options={EDUCATION} />
              </div>
              <div>
                <Label required>Major</Label>
                <input className="input" placeholder="e.g. English Literature, Education"
                  value={form.major} onChange={set('major')} />
              </div>
              <div>
                <Label required>Certification</Label>
                <Desc text="Completed teaching license or certification" />
                <Dropdown value={form.certification} onChange={(v) => setForm((p) => ({ ...p, certification: v }))} options={CERTIFICATION} />
              </div>
            </section>

            <section className="card space-y-4">
              <Sec title="Visa & Documents" />
              <div>
                <Label required>E Visa</Label>
                <Desc text="I've previously applied for an E-2, E-1 visa etc." />
                <SingleTog value={form.e_visa} onChange={(v) => setForm((p) => ({ ...p, e_visa: v }))} options={E_VISA} />
              </div>
              <div>
                <Label>ARC Holders</Label>
                <Desc text="E or F visa holders: include type and expiry. (e.g. E2 25/12/06)" />
                <input className="input" placeholder="e.g. E2 25/12/06" value={form.arc_holders} onChange={set('arc_holders')} />
              </div>
              <div>
                <Label required>Passport</Label>
                <Desc text="Is your passport valid for less than 2 years?" />
                <SingleTog value={form.passport} onChange={(v) => setForm((p) => ({ ...p, passport: v }))} options={PASSPORT} />
              </div>
              <div>
                <Label required>Criminal Record</Label>
                <Desc text="Only from designated sources (FBI, RCMP, etc.) with the eligible-country stamp." />
                <SingleTog value={form.criminal_record} onChange={(v) => setForm((p) => ({ ...p, criminal_record: v }))} options={CRIMINAL_RECORD} />
              </div>
              <div>
                <Label required>Document Status</Label>
                <Desc text="Current CBC/CRC preparation status." />
                <Dropdown value={form.doc_status} onChange={(v) => setForm((p) => ({ ...p, doc_status: v }))} options={DOC_STATUS} />
              </div>
            </section>
          </>
        )}

        {/* ================================================================ */}
        {/*  STEP 2 — Preferences                                            */}
        {/* ================================================================ */}
        {step === 2 && (
          <>
            <section className="card !border-blue-100 bg-blue-50/30">
              <p className="text-xs text-blue-700 leading-relaxed">
                You may freely list your desired conditions, but if you lack experience or teaching qualifications,
                you may struggle to find a position that meets your preferences.
              </p>
            </section>

            <section className="card space-y-5">
              <Sec title="Work Preferences" />
              <div>
                <Label required>Start Date</Label>
                <Desc text="Earliest date you can fully start. If traveling, use your return date." />
                <input
                  type="date"
                  lang="en"
                  className="input cursor-pointer"
                  style={{ width: '220px', maxWidth: '100%' }}
                  value={form.start_date}
                  min={new Date().toISOString().slice(0, 10)}
                  max={`${new Date().getFullYear() + 2}-12-31`}
                  onChange={(e) => setForm((p) => ({ ...p, start_date: e.target.value }))}
                  placeholder="YYYY-MM-DD"
                />
              </div>
              <div>
                <Label required>Preferred Age Group</Label>
                <Desc text="Older students often mean later hours. Select all you'd consider." />
                <CheckList value={form.target_age as string[]} onChange={(arr) => setForm((p) => ({ ...p, target_age: arr }))} options={TARGET_AGE} />
              </div>
              <div>
                <Label required>Area Preferences</Label>
                <Desc text="Select all locations you'd consider." />
                <CheckList value={form.area_prefs as string[]} onChange={(arr) => setForm((p) => ({ ...p, area_prefs: arr }))} options={AREA_PREFS} />
              </div>
              <div>
                <Label>Job Preferences / Notes</Label>
                <Desc text="School type, schedule, or any special requests. Note if under 1 year." />
                <textarea className="textarea h-24" placeholder="Type of school, schedule preference, special notes..."
                  value={form.job_prefs} onChange={set('job_prefs')} />
              </div>
            </section>

            <section className="card space-y-4">
              <Sec title="Experience & Employment" />
              <div>
                <Label required>Teaching Experience in Korea</Label>
                <Desc text="Count only experience in Korea." />
                <select className="input" value={form.experience} onChange={set('experience')}>
                  <option value="">Select...</option>
                  {EXPERIENCE.map((e) => <option key={e}>{e}</option>)}
                </select>
              </div>
              <div>
                <Label required>Employment</Label>
                <Desc text="If working in Korea, does your current employer know you're looking?" />
                <Dropdown value={form.employment} onChange={(v) => setForm((p) => ({ ...p, employment: v }))} options={EMPLOYMENT} />
              </div>
              <div>
                <Label>Reference</Label>
                <Desc text="Full-time Korea experience only. Include: school name, location, contact name, position, phone, email. Skip if already in your resume." />
                <textarea className="textarea h-24"
                  placeholder="School name, location, contact person's name, position, phone, email..."
                  value={form.reference} onChange={set('reference')} />
              </div>
            </section>

            <section className="card space-y-4">
              <Sec title="Salary" />
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <Label required>Current Salary</Label>
                  <Desc text="Base salary only, no allowances. Enter 0 if no Korean income." />
                  <input className="input" placeholder="e.g. 2.3 KRW or 0"
                    value={form.current_salary} onChange={set('current_salary')} />
                </div>
                <div>
                  <Label required>Desired Salary</Label>
                  <Desc text="Base salary, no housing. (e.g. 2.4 KRW — 3 years experience)" />
                  <input className="input" placeholder="e.g. 2.4 KRW — 3 years experience"
                    value={form.desired_salary} onChange={set('desired_salary')} />
                </div>
              </div>
            </section>

            <section className="card space-y-5">
              <Sec title="Personal Situation" />
              <div>
                <Label required>Marital Status</Label>
                <Dropdown value={form.marital_status} onChange={(v) => setForm((p) => ({ ...p, marital_status: v }))} options={MARITAL} />
              </div>
              <div>
                <Label required>Housing</Label>
                <Desc text="Make sure you understand housing costs in Korea before selecting." />
                <SingleTog value={form.housing} onChange={(v) => setForm((p) => ({ ...p, housing: v }))} options={HOUSING} />
              </div>
              <div>
                <Label required>Dependents & Pets</Label>
                <Desc text="Children under 6 require reliable childcare to maintain consistent attendance." />
                <CheckList value={form.dependents_pets as string[]} onChange={(arr) => setForm((p) => ({ ...p, dependents_pets: arr }))} options={DEPENDENTS_PETS} />
              </div>
              <div>
                <Label required>Personal Considerations</Label>
                <Desc text="Anything employers should know within Korean cultural context." />
                <SingleTog value={form.personal_considerations} onChange={(v) => setForm((p) => ({ ...p, personal_considerations: v }))} options={PERSONAL} />
              </div>
              <div>
                <Label required>Religion</Label>
                <Desc text="Note if religion affects your schedule or work." />
                <Dropdown value={form.religion} onChange={(v) => setForm((p) => ({ ...p, religion: v }))} options={RELIGION} />
              </div>
            </section>
          </>
        )}

        {/* ================================================================ */}
        {/*  STEP 3 — Contact & Agreement                                    */}
        {/* ================================================================ */}
        {step === 3 && (
          <>
            <section className="card space-y-3 !border-blue-100 bg-blue-50/30">
              <div className="text-xs text-gray-600 space-y-3 max-h-48 overflow-y-auto leading-relaxed">
                <p className="font-semibold text-gray-800">Consent to Data Collection and Use for Recruitment Purposes</p>
                <p>By submitting your application, you hereby consent to the collection, processing, and use of your personal data as outlined in our{' '}
                  <a href="/privacy" className="underline text-blue-700 hover:text-blue-900" target="_blank" rel="noopener noreferrer">Privacy Policy</a>.
                  This information will be utilized solely for recruitment purposes and, when necessary, shared with prospective employers relevant to your application.</p>
                <p className="font-semibold text-gray-800">Data Retention</p>
                <p>Your personal data will be retained for a minimum of three (3) years following the conclusion of your recruitment process. Retention may extend beyond this period where required by Korean immigration, visa, or employment law. Deletion requests may be declined where retention is legally required.</p>
                <p className="font-semibold text-gray-800">Geographic Service Availability</p>
                <p>This service is available to applicants currently residing in: the United States, United Kingdom, Canada, Australia, Ireland, South Africa, or South Korea. By submitting, you confirm you are currently residing in one of these countries. Due to GDPR compliance requirements, we are unable to process applications from individuals residing in EU/EEA member states (Ireland excepted).</p>
                <p className="font-semibold text-gray-800">Agreement to Terms of Service</p>
                <p>You agree to abide by the terms and conditions established by the BRIDGE team. Should you choose to withdraw, email correspondence and associated records will be securely retained for a minimum period of five years.</p>
                <p className="font-semibold text-gray-800">Responsibility for Accurate Information</p>
                <p>By submitting this application, you confirm that all information provided is accurate and truthful. If any information is found to be false, you may be held legally responsible for any resulting harm or damages.</p>
                <p className="font-semibold text-gray-800">Right to Refusal</p>
                <p>While you retain the right to withhold consent, this may affect our ability to fully assist you in your job search.</p>
              </div>
            </section>

            <section className="card space-y-4 !border-amber-200 bg-amber-50/50">
              <Sec title="Sensitive Information" />
              <p className="text-xs text-amber-700 -mt-2 mb-1">Please check the boxes below if you have a health condition that may affect work performance, or that an employer should be aware of.</p>
              <div>
                <Label required>Health Information</Label>
                <Desc text="Any condition the school should know about for safe teaching? (e.g. diabetes, vision)" />
                <SingleTog value={form.health_info} onChange={(v) => setForm((p) => ({ ...p, health_info: v }))} options={HEALTH} />
              </div>
              <div>
                <Label required>Criminal Record Check</Label>
                <Desc text="Home country or Korea. Used for visa eligibility only." />
                <SingleTog value={form.criminal_record_check} onChange={(v) => setForm((p) => ({ ...p, criminal_record_check: v }))} options={CRC} />
              </div>
            </section>

            <section className="card space-y-4">
              <Sec title="Contact Information" />
              <div>
                <Label required>Interview Time</Label>
                <Desc text="Google Meet, 5–10 min. List specific times in KST (09:30–18:30). Double-check timezone if abroad." />
                <textarea className="textarea h-20"
                  placeholder="e.g. Mon 10:00 KST, Wed 14:00 KST, Fri 11:00 KST"
                  value={form.interview_time} onChange={set('interview_time')} />
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <Label>KakaoTalk</Label>
                  <Desc text="KakaoTalk ID only (not an email). We only contact when necessary." />
                  <input className="input" placeholder="KakaoTalk ID" value={form.kakaotalk} onChange={set('kakaotalk')} />
                </div>
                <div>
                  <Label required>Mobile Phone</Label>
                  <Desc text="Korean number if in Korea. We won't call." />
                  <input className="input" placeholder="+82 10-xxxx-xxxx or +1 555-000-0000"
                    value={form.mobile_phone} onChange={set('mobile_phone')} />
                </div>
              </div>
            </section>

            <section className="card space-y-4">
              <Sec title="Agreement & Declaration" />
              <div>
                <Label required>Agreement</Label>
                <Desc text='I agree that submission of any false information will render the process ineligible.' />
                <SingleTog value={form.agreement} onChange={(v) => setForm((p) => ({ ...p, agreement: v }))} options={['I Agree', 'I Do Not Agree']} />
              </div>
              <div>
                <Label required>Facts</Label>
                <Desc text="My response is based on facts." />
                <SingleTog value={form.facts} onChange={(v) => setForm((p) => ({ ...p, facts: v }))} options={['Yes', 'Not true']} />
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
              className="btn-shimmer flex-1 text-base py-3.5 px-8 rounded-lg font-bold text-white disabled:opacity-50"
              style={{ background: '#1a1a2e', fontSize: 16 }}>
              <span>{status === 'submitting' ? 'Submitting...' : 'Submit Application'}</span>
            </button>
          )}
        </div>

        {step === 3 && (
          <div className="trust-badge">
            <span>All personal data is AES-256 encrypted and securely protected.</span>
            <span className="text-gray-300">&middot;</span>
            <span>Never sold or shared publicly.</span>
          </div>
        )}

      </div>
    </div>
  )
}
