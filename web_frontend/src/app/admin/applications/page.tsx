'use client'

/**
 * /admin/applications — 업체관리 (구인자 전용)
 * 10-column table + Word-style detail + region normalization
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL

const STATUS_FLOW = ['new', 'pending', 'reviewing', 'verified', 'matched', 'placed', 'rejected'] as const

interface EmployerApp {
  id: string
  type: 'employer'
  name: string
  email: string
  status: string
  created_at: string
  school_name?: string
  contact_name?: string | null
  job_code?: string | null
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

const statusColors: Record<string, string> = {
  new:       'bg-sky-100 text-sky-700',
  pending:   'bg-yellow-100 text-yellow-700',
  reviewing: 'bg-blue-100 text-blue-700',
  verified:  'bg-emerald-100 text-emerald-700',
  matched:   'bg-violet-100 text-violet-700',
  placed:    'bg-green-100 text-green-700',
  rejected:  'bg-red-100 text-red-700',
  Active:    'bg-emerald-100 text-emerald-700',
}

/** 지역 정규화 */
const REGION_NORMALIZE: Record<string, string> = {
  '경기남부': '경기', '경기북부': '경기',
  '서울남동': '서울', '서울남서': '서울', '서울북동': '서울', '서울북서': '서울',
}

function extractProvince(loc: string | null | undefined): string {
  if (!loc) return ''
  const s = loc.trim()
  const match = s.match(/^(서울[남북][동서]?|경기[남북]부|서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주|Seoul|Busan|Daegu|Incheon|Gwangju|Daejeon|Ulsan|Sejong|Gyeonggi|Gangwon|Chungbuk|Chungnam|Jeonbuk|Jeonnam|Gyeongbuk|Gyeongnam|Jeju)/i)
  if (match) {
    const raw = match[1]
    return REGION_NORMALIZE[raw] || raw
  }
  const parts = s.split(',')
  if (parts.length > 1) {
    const last = parts[parts.length - 1]?.trim() || ''
    return REGION_NORMALIZE[last] || last
  }
  return ''
}

function extractCity(loc: string | null | undefined): string {
  if (!loc) return ''
  const s = loc.trim()
  const krMatch = s.match(/(?:서울[남북][동서]?|경기[남북]부|서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)\s*(.+?)(?:\s|$)/)
  if (krMatch) return krMatch[1].trim()
  const parts = s.split(',').map(p => p.trim())
  if (parts.length >= 2) return parts[0]
  return ''
}

function extractAge(age: string | null | undefined): string[] {
  if (!age) return []
  const result: string[] = []
  const l = age.toLowerCase()
  if (l.includes('pre-k') || l.includes('pre k') || l.includes('영아') || l.includes('유아')) result.push('Pre-K')
  if (l.includes('kindergarten') || l.includes('유치원')) result.push('Kindergarten')
  if (l.includes('elementary') || l.includes('초등')) result.push('Elementary')
  if (l.includes('middle') || l.includes('중학')) result.push('Middle')
  if (l.includes('high') || l.includes('고등') || l.includes('고교')) result.push('High')
  if (l.includes('adult') || l.includes('성인')) result.push('Adult')
  return result
}

/** 빈 값 → 공백 */
function v(s: string | null | undefined): string {
  if (!s || s.trim() === '' || s.trim() === 'None') return ''
  return s.trim()
}

export default function AdminApplicationsPage() {
  const { authed, login, headers, waking } = useAdminAuth()

  const [employers, setEmployers] = useState<EmployerApp[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)

  const [viewMode, setViewMode] = useState<'default' | 'school'>('default')

  const [filterProvince, setFilterProvince] = useState('')
  const [filterCity, setFilterCity] = useState('')
  const [filterAge, setFilterAge] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [searchText, setSearchText] = useState('')

  const fetchApplications = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/applications`, { headers: headers() })
      if (res.status === 403) {
        const errBody = await res.json().catch(() => ({}))
        if (errBody.error?.includes?.('Access denied')) {
          setError('Access denied. Retrying...')
          const k = sessionStorage.getItem('bridge_admin_key') || ''
          await fetch(`${API}/api/admin/reset-blacklist`, { method: 'POST', headers: { 'x-admin-key': k } }).catch(() => {})
          setTimeout(() => window.location.reload(), 3000)
          return
        }
        setError('Invalid admin key.')
        sessionStorage.removeItem('bridge_admin_key')
        return
      }
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Error')
      const all = json.data ?? []
      setEmployers(all.filter((a: EmployerApp) => a.type === 'employer'))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => {
    if (authed) fetchApplications()
  }, [authed, fetchApplications])

  const updateStatus = async (id: string, newStatus: string) => {
    try {
      const res = await fetch(`${API}/api/admin/applications/${id}`, {
        method: 'PATCH', headers: headers(),
        body: JSON.stringify({ status: newStatus, type: 'employer' }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`#${id} → ${newStatus}`)
      setTimeout(() => setActionMsg(null), 3000)
      fetchApplications()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  const provinceOptions = useMemo(() => {
    const set = new Set<string>()
    employers.forEach(e => {
      const p = extractProvince(e.location)
      if (p) set.add(p)
    })
    return Array.from(set).sort()
  }, [employers])

  const cityOptions = useMemo(() => {
    const set = new Set<string>()
    const src = filterProvince
      ? employers.filter(e => extractProvince(e.location) === filterProvince)
      : employers
    src.forEach(e => {
      const c = extractCity(e.location)
      if (c) set.add(c)
    })
    return Array.from(set).sort()
  }, [employers, filterProvince])

  const ageOptions = useMemo(() => {
    const set = new Set<string>()
    employers.forEach(e => extractAge(e.teaching_age).forEach(a => set.add(a)))
    return Array.from(set).sort()
  }, [employers])

  const statusOptions = useMemo(() => {
    const set = new Set<string>()
    employers.forEach(e => { if (e.status) set.add(e.status) })
    return Array.from(set).sort()
  }, [employers])

  const filtered = useMemo(() => {
    return employers.filter(e => {
      if (filterProvince && extractProvince(e.location) !== filterProvince) return false
      if (filterCity && !extractCity(e.location).includes(filterCity)) return false
      if (filterAge && !extractAge(e.teaching_age).includes(filterAge)) return false
      if (filterStatus && e.status !== filterStatus) return false
      if (searchText) {
        const q = searchText.toLowerCase()
        const hay = [e.school_name, e.name, e.email, e.location, e.phone].filter(Boolean).join(' ').toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  }, [employers, filterProvince, filterCity, filterAge, filterStatus, searchText])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  const hasFilters = !!(filterProvince || filterCity || filterAge || filterStatus || searchText)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[#1d1d1f]">업체관리</h1>
          <p className="text-sm text-[#86868b] mt-0.5">
            {hasFilters ? `${filtered.length} / ${employers.length}건` : `${employers.length}건`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {actionMsg && <span className="text-sm text-green-600 font-medium">{actionMsg}</span>}
          <button type="button" onClick={fetchApplications} className="text-sm text-[#0071e3] hover:underline font-medium">새로고침</button>
        </div>
      </div>

      {/* View Toggle + Filters */}
      <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex bg-gray-100 rounded-xl p-0.5">
            <button type="button" onClick={() => setViewMode('default')}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                viewMode === 'default' ? 'bg-white text-[#1d1d1f] shadow-sm' : 'text-[#86868b] hover:text-[#424245]'
              }`}>
              기본보기
            </button>
            <button type="button" onClick={() => setViewMode('school')}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                viewMode === 'school' ? 'bg-white text-[#1d1d1f] shadow-sm' : 'text-[#86868b] hover:text-[#424245]'
              }`}>
              학원 &middot; 메일
            </button>
          </div>

          <div className="h-6 w-px bg-gray-200" />

          <input
            className="px-4 py-2 text-sm border border-gray-200 rounded-xl w-48 focus:outline-none focus:ring-2 focus:ring-blue-400"
            placeholder="학원명, 이름, 이메일..."
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
          />

          <select className="px-3 py-2 text-sm border border-gray-200 rounded-xl bg-white font-medium"
            value={filterProvince} onChange={e => { setFilterProvince(e.target.value); setFilterCity('') }}>
            <option value="">전체 지역</option>
            {provinceOptions.map(r => <option key={r} value={r}>{r}</option>)}
          </select>

          <select className="px-3 py-2 text-sm border border-gray-200 rounded-xl bg-white font-medium"
            value={filterCity} onChange={e => setFilterCity(e.target.value)}>
            <option value="">전체 도시</option>
            {cityOptions.map(c => <option key={c} value={c}>{c}</option>)}
          </select>

          <select className="px-3 py-2 text-sm border border-gray-200 rounded-xl bg-white font-medium"
            value={filterAge} onChange={e => setFilterAge(e.target.value)}>
            <option value="">전체 대상</option>
            {ageOptions.map(a => <option key={a} value={a}>{a}</option>)}
          </select>

          <select className="px-3 py-2 text-sm border border-gray-200 rounded-xl bg-white font-medium"
            value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
            <option value="">전체 상태</option>
            {statusOptions.map(s => <option key={s} value={s}>{s}</option>)}
          </select>

          {hasFilters && (
            <button type="button" onClick={() => { setFilterProvince(''); setFilterCity(''); setFilterAge(''); setFilterStatus(''); setSearchText('') }}
              className="text-sm text-red-500 hover:text-red-700 font-medium">
              초기화
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-600 text-sm rounded-2xl">{error}</div>
      )}

      {loading ? (
        <div className="text-center py-16 text-[#86868b] animate-pulse text-sm">로딩 중...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-[#86868b] text-sm">
          {hasFilters ? '필터 조건에 맞는 접수가 없습니다.' : '구인 접수 내역이 없습니다.'}
        </div>
      ) : viewMode === 'default' ? (
        /* ── 기본보기: 10-column table ── */
        <div className="bg-white border border-[#e5e5e7] rounded-2xl overflow-hidden relative">
          <div className="overflow-x-auto">
            <table className="w-full" style={{ tableLayout: 'fixed', minWidth: '1170px' }}>
              <colgroup>
                <col style={{ width: '90px' }} />
                <col style={{ width: '60px' }} />
                <col style={{ width: '80px' }} />
                <col style={{ width: '180px' }} />
                <col style={{ width: '180px' }} />
                <col style={{ width: '130px' }} />
                <col style={{ width: '120px' }} />
                <col style={{ width: '140px' }} />
                <col style={{ width: '100px' }} />
                <col style={{ width: '90px' }} />
              </colgroup>
              <thead>
                <tr className="bg-[#f5f5f7] text-[11px] text-[#86868b] uppercase tracking-wider" style={{ position: 'sticky', top: 0, zIndex: 20 }}>
                  <th className="px-3 py-3 text-left font-semibold">No.</th>
                  <th className="px-3 py-3 text-left font-semibold">지역</th>
                  <th className="px-3 py-3 text-left font-semibold">도시</th>
                  <th className="px-3 py-3 text-left font-semibold">업체명</th>
                  <th className="px-3 py-3 text-left font-semibold">이메일</th>
                  <th className="px-3 py-3 text-left font-semibold">연락처</th>
                  <th className="px-3 py-3 text-left font-semibold">Teaching Age</th>
                  <th className="px-3 py-3 text-left font-semibold">급여</th>
                  <th className="px-3 py-3 text-left font-semibold">시작일</th>
                  <th className="px-3 py-3 text-left font-semibold" style={{ position: 'sticky', right: 0, background: '#f5f5f7', zIndex: 21 }}>상태</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#f0f0f2]">
                {filtered.map(app => (
                  <DefaultRow key={app.id} app={app} expanded={expanded === app.id}
                    onToggle={() => setExpanded(expanded === app.id ? null : app.id)}
                    onStatusChange={updateStatus} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* ── 학원·메일 보기 ── */
        <div className="bg-white border border-[#e5e5e7] rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px]">
              <thead className="bg-[#f5f5f7] text-[11px] text-[#86868b] uppercase tracking-wider" style={{ position: 'sticky', top: 0, zIndex: 20 }}>
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">학원명</th>
                  <th className="px-4 py-3 text-left font-semibold">담당자</th>
                  <th className="px-4 py-3 text-left font-semibold">이메일</th>
                  <th className="px-4 py-3 text-left font-semibold">전화번호</th>
                  <th className="px-4 py-3 text-left font-semibold">지역</th>
                  <th className="px-4 py-3 text-left font-semibold">도시</th>
                  <th className="px-4 py-3 text-left font-semibold">상태</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#f0f0f2]">
                {filtered.map(app => (
                  <SchoolRow key={app.id} app={app} onStatusChange={updateStatus} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── 기본보기 행: 10 columns + Word-style expand ── */
function DefaultRow({ app, expanded, onToggle, onStatusChange }: {
  app: EmployerApp; expanded: boolean; onToggle: () => void
  onStatusChange: (id: string, status: string) => void
}) {
  const province = extractProvince(app.location)
  const city = extractCity(app.location)

  return (
    <>
      <tr className="hover:bg-[#fafafa] cursor-pointer transition-colors" onClick={onToggle}>
        <td className="px-3 py-2.5 text-[12px] text-[#86868b] font-mono truncate" title={v(app.job_code) || app.id}>{v(app.job_code) || app.id}</td>
        <td className="px-3 py-2.5 text-[13px] text-[#424245]">{province}</td>
        <td className="px-3 py-2.5 text-[13px] text-[#424245] truncate">{city}</td>
        <td className="px-3 py-2.5 text-[13px] font-semibold text-[#1d1d1f] truncate" title={v(app.school_name) || v(app.name)}>
          {v(app.school_name) || v(app.name)}
        </td>
        <td className="px-3 py-2.5 text-[13px] text-[#424245] truncate" title={v(app.email)}>
          {v(app.email)}
        </td>
        <td className="px-3 py-2.5 text-[13px] text-[#424245] truncate">{v(app.phone)}</td>
        <td className="px-3 py-2.5 text-[13px] text-[#424245] truncate" title={v(app.teaching_age)}>
          {v(app.teaching_age)}
        </td>
        <td className="px-3 py-2.5 text-[13px] text-[#424245] truncate" title={v(app.salary_raw)}>
          {v(app.salary_raw)}
        </td>
        <td className="px-3 py-2.5 text-[13px] text-[#424245] whitespace-nowrap">{v(app.start_date)}</td>
        <td className="px-3 py-2.5" style={{ position: 'sticky', right: 0, background: '#fff', zIndex: 10, boxShadow: '-2px 0 4px rgba(0,0,0,0.04)' }} onClick={e => e.stopPropagation()}>
          <select
            className={`text-[11px] px-2 py-1 rounded-full font-semibold border-0 cursor-pointer ${statusColors[app.status] ?? 'bg-gray-100 text-gray-600'}`}
            value={app.status}
            onChange={e => onStatusChange(app.id, e.target.value)}>
            {STATUS_FLOW.map(s => <option key={s} value={s}>{s}</option>)}
            <option value="Active">Active</option>
          </select>
        </td>
      </tr>

      {expanded && (
        <tr>
          <td colSpan={10} className="p-0">
            <div className="bg-[#fafafa] border-t border-[#e5e5e7] px-6 py-5">
              <div className="font-mono text-[13px] leading-relaxed text-[#1d1d1f] space-y-1">
                <p className="font-bold text-[15px] mb-3">{v(app.job_code) ? `${app.job_code}` : `#${app.id}`}</p>
                <DL label="Location" value={[province, city].filter(Boolean).join(' ') || v(app.location)} />
                <DL label="Starting Date" value={v(app.start_date)} />
                <DL label="Teaching Age" value={v(app.teaching_age)} />
                <DL label="Working Hours" value={v(app.working_hours)} />
                <DL label="Monthly Salary" value={v(app.salary_raw)} />
                <DL label="Housing" value={v(app.housing_type)} />
                <DL label="Vacation" value={v(app.vacation)} />
                <DL label="Benefits" value={v(app.benefits)} />
                <DL label="Contact" value={
                  [v(app.contact_name) || v(app.name), v(app.phone), v(app.email)]
                    .filter(Boolean).join(' / ')
                } />
                {v(app.memo) && (
                  <div className="mt-3 pt-3 border-t border-[#e5e5e7]">
                    <span className="font-semibold text-[#86868b]">Memo: </span>
                    <span className="whitespace-pre-wrap">{v(app.memo)}</span>
                  </div>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

function DL({ label, value }: { label: string; value: string }) {
  if (!value) return null
  return (
    <p>
      <span className="font-semibold text-[#86868b] inline-block" style={{ minWidth: '140px' }}>{label}:</span>
      <span>{value}</span>
    </p>
  )
}

/* ── 학원·메일 보기 행 ── */
function SchoolRow({ app, onStatusChange }: {
  app: EmployerApp
  onStatusChange: (id: string, status: string) => void
}) {
  return (
    <tr className="hover:bg-[#fafafa] transition-colors">
      <td className="px-4 py-3">
        <span className="font-semibold text-[#1d1d1f] text-sm">{v(app.school_name)}</span>
      </td>
      <td className="px-4 py-3 text-sm text-[#424245]">{v(app.contact_name) || v(app.name)}</td>
      <td className="px-4 py-3 text-sm">
        {v(app.email) ? (
          <a href={`mailto:${app.email}`} className="text-[#0071e3] hover:underline">{app.email}</a>
        ) : ''}
      </td>
      <td className="px-4 py-3 text-sm text-[#424245]">{v(app.phone)}</td>
      <td className="px-4 py-3 text-sm text-[#424245] font-medium">{extractProvince(app.location)}</td>
      <td className="px-4 py-3 text-sm text-[#424245]">{extractCity(app.location)}</td>
      <td className="px-4 py-3">
        <select
          className={`text-[12px] px-2.5 py-1 rounded-full font-semibold border-0 ${statusColors[app.status] ?? 'bg-gray-100 text-gray-600'}`}
          value={app.status}
          onChange={e => onStatusChange(app.id, e.target.value)}>
          {STATUS_FLOW.map(s => <option key={s} value={s}>{s}</option>)}
          <option value="Active">Active</option>
        </select>
      </td>
    </tr>
  )
}
