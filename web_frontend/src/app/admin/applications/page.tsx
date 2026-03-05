'use client'

/**
 * /admin/applications — 업체관리
 * 지역/도시 분리 필터 + 업체명/대상 + 관리자 전용 한글 번역 + 큰 글자
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

/** 지역(시/도) 추출 */
function extractProvince(loc: string | null | undefined): string {
  if (!loc) return ''
  const s = loc.trim()
  const match = s.match(/^(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주|Seoul|Busan|Daegu|Incheon|Gwangju|Daejeon|Ulsan|Sejong|Gyeonggi|Gangwon|Chungbuk|Chungnam|Jeonbuk|Jeonnam|Gyeongbuk|Gyeongnam|Jeju)/i)
  if (match) return match[1]
  const parts = s.split(',')
  if (parts.length > 1) return parts[parts.length - 1]?.trim() || ''
  return ''
}

/** 도시(구/군/시) 추출 */
function extractCity(loc: string | null | undefined): string {
  if (!loc) return ''
  const s = loc.trim()
  // "서울 강남구" → "강남구"
  const krMatch = s.match(/(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)\s*(.+?)(?:\s|$)/)
  if (krMatch) return krMatch[1].trim()
  // "Gangnam-gu, Seoul" → "Gangnam-gu"
  const parts = s.split(',').map(p => p.trim())
  if (parts.length >= 2) return parts[0]
  return ''
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

/** 교육대상 한글 번역 (관리자 전용) */
function translateAge(age: string | null | undefined): string {
  if (!age) return ''
  const map: Record<string, string> = {
    'Pre-K': '영유아',
    'Kindergarten': '유치원',
    'Elementary': '초등',
    'Middle': '중등',
    'High': '고등',
    'Adult': '성인',
  }
  const extracted = extractAge(age)
  if (extracted.length === 0) return age
  return extracted.map(e => map[e] || e).join(', ')
}

export default function AdminApplicationsPage() {
  const { authed, login, headers, waking } = useAdminAuth()

  const [employers, setEmployers] = useState<EmployerApp[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)

  const [viewMode, setViewMode] = useState<'default' | 'school'>('default')

  // 필터: 지역 + 도시 분리
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

  // 지역 옵션
  const provinceOptions = useMemo(() => {
    const set = new Set<string>()
    employers.forEach(e => {
      const p = extractProvince(e.location)
      if (p) set.add(p)
    })
    return Array.from(set).sort()
  }, [employers])

  // 도시 옵션 (선택된 지역 기반)
  const cityOptions = useMemo(() => {
    const set = new Set<string>()
    const filtered = filterProvince
      ? employers.filter(e => extractProvince(e.location) === filterProvince)
      : employers
    filtered.forEach(e => {
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

  // 필터링
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
          {/* View mode toggle */}
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

          {/* 검색 */}
          <input
            className="px-4 py-2 text-sm border border-gray-200 rounded-xl w-48 focus:outline-none focus:ring-2 focus:ring-blue-400"
            placeholder="학원명, 이름, 이메일..."
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
          />

          {/* 지역 필터 */}
          <select className="px-3 py-2 text-sm border border-gray-200 rounded-xl bg-white font-medium"
            value={filterProvince} onChange={e => { setFilterProvince(e.target.value); setFilterCity('') }}>
            <option value="">전체 지역</option>
            {provinceOptions.map(r => <option key={r} value={r}>{r}</option>)}
          </select>

          {/* 도시 필터 */}
          <select className="px-3 py-2 text-sm border border-gray-200 rounded-xl bg-white font-medium"
            value={filterCity} onChange={e => setFilterCity(e.target.value)}>
            <option value="">전체 도시</option>
            {cityOptions.map(c => <option key={c} value={c}>{c}</option>)}
          </select>

          {/* 교육대상 필터 */}
          <select className="px-3 py-2 text-sm border border-gray-200 rounded-xl bg-white font-medium"
            value={filterAge} onChange={e => setFilterAge(e.target.value)}>
            <option value="">전체 대상</option>
            {ageOptions.map(a => <option key={a} value={a}>{a}</option>)}
          </select>

          {/* 상태 필터 */}
          <select className="px-3 py-2 text-sm border border-gray-200 rounded-xl bg-white font-medium"
            value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
            <option value="">전체 상태</option>
            {statusOptions.map(s => <option key={s} value={s}>{s}</option>)}
          </select>

          {hasFilters && (
            <button type="button" onClick={() => { setFilterProvince(''); setFilterCity(''); setFilterAge(''); setFilterStatus(''); setSearchText('') }}
              className="text-sm text-red-500 hover:text-red-700 font-medium">
              필터 초기화
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
        /* ── 기본보기 ── */
        <div className="bg-white border border-[#e5e5e7] rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1100px]">
              <thead className="bg-[#f5f5f7] text-[12px] text-[#86868b] uppercase tracking-wider sticky top-0">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">지역</th>
                  <th className="px-4 py-3 text-left font-semibold">도시</th>
                  <th className="px-4 py-3 text-left font-semibold">업체명</th>
                  <th className="px-4 py-3 text-left font-semibold">대상 (원문)</th>
                  <th className="px-4 py-3 text-left font-semibold">대상 (한글)</th>
                  <th className="px-4 py-3 text-left font-semibold">시작일</th>
                  <th className="px-4 py-3 text-left font-semibold">급여</th>
                  <th className="px-4 py-3 text-left font-semibold">숙소</th>
                  <th className="px-4 py-3 text-left font-semibold">접수일</th>
                  <th className="px-4 py-3 text-left font-semibold">상태</th>
                  <th className="px-4 py-3 text-left w-10"></th>
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
              <thead className="bg-[#f5f5f7] text-[12px] text-[#86868b] uppercase tracking-wider sticky top-0">
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

/* ── 기본보기 행 ── */
function DefaultRow({ app, expanded, onToggle, onStatusChange }: {
  app: EmployerApp; expanded: boolean; onToggle: () => void
  onStatusChange: (id: string, status: string) => void
}) {
  const housing = [app.housing_type, app.housing_detail].filter(v => v && v !== 'None').join(' · ')
  const province = extractProvince(app.location)
  const city = extractCity(app.location)

  return (
    <>
      <tr className="hover:bg-[#fafafa] cursor-pointer transition-colors" onClick={onToggle}>
        <td className="px-4 py-3 text-sm text-[#424245] font-medium">{province || '—'}</td>
        <td className="px-4 py-3 text-sm text-[#424245]">{city || '—'}</td>
        <td className="px-4 py-3">
          <span className="font-semibold text-[#1d1d1f] text-sm">{app.school_name || app.name || '—'}</span>
        </td>
        <td className="px-4 py-3 text-sm text-[#424245] max-w-[180px] truncate" title={app.teaching_age || ''}>
          {app.teaching_age || '—'}
        </td>
        <td className="px-4 py-3 text-sm text-[#0071e3] font-medium max-w-[140px] truncate" title={translateAge(app.teaching_age)}>
          {translateAge(app.teaching_age) || '—'}
        </td>
        <td className="px-4 py-3 text-sm text-[#424245]">{app.start_date || '—'}</td>
        <td className="px-4 py-3 text-sm text-[#424245] max-w-[120px] truncate" title={app.salary_raw || ''}>
          {app.salary_raw || '—'}
        </td>
        <td className="px-4 py-3 text-sm text-[#424245] max-w-[120px] truncate" title={housing}>
          {housing || '—'}
        </td>
        <td className="px-4 py-3 text-sm text-[#86868b] whitespace-nowrap">
          {app.created_at?.slice(0, 10) || '—'}
        </td>
        <td className="px-4 py-3">
          <select
            className={`text-[12px] px-2.5 py-1 rounded-full font-semibold border-0 ${statusColors[app.status] ?? 'bg-gray-100 text-gray-600'}`}
            value={app.status}
            onClick={e => e.stopPropagation()}
            onChange={e => onStatusChange(app.id, e.target.value)}>
            {STATUS_FLOW.map(s => <option key={s} value={s}>{s}</option>)}
            <option value="Active">Active</option>
          </select>
        </td>
        <td className="px-4 py-3 text-[#86868b] text-sm">{expanded ? '▲' : '▼'}</td>
      </tr>

      {expanded && (
        <tr>
          <td colSpan={11} className="px-5 py-5 bg-[#fafafa]">
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Info label="업체명" value={app.school_name} />
                <Info label="담당자" value={app.name} />
                <Info label="이메일" value={app.email} />
                <Info label="전화" value={app.phone} />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Info label="위치" value={app.location} />
                <Info label="시작일" value={app.start_date} />
                <Info label="포지션 수" value={app.vacancies} />
                <Info label="교육대상" value={app.teaching_age} />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Info label="스케줄" value={app.schedule} />
                <Info label="근무시간" value={app.working_hours} />
                <Info label="급여" value={app.salary_raw} />
                <Info label="숙소" value={housing || null} />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Info label="교통비" value={app.travel_support} />
                <Info label="복리후생" value={app.benefits} />
                <Info label="휴가" value={app.vacation} />
                <Info label="병가" value={app.sick_leave} />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Info label="식사" value={app.meal} />
                <Info label="담당자(내부)" value={app.assigned_to} />
              </div>
              {app.memo && app.memo !== 'None' && (
                <div>
                  <span className="font-semibold text-[#86868b] text-sm">메모:</span>
                  <p className="text-[#1d1d1f] text-sm mt-1 whitespace-pre-wrap bg-white p-3 rounded-xl border border-[#e5e5e7]">{app.memo}</p>
                </div>
              )}
              {app.notes && app.notes !== 'None' && (
                <div>
                  <span className="font-semibold text-[#86868b] text-sm">관리자 메모:</span>
                  <p className="text-[#1d1d1f] text-sm mt-1 whitespace-pre-wrap bg-white p-3 rounded-xl border border-[#e5e5e7]">{app.notes}</p>
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
    <tr className="hover:bg-[#fafafa] transition-colors">
      <td className="px-4 py-3">
        <span className="font-semibold text-[#1d1d1f] text-sm">{app.school_name || '—'}</span>
      </td>
      <td className="px-4 py-3 text-sm text-[#424245]">{app.name || '—'}</td>
      <td className="px-4 py-3 text-sm">
        {app.email ? (
          <a href={`mailto:${app.email}`} className="text-[#0071e3] hover:underline">{app.email}</a>
        ) : '—'}
      </td>
      <td className="px-4 py-3 text-sm text-[#424245]">{app.phone || '—'}</td>
      <td className="px-4 py-3 text-sm text-[#424245] font-medium">{extractProvince(app.location) || '—'}</td>
      <td className="px-4 py-3 text-sm text-[#424245]">{extractCity(app.location) || '—'}</td>
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

function Info({ label, value }: { label: string; value: string | null | undefined }) {
  const display = (value && value !== 'None') ? value.trim() : '—'
  return (
    <div>
      <span className="font-semibold text-[#86868b] text-sm">{label}</span>
      <p className="text-[#1d1d1f] text-sm mt-0.5 break-words">{display}</p>
    </div>
  )
}
