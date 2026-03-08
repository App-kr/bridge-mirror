'use client'

/**
 * /admin/faq — FAQ 게시판 관리
 * 드래그로 순서변경 + 인라인 편집 + 새 게시물 작성
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import FaqDndList, { FaqPost } from '@/app/admin/components/FaqDndList'
import { API_URL } from '@/lib/api'

const API = API_URL

const FAQ_BOARDS = [
  { id: 'visa',       label: 'Visa FAQ' },
  { id: 'support',    label: 'Support (EN)' },
  { id: 'support_kr', label: '업무지원 (KR)' },
  { id: 'about',      label: 'About' },
  { id: 'korea',      label: 'Korea' },
  { id: 'tips',       label: 'Tips' },
  { id: 'testimonials', label: 'Testimonials' },
  { id: 'information', label: 'Information' },
] as const

export default function AdminFaqPage() {
  const { authed, login, headers, signedFetch, waking } = useAdminAuth()

  const [board, setBoard] = useState<string>('visa')
  const [posts, setPosts] = useState<FaqPost[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  // 새 게시물 폼
  const [showForm, setShowForm] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newBody, setNewBody] = useState('')
  const [posting, setPosting] = useState(false)

  const fetchPosts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/community/${board}?limit=200`, { headers: headers() })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || `Error ${res.status}`)
      const raw: FaqPost[] = (json.data?.posts || []).map((p: { id: number; title: string; sort_order?: number }) => ({
        id: p.id,
        title: p.title,
        board,
        sort_order: p.sort_order,
      }))
      setPosts(raw)
    } catch (e) {
      setError(e instanceof Error ? e.message : '로드 실패')
    } finally {
      setLoading(false)
    }
  }, [board, headers])

  useEffect(() => {
    if (authed) fetchPosts()
  }, [authed, board, fetchPosts])

  const handleCreate = async () => {
    if (!newTitle.trim()) { setActionMsg('제목을 입력하세요.'); return }
    setPosting(true)
    try {
      const res = await signedFetch(`${API}/api/community/${board}`, {
        method: 'POST',
        body: JSON.stringify({ title: newTitle.trim(), body: newBody.trim() }),
      })
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? '작성 실패')
      setActionMsg(`게시물 작성 완료: #${json.data.id}`)
      setNewTitle(''); setNewBody(''); setShowForm(false)
      fetchPosts()
    } catch (e) {
      setActionMsg(`오류: ${e instanceof Error ? e.message : '실패'}`)
    } finally {
      setPosting(false)
    }
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">FAQ 관리</h1>
          <p className="text-gray-500 text-sm">드래그로 순서변경 · ✏️ 클릭으로 인라인 편집</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setShowForm(!showForm)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              showForm ? 'bg-gray-200 text-gray-700' : 'bg-[#1d1d1f] text-white hover:bg-[#424245]'
            }`}
          >
            {showForm ? '취소' : '+ 새 게시물'}
          </button>
          <button
            type="button"
            onClick={fetchPosts}
            className="text-sm text-blue-600 hover:underline px-2"
          >
            ↻ 새로고침
          </button>
        </div>
      </div>

      {/* 게시판 탭 */}
      <div className="flex gap-2 flex-wrap">
        {FAQ_BOARDS.map((b) => (
          <button
            key={b.id}
            type="button"
            onClick={() => { setBoard(b.id); setActionMsg(null) }}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              board === b.id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {b.label}
          </button>
        ))}
      </div>

      {/* 새 게시물 폼 */}
      {showForm && (
        <div className="card border-2 border-blue-200 bg-blue-50/30 space-y-3">
          <h2 className="font-bold text-gray-900 text-sm">새 게시물 — {FAQ_BOARDS.find(b => b.id === board)?.label}</h2>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">제목</label>
            <input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              placeholder="게시물 제목"
              maxLength={200}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">본문</label>
            <textarea
              value={newBody}
              onChange={(e) => setNewBody(e.target.value)}
              rows={6}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-mono resize-y focus:outline-none focus:ring-2 focus:ring-blue-400"
              placeholder="본문 내용을 입력하세요..."
              maxLength={10000}
            />
          </div>
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleCreate}
              disabled={posting || !newTitle.trim()}
              className="px-5 py-2 rounded-full bg-[#1d1d1f] text-white text-sm font-medium hover:bg-[#424245] disabled:opacity-50 transition-colors"
            >
              {posting ? '게시 중...' : '게시하기'}
            </button>
          </div>
        </div>
      )}

      {/* 액션 메시지 */}
      {actionMsg && (
        <div className="card-flat bg-blue-50 border-blue-200 text-sm text-blue-700 flex justify-between items-center">
          <span>{actionMsg}</span>
          <button type="button" onClick={() => setActionMsg(null)} className="text-blue-500 hover:text-blue-700">×</button>
        </div>
      )}

      {/* 게시물 목록 */}
      {loading ? (
        <div className="text-center py-16 text-gray-400 animate-pulse">로딩 중...</div>
      ) : error ? (
        <div className="text-center py-16 text-red-500">{error}</div>
      ) : (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-semibold text-gray-700">
              {FAQ_BOARDS.find(b => b.id === board)?.label} — {posts.length}개
            </span>
            <span className="text-[11px] text-gray-400">≡ 핸들 드래그로 순서변경</span>
          </div>
          <FaqDndList
            key={board}
            posts={posts}
            board={board}
            apiBase={API}
            authHeaders={headers}
            onSaved={() => { setActionMsg('저장 완료!'); fetchPosts() }}
            onCancel={fetchPosts}
          />
        </div>
      )}
    </div>
  )
}
