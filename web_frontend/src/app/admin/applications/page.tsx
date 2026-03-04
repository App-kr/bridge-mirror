'use client'

/**
 * /admin/applications — 구인자 접수 관리
 * 구인자(employer) 접수 목록 전용 (구직자는 /admin/candidates)
 */

import { useCallback, useEffect, useState } from 'react'
import AdminNav from '@/components/admin/AdminNav'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'

import { API_URL } from '@/lib/api'

const API = API_URL

const STATUS_FLOW = ['pending', 'reviewing', 'verified', 'matched', 'placed', 'rejected'] as const

interface EmployerApp {
  id: string
  type: 'employer'
  name: string
  email: string
  status: string
  created_at: string
  updated_at?: string
  school_name?: string
  phone?: string | null
  location?: string | null
  start_date?: string | null
  vacancies?: string | null
  teaching_age?: string | null
  working_hours?: string | null
  salary_raw?: string | null
  housing_type?: string | null
  housing_detail?: string | null
  travel_support?: string | null
  benefits?: string | null
  vacation?: string | null
  memo?: string | null
  notes?: string | null
  assigned_to?: string | null
}

const statusColors: Record<string, string> = {
  pending:   'bg-yellow-100 text-yellow-700',
  reviewing: 'bg-blue-100 text-blue-700',
  verified:  'bg-emerald-100 text-emerald-700',
  matched:   'bg-violet-100 text-violet-700',
  placed:    'bg-green-100 text-green-700',
  rejected:  'bg-red-100 text-red-700',
  Active:    'bg-emerald-100 text-emerald-700',
  processing:'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
}

export default function AdminApplicationsPage() {
  const { authed, login, headers, waking } = useAdminAuth()

  const [employers, setEmployers] = useState<EmployerApp[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)

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
      setActionMsg(`${id} → ${newStatus}`)
      setTimeout(() => setActionMsg(null), 3000)
      fetchApplications()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="max-w-[1400px] mx-auto px-4 py-6">
      <AdminNav active="/admin/applications" />

      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-lg font-bold text-gray-900">구인자 접수 관리</h1>
          <p className="text-xs text-gray-500">{employers.length}건의 구인 접수</p>
        </div>
        <div className="flex items-center gap-3">
          {actionMsg && <span className="text-xs text-green-600 font-medium">{actionMsg}</span>}
          <button type="button" onClick={fetchApplications} className="text-sm text-blue-600 hover:underline">↻ 새로고침</button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg">{error}</div>
      )}

      {loading ? (
        <div className="text-center py-16 text-gray-400 animate-pulse">로딩 중...</div>
      ) : employers.length === 0 ? (
        <div className="text-center py-16 text-gray-400">구인 접수 내역이 없습니다.</div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-3 py-2 text-left">업체명</th>
                <th className="px-3 py-2 text-left">담당자</th>
                <th className="px-3 py-2 text-left">연락처</th>
                <th className="px-3 py-2 text-left">위치</th>
                <th className="px-3 py-2 text-left">급여</th>
                <th className="px-3 py-2 text-left">접수일</th>
                <th className="px-3 py-2 text-left">상태</th>
                <th className="px-3 py-2 text-left w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {employers.map((app) => {
                const isExpanded = expanded === app.id
                return (
                  <EmployerRow
                    key={app.id}
                    app={app}
                    expanded={isExpanded}
                    onToggle={() => setExpanded(isExpanded ? null : app.id)}
                    onStatusChange={updateStatus}
                  />
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function EmployerRow({ app, expanded, onToggle, onStatusChange }: {
  app: EmployerApp
  expanded: boolean
  onToggle: () => void
  onStatusChange: (id: string, status: string) => void
}) {
  return (
    <>
      <tr className="hover:bg-gray-50 cursor-pointer" onClick={onToggle}>
        <td className="px-3 py-2">
          <span className="font-medium text-gray-900">{app.school_name || app.name}</span>
        </td>
        <td className="px-3 py-2 text-xs text-gray-600">
          {app.school_name && app.name ? app.name : '—'}
        </td>
        <td className="px-3 py-2 text-xs text-gray-500">
          <div>{app.email || '—'}</div>
          {app.phone && <div className="text-gray-400">{app.phone}</div>}
        </td>
        <td className="px-3 py-2 text-xs">{app.location || '—'}</td>
        <td className="px-3 py-2 text-xs">{app.salary_raw || '—'}</td>
        <td className="px-3 py-2 text-xs text-gray-500">
          {app.created_at ? new Date(app.created_at).toLocaleDateString('ko-KR') : '—'}
        </td>
        <td className="px-3 py-2">
          <select
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColors[app.status] ?? 'bg-gray-100 text-gray-600'}`}
            value={app.status}
            onClick={(e) => e.stopPropagation()}
            onChange={(e) => onStatusChange(app.id, e.target.value)}
          >
            {STATUS_FLOW.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
            <option value="Active">Active</option>
          </select>
        </td>
        <td className="px-3 py-2 text-gray-400">{expanded ? '▲' : '▼'}</td>
      </tr>

      {expanded && (
        <tr>
          <td colSpan={8} className="px-4 py-4 bg-gray-50">
            <div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs mb-4">
                <InfoItem label="시작일" value={app.start_date} />
                <InfoItem label="교육대상" value={app.teaching_age} />
                <InfoItem label="근무시간" value={app.working_hours} />
                <InfoItem label="포지션 수" value={app.vacancies} />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs mb-4">
                <InfoItem label="급여" value={app.salary_raw} />
                <InfoItem label="숙소" value={[app.housing_type, app.housing_detail].filter(Boolean).join(' · ') || null} />
                <InfoItem label="복리후생" value={app.benefits} />
                <InfoItem label="교통비" value={app.travel_support} />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs mb-4">
                <InfoItem label="휴가" value={app.vacation} />
                <InfoItem label="담당자" value={app.assigned_to} />
              </div>
              {app.memo && (
                <div className="mb-3 text-xs">
                  <span className="font-medium text-gray-500">메모:</span>
                  <p className="text-gray-700 mt-1 whitespace-pre-wrap">{app.memo}</p>
                </div>
              )}
              {app.notes && (
                <div className="text-xs">
                  <span className="font-medium text-gray-500">관리자 메모:</span>
                  <p className="text-gray-700 mt-1 whitespace-pre-wrap">{app.notes}</p>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

function InfoItem({ label, value }: { label: string; value: string | null | undefined }) {
  const display = value?.trim() || '—'
  return (
    <div>
      <span className="font-medium text-gray-500">{label}</span>
      <p className="text-gray-800 mt-0.5">{display}</p>
    </div>
  )
}
