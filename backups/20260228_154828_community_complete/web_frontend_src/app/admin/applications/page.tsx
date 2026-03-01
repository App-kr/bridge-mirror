'use client'

/**
 * /admin/applications — Applications Management
 * 구직자 + 구인자 접수 통합 목록
 * 상태: NEW → REVIEWING → VERIFIED → MATCHED → PLACED → REJECTED
 */

import { useCallback, useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

const STATUS_FLOW = ['pending', 'reviewing', 'verified', 'matched', 'placed', 'rejected'] as const
type AppStatus = typeof STATUS_FLOW[number]

interface Application {
  id: string
  type: 'candidate' | 'employer'
  name: string
  email: string
  status: string
  school_name?: string
  created_at: string
  updated_at?: string
}

function AdminNav({ active }: { active: string }) {
  const items = [
    { href: '/admin',              label: 'Ad Posts',     icon: '📢' },
    { href: '/admin/posts',        label: 'Posts',        icon: '📝' },
    { href: '/admin/interviews',   label: 'Interviews',   icon: '🎥' },
    { href: '/admin/applications', label: 'Applications', icon: '📋' },
    { href: '/admin/payments',     label: 'Payments',     icon: '💳' },
    { href: '/admin/candidates',   label: 'Candidates',   icon: '👥' },
  ]
  return (
    <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
      {items.map((nav) => (
        <a key={nav.href} href={nav.href}
          className={`card !p-3 text-center text-sm font-medium transition-all
            ${nav.href === active
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'hover:border-blue-300 text-gray-600 hover:text-blue-600'}`}>
          <span className="text-lg block mb-1">{nav.icon}</span>
          {nav.label}
        </a>
      ))}
    </div>
  )
}

const statusColors: Record<string, string> = {
  pending:   'bg-yellow-50 text-yellow-700 border-yellow-200',
  reviewing: 'bg-blue-50 text-blue-700 border-blue-200',
  verified:  'bg-emerald-50 text-emerald-700 border-emerald-200',
  matched:   'bg-violet-50 text-violet-700 border-violet-200',
  placed:    'bg-green-50 text-green-700 border-green-200',
  rejected:  'bg-red-50 text-red-700 border-red-200',
  Active:    'bg-emerald-50 text-emerald-700 border-emerald-200',
}

export default function AdminApplicationsPage() {
  const [adminKey, setAdminKey] = useState('')
  const [keyInput, setKeyInput] = useState('')
  const [authed, setAuthed] = useState(false)

  const [applications, setApplications] = useState<Application[]>([])
  const [tab, setTab] = useState<'all' | 'candidate' | 'employer'>('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  const headers = useCallback((): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (adminKey) h['x-admin-key'] = adminKey
    return h
  }, [adminKey])

  const fetchApplications = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/applications`, { headers: headers() })
      if (res.status === 403) { setError('관리자 키가 올바르지 않습니다.'); setAuthed(false); return }
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Error')
      setApplications(json.data ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => {
    if (authed) fetchApplications()
  }, [authed, fetchApplications])

  const updateStatus = async (id: string, type: string, newStatus: string) => {
    try {
      const res = await fetch(`${API}/api/admin/applications/${id}`, {
        method: 'PATCH',
        headers: headers(),
        body: JSON.stringify({ status: newStatus, type }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`Application ${id} → ${newStatus}`)
      fetchApplications()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  // Auth screen
  if (!authed) {
    return (
      <div className="max-w-sm mx-auto mt-32 space-y-6 text-center">
        <h1 className="text-2xl font-bold text-gray-900">관리자 인증</h1>
        <p className="text-gray-500 text-sm">ADMIN_API_KEY를 입력하세요</p>
        <input type="password" className="input text-center" placeholder="Admin key"
          value={keyInput} onChange={(e) => setKeyInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { setAdminKey(keyInput); setAuthed(true) } }} />
        <button className="btn-primary w-full"
          onClick={() => { setAdminKey(keyInput); setAuthed(true) }}>접속</button>
      </div>
    )
  }

  const filtered = tab === 'all' ? applications : applications.filter((a) => a.type === tab)

  return (
    <div className="space-y-6">
      <AdminNav active="/admin/applications" />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">접수 관리</h1>
          <p className="text-gray-500 text-sm">구직자 + 구인자 통합 목록</p>
        </div>
        <button onClick={fetchApplications} className="text-sm text-blue-600 hover:underline">↻ 새로고침</button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        {(['all', 'candidate', 'employer'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              tab === t ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}>
            {t === 'all' ? `전체 (${applications.length})` :
             t === 'candidate' ? `구직자 (${applications.filter(a => a.type === 'candidate').length})` :
             `구인자 (${applications.filter(a => a.type === 'employer').length})`}
          </button>
        ))}
      </div>

      {actionMsg && (
        <div className="card-flat bg-blue-50 border-blue-200 text-sm text-blue-700 flex justify-between items-center">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg(null)} className="text-blue-500">×</button>
        </div>
      )}

      {loading ? (
        <div className="text-center py-16 text-gray-400 animate-pulse">로딩 중...</div>
      ) : error ? (
        <div className="text-center py-16 text-red-500">{error}</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-400">접수 내역이 없습니다.</div>
      ) : (
        <div className="space-y-2">
          {filtered.map((app) => (
            <div key={`${app.type}-${app.id}`} className="card !py-3 flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`badge text-[10px] border ${
                    app.type === 'candidate' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-orange-50 text-orange-700 border-orange-200'
                  }`}>{app.type === 'candidate' ? '구직' : '구인'}</span>
                  <span className={`badge text-[10px] border ${statusColors[app.status] ?? 'bg-gray-50 text-gray-600 border-gray-200'}`}>
                    {app.status}
                  </span>
                  <span className="font-semibold text-gray-900 truncate">{app.name || 'N/A'}</span>
                </div>
                <p className="text-xs text-gray-400">
                  {app.email || 'No email'}
                  {app.school_name && ` · ${app.school_name}`}
                  {' · '}
                  {new Date(app.created_at).toLocaleDateString('ko-KR')}
                </p>
              </div>
              <select
                className="text-xs border border-gray-200 rounded px-2 py-1 bg-white text-gray-700"
                value={app.status}
                onChange={(e) => updateStatus(app.id, app.type, e.target.value)}
              >
                {STATUS_FLOW.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
                <option value="Active">Active</option>
              </select>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
