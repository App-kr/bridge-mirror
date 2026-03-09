'use client'

/**
 * /admin/interviews — Interview Scheduling & Management
 * Google Meet 인터뷰 스케줄링, 이메일 미리보기/발송, 상태 관리
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'

import { API_URL } from '@/lib/api'

const API = API_URL

interface Interview {
  id: number
  candidate_name: string
  candidate_email: string
  employer_name: string
  employer_email: string
  interview_date: string
  interview_time: string
  meet_link: string
  status: string
  notes: string
  email_sent_candidate: number
  email_sent_employer: number
  email_sent_candidate_at: string | null
  email_sent_employer_at: string | null
  created_at: string
}

interface EmailPreview {
  subject: string
  body_html: string
  to_email: string
}

interface CandidateOption {
  id: string
  name: string
  email: string
}

interface InquiryOption {
  id: number
  name: string
}

const STATUS_COLORS: Record<string, string> = {
  scheduled: 'bg-blue-50 text-blue-700 border-blue-200',
  completed: 'bg-green-50 text-green-700 border-green-200',
  cancelled: 'bg-gray-50 text-gray-500 border-gray-200',
  no_show: 'bg-red-50 text-red-600 border-red-200',
}

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
      .then(json => {
        if (json.success) setPreview(json.data)
        else setError(json.message || 'Failed to load preview')
      })
      .catch(e => setError(e instanceof Error ? e.message : 'Failed'))
      .finally(() => setLoading(false))
  }, [interviewId, target, hdrs])

  const handleSend = async () => {
    setSending(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/interviews/${interviewId}/send-email`, {
        method: 'POST', headers: hdrs(), body: JSON.stringify({ target }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? json.message ?? 'Failed')
      onSent()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Send failed')
      setSending(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-gray-900">
              Email Preview — {target === 'candidate' ? 'Candidate' : 'School'}
            </h3>
            <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
          </div>
          {preview && (
            <div className="mt-2 text-sm text-gray-500 space-y-1">
              <p><span className="font-medium text-gray-600">To:</span> {preview.to_email}</p>
              <p><span className="font-medium text-gray-600">Subject:</span> {preview.subject}</p>
            </div>
          )}
        </div>
        <div className="flex-1 overflow-auto p-1 bg-gray-50">
          {loading ? (
            <div className="text-center py-16 text-gray-400 animate-pulse">Loading preview...</div>
          ) : error && !preview ? (
            <div className="text-center py-16 text-red-500">{error}</div>
          ) : preview ? (
            <iframe
              srcDoc={preview.body_html}
              className="w-full border-0 bg-white rounded"
              style={{ minHeight: '400px' }}
              title="Email Preview"
              sandbox="allow-same-origin"
            />
          ) : null}
        </div>
        <div className="p-4 border-t border-gray-200 flex items-center justify-between">
          {error && preview && <p className="text-sm text-red-500">{error}</p>}
          {!error && <span />}
          <div className="flex gap-2">
            <button type="button" onClick={onClose}
              className="admin-btn admin-btn-cancel">
              ✕ 취소
            </button>
            <button type="button" onClick={handleSend} disabled={sending || !preview}
              className="admin-btn admin-btn-save">
              {sending ? '발송 중...' : '💾 발송 확인'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function AdminInterviewsPage() {
  const { authed, login, headers, waking } = useAdminAuth()

  const [interviews, setInterviews] = useState<Interview[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [emailModal, setEmailModal] = useState<{ id: number; target: 'candidate' | 'employer' } | null>(null)

  // Manual creation form
  const [form, setForm] = useState({
    candidate_name: '', candidate_email: '',
    employer_name: '', employer_email: '',
    interview_date: '', interview_time: '',
    meet_link: '', notes: '', duration_minutes: '60',
    candidate_phone: '', employer_phone: '',
  })
  const [candidates, setCandidates] = useState<CandidateOption[]>([])
  const [searchTerm, setSearchTerm] = useState('')

  // Google Calendar confirm modal
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [confirmForm, setConfirmForm] = useState({
    candidate_id: '',
    candidate_name: '',
    inquiry_id: 0,
    inquiry_name: '',
    interview_date: '',
    interview_time: '',
    duration_minutes: '60',
    notes: '',
  })
  const [confirmCandidateSearch, setConfirmCandidateSearch] = useState('')
  const [confirmCandidates, setConfirmCandidates] = useState<CandidateOption[]>([])
  const [inquirySearch, setInquirySearch] = useState('')
  const [inquiries, setInquiries] = useState<InquiryOption[]>([])
  const [confirmLoading, setConfirmLoading] = useState(false)
  const [confirmResult, setConfirmResult] = useState<{
    id: number; meet_link: string; gcal_error?: string | null
  } | null>(null)

  const fetchInterviews = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/interviews`, { headers: headers() })
      if (res.status === 403) {
        const errBody = await res.json().catch(() => ({}))
        if (errBody.error?.includes?.('Access denied')) {
          setError('일시적으로 차단되었습니다. 자동 재시도 중...')
          const k = localStorage.getItem('bridge_admin_key') || ''
          await fetch(`${API}/api/admin/reset-blacklist`, { method: 'POST', headers: { 'x-admin-key': k } }).catch(() => {})
          setTimeout(() => window.location.reload(), 3000)
          return
        }
        setError('관리자 키가 올바르지 않습니다. 다시 로그인해주세요.')
        localStorage.removeItem('bridge_admin_key')
        return
      }
      const json = await res.json()
      if (json.success) setInterviews(json.data || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => {
    if (authed) fetchInterviews()
  }, [authed, fetchInterviews])

  const handleCreate = async () => {
    if (!form.interview_date || !form.interview_time || !form.meet_link) {
      setActionMsg('Date, Time, Meet Link는 필수입니다.')
      return
    }
    try {
      const res = await fetch(`${API}/api/admin/interviews`, {
        method: 'POST', headers: headers(), body: JSON.stringify(form),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`Interview #${json.data?.id} created!`)
      setShowForm(false)
      setForm({ candidate_name: '', candidate_email: '', employer_name: '', employer_email: '',
        interview_date: '', interview_time: '', meet_link: '', notes: '', duration_minutes: '60',
        candidate_phone: '', employer_phone: '' })
      fetchInterviews()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  const handleConfirm = async () => {
    if (!confirmForm.candidate_id || !confirmForm.inquiry_id || !confirmForm.interview_date || !confirmForm.interview_time) {
      setActionMsg('후보자, 구인처, 날짜, 시간은 필수입니다.')
      return
    }
    setConfirmLoading(true)
    try {
      const res = await fetch(`${API}/api/admin/interview/confirm`, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({
          candidate_id:     confirmForm.candidate_id,
          inquiry_id:       confirmForm.inquiry_id,
          interview_date:   confirmForm.interview_date,
          interview_time:   confirmForm.interview_time,
          duration_minutes: parseInt(confirmForm.duration_minutes),
          notes:            confirmForm.notes,
        }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? json.message ?? 'Failed')
      setConfirmResult({
        id:         json.data?.id,
        meet_link:  json.data?.meet_link || '',
        gcal_error: json.data?.gcal_error ?? null,
      })
    } catch (e) {
      setActionMsg(`확정 오류: ${e instanceof Error ? e.message : 'Failed'}`)
      setShowConfirmModal(false)
    } finally {
      setConfirmLoading(false)
    }
  }

  const handleStatus = async (id: number, newStatus: string) => {
    try {
      const res = await fetch(`${API}/api/admin/interviews/${id}`, {
        method: 'PATCH', headers: headers(), body: JSON.stringify({ status: newStatus }),
      })
      if (!res.ok) throw new Error('Failed')
      setActionMsg(`Interview #${id} → ${newStatus}`)
      fetchInterviews()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm(`Interview #${id}를 삭제하시겠습니까?`)) return
    try {
      await fetch(`${API}/api/admin/interviews/${id}`, { method: 'DELETE', headers: headers() })
      fetchInterviews()
    } catch { /* ignore */ }
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="space-y-6">

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Interview Management</h1>
          <p className="text-gray-500 text-sm">{interviews.length} interviews</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={fetchInterviews}
            className="text-sm text-blue-600 hover:underline">↻ 새로고침</button>
          <button type="button"
            onClick={() => { setShowConfirmModal(true); setConfirmResult(null); setConfirmForm({ candidate_id: '', candidate_name: '', inquiry_id: 0, inquiry_name: '', interview_date: '', interview_time: '', duration_minutes: '60', notes: '' }); setConfirmCandidateSearch(''); setInquirySearch('') }}
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors">
            ⚡ Google Meet 확정
          </button>
          <button type="button" onClick={() => setShowForm(!showForm)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
            + New Interview
          </button>
        </div>
      </div>

      {actionMsg && (
        <div className="card-flat bg-blue-50 border-blue-200 text-sm text-blue-700 flex justify-between items-center">
          <span>{actionMsg}</span>
          <button type="button" onClick={() => setActionMsg(null)} className="text-blue-500 hover:text-blue-700">×</button>
        </div>
      )}

      {/* New Interview Form (manual) */}
      {showForm && (
        <div className="card space-y-4">
          <h2 className="font-bold text-gray-900">Schedule New Interview</h2>

          {/* Candidate search */}
          <div>
            <label className="text-xs font-medium text-gray-500">후보자 *</label>
            <input className="input mt-1" placeholder="이름 또는 이메일 검색..."
              value={searchTerm}
              onChange={async (e) => {
                setSearchTerm(e.target.value)
                if (e.target.value.length >= 2) {
                  try {
                    const r = await fetch(`${API}/api/admin/candidates?search=${encodeURIComponent(e.target.value)}&limit=5`, { headers: headers() })
                    const j = await r.json()
                    if (j.success) setCandidates((j.data?.candidates ?? []).map((c: Record<string, unknown>) => ({ id: String(c.id || ''), name: String(c.full_name || c.name || ''), email: String(c.email || '') })))
                  } catch { setCandidates([]) }
                } else setCandidates([])
              }} />
            {candidates.length > 0 && (
              <div className="border border-gray-200 rounded-lg mt-1 bg-white shadow-sm max-h-40 overflow-auto">
                {candidates.map(c => (
                  <button key={c.id} type="button" className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm"
                    onClick={() => {
                      setForm({ ...form, candidate_name: c.name, candidate_email: c.email })
                      setSearchTerm(c.name)
                      setCandidates([])
                    }}>
                    {c.name} <span className="text-gray-400">({c.email})</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { key: 'candidate_name', label: 'Candidate Name *', ph: 'e.g. Sarah Johnson' },
              { key: 'candidate_email', label: 'Candidate Email *', ph: 'e.g. sarah@example.com' },
              { key: 'employer_name', label: 'Employer Name *', ph: 'e.g. ABC Academy' },
              { key: 'employer_email', label: 'Employer Email *', ph: 'e.g. admin@abc.com' },
              { key: 'interview_date', label: 'Date *', ph: '2026-03-15' },
              { key: 'interview_time', label: 'Time (KST) *', ph: '14:00' },
              { key: 'candidate_phone', label: 'Candidate Phone', ph: '010-1234-5678' },
              { key: 'employer_phone', label: 'Employer Phone', ph: '02-1234-5678' },
            ].map(({ key, label, ph }) => (
              <div key={key}>
                <label className="text-xs font-medium text-gray-500">{label}</label>
                <input className="input mt-1" placeholder={ph}
                  type={key === 'interview_date' ? 'date' : key === 'interview_time' ? 'time' : 'text'}
                  value={(form as Record<string, unknown>)[key] as string}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })} />
              </div>
            ))}
          </div>

          {/* Duration */}
          <div>
            <label className="text-xs font-medium text-gray-500">면접 시간</label>
            <div className="flex gap-2 mt-1">
              {['30', '45', '60'].map(d => (
                <button key={d} type="button"
                  className={`px-4 py-2 rounded-lg text-sm border transition-colors ${form.duration_minutes === d ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}
                  onClick={() => setForm({ ...form, duration_minutes: d })}>
                  {d}분
                </button>
              ))}
            </div>
          </div>

          {/* Meet link */}
          <div>
            <label className="text-xs font-medium text-gray-500">Google Meet Link *</label>
            <input className="input mt-1" placeholder="https://meet.google.com/xxx-xxxx-xxx"
              value={form.meet_link} onChange={(e) => setForm({ ...form, meet_link: e.target.value })} />
            <div className="mt-2 flex items-center gap-3 text-xs">
              <span className="text-amber-600">* 회의 액세스 유형: &apos;열기&apos; 자동 설정됨</span>
              <a href="https://meet.google.com/new" target="_blank" rel="noopener noreferrer"
                className="text-blue-600 hover:underline font-medium">+ New Meet Room</a>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="text-xs font-medium text-gray-500">메모</label>
            <textarea className="input mt-1" rows={2} placeholder="Optional notes..."
              value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>

          <div className="flex gap-2 justify-end">
            <button type="button" onClick={() => setShowForm(false)}
              className="admin-btn admin-btn-cancel">✕ 취소</button>
            <button type="button" onClick={handleCreate}
              className="admin-btn admin-btn-save">
              💾 저장
            </button>
          </div>
        </div>
      )}

      {/* Interview List */}
      {loading ? (
        <div className="text-center py-16 text-gray-400 animate-pulse">로딩 중...</div>
      ) : error ? (
        <div className="text-center py-16 text-red-500">{error}</div>
      ) : interviews.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-4xl mb-4">🎥</p>
          <p>No interviews scheduled yet.</p>
          <p className="text-sm mt-2">Click &quot;+ New Interview&quot; to schedule one.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {interviews.map((iv) => (
            <div key={iv.id} className="card !py-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`badge text-[10px] border ${STATUS_COLORS[iv.status] ?? 'bg-gray-50 text-gray-600 border-gray-200'}`}>
                      {iv.status}
                    </span>
                    <span className="font-bold text-gray-900">
                      {iv.interview_date} {iv.interview_time}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-400 text-xs">Candidate:</span>{' '}
                      <span className="text-gray-700">{iv.candidate_name || '-'}</span>
                      {iv.candidate_email && <span className="text-gray-400 text-xs ml-1">({iv.candidate_email})</span>}
                    </div>
                    <div>
                      <span className="text-gray-400 text-xs">Employer:</span>{' '}
                      <span className="text-gray-700">{iv.employer_name || '-'}</span>
                      {iv.employer_email && <span className="text-gray-400 text-xs ml-1">({iv.employer_email})</span>}
                    </div>
                  </div>
                  {iv.meet_link && (
                    <a href={iv.meet_link} target="_blank" rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline mt-2">
                      🔗 {iv.meet_link.length > 50 ? iv.meet_link.slice(0, 50) + '...' : iv.meet_link}
                    </a>
                  )}
                  {iv.notes && <p className="text-xs text-gray-400 mt-1">{iv.notes}</p>}

                  {/* Email send buttons */}
                  <div className="flex items-center gap-2 mt-3">
                    <button type="button"
                      onClick={() => setEmailModal({ id: iv.id, target: 'employer' })}
                      className={`text-[11px] px-2 py-1 rounded border ${iv.email_sent_employer === 1 ? 'border-green-200 text-green-600 hover:bg-green-50' : 'border-indigo-200 text-indigo-600 hover:bg-indigo-50'}`}>
                      {iv.email_sent_employer === 1 ? '✓ 학교 발송됨 (재발송)' : '📧 학교 발송'}
                    </button>
                    <button type="button"
                      onClick={() => setEmailModal({ id: iv.id, target: 'candidate' })}
                      className={`text-[11px] px-2 py-1 rounded border ${iv.email_sent_candidate === 1 ? 'border-green-200 text-green-600 hover:bg-green-50' : 'border-teal-200 text-teal-600 hover:bg-teal-50'}`}>
                      {iv.email_sent_candidate === 1 ? '✓ 후보자 발송됨 (재발송)' : '📧 후보자 발송'}
                    </button>
                  </div>
                </div>

                <div className="flex flex-col gap-1 shrink-0">
                  {iv.status === 'scheduled' && (
                    <>
                      <button type="button" onClick={() => handleStatus(iv.id, 'completed')}
                        className="text-[11px] px-2 py-1 rounded border border-green-200 text-green-600 hover:bg-green-50">
                        Completed
                      </button>
                      <button type="button" onClick={() => handleStatus(iv.id, 'no_show')}
                        className="text-[11px] px-2 py-1 rounded border border-amber-200 text-amber-600 hover:bg-amber-50">
                        No-Show
                      </button>
                      <button type="button" onClick={() => handleStatus(iv.id, 'cancelled')}
                        className="text-[11px] px-2 py-1 rounded border border-gray-200 text-gray-500 hover:bg-gray-50">
                        Cancel
                      </button>
                    </>
                  )}
                  <button type="button" onClick={() => handleDelete(iv.id)}
                    className="admin-btn admin-btn-delete">
                    − 삭제
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Email Preview Modal */}
      {emailModal && (
        <EmailPreviewModal
          interviewId={emailModal.id}
          target={emailModal.target}
          hdrs={headers}
          onClose={() => setEmailModal(null)}
          onSent={() => {
            setEmailModal(null)
            setActionMsg(`${emailModal.target} email sent!`)
            fetchInterviews()
          }}
        />
      )}

      {/* Google Calendar 자동 확정 Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-xl max-h-[90vh] flex flex-col overflow-hidden">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="font-bold text-gray-900">⚡ Google Meet 인터뷰 자동 확정</h3>
              <button type="button"
                onClick={() => { setShowConfirmModal(false); setConfirmResult(null) }}
                className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>

            <div className="flex-1 overflow-auto p-4 space-y-4">
              {confirmResult ? (
                /* Success view */
                <div className="text-center py-8">
                  <div className="text-5xl mb-4">✅</div>
                  <p className="font-bold text-gray-900 text-lg">인터뷰 확정 완료!</p>
                  <p className="text-sm text-gray-500 mt-1">Interview #{confirmResult.id}</p>
                  {confirmResult.meet_link ? (
                    <a href={confirmResult.meet_link} target="_blank" rel="noopener noreferrer"
                      className="inline-block mt-4 px-5 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 transition-colors">
                      🔗 Google Meet 참가
                    </a>
                  ) : (
                    <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-700">
                      <p className="font-semibold">⚠️ Google Calendar 미연동</p>
                      <p className="mt-1 text-xs">인터뷰는 저장되었습니다. Meet 링크는 나중에 수동으로 추가하세요.</p>
                      <p className="mt-1 text-xs text-amber-500">설정: GOOGLE_SERVICE_ACCOUNT_JSON + GOOGLE_CALENDAR_ID 환경변수</p>
                    </div>
                  )}
                  {confirmResult.gcal_error && !confirmResult.meet_link && (
                    <p className="text-xs text-red-400 mt-2">{confirmResult.gcal_error}</p>
                  )}
                </div>
              ) : (
                /* Form view */
                <>
                  {/* Candidate search */}
                  <div>
                    <label className="text-xs font-medium text-gray-500">후보자 * (이름/이메일 검색)</label>
                    <input className="input mt-1" placeholder="이름 또는 이메일 입력..."
                      value={confirmCandidateSearch}
                      onChange={async (e) => {
                        setConfirmCandidateSearch(e.target.value)
                        setConfirmForm(p => ({ ...p, candidate_id: '', candidate_name: '' }))
                        if (e.target.value.length >= 2) {
                          try {
                            const r = await fetch(`${API}/api/admin/candidates?search=${encodeURIComponent(e.target.value)}&limit=5`, { headers: headers() })
                            const j = await r.json()
                            if (j.success) setConfirmCandidates((j.data?.candidates ?? []).map((c: Record<string, unknown>) => ({
                              id: String(c.id || ''),
                              name: String(c.full_name || c.name || ''),
                              email: String(c.email || ''),
                            })))
                          } catch { setConfirmCandidates([]) }
                        } else setConfirmCandidates([])
                      }} />
                    {confirmCandidates.length > 0 && (
                      <div className="border border-gray-200 rounded-lg mt-1 bg-white shadow-sm max-h-40 overflow-auto">
                        {confirmCandidates.map(c => (
                          <button key={c.id} type="button"
                            className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm"
                            onClick={() => {
                              setConfirmForm(p => ({ ...p, candidate_id: c.id, candidate_name: c.name }))
                              setConfirmCandidateSearch(`${c.name} (${c.email})`)
                              setConfirmCandidates([])
                            }}>
                            {c.name} <span className="text-gray-400">({c.email})</span>
                          </button>
                        ))}
                      </div>
                    )}
                    {confirmForm.candidate_id && (
                      <p className="text-xs text-emerald-600 mt-1">✓ {confirmForm.candidate_name} · ID: {confirmForm.candidate_id}</p>
                    )}
                  </div>

                  {/* Inquiry search */}
                  <div>
                    <label className="text-xs font-medium text-gray-500">구인처 (학교) * 검색</label>
                    <input className="input mt-1" placeholder="학교명 또는 담당자명 입력..."
                      value={inquirySearch}
                      onChange={async (e) => {
                        setInquirySearch(e.target.value)
                        setConfirmForm(p => ({ ...p, inquiry_id: 0, inquiry_name: '' }))
                        if (e.target.value.length >= 2) {
                          try {
                            const r = await fetch(`${API}/api/admin/inquiries?q=${encodeURIComponent(e.target.value)}&limit=5`, { headers: headers() })
                            const j = await r.json()
                            if (j.success) setInquiries((j.data?.inquiries ?? []).map((i: Record<string, unknown>) => ({
                              id: Number(i.id),
                              name: String(i.school_name || i.contact_name || ''),
                            })))
                          } catch { setInquiries([]) }
                        } else setInquiries([])
                      }} />
                    {inquiries.length > 0 && (
                      <div className="border border-gray-200 rounded-lg mt-1 bg-white shadow-sm max-h-40 overflow-auto">
                        {inquiries.map(i => (
                          <button key={i.id} type="button"
                            className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm"
                            onClick={() => {
                              setConfirmForm(p => ({ ...p, inquiry_id: i.id, inquiry_name: i.name }))
                              setInquirySearch(i.name)
                              setInquiries([])
                            }}>
                            #{i.id} {i.name}
                          </button>
                        ))}
                      </div>
                    )}
                    {confirmForm.inquiry_id > 0 && (
                      <p className="text-xs text-emerald-600 mt-1">✓ {confirmForm.inquiry_name} · Inquiry #{confirmForm.inquiry_id}</p>
                    )}
                  </div>

                  {/* Date / Time */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-medium text-gray-500">날짜 *</label>
                      <input type="date" className="input mt-1"
                        value={confirmForm.interview_date}
                        onChange={e => setConfirmForm(p => ({ ...p, interview_date: e.target.value }))} />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-500">시간 (KST) *</label>
                      <input type="time" className="input mt-1"
                        value={confirmForm.interview_time}
                        onChange={e => setConfirmForm(p => ({ ...p, interview_time: e.target.value }))} />
                    </div>
                  </div>

                  {/* Duration */}
                  <div>
                    <label className="text-xs font-medium text-gray-500">면접 시간</label>
                    <div className="flex gap-2 mt-1">
                      {['30', '45', '60'].map(d => (
                        <button key={d} type="button"
                          className={`px-4 py-2 rounded-lg text-sm border transition-colors ${confirmForm.duration_minutes === d ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}
                          onClick={() => setConfirmForm(p => ({ ...p, duration_minutes: d }))}>
                          {d}분
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Notes */}
                  <div>
                    <label className="text-xs font-medium text-gray-500">메모</label>
                    <textarea className="input mt-1" rows={2} placeholder="Optional notes..."
                      value={confirmForm.notes}
                      onChange={e => setConfirmForm(p => ({ ...p, notes: e.target.value }))} />
                  </div>

                  <div className="p-3 bg-gray-50 rounded-xl text-xs text-gray-500 space-y-1">
                    <p>📅 Google Calendar 이벤트 + Meet 링크 자동 생성</p>
                    <p>📧 후보자(영문)·구인처(한국어) 이메일 자동 발송</p>
                    <p className="text-amber-500">* GOOGLE_SERVICE_ACCOUNT_JSON 미설정 시 이벤트 없이 저장됩니다</p>
                  </div>
                </>
              )}
            </div>

            <div className="p-4 border-t border-gray-200 flex gap-2 justify-end">
              {confirmResult ? (
                <button type="button"
                  onClick={() => { setShowConfirmModal(false); setConfirmResult(null); fetchInterviews() }}
                  className="admin-btn admin-btn-save">
                  확인
                </button>
              ) : (
                <>
                  <button type="button"
                    onClick={() => { setShowConfirmModal(false); setConfirmResult(null) }}
                    className="admin-btn admin-btn-cancel">
                    ✕ 취소
                  </button>
                  <button type="button" onClick={handleConfirm}
                    disabled={confirmLoading || !confirmForm.candidate_id || !confirmForm.inquiry_id || !confirmForm.interview_date || !confirmForm.interview_time}
                    className="admin-btn admin-btn-save disabled:opacity-50 disabled:cursor-not-allowed">
                    {confirmLoading ? '확정 중...' : '⚡ Google Meet 확정'}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
