'use client'

/* ── PII 마스킹 유틸 ── */
export function maskEmail(email: string | null | undefined): string {
  if (!email || email === 'None') return '—'
  const at = email.indexOf('@')
  if (at <= 1) return '****@****'
  return email[0] + '****' + email.slice(at)
}

export function maskPhone(phone: string | null | undefined): string {
  if (!phone || phone === 'None') return '—'
  const digits = phone.replace(/\D/g, '')
  if (digits.length < 8) return '****'
  return digits.slice(0, 3) + '-****-' + digits.slice(-4)
}

export function maskName(name: string | null | undefined): string {
  if (!name || name === 'None') return '—'
  if (name.length <= 1) return '***'
  return name.slice(0, 2) + '***'
}

export function v(s: string | null | undefined): string {
  if (!s || s.trim() === '' || s.trim() === 'None') return ''
  return s.trim()
}

export interface EmployerApp {
  id: string
  type: 'employer'
  name: string
  email: string
  status: string
  created_at: string
  school_name?: string
  contact_name?: string | null
  job_code?: string | null
  source_file?: string | null
  phone?: string | null
  location?: string | null
  start_date?: string | null
  vacancies?: string | null
  teaching_age?: string | null
  schedule?: string | null
  working_hours?: string | null
  salary_raw?: string | null
  housing_type?: string | null
  housing_detail?: string | null
  travel_support?: string | null
  benefits?: string | null
  vacation?: string | null
  sick_leave?: string | null
  meal?: string | null
  memo?: string | null
  notes?: string | null
  assigned_to?: string | null
}

/* ── Job 번호 표시 ── */
function jobNo(app: EmployerApp): string {
  if (v(app.job_code)) return app.job_code as string
  const src = app.source_file || ''
  if (src.startsWith('BRIDGE_clients')) return `F-${app.id}`
  if (src === 'memo_extract') return `M-${app.id}`
  return app.id
}

function isNewJobCode(code: string): boolean {
  return /^N\d+/.test(code)
}

/* ── 메모 추출 (괄호 내용) ── */
function extractMemo(app: EmployerApp): string {
  const text = app.memo || app.notes || ''
  const matches = text.match(/\(([^)]+)\)/g)
  if (matches) return matches.map(m => m.slice(1, -1)).join(' / ')
  if (v(app.memo)) return app.memo as string
  return ''
}

/* ── 상태 뱃지 색상 ── */
const statusColors: Record<string, string> = {
  new: 'bg-sky-100 text-sky-700',
  contacted: 'bg-yellow-100 text-yellow-700',
  interviewing: 'bg-blue-100 text-blue-700',
  hired: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  hold: 'bg-gray-100 text-gray-500',
  blacklist: 'bg-red-200 text-red-800',
}

const statusLabel: Record<string, string> = {
  new: 'New', contacted: 'Contacted', interviewing: 'Interviewing',
  hired: 'Hired', rejected: 'Rejected', hold: 'Hold', blacklist: 'Blacklist',
}

/* ── DocBlock 컴포넌트 ── */
interface DocBlockProps {
  employer: EmployerApp
  isNew: boolean
  isConfirmed: boolean
  isBlacklist: boolean
  showPII: boolean
  province: string
  city: string
  onConfirm: (id: string) => void
  onStatusChange: (id: string, status: string) => void
  showDivider: boolean
}

export default function DocBlock({
  employer, isNew, isConfirmed, isBlacklist, showPII,
  province, city, onConfirm, onStatusChange, showDivider,
}: DocBlockProps) {
  const no = jobNo(employer)
  const isNewCode = isNewJobCode(no)
  const memo = extractMemo(employer)
  const shouldBlink = isNew && !isConfirmed

  return (
    <>
      <div
        className={`relative bg-white rounded-2xl border max-w-[740px] mx-auto overflow-hidden shadow-[0_2px_16px_rgba(0,0,0,0.06)] ${
          isBlacklist ? 'border-red-300' : 'border-gray-200/80'
        } ${shouldBlink ? 'employer-blink' : ''}`}
      >
        {/* 블랙리스트 오버레이 */}
        {isBlacklist && (
          <div className="absolute inset-0 bg-[rgba(220,38,38,0.06)] pointer-events-none z-10 rounded-2xl" />
        )}

        {/* 헤더 */}
        <div className="px-6 pt-5 pb-3 border-b border-gray-100 flex items-start justify-between">
          <div className="flex items-center gap-3">
            {/* Job 번호 뱃지 */}
            <code
              className={`px-2.5 py-1 text-[13px] font-bold rounded border ${
                isNewCode
                  ? 'bg-blue-600 text-white border-blue-700'
                  : 'bg-[#1d1d1f] text-white border-gray-700'
              }`}
              style={{ fontFamily: 'Consolas, monospace' }}
            >
              {no}
            </code>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
              statusColors[employer.status] || 'bg-gray-100 text-gray-600'
            }`}>
              {statusLabel[employer.status] || employer.status}
            </span>
            {isBlacklist && (
              <span className="px-2 py-0.5 bg-red-100 text-red-700 text-[10px] font-bold rounded border border-red-200">BLACKLIST</span>
            )}
          </div>

          {/* NEW 확인 버튼 */}
          {isNew && !isConfirmed && (
            <button
              type="button"
              onClick={() => onConfirm(employer.id)}
              className="px-3 py-1.5 bg-red-500 text-white text-[12px] font-bold rounded-lg hover:bg-red-600 transition-colors employer-blink"
            >
              &#9733; NEW — 확인
            </button>
          )}
        </div>

        {/* 본문 */}
        <div className="px-6 py-4 space-y-3 relative z-20">
          {/* 위치 정보 */}
          <div className="grid grid-cols-2 gap-x-8 gap-y-2">
            <Field label="지역" value={province} />
            <Field label="도시" value={city} />
            <Field label="Teaching Age" value={v(employer.teaching_age)} />
            <Field label="시작일" value={v(employer.start_date)} />
            <Field label="근무시간" value={v(employer.working_hours)} />
            <Field label="급여" value={v(employer.salary_raw)} />
            <Field label="숙소" value={[v(employer.housing_type), v(employer.housing_detail)].filter(Boolean).join(' — ')} />
            <Field label="휴가" value={v(employer.vacation)} />
            <Field label="복리후생" value={v(employer.benefits)} />
            <Field label="식비" value={v(employer.meal)} />
          </div>

          {/* 연락처 (PII) */}
          <div className="mt-3 pt-3 border-t border-gray-100">
            <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Contact {showPII ? '(OPEN)' : '(MASKED)'}
            </div>
            <div className="grid grid-cols-2 gap-x-8 gap-y-1">
              <Field label="업체명" value={showPII ? v(employer.school_name) || v(employer.name) : maskName(employer.school_name || employer.name)} />
              <Field label="담당자" value={showPII ? v(employer.contact_name) || v(employer.name) : maskName(employer.contact_name || employer.name)} />
              <Field label="이메일" value={showPII ? v(employer.email) : maskEmail(employer.email)} />
              <Field label="전화" value={showPII ? v(employer.phone) : maskPhone(employer.phone)} />
            </div>
          </div>

          {/* 메모 (노란 박스) */}
          {memo && (
            <div className="mt-3 rounded-lg border px-4 py-3" style={{ background: '#fffde7', borderColor: '#f0e68c' }}>
              <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">MEMO</span>
              <p className="text-[13px] text-gray-700 mt-1 whitespace-pre-wrap leading-relaxed">{memo}</p>
            </div>
          )}

          {/* 상태 변경 */}
          <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100">
            <span className="text-[11px] text-gray-400">상태:</span>
            <select
              className={`text-[11px] px-2.5 py-1 rounded-full font-semibold border-0 cursor-pointer ${
                statusColors[employer.status] || 'bg-gray-100 text-gray-600'
              }`}
              value={employer.status}
              onChange={e => onStatusChange(employer.id, e.target.value)}
            >
              {Object.entries(statusLabel).map(([k, l]) => (
                <option key={k} value={k}>{l}</option>
              ))}
            </select>
            <span className="text-[11px] text-gray-300 ml-auto">
              {employer.created_at?.slice(0, 10)}
            </span>
          </div>
        </div>
      </div>

      {/* 페이지 구분선 (2개마다) */}
      {showDivider && (
        <div className="max-w-[740px] mx-auto my-8 border-t-2 border-dashed border-gray-200 relative">
          <span className="absolute left-1/2 -translate-x-1/2 -top-3 bg-[#f5f5f7] px-3 text-[11px] text-gray-300">page break</span>
        </div>
      )}
    </>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  if (!value) return null
  return (
    <div className="text-[13px]">
      <span className="text-[#86868b] font-medium text-[12px]">{label}</span>
      <p className="text-[#1d1d1f] mt-0.5">{value}</p>
    </div>
  )
}
