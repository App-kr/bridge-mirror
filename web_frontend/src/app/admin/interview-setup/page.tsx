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
  sheet_number: string
  full_name: string
  nationality: string
  email: string
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
  interview_time: string
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

/* ── Meet Room Pool ── */
const MEET_ROOMS = [
  { label: 'Room 1', code: 'kmt-ydhj-fmf' },
]

/** 풀에서 랜덤 Meet 링크 반환 */
function fallbackMeetLink(): string {
  return `https://meet.google.com/${MEET_ROOMS[0]?.code || 'kmt-ydhj-fmf'}`
}

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
  const [selectedRoom, setSelectedRoom] = useState(-1) // -1 = random
  const [emailSubject, setEmailSubject] = useState('')
  const [emailBody, setEmailBody] = useState('')
  const [confirming, setConfirming] = useState(false)
  const [result, setResult] = useState<ConfirmResult | null>(null)

  // Edit mode
  const [editing, setEditing] = useState(false)
  const [editDate, setEditDate] = useState('')
  const [editTime, setEditTime] = useState('')
  const [editDuration, setEditDuration] = useState(20)
  const [editNotes, setEditNotes] = useState('')
  const [editSaving, setEditSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  /* ── Generate email preview ── */
  const generateEmailPreview = useCallback((c: CandidateResult | null, date: string, time: string, dur: number, roomIdx: number) => {
    if (!c) return
    const firstName = (c.full_name || '').split(' ')[0] || c.full_name
    const meetUrl = roomIdx >= 0 && roomIdx < MEET_ROOMS.length ? `https://meet.google.com/${MEET_ROOMS[roomIdx].code}` : fallbackMeetLink()
    setEmailSubject(`[BRIDGE] Interview — ${firstName}`)
    setEmailBody(
      `Dear ${firstName},\n\nYour interview has been scheduled.\n\nDate: ${date}\nTime: ${time} KST\nDuration: ${dur} minutes\n\nMeet Link: ${meetUrl}\n\nPlease join 2-3 minutes early.\n\nBest regards,\nBRIDGE Recruitment`
    )
  }, [])

  // Update email preview when schedule changes
  useEffect(() => {
    if (step === 3 && candidate) {
      generateEmailPreview(candidate, interviewDate, interviewTime, duration, selectedRoom)
    }
  }, [step, candidate, interviewDate, interviewTime, duration, selectedRoom, generateEmailPreview])

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
      // candidate_id (cnd_) 검색은 profile-search, 이름 검색은 main API
      const isCidSearch = q.trim().startsWith('cnd_') || /^\d+$/.test(q.trim())
      if (isCidSearch) {
        // profile-search: candidate_id, nationality, location 검색 가능
        const res = await adminFetch(`${API_URL}/api/admin/candidates/profile-search?q=${encodeURIComponent(q)}&limit=20`)
        if (!res.ok) throw new Error(`Error ${res.status}`)
        const j = await res.json()
        const rows = j.data || []
        // profile-search는 full_name이 없음 → nationality로 대체 표시
        const mapped = (Array.isArray(rows) ? rows : []).map((r: Record<string, unknown>) => ({
          candidate_id: String(r.candidate_id || ''),
          sheet_number: String(r.sheet_number || ''),
          full_name: String(r.full_name || `#${r.sheet_number || '?'} (${r.nationality || '?'})`),
          nationality: String(r.nationality || ''),
          target: String(r.target || ''),
          target_age: String(r.target_age || ''),
          area_prefs: String(r.area_prefs || ''),
          experience: String(r.experience || ''),
          education_level: String(r.education_level || ''),
          certification: String(r.certification || ''),
          visa_type: String(r.visa_type || ''),
          start_date: String(r.start_date || ''),
          photo_url: String(r.photo_url || ''),
          dob: String(r.dob || ''),
          gender: String(r.gender || ''),
          email: String(r.email || ''),
          interview_time: String(r.interview_time || ''),
        } as CandidateResult))
        setCandidates(mapped)
      } else {
        // main API: full_name, email 검색 (암호화 필드)
        const res = await adminFetch(`${API_URL}/api/admin/candidates?search=${encodeURIComponent(q)}&limit=20&status=active`)
        if (!res.ok) throw new Error(`Error ${res.status}`)
        const j = await res.json()
        const rows = j.data?.candidates || []
        // main API renames candidate_id → id
        const mapped = (Array.isArray(rows) ? rows : []).map((r: Record<string, unknown>) => ({
          candidate_id: String(r.candidate_id || r.id || ''),
          sheet_number: String(r.sheet_number || ''),
          full_name: String(r.full_name || ''),
          nationality: String(r.nationality || ''),
          target: String(r.target || ''),
          target_age: String(r.target_age || ''),
          area_prefs: String(r.area_prefs || ''),
          experience: String(r.experience || ''),
          education_level: String(r.education_level || ''),
          certification: String(r.certification || ''),
          visa_type: String(r.visa_type || ''),
          start_date: String(r.start_date || ''),
          photo_url: String(r.photo_url || ''),
          dob: String(r.dob || ''),
          gender: String(r.gender || ''),
          email: String(r.email || ''),
          interview_time: String(r.interview_time || ''),
        } as CandidateResult))
        setCandidates(mapped)
      }
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
      // matching API로 직접 조회 — candidate_id 정확 매칭 + 매칭 데이터도 함께 로드
      const res = await adminFetch(`${API_URL}/api/admin/matching/employers?candidate_id=${encodeURIComponent(cid)}`)
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(j.detail || `Candidate ${cid} not found`)
      }
      const j = await res.json()
      const cand = j.data?.candidate
      if (cand) {
        setCandidate(cand)
        setMatched(j.data?.matched || [])
        setUnmatched(j.data?.unmatched || [])
        setCandidates([])
        setSearchQ('')
        if (cand.interview_time) setNotes(cand.interview_time)
        setStep(2) // 바로 Step 2 (매칭 데이터 이미 로드됨)
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
    // main API renames candidate_id → id, normalize it
    const normalized = { ...c, candidate_id: c.candidate_id || (c as unknown as Record<string, string>).id || '' }
    setCandidate(normalized)
    setStep(2)
    setCandidates([])
    setSearchQ('')
    // Pre-fill notes from candidate's interview_time preference
    if (normalized.interview_time) setNotes(normalized.interview_time)
    fetchMatching(normalized.candidate_id)
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

  /* ── Pick random meet room ── */
  const pickRandomRoom = () => {
    const idx = Math.floor(Math.random() * MEET_ROOMS.length)
    setSelectedRoom(idx)
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

      // GCal 실패 시 폴백 — 저장된 Meet 풀에서 선택
      if (data.gcal_error && !data.meet_link) {
        const fallbackLink = selectedRoom >= 0 && selectedRoom < MEET_ROOMS.length
          ? `https://meet.google.com/${MEET_ROOMS[selectedRoom].code}`
          : fallbackMeetLink()
        data.meet_link = fallbackLink
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

  /* ── Edit Interview ── */
  const startEdit = () => {
    setEditDate(interviewDate)
    setEditTime(interviewTime)
    setEditDuration(duration)
    setEditNotes(notes)
    setEditing(true)
    setError(null)
  }

  const saveEdit = async () => {
    if (!result) return
    setEditSaving(true)
    setError(null)
    try {
      const res = await signedFetch(`${API_URL}/api/admin/interviews/${result.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          interview_date: editDate,
          interview_time: editTime,
          duration_minutes: editDuration,
          notes: editNotes,
        }),
      })
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(j.detail || `Error ${res.status}`)
      }
      // Apply changes locally
      setInterviewDate(editDate)
      setInterviewTime(editTime)
      setDuration(editDuration)
      setNotes(editNotes)
      setEditing(false)
      setMsg('Schedule updated successfully')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Update failed')
    } finally {
      setEditSaving(false)
    }
  }

  /* ── Delete Interview ── */
  const handleDelete = async () => {
    if (!result) return
    if (!window.confirm(`Interview #${result.id} will be permanently deleted. Are you sure?`)) return
    setDeleting(true)
    setError(null)
    try {
      const res = await signedFetch(`${API_URL}/api/admin/interviews/${result.id}`, {
        method: 'DELETE',
      })
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(j.detail || `Error ${res.status}`)
      }
      setMsg(`Interview #${result.id} deleted`)
      setResult(null)
      // Go back to step 3 so they can recreate
      setEditing(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setDeleting(false)
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
    setSelectedRoom(-1)
    setEditing(false)
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
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6">
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
        {msg && !error && !result && (
          <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 mb-4 text-[13px] text-green-700">
            {msg}
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
                          <span className="text-[11px] text-[#86868b]">#{c.sheet_number || c.candidate_id}</span>
                        </div>
                        <div className="flex items-center gap-2 mt-0.5 text-[12px] text-[#86868b]">
                          <span>{c.nationality || '\u2014'}</span>
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
                      <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 ${
                        selectedEmployer?.id === emp.id ? 'border-[#0071e3] bg-[#0071e3]' : 'border-[#d2d2d7]'
                      }`}>
                        {selectedEmployer?.id === emp.id && (
                          <span className="text-white text-[10px]">{'\u2713'}</span>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[14px] font-medium text-[#1d1d1f]" title={emp.school_name || ''}>{emp.school_name || 'Unknown'}</span>
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
                          <span>{emp.location || '\u2014'}</span>
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
          <div className="space-y-5">
            {/* ── Candidate Info Card (큰 폰트) ── */}
            <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
              <div className="flex items-start gap-5">
                {candidate.photo_url ? (
                  <img src={candidate.photo_url} alt="" className="w-16 h-16 rounded-xl object-cover border border-[#e5e5e7] shrink-0" />
                ) : (
                  <div className="w-16 h-16 rounded-xl bg-[#f5f5f7] flex items-center justify-center text-[22px] font-bold text-[#86868b] shrink-0">
                    {(candidate.full_name || '?')[0]}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-2">
                    <div>
                      <div className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider">번호</div>
                      <div className="text-[16px] font-bold text-[#1d1d1f]">#{candidate.sheet_number || candidate.candidate_id}</div>
                    </div>
                    <div>
                      <div className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider">이름</div>
                      <div className="text-[16px] font-bold text-[#1d1d1f]">{candidate.full_name}</div>
                    </div>
                    <div>
                      <div className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider">국적</div>
                      <div className="text-[16px] font-semibold text-[#1d1d1f]">{candidate.nationality || '\u2014'}</div>
                    </div>
                    <div>
                      <div className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider">이메일</div>
                      <div className="text-[15px] text-[#1d1d1f] truncate">{candidate.email || '\u2014'}</div>
                    </div>
                    <div>
                      <div className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider">시작일</div>
                      <div className="text-[15px] text-[#1d1d1f]">{candidate.start_date || '\u2014'}</div>
                    </div>
                    <div className="col-span-2 sm:col-span-1">
                      <div className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider">메모 / 선호 인터뷰 시간</div>
                      <div className="text-[15px] text-[#1d1d1f]">{candidate.interview_time || '\u2014'}</div>
                    </div>
                  </div>
                </div>
                <div className="flex flex-col gap-1.5 shrink-0">
                  <button type="button" onClick={() => setStep(2)}
                    className="text-[11px] text-[#86868b] hover:text-[#1d1d1f] px-3 py-1 border border-[#e5e5e7] rounded-lg">
                    Change
                  </button>
                </div>
              </div>
              {/* Employer info (compact) */}
              <div className="mt-3 pt-3 border-t border-[#f0f0f2] flex items-center gap-3 text-[13px]">
                <span className="text-[#86868b]">Employer:</span>
                <span className="font-semibold text-[#1d1d1f]">{selectedEmployer.school_name}</span>
                <span className="text-[#86868b]">{selectedEmployer.location}</span>
                <span className="text-[#86868b]">{selectedEmployer.contact_name}</span>
              </div>
            </div>

            {/* ── Schedule Row ── */}
            <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div>
                  <label className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider block mb-1.5">Date</label>
                  <input
                    type="date"
                    value={interviewDate}
                    onChange={e => setInterviewDate(e.target.value)}
                    className="w-full px-3 py-2.5 border border-[#d2d2d7] rounded-xl text-[14px] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 focus:border-[#0071e3]"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider block mb-1.5">Time (KST)</label>
                  <input
                    type="time"
                    value={interviewTime}
                    onChange={e => setInterviewTime(e.target.value)}
                    className="w-full px-3 py-2.5 border border-[#d2d2d7] rounded-xl text-[14px] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 focus:border-[#0071e3]"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider block mb-1.5">Duration</label>
                  <div className="flex gap-1.5">
                    {[15, 20, 30].map(d => (
                      <button
                        key={d}
                        type="button"
                        onClick={() => setDuration(d)}
                        className={`flex-1 py-2.5 rounded-xl text-[13px] font-semibold border transition-colors ${
                          duration === d
                            ? 'bg-[#0071e3]/10 text-[#0071e3] border-[#0071e3]/30'
                            : 'bg-white text-[#424245] border-[#d2d2d7] hover:bg-[#f5f5f7]'
                        }`}
                      >
                        {d}m
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider block mb-1.5">메모</label>
                  <input
                    type="text"
                    value={notes}
                    onChange={e => setNotes(e.target.value)}
                    placeholder="추가 메모..."
                    className="w-full px-3 py-2.5 border border-[#d2d2d7] rounded-xl text-[14px] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 focus:border-[#0071e3]"
                  />
                </div>
              </div>
            </div>

            {/* ── Two Column: Meet Rooms (Left) + Email Preview (Right) ── */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {/* LEFT: Meet 회의실 */}
              <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden">
                <div className="px-5 py-3 border-b border-[#e5e5e7] bg-[#fafafa] flex items-center justify-between">
                  <h3 className="text-[14px] font-semibold text-[#1d1d1f]">
                    Meet 회의실 ({MEET_ROOMS.length})
                  </h3>
                  <div className="flex items-center gap-2">
                    <a
                      href={`https://calendar.google.com/calendar/u/0/r/eventedit?text=${encodeURIComponent(`BRIDGE Interview — ${candidate?.full_name || ''}`)}&dates=${(() => { const d = interviewDate; const t = interviewTime || '14:00'; const [y,mo,dd] = d.split('-').map(Number); const [h,mi] = t.split(':').map(Number); const s = new Date(y,mo-1,dd,h,mi); const e = new Date(s.getTime()+duration*60000); const f = (dt: Date) => dt.toISOString().replace(/[-:]/g,'').replace(/\.\d+/,''); return `${f(s)}/${f(e)}` })()}&details=${encodeURIComponent('BRIDGE Recruitment Interview')}${candidate?.email ? `&add=${encodeURIComponent(candidate.email)}` : ''}`}
                      target="_blank" rel="noopener noreferrer"
                      className="text-[12px] px-3 py-1 bg-blue-500 text-white rounded-full font-medium hover:bg-blue-600 transition-colors"
                    >
                      📅 캘린더에서 Meet 생성
                    </a>
                    <button
                      type="button"
                      onClick={pickRandomRoom}
                      className="text-[12px] px-3 py-1 bg-[#0071e3]/10 text-[#0071e3] rounded-full font-medium hover:bg-[#0071e3]/20 transition-colors"
                    >
                      랜덤
                    </button>
                  </div>
                </div>
                <div className="px-4 py-2 text-[11px] text-[#86868b] border-b border-[#f5f5f7]">
                  액세스: 항상 열기 &middot; 허가없이 참여 가능
                </div>
                <div className="divide-y divide-[#f5f5f7]">
                  {MEET_ROOMS.map((room, idx) => (
                    <div
                      key={room.code}
                      className={`flex items-center gap-3 px-4 py-3 transition-colors cursor-pointer ${
                        selectedRoom === idx ? 'bg-green-50' : 'hover:bg-[#fafafa]'
                      }`}
                      onClick={() => setSelectedRoom(idx)}
                    >
                      {/* Radio indicator */}
                      <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 ${
                        selectedRoom === idx ? 'border-green-500 bg-green-500' : 'border-[#d2d2d7]'
                      }`}>
                        {selectedRoom === idx && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className="text-[13px] font-medium text-[#1d1d1f]">{room.label}</span>
                        <span className="text-[12px] text-[#86868b] ml-2">&middot; {room.code}</span>
                      </div>
                      <a
                        href={`https://meet.google.com/${room.code}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={e => e.stopPropagation()}
                        className="text-[11px] px-2.5 py-1 bg-[#0071e3]/10 text-[#0071e3] rounded-lg font-medium hover:bg-[#0071e3]/20 transition-colors"
                      >
                        입장
                      </a>
                    </div>
                  ))}
                </div>
              </div>

              {/* RIGHT: 이메일 자동 발송 */}
              <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden flex flex-col">
                <div className="px-5 py-3 border-b border-[#e5e5e7] bg-[#fafafa]">
                  <h3 className="text-[14px] font-semibold text-[#1d1d1f]">이메일 자동 발송</h3>
                </div>
                <div className="p-4 flex-1 flex flex-col gap-3">
                  <div>
                    <label className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider block mb-1">제목</label>
                    <input
                      type="text"
                      value={emailSubject}
                      onChange={e => setEmailSubject(e.target.value)}
                      className="w-full px-3 py-2 border border-[#d2d2d7] rounded-lg text-[13px] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 focus:border-[#0071e3] bg-[#fafafa]"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider block mb-1">본문</label>
                    <textarea
                      value={emailBody}
                      onChange={e => setEmailBody(e.target.value)}
                      className="w-full h-full min-h-[200px] px-3 py-2 border border-[#d2d2d7] rounded-lg text-[13px] leading-relaxed focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 focus:border-[#0071e3] bg-[#fafafa] resize-none font-mono"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* ── Confirm Button (옅은 초록) ── */}
            <button
              type="button"
              onClick={handleConfirm}
              disabled={confirming}
              className="w-full py-4 bg-green-500 text-white text-[16px] font-bold rounded-2xl hover:bg-green-600 disabled:opacity-50 transition-colors shadow-sm"
            >
              {confirming ? 'Setting up interview...' : '생성'}
            </button>
          </div>
        )}

        {/* ═══ RESULT ═══ */}
        {result && (
          <div className="space-y-4">
            <div className="bg-white rounded-2xl border border-green-200 p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center text-green-600 text-[20px] shrink-0">
                  {'\u2713'}
                </div>
                <div>
                  <h2 className="text-[17px] font-bold text-[#1d1d1f]">Interview #{result.id} Confirmed</h2>
                  <p className="text-[13px] text-[#86868b]">{msg}</p>
                </div>
              </div>

              {/* Edit Form */}
              {editing ? (
                <div className="space-y-4 mb-5">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-[12px] font-semibold text-[#86868b] block mb-1">Date</label>
                      <input type="date" value={editDate} onChange={e => setEditDate(e.target.value)}
                        className="w-full px-3 py-2 border border-[#d2d2d7] rounded-xl text-[14px] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30" />
                    </div>
                    <div>
                      <label className="text-[12px] font-semibold text-[#86868b] block mb-1">Time</label>
                      <input type="time" value={editTime} onChange={e => setEditTime(e.target.value)}
                        className="w-full px-3 py-2 border border-[#d2d2d7] rounded-xl text-[14px] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30" />
                    </div>
                  </div>
                  <div>
                    <label className="text-[12px] font-semibold text-[#86868b] block mb-1">Duration</label>
                    <div className="flex gap-2">
                      {[15, 20, 30].map(d => (
                        <button key={d} type="button" onClick={() => setEditDuration(d)}
                          className={`px-5 py-2 rounded-xl text-[13px] font-semibold border transition-colors ${
                            editDuration === d
                              ? 'bg-[#0071e3]/10 text-[#0071e3] border-[#0071e3]/30'
                              : 'bg-white text-[#424245] border-[#d2d2d7] hover:bg-[#f5f5f7]'
                          }`}>
                          {d} min
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="text-[12px] font-semibold text-[#86868b] block mb-1">Notes</label>
                    <textarea value={editNotes} onChange={e => setEditNotes(e.target.value)} rows={2}
                      className="w-full px-3 py-2 border border-[#d2d2d7] rounded-xl text-[14px] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 resize-none" />
                  </div>
                  <div className="flex gap-2">
                    <button type="button" onClick={saveEdit} disabled={editSaving}
                      className="flex-1 py-2.5 bg-[#0071e3] text-white text-[14px] font-semibold rounded-xl hover:bg-[#0077ED] disabled:opacity-50 transition-colors">
                      {editSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                    <button type="button" onClick={() => setEditing(false)}
                      className="px-5 py-2.5 text-[14px] text-[#86868b] border border-[#d2d2d7] rounded-xl hover:bg-[#f5f5f7] transition-colors">
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-3 text-[14px] mb-5">
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
                      <div className="flex items-center gap-2">
                        <a href={result.meet_link} target="_blank" rel="noopener noreferrer"
                          className="text-[#0071e3] font-medium hover:underline truncate max-w-[200px]">
                          {result.meet_link.replace('https://meet.google.com/', '')}
                        </a>
                        <a href={`https://calendar.google.com/calendar/u/0/r/eventedit?text=${encodeURIComponent(`BRIDGE Interview — ${candidate?.full_name || ''}`)}&details=${encodeURIComponent('Meet: ' + result.meet_link)}`}
                          target="_blank" rel="noopener noreferrer"
                          className="text-[10px] px-2 py-0.5 bg-blue-100 text-blue-600 rounded-full font-medium hover:bg-blue-200 shrink-0">
                          📅 편집
                        </a>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Status badges */}
              {!editing && (
                <div className="flex flex-wrap gap-2 mb-4">
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
              )}
            </div>

            {/* Actions: 수정 / 삭제 / New / View All */}
            {!editing && (
              <div className="flex gap-3">
                <button type="button" onClick={startEdit}
                  className="flex-1 py-3 text-center text-[14px] font-semibold text-[#0071e3] bg-white border border-[#0071e3]/30 rounded-2xl hover:bg-[#0071e3]/5 transition-colors">
                  일정 수정
                </button>
                <button type="button" onClick={handleDelete} disabled={deleting}
                  className="flex-1 py-3 text-center text-[14px] font-semibold text-red-600 bg-white border border-red-200 rounded-2xl hover:bg-red-50 disabled:opacity-50 transition-colors">
                  {deleting ? 'Deleting...' : '일정 삭제'}
                </button>
                <button type="button" onClick={resetAll}
                  className="flex-1 py-3 text-[14px] font-bold text-white bg-green-500 rounded-2xl hover:bg-green-600 transition-colors">
                  New Interview
                </button>
              </div>
            )}

            {/* View All link */}
            <a href="/admin/interviews"
              className="block text-center text-[13px] text-[#86868b] hover:text-[#1d1d1f] transition-colors py-2">
              View All Interviews &rarr;
            </a>
          </div>
        )}

        {/* ═══ Deleted → Back to creation ═══ */}
        {!result && msg && step === 3 && candidate && selectedEmployer && msg.includes('deleted') && (
          <div className="mt-4 bg-orange-50 border border-orange-200 rounded-xl px-4 py-3 text-[13px] text-orange-700">
            Interview deleted. You can create a new one above.
          </div>
        )}
      </div>
    </div>
  )
}
