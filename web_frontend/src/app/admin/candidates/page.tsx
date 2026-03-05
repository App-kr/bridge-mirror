'use client'

/**
 * /admin/candidates — 원어민 관리
 * Active/Inactive 탭 + 10-column table + 섹션별 상세 펼침
 * 모든 DB 필드 보존, 기본 테이블에서만 핵심 10개 표시
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL
const PAGE_SIZE = 100

type TabType = 'all' | 'Active' | 'Inactive'

const STATUS_VALUES = ['Active', 'Inactive', 'new', 'reviewing', 'interviewing', 'offered', 'placed', 'rejected', 'withdrawn', 'blacklisted']

const statusColors: Record<string, string> = {
  Active:       'bg-blue-100 text-blue-700',
  new:          'bg-blue-100 text-blue-700',
  reviewing:    'bg-yellow-100 text-yellow-700',
  interviewing: 'bg-indigo-100 text-indigo-700',
  offered:      'bg-violet-100 text-violet-700',
  placed:       'bg-green-100 text-green-700',
  rejected:     'bg-red-100 text-red-700',
  withdrawn:    'bg-gray-200 text-gray-500',
  inactive:     'bg-gray-100 text-gray-500',
  Inactive:     'bg-gray-100 text-gray-500',
  blacklisted:  'bg-red-200 text-red-800',
}

interface Candidate {
  id: string
  candidate_id?: string
  full_name: string
  nationality: string
  email: string
  status: string
  [key: string]: string | null | undefined
}

/** 빈 값 → 공백 */
function v(s: string | null | undefined): string {
  if (!s || s.trim() === '' || s.trim() === 'None' || s.trim() === 'N/A') return ''
  return s.trim()
}

/** 날짜 포맷 */
function fmtDate(s: string | null | undefined): string {
  if (!v(s)) return ''
  try {
    return new Date(s as string).toLocaleDateString('ko-KR')
  } catch {
    return v(s)
  }
}

export default function CandidatesPage() {
  const { adminKey, authed, login, headers, waking } = useAdminAuth()

  const [rows, setRows] = useState<Candidate[]>([])
  const [total, setTotal] = useState(0)
  const [activeCnt, setActiveCnt] = useState(0)
  const [inactiveCnt, setInactiveCnt] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  const [tab, setTab] = useState<TabType>('Active')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [expanded, setExpanded] = useState<string | null>(null)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const fetchData = useCallback(async (q: string = '', statusTab: TabType = tab, pg: number = page) => {
    setLoading(true)
    setError(null)
    try {
      const offset = (pg - 1) * PAGE_SIZE
      const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) })
      if (statusTab !== 'all') params.set('status', statusTab)
      if (q) params.set('search', q)

      const res = await fetch(`${API}/api/admin/candidates?${params}`, { headers: headers() })
      if (res.status === 403) {
        setError('Invalid admin key.')
        sessionStorage.removeItem('bridge_admin_key')
        return
      }
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Error')
      setRows(json.data?.candidates ?? [])
      setTotal(json.data?.total ?? 0)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [headers, tab, page])

  // 탭 카운트 별도 조회
  const fetchCounts = useCallback(async () => {
    try {
      const [resA, resI] = await Promise.all([
        fetch(`${API}/api/admin/candidates?status=Active&limit=0&offset=0`, { headers: headers() }),
        fetch(`${API}/api/admin/candidates?status=Inactive&limit=0&offset=0`, { headers: headers() }),
      ])
      const [jA, jI] = await Promise.all([resA.json(), resI.json()])
      setActiveCnt(jA.data?.total ?? 0)
      setInactiveCnt(jI.data?.total ?? 0)
    } catch { /* ignore */ }
  }, [headers])

  useEffect(() => {
    if (authed) {
      fetchData(search, tab, page)
      fetchCounts()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed, tab, page])

  const handleTabChange = (t: TabType) => {
    setTab(t)
    setPage(1)
    setExpanded(null)
    fetchData(search, t, 1)
  }

  const handleSearch = () => {
    setPage(1)
    setExpanded(null)
    fetchData(search, tab, 1)
  }

  const updateStatus = async (id: string, newStatus: string) => {
    try {
      const res = await fetch(`${API}/api/admin/candidates/${id}`, {
        method: 'PATCH', headers: headers(),
        body: JSON.stringify({ status: newStatus }),
      })
      if (!res.ok) throw new Error('Failed')
      setActionMsg(`#${id} → ${newStatus}`)
      setTimeout(() => setActionMsg(null), 3000)
      fetchData(search, tab, page)
      fetchCounts()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[#1d1d1f]">원어민 관리</h1>
          <p className="text-sm text-[#86868b] mt-0.5">
            {loading ? '로딩 중...' : `${total.toLocaleString()}명`}
            {total > rows.length ? ` (표시: ${rows.length}명)` : ''}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {actionMsg && <span className="text-sm text-green-600 font-medium">{actionMsg}</span>}
          <button type="button" onClick={() => fetchData(search, tab, page)}
            className="text-sm text-[#0071e3] hover:underline font-medium">새로고침</button>
        </div>
      </div>

      {/* Tabs + Search */}
      <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Tabs */}
          <div className="flex bg-gray-100 rounded-xl p-0.5">
            {([
              { key: 'all' as TabType, label: '전체', count: activeCnt + inactiveCnt },
              { key: 'Active' as TabType, label: 'Active', count: activeCnt },
              { key: 'Inactive' as TabType, label: 'Inactive', count: inactiveCnt },
            ]).map(t => (
              <button key={t.key} type="button" onClick={() => handleTabChange(t.key)}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                  tab === t.key
                    ? 'bg-white text-[#1d1d1f] shadow-sm'
                    : 'text-[#86868b] hover:text-[#424245]'
                }`}>
                {t.label}
                <span className="ml-1.5 text-[11px] text-[#86868b]">{t.count.toLocaleString()}</span>
              </button>
            ))}
          </div>

          <div className="h-6 w-px bg-gray-200" />

          {/* Search */}
          <input
            className="px-4 py-2 text-sm border border-gray-200 rounded-xl w-56 focus:outline-none focus:ring-2 focus:ring-blue-400"
            placeholder="이름, 이메일, 국적..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleSearch() }}
          />
          <button type="button" onClick={handleSearch}
            className="text-sm text-[#0071e3] hover:underline font-medium">검색</button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-600 text-sm rounded-2xl">{error}</div>
      )}

      {loading ? (
        <div className="text-center py-16 text-[#86868b] animate-pulse text-sm">로딩 중...</div>
      ) : rows.length === 0 ? (
        <div className="text-center py-16 text-[#86868b] text-sm">해당 지원자가 없습니다.</div>
      ) : (
        <div className="bg-white border border-[#e5e5e7] rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full" style={{ tableLayout: 'fixed', minWidth: '1140px' }}>
              <colgroup>
                <col style={{ width: '80px' }} />
                <col style={{ width: '140px' }} />
                <col style={{ width: '80px' }} />
                <col style={{ width: '120px' }} />
                <col style={{ width: '180px' }} />
                <col style={{ width: '130px' }} />
                <col style={{ width: '120px' }} />
                <col style={{ width: '100px' }} />
                <col style={{ width: '100px' }} />
                <col style={{ width: '90px' }} />
              </colgroup>
              <thead>
                <tr className="bg-[#f5f5f7] text-[11px] text-[#86868b] uppercase tracking-wider"
                  style={{ position: 'sticky', top: 0, zIndex: 20 }}>
                  <th className="px-3 py-3 text-left font-semibold">No.</th>
                  <th className="px-3 py-3 text-left font-semibold">이름</th>
                  <th className="px-3 py-3 text-left font-semibold">국적</th>
                  <th className="px-3 py-3 text-left font-semibold">현위치</th>
                  <th className="px-3 py-3 text-left font-semibold">이메일</th>
                  <th className="px-3 py-3 text-left font-semibold">연락처</th>
                  <th className="px-3 py-3 text-left font-semibold">Teaching Age</th>
                  <th className="px-3 py-3 text-left font-semibold">희망급여</th>
                  <th className="px-3 py-3 text-left font-semibold">시작가능</th>
                  <th className="px-3 py-3 text-left font-semibold"
                    style={{ position: 'sticky', right: 0, background: '#f5f5f7', zIndex: 21 }}>상태</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#f0f0f2]">
                {rows.map(c => (
                  <CandidateRow key={c.id} c={c}
                    expanded={expanded === c.id}
                    onToggle={() => setExpanded(expanded === c.id ? null : c.id)}
                    onStatusChange={updateStatus} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1 py-2">
          <button type="button" disabled={page === 1} onClick={() => { setPage(page - 1); fetchData(search, tab, page - 1) }}
            className="px-3 py-1.5 rounded-lg text-sm font-medium disabled:opacity-30 hover:bg-gray-100 text-gray-600">
            &laquo;
          </button>
          {Array.from({ length: Math.min(totalPages, 9) }, (_, i) => {
            let p: number
            if (totalPages <= 9) { p = i + 1 }
            else if (page <= 5) { p = i + 1 }
            else if (page >= totalPages - 4) { p = totalPages - 8 + i }
            else { p = page - 4 + i }
            return (
              <button key={p} type="button" onClick={() => { setPage(p); fetchData(search, tab, p) }}
                className={`w-9 h-9 rounded-lg text-sm font-semibold transition-all ${
                  p === page ? 'bg-[#0071e3] text-white shadow-md' : 'text-gray-600 hover:bg-gray-100'
                }`}>
                {p}
              </button>
            )
          })}
          <button type="button" disabled={page === totalPages} onClick={() => { setPage(page + 1); fetchData(search, tab, page + 1) }}
            className="px-3 py-1.5 rounded-lg text-sm font-medium disabled:opacity-30 hover:bg-gray-100 text-gray-600">
            &raquo;
          </button>
        </div>
      )}
    </div>
  )
}

/* ── 후보자 행 ── */
function CandidateRow({ c, expanded, onToggle, onStatusChange }: {
  c: Candidate; expanded: boolean; onToggle: () => void
  onStatusChange: (id: string, status: string) => void
}) {
  const [detailTab, setDetailTab] = useState<'basic' | 'work' | 'docs' | 'placement' | 'comm' | 'extra'>('basic')

  return (
    <>
      <tr className="hover:bg-[#f0f4ff] cursor-pointer transition-colors" onClick={onToggle}>
        <td className="px-3 py-2.5 text-[12px] text-[#86868b] font-mono truncate">{c.id}</td>
        <td className="px-3 py-2.5 text-[13px] font-semibold text-[#1d1d1f] truncate" title={v(c.full_name)}>{v(c.full_name)}</td>
        <td className="px-3 py-2.5 text-[13px] text-[#424245]">{v(c.nationality)}</td>
        <td className="px-3 py-2.5 text-[13px] text-[#424245] truncate">{v(c.current_location)}</td>
        <td className="px-3 py-2.5 text-[13px] text-[#424245] truncate" title={v(c.email)}>{v(c.email)}</td>
        <td className="px-3 py-2.5 text-[13px] text-[#424245] truncate">{v(c.mobile_phone)}</td>
        <td className="px-3 py-2.5 text-[13px] text-[#424245] truncate">{v(c.target)}</td>
        <td className="px-3 py-2.5 text-[13px] text-[#424245] truncate">{v(c.desired_salary)}</td>
        <td className="px-3 py-2.5 text-[13px] text-[#424245] whitespace-nowrap">{v(c.start_date)}</td>
        <td className="px-3 py-2.5"
          style={{ position: 'sticky', right: 0, background: '#fff', zIndex: 10, boxShadow: '-2px 0 4px rgba(0,0,0,0.04)' }}
          onClick={e => e.stopPropagation()}>
          <select
            className={`text-[11px] px-2 py-1 rounded-full font-semibold border-0 cursor-pointer ${statusColors[c.status] ?? 'bg-gray-100 text-gray-600'}`}
            value={c.status}
            onChange={e => onStatusChange(c.id, e.target.value)}>
            {STATUS_VALUES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </td>
      </tr>

      {expanded && (
        <tr>
          <td colSpan={10} className="p-0">
            <div className="py-4 px-6" style={{ background: '#f8f9ff', borderLeft: '3px solid #3b82f6' }}>
              {/* Section tabs */}
              <div className="flex gap-1 mb-4 flex-wrap">
                {([
                  { key: 'basic', label: '기본정보' },
                  { key: 'work', label: '업무정보' },
                  { key: 'docs', label: '서류/비자' },
                  { key: 'placement', label: '배치이력' },
                  { key: 'comm', label: '커뮤니케이션' },
                  { key: 'extra', label: '메모/기타' },
                ] as const).map(t => (
                  <button key={t.key} type="button" onClick={() => setDetailTab(t.key)}
                    className={`px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-colors ${
                      detailTab === t.key
                        ? 'bg-[#3b82f6] text-white'
                        : 'bg-white text-[#424245] border border-[#e5e5e7] hover:bg-gray-50'
                    }`}>
                    {t.label}
                  </button>
                ))}
              </div>

              {/* Section content */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-x-8 gap-y-2">
                {detailTab === 'basic' && <>
                  <DL label="ID" value={c.id} />
                  <DL label="Full Name" value={v(c.full_name)} />
                  <DL label="Nationality" value={v(c.nationality)} />
                  <DL label="Gender" value={v(c.gender)} />
                  <DL label="Date of Birth" value={v(c.dob)} />
                  <DL label="Current Location" value={v(c.current_location)} />
                  <DL label="Email" value={v(c.email)} />
                  <DL label="Mobile Phone" value={v(c.mobile_phone)} />
                  <DL label="KakaoTalk" value={v(c.kakaotalk)} />
                  <DL label="Ancestry" value={v(c.ancestry)} />
                  <DL label="Created" value={fmtDate(c.created_at)} />
                  <DL label="Updated" value={fmtDate(c.updated_at)} />
                </>}

                {detailTab === 'work' && <>
                  <DL label="Target" value={v(c.target)} />
                  <DL label="Certification" value={v(c.certification)} />
                  <DL label="Experience" value={v(c.experience)} />
                  <DL label="E-Visa" value={v(c.e_visa)} />
                  <DL label="Desired Salary" value={v(c.desired_salary)} />
                  <DL label="Current Salary" value={v(c.current_salary)} />
                  <DL label="Start Date" value={v(c.start_date)} />
                  <DL label="Employment" value={v(c.employment)} />
                  <DL label="Area Prefs" value={v(c.area_prefs)} />
                  <DL label="Job Prefs" value={v(c.job_prefs)} />
                  <DL label="Housing" value={v(c.housing)} />
                  <DL label="ARC Holders" value={v(c.arc_holders)} />
                </>}

                {detailTab === 'docs' && <>
                  <DL label="Documents" value={v(c.documents)} />
                  <DL label="Criminal Record" value={v(c.criminal_record)} />
                  <DL label="Passport" value={v(c.passport)} />
                  <DL label="Reference" value={v(c.reference)} />
                  <DL label="Source" value={v(c.source)} />
                  <DL label="Korean Criminal Record" value={v(c.korean_criminal_record)} />
                  <DL label="Consent" value={v(c.consent)} />
                  <DL label="Fact Check" value={v(c.fact_check)} />
                </>}

                {detailTab === 'placement' && <>
                  <DL label="Contract Offered" value={v(c.contract_offered)} />
                  <DL label="Contract Progress" value={v(c.contract_progress)} />
                  <DL label="Placed Company" value={v(c.placed_company)} />
                  <DL label="Placed Salary" value={v(c.placed_salary)} />
                  <DL label="Start Month" value={v(c.start_month)} />
                  <DL label="Referral Fee" value={v(c.referral_fee)} />
                  <DL label="Process Date" value={v(c.process_date)} />
                  <DL label="Past Placement" value={v(c.past_placement)} />
                </>}

                {detailTab === 'comm' && <>
                  <DL label="Email Contract" value={v(c.email_contract)} />
                  <DL label="Email Immigration" value={v(c.email_immigration)} />
                  <DL label="Email Overseas" value={v(c.email_overseas)} />
                  <DL label="Email Transition" value={v(c.email_transition)} />
                  <DL label="Email Arrival" value={v(c.email_arrival)} />
                  <DL label="Gmail Message ID" value={v(c.gmail_message_id)} />
                  <DL label="Last Activity" value={fmtDate(c.last_activity)} />
                  <DL label="Assigned To" value={v(c.assigned_to)} />
                  <DL label="Inbox Status" value={v(c.inbox_status)} />
                </>}

                {detailTab === 'extra' && <>
                  <DL label="Recruiter Memo" value={v(c.recruiter_memo)} />
                  <DL label="Notes" value={v(c.notes) || v(c.admin_notes)} />
                  <DL label="Preferences" value={v(c.preferences)} />
                  <DL label="Dislikes" value={v(c.dislikes)} />
                  <DL label="Residence Type" value={v(c.residence_type)} />
                  <DL label="Start Detail" value={v(c.start_detail)} />
                  <DL label="Target Level" value={v(c.target_level)} />
                  <DL label="Housing Type" value={v(c.housing_type)} />
                  <DL label="Housing Detail" value={v(c.housing_detail)} />
                  <DL label="Education Level" value={v(c.education_level)} />
                  <DL label="Major" value={v(c.major)} />
                  <DL label="Interview Time" value={v(c.interview_time)} />
                  <DL label="Health Info" value={v(c.health_info)} />
                  <DL label="Personal Consideration" value={v(c.personal_consideration)} />
                  <DL label="Piercings" value={v(c.piercings)} />
                  <DL label="Dependents" value={v(c.dependents)} />
                  <DL label="Pets" value={v(c.pets)} />
                  <DL label="Married" value={v(c.married)} />
                  <DL label="Religion" value={v(c.religion)} />
                  <DL label="Target Age" value={v(c.target_age)} />
                </>}
              </div>

              {/* 빈 섹션 안내 */}
              {detailTab !== 'basic' && detailTab !== 'work' && (
                <NoDataHint c={c} tab={detailTab} />
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

/** 빈 섹션 힌트 */
function NoDataHint({ c, tab }: { c: Candidate; tab: string }) {
  const fieldMap: Record<string, string[]> = {
    docs: ['documents', 'criminal_record', 'passport', 'reference', 'korean_criminal_record', 'consent', 'fact_check'],
    placement: ['placed_company', 'placed_salary', 'referral_fee', 'process_date', 'past_placement', 'contract_offered', 'contract_progress'],
    comm: ['email_contract', 'email_immigration', 'email_overseas', 'email_transition', 'email_arrival', 'gmail_message_id', 'assigned_to'],
    extra: ['recruiter_memo', 'notes', 'preferences', 'dislikes', 'education_level', 'major', 'health_info'],
  }
  const fields = fieldMap[tab] || []
  const hasData = fields.some(f => {
    const val = c[f]
    return val && String(val).trim() !== '' && String(val).trim() !== 'None' && String(val).trim() !== 'N'
  })
  if (hasData) return null
  return <p className="text-[12px] text-[#86868b] mt-3 italic">입력된 데이터가 없습니다.</p>
}

/** Detail field — 빈 값은 렌더링하지 않음 */
function DL({ label, value }: { label: string; value: string }) {
  if (!value) return null
  return (
    <div className="text-[13px]">
      <span className="text-[#86868b] font-medium">{label}</span>
      <p className="text-[#1d1d1f] mt-0.5 break-words">{value}</p>
    </div>
  )
}
