'use client'

/**
 * /admin/interviews — Interview Management (Card Layout)
 * 예정/지난 인터뷰 분리 · 날짜/시간 변경 · 취소 · Meet 참가 · 이메일 상태
 * 한국 날짜/시간 표시 · 강사번호 표시
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL

/* ── Google Meet Room Pool (5개 고정 열린방) ── */
const DEFAULT_MEET_POOL = [
  'https://meet.google.com/kmt-ydhj-fmf',
  'https://meet.google.com/abc-defg-hij',
  'https://meet.google.com/xyz-uvwx-rst',
  'https://meet.google.com/qwe-rtyp-asd',
  'https://meet.google.com/mnb-vcxz-lkj',
]
const MEET_POOL_KEY = 'bridge_meet_pool'

function loadMeetPool(): string[] {
  try {
    const s = localStorage.getItem(MEET_POOL_KEY)
    if (s) { const arr = JSON.parse(s); if (Array.isArray(arr) && arr.length) return arr }
  } catch { /* ignore */ }
  return DEFAULT_MEET_POOL
}

function saveMeetPool(pool: string[]) {
  localStorage.setItem(MEET_POOL_KEY, JSON.stringify(pool))
}

/** 예정된 인터뷰와 겹치지 않는 Meet 링크를 랜덤 배정 */
function pickAvailableMeet(pool: string[], interviews: Interview[], date: string): string {
  // 같은 날 scheduled 인터뷰에서 사용 중인 링크 수집
  const usedOnDate = new Set(
    interviews
      .filter(iv => iv.status === 'scheduled' && iv.interview_date === date)
      .map(iv => iv.meet_link)
  )
  // 사용 안 된 링크 우선
  const available = pool.filter(link => !usedOnDate.has(link))
  if (available.length > 0) return available[Math.floor(Math.random() * available.length)]
  // 모두 사용 중이면 그냥 랜덤 (5개 이상 인터뷰가 같은 날 겹칠 가능성 낮음)
  return pool[Math.floor(Math.random() * pool.length)]
}

interface Interview {
  id: number
  candidate_name: string
  candidate_email: string
  candidate_id: string
  employer_name: string
  employer_email: string
  interview_date: string
  interview_time: string
  meet_link: string
  status: string
  notes: string
  duration_minutes: number
  email_sent_candidate: number
  email_sent_employer: number
  candidate_email_sent_at: string | null
  school_email_sent_at: string | null
  created_at: string
}

interface EmailPreview {
  subject: string
  body_html: string
  to_email: string
}

const STATUS_META: Record<string, { label: string; color: string; bg: string; border: string; icon: string }> = {
  scheduled:  { label: '예정',   color: '#2563eb', bg: '#eff6ff',  border: '#bfdbfe', icon: '📅' },
  completed:  { label: '완료',   color: '#16a34a', bg: '#f0fdf4',  border: '#bbf7d0', icon: '✅' },
  cancelled:  { label: '취소',   color: '#6b7280', bg: '#f9fafb',  border: '#e5e7eb', icon: '❌' },
  no_show:    { label: '불참',   color: '#dc2626', bg: '#fef2f2',  border: '#fecaca', icon: '🚫' },
}

/* ── Korean Date/Time Formatting ── */
const WEEKDAYS_KO = ['일', '월', '화', '수', '목', '금', '토']

function formatKoreanDateTime(date: string, time: string): { dateStr: string; timeStr: string; weekday: string; relative: string } {
  const d = new Date(`${date}T${time || '00:00'}`)
  const now = new Date()
  const diff = d.getTime() - now.getTime()
  const days = Math.ceil(diff / (1000 * 60 * 60 * 24))

  const m = d.getMonth() + 1
  const day = d.getDate()
  const weekday = WEEKDAYS_KO[d.getDay()]

  // time → 오전/오후 표시
  const [h, min] = (time || '00:00').split(':').map(Number)
  const ampm = h < 12 ? '오전' : '오후'
  const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h
  const timeStr = `${ampm} ${h12}:${String(min).padStart(2, '0')}`

  let relative = ''
  if (days === 0) relative = '오늘'
  else if (days === 1) relative = '내일'
  else if (days === 2) relative = '모레'
  else if (days > 0 && days <= 7) relative = `${days}일 후`
  else if (days > 7) relative = `${Math.ceil(days / 7)}주 후`
  else if (days === -1) relative = '어제'
  else if (days < -1) relative = `${Math.abs(days)}일 전`

  return { dateStr: `${m}월 ${day}일 (${weekday})`, timeStr, weekday, relative }
}

/* ── Email Preview Modal ── */
function EmailPreviewModal({
  interviewId, target, hdrs, onClose, onSent,
}: {
  interviewId: number
  target: 'candidate' | 'employer'
  hdrs: () => Record<string, string>
  onClose: () => void
  onSent: () => void
}) {
  const [preview, setPreview] = useState<EmailPreview | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    fetch(`${API}/api/admin/interviews/${interviewId}/preview-email?target=${target}`, { headers: hdrs() })
      .then(r => r.json())
      .then(json => { if (json.success) setPreview(json.data); else setError(json.message || 'Failed') })
      .catch(e => setError(e instanceof Error ? e.message : 'Failed'))
      .finally(() => setLoading(false))
  }, [interviewId, target, hdrs])

  const handleSend = async () => {
    setSending(true); setError(null)
    try {
      const res = await fetch(`${API}/api/admin/interviews/${interviewId}/send-email`, {
        method: 'POST', headers: hdrs(), body: JSON.stringify({ target }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? json.message ?? 'Failed')
      onSent()
    } catch (e) { setError(e instanceof Error ? e.message : 'Send failed'); setSending(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-gray-900">이메일 미리보기 — {target === 'candidate' ? '후보자' : '학교'}</h3>
            {preview && <p className="text-xs text-gray-500 mt-1">To: {preview.to_email} · Subject: {preview.subject}</p>}
          </div>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        <div className="flex-1 overflow-auto p-1 bg-gray-50">
          {loading ? <div className="text-center py-16 text-gray-400 animate-pulse">로딩 중...</div>
            : error && !preview ? <div className="text-center py-16 text-red-500">{error}</div>
            : preview ? <iframe srcDoc={preview.body_html} className="w-full border-0 bg-white rounded" style={{ minHeight: 400 }} title="Preview" sandbox="allow-same-origin" />
            : null}
        </div>
        <div className="p-4 border-t border-gray-200 flex items-center justify-between">
          {error && preview ? <p className="text-sm text-red-500">{error}</p> : <span />}
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200">취소</button>
            <button type="button" onClick={handleSend} disabled={sending || !preview}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
              {sending ? '발송 중...' : '📧 발송 확인'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Reschedule Modal ── */
function RescheduleModal({
  interview, hdrs, onClose, onDone,
}: {
  interview: Interview
  hdrs: () => Record<string, string>
  onClose: () => void
  onDone: () => void
}) {
  const [date, setDate] = useState(interview.interview_date)
  const [time, setTime] = useState(interview.interview_time)
  const [duration, setDuration] = useState(interview.duration_minutes || 20)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSave = async () => {
    setSaving(true); setError(null)
    try {
      const res = await fetch(`${API}/api/admin/interviews/${interview.id}`, {
        method: 'PATCH', headers: hdrs(),
        body: JSON.stringify({ interview_date: date, interview_time: time, duration_minutes: duration }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      onDone()
    } catch (e) { setError(e instanceof Error ? e.message : 'Failed'); setSaving(false) }
  }

  const fmt = formatKoreanDateTime(date, time)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <h3 className="font-bold text-gray-900">📅 일정 변경 — #{interview.id}</h3>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        <div className="p-5 space-y-4">
          {/* Current → New preview */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-sm">
            <span className="font-semibold text-amber-700">현재:</span>{' '}
            {formatKoreanDateTime(interview.interview_date, interview.interview_time).dateStr}{' '}
            {formatKoreanDateTime(interview.interview_date, interview.interview_time).timeStr}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">날짜</label>
              <input type="date" value={date} onChange={e => setDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-violet-400 focus:border-violet-400 outline-none" />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">시간 (KST)</label>
              <input type="time" value={time} onChange={e => setTime(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-violet-400 focus:border-violet-400 outline-none" />
            </div>
          </div>

          {/* Duration */}
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-2">면접 시간</label>
            <div className="flex gap-2">
              {[15, 20, 30].map(d => (
                <button key={d} type="button" onClick={() => setDuration(d)}
                  className={`px-4 py-1.5 rounded-lg text-sm font-semibold border transition-colors ${
                    duration === d ? 'bg-violet-100 text-violet-700 border-violet-300' : 'bg-white text-gray-500 border-gray-200 hover:bg-gray-50'
                  }`}>{d}분</button>
              ))}
            </div>
          </div>

          {/* Preview */}
          <div className="bg-violet-50 border border-violet-200 rounded-xl p-3 text-sm">
            <span className="font-semibold text-violet-700">변경 후:</span>{' '}
            {fmt.dateStr} {fmt.timeStr}
            {fmt.relative && <span className="ml-2 text-violet-500">({fmt.relative})</span>}
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}
        </div>
        <div className="p-4 border-t border-gray-200 flex gap-2 justify-end">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200">취소</button>
          <button type="button" onClick={handleSave} disabled={saving}
            className="px-4 py-2 text-sm font-semibold text-white bg-violet-600 rounded-lg hover:bg-violet-700 disabled:opacity-50">
            {saving ? '저장 중...' : '📅 일정 변경'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Interview Card ── */
function InterviewCard({
  iv, onStatusChange, onDelete, onReschedule, onEmailPreview, isUpcoming,
}: {
  iv: Interview
  onStatusChange: (id: number, status: string) => void
  onDelete: (id: number) => void
  onReschedule: (iv: Interview) => void
  onEmailPreview: (id: number, target: 'candidate' | 'employer') => void
  isUpcoming: boolean
}) {
  const meta = STATUS_META[iv.status] || STATUS_META.scheduled
  const fmt = formatKoreanDateTime(iv.interview_date, iv.interview_time)
  const meetLink = iv.meet_link || loadMeetPool()[0]

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
      style={{ borderLeft: `4px solid ${meta.color}` }}>
      <div className="p-4">
        {/* Top row: status + date + relative */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold" style={{ color: meta.color }}>
              {meta.icon} {meta.label}
            </span>
            {iv.duration_minutes > 0 && (
              <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">{iv.duration_minutes}분</span>
            )}
          </div>
          {fmt.relative && (
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
              isUpcoming ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'
            }`}>{fmt.relative}</span>
          )}
        </div>

        {/* Date/Time prominent */}
        <div className="mb-3">
          <div className="text-lg font-bold text-gray-900">{fmt.dateStr}</div>
          <div className="text-sm font-semibold text-gray-600">{fmt.timeStr} KST</div>
        </div>

        {/* Candidate / Employer info */}
        <div className="grid grid-cols-2 gap-3 text-sm mb-3">
          <div className="bg-gray-50 rounded-lg p-2.5">
            <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Candidate</div>
            <div className="font-semibold text-gray-900">{iv.candidate_name || '-'}</div>
            {iv.candidate_id && (
              <div className="text-xs text-violet-600 font-semibold">#{iv.candidate_id}</div>
            )}
            {iv.candidate_email && <div className="text-xs text-gray-500 truncate">{iv.candidate_email}</div>}
          </div>
          <div className="bg-gray-50 rounded-lg p-2.5">
            <div className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">School</div>
            <div className="font-semibold text-gray-900">{iv.employer_name || '-'}</div>
            {iv.employer_email && <div className="text-xs text-gray-500 truncate">{iv.employer_email}</div>}
          </div>
        </div>

        {/* Notes */}
        {iv.notes && (
          <div className="text-xs text-gray-500 bg-yellow-50 border border-yellow-100 rounded-lg px-3 py-2 mb-3">
            💬 {iv.notes}
          </div>
        )}

        {/* Meet link */}
        <a href={meetLink} target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-2 text-xs font-semibold text-blue-600 hover:text-blue-800 mb-3 group">
          <span className="bg-blue-100 group-hover:bg-blue-200 rounded-lg px-3 py-1.5 transition-colors">
            🔗 Meet 참가
          </span>
          <span className="text-gray-400 truncate">{meetLink.replace('https://meet.google.com/', '')}</span>
        </a>

        {/* Email status + action buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={() => onEmailPreview(iv.id, 'candidate')}
            className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-colors ${
              iv.email_sent_candidate ? 'border-green-200 text-green-600 bg-green-50 hover:bg-green-100' : 'border-teal-200 text-teal-600 hover:bg-teal-50'
            }`}>
            {iv.email_sent_candidate ? '✓ 후보자 발송됨' : '📧 후보자'}
          </button>
          <button type="button" onClick={() => onEmailPreview(iv.id, 'employer')}
            className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-colors ${
              iv.email_sent_employer ? 'border-green-200 text-green-600 bg-green-50 hover:bg-green-100' : 'border-indigo-200 text-indigo-600 hover:bg-indigo-50'
            }`}>
            {iv.email_sent_employer ? '✓ 학교 발송됨' : '📧 학교'}
          </button>

          <div className="flex-1" />

          {/* Actions */}
          {iv.status === 'scheduled' && (
            <>
              <button type="button" onClick={() => onReschedule(iv)}
                className="text-[11px] font-semibold px-2.5 py-1 rounded-full border border-violet-200 text-violet-600 hover:bg-violet-50 transition-colors"
                title="날짜/시간 변경">
                🔄 일정변경
              </button>
              <button type="button" onClick={() => onStatusChange(iv.id, 'completed')}
                className="text-[11px] font-semibold px-2.5 py-1 rounded-full border border-green-200 text-green-600 hover:bg-green-50 transition-colors">
                ✅ 완료
              </button>
              <button type="button" onClick={() => onStatusChange(iv.id, 'no_show')}
                className="text-[11px] font-semibold px-2.5 py-1 rounded-full border border-amber-200 text-amber-600 hover:bg-amber-50 transition-colors">
                🚫 불참
              </button>
              <button type="button" onClick={() => onStatusChange(iv.id, 'cancelled')}
                className="text-[11px] font-semibold px-2.5 py-1 rounded-full border border-gray-200 text-gray-500 hover:bg-gray-50 transition-colors">
                ❌ 취소
              </button>
            </>
          )}
          {iv.status !== 'scheduled' && (
            <button type="button" onClick={() => onStatusChange(iv.id, 'scheduled')}
              className="text-[11px] font-semibold px-2.5 py-1 rounded-full border border-blue-200 text-blue-600 hover:bg-blue-50 transition-colors">
              📅 재예약
            </button>
          )}
          <button type="button" onClick={() => onDelete(iv.id)}
            className="text-[11px] font-semibold px-2.5 py-1 rounded-full border border-red-200 text-red-400 hover:bg-red-50 hover:text-red-600 transition-colors">
            🗑
          </button>
        </div>
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════
   Main Page
   ══════════════════════════════════════════ */
export default function AdminInterviewsPage() {
  const { authed, login, headers, waking } = useAdminAuth()

  const [interviews, setInterviews] = useState<Interview[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [emailModal, setEmailModal] = useState<{ id: number; target: 'candidate' | 'employer' } | null>(null)
  const [rescheduleTarget, setRescheduleTarget] = useState<Interview | null>(null)
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [meetPool, setMeetPool] = useState<string[]>(DEFAULT_MEET_POOL)
  const [showMeetSettings, setShowMeetSettings] = useState(false)

  // Load meet pool from localStorage on mount
  useEffect(() => { setMeetPool(loadMeetPool()) }, [])

  // Quick create form
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    candidate_name: '', candidate_email: '', candidate_id: '',
    employer_name: '', employer_email: '',
    interview_date: '', interview_time: '14:00',
    meet_link: '', notes: '', duration_minutes: 20,
    auto_send_email: false,
  })
  const [creating, setCreating] = useState(false)

  const fetchInterviews = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const res = await fetch(`${API}/api/admin/interviews`, { headers: headers() })
      if (res.status === 403) { setError('인증 오류'); return }
      const json = await res.json()
      if (json.success) setInterviews(json.data || [])
    } catch (e) { setError(e instanceof Error ? e.message : 'Failed') }
    finally { setLoading(false) }
  }, [headers])

  useEffect(() => { if (authed) fetchInterviews() }, [authed, fetchInterviews])

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) { const t = setTimeout(() => setToast(null), 3000); return () => clearTimeout(t) }
  }, [toast])

  const handleCreate = async () => {
    if (!form.interview_date || !form.interview_time) { setToast('날짜와 시간을 입력하세요'); return }
    setCreating(true)
    try {
      const res = await fetch(`${API}/api/admin/interviews`, {
        method: 'POST', headers: headers(), body: JSON.stringify(form),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setToast(`Interview #${json.data?.id} 생성됨${json.data?.email_result?.status === 'sent' ? ' + 이메일 발송' : ''}`)
      setShowCreate(false)
      setForm({ ...form, candidate_name: '', candidate_email: '', candidate_id: '', employer_name: '', employer_email: '', notes: '' })
      fetchInterviews()
    } catch (e) { setToast(`오류: ${e instanceof Error ? e.message : 'Failed'}`) }
    finally { setCreating(false) }
  }

  const handleStatus = async (id: number, newStatus: string) => {
    if (newStatus === 'cancelled' && !confirm('인터뷰를 취소하시겠습니까?')) return
    try {
      const res = await fetch(`${API}/api/admin/interviews/${id}`, {
        method: 'PATCH', headers: headers(), body: JSON.stringify({ status: newStatus }),
      })
      if (!res.ok) throw new Error('Failed')
      setToast(`#${id} → ${STATUS_META[newStatus]?.label || newStatus}`)
      fetchInterviews()
    } catch (e) { setToast(`오류: ${e instanceof Error ? e.message : 'Failed'}`) }
  }

  const handleDelete = async (id: number) => {
    if (!confirm(`Interview #${id}를 삭제하시겠습니까?`)) return
    try {
      await fetch(`${API}/api/admin/interviews/${id}`, { method: 'DELETE', headers: headers() })
      setToast(`#${id} 삭제됨`)
      fetchInterviews()
    } catch { /* ignore */ }
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  // Split interviews
  const now = new Date()
  const filtered = filterStatus === 'all' ? interviews : interviews.filter(iv => iv.status === filterStatus)
  const upcoming = filtered.filter(iv => {
    const d = new Date(`${iv.interview_date}T${iv.interview_time || '23:59'}`)
    return d >= now && iv.status === 'scheduled'
  }).sort((a, b) => `${a.interview_date}${a.interview_time}`.localeCompare(`${b.interview_date}${b.interview_time}`))
  const past = filtered.filter(iv => !upcoming.includes(iv))
    .sort((a, b) => `${b.interview_date}${b.interview_time}`.localeCompare(`${a.interview_date}${a.interview_time}`))

  // Stats
  const stats = {
    total: interviews.length,
    scheduled: interviews.filter(iv => iv.status === 'scheduled').length,
    completed: interviews.filter(iv => iv.status === 'completed').length,
    cancelled: interviews.filter(iv => iv.status === 'cancelled').length,
    no_show: interviews.filter(iv => iv.status === 'no_show').length,
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Toast */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-gray-900 text-white px-5 py-3 rounded-xl shadow-2xl text-sm font-semibold flex items-center gap-2 animate-in slide-in-from-top">
          <span>{toast}</span>
          <button type="button" onClick={() => setToast(null)} className="text-gray-400 hover:text-white ml-2">&times;</button>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Interview Management</h1>
          <p className="text-sm text-gray-500 mt-1">
            전체 {stats.total}건 · 예정 <span className="text-blue-600 font-semibold">{stats.scheduled}</span> · 완료 <span className="text-green-600 font-semibold">{stats.completed}</span>
            {stats.cancelled > 0 && <> · 취소 {stats.cancelled}</>}
            {stats.no_show > 0 && <> · 불참 {stats.no_show}</>}
          </p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => setShowMeetSettings(true)}
            className="px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors" title="Meet 링크 설정">
            🔗 Meet 설정
          </button>
          <button type="button" onClick={fetchInterviews}
            className="px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            ↻ 새로고침
          </button>
          <button type="button" onClick={() => {
            const tom = new Date(); tom.setDate(tom.getDate()+1)
            const d = tom.toISOString().slice(0,10)
            setForm(p => ({...p, interview_date: d, meet_link: pickAvailableMeet(meetPool, interviews, d)}))
            setShowCreate(!showCreate)
          }}
            className="px-4 py-2 bg-violet-600 text-white rounded-lg text-sm font-semibold hover:bg-violet-700 transition-colors">
            + 인터뷰 생성
          </button>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 p-1 bg-gray-100 rounded-xl w-fit">
        {[
          { key: 'all', label: '전체' },
          { key: 'scheduled', label: '📅 예정' },
          { key: 'completed', label: '✅ 완료' },
          { key: 'cancelled', label: '❌ 취소' },
          { key: 'no_show', label: '🚫 불참' },
        ].map(f => (
          <button key={f.key} type="button" onClick={() => setFilterStatus(f.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              filterStatus === f.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>{f.label}</button>
        ))}
      </div>

      {/* Quick Create Form */}
      {showCreate && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h2 className="font-bold text-gray-900">📅 새 인터뷰</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">후보자 이름</label>
              <input className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="Sarah Johnson"
                value={form.candidate_name} onChange={e => setForm({...form, candidate_name: e.target.value})} />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">후보자 이메일</label>
              <input className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="sarah@email.com"
                value={form.candidate_email} onChange={e => setForm({...form, candidate_email: e.target.value})} />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">강사번호</label>
              <input className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="1234"
                value={form.candidate_id} onChange={e => setForm({...form, candidate_id: e.target.value})} />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">학교명</label>
              <input className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="ABC Academy"
                value={form.employer_name} onChange={e => setForm({...form, employer_name: e.target.value})} />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">날짜</label>
              <input type="date" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                value={form.interview_date} onChange={e => {
                  const d = e.target.value
                  setForm(p => ({...p, interview_date: d, meet_link: pickAvailableMeet(meetPool, interviews, d)}))
                }} />
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1">시간 (KST)</label>
              <input type="time" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                value={form.interview_time} onChange={e => setForm({...form, interview_time: e.target.value})} />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-2">면접 시간</label>
            <div className="flex gap-2">
              {[15, 20, 30].map(d => (
                <button key={d} type="button" onClick={() => setForm({...form, duration_minutes: d})}
                  className={`px-4 py-1.5 rounded-lg text-sm font-semibold border transition-colors ${
                    form.duration_minutes === d ? 'bg-violet-100 text-violet-700 border-violet-300' : 'bg-white text-gray-500 border-gray-200'
                  }`}>{d}분</button>
              ))}
            </div>
          </div>

          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div className="text-sm text-green-700">
                🔗 Meet: <code className="text-xs bg-green-100 px-1.5 py-0.5 rounded">{form.meet_link || '(미배정)'}</code>
              </div>
              <button type="button" onClick={() => setForm(p => ({...p, meet_link: pickAvailableMeet(meetPool, interviews, form.interview_date)}))}
                className="text-xs font-semibold text-violet-600 hover:text-violet-800 bg-violet-50 hover:bg-violet-100 px-2 py-1 rounded-lg transition-colors">
                🔄 다른 방
              </button>
            </div>
            <div className="text-[11px] text-green-600 mt-1">풀 {meetPool.length}개 중 자동 배정 (같은 날 겹침 방지)</div>
          </div>

          <textarea className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" rows={2} placeholder="메모 (선택)"
            value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} />

          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.auto_send_email} onChange={e => setForm({...form, auto_send_email: e.target.checked})}
              className="w-4 h-4" style={{ accentColor: '#7c3aed' }} />
            <span className="text-sm font-semibold text-gray-700">후보자에게 이메일 자동 발송</span>
          </label>

          <div className="flex gap-2 justify-end">
            <button type="button" onClick={() => setShowCreate(false)}
              className="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200">취소</button>
            <button type="button" onClick={handleCreate} disabled={creating}
              className="px-5 py-2 text-sm font-semibold text-white bg-violet-600 rounded-lg hover:bg-violet-700 disabled:opacity-50">
              {creating ? '생성 중...' : '📅 생성'}
            </button>
          </div>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="text-center py-20 text-gray-400 animate-pulse text-sm">로딩 중...</div>
      ) : error ? (
        <div className="text-center py-20 text-red-500 text-sm">{error}</div>
      ) : interviews.length === 0 ? (
        <div className="text-center py-20">
          <div className="text-5xl mb-4">📅</div>
          <p className="text-gray-500 font-medium">예정된 인터뷰가 없습니다</p>
          <p className="text-sm text-gray-400 mt-1">&quot;+ 인터뷰 생성&quot; 버튼을 클릭하세요</p>
        </div>
      ) : (
        <>
          {/* Upcoming */}
          {upcoming.length > 0 && (
            <div>
              <h2 className="text-sm font-bold text-blue-600 uppercase tracking-wider mb-3 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                예정된 인터뷰 ({upcoming.length})
              </h2>
              <div className="grid gap-3 md:grid-cols-2">
                {upcoming.map(iv => (
                  <InterviewCard key={iv.id} iv={iv} isUpcoming={true}
                    onStatusChange={handleStatus} onDelete={handleDelete}
                    onReschedule={setRescheduleTarget}
                    onEmailPreview={(id, target) => setEmailModal({ id, target })} />
                ))}
              </div>
            </div>
          )}

          {/* Past / Other */}
          {past.length > 0 && (
            <div>
              <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-3">
                지난 인터뷰 ({past.length})
              </h2>
              <div className="grid gap-3 md:grid-cols-2">
                {past.map(iv => (
                  <InterviewCard key={iv.id} iv={iv} isUpcoming={false}
                    onStatusChange={handleStatus} onDelete={handleDelete}
                    onReschedule={setRescheduleTarget}
                    onEmailPreview={(id, target) => setEmailModal({ id, target })} />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Email Preview Modal */}
      {emailModal && (
        <EmailPreviewModal
          interviewId={emailModal.id} target={emailModal.target} hdrs={headers}
          onClose={() => setEmailModal(null)}
          onSent={() => { setEmailModal(null); setToast(`${emailModal.target} 이메일 발송 완료`); fetchInterviews() }}
        />
      )}

      {/* Reschedule Modal */}
      {rescheduleTarget && (
        <RescheduleModal
          interview={rescheduleTarget} hdrs={headers}
          onClose={() => setRescheduleTarget(null)}
          onDone={() => { setRescheduleTarget(null); setToast('일정이 변경되었습니다'); fetchInterviews() }}
        />
      )}

      {/* Meet Settings Modal */}
      {showMeetSettings && (
        <MeetSettingsModal
          pool={meetPool}
          onSave={(newPool) => { setMeetPool(newPool); saveMeetPool(newPool); setShowMeetSettings(false); setToast('Meet 링크 저장 완료') }}
          onClose={() => setShowMeetSettings(false)}
        />
      )}
    </div>
  )
}

/* ── Meet Settings Modal ── */
function MeetSettingsModal({
  pool, onSave, onClose,
}: {
  pool: string[]
  onSave: (pool: string[]) => void
  onClose: () => void
}) {
  const [links, setLinks] = useState<string[]>([...pool])
  const [newLink, setNewLink] = useState('')

  const addLink = () => {
    const url = newLink.trim()
    if (!url || !url.includes('meet.google.com/')) return
    if (links.includes(url)) return
    setLinks([...links, url])
    setNewLink('')
  }

  const removeLink = (idx: number) => {
    if (links.length <= 1) return // 최소 1개 유지
    setLinks(links.filter((_, i) => i !== idx))
  }

  const resetDefaults = () => setLinks([...DEFAULT_MEET_POOL])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-gray-900">🔗 Google Meet 링크 풀 설정</h3>
            <p className="text-xs text-gray-500 mt-1">인터뷰 생성 시 같은 날 겹치지 않도록 랜덤 배정됩니다</p>
          </div>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>

        <div className="p-4 space-y-3 max-h-[60vh] overflow-auto">
          {links.map((link, idx) => (
            <div key={idx} className="flex items-center gap-2 group">
              <span className="w-6 h-6 rounded-full bg-violet-100 text-violet-700 flex items-center justify-center text-xs font-bold shrink-0">
                {idx + 1}
              </span>
              <div className="flex-1 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono text-gray-700 truncate">
                {link}
              </div>
              <a href={link} target="_blank" rel="noopener noreferrer"
                className="text-blue-500 hover:text-blue-700 text-sm shrink-0" title="열기">
                ↗
              </a>
              <button type="button" onClick={() => removeLink(idx)}
                className="text-red-300 hover:text-red-500 text-lg shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                title="삭제">×</button>
            </div>
          ))}

          {/* Add new */}
          <div className="flex gap-2 mt-2">
            <input className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="https://meet.google.com/xxx-xxxx-xxx"
              value={newLink} onChange={e => setNewLink(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') addLink() }} />
            <button type="button" onClick={addLink}
              className="px-3 py-2 bg-violet-600 text-white rounded-lg text-sm font-semibold hover:bg-violet-700 shrink-0">
              + 추가
            </button>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700 space-y-1">
            <p>💡 <b>Google Meet에서 방 만들기:</b> <a href="https://meet.google.com/new" target="_blank" rel="noopener noreferrer" className="underline font-semibold">meet.google.com/new</a></p>
            <p>방 생성 후 링크를 복사해서 위에 추가하세요. 액세스 유형을 &apos;열기&apos;로 설정하면 항상 열린 방이 됩니다.</p>
          </div>
        </div>

        <div className="p-4 border-t border-gray-200 flex items-center justify-between">
          <button type="button" onClick={resetDefaults} className="text-xs text-gray-400 hover:text-gray-600">기본값 복원</button>
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200">취소</button>
            <button type="button" onClick={() => onSave(links)} disabled={links.length === 0}
              className="px-5 py-2 text-sm font-semibold text-white bg-violet-600 rounded-lg hover:bg-violet-700 disabled:opacity-50">
              💾 저장 ({links.length}개)
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
