'use client'

/**
 * /admin/interview-setup — 인터뷰 세팅 (다중 발송)
 *
 * 흐름:
 *  ① 활성 후보자 리스트 + 체크박스 다중 선택 (검색)
 *  ② 구인처 리스트 + 체크박스 다중 선택 (검색·필터)
 *  ③ 일정 설정 (Date/Time/Duration/Stagger)
 *  ④ 발송 → N후보자 × M구인처 = N×M 인터뷰 생성
 *      · 각자에게 자기 Meet 링크만 포함된 개별 이메일
 *      · 상대측 이메일/연락처 노출 안 함 (백엔드 _render_interview_email PII 격리)
 *
 * 백엔드 변경 0줄 — /api/admin/interview/confirm (1쌍/호출) 순차 호출.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import AdminAuth from '@/components/admin/AdminAuth'
import { API_URL } from '@/lib/api'

/* ── Types ── */
interface Candidate {
  candidate_id: string
  sheet_number: string
  full_name: string
  nationality: string
  current_location: string
  email: string
  kakao_id: string
  status: string
  target: string
  target_age: string
  area_prefs: string
}

interface Employer {
  id: number
  school_name: string
  location: string
  contact_name: string
  email: string
  phone: string
  teaching_age: string
  start_date: string
}

interface PairResult {
  candidate_id: string
  candidate_name: string
  inquiry_id: number
  school_name: string
  interview_id: number | null
  meet_link: string
  date: string
  time: string
  ok: boolean
  error?: string
}

/* ── Helpers ── */
function defaultDate(): string {
  const d = new Date()
  let added = 0
  while (added < 3) {
    d.setDate(d.getDate() + 1)
    const dow = d.getDay()
    if (dow !== 0 && dow !== 6) added++
  }
  return d.toISOString().slice(0, 10)
}

function addMinutes(hhmm: string, minutes: number): string {
  const [h, m] = hhmm.split(':').map(Number)
  const total = h * 60 + m + minutes
  const nh = Math.floor(total / 60) % 24
  const nm = total % 60
  return `${String(nh).padStart(2, '0')}:${String(nm).padStart(2, '0')}`
}

/* ═══════════════════════════════════════════════════════════════════ */
export default function InterviewSetupPage() {
  const { authed, login, signedFetch, adminFetch, waking } = useAdminAuth()

  /* ── 후보자 패널 ── */
  const [candQ, setCandQ] = useState('')
  const [candList, setCandList] = useState<Candidate[]>([])
  const [candLoading, setCandLoading] = useState(false)
  const [selectedCands, setSelectedCands] = useState<Set<string>>(new Set())

  /* ── 구인처 패널 ── */
  const [empLocation, setEmpLocation] = useState('')
  const [empAge, setEmpAge] = useState('')
  const [empQ, setEmpQ] = useState('')
  const [empList, setEmpList] = useState<Employer[]>([])
  const [empLoading, setEmpLoading] = useState(false)
  const [selectedEmps, setSelectedEmps] = useState<Set<number>>(new Set())

  /* ── 일정 ── */
  const [date, setDate] = useState(defaultDate)
  const [time, setTime] = useState('10:00')
  const [duration, setDuration] = useState(20)
  const [stagger, setStagger] = useState(30)
  const [notes, setNotes] = useState('')

  /* ── 발송 ── */
  const [sending, setSending] = useState(false)
  const [progress, setProgress] = useState({ done: 0, total: 0 })
  const [results, setResults] = useState<PairResult[]>([])
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  /* ── 후보자 검색 (디바운스) ── */
  const fetchCandidates = useCallback(async (q: string) => {
    setCandLoading(true)
    setError(null)
    try {
      const url = q.trim()
        ? `${API_URL}/api/admin/candidates?search=${encodeURIComponent(q)}&limit=100&status=active`
        : `${API_URL}/api/admin/candidates?limit=100&status=active`
      const res = await adminFetch(url)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const j = await res.json()
      const rows = j.data?.candidates || []
      const mapped: Candidate[] = (Array.isArray(rows) ? rows : []).map((r: Record<string, unknown>) => ({
        candidate_id: String(r.candidate_id || r.id || ''),
        sheet_number: String(r.sheet_number || ''),
        full_name: String(r.full_name || ''),
        nationality: String(r.nationality || ''),
        current_location: String(r.current_location || ''),
        email: String(r.email || ''),
        kakao_id: String(r.kakao_id || ''),
        status: String(r.status || ''),
        target: String(r.target || ''),
        target_age: String(r.target_age || ''),
        area_prefs: String(r.area_prefs || ''),
      }))
      setCandList(mapped)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Candidate fetch failed')
    } finally {
      setCandLoading(false)
    }
  }, [adminFetch])

  /* ── 구인처 검색 ── */
  const fetchEmployers = useCallback(async () => {
    setEmpLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (empLocation.trim()) params.set('location', empLocation.trim())
      if (empAge.trim()) params.set('teaching_age', empAge.trim())
      params.set('per_page', '200')
      const res = await adminFetch(`${API_URL}/api/admin/employers-for-mail?${params}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const j = await res.json()
      const rows = j.data?.employers || []
      setEmpList(rows as Employer[])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Employer fetch failed')
    } finally {
      setEmpLoading(false)
    }
  }, [adminFetch, empLocation, empAge])

  /* ── 초기 + 디바운스 로드 ── */
  useEffect(() => {
    if (!authed) return
    const t = setTimeout(() => fetchCandidates(candQ), 300)
    return () => clearTimeout(t)
  }, [authed, candQ, fetchCandidates])

  useEffect(() => {
    if (!authed) return
    fetchEmployers()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed])

  /* ── 클라이언트측 추가 필터 (school_name) ── */
  const filteredEmps = useMemo(() => {
    const q = empQ.trim().toLowerCase()
    if (!q) return empList
    return empList.filter(e =>
      (e.school_name || '').toLowerCase().includes(q) ||
      (e.contact_name || '').toLowerCase().includes(q) ||
      (e.email || '').toLowerCase().includes(q)
    )
  }, [empList, empQ])

  /* ── 선택 토글 ── */
  const toggleCand = (cid: string) => {
    setSelectedCands(prev => {
      const next = new Set(prev)
      next.has(cid) ? next.delete(cid) : next.add(cid)
      return next
    })
  }
  const toggleEmp = (id: number) => {
    setSelectedEmps(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }
  const toggleAllCands = () => {
    if (selectedCands.size === candList.length) {
      setSelectedCands(new Set())
    } else {
      setSelectedCands(new Set(candList.map(c => c.candidate_id)))
    }
  }
  const toggleAllEmps = () => {
    if (selectedEmps.size === filteredEmps.length) {
      setSelectedEmps(new Set())
    } else {
      setSelectedEmps(new Set(filteredEmps.map(e => e.id)))
    }
  }

  /* ── 미리보기 ── */
  const totalPairs = selectedCands.size * selectedEmps.size

  const pairs = useMemo(() => {
    const out: { candidate: Candidate; employer: Employer; slot: number }[] = []
    let slot = 0
    for (const cid of selectedCands) {
      const c = candList.find(x => x.candidate_id === cid)
      if (!c) continue
      for (const eid of selectedEmps) {
        const e = empList.find(x => x.id === eid)
        if (!e) continue
        out.push({ candidate: c, employer: e, slot })
        slot++
      }
    }
    return out
  }, [selectedCands, selectedEmps, candList, empList])

  /* ── 발송 (순차 호출, 백엔드 부하 보호) ── */
  const handleSend = async () => {
    if (totalPairs === 0) {
      setError('후보자·구인처 각각 최소 1명 이상 선택하세요.')
      return
    }
    if (!window.confirm(
      `${selectedCands.size}명 후보자 × ${selectedEmps.size}개 구인처 = ${totalPairs}개 인터뷰를 생성합니다.\n` +
      `각자에게 개별 메일이 발송됩니다.\n계속하시겠습니까?`
    )) return

    setSending(true)
    setError(null)
    setMsg(null)
    setResults([])
    setProgress({ done: 0, total: totalPairs })

    const out: PairResult[] = []
    for (let i = 0; i < pairs.length; i++) {
      const { candidate, employer, slot } = pairs[i]
      const slotTime = addMinutes(time, slot * stagger)
      try {
        const res = await signedFetch(`${API_URL}/api/admin/interview/confirm`, {
          method: 'POST',
          body: JSON.stringify({
            candidate_id: candidate.candidate_id,
            inquiry_id: employer.id,
            interview_date: date,
            interview_time: slotTime,
            duration_minutes: duration,
            notes,
          }),
        })
        if (!res.ok) {
          const j = await res.json().catch(() => ({}))
          out.push({
            candidate_id: candidate.candidate_id,
            candidate_name: candidate.full_name,
            inquiry_id: employer.id,
            school_name: employer.school_name,
            interview_id: null,
            meet_link: '',
            date,
            time: slotTime,
            ok: false,
            error: j.detail || j.message || `HTTP ${res.status}`,
          })
        } else {
          const j = await res.json()
          const data = j.data || {}
          out.push({
            candidate_id: candidate.candidate_id,
            candidate_name: candidate.full_name,
            inquiry_id: employer.id,
            school_name: employer.school_name,
            interview_id: data.id || null,
            meet_link: data.meet_link || '',
            date,
            time: slotTime,
            ok: true,
            error: data.email_errors?.length ? `email: ${data.email_errors.join(', ')}` : undefined,
          })
        }
      } catch (e) {
        out.push({
          candidate_id: candidate.candidate_id,
          candidate_name: candidate.full_name,
          inquiry_id: employer.id,
          school_name: employer.school_name,
          interview_id: null,
          meet_link: '',
          date,
          time: slotTime,
          ok: false,
          error: e instanceof Error ? e.message : 'Unknown error',
        })
      }
      setResults([...out])
      setProgress({ done: i + 1, total: pairs.length })
      // 백엔드 부하 보호 (Render Free + Google Calendar API throttle)
      if (i + 1 < pairs.length) {
        await new Promise(r => setTimeout(r, 500))
      }
    }

    setSending(false)
    const okCount = out.filter(r => r.ok).length
    setMsg(`${okCount}/${out.length}개 인터뷰 생성 완료`)
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-[22px] font-bold text-[#1d1d1f] tracking-tight">Interview Setup (Bulk)</h1>
          <p className="text-[13px] text-[#86868b] mt-0.5">
            후보자·구인처 다중 선택 → 개별 메일로 인터뷰 가이드 + Google Meet 링크 발송
          </p>
        </div>

        {/* Error / Success */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 mb-4 text-[13px] text-red-700">
            {error}
          </div>
        )}
        {msg && !error && (
          <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 mb-4 text-[13px] text-green-700">
            {msg}
          </div>
        )}

        {/* ═══ 2-PANEL: Candidates + Employers ═══ */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
          {/* Candidates */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden">
            <div className="px-5 py-3 border-b border-[#e5e5e7] bg-[#fafafa] flex items-center justify-between">
              <h2 className="text-[14px] font-semibold text-[#1d1d1f]">
                후보자 ({selectedCands.size}/{candList.length})
              </h2>
              <button type="button" onClick={toggleAllCands}
                className="text-[12px] text-[#0071e3] hover:underline">
                {selectedCands.size === candList.length && candList.length > 0 ? '전체 해제' : '전체 선택'}
              </button>
            </div>
            <div className="p-4 border-b border-[#e5e5e7]">
              <input
                type="text"
                value={candQ}
                onChange={e => setCandQ(e.target.value)}
                placeholder="이름·국적·번호로 검색…"
                className="w-full px-3 py-2 rounded-lg border border-[#d2d2d7] text-[13px] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30"
              />
              {candLoading && <p className="text-[11px] text-[#86868b] mt-2">검색 중…</p>}
            </div>
            <div className="max-h-[420px] overflow-y-auto">
              {candList.length === 0 && !candLoading && (
                <p className="px-5 py-8 text-[13px] text-[#86868b] text-center">활성 후보자 없음</p>
              )}
              <table className="w-full text-[12px]">
                <thead className="bg-[#fafafa] sticky top-0">
                  <tr className="text-left text-[#86868b]">
                    <th className="px-2 py-2 w-[30px]"></th>
                    <th className="px-2 py-2 w-[50px]">#</th>
                    <th className="px-2 py-2">이름</th>
                    <th className="px-2 py-2">국적</th>
                    <th className="px-2 py-2">현위치</th>
                    <th className="px-2 py-2">이메일</th>
                    <th className="px-2 py-2">카톡</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f5f5f7]">
                  {candList.map((c, idx) => {
                    const checked = selectedCands.has(c.candidate_id)
                    return (
                      <tr key={c.candidate_id}
                        onClick={() => toggleCand(c.candidate_id)}
                        className={`cursor-pointer hover:bg-[#f5f5f7] ${checked ? 'bg-[#e6f0ff]' : ''}`}>
                        <td className="px-2 py-1.5"><input type="checkbox" checked={checked} readOnly /></td>
                        <td className="px-2 py-1.5 text-[#86868b]">{idx + 1}</td>
                        <td className="px-2 py-1.5 font-medium">
                          {c.full_name || `#${c.sheet_number || c.candidate_id}`}
                          {c.sheet_number && <span className="ml-1 text-[10px] text-[#86868b]">#{c.sheet_number}</span>}
                        </td>
                        <td className="px-2 py-1.5 text-[#86868b]">{c.nationality || '-'}</td>
                        <td className="px-2 py-1.5 text-[#86868b]">{c.current_location || '-'}</td>
                        <td className="px-2 py-1.5 text-[#86868b] truncate max-w-[120px]" title={c.email}>
                          {c.email || '-'}
                        </td>
                        <td className="px-2 py-1.5 text-[#86868b] truncate max-w-[80px]" title={c.kakao_id}>
                          {c.kakao_id || '-'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Employers */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden">
            <div className="px-5 py-3 border-b border-[#e5e5e7] bg-[#fafafa] flex items-center justify-between">
              <h2 className="text-[14px] font-semibold text-[#1d1d1f]">
                구인처 ({selectedEmps.size}/{filteredEmps.length})
              </h2>
              <button type="button" onClick={toggleAllEmps}
                className="text-[12px] text-[#0071e3] hover:underline">
                {selectedEmps.size === filteredEmps.length && filteredEmps.length > 0 ? '전체 해제' : '전체 선택'}
              </button>
            </div>
            <div className="p-4 border-b border-[#e5e5e7] space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  value={empLocation}
                  onChange={e => setEmpLocation(e.target.value)}
                  placeholder="도시 (예: 서울)"
                  className="px-3 py-2 rounded-lg border border-[#d2d2d7] text-[13px]"
                />
                <input
                  type="text"
                  value={empAge}
                  onChange={e => setEmpAge(e.target.value)}
                  placeholder="대상 연령 (예: K-5)"
                  className="px-3 py-2 rounded-lg border border-[#d2d2d7] text-[13px]"
                />
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={empQ}
                  onChange={e => setEmpQ(e.target.value)}
                  placeholder="업체명·담당자·이메일로 필터…"
                  className="flex-1 px-3 py-2 rounded-lg border border-[#d2d2d7] text-[13px]"
                />
                <button type="button" onClick={fetchEmployers}
                  className="px-4 py-2 rounded-lg bg-[#0071e3] text-white text-[13px] font-medium hover:bg-[#0077ed]">
                  검색
                </button>
              </div>
              {empLoading && <p className="text-[11px] text-[#86868b]">검색 중…</p>}
            </div>
            <div className="max-h-[420px] overflow-y-auto">
              {filteredEmps.length === 0 && !empLoading && (
                <p className="px-5 py-8 text-[13px] text-[#86868b] text-center">구인처 없음</p>
              )}
              <table className="w-full text-[12px]">
                <thead className="bg-[#fafafa] sticky top-0">
                  <tr className="text-left text-[#86868b]">
                    <th className="px-2 py-2 w-[30px]"></th>
                    <th className="px-2 py-2">업체명</th>
                    <th className="px-2 py-2">지역</th>
                    <th className="px-2 py-2">연령</th>
                    <th className="px-2 py-2">담당자</th>
                    <th className="px-2 py-2">이메일</th>
                    <th className="px-2 py-2">전화</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f5f5f7]">
                  {filteredEmps.map(e => {
                    const checked = selectedEmps.has(e.id)
                    return (
                      <tr key={e.id}
                        onClick={() => toggleEmp(e.id)}
                        className={`cursor-pointer hover:bg-[#f5f5f7] ${checked ? 'bg-[#e6f0ff]' : ''}`}>
                        <td className="px-2 py-1.5"><input type="checkbox" checked={checked} readOnly /></td>
                        <td className="px-2 py-1.5 font-medium truncate max-w-[140px]" title={e.school_name}>
                          {e.school_name || `#${e.id}`}
                        </td>
                        <td className="px-2 py-1.5 text-[#86868b] truncate max-w-[80px]" title={e.location}>
                          {e.location || '-'}
                        </td>
                        <td className="px-2 py-1.5 text-[#86868b]">{e.teaching_age || '-'}</td>
                        <td className="px-2 py-1.5 text-[#86868b] truncate max-w-[80px]" title={e.contact_name}>
                          {e.contact_name || '-'}
                        </td>
                        <td className="px-2 py-1.5 text-[#86868b] truncate max-w-[120px]" title={e.email}>
                          {e.email || '-'}
                        </td>
                        <td className="px-2 py-1.5 text-[#86868b] truncate max-w-[100px]" title={e.phone}>
                          {e.phone || '-'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ═══ 일정 + 발송 ═══ */}
        <div className="bg-white rounded-2xl border border-[#e5e5e7] p-6 mb-4">
          <h2 className="text-[14px] font-semibold text-[#1d1d1f] mb-4">일정 설정</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
            <div>
              <label className="block text-[12px] text-[#86868b] mb-1">날짜</label>
              <input type="date" value={date} onChange={e => setDate(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-[#d2d2d7] text-[13px]" />
            </div>
            <div>
              <label className="block text-[12px] text-[#86868b] mb-1">시작 시각 (KST)</label>
              <input type="time" value={time} onChange={e => setTime(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-[#d2d2d7] text-[13px]" />
            </div>
            <div>
              <label className="block text-[12px] text-[#86868b] mb-1">개당 시간 (분)</label>
              <input type="number" min={5} max={120} value={duration}
                onChange={e => setDuration(Math.max(5, Math.min(120, Number(e.target.value) || 20)))}
                className="w-full px-3 py-2 rounded-lg border border-[#d2d2d7] text-[13px]" />
            </div>
            <div>
              <label className="block text-[12px] text-[#86868b] mb-1">간격 (분)</label>
              <input type="number" min={0} max={240} value={stagger}
                onChange={e => setStagger(Math.max(0, Math.min(240, Number(e.target.value) || 30)))}
                className="w-full px-3 py-2 rounded-lg border border-[#d2d2d7] text-[13px]" />
            </div>
          </div>
          <div>
            <label className="block text-[12px] text-[#86868b] mb-1">공통 메모 (선택)</label>
            <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2}
              placeholder="모든 인터뷰에 동일하게 추가될 메모…"
              className="w-full px-3 py-2 rounded-lg border border-[#d2d2d7] text-[13px]" />
          </div>
        </div>

        {/* 발송 미리보기 + 버튼 */}
        <div className="bg-white rounded-2xl border border-[#e5e5e7] p-6 mb-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-[14px] font-semibold text-[#1d1d1f]">
                {selectedCands.size}명 × {selectedEmps.size}개 = <span className="text-[#0071e3]">{totalPairs}개</span> 인터뷰 생성
              </div>
              <div className="text-[12px] text-[#86868b] mt-0.5">
                메일 발송: 후보자 {selectedCands.size * selectedEmps.size}건 + 구인처 {selectedCands.size * selectedEmps.size}건 (개별 발송, PII 격리됨)
              </div>
            </div>
            <button
              type="button"
              onClick={handleSend}
              disabled={sending || totalPairs === 0}
              className="px-6 py-3 rounded-xl bg-[#0071e3] text-white text-[14px] font-semibold hover:bg-[#0077ed] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sending ? `발송 중… ${progress.done}/${progress.total}` : '발송하기'}
            </button>
          </div>
          {sending && progress.total > 0 && (
            <div className="w-full bg-[#f5f5f7] rounded-full h-2 overflow-hidden">
              <div
                className="bg-[#0071e3] h-full transition-all duration-300"
                style={{ width: `${(progress.done / progress.total) * 100}%` }}
              />
            </div>
          )}
        </div>

        {/* 결과 */}
        {results.length > 0 && (
          <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden">
            <div className="px-5 py-3 border-b border-[#e5e5e7] bg-[#fafafa]">
              <h3 className="text-[14px] font-semibold text-[#1d1d1f]">
                발송 결과 ({results.filter(r => r.ok).length}/{results.length} 성공)
              </h3>
            </div>
            <div className="max-h-[400px] overflow-y-auto">
              <table className="w-full text-[12px]">
                <thead className="bg-[#fafafa] sticky top-0">
                  <tr className="text-left text-[#86868b]">
                    <th className="px-3 py-2 w-[40px]">상태</th>
                    <th className="px-3 py-2">후보자</th>
                    <th className="px-3 py-2">구인처</th>
                    <th className="px-3 py-2">시각</th>
                    <th className="px-3 py-2">Meet</th>
                    <th className="px-3 py-2">메모</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f5f5f7]">
                  {results.map((r, i) => (
                    <tr key={i}>
                      <td className="px-3 py-2">
                        {r.ok
                          ? <span className="text-green-600 font-semibold">✓</span>
                          : <span className="text-red-600 font-semibold">✗</span>}
                      </td>
                      <td className="px-3 py-2 truncate max-w-[140px]" title={r.candidate_name}>
                        {r.candidate_name || r.candidate_id}
                      </td>
                      <td className="px-3 py-2 truncate max-w-[140px]" title={r.school_name}>
                        {r.school_name}
                      </td>
                      <td className="px-3 py-2 text-[#86868b]">{r.date} {r.time}</td>
                      <td className="px-3 py-2">
                        {r.meet_link
                          ? <a href={r.meet_link} target="_blank" rel="noopener noreferrer"
                              className="text-[#0071e3] hover:underline">link</a>
                          : '-'}
                      </td>
                      <td className="px-3 py-2 text-[#86868b] truncate max-w-[200px]" title={r.error}>
                        {r.error || (r.ok ? `#${r.interview_id} OK` : '-')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
