'use client'

/**
 * /admin/inbox — 통합 수신함
 * candidates + client_inquiries 통합 목록
 * 채널 필터, 상태 필터, 검색, 벌크 처리
 */

import { useCallback, useEffect, useState } from 'react'
import { useAdminAuth } from '@/hooks/useAdminAuth'

import { API_URL } from '@/lib/api'

const API = API_URL

interface InboxItem {
  id: string
  type: 'candidate' | 'inquiry'
  name: string
  email: string
  nationality: string
  location: string
  area_prefs: string
  source: string
  inbox_status: string
  school_name?: string
  notes: string
  assigned_to: string
  created_at: string
}

const SOURCE_TABS = [
  { key: 'all',         label: '전체' },
  { key: 'website',     label: '웹사이트' },
  { key: 'google_form', label: '구글폼' },
  { key: 'email',       label: '이메일' },
  { key: 'inquiry',     label: '문의' },
]

const STATUS_FILTERS = [
  { key: 'all',        label: '전체',   color: '' },
  { key: 'new',        label: '신규',   color: 'bg-green-100 text-green-700' },
  { key: 'reviewed',   label: '검토',   color: 'bg-blue-100 text-blue-700' },
  { key: 'contacted',  label: '연락',   color: 'bg-yellow-100 text-yellow-700' },
  { key: 'interview',  label: '면접',   color: 'bg-orange-100 text-orange-700' },
  { key: 'hired',      label: '채용',   color: 'bg-emerald-100 text-emerald-700' },
  { key: 'rejected',   label: '거절',   color: 'bg-red-100 text-red-700' },
]

const SOURCE_ICONS: Record<string, string> = {
  website: '🌐', web_form: '🌐', google_form: '📋',
  google_sheet: '📋', email: '📧', inquiry: '🏫',
  manual: '✏️', import: '📥',
}

const STATUS_BADGES: Record<string, string> = {
  new: 'bg-green-100 text-green-700 border-green-200',
  reviewed: 'bg-blue-100 text-blue-700 border-blue-200',
  contacted: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  interview: 'bg-orange-100 text-orange-700 border-orange-200',
  hired: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  rejected: 'bg-red-100 text-red-700 border-red-200',
}

export default function AdminInboxPage() {
  const { authed, headers } = useAdminAuth()

  const [items, setItems] = useState<InboxItem[]>([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  // Filters
  const [source, setSource] = useState('all')
  const [status, setStatus] = useState('all')
  const [search, setSearch] = useState('')

  // Bulk
  const [selected, setSelected] = useState<Set<string>>(new Set())

  // Gmail sync
  const [syncing, setSyncing] = useState(false)

  const fetchInbox = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ page: String(page), per_page: '50' })
      if (source !== 'all') params.set('source', source)
      if (status !== 'all') params.set('status', status)
      if (search.trim()) params.set('search', search.trim())

      const res = await fetch(`${API}/api/admin/inbox?${params}`, { headers: headers() })
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

      setItems(json.data?.items ?? [])
      setTotal(json.data?.total ?? 0)
      setTotalPages(json.data?.total_pages ?? 1)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [page, source, status, search, headers])

  useEffect(() => {
    if (authed) fetchInbox()
  }, [authed, page, source, status, fetchInbox])

  const handleGmailSync = async () => {
    setSyncing(true)
    try {
      const res = await fetch(`${API}/api/admin/gmail/sync`, {
        method: 'POST', headers: headers(),
      })
      const json = await res.json()
      if (json.success) {
        const count = json.data?.collected ?? 0
        setActionMsg(`Gmail 동기화 완료: ${count}건 새로 수집`)
        if (count > 0) fetchInbox()
      } else {
        setActionMsg(`동기화 실패: ${json.message || json.detail || 'Error'}`)
      }
    } catch (e) {
      setActionMsg(`동기화 오류: ${e instanceof Error ? e.message : 'Error'}`)
    } finally {
      setSyncing(false)
    }
  }

  const handleStatusChange = async (id: string, newStatus: string) => {
    try {
      const res = await fetch(`${API}/api/admin/inbox/${id}/status`, {
        method: 'PATCH', headers: headers(),
        body: JSON.stringify({ status: newStatus }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`상태 변경: ${newStatus}`)
      fetchInbox()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  // Bulk
  const toggleSelect = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (selected.size === items.length) setSelected(new Set())
    else setSelected(new Set(items.map(i => i.id)))
  }

  const handleBulkStatus = async (newStatus: string) => {
    try {
      const res = await fetch(`${API}/api/admin/inbox/bulk`, {
        method: 'POST', headers: headers(),
        body: JSON.stringify({ ids: Array.from(selected), action: 'status', value: newStatus }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`${selected.size}건 상태 변경 → ${newStatus}`)
      setSelected(new Set())
      fetchInbox()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }


  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">통합 수신함</h1>
          <p className="text-gray-500 text-sm">{total}건 접수</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={handleGmailSync} disabled={syncing}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-2">
            {syncing ? (
              <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
            ) : '📧'}
            {syncing ? '동기화 중...' : 'Gmail 동기화'}
          </button>
          <button type="button" onClick={fetchInbox} className="text-sm text-blue-600 hover:underline px-2">
            ↻ 새로고침
          </button>
        </div>
      </div>

      {/* Source tabs */}
      <div className="flex gap-2 flex-wrap">
        {SOURCE_TABS.map(t => (
          <button key={t.key} type="button"
            onClick={() => { setSource(t.key); setPage(1) }}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              source === t.key ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Status filters */}
      <div className="flex gap-2 flex-wrap">
        {STATUS_FILTERS.map(s => (
          <button key={s.key} type="button"
            onClick={() => { setStatus(s.key); setPage(1) }}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors border ${
              status === s.key
                ? 'bg-[#1d1d1f] text-white border-[#1d1d1f]'
                : `${s.color || 'bg-gray-50 text-gray-600'} border-gray-200 hover:border-gray-400`
            }`}>
            {s.label}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="flex gap-3">
        <input
          className="flex-1 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          placeholder="이름, 이메일, 국적 검색..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { setPage(1); fetchInbox() } }}
        />
        <button type="button" onClick={() => { setPage(1); fetchInbox() }}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors">
          검색
        </button>
      </div>

      {/* Bulk actions */}
      {selected.size > 0 && (
        <div className="card-flat bg-blue-50 border-blue-200 flex items-center gap-3 text-sm flex-wrap">
          <span className="font-medium text-blue-700">{selected.size}건 선택</span>
          {STATUS_FILTERS.filter(s => s.key !== 'all').map(s => (
            <button key={s.key} type="button"
              onClick={() => handleBulkStatus(s.key)}
              className={`px-3 py-1 rounded border text-xs font-medium ${s.color || 'bg-gray-50 text-gray-600'} border-gray-300 hover:opacity-80`}>
              → {s.label}
            </button>
          ))}
          <button type="button" onClick={() => setSelected(new Set())}
            className="ml-auto text-gray-400 hover:text-gray-600 text-xs">선택 해제</button>
        </div>
      )}

      {actionMsg && (
        <div className="card-flat bg-blue-50 border-blue-200 text-sm text-blue-700 flex justify-between items-center">
          <span>{actionMsg}</span>
          <button type="button" onClick={() => setActionMsg(null)} className="text-blue-500 hover:text-blue-700">×</button>
        </div>
      )}

      {/* Items list */}
      {loading ? (
        <div className="text-center py-16 text-gray-400 animate-pulse">로딩 중...</div>
      ) : error ? (
        <div className="text-center py-16 text-red-500">{error}</div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 text-gray-400">접수 내역이 없습니다.</div>
      ) : (
        <div className="space-y-2">
          {/* Select all */}
          <div className="flex items-center gap-2 px-2 text-xs text-gray-400">
            <input type="checkbox" checked={selected.size === items.length && items.length > 0}
              onChange={toggleAll} className="rounded" />
            <span>전체 선택</span>
          </div>

          {items.map(item => (
            <div key={item.id}
              className="card !py-3 flex items-start gap-3 hover:border-blue-200 transition-colors">
              <input type="checkbox" checked={selected.has(item.id)}
                onChange={() => toggleSelect(item.id)} className="mt-1 rounded" />

              {/* Source icon */}
              <span className="text-lg shrink-0" title={item.source}>
                {SOURCE_ICONS[item.source] || '📄'}
              </span>

              {/* Main info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                  <span className={`badge text-[10px] border ${
                    STATUS_BADGES[item.inbox_status] || 'bg-gray-100 text-gray-600 border-gray-200'
                  }`}>
                    {STATUS_FILTERS.find(s => s.key === item.inbox_status)?.label || item.inbox_status}
                  </span>
                  {item.type === 'inquiry' && (
                    <span className="badge text-[10px] bg-orange-50 text-orange-700 border border-orange-200">구인</span>
                  )}
                  <a href={`/admin/inbox/${item.id}`}
                    className="font-semibold text-gray-900 truncate hover:text-blue-600 hover:underline">
                    {item.name || 'N/A'}
                  </a>
                  {item.nationality && (
                    <span className="text-xs text-gray-400">{item.nationality}</span>
                  )}
                </div>
                <p className="text-xs text-gray-400">
                  {item.email || 'No email'}
                  {item.area_prefs && ` · ${item.area_prefs}`}
                  {item.school_name && ` · ${item.school_name}`}
                  {' · '}{new Date(item.created_at).toLocaleDateString('ko-KR')}
                  {item.assigned_to && ` · 담당: ${item.assigned_to}`}
                </p>
              </div>

              {/* Status dropdown */}
              <select
                className="text-xs border border-gray-200 rounded px-2 py-1 bg-white text-gray-700 shrink-0"
                value={item.inbox_status}
                onChange={e => handleStatusChange(item.id, e.target.value)}
              >
                {STATUS_FILTERS.filter(s => s.key !== 'all').map(s => (
                  <option key={s.key} value={s.key}>{s.label}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2 pt-4">
          <button type="button" onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-3 py-1 rounded border border-gray-200 text-sm disabled:opacity-30 hover:bg-gray-50">
            ← 이전
          </button>
          <span className="px-3 py-1 text-sm text-gray-500">
            {page} / {totalPages}
          </span>
          <button type="button" onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-3 py-1 rounded border border-gray-200 text-sm disabled:opacity-30 hover:bg-gray-50">
            다음 →
          </button>
        </div>
      )}
    </div>
  )
}
