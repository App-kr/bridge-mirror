'use client'

/**
 * /admin/applications — 구인자 접수 관리
 * 기본보기 / 학원·메일 보기 전환 + 지역/교육대상/시작일 필터
 * 구직자는 /admin/candidates에서 관리
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import AdminNav from '@/components/admin/AdminNav'
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

/** 지역 키워드 추출 (첫 시/도 단위) */
function extractRegion(loc: string | null | undefined): string {
  if (!loc) return ''
  const s = loc.trim()
  // 한국 시/도 패턴
  const match = s.match(/^(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주|Seoul|Busan|Daegu|Incheon|Gwangju|Daejeon|Ulsan|Sejong|Gyeonggi|Gangwon|Chungbuk|Chungnam|Jeonbuk|Jeonnam|Gyeongbuk|Gyeongnam|Jeju)/i)
  if (match) return match[1]
  // 영어 주소에서 도시 추출
  const parts = s.split(',')
  if (parts.length > 1) return parts[parts.length - 2]?.trim() || s.slice(0, 20)
  return s.slice(0, 10)
}

/** 교육대상 키워드 추출 */
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

export default function AdminApplicationsPage() {
  const { authed, login, headers, waking } = useAdminAuth()

  const [employers, setEmployers] = useState<EmployerApp[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)

  // 보기 모드
  const [viewMode, setViewMode] = useState<'default' | 'school'>('default')

  // 필터
  const [filterRegion, setFilterRegion] = useState('')
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
          setError('일시적으로 차단되었습니다. 자동 재시도 중...')
          const k = sessionStorage.getItem('bridge_admin_key') || ''
          await fetch(`${API}/api/admin/reset-blacklist`, { method: 'POST', headers: { 'x-admin-key': k } }).catch(() => {})
          setTimeout(() => window.location.reload(), 3000)
          return
        }
        setError('관리자 키가 올바르지 않습니다. 다시 로그인해주세요.')
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

  // 필터 옵션 추출
  const regionOptions = useMemo(() => {
    const set = new Set<string>()
    employers.forEach(e => {
      const r = extractRegion(e.location)
      if (r) set.add(r)
    })
    return Array.from(set).sort()
  }, [employers])

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

  // 필터링
  const filtered = useMemo(() => {
    return employers.filter(e => {
      if (filterRegion && !extractRegion(e.location).includes(filterRegion)) return false
      if (filterAge && !extractAge(e.teaching_age).includes(filterAge)) return false
      if (filterStatus && e.status !== filterStatus) return false
      if (searchText) {
        const q = searchText.toLowerCase()
        const hay = [e.school_name, e.name, e.email, e.location, e.phone].filter(Boolean).join(' ').toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  }, [employers, filterRegion, filterAge, filterStatus, searchText])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  const hasFilters = !!(filterRegion || filterAge || filterStatus || searchText)

  return (
    <div className="max-w-[1400px] mx-auto px-4 py-6">
      <AdminNav active="/admin/applications" />

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-lg font-bold text-gray-900">구인자 접수 관리</h1>
          <p className="text-xs text-gray-500">
            {hasFilters ? `${filtered.length} / ${employers.length}건` : `${employers.length}건`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {actionMsg && <span className="text-xs text-green-600 font-medium">{actionMsg}</span>}
          <button type="button" onClick={fetchApplications} className="text-sm text-blue-600 hover:underline">↻ 새로고침</button>
        </div>
      </div>

      {/* View Toggle + Filters */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        {/* View mode toggle */}
        <div className="flex bg-gray-100 rounded-lg p-0.5">
          <button type="button" onClick={() => setViewMode('default')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              viewMode === 'default' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>
            기본보기
          </button>
          <button type="button" onClick={() => setViewMode('school')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              viewMode === 'school' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>
            학원·메일
          </button>
        </div>

        <div className="h-5 w-px bg-gray-200 mx-1" />

        {/* Search */}
        <input
          className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg w-40 focus:outline-none focus:border-blue-400"
          placeholder="학원명, 이름, 이메일..."
          value={searchText}
          onChange={e => setSearchText(e.target.value)}
        />

        {/* Region filter */}
        <select className="px-2 py-1.5 text-xs border border-gray-200 rounded-lg bg-white"
          value={filterRegion} onChange={e => setFilterRegion(e.target.value)}>
          <option value="">전체 지역</option>
          {regionOptions.map(r => <option key={r} value={r}>{r}</option>)}
        </select>

        {/* Teaching age filter */}
        <select className="px-2 py-1.5 text-xs border border-gray-200 rounded-lg bg-white"
          value={filterAge} onChange={e => setFilterAge(e.target.value)}>
          <option value="">전체 대상</option>
          {ageOptions.map(a => <option key={a} value={a}>{a}</option>)}
        </select>

        {/* Status filter */}
        <select className="px-2 py-1.5 text-xs border border-gray-200 rounded-lg bg-white"
          value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
          <option value="">전체 상태</option>
          {statusOptions.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        {hasFilters && (
          <button type="button" onClick={() => { setFilterRegion(''); setFilterAge(''); setFilterStatus(''); setSearchText('') }}
            className="text-xs text-red-500 hover:text-red-700">
            필터 초기화
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg">{error}</div>
      )}

      {loading ? (
        <div className="text-center py-16 text-gray-400 animate-pulse">로딩 중...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          {hasFilters ? '필터 조건에 맞는 접수가 없습니다.' : '구인 접수 내역이 없습니다.'}
        </div>
      ) : viewMode === 'default' ? (
        /* ── 기본보기: 상세 정보 테이블 ── */
        <div className="bg-white border border-gray-200 rounded-xl overflow-x-auto">
          <table className="w-full text-sm min-w-[900px]">
            <thead className="bg-gray-50 text-[11px] text-gray-500 uppercase sticky top-0">
              <tr>
                <th className="px-3 py-2 text-left">업체명</th>
                <th className="px-3 py-2 text-left">위치</th>
                <th className="px-3 py-2 text-left">교육대상</th>
                <th className="px-3 py-2 text-left">시작일</th>
                <th className="px-3 py-2 text-left">급여</th>
                <th className="px-3 py-2 text-left">숙소</th>
                <th className="px-3 py-2 text-left">접수일</th>
                <th className="px-3 py-2 text-left">상태</th>
                <th className="px-3 py-2 text-left w-8"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map(app => (
                <DefaultRow key={app.id} app={app} expanded={expanded === app.id}
                  onToggle={() => setExpanded(expanded === app.id ? null : app.id)}
                  onStatusChange={updateStatus} />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* ── 학원·메일 보기 ── */
        <div className="bg-white border border-gray-200 rounded-xl overflow-x-auto">
          <table className="w-full text-sm min-w-[700px]">
            <thead className="bg-gray-50 text-[11px] text-gray-500 uppercase sticky top-0">
              <tr>
                <th className="px-3 py-2 text-left">학원명</th>
                <th className="px-3 py-2 text-left">담당자</th>
                <th className="px-3 py-2 text-left">이메일</th>
                <th className="px-3 py-2 text-left">전화번호</th>
                <th className="px-3 py-2 text-left">위치</th>
                <th className="px-3 py-2 text-left">상태</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map(app => (
                <SchoolRow key={app.id} app={app} onStatusChange={updateStatus} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

/* ── 기본보기 행 ── */
function DefaultRow({ app, expanded, onToggle, onStatusChange }: {
  app: EmployerApp; expanded: boolean; onToggle: () => void
  onStatusChange: (id: string, status: string) => void
}) {
  const housing = [app.housing_type, app.housing_detail].filter(v => v && v !== 'None').join(' · ')

  return (
    <>
      <tr className="hover:bg-gray-50 cursor-pointer" onClick={onToggle}>
        <td className="px-3 py-2">
          <span className="font-medium text-gray-900 text-xs">{app.school_name || app.name || '—'}</span>
        </td>
        <td className="px-3 py-2 text-xs text-gray-600 max-w-[160px] truncate" title={app.location || ''}>
          {app.location ? extractRegion(app.location) || app.location.slice(0, 20) : '—'}
        </td>
        <td className="px-3 py-2 text-xs text-gray-600 max-w-[180px] truncate" title={app.teaching_age || ''}>
          {app.teaching_age ? extractAge(app.teaching_age).join(', ') || app.teaching_age.slice(0, 25) : '—'}
        </td>
        <td className="px-3 py-2 text-xs text-gray-600">{app.start_date || '—'}</td>
        <td className="px-3 py-2 text-xs text-gray-600 max-w-[120px] truncate" title={app.salary_raw || ''}>
          {app.salary_raw || '—'}
        </td>
        <td className="px-3 py-2 text-xs text-gray-600 max-w-[120px] truncate" title={housing}>
          {housing || '—'}
        </td>
        <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">
          {app.created_at?.slice(0, 10) || '—'}
        </td>
        <td className="px-3 py-2">
          <select
            className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${statusColors[app.status] ?? 'bg-gray-100 text-gray-600'}`}
            value={app.status}
            onClick={e => e.stopPropagation()}
            onChange={e => onStatusChange(app.id, e.target.value)}>
            {STATUS_FLOW.map(s => <option key={s} value={s}>{s}</option>)}
            <option value="Active">Active</option>
          </select>
        </td>
        <td className="px-3 py-2 text-gray-400 text-xs">{expanded ? '▲' : '▼'}</td>
      </tr>

      {expanded && (
        <tr>
          <td colSpan={9} className="px-4 py-4 bg-gray-50/80">
            <div className="space-y-3">
              {/* 기본 정보 */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <Info label="업체명" value={app.school_name} />
                <Info label="담당자" value={app.name} />
                <Info label="이메일" value={app.email} />
                <Info label="전화" value={app.phone} />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <Info label="위치" value={app.location} />
                <Info label="시작일" value={app.start_date} />
                <Info label="포지션 수" value={app.vacancies} />
                <Info label="교육대상" value={app.teaching_age} />
              </div>
              {/* 근무 조건 */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <Info label="스케줄" value={app.schedule} />
                <Info label="근무시간" value={app.working_hours} />
                <Info label="급여" value={app.salary_raw} />
                <Info label="숙소" value={housing || null} />
              </div>
              {/* 복리후생 */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <Info label="교통비" value={app.travel_support} />
                <Info label="복리후생" value={app.benefits} />
                <Info label="휴가" value={app.vacation} />
                <Info label="병가" value={app.sick_leave} />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <Info label="식사" value={app.meal} />
                <Info label="담당자(내부)" value={app.assigned_to} />
              </div>
              {/* 메모 */}
              {app.memo && app.memo !== 'None' && (
                <div className="text-xs">
                  <span className="font-medium text-gray-500">메모:</span>
                  <p className="text-gray-700 mt-1 whitespace-pre-wrap bg-white p-2 rounded border border-gray-100">{app.memo}</p>
                </div>
              )}
              {app.notes && app.notes !== 'None' && (
                <div className="text-xs">
                  <span className="font-medium text-gray-500">관리자 메모:</span>
                  <p className="text-gray-700 mt-1 whitespace-pre-wrap bg-white p-2 rounded border border-gray-100">{app.notes}</p>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

/* ── 학원·메일 보기 행 ── */
function SchoolRow({ app, onStatusChange }: {
  app: EmployerApp
  onStatusChange: (id: string, status: string) => void
}) {
  return (
    <tr className="hover:bg-gray-50">
      <td className="px-3 py-2">
        <span className="font-medium text-gray-900 text-xs">{app.school_name || '—'}</span>
      </td>
      <td className="px-3 py-2 text-xs text-gray-600">{app.name || '—'}</td>
      <td className="px-3 py-2 text-xs">
        {app.email ? (
          <a href={`mailto:${app.email}`} className="text-blue-600 hover:underline">{app.email}</a>
        ) : '—'}
      </td>
      <td className="px-3 py-2 text-xs text-gray-600">{app.phone || '—'}</td>
      <td className="px-3 py-2 text-xs text-gray-500 max-w-[200px] truncate" title={app.location || ''}>
        {app.location ? extractRegion(app.location) || app.location.slice(0, 25) : '—'}
      </td>
      <td className="px-3 py-2">
        <select
          className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${statusColors[app.status] ?? 'bg-gray-100 text-gray-600'}`}
          value={app.status}
          onChange={e => onStatusChange(app.id, e.target.value)}>
          {STATUS_FLOW.map(s => <option key={s} value={s}>{s}</option>)}
          <option value="Active">Active</option>
        </select>
      </td>
    </tr>
  )
}

function Info({ label, value }: { label: string; value: string | null | undefined }) {
  const display = (value && value !== 'None') ? value.trim() : '—'
  return (
    <div>
      <span className="font-medium text-gray-400">{label}</span>
      <p className="text-gray-800 mt-0.5 break-words">{display}</p>
    </div>
  )
}
