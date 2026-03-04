'use client'

/**
 * /admin/interviews — Interview Scheduling & Management
 * Google Meet 인터뷰 스케줄링, 이메일 미리보기/발송, 상태 관리
 */

import { useCallback, useEffect, useState } from 'react'
import AdminNav from '@/components/admin/AdminNav'
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
              className="px-4 py-2 text-gray-600 bg-gray-100 rounded-lg text-sm hover:bg-gray-200">
              Cancel
            </button>
            <button type="button" onClick={handleSend} disabled={sending || !preview}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
              {sending ? 'Sending...' : 'Confirm & Send'}
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

  const [form, setForm] = useState({
    candidate_name: '', candidate_email: '',
    employer_name: '', employer_email: '',
    interview_date: '', interview_time: '',
    meet_link: '', notes: '',
  })

  const fetchInterviews = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/interviews`, { headers: headers() })
      if (res.status === 403) { setError('Admin key가 올바르지 않습니다.'); return }
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
        interview_date: '', interview_time: '', meet_link: '', notes: '' })
      fetchInterviews()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
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
      <AdminNav active="/admin/interviews" />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Interview Management</h1>
          <p className="text-gray-500 text-sm">{interviews.length} interviews</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={fetchInterviews}
            className="text-sm text-blue-600 hover:underline">↻ 새로고침</button>
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

      {/* New Interview Form */}
      {showForm && (
        <div className="card space-y-4">
          <h2 className="font-bold text-gray-900">Schedule New Interview</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { key: 'candidate_name', label: 'Candidate Name', ph: 'e.g. Sarah Johnson' },
              { key: 'candidate_email', label: 'Candidate Email', ph: 'e.g. sarah@example.com' },
              { key: 'employer_name', label: 'Employer Name', ph: 'e.g. ABC Academy' },
              { key: 'employer_email', label: 'Employer Email', ph: 'e.g. admin@abc.com' },
              { key: 'interview_date', label: 'Date (YYYY-MM-DD) *', ph: '2026-03-15' },
              { key: 'interview_time', label: 'Time (HH:MM KST) *', ph: '14:00' },
            ].map(({ key, label, ph }) => (
              <div key={key}>
                <label className="text-xs font-medium text-gray-500">{label}</label>
                <input className="input mt-1" placeholder={ph}
                  value={(form as Record<string, unknown>)[key] as string}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })} />
              </div>
            ))}
          </div>
          <div>
            <label className="text-xs font-medium text-gray-500">Google Meet Link *</label>
            <input className="input mt-1" placeholder="https://meet.google.com/xxx-xxxx-xxx"
              value={form.meet_link} onChange={(e) => setForm({ ...form, meet_link: e.target.value })} />
            <div className="mt-2 flex items-center gap-3 text-xs">
              <span className="text-amber-600">* Meet 설정에서 &apos;회의 액세스 유형&apos;을 &apos;열기&apos;로 설정해주세요</span>
              <a href="https://meet.google.com/new" target="_blank" rel="noopener noreferrer"
                className="text-blue-600 hover:underline font-medium">+ New Meet Room</a>
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-500">Notes</label>
            <input className="input mt-1" placeholder="Optional notes..."
              value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={() => setShowForm(false)}
              className="px-4 py-2 text-gray-600 bg-gray-100 rounded-lg text-sm hover:bg-gray-200">Cancel</button>
            <button type="button" onClick={handleCreate}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
              Schedule Interview
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
                  {iv.status === 'scheduled' && (
                    <div className="flex items-center gap-2 mt-3">
                      {iv.email_sent_employer === 1 ? (
                        <span className="text-[11px] text-green-600 flex items-center gap-1">
                          ✓ School sent{iv.email_sent_employer_at ? ` (${iv.email_sent_employer_at.slice(0, 16)})` : ''}
                        </span>
                      ) : (
                        <button type="button"
                          onClick={() => setEmailModal({ id: iv.id, target: 'employer' })}
                          className="text-[11px] px-2 py-1 rounded border border-indigo-200 text-indigo-600 hover:bg-indigo-50">
                          Send to School
                        </button>
                      )}
                      {iv.email_sent_candidate === 1 ? (
                        <span className="text-[11px] text-green-600 flex items-center gap-1">
                          ✓ Candidate sent{iv.email_sent_candidate_at ? ` (${iv.email_sent_candidate_at.slice(0, 16)})` : ''}
                        </span>
                      ) : (
                        <button type="button"
                          onClick={() => setEmailModal({ id: iv.id, target: 'candidate' })}
                          className="text-[11px] px-2 py-1 rounded border border-teal-200 text-teal-600 hover:bg-teal-50">
                          Send to Candidate
                        </button>
                      )}
                    </div>
                  )}
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
                    className="text-[11px] px-2 py-1 rounded border border-red-200 text-red-500 hover:bg-red-50">
                    Delete
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
    </div>
  )
}
