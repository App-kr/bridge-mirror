'use client'

/**
 * /admin — Ad Posts Dashboard
 *
 * 데이터 소스: FastAPI /api/admin/ad-posts → master.db (SQLite)
 * 보호: ADMIN_API_KEY 가 설정된 경우 X-Admin-Key 헤더 검증
 *
 * 접근 방법: /admin (URL 직접 입력, nav 노출 없음)
 */

import { useCallback, useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
// Admin key는 절대 NEXT_PUBLIC_ 접두어를 사용하면 안됨 (클라이언트 번들에 노출됨)
// 런타임에 사용자가 직접 입력하는 방식으로만 인증
const ENV_KEY = ''

// ── Types ─────────────────────────────────────────────────────────────────────
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

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ko-KR', {
    month: '2-digit', day: '2-digit',
    hour:  '2-digit', minute: '2-digit',
  })
}

function StatusBadge({ status }: { status: AdPost['status'] }) {
  const map = {
    posted: 'bg-green-900/60 text-green-300 border-green-800',
    draft:  'bg-yellow-900/60 text-yellow-300 border-yellow-800',
    error:  'bg-red-900/60 text-red-300 border-red-800',
  }
  const label = { posted: '게시완료', draft: 'Draft', error: '오류' }
  return (
    <span className={`inline-flex items-center text-xs font-medium px-2 py-0.5
                      rounded-full border ${map[status] ?? 'bg-gray-800 text-gray-400 border-gray-700'}`}>
      {label[status] ?? status}
    </span>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function AdminPage() {
  const [adminKey,  setAdminKey]  = useState(ENV_KEY)
  const [keyInput,  setKeyInput]  = useState('')
  const [authed,    setAuthed]    = useState(Boolean(ENV_KEY))

  const [data,      setData]      = useState<ApiData | null>(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState<string | null>(null)

  // Filters
  const [statusF,   setStatusF]   = useState<string>('all')
  const [expandId,  setExpandId]  = useState<number | null>(null)

  // ── Fetch ──────────────────────────────────────────────────────────────────
  const fetchData = useCallback(async (key: string) => {
    setLoading(true)
    setError(null)
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (key) headers['x-admin-key'] = key

      const res  = await fetch(`${API}/api/admin/ad-posts?limit=500`, { headers })
      const json = await res.json()

      if (res.status === 403) {
        setError('관리자 키가 올바르지 않습니다.')
        setAuthed(false)
        return
      }
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Error')

      setData(json.data as ApiData)
      setAuthed(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : '데이터 로드 실패')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (authed) fetchData(adminKey)
  }, [authed, adminKey, fetchData])

  // ── Key prompt ─────────────────────────────────────────────────────────────
  if (!authed) {
    return (
      <div className="max-w-sm mx-auto mt-32 space-y-6 text-center">
        <div>
          <h1 className="text-2xl font-bold">관리자 인증</h1>
          <p className="text-gray-500 text-sm mt-1">ADMIN_API_KEY를 입력하세요</p>
        </div>
        <div className="space-y-3">
          <input
            type="password"
            className="input text-center"
            placeholder="Admin key"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                setAdminKey(keyInput)
                setAuthed(true)
              }
            }}
          />
          <button
            className="btn-primary w-full"
            onClick={() => { setAdminKey(keyInput); setAuthed(true) }}
          >
            접속
          </button>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <p className="text-xs text-gray-600">
            ADMIN_API_KEY 미설정 시 빈 채로 접속
          </p>
        </div>
      </div>
    )
  }

  // ── Loading ────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="text-center py-32 text-gray-500 animate-pulse">
        데이터 로딩 중…
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-32 space-y-4">
        <p className="text-red-400">{error}</p>
        <button className="btn-primary" onClick={() => fetchData(adminKey)}>
          재시도
        </button>
        <button
          className="block mx-auto text-sm text-gray-500 hover:text-gray-300"
          onClick={() => { setAuthed(false); setError(null) }}
        >
          키 재입력
        </button>
      </div>
    )
  }

  if (!data) return null

  const { stats, posts } = data

  // Client-side filter
  const filtered = statusF === 'all'
    ? posts
    : posts.filter((p) => p.status === statusF)

  // ── Dashboard ──────────────────────────────────────────────────────────────
  return (
    <div className="space-y-8">

      {/* ── Admin Navigation ────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-2">
        {[
          { href: '/admin',              label: 'Ad Posts',     icon: '📢', active: true },
          { href: '/admin/posts',        label: 'Posts',        icon: '📝', active: false },
          { href: '/admin/interviews',   label: 'Interviews',   icon: '🎥', active: false },
          { href: '/admin/applications', label: 'Applications', icon: '📋', active: false },
          { href: '/admin/payments',     label: 'Payments',     icon: '💳', active: false },
          { href: '/admin/candidates',   label: 'Candidates',   icon: '👥', active: false },
        ].map((nav) => (
          <a
            key={nav.href}
            href={nav.href}
            className={`card !p-3 text-center text-sm font-medium transition-all
              ${nav.active
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'hover:border-blue-300 text-gray-600 hover:text-blue-600'}`}
          >
            <span className="text-lg block mb-1">{nav.icon}</span>
            {nav.label}
          </a>
        ))}
      </div>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Ad Posts 대시보드</h1>
          <p className="text-gray-500 text-sm mt-0.5">
            Craigslist 자동 게시 현황 — master.db
          </p>
        </div>
        <button
          onClick={() => fetchData(adminKey)}
          className="text-sm text-blue-600 hover:underline"
        >
          ↻ 새로고침
        </button>
      </div>

      {/* ── Stats cards ────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: '전체',     value: stats.total,          color: 'text-white'       },
          { label: '게시완료', value: stats.posted  ?? 0,   color: 'text-green-400'   },
          { label: 'Draft',    value: stats.draft   ?? 0,   color: 'text-yellow-400'  },
          { label: '오류',     value: stats.error   ?? 0,   color: 'text-red-400'     },
        ].map((s) => (
          <div key={s.label} className="card text-center">
            <div className={`text-3xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-sm text-gray-500 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── Filter tabs ────────────────────────────────────────────────────── */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'posted', 'draft', 'error'].map((f) => (
          <button
            key={f}
            onClick={() => setStatusF(f)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              statusF === f
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            {f === 'all' ? `전체 (${stats.total})` :
             f === 'posted' ? `게시완료 (${stats.posted ?? 0})` :
             f === 'draft'  ? `Draft (${stats.draft ?? 0})` :
                              `오류 (${stats.error ?? 0})`}
          </button>
        ))}
      </div>

      {/* ── Table ──────────────────────────────────────────────────────────── */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          해당 상태의 게시물이 없습니다.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((post) => (
            <div
              key={post.id}
              className="card space-y-3"
            >
              {/* ── Row summary ─────────────────────────────────────────── */}
              <div className="flex flex-wrap items-start gap-3">

                {/* ID + job code */}
                <div className="font-mono text-xs text-gray-500 w-10 pt-0.5">
                  #{post.id}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="font-semibold text-white">{post.job_code}</span>
                    <StatusBadge status={post.status} />
                    <span className="text-xs text-gray-600 bg-gray-800 px-2 py-0.5 rounded">
                      {post.platform}
                    </span>
                  </div>
                  {/* Ad title */}
                  {post.ad_title && (
                    <p className="text-sm text-gray-400 truncate">{post.ad_title}</p>
                  )}
                </div>

                {/* Dates */}
                <div className="text-right text-xs text-gray-500 shrink-0 space-y-0.5">
                  <div>Draft: {fmtDate(post.draft_at)}</div>
                  {post.posted_at && (
                    <div className="text-green-500">게시: {fmtDate(post.posted_at)}</div>
                  )}
                </div>
              </div>

              {/* ── Links & error ───────────────────────────────────────── */}
              <div className="flex flex-wrap items-center gap-3 text-sm border-t border-gray-800 pt-2">
                {post.posted_url && (
                  <a
                    href={post.posted_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:underline text-xs font-mono truncate max-w-xs"
                  >
                    🔗 {post.posted_url}
                  </a>
                )}
                {post.error_msg && (
                  <span className="text-red-400 text-xs">
                    ⚠ {post.error_msg}
                  </span>
                )}
                {post.screenshot_path && (
                  <span className="text-gray-600 text-xs">
                    📸 {post.screenshot_path.split(/[\\/]/).pop()}
                  </span>
                )}

                {/* Ad body preview toggle */}
                {post.ad_body && (
                  <button
                    onClick={() => setExpandId(expandId === post.id ? null : post.id)}
                    className="ml-auto text-xs text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    {expandId === post.id ? '▲ 광고 숨기기' : '▼ 광고 본문 보기'}
                  </button>
                )}
              </div>

              {/* ── Ad body (expanded) ──────────────────────────────────── */}
              {expandId === post.id && post.ad_body && (
                <pre className="bg-gray-950 border border-gray-800 rounded-lg p-4
                                text-xs text-gray-300 whitespace-pre-wrap leading-relaxed
                                overflow-auto max-h-64 font-mono">
                  {post.ad_body}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Footer note ────────────────────────────────────────────────────── */}
      <div className="text-center text-xs text-gray-700 border-t border-gray-800 pt-6">
        데이터: master.db → FastAPI /api/admin/ad-posts
        &nbsp;·&nbsp;
        플랫폼: {stats.platforms?.join(', ') || '—'}
        &nbsp;·&nbsp;
        이 페이지는 URL 직접 접근으로만 이용 가능합니다
      </div>

    </div>
  )
}
