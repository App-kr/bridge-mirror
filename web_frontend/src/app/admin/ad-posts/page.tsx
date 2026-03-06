'use client'

/**
 * /admin/ad-posts — Ad Posts Dashboard
 * 기존 /admin 페이지에서 분리
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'

import { API_URL } from '@/lib/api'

const API = API_URL

interface AdPost {
  id:              number
  job_code:        string
  seq:             number
  platform:        string
  status:          'posted' | 'draft' | 'error'
  ad_title:        string | null
  ad_body:         string | null
  draft_at:        string | null
  posted_at:       string | null
  posted_url:      string | null
  screenshot_path: string | null
  error_msg:       string | null
}

interface Stats {
  total:     number
  posted?:   number
  draft?:    number
  error?:    number
  platforms: string[]
}

interface ApiData {
  stats: Stats
  posts: AdPost[]
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ko-KR', {
    month: '2-digit', day: '2-digit',
    hour:  '2-digit', minute: '2-digit',
  })
}

function StatusBadge({ status }: { status: AdPost['status'] }) {
  const map = {
    posted: 'bg-green-100 text-green-700 border-green-200',
    draft:  'bg-yellow-100 text-yellow-700 border-yellow-200',
    error:  'bg-red-100 text-red-700 border-red-200',
  }
  const label = { posted: '게시완료', draft: 'Draft', error: '오류' }
  return (
    <span className={`inline-flex items-center text-xs font-medium px-2 py-0.5
                      rounded-full border ${map[status] ?? 'bg-gray-100 text-gray-500 border-gray-200'}`}>
      {label[status] ?? status}
    </span>
  )
}

export default function AdminAdPostsPage() {
  const { authed, login, headers, waking } = useAdminAuth()

  const [data,      setData]      = useState<ApiData | null>(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState<string | null>(null)
  const [statusF,   setStatusF]   = useState<string>('all')
  const [expandId,  setExpandId]  = useState<number | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res  = await fetch(`${API}/api/admin/ad-posts?limit=500`, { headers: headers() })
      const json = await res.json()
      if (res.status === 403) {
        const errBody = await res.json().catch(() => ({}))
        if (errBody.error?.includes?.('Access denied')) {
          setError('일시적으로 차단되었습니다. 자동 재시도 중...')
          const k = localStorage.getItem('bridge_admin_key') || ''
          await fetch(`${API}/api/admin/reset-blacklist`, { method: 'POST', headers: { 'x-admin-key': k } }).catch(() => {})
          setTimeout(() => window.location.reload(), 3000)
          return
        }
        setError('관리자 키가 올바르지 않습니다. 다시 로그인해주세요.')
        localStorage.removeItem('bridge_admin_key')
        return
      }
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Error')
      setData(json.data as ApiData)
    } catch (e) {
      setError(e instanceof Error ? e.message : '데이터 로드 실패')
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => {
    if (authed) fetchData()
  }, [authed, fetchData])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  if (loading) {
    return (
      <div>
        <div className="text-center py-32 text-gray-400 animate-pulse">데이터 로딩 중…</div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <div className="text-center py-32 space-y-4">
          <p className="text-red-500">{error}</p>
          <button type="button" className="btn-primary" onClick={fetchData}>재시도</button>
        </div>
      </div>
    )
  }

  if (!data) return null

  const { stats, posts } = data
  const filtered = statusF === 'all' ? posts : posts.filter((p) => p.status === statusF)

  return (
    <div className="space-y-8">

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Ad Posts 대시보드</h1>
          <p className="text-gray-500 text-sm mt-0.5">Craigslist 자동 게시 현황 — master.db</p>
        </div>
        <button type="button" onClick={fetchData} className="text-sm text-blue-600 hover:underline">
          ↻ 새로고침
        </button>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: '전체',     value: stats.total,        color: 'text-gray-900' },
          { label: '게시완료', value: stats.posted ?? 0,  color: 'text-green-600' },
          { label: 'Draft',    value: stats.draft  ?? 0,  color: 'text-yellow-600' },
          { label: '오류',     value: stats.error  ?? 0,  color: 'text-red-600' },
        ].map((s) => (
          <div key={s.label} className="card text-center">
            <div className={`text-3xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-sm text-gray-500 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'posted', 'draft', 'error'].map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setStatusF(f)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              statusF === f
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f === 'all' ? `전체 (${stats.total})` :
             f === 'posted' ? `게시완료 (${stats.posted ?? 0})` :
             f === 'draft'  ? `Draft (${stats.draft ?? 0})` :
                              `오류 (${stats.error ?? 0})`}
          </button>
        ))}
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-400">해당 상태의 게시물이 없습니다.</div>
      ) : (
        <div className="space-y-3">
          {filtered.map((post) => (
            <div key={post.id} className="card space-y-3">
              <div className="flex flex-wrap items-start gap-3">
                <div className="font-mono text-xs text-gray-400 w-10 pt-0.5">#{post.id}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="font-semibold text-gray-900">{post.job_code}</span>
                    <StatusBadge status={post.status} />
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                      {post.platform}
                    </span>
                  </div>
                  {post.ad_title && (
                    <p className="text-sm text-gray-500 truncate">{post.ad_title}</p>
                  )}
                </div>
                <div className="text-right text-xs text-gray-400 shrink-0 space-y-0.5">
                  <div>Draft: {fmtDate(post.draft_at)}</div>
                  {post.posted_at && (
                    <div className="text-green-600">게시: {fmtDate(post.posted_at)}</div>
                  )}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3 text-sm border-t border-gray-100 pt-2">
                {post.posted_url && (
                  <a href={post.posted_url} target="_blank" rel="noopener noreferrer"
                    className="text-blue-600 hover:underline text-xs font-mono truncate max-w-xs">
                    🔗 {post.posted_url}
                  </a>
                )}
                {post.error_msg && (
                  <span className="text-red-500 text-xs">⚠ {post.error_msg}</span>
                )}
                {post.screenshot_path && (
                  <span className="text-gray-400 text-xs">
                    📸 {post.screenshot_path.split(/[\\/]/).pop()}
                  </span>
                )}
                {post.ad_body && (
                  <button
                    type="button"
                    onClick={() => setExpandId(expandId === post.id ? null : post.id)}
                    className="ml-auto text-xs text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    {expandId === post.id ? '▲ 광고 숨기기' : '▼ 광고 본문 보기'}
                  </button>
                )}
              </div>

              {expandId === post.id && post.ad_body && (
                <pre className="bg-gray-50 border border-gray-200 rounded-lg p-4
                                text-xs text-gray-600 whitespace-pre-wrap leading-relaxed
                                overflow-auto max-h-64 font-mono">
                  {post.ad_body}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="text-center text-xs text-gray-400 border-t border-gray-100 pt-6">
        데이터: master.db → FastAPI /api/admin/ad-posts
        &nbsp;·&nbsp;
        플랫폼: {stats.platforms?.join(', ') || '—'}
      </div>
    </div>
  )
}
