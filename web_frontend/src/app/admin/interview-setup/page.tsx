'use client'

/**
 * /admin/interview-setup — 인터뷰 세팅 위저드 (원클릭 자동화)
 * 3단계: ① 후보자 선택 → ② 구인처 매칭 → ③ 일정 확정 & 발송
 * 기존 API만 사용, 백엔드 변경 0건
 */

import { Suspense, useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import AdminAuth from '@/components/admin/AdminAuth'
import { API_URL } from '@/lib/api'

/* ── Types ── */
interface CandidateResult {
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
  _region_match: boolean
  _target_match: boolean
  _already_sent: boolean
  _match_score: number
}

interface ConfirmResult {
  id: number
  meet_link: string
  gcal_error: string | null
  email_errors: string[]
}

/* ── Meet Room Pool (fallback) ── */
const DEFAULT_MEET_POOL = [
  'https://meet.google.com/kmt-ydhj-fmf',
  'https://meet.google.com/abc-defg-hij',
  'https://meet.google.com/xyz-uvwx-rst',
  'https://meet.google.com/qwe-rtyp-asd',
  'https://meet.google.com/mnb-vcxz-lkj',
]

function getDefaultDate(): string {
  const d = new Date()
  let added = 0
  while (added < 3) {
    d.setDate(d.getDate() + 1)
    const day = d.getDay()
    if (day !== 0 && day !== 6) added++
  }
  return d.toISOString().slice(0, 10)
}

/* ── Step Bar ── */
function StepBar({ step }: { step: number }) {
  const steps = [
    { num: 1, label: '후보자 선택' },
    { num: 2, label: '구인처 매칭' },
    { num: 3, label: '일정 확정' },
  ]
  return (
    <div className="flex items-center justify-center gap-1 mb-8">
      {steps.map((s, i) => (
        <div key={s.num} className="flex items-center">
          <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-[13px] font-semibold transition-all ${
            step === s.num
              ? 'bg-[#0071e3] text-white shadow-sm'
              : step > s.num
                ? 'bg-green-100 text-green-700'
                : 'bg-[#f5f5f7] text-[#86868b]'
          }`}>
            <span className="w-5 h-5 flex items-center justify-center rounded-full text-[11px] font-bold bg-white/20">
              {step > s.num ? '\u2713' : s.num}
            </span>
            {s.label}
          </div>
          {i < steps.length - 1 && (
            <div className={`w-8 h-px mx-1 ${step > s.num ? 'bg-green-300' : 'bg-[#d2d2d7]'}`} />
          )}
        </div>
      ))}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════ */
export default function InterviewSetupPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#f5f5f7] flex items-center justify-center text-[#86868b]">Loading...</div>}>
      <InterviewSetupInner />
    </Suspense>
  )
}

function InterviewSetupInner() {
  const { authed, login, signedFetch, adminFetch, waking } = useAdminAuth()
  const searchParams = useSearchParams()

  /* ── State ── */
  const [step, setStep] = useState(1)

  // Step 1
  const [searchQ, setSearchQ] = useState('')
  const [candidates, setCandidates] = useState<CandidateResult[]>([])
  const [candidate, setCandidate] = useState<CandidateResult | null>(null)
  const [searchLoading, setSearchLoading] = useState(false)

  // Step 2
  const [matched, setMatched] = useState<Employer[]>([])
  const [unmatched, setUnmatched] = useState<Employer[]>([])
  const [showUnmatched, setShowUnmatched] = useState(false)
  const [selectedEmployer, setSelectedEmployer] = useState<Employer | null>(null)
  const [matchLoading, setMatchLoading] = useState(false)

  // Step 3
  const [interviewDate, setInterviewDate] = useState(getDefaultDate)
  const [interviewTime, setInterviewTime] = useState('10:00')
  const [duration, setDuration] = useState(20)
  const [notes, setNotes] = useState('')
  const [confirming, setConfirming] = useState(false)
  const [result, setResult] = useState<ConfirmResult | null>(null)

  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  /* ── URL param auto-load ── */
  useEffect(() => {
    const cid = searchParams.get('candidate')
    if (cid && authed) {
      loadCandidateById(cid)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, authed])

  /* ── Candidate Search ── */
  const searchCandidates = useCallback(async (q: string) => {
    if (!q.trim()) { setCandidates([]); return }
    setSearchLoading(true)
    setError(null)
    try {
      const res = await adminFetch(`${API_URL}/api/admin/candidates?search=${encodeURIComponent(q)}&limit=20&status=active`)
      if (!res.ok) throw new Error(`Error ${res.status}`)
      const j = await res.json()
      const rows = j.data?.rows || j.data || []
      setCandidates(Array.isArray(rows) ? rows : [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed')
    } finally {
      setSearchLoading(false)
    }
  }, [adminFetch])

  const loadCandidateById = useCallback(async (cid: string) => {
    setSearchLoading(true)
    setError(null)
    try {
      const res = await adminFetch(`${API_URL}/api/admin/candidates?search=${encodeURIComponent(cid)}&limit=5`)
      if (!res.ok) throw new Error(`Error ${res.status}`)
      const j = await res.json()
      const rows = j.data?.rows || j.data || []
      const found = (Array.isArray(rows) ? rows : []).find((r: CandidateResult) => r.candidate_id === cid)
      if (found) {
        selectCandidate(found)
      } else {
        setError(`Candidate ${cid} not found`)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Load failed')
    } finally {
      setSearchLoading(false)
    }
  }, [adminFetch]) // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Select Candidate → Go to Step 2 ── */
  const selectCandidate = (c: CandidateResult) => {
    setCandidate(c)
    setStep(2)
    setCandidates([])
    setSearchQ('')
    fetchMatching(c.candidate_id)
  }

  /* ── Matching ── */
  const fetchMatching = useCallback(async (cid: string) => {
    setMatchLoading(true)
    setError(null)
    try {
      const res = await adminFetch(`${API_URL}/api/admin/matching/employers?candidate_id=${encodeURIComponent(cid)}`)
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(j.detail || `Error ${res.status}`)
      }
      const j = await res.json()
      setMatched(j.data?.matched || [])
      setUnmatched(j.data?.unmatched || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Matching failed')
    } finally {
      setMatchLoading(false)
    }
  }, [adminFetch])

  /* ── Select Employer → Go to Step 3 ── */
  const selectEmployerAndProceed = (emp: Employer) => {
    setSelectedEmployer(emp)
    setStep(3)
    setInterviewDate(getDefaultDate())
  }

  /* ── Confirm Interview ── */
  const handleConfirm = async () => {
    if (!candidate || !selectedEmployer) return
    setConfirming(true)
    setError(null)
    setResult(null)
    try {
      const res = await signedFetch(`${API_URL}/api/admin/interview/confirm`, {
        method: 'POST',
        body: JSON.stringify({
          candidate_id: candidate.candidate_id,
          inquiry_id: selectedEmployer.id,
          interview_date: interviewDate,
          interview_time: interviewTime,
          duration_minutes: duration,
          notes: notes,
        }),
      })
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(j.detail || j.message || `Error ${res.status}`)
      }
      const j = await res.json()
      const data = j.data as ConfirmResult

      // GCal 실패 시 Meet pool fallback
      if (data.gcal_error && !data.meet_link) {
        const pool = DEFAULT_MEET_POOL
        const fallbackLink = pool[Math.floor(Math.random() * pool.length)]
        data.meet_link = fallbackLink
        // PATCH meet_link
        await signedFetch(`${API_URL}/api/admin/interviews/${data.id}`, {
          method: 'PATCH',
          body: JSON.stringify({ meet_link: fallbackLink }),
        }).catch(() => {})
      }

      setResult(data)
      setMsg('Interview confirmed successfully')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Confirm failed')
    } finally {
      setConfirming(false)
    }
  }

  /* ── Reset ── */
  const resetAll = () => {
    setStep(1)
    setCandidate(null)
    setSelectedEmployer(null)
    setMatched([])
    setUnmatched([])
    setResult(null)
    setError(null)
    setMsg(null)
    setNotes('')
    setSearchQ('')
    setCandidates([])
  }

  /* ── Debounced search ── */
  useEffect(() => {
    if (step !== 1 || !searchQ.trim()) return
    const t = setTimeout(() => searchCandidates(searchQ), 300)
    return () => clearTimeout(t)
  }, [searchQ, step, searchCandidates])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-[22px] font-bold text-[#1d1d1f] tracking-tight">Interview Setup</h1>
            <p className="text-[13px] text-[#86868b] mt-0.5">
              {result ? 'Interview confirmed' : 'One-click interview automation'}
            </p>
          </div>
          {step > 1 && !result && (
            <button type="button" onClick={resetAll}
              className="text-[13px] text-[#0071e3] hover:underline">
              Start Over
            </button>
          )}
        </div>

        {/* Step Bar */}
        {!result && <StepBar step={step} />}

        {/* Error / Success */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 mb-4 text-[13px] text-red-700">
            {error}
          </div>
        )}

        {/* ═══ STEP 1: Candidate Search ═══ */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="bg-white rounded-2xl border border-[#e5e5e7] p-6">
              <h2 className="text-[16px] font-semibold text-[#1d1d1f] mb-4">Search Candidate</h2>
              <input
                type="text"
                value={searchQ}
                onChange={e => setSearchQ(e.target.value)}
                placeholder="Search by name, nationality, or candidate ID..."
                className="w-full px-4 py-3 rounded-xl border border-[#d2d2d7] text-[14px] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 focus:border-[#0071e3]"
                autoFocus
              />
              {searchLoading && (
                <p className="text-[13px] text-[#86868b] mt-3 animate-pulse">Searching...</p>
              )}
            </div>

            {/* Search Results */}
            {candidates.length > 0 && (
              <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden">
                <div className="px-5 py-3 border-b border-[#e5e5e7] bg-[#fafafa]">
                  <h3 className="text-[13px] font-semibold text-[#86868b]">
                    {candidates.length} candidate(s) found
                  </h3>
                </div>
                <div className="divide-y divide-[#f5f5f7] max-h-[400px] overflow-y-auto">
                  {candidates.map(c => (
                    <button
                      key={c.candidate_id}
                      type="button"
                      onClick={() => selectCandidate(c)}
                      className="w-full flex items-center gap-4 px-5 py-3.5 hover:bg-[#0071e3]/5 transition-colors text-left"
                    >
                      {c.photo_url ? (
                        <img src={c.photo_url} alt="" className="w-11 h-11 rounded-full object-cover border border-[#e5e5e7] shrink-0" />
                      ) : (
                        <div className="w-11 h-11 rounded-full bg-[#f5f5f7] flex items-center justify-center text-[16px] font-bold text-[#86868b] shrink-0">
                          {(c.full_name || '?')[0]}
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[14px] font-semibold text-[#1d1d1f] truncate">{c.full_name || 'Unknown'}</span>
                          <span className="text-[11px] text-[#86868b]">{c.candidate_id}</span>
                        </div>
                        <div className="flex items-center gap-2 mt-0.5 text-[12px] text-[#86868b]">
                          <span>{c.nationality || '—'}</span>
                          {c.target && <><span className="text-[#d2d2d7]">|</span><span>{c.target}</span></>}
                          {c.area_prefs && <><span className="text-[#d2d2d7]">|</span><span>{c.area_prefs}</span></>}
                        </div>
                      </div>
                      <span className="text-[#0071e3] text-[13px] shrink-0">Select</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ═══ STEP 2: Employer Matching ═══ */}
        {step === 2 && candidate && (
          <div className="space-y-4">
            {/* Selected Candidate Card */}
            <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
              <div className="flex items-center gap-4">
                {candidate.photo_url ? (
                  <img src={candidate.photo_url} alt="" className="w-14 h-14 rounded-full object-cover border-2 border-[#e5e5e7]" />
                ) : (
                  <div className="w-14 h-14 rounded-full bg-[#f5f5f7] flex items-center justify-center text-[20px] font-bold text-[#86868b]">
                    {(candidate.full_name || '?')[0]}
                  </div>
                )}
                <div className="flex-1">
                  <h3 className="text-[16px] font-bold text-[#1d1d1f]">{candidate.full_name}</h3>
                  <div className="flex items-center gap-2 mt-0.5 text-[12px] text-[#86868b] flex-wrap">
                    <span>{candidate.nationality}</span>
                    {candidate.target && <><span className="text-[#d2d2d7]">|</span><span>Target: {candidate.target}</span></>}
                    {candidate.area_prefs && <><span className="text-[#d2d2d7]">|</span><span>Area: {candidate.area_prefs}</span></>}
                  </div>
                </div>
                <button type="button" onClick={() => { setStep(1); setCandidate(null); setMatched([]); setUnmatched([]) }}
                  className="text-[12px] text-[#86868b] hover:text-[#1d1d1f] px-3 py-1.5 border border-[#e5e5e7] rounded-lg shrink-0">
                  Change
                </button>
              </div>
            </div>

            {/* Matched Employers */}
            <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden">
              <div className="px-5 py-3 border-b border-[#e5e5e7] bg-[#fafafa] flex items-center justify-between">
                <h3 className="text-[14px] font-semibold text-[#1d1d1f]">
                  Matched Employers ({matched.length})
                </h3>
                <span className="text-[12px] text-[#86868b]">Select one for interview</span>
              </div>
              <div className="divide-y divide-[#f5f5f7] max-h-[450px] overflow-y-auto">
                {matchLoading ? (
                  <div className="py-12 text-center text-[13px] text-[#86868b] animate-pulse">Loading matched employers...</div>
                ) : matched.length === 0 ? (
                  <div className="py-12 text-center text-[13px] text-[#86868b]">No matched employers found</div>
                ) : (
                  matched.map(emp => (
                    <button
                      key={emp.id}
                      type="button"
                      onClick={() => selectEmployerAndProceed(emp)}
                      className={`w-full flex items-center gap-3 px-5 py-3.5 transition-colors text-left ${
                        selectedEmployer?.id === emp.id ? 'bg-[#0071e3]/10' : 'hover:bg-[#fafafa]'
                      }`}
                    >
                      <div className="w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 ${
                        selectedEmployer?.id === emp.id ? 'border-[#0071e3] bg-[#0071e3]' : 'border-[#d2d2d7]'
                      }">
                        {selectedEmployer?.id === emp.id && (
                          <span className="text-white text-[10px]">{'\u2713'}</span>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[14px] font-medium text-[#1d1d1f] truncate">{emp.school_name || 'Unknown'}</span>
                          {emp._match_score === 2 && (
                            <span className="text-[10px] px-1.5 py-0.5 bg-green-100 text-green-700 rounded-full font-medium">Full Match</span>
                          )}
                          {emp._region_match && !emp._target_match && (
                            <span className="text-[10px] px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded-full font-medium">Region</span>
                          )}
                          {emp._target_match && !emp._region_match && (
                            <span className="text-[10px] px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded-full font-medium">Target</span>
                          )}
                          {emp._already_sent && (
                            <span className="text-[10px] px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded-full font-medium">Profile Sent</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5 text-[12px] text-[#86868b]">
                          <span>{emp.location || '—'}</span>
                          {emp.teaching_age && <><span className="text-[#d2d2d7]">|</span><span>{emp.teaching_age}</span></>}
                          {emp.contact_name && <><span className="text-[#d2d2d7]">|</span><span>{emp.contact_name}</span></>}
                        </div>
                      </div>
                      <span className="text-[#0071e3] text-[13px] font-medium shrink-0">Select</span>
                    </button>
                  ))
                )}
              </div>
            </div>

            {/* Unmatched Toggle */}
            {unmatched.length > 0 && (
              <>
                <button
                  type="button"
                  onClick={() => setShowUnmatched(!showUnmatched)}
                  className="text-[13px] text-[#86868b] hover:text-[#1d1d1f] transition-colors"
                >
                  {showUnmatched ? 'Hide' : 'Show'} Unmatched ({unmatched.length})
                </button>
                {showUnmatched && (
                  <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden">
                    <div className="px-5 py-3 border-b border-[#e5e5e7] bg-[#fafafa]">
                      <h3 className="text-[13px] font-semibold text-[#86868b]">Unmatched ({unmatched.length})</h3>
                    </div>
                    <div className="divide-y divide-[#f5f5f7] max-h-[300px] overflow-y-auto">
                      {unmatched.map(emp => (
                        <button
                          key={emp.id}
                          type="button"
                          onClick={() => selectEmployerAndProceed(emp)}
                          className="w-full flex items-center gap-3 px-5 py-3 hover:bg-[#fafafa] transition-colors text-left"
                        >
                          <div className="flex-1 min-w-0">
                            <span className="text-[13px] text-[#424245]">{emp.school_name || 'Unknown'}</span>
                            <span className="text-[12px] text-[#86868b] ml-2">{emp.location || ''}</span>
                          </div>
                          <span className="text-[#0071e3] text-[12px] shrink-0">Select</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ═══ STEP 3: Schedule & Confirm ═══ */}
        {step === 3 && candidate && selectedEmployer && !result && (
          <div className="space-y-4">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4">
                <div className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider mb-2">Candidate</div>
                <div className="flex items-center gap-3">
                  {candidate.photo_url ? (
                    <img src={candidate.photo_url} alt="" className="w-10 h-10 rounded-full object-cover border border-[#e5e5e7]" />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-[#f5f5f7] flex items-center justify-center text-[14px] font-bold text-[#86868b]">
                      {(candidate.full_name || '?')[0]}
                    </div>
                  )}
                  <div>
                    <p className="text-[14px] font-semibold text-[#1d1d1f]">{candidate.full_name}</p>
                    <p className="text-[12px] text-[#86868b]">{candidate.nationality} / {candidate.target || '—'}</p>
                  </div>
                </div>
              </div>
              <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4">
                <div className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider mb-2">Employer</div>
                <p className="text-[14px] font-semibold text-[#1d1d1f]">{selectedEmployer.school_name || 'Unknown'}</p>
                <p className="text-[12px] text-[#86868b]">{selectedEmployer.location} / {selectedEmployer.contact_name || '—'}</p>
                <button type="button" onClick={() => setStep(2)}
                  className="text-[11px] text-[#0071e3] hover:underline mt-1">
                  Change employer
                </button>
              </div>
            </div>

            {/* Schedule Form */}
            <div className="bg-white rounded-2xl border border-[#e5e5e7] p-6">
              <h2 className="text-[16px] font-semibold text-[#1d1d1f] mb-5">Schedule Interview</h2>

              <div className="grid grid-cols-2 gap-4 mb-5">
                <div>
                  <label className="text-[12px] font-semibold text-[#86868b] block mb-1.5">Date</label>
                  <input
                    type="date"
                    value={interviewDate}
                    onChange={e => setInterviewDate(e.target.value)}
                    className="w-full px-3 py-2.5 border border-[#d2d2d7] rounded-xl text-[14px] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 focus:border-[#0071e3]"
                  />
                </div>
                <div>
                  <label className="text-[12px] font-semibold text-[#86868b] block mb-1.5">Time (KST)</label>
                  <input
                    type="time"
                    value={interviewTime}
                    onChange={e => setInterviewTime(e.target.value)}
                    className="w-full px-3 py-2.5 border border-[#d2d2d7] rounded-xl text-[14px] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 focus:border-[#0071e3]"
                  />
                </div>
              </div>

              <div className="mb-5">
                <label className="text-[12px] font-semibold text-[#86868b] block mb-2">Duration</label>
                <div className="flex gap-2">
                  {[15, 20, 30].map(d => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setDuration(d)}
                      className={`px-5 py-2 rounded-xl text-[13px] font-semibold border transition-colors ${
                        duration === d
                          ? 'bg-[#0071e3]/10 text-[#0071e3] border-[#0071e3]/30'
                          : 'bg-white text-[#424245] border-[#d2d2d7] hover:bg-[#f5f5f7]'
                      }`}
                    >
                      {d} min
                    </button>
                  ))}
                </div>
              </div>

              <div className="mb-5">
                <label className="text-[12px] font-semibold text-[#86868b] block mb-1.5">Notes (optional)</label>
                <textarea
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  placeholder="Additional notes for this interview..."
                  rows={2}
                  className="w-full px-3 py-2.5 border border-[#d2d2d7] rounded-xl text-[14px] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 focus:border-[#0071e3] resize-none"
                />
              </div>

              {/* What will happen */}
              <div className="bg-[#f5f5f7] rounded-xl p-4 mb-5 text-[12px] text-[#86868b] space-y-1">
                <p className="font-semibold text-[#1d1d1f] text-[13px] mb-2">What happens on confirm:</p>
                <p>{'\u2713'} Google Calendar event created (Meet link auto-generated)</p>
                <p>{'\u2713'} Interview record saved to database</p>
                <p>{'\u2713'} Guide email sent to candidate with Meet link</p>
                <p>{'\u2713'} Guide email sent to employer with Meet link</p>
              </div>

              {/* Confirm Button */}
              <button
                type="button"
                onClick={handleConfirm}
                disabled={confirming}
                className="w-full py-3.5 bg-[#0071e3] text-white text-[15px] font-semibold rounded-2xl hover:bg-[#0077ED] disabled:opacity-50 transition-colors"
              >
                {confirming ? 'Setting up interview...' : 'Confirm Interview'}
              </button>
            </div>
          </div>
        )}

        {/* ═══ RESULT ═══ */}
        {result && (
          <div className="space-y-4">
            <div className="bg-white rounded-2xl border border-green-200 p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center text-green-600 text-[20px] shrink-0">
                  {'\u2713'}
                </div>
                <div>
                  <h2 className="text-[17px] font-bold text-[#1d1d1f]">Interview #{result.id} Confirmed</h2>
                  <p className="text-[13px] text-[#86868b]">{msg}</p>
                </div>
              </div>

              <div className="space-y-3 text-[13px]">
                <div className="flex justify-between py-2 border-b border-[#f5f5f7]">
                  <span className="text-[#86868b]">Candidate</span>
                  <span className="text-[#1d1d1f] font-medium">{candidate?.full_name}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-[#f5f5f7]">
                  <span className="text-[#86868b]">Employer</span>
                  <span className="text-[#1d1d1f] font-medium">{selectedEmployer?.school_name}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-[#f5f5f7]">
                  <span className="text-[#86868b]">Date / Time</span>
                  <span className="text-[#1d1d1f] font-medium">{interviewDate} {interviewTime} KST</span>
                </div>
                <div className="flex justify-between py-2 border-b border-[#f5f5f7]">
                  <span className="text-[#86868b]">Duration</span>
                  <span className="text-[#1d1d1f] font-medium">{duration} min</span>
                </div>
                {result.meet_link && (
                  <div className="flex justify-between py-2 border-b border-[#f5f5f7]">
                    <span className="text-[#86868b]">Meet Link</span>
                    <a href={result.meet_link} target="_blank" rel="noopener noreferrer"
                      className="text-[#0071e3] font-medium hover:underline truncate max-w-[250px]">
                      {result.meet_link}
                    </a>
                  </div>
                )}
              </div>

              {/* Status badges */}
              <div className="flex flex-wrap gap-2 mt-4">
                {result.gcal_error ? (
                  <span className="text-[11px] px-2 py-1 bg-orange-100 text-orange-700 rounded-full">
                    GCal: {result.gcal_error.length > 30 ? 'Fallback to Meet Pool' : result.gcal_error}
                  </span>
                ) : (
                  <span className="text-[11px] px-2 py-1 bg-green-100 text-green-700 rounded-full">
                    Google Calendar OK
                  </span>
                )}
                {result.email_errors.length === 0 ? (
                  <span className="text-[11px] px-2 py-1 bg-green-100 text-green-700 rounded-full">
                    Emails sent to both parties
                  </span>
                ) : (
                  <span className="text-[11px] px-2 py-1 bg-red-100 text-red-700 rounded-full">
                    Email errors: {result.email_errors.join(', ')}
                  </span>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <a href="/admin/interviews"
                className="flex-1 py-3 text-center text-[14px] font-medium text-[#424245] bg-white border border-[#d2d2d7] rounded-2xl hover:bg-[#f5f5f7] transition-colors">
                View All Interviews
              </a>
              <button
                type="button"
                onClick={resetAll}
                className="flex-1 py-3 text-[14px] font-semibold text-white bg-[#0071e3] rounded-2xl hover:bg-[#0077ED] transition-colors"
              >
                New Interview Setup
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
