'use client'

/**
 * /admin/posts — Community Posts Management
 * 전체 게시물 CRUD + 보드별 필터 + 고정/삭제
 */

import { useCallback, useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

const BOARDS = ['all', 'visa', 'support', 'support_kr', 'about', 'korea', 'tips', 'testimonials'] as const

interface Post {
  id: number
  board: string
  title: string
  preview?: string
  body?: string
  author_hash: string
  pinned: number
  views: number
  created_at: string
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

export default function AdminPostsPage() {
  const [adminKey, setAdminKey] = useState('')
  const [keyInput, setKeyInput] = useState('')
  const [authed, setAuthed] = useState(false)

  const [posts, setPosts] = useState<Post[]>([])
  const [board, setBoard] = useState<string>('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  const headers = useCallback((): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (adminKey) h['x-admin-key'] = adminKey
    return h
  }, [adminKey])

  const fetchPosts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const allPosts: Post[] = []
      const boards = board === 'all'
        ? ['visa', 'support', 'support_kr', 'about', 'korea', 'tips', 'testimonials']
        : [board]

      for (const b of boards) {
        const res = await fetch(`${API}/api/community/${b}?limit=200`, { headers: headers() })
        const json = await res.json()
        if (json.success && json.data?.posts) {
          allPosts.push(...json.data.posts.map((p: Post) => ({ ...p, board: b })))
        }
      }

      allPosts.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      setPosts(allPosts)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [board, headers])

  useEffect(() => {
    if (authed) fetchPosts()
  }, [authed, board, fetchPosts])

  const handleDelete = async (postBoard: string, postId: number) => {
    if (!confirm(`Delete post #${postId}?`)) return
    try {
      const res = await fetch(`${API}/api/community/${postBoard}/${postId}`, {
        method: 'DELETE',
        headers: headers(),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`Post #${postId} deleted`)
      fetchPosts()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  const handlePin = async (postBoard: string, postId: number, currentPin: number) => {
    try {
      const res = await fetch(`${API}/api/admin/community/posts/${postId}/pin`, {
        method: 'PATCH',
        headers: headers(),
        body: JSON.stringify({ pinned: currentPin === 1 ? 0 : 1 }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`Post #${postId} ${currentPin === 1 ? 'unpinned' : 'pinned'}`)
      fetchPosts()
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

  const boardLabel = (b: string) => {
    const map: Record<string, string> = {
      visa: 'Visa', support: 'Support(EN)', support_kr: '업무지원(KR)',
      about: 'About', korea: 'Korea', tips: 'Tips', testimonials: 'Testimonials'
    }
    return map[b] ?? b
  }

  return (
    <div className="space-y-6">
      <AdminNav active="/admin/posts" />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">게시판 관리</h1>
          <p className="text-gray-500 text-sm">{posts.length} posts</p>
        </div>
        <button onClick={fetchPosts} className="text-sm text-blue-600 hover:underline">↻ 새로고침</button>
      </div>

      {/* Board filter */}
      <div className="flex gap-2 flex-wrap">
        {BOARDS.map((b) => (
          <button key={b} onClick={() => setBoard(b)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              board === b ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}>
            {b === 'all' ? '전체' : boardLabel(b)}
          </button>
        ))}
      </div>

      {actionMsg && (
        <div className="card-flat bg-blue-50 border-blue-200 text-sm text-blue-700 flex justify-between items-center">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg(null)} className="text-blue-500 hover:text-blue-700">×</button>
        </div>
      )}

      {loading ? (
        <div className="text-center py-16 text-gray-400 animate-pulse">로딩 중...</div>
      ) : error ? (
        <div className="text-center py-16 text-red-500">{error}</div>
      ) : posts.length === 0 ? (
        <div className="text-center py-16 text-gray-400">게시물이 없습니다.</div>
      ) : (
        <div className="space-y-2">
          {posts.map((p) => (
            <div key={`${p.board}-${p.id}`}
              className={`card !py-3 flex items-start gap-3 ${p.pinned === 1 ? 'border-l-4 !border-l-blue-500' : ''}`}>
              <div className="text-xs text-gray-400 font-mono w-8 pt-0.5">#{p.id}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={`badge text-[10px] ${
                    p.board === 'visa' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                    p.board === 'support_kr' ? 'bg-orange-50 text-orange-700 border border-orange-200' :
                    p.board === 'support' ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                    p.board === 'about' ? 'bg-violet-50 text-violet-700 border border-violet-200' :
                    p.board === 'korea' ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                    'bg-amber-50 text-amber-700 border border-amber-200'
                  }`}>{boardLabel(p.board)}</span>
                  {p.pinned === 1 && <span className="badge bg-blue-50 text-blue-600 border border-blue-200 text-[10px]">pinned</span>}
                  <span className="font-semibold text-gray-900 truncate">{p.title}</span>
                </div>
                <p className="text-xs text-gray-400">
                  #{p.author_hash} · {new Date(p.created_at).toLocaleDateString()} · {p.views} views
                </p>
              </div>
              <div className="flex gap-1 shrink-0">
                <button type="button" onClick={() => handlePin(p.board, p.id, p.pinned)}
                  className="text-xs px-2 py-1 rounded border border-gray-200 hover:bg-gray-100 transition-colors"
                  title={p.pinned === 1 ? 'Unpin' : 'Pin'}>
                  {p.pinned === 1 ? '📌' : '📍'}
                </button>
                <button type="button" onClick={() => handleDelete(p.board, p.id)}
                  className="text-xs px-2 py-1 rounded border border-red-200 text-red-500 hover:bg-red-50 transition-colors"
                  title="Delete">
                  🗑
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
