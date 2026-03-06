'use client'

import { Suspense, useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

/* ── Types ── */
interface CandidateProfile {
  candidate_id: string
  full_name: string
  nationality: string
  target: string
  target_age: string
  area_prefs: string
  experience: string
  education_level: string
  certification: string
  visa_type: string
  start_date: string
  photo_url: string
  dob: string
  gender: string
}

interface Employer {
  id: number
  school_name: string
  location: string
  email: string
  contact_name: string
  teaching_age: string
  phone: string
  vacancies: string
  _region_match: boolean
  _target_match: boolean
  _already_sent: boolean
  _match_score: number
}

/* ── Helpers ── */
function calcAge(dob: string | null): string {
  if (!dob) return ''
  const d = new Date(dob)
  if (isNaN(d.getTime())) return ''
  const now = new Date()
  let age = now.getFullYear() - d.getFullYear()
  if (now.getMonth() < d.getMonth() || (now.getMonth() === d.getMonth() && now.getDate() < d.getDate())) age--
  return String(age)
}

/* ═══════════════════════════════════════════════════════════════════ */
export default function MatchingPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#f5f5f7] flex items-center justify-center text-[#86868b]">Loading...</div>}>
      <MatchingPageInner />
    </Suspense>
  )
}

function MatchingPageInner() {
  const { authed, login, signedFetch, adminFetch, waking } = useAdminAuth()
  const searchParams = useSearchParams()

  /* State */
  const [candidateId, setCandidateId] = useState('')
  const [candidate, setCandidate] = useState<CandidateProfile | null>(null)
  const [matched, setMatched] = useState<Employer[]>([])
  const [unmatched, setUnmatched] = useState<Employer[]>([])
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [showUnmatched, setShowUnmatched] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [searchQ, setSearchQ] = useState('')

  /* URL param auto-load */
  useEffect(() => {
    const cid = searchParams.get('candidate')
    if (cid && authed) {
      setCandidateId(cid)
    }
  }, [searchParams, authed])

  /* Auto-fetch when candidateId changes */
  useEffect(() => {
    if (candidateId && authed) {
      fetchMatching(candidateId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateId, authed])

  /* ── Fetch matching ── */
  const fetchMatching = useCallback(async (cid: string) => {
    setLoading(true)
    setError(null)
    setMsg(null)
    setSelected(new Set())
    try {
      const res = await adminFetch(`${API_URL}/api/admin/matching/employers?candidate_id=${encodeURIComponent(cid)}`)
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(j.detail || j.error || `Error ${res.status}`)
      }
      const j = await res.json()
      const data = j.data
      setCandidate(data.candidate)
      setMatched(data.matched || [])
      setUnmatched(data.unmatched || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [adminFetch])

  /* ── Toggle selection ── */
  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectAllMatched = () => {
    const notSent = matched.filter(e => !e._already_sent).map(e => e.id)
    setSelected(new Set(notSent))
  }

  const clearSelection = () => setSelected(new Set())

  /* ── Send profiles (SECURITY: 보안 엔드포인트 사용) ── */
  const handleSend = async () => {
    if (selected.size === 0 || !candidate) return
    setSending(true)
    setError(null)
    setMsg(null)
    try {
      // SECURITY: 개별 발송 + PII 스캔 + Rate limit 적용 엔드포인트
      const res = await signedFetch(`${API_URL}/api/admin/matching/send-profile-secure`, {
        method: 'POST',
        body: JSON.stringify({
          candidate_id: candidate.candidate_id,
          employer_ids: Array.from(selected),
        }),
      })
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(j.detail || j.error || `Error ${res.status}`)
      }
      const j = await res.json()
      const data = j.data || {}
      setMsg(`${data.sent || 0}건 발송 완료, ${data.failed || 0}건 실패`)
      // Refresh to update _already_sent
      fetchMatching(candidate.candidate_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Send failed')
    } finally {
      setSending(false)
    }
  }

  /* ── Filter employers by search ── */
  const filterEmployers = (list: Employer[]) => {
    if (!searchQ.trim()) return list
    const q = searchQ.toLowerCase()
    return list.filter(e =>
      (e.school_name || '').toLowerCase().includes(q) ||
      (e.location || '').toLowerCase().includes(q) ||
      (e.email || '').toLowerCase().includes(q) ||
      (e.teaching_age || '').toLowerCase().includes(q)
    )
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-[22px] font-bold text-[#1d1d1f] tracking-tight">Profile Matching</h1>
            <p className="text-[13px] text-[#86868b] mt-1">Match candidates with employers by region &amp; target</p>
          </div>
        </div>

        {/* Candidate ID Input */}
        {!candidate && (
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-6 mb-6">
            <label className="block text-[13px] font-medium text-[#1d1d1f] mb-2">Candidate ID</label>
            <div className="flex gap-3">
              <input
                type="text"
                value={candidateId}
                onChange={e => setCandidateId(e.target.value)}
                placeholder="cnd_xxxxxxxx"
                className="flex-1 px-4 py-2.5 rounded-xl border border-[#d2d2d7] text-[14px] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 focus:border-[#0071e3]"
                onKeyDown={e => { if (e.key === 'Enter' && candidateId) fetchMatching(candidateId) }}
              />
              <button
                type="button"
                onClick={() => candidateId && fetchMatching(candidateId)}
                disabled={loading || !candidateId}
                className="px-6 py-2.5 bg-[#0071e3] text-white text-[14px] font-medium rounded-xl hover:bg-[#0077ED] disabled:opacity-40 transition-colors"
              >
                {loading ? 'Loading...' : 'Search'}
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 mb-4 text-[13px] text-red-700">
            {error}
          </div>
        )}
        {msg && (
          <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 mb-4 text-[13px] text-green-700">
            {msg}
          </div>
        )}

        {candidate && (
          <div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-6">
            {/* ── Left: Candidate Profile ── */}
            <div className="space-y-4">
              <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
                <div className="flex items-center gap-4 mb-4">
                  {candidate.photo_url ? (
                    <img
                      src={candidate.photo_url}
                      alt=""
                      className="w-16 h-16 rounded-full object-cover border-2 border-[#e5e5e7]"
                    />
                  ) : (
                    <div className="w-16 h-16 rounded-full bg-[#f5f5f7] flex items-center justify-center text-[22px] font-bold text-[#86868b]">
                      {(candidate.full_name || '?')[0]}
                    </div>
                  )}
                  <div>
                    <h2 className="text-[17px] font-bold text-[#1d1d1f]">{candidate.full_name || 'Unknown'}</h2>
                    <p className="text-[13px] text-[#86868b]">{candidate.candidate_id}</p>
                  </div>
                </div>

                <div className="space-y-2 text-[13px]">
                  {[
                    ['Nationality', candidate.nationality],
                    ['Age', calcAge(candidate.dob)],
                    ['Gender', candidate.gender],
                    ['Target', [candidate.target, candidate.target_age].filter(Boolean).join(' / ')],
                    ['Area Prefs', candidate.area_prefs],
                    ['Experience', candidate.experience],
                    ['Education', candidate.education_level],
                    ['Certification', candidate.certification],
                    ['Visa', candidate.visa_type],
                    ['Start Date', candidate.start_date],
                  ].map(([label, val]) => (
                    <div key={label} className="flex justify-between py-1 border-b border-[#f5f5f7] last:border-0">
                      <span className="text-[#86868b]">{label}</span>
                      <span className="text-[#1d1d1f] font-medium text-right max-w-[200px] truncate">{val || '—'}</span>
                    </div>
                  ))}
                </div>

                <button
                  type="button"
                  onClick={() => { setCandidate(null); setCandidateId(''); setMatched([]); setUnmatched([]) }}
                  className="mt-4 w-full py-2 text-[13px] text-[#86868b] hover:text-[#1d1d1f] border border-[#e5e5e7] rounded-xl transition-colors"
                >
                  Change Candidate
                </button>
              </div>

              {/* Match Summary */}
              <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
                <h3 className="text-[14px] font-semibold text-[#1d1d1f] mb-3">Match Summary</h3>
                <div className="grid grid-cols-2 gap-3 text-center">
                  <div className="bg-green-50 rounded-xl py-3">
                    <div className="text-[22px] font-bold text-green-600">{matched.length}</div>
                    <div className="text-[11px] text-green-600/70">Matched</div>
                  </div>
                  <div className="bg-gray-50 rounded-xl py-3">
                    <div className="text-[22px] font-bold text-[#86868b]">{unmatched.length}</div>
                    <div className="text-[11px] text-[#86868b]">Unmatched</div>
                  </div>
                </div>
                <div className="mt-3 text-center">
                  <span className="text-[13px] font-semibold text-[#0071e3]">{selected.size}</span>
                  <span className="text-[13px] text-[#86868b]"> selected</span>
                </div>
              </div>

              {/* Send Button */}
              <button
                type="button"
                onClick={() => selected.size > 0 && setShowPreview(true)}
                disabled={selected.size === 0 || sending}
                className="w-full py-3 bg-[#0071e3] text-white text-[15px] font-semibold rounded-2xl hover:bg-[#0077ED] disabled:opacity-40 transition-colors"
              >
                {sending ? 'Sending...' : `Send Profile (${selected.size})`}
              </button>
            </div>

            {/* ── Right: Employer List ── */}
            <div className="space-y-4">
              {/* Controls */}
              <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4 flex flex-col sm:flex-row items-start sm:items-center gap-3">
                <input
                  type="text"
                  value={searchQ}
                  onChange={e => setSearchQ(e.target.value)}
                  placeholder="Search employers..."
                  className="flex-1 px-4 py-2 rounded-xl border border-[#d2d2d7] text-[13px] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 w-full sm:w-auto"
                />
                <div className="flex gap-2 flex-wrap">
                  <button
                    type="button"
                    onClick={selectAllMatched}
                    className="px-3 py-1.5 text-[12px] font-medium bg-[#0071e3]/10 text-[#0071e3] rounded-lg hover:bg-[#0071e3]/20 transition-colors"
                  >
                    Select All Matched
                  </button>
                  <button
                    type="button"
                    onClick={clearSelection}
                    className="px-3 py-1.5 text-[12px] font-medium bg-gray-100 text-[#424245] rounded-lg hover:bg-gray-200 transition-colors"
                  >
                    Clear
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowUnmatched(!showUnmatched)}
                    className={`px-3 py-1.5 text-[12px] font-medium rounded-lg transition-colors ${
                      showUnmatched ? 'bg-[#424245] text-white' : 'bg-gray-100 text-[#424245] hover:bg-gray-200'
                    }`}
                  >
                    {showUnmatched ? 'Hide' : 'Show'} Unmatched ({unmatched.length})
                  </button>
                </div>
              </div>

              {/* Matched Employers */}
              <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden">
                <div className="px-5 py-3 border-b border-[#e5e5e7] bg-[#fafafa]">
                  <h3 className="text-[14px] font-semibold text-[#1d1d1f]">
                    Matched Employers ({filterEmployers(matched).length})
                  </h3>
                </div>
                <div className="divide-y divide-[#f5f5f7] max-h-[500px] overflow-y-auto">
                  {loading ? (
                    <div className="py-12 text-center text-[13px] text-[#86868b]">Loading...</div>
                  ) : filterEmployers(matched).length === 0 ? (
                    <div className="py-12 text-center text-[13px] text-[#86868b]">No matched employers</div>
                  ) : (
                    filterEmployers(matched).map(emp => (
                      <EmployerRow
                        key={emp.id}
                        emp={emp}
                        checked={selected.has(emp.id)}
                        onToggle={() => toggleSelect(emp.id)}
                      />
                    ))
                  )}
                </div>
              </div>

              {/* Unmatched Employers */}
              {showUnmatched && (
                <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden">
                  <div className="px-5 py-3 border-b border-[#e5e5e7] bg-[#fafafa]">
                    <h3 className="text-[14px] font-semibold text-[#86868b]">
                      Unmatched Employers ({filterEmployers(unmatched).length})
                    </h3>
                  </div>
                  <div className="divide-y divide-[#f5f5f7] max-h-[400px] overflow-y-auto">
                    {filterEmployers(unmatched).length === 0 ? (
                      <div className="py-8 text-center text-[13px] text-[#86868b]">No unmatched employers</div>
                    ) : (
                      filterEmployers(unmatched).map(emp => (
                        <EmployerRow
                          key={emp.id}
                          emp={emp}
                          checked={selected.has(emp.id)}
                          onToggle={() => toggleSelect(emp.id)}
                        />
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Send Preview Modal ── */}
        {showPreview && candidate && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[80vh] overflow-y-auto">
              <div className="p-6">
                <h3 className="text-[17px] font-bold text-[#1d1d1f] mb-4">Confirm Send</h3>

                <div className="bg-[#f5f5f7] rounded-xl p-4 mb-4 text-[13px]">
                  <p className="font-semibold text-[#1d1d1f] mb-2">Candidate: {candidate.full_name} ({candidate.candidate_id})</p>
                  <p className="text-[#86868b]">
                    Sending profile to <span className="font-semibold text-[#1d1d1f]">{selected.size}</span> employer(s)
                  </p>
                  <div className="mt-3 space-y-1 text-[11px] text-[#86868b]">
                    <p>&#x2713; PII (name, email, phone) will NOT be included</p>
                    <p>&#x2713; Each email sent individually (no CC/BCC)</p>
                    <p>&#x2713; Reply-To: bridgejobkr@gmail.com</p>
                    <p>&#x2713; Rate limit: 3s interval, 10/min, 200/day</p>
                    <p>&#x2713; PII auto-scan before each send</p>
                  </div>
                </div>

                <div className="space-y-1 max-h-[200px] overflow-y-auto mb-4">
                  {Array.from(selected).map(id => {
                    const emp = [...matched, ...unmatched].find(e => e.id === id)
                    if (!emp) return null
                    return (
                      <div key={id} className="flex items-center justify-between py-1.5 text-[12px]">
                        <span className="text-[#1d1d1f] truncate max-w-[250px]">{emp.school_name || 'Unknown'}</span>
                        <span className="text-[#86868b] ml-2 shrink-0">{emp.email}</span>
                      </div>
                    )
                  })}
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setShowPreview(false)}
                    className="flex-1 py-2.5 border border-[#d2d2d7] text-[14px] font-medium text-[#424245] rounded-xl hover:bg-[#f5f5f7] transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => { setShowPreview(false); handleSend() }}
                    disabled={sending}
                    className="flex-1 py-2.5 bg-[#0071e3] text-white text-[14px] font-semibold rounded-xl hover:bg-[#0077ED] disabled:opacity-40 transition-colors"
                  >
                    {sending ? 'Sending...' : 'Confirm Send'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Employer Row Component ── */
function EmployerRow({ emp, checked, onToggle }: { emp: Employer; checked: boolean; onToggle: () => void }) {
  return (
    <label
      className={`flex items-center gap-3 px-5 py-3 cursor-pointer transition-colors ${
        emp._already_sent ? 'bg-yellow-50/50' : checked ? 'bg-[#0071e3]/5' : 'hover:bg-[#fafafa]'
      }`}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={onToggle}
        disabled={emp._already_sent}
        className="w-4 h-4 rounded border-[#d2d2d7] text-[#0071e3] focus:ring-[#0071e3] shrink-0"
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[14px] font-medium text-[#1d1d1f] truncate">
            {emp.school_name || 'Unknown School'}
          </span>
          {emp._already_sent && (
            <span className="text-[10px] px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded-full font-medium shrink-0">
              Sent
            </span>
          )}
          {emp._match_score === 2 && (
            <span className="text-[10px] px-1.5 py-0.5 bg-green-100 text-green-700 rounded-full font-medium shrink-0">
              Full Match
            </span>
          )}
          {emp._region_match && !emp._target_match && (
            <span className="text-[10px] px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded-full font-medium shrink-0">
              Region
            </span>
          )}
          {emp._target_match && !emp._region_match && (
            <span className="text-[10px] px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded-full font-medium shrink-0">
              Target
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 mt-0.5 text-[12px] text-[#86868b]">
          <span>{emp.location || '—'}</span>
          <span>{emp.teaching_age || '—'}</span>
          <span className="truncate">{emp.email}</span>
        </div>
      </div>
    </label>
  )
}
