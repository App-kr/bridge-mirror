'use client'

/**
 * /admin/jobs — 채용공고 워드형 게시판
 * BRJ ID 시스템, A4 문서 뷰, PII 토글, 상태 관리
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL
const PER_PAGE = 20

/* ── Types ── */
interface AdminJob {
  id: number
  brj_id: string | null
  legacy_id: string | null
  job_code: string
  region: string | null
  region_name: string | null
  city: string | null
  district: string | null
  location: string | null
  teaching_age: string | null
  class_size: string | null
  working_hours: string | null
  daily_hours: number | null
  start_date: string | null
  salary_raw: string | null
  salary_krw: number | null
  salary_negotiable: number
  salary_min: number | null
  salary_max: number | null
  vacation: string | null
  vacation_days: number | null
  housing: string | null
  housing_type: string | null
  housing_detail: string | null
  benefits: string | null
  native_count: string | null
  teach_hrs_week: string | null
  teaching_hours_weekly: string | null
  is_hot: number
  is_part_time: number
  status: string
  enc_employer_name: string | null
  enc_contact_name: string | null
  enc_contact_phone: string | null
  enc_contact_email: string | null
  enc_contact_kakao: string | null
  employer_display_name: string | null
  visa_sponsorship: number
  f_visa_welcome: number
  kyopo_welcome: number
  degree_requirement: string | null
  korea_resident_only: number
  raw_text: string | null
  raw_source: string | null
  parse_confidence: number | null
  parse_warnings: string | null
  internal_notes: string | null
  recruiter_memo: string | null
  created_at: string | null
  is_deleted: number
}

/* ── Constants ── */
const REGION_OPTIONS = [
  { label: '전체', value: '' },
  { label: '서울', value: 'SE' }, { label: '경기', value: 'GG' },
  { label: '부산', value: 'BS' }, { label: '인천', value: 'IC' },
  { label: '대구', value: 'DG' }, { label: '광주', value: 'GJ' },
  { label: '대전', value: 'DJ' }, { label: '울산', value: 'US' },
  { label: '세종', value: 'SJ' }, { label: '강원', value: 'GW' },
  { label: '충북', value: 'CB' }, { label: '충남', value: 'CN' },
  { label: '전북', value: 'JB' }, { label: '전남', value: 'JN' },
  { label: '경북', value: 'KB' }, { label: '경남', value: 'KN' },
  { label: '제주', value: 'JJ' },
]

const STATUS_OPTIONS = [
  { label: 'All', value: '' },
  { label: 'Open', value: 'open' },
  { label: 'Closed', value: 'closed' },
  { label: 'Filled', value: 'filled' },
  { label: 'Hold', value: 'hold' },
]

/* ── Helpers ── */
function fmtSalary(krw: number | null | undefined): string {
  if (!krw) return '—'
  if (krw >= 1_000_000) return `${(krw / 1_000_000).toFixed(1)}M KRW`
  if (krw >= 10_000) return `${Math.round(krw / 10_000)}만원`
  return `${krw.toLocaleString()} KRW`
}

function fmtDate(d: string | null | undefined): string {
  if (!d) return '—'
  return d.slice(0, 10)
}

function maskPII(val: string | null | undefined, show: boolean): string {
  if (!val || val === 'None' || val === 'N/A') return '—'
  if (show) return val
  if (val.length <= 2) return '●●●●'
  return val.slice(0, 2) + '●'.repeat(Math.min(val.length - 2, 8))
}

function v(s: string | null | undefined): string {
  if (!s || s === 'None' || s === 'N/A') return '—'
  return s
}

/* ── StatusBadge ── */
function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    open: 'bg-emerald-100 text-emerald-700',
    closed: 'bg-gray-200 text-gray-500',
    filled: 'bg-blue-100 text-blue-700',
    hold: 'bg-amber-100 text-amber-700',
    cancelled: 'bg-red-100 text-red-600',
    new: 'bg-purple-100 text-purple-700',
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold tracking-wide ${colors[status] || 'bg-gray-100 text-gray-500'}`}>
      {status.toUpperCase()}
    </span>
  )
}

/* ── JobIDBadge ── */
function JobIDBadge({ brjId, legacyId }: { brjId: string | null; legacyId?: string | null }) {
  return (
    <div className="flex items-center gap-2">
      <code className="px-2 py-0.5 bg-[#f0f1f3] text-[#1d1d1f] text-[13px] font-bold rounded border border-gray-200" style={{ fontFamily: 'Consolas, monospace' }}>
        {brjId || '—'}
      </code>
      {legacyId && <span className="text-[11px] text-gray-400">{legacyId}</span>}
    </div>
  )
}

/* ── PIIMask ── */
function PIIMask({ value, show }: { value: string | null | undefined; show: boolean }) {
  const masked = maskPII(value, show)
  const isHidden = !show && value && value !== 'None' && value !== 'N/A'
  return (
    <span className={isHidden ? 'text-gray-400' : 'text-red-700'} style={isHidden ? { fontFamily: 'monospace' } : undefined}>
      {masked}{isHidden && <span className="ml-1 text-[10px] text-gray-300">&#128274;</span>}
    </span>
  )
}

/* ── ConfidenceMeter ── */
function ConfidenceMeter({ value }: { value: number | null | undefined }) {
  const pct = Math.round((value ?? 0) * 100)
  const color = pct >= 75 ? 'bg-emerald-400' : pct >= 50 ? 'bg-amber-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-14 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] text-gray-400">{pct}%</span>
    </div>
  )
}

/* ── DocRow (document table row) ── */
function DocRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <tr className="border-b border-gray-100 last:border-0">
      <td className="py-2 px-3 text-[11px] font-semibold text-gray-500 bg-[#f5f5f7] w-[130px] align-top whitespace-nowrap">{label}</td>
      <td className="py-2 px-3 text-[13px] text-[#1d1d1f]">{children}</td>
    </tr>
  )
}

/* ── JobDocumentView (A4-like expanded view) ── */
function JobDocumentView({ job, showPII, onAction }: {
  job: AdminJob
  showPII: boolean
  onAction: (action: string) => void
}) {
  return (
    <div className="bg-white rounded-2xl shadow-[0_2px_20px_rgba(0,0,0,0.08)] border border-gray-200/80 max-w-[740px] mx-auto overflow-hidden">
      {/* Document Header */}
      <div className="px-7 pt-5 pb-4 border-b border-gray-100">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[17px] font-bold text-[#0071E3] tracking-tight">BRIDGE</span>
              <span className="text-[13px] text-gray-400 font-light">Job Description</span>
            </div>
            <JobIDBadge brjId={job.brj_id} legacyId={job.legacy_id || job.job_code} />
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={job.status || 'open'} />
            {!!job.is_hot && <span className="text-[11px] bg-red-50 text-red-600 px-2 py-0.5 rounded-full font-semibold border border-red-100">HOT</span>}
            <button type="button" onClick={() => onAction('close')} className="ml-1 w-7 h-7 flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors text-sm">&#10005;</button>
          </div>
        </div>
      </div>

      {/* Document Body */}
      <div className="px-7 py-5 space-y-5">
        {/* Position Info */}
        <section>
          <h3 className="text-[12px] font-bold text-[#0071E3] uppercase tracking-wider pb-1 mb-2 border-b-2 border-[#0071E3]">Position Information</h3>
          <table className="w-full"><tbody>
            <DocRow label="Region">{v(job.region_name)} ({v(job.region)})</DocRow>
            <DocRow label="City / District">{`${v(job.city)} ${job.district || ''}`.trim() || '—'}</DocRow>
            <DocRow label="Teaching Level">{v(job.teaching_age)}</DocRow>
            <DocRow label="Class Size">{v(job.class_size)}</DocRow>
            <DocRow label="Start Date">{v(job.start_date)}</DocRow>
            <DocRow label="Status"><StatusBadge status={job.status || 'open'} /></DocRow>
          </tbody></table>
        </section>

        {/* Salary & Benefits */}
        <section>
          <h3 className="text-[12px] font-bold text-[#0071E3] uppercase tracking-wider pb-1 mb-2 border-b-2 border-[#0071E3]">Salary & Benefits</h3>
          <table className="w-full"><tbody>
            <DocRow label="Salary">{job.salary_krw ? fmtSalary(job.salary_krw) : v(job.salary_raw)}</DocRow>
            {job.salary_raw && job.salary_krw ? <DocRow label="Salary (Raw)">{job.salary_raw}</DocRow> : null}
            <DocRow label="Negotiable">{job.salary_negotiable ? 'Yes' : 'No'}</DocRow>
            <DocRow label="Housing">{`${job.housing_type || ''} — ${job.housing_detail || job.housing || ''}`.replace(/^[\s—]+|[\s—]+$/g, '') || '—'}</DocRow>
            <DocRow label="Vacation">{job.vacation_days ? `${job.vacation_days} days` : v(job.vacation)}</DocRow>
            <DocRow label="Benefits">{v(job.benefits)}</DocRow>
            <DocRow label="Visa Sponsorship">{job.visa_sponsorship !== 0 ? 'Yes' : 'No'}</DocRow>
            {!!job.f_visa_welcome && <DocRow label="F-Visa Welcome">Yes</DocRow>}
            {!!job.kyopo_welcome && <DocRow label="Kyopo Welcome">Yes</DocRow>}
          </tbody></table>
        </section>

        {/* Work Schedule */}
        <section>
          <h3 className="text-[12px] font-bold text-[#0071E3] uppercase tracking-wider pb-1 mb-2 border-b-2 border-[#0071E3]">Work Schedule</h3>
          <table className="w-full"><tbody>
            <DocRow label="Working Hours">{v(job.working_hours)}</DocRow>
            <DocRow label="Teaching Hrs/Wk">{v(job.teaching_hours_weekly || job.teach_hrs_week)}</DocRow>
            <DocRow label="Native Teachers">{v(job.native_count)}</DocRow>
          </tbody></table>
        </section>

        {/* Employer (PII) */}
        <section>
          <h3 className={`text-[12px] font-bold uppercase tracking-wider pb-1 mb-2 border-b-2 ${showPII ? 'text-red-600 border-red-300' : 'text-gray-500 border-gray-200'}`}>
            Employer Information {showPII ? '(CONFIDENTIAL)' : '(MASKED)'}
          </h3>
          <table className="w-full"><tbody>
            <DocRow label="Display Name">{v(job.employer_display_name)}</DocRow>
            <DocRow label="Employer"><PIIMask value={job.enc_employer_name} show={showPII} /></DocRow>
            <DocRow label="Contact Name"><PIIMask value={job.enc_contact_name} show={showPII} /></DocRow>
            <DocRow label="Phone"><PIIMask value={job.enc_contact_phone} show={showPII} /></DocRow>
            <DocRow label="Email"><PIIMask value={job.enc_contact_email} show={showPII} /></DocRow>
            <DocRow label="Kakao"><PIIMask value={job.enc_contact_kakao} show={showPII} /></DocRow>
          </tbody></table>
        </section>

        {/* Internal Notes (PII only) */}
        {showPII && (job.internal_notes || job.recruiter_memo) && (
          <section>
            <h3 className="text-[12px] font-bold text-gray-600 uppercase tracking-wider pb-1 mb-2 border-b border-gray-200">Internal Notes</h3>
            <p className="text-[13px] text-gray-500 italic whitespace-pre-wrap">{job.internal_notes || job.recruiter_memo}</p>
          </section>
        )}

        {/* Meta Footer */}
        <div className="flex items-center justify-between text-[11px] text-gray-400 pt-3 border-t border-gray-100">
          <div className="flex items-center gap-4">
            <span>Created: {fmtDate(job.created_at)}</span>
            <ConfidenceMeter value={job.parse_confidence} />
            {job.raw_source && <span>Source: {job.raw_source}</span>}
          </div>
          <span className="text-gray-300">bridgejob.co.kr</span>
        </div>
      </div>

      {/* Action Bar */}
      <div className="px-7 py-3 bg-[#f5f5f7] border-t border-gray-200 flex items-center gap-2 flex-wrap">
        <button type="button" onClick={() => onAction('toggle-status')}
          className="admin-btn admin-btn-edit">
          {(job.status || 'open') === 'open' ? 'Close' : 'Reopen'}
        </button>
        <button type="button" onClick={() => onAction('toggle-hot')}
          className={`admin-btn ${job.is_hot ? 'admin-btn-cancel' : 'admin-btn-save'}`}>
          {job.is_hot ? 'HOT OFF' : 'HOT ON'}
        </button>
        <button type="button" onClick={() => onAction('delete')}
          className="admin-btn admin-btn-delete">
          Delete
        </button>
        <div className="flex-1" />
        {job.raw_text && (
          <button type="button" onClick={() => onAction('raw-text')}
            className="admin-btn">
            Raw Text
          </button>
        )}
      </div>
    </div>
  )
}

/* ── JobRegistrationForm (modal) ── */
function JobRegistrationForm({ onSubmit, onClose }: {
  onSubmit: (data: Record<string, string | number>) => void
  onClose: () => void
}) {
  const [form, setForm] = useState<Record<string, string>>({
    city: '', district: '', teaching_age: '', class_size: '',
    working_hours: '', start_date: '', salary_raw: '', salary_krw: '',
    vacation: '', housing_type: '', housing_detail: '',
    benefits: '', native_count: '', teach_hrs_week: '',
    enc_employer_name: '', enc_contact_name: '', enc_contact_phone: '',
    enc_contact_email: '', enc_contact_kakao: '', employer_display_name: '',
    internal_notes: '', region: '',
  })

  const set = (k: string, val: string) => setForm(p => ({ ...p, [k]: val }))

  const handleSubmit = () => {
    if (!form.city && !form.region) return
    const data: Record<string, string | number> = {}
    for (const [k, val] of Object.entries(form)) {
      if (val.trim()) {
        if (k === 'salary_krw') data[k] = Number(val)
        else data[k] = val.trim()
      }
    }
    onSubmit(data)
  }

  const inputCls = 'w-full px-3 py-2 text-[13px] border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[#0071E3]/30 focus:border-[#0071E3] transition-colors'
  const labelCls = 'block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-[640px] max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 bg-white px-6 py-4 border-b border-gray-100 flex items-center justify-between z-10">
          <h2 className="text-[15px] font-bold text-[#1d1d1f]">New Job Registration</h2>
          <button type="button" onClick={onClose} className="w-7 h-7 flex items-center justify-center text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">&#10005;</button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Location */}
          <div>
            <h3 className="text-[12px] font-bold text-[#0071E3] mb-3">Location</h3>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={labelCls}>Region</label>
                <select value={form.region} onChange={e => set('region', e.target.value)} className={inputCls}>
                  <option value="">Auto-detect</option>
                  {REGION_OPTIONS.filter(r => r.value).map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>City *</label>
                <input value={form.city} onChange={e => set('city', e.target.value)} className={inputCls} placeholder="Seoul" />
              </div>
              <div>
                <label className={labelCls}>District</label>
                <input value={form.district} onChange={e => set('district', e.target.value)} className={inputCls} placeholder="Gangnam" />
              </div>
            </div>
          </div>

          {/* Position */}
          <div>
            <h3 className="text-[12px] font-bold text-[#0071E3] mb-3">Position</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Teaching Level</label>
                <input value={form.teaching_age} onChange={e => set('teaching_age', e.target.value)} className={inputCls} placeholder="Kindy - Elem" />
              </div>
              <div>
                <label className={labelCls}>Class Size</label>
                <input value={form.class_size} onChange={e => set('class_size', e.target.value)} className={inputCls} placeholder="~12" />
              </div>
              <div>
                <label className={labelCls}>Start Date</label>
                <input value={form.start_date} onChange={e => set('start_date', e.target.value)} className={inputCls} placeholder="2026-04-01" />
              </div>
              <div>
                <label className={labelCls}>Working Hours</label>
                <input value={form.working_hours} onChange={e => set('working_hours', e.target.value)} className={inputCls} placeholder="09:00~18:00" />
              </div>
            </div>
          </div>

          {/* Salary */}
          <div>
            <h3 className="text-[12px] font-bold text-[#0071E3] mb-3">Salary & Benefits</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Salary (Raw)</label>
                <input value={form.salary_raw} onChange={e => set('salary_raw', e.target.value)} className={inputCls} placeholder="2.4M KRW" />
              </div>
              <div>
                <label className={labelCls}>Salary (KRW)</label>
                <input value={form.salary_krw} onChange={e => set('salary_krw', e.target.value)} className={inputCls} placeholder="2400000" type="number" />
              </div>
              <div>
                <label className={labelCls}>Housing</label>
                <select value={form.housing_type} onChange={e => set('housing_type', e.target.value)} className={inputCls}>
                  <option value="">Select</option>
                  <option value="provided">Provided</option>
                  <option value="allowance">Allowance</option>
                  <option value="both">Both</option>
                  <option value="none">None</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Housing Detail</label>
                <input value={form.housing_detail} onChange={e => set('housing_detail', e.target.value)} className={inputCls} placeholder="Furnished studio" />
              </div>
              <div>
                <label className={labelCls}>Vacation</label>
                <input value={form.vacation} onChange={e => set('vacation', e.target.value)} className={inputCls} placeholder="10 days" />
              </div>
              <div>
                <label className={labelCls}>Benefits</label>
                <input value={form.benefits} onChange={e => set('benefits', e.target.value)} className={inputCls} placeholder="Severance, Pension" />
              </div>
            </div>
          </div>

          {/* Employer (PII) */}
          <div>
            <h3 className="text-[12px] font-bold text-red-600 mb-3">Employer (Confidential)</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Display Name</label>
                <input value={form.employer_display_name} onChange={e => set('employer_display_name', e.target.value)} className={inputCls} placeholder="Seoul English Academy" />
              </div>
              <div>
                <label className={labelCls}>Employer Name</label>
                <input value={form.enc_employer_name} onChange={e => set('enc_employer_name', e.target.value)} className={inputCls} placeholder="Actual company name" />
              </div>
              <div>
                <label className={labelCls}>Contact Name</label>
                <input value={form.enc_contact_name} onChange={e => set('enc_contact_name', e.target.value)} className={inputCls} placeholder="Contact person" />
              </div>
              <div>
                <label className={labelCls}>Phone</label>
                <input value={form.enc_contact_phone} onChange={e => set('enc_contact_phone', e.target.value)} className={inputCls} placeholder="010-0000-0000" />
              </div>
              <div>
                <label className={labelCls}>Email</label>
                <input value={form.enc_contact_email} onChange={e => set('enc_contact_email', e.target.value)} className={inputCls} placeholder="email@example.com" />
              </div>
              <div>
                <label className={labelCls}>Kakao</label>
                <input value={form.enc_contact_kakao} onChange={e => set('enc_contact_kakao', e.target.value)} className={inputCls} placeholder="Kakao ID" />
              </div>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className={labelCls}>Internal Notes</label>
            <textarea value={form.internal_notes} onChange={e => set('internal_notes', e.target.value)}
              className={`${inputCls} h-20 resize-none`} placeholder="Internal memo..." />
          </div>
        </div>

        <div className="sticky bottom-0 bg-white px-6 py-4 border-t border-gray-100 flex justify-end gap-2">
          <button type="button" onClick={onClose}
            className="admin-btn admin-btn-cancel">
            Cancel
          </button>
          <button type="button" onClick={handleSubmit}
            className="admin-btn admin-btn-save">
            Register
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── RawTextModal ── */
function RawTextModal({ job, onClose }: { job: AdminJob; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-[600px] max-h-[80vh] overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h2 className="text-[14px] font-bold text-[#1d1d1f]">Raw Text</h2>
            <span className="text-[11px] text-gray-400">{job.brj_id}</span>
          </div>
          <button type="button" onClick={onClose} className="w-7 h-7 flex items-center justify-center text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">&#10005;</button>
        </div>
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-60px)]">
          <pre className="text-[12px] text-gray-700 whitespace-pre-wrap leading-relaxed bg-[#f5f5f7] rounded-xl p-4 border border-gray-200" style={{ fontFamily: 'Consolas, monospace' }}>
            {job.raw_text || '(No raw text available)'}
          </pre>
          {job.parse_warnings && job.parse_warnings !== '[]' && (
            <div className="mt-3 text-[11px] text-amber-600 bg-amber-50 rounded-lg p-3 border border-amber-100">
              Warnings: {job.parse_warnings}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ════════════════════════════════════════════════════════════════════════════════
   MAIN PAGE
   ════════════════════════════════════════════════════════════════════════════════ */
export default function AdminJobsPage() {
  const { authed, login, signedFetch, waking } = useAdminAuth()

  const [jobs, setJobs] = useState<AdminJob[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [regionFilter, setRegionFilter] = useState('')
  const [page, setPage] = useState(1)
  const [showPII, setShowPII] = useState(false)

  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [showRegForm, setShowRegForm] = useState(false)
  const [rawTextJob, setRawTextJob] = useState<AdminJob | null>(null)

  const flash = (msg: string) => { setActionMsg(msg); setTimeout(() => setActionMsg(null), 3000) }

  /* ── Fetch ── */
  const fetchJobs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ limit: '2000', offset: '0' })
      if (statusFilter) params.set('status', statusFilter)
      if (regionFilter) params.set('region', regionFilter)
      if (search.trim()) params.set('search', search.trim())

      const res = await signedFetch(`${API}/api/admin/jobs/v2?${params}`)
      const json = await res.json()
      if (json.success && json.data) {
        setJobs(json.data.jobs || [])
        setTotal(json.data.total ?? 0)
      } else {
        setError(json.message || 'Failed to load')
      }
    } catch {
      setError('Failed to load jobs')
    } finally {
      setLoading(false)
    }
  }, [signedFetch, statusFilter, regionFilter, search])

  useEffect(() => { if (authed) fetchJobs() }, [authed, fetchJobs])
  useEffect(() => { setPage(1) }, [search, statusFilter, regionFilter])

  /* ── Pagination ── */
  const totalPages = Math.max(1, Math.ceil(jobs.length / PER_PAGE))
  const pageJobs = useMemo(() => {
    const start = (page - 1) * PER_PAGE
    return jobs.slice(start, start + PER_PAGE)
  }, [jobs, page])

  /* ── Actions ── */
  const toggleStatus = useCallback(async (job: AdminJob) => {
    const newStatus = (job.status || 'open') === 'open' ? 'closed' : 'open'
    try {
      const jobId = String(job.id)
      const res = await signedFetch(`${API}/api/admin/jobs/${jobId}/status`, {
        method: 'PUT', body: JSON.stringify({ status: newStatus }),
      })
      if (res.ok) {
        setJobs(prev => prev.map(j => j.id === job.id ? { ...j, status: newStatus } : j))
        flash(`${job.brj_id || job.job_code} → ${newStatus}`)
      }
    } catch { flash('Network error') }
  }, [signedFetch])

  const toggleHot = useCallback(async (job: AdminJob) => {
    try {
      const res = await signedFetch(`${API}/api/admin/jobs/${job.id}/hot`, { method: 'PUT' })
      if (res.ok) {
        setJobs(prev => prev.map(j => j.id === job.id ? { ...j, is_hot: j.is_hot ? 0 : 1 } : j))
        flash(`${job.brj_id || job.job_code} HOT → ${!job.is_hot ? 'ON' : 'OFF'}`)
      }
    } catch { flash('Network error') }
  }, [signedFetch])

  const deleteJob = useCallback(async (job: AdminJob) => {
    if (!job.brj_id) return
    try {
      const res = await signedFetch(`${API}/api/admin/jobs/v2/${job.brj_id}`, { method: 'DELETE' })
      if (res.ok) {
        setJobs(prev => prev.filter(j => j.id !== job.id))
        setExpandedId(null)
        flash(`${job.brj_id} deleted`)
      }
    } catch { flash('Network error') }
  }, [signedFetch])

  const createJob = useCallback(async (data: Record<string, string | number>) => {
    try {
      const res = await signedFetch(`${API}/api/admin/jobs/v2`, {
        method: 'POST', body: JSON.stringify(data),
      })
      const json = await res.json()
      if (json.success) {
        flash(`${json.data?.brj_id} created`)
        setShowRegForm(false)
        fetchJobs()
      } else {
        flash(`Error: ${json.message || json.detail}`)
      }
    } catch { flash('Registration failed') }
  }, [signedFetch, fetchJobs])

  const handleDocAction = useCallback((job: AdminJob, action: string) => {
    if (action === 'close') setExpandedId(null)
    else if (action === 'toggle-status') toggleStatus(job)
    else if (action === 'toggle-hot') toggleHot(job)
    else if (action === 'delete') { if (confirm(`Delete ${job.brj_id}?`)) deleteJob(job) }
    else if (action === 'raw-text') setRawTextJob(job)
  }, [toggleStatus, toggleHot, deleteJob])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  const openCount = jobs.filter(j => (j.status || 'open') === 'open').length
  const closedCount = jobs.filter(j => (j.status || 'open') === 'closed').length

  return (
    <div className="max-w-[1200px] mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[22px] font-bold text-[#1d1d1f] tracking-tight">Jobs Management</h1>
          <p className="text-[13px] text-gray-500 mt-0.5">
            Total {total || jobs.length} &middot; Open {openCount} &middot; Closed {closedCount}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {actionMsg && (
            <div className="text-[12px] font-medium text-green-700 bg-green-50 border border-green-200 px-3 py-1.5 rounded-lg">{actionMsg}</div>
          )}
          <button type="button" onClick={() => setShowRegForm(true)}
            className="px-4 py-2 text-[13px] rounded-xl bg-[#0071E3] text-white font-medium hover:bg-[#0066CC] transition-colors shadow-sm">
            + New Job
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-5">
        <input type="search" value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search BRJ ID, city, employer..."
          className="px-3 py-2 text-[13px] border border-gray-200 rounded-lg w-64 bg-white focus:outline-none focus:ring-2 focus:ring-[#0071E3]/20 focus:border-[#0071E3]" />

        <div className="flex gap-1">
          {STATUS_OPTIONS.map(f => (
            <button key={f.value} type="button" onClick={() => setStatusFilter(f.value)}
              className={`px-3 py-1.5 text-[12px] rounded-lg font-medium transition-colors ${
                statusFilter === f.value ? 'bg-[#1d1d1f] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}>
              {f.label}
            </button>
          ))}
        </div>

        <select value={regionFilter} onChange={e => setRegionFilter(e.target.value)}
          className="px-3 py-1.5 text-[12px] border border-gray-200 rounded-lg bg-white">
          {REGION_OPTIONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>

        <label className="flex items-center gap-1.5 text-[12px] text-gray-500 cursor-pointer select-none ml-2">
          <input type="checkbox" checked={showPII} onChange={e => setShowPII(e.target.checked)}
            className="w-3.5 h-3.5 rounded border-gray-300 text-red-600 focus:ring-red-500" />
          PII
        </label>

        <span className="text-[12px] text-gray-400 ml-auto">
          {jobs.length} results &middot; Page {page}/{totalPages}
        </span>
      </div>

      {/* Loading / Error */}
      {loading && <p className="text-center py-16 text-gray-400 animate-pulse text-[14px]">Loading...</p>}
      {error && <p className="text-center py-16 text-red-500 text-[14px]">{error}</p>}

      {/* Job List */}
      {!loading && !error && (
        <div className="space-y-3">
          {pageJobs.map(job => {
            const isExpanded = expandedId === (job.brj_id || job.job_code)
            const isOpen = (job.status || 'open') === 'open'

            return (
              <div key={job.id}>
                {/* Compact Row */}
                <div
                  className={`bg-white rounded-xl border border-gray-200/80 px-5 py-3.5 cursor-pointer hover:shadow-sm transition-all ${
                    !isOpen ? 'opacity-60' : ''
                  } ${isExpanded ? 'ring-2 ring-[#0071E3]/30 border-[#0071E3]/40' : ''}`}
                  onClick={() => setExpandedId(isExpanded ? null : (job.brj_id || job.job_code))}
                >
                  <div className="flex items-center gap-4">
                    {/* BRJ ID */}
                    <div className="min-w-[180px]">
                      <JobIDBadge brjId={job.brj_id} legacyId={job.legacy_id || job.job_code} />
                    </div>

                    {/* Location */}
                    <div className="min-w-[100px]">
                      <span className="text-[13px] text-gray-700">{v(job.city) || v(job.location)}</span>
                      {job.region_name && <span className="text-[11px] text-gray-400 ml-1">({job.region_name})</span>}
                    </div>

                    {/* Teaching */}
                    <span className="text-[12px] text-gray-500 min-w-[80px] truncate">{v(job.teaching_age)}</span>

                    {/* Salary */}
                    <span className="text-[13px] text-gray-700 min-w-[90px]">
                      {job.salary_krw ? fmtSalary(job.salary_krw) : v(job.salary_raw)}
                    </span>

                    {/* Confidence */}
                    <ConfidenceMeter value={job.parse_confidence} />

                    {/* Badges */}
                    <div className="flex items-center gap-1.5 ml-auto">
                      {!!job.is_hot && <span className="text-[10px] bg-red-50 text-red-600 px-1.5 py-0.5 rounded-full font-semibold border border-red-100">HOT</span>}
                      <StatusBadge status={job.status || 'open'} />
                    </div>

                    {/* Expand arrow */}
                    <span className={`text-gray-400 text-[12px] transition-transform ${isExpanded ? 'rotate-180' : ''}`}>&#9660;</span>
                  </div>
                </div>

                {/* Expanded Document View */}
                {isExpanded && (
                  <div className="mt-2 mb-4">
                    <JobDocumentView
                      job={job}
                      showPII={showPII}
                      onAction={(action) => handleDocAction(job, action)}
                    />
                  </div>
                )}
              </div>
            )
          })}

          {pageJobs.length === 0 && (
            <div className="text-center py-16 text-gray-400 text-[14px]">No jobs found</div>
          )}
        </div>
      )}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <nav className="flex items-center justify-center gap-1 mt-8">
          <button type="button" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
            className="px-3 py-2 text-[13px] rounded-lg disabled:opacity-30 text-gray-600 hover:bg-gray-100">
            &#8592; Prev
          </button>
          {Array.from({ length: totalPages }, (_, i) => i + 1)
            .filter(p => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
            .reduce<(number | string)[]>((acc, p, idx, arr) => {
              if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push('...')
              acc.push(p)
              return acc
            }, [])
            .map((item, idx) =>
              item === '...' ? (
                <span key={`dot-${idx}`} className="px-2 text-gray-400 text-[13px]">...</span>
              ) : (
                <button key={item} type="button" onClick={() => setPage(item as number)}
                  className={`w-9 h-9 text-[13px] rounded-lg font-medium transition-colors ${
                    page === item ? 'bg-[#1d1d1f] text-white' : 'text-gray-600 hover:bg-gray-100'
                  }`}>
                  {item}
                </button>
              )
            )}
          <button type="button" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
            className="px-3 py-2 text-[13px] rounded-lg disabled:opacity-30 text-gray-600 hover:bg-gray-100">
            Next &#8594;
          </button>
        </nav>
      )}

      {/* Modals */}
      {showRegForm && <JobRegistrationForm onSubmit={createJob} onClose={() => setShowRegForm(false)} />}
      {rawTextJob && <RawTextModal job={rawTextJob} onClose={() => setRawTextJob(null)} />}
    </div>
  )
}
