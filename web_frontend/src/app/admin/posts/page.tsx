'use client'

/**
 * /admin/posts — Community Posts Management
 * 검색, 인라인 수정, 벌크 선택/고정/삭제, 드래그앤드롭 순서변경
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import MarkdownBody from '@/components/MarkdownBody'
import HtmlPreview from '@/components/HtmlPreview'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
  sortableKeyboardCoordinates,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

import { API_URL } from '@/lib/api'

const API = API_URL

const BOARDS = ['all', 'visa', 'support', 'support_kr', 'about', 'korea', 'tips', 'testimonials', 'information'] as const

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
  content_type?: string
}

const boardLabel = (b: string) => {
  const map: Record<string, string> = {
    visa: 'Visa', support: 'Support(EN)', support_kr: '업무지원(KR)',
    about: 'About', korea: 'Korea', tips: 'Tips', testimonials: 'Testimonials',
    information: 'Information'
  }
  return map[b] ?? b
}

function getInitialBoard(): string {
  if (typeof window === 'undefined') return 'all'
  const params = new URLSearchParams(window.location.search)
  return params.get('board') ?? 'all'
}

/* ── 전체 카드 드래그 래퍼 ── */
function SortablePostWrapper({
  id,
  disabled,
  children,
}: {
  id: number
  disabled?: boolean
  children: React.ReactNode
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id, disabled })
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.45 : 1,
    zIndex: isDragging ? 999 : undefined,
  }
  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`touch-none select-none ${disabled ? '' : 'cursor-grab active:cursor-grabbing'} ${isDragging ? 'shadow-xl ring-2 ring-blue-400 rounded-xl' : ''}`}
    >
      {children}
    </div>
  )
}

export default function AdminPostsPage() {
  const { authed, login, headers, signedFetch, waking } = useAdminAuth()

  const [posts, setPosts] = useState<Post[]>([])
  const [localPosts, setLocalPosts] = useState<Post[] | null>(null)
  const [board, setBoard] = useState<string>(getInitialBoard)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)
  const [savingOrder, setSavingOrder] = useState(false)

  // New post form
  const [showForm, setShowForm] = useState(false)
  const [newBoard, setNewBoard] = useState('visa')
  const [newTitle, setNewTitle] = useState('')
  const [newBody, setNewBody] = useState('')
  const [posting, setPosting] = useState(false)
  const [newTab, setNewTab] = useState<'write' | 'preview'>('write')
  const [newContentType, setNewContentType] = useState<'markdown' | 'html'>('markdown')

  // Edit state
  const [editId, setEditId] = useState<number | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [editBody, setEditBody] = useState('')
  const [editBoard, setEditBoard] = useState('')
  const [saving, setSaving] = useState(false)
  const [editTab, setEditTab] = useState<'write' | 'preview'>('write')
  const [editContentType, setEditContentType] = useState<'markdown' | 'html'>('markdown')

  // Bulk selection
  const [selected, setSelected] = useState<Set<string>>(new Set())

  // DnD 상태
  const displayPosts = localPosts ?? posts
  const orderChanged = localPosts !== null

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const source = localPosts ?? posts
    const oldIdx = source.findIndex(p => p.id === active.id)
    const newIdx = source.findIndex(p => p.id === over.id)
    setLocalPosts(arrayMove(source, oldIdx, newIdx))
  }

  const handleSaveOrder = async () => {
    if (!localPosts) return
    setSavingOrder(true)
    try {
      const items = localPosts.map((p, idx) => ({ id: p.id, sort_order: localPosts.length - idx }))
      const res = await fetch(`${API}/api/admin/community-reorder/${board}`, {
        method: 'PATCH',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ items }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || json.error || `Error ${res.status}`)
      setActionMsg('순서 저장 완료!')
      setLocalPosts(null)
      fetchPosts()
    } catch (e) {
      setActionMsg(`순서 저장 오류: ${e instanceof Error ? e.message : '실패'}`)
    } finally {
      setSavingOrder(false)
    }
  }

  const fetchPosts = useCallback(async () => {
    setLoading(true)
    setError(null)
    setLocalPosts(null)
    try {
      // 검색어가 있으면 관리자 검색 API 사용
      if (search.trim()) {
        const params = new URLSearchParams({ search: search.trim(), limit: '200' })
        if (board !== 'all') params.set('board', board)
        const res = await fetch(`${API}/api/admin/community/posts?${params}`, { headers: headers() })
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
        if (json.success && json.data?.posts) {
          setPosts(json.data.posts)
        }
      } else {
        // 검색어 없으면 기존 방식
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
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [board, search, headers])

  useEffect(() => {
    if (authed) fetchPosts()
  }, [authed, board, fetchPosts])

  // URL ?edit=ID 파라미터 → 자동 편집 열기
  useEffect(() => {
    if (!authed || loading || posts.length === 0) return
    const params = new URLSearchParams(window.location.search)
    const editParam = params.get('edit')
    if (!editParam) return
    const targetId = parseInt(editParam)
    if (!targetId || editId === targetId) return
    const target = posts.find((p) => p.id === targetId)
    if (target) {
      startEdit(target)
      params.delete('edit')
      const qs = params.toString()
      window.history.replaceState({}, '', `${window.location.pathname}${qs ? `?${qs}` : ''}`)
    }
  }, [authed, loading, posts, editId])

  const handleDelete = async (postBoard: string, postId: number) => {
    if (!confirm(`Delete post #${postId}?`)) return
    try {
      const res = await signedFetch(`${API}/api/community/${postBoard}/${postId}`, {
        method: 'DELETE',
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || json.error || `Error ${res.status}`)
      setActionMsg(`Post #${postId} deleted`)
      fetchPosts()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  const handleCreate = async () => {
    if (!newTitle.trim() || !newBody.trim()) { setActionMsg('제목과 본문을 입력하세요.'); return }
    setPosting(true)
    try {
      const bodyStr = JSON.stringify({ title: newTitle.trim(), body: newBody.trim(), content_type: newContentType })
      const res = await signedFetch(`${API}/api/community/${newBoard}`, {
        method: 'POST',
        body: bodyStr,
      })
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Failed')
      setActionMsg(`게시물 작성 완료: #${json.data.id} [${newBoard}] ${newTitle}`)
      setNewTitle(''); setNewBody(''); setShowForm(false); setNewContentType('markdown')
      fetchPosts()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    } finally {
      setPosting(false)
    }
  }

  const handlePin = async (postBoard: string, postId: number, currentPin: number) => {
    try {
      const bodyStr = JSON.stringify({ pinned: currentPin === 1 ? 0 : 1 })
      const res = await signedFetch(`${API}/api/admin/community/posts/${postId}/pin`, {
        method: 'PATCH',
        body: bodyStr,
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || json.error || `Error ${res.status}`)
      setActionMsg(`Post #${postId} ${currentPin === 1 ? 'unpinned' : 'pinned'}`)
      fetchPosts()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  // Edit handlers
  const startEdit = async (post: Post) => {
    try {
      const res = await fetch(`${API}/api/community/${post.board}/${post.id}`, { headers: headers() })
      const json = await res.json()
      if (json.success && json.data) {
        setEditId(post.id)
        setEditBoard(post.board)
        setEditTitle(json.data.title || post.title)
        setEditBody(json.data.body || '')
        setEditContentType(json.data.content_type === 'html' ? 'html' : 'markdown')
      }
    } catch {
      setEditId(post.id)
      setEditBoard(post.board)
      setEditTitle(post.title)
      setEditBody(post.preview || '')
      setEditContentType(post.content_type === 'html' ? 'html' : 'markdown')
    }
  }

  const handleEdit = async () => {
    if (!editTitle.trim()) { setActionMsg('제목을 입력하세요.'); return }
    setSaving(true)
    try {
      const bodyStr = JSON.stringify({ title: editTitle.trim(), body: editBody.trim(), content_type: editContentType })
      const res = await signedFetch(`${API}/api/admin/community/${editBoard}/${editId}`, {
        method: 'PATCH',
        body: bodyStr,
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || json.error || `Error ${res.status}`)
      setActionMsg(`Post #${editId} 수정 완료`)
      setEditId(null)
      fetchPosts()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    } finally {
      setSaving(false)
    }
  }

  // Bulk handlers
  const toggleSelect = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const toggleAll = () => {
    if (selected.size === posts.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(posts.map((p) => `${p.board}-${p.id}`)))
    }
  }

  const bulkPin = async (pin: number) => {
    for (const key of selected) {
      const postId = parseInt(key.split('-').pop() || '0')
      if (postId) {
        const pinBody = JSON.stringify({ pinned: pin })
        await signedFetch(`${API}/api/admin/community/posts/${postId}/pin`, {
          method: 'PATCH',
          body: pinBody,
        })
      }
    }
    setSelected(new Set())
    setActionMsg(`${selected.size}개 게시물 ${pin ? 'pinned' : 'unpinned'}`)
    fetchPosts()
  }

  const bulkDelete = async () => {
    if (!confirm(`${selected.size}개 게시물을 삭제하시겠습니까?`)) return
    for (const key of selected) {
      const parts = key.split('-')
      const postId = parseInt(parts.pop() || '0')
      const postBoard = parts.join('-')
      if (postId && postBoard) {
        await signedFetch(`${API}/api/community/${postBoard}/${postId}`, {
          method: 'DELETE',
        })
      }
    }
    setSelected(new Set())
    setActionMsg(`${selected.size}개 게시물 삭제 완료`)
    fetchPosts()
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  /* ── 개별 게시물 카드 ── */
  const renderPost = (p: Post) => {
    const key = `${p.board}-${p.id}`
    const isEditing = editId === p.id && editBoard === p.board
    return (
      <>
        <div className={`card !py-3 flex items-start gap-3 ${p.pinned === 1 ? 'border-l-4 !border-l-blue-500' : ''}`}>
          <input type="checkbox" checked={selected.has(key)}
            onChange={() => toggleSelect(key)}
            onPointerDown={(e) => e.stopPropagation()}
            className="mt-1 rounded" />
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
              #{p.author_hash} · {new Date(p.created_at).toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' })} · 👁 {p.views}
            </p>
          </div>
          <div className="flex gap-1 shrink-0" onPointerDown={(e) => e.stopPropagation()}>
            <button type="button" onClick={() => startEdit(p)}
              className="text-xs px-2 py-1 rounded border border-gray-200 hover:bg-gray-100 transition-colors"
              title="Edit">
              ✏️
            </button>
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

        {/* Inline Edit Form */}
        {isEditing && (
          <div className="card border-2 border-yellow-200 bg-yellow-50/30 space-y-3 mt-1">
            <h3 className="text-sm font-bold text-gray-700">게시글 수정 #{p.id}</h3>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">제목</label>
              <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)}
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
                maxLength={200} />
            </div>
            <div>
              <div className="flex items-center gap-1 mb-2">
                <button type="button" onClick={() => setEditTab('write')}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                    editTab === 'write' ? 'bg-[#1d1d1f] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}>작성</button>
                <button type="button" onClick={() => setEditTab('preview')}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                    editTab === 'preview' ? 'bg-[#1d1d1f] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}>미리보기</button>
                <div className="ml-auto flex items-center gap-1 bg-gray-100 rounded-md p-0.5">
                  <button type="button" onClick={() => setEditContentType('markdown')}
                    className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
                      editContentType === 'markdown' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
                    }`}>MD</button>
                  <button type="button" onClick={() => setEditContentType('html')}
                    className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
                      editContentType === 'html' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
                    }`}>HTML</button>
                </div>
              </div>
              {editTab === 'write' ? (
                <textarea value={editBody} onChange={(e) => setEditBody(e.target.value)}
                  className="w-full h-40 rounded-lg border border-gray-200 bg-white px-3 py-3 text-sm font-mono resize-y focus:outline-none focus:ring-2 focus:ring-yellow-400"
                  maxLength={10000} />
              ) : (
                <div className="w-full min-h-[160px] rounded-lg border border-gray-200 bg-white px-4 py-4 overflow-auto">
                  {editBody.trim() ? (
                    editContentType === 'html' ? <HtmlPreview html={editBody} /> : <MarkdownBody text={editBody} />
                  ) : <p className="text-gray-400 text-sm">미리보기할 내용이 없습니다.</p>}
                </div>
              )}
            </div>
            <div className="flex gap-2 justify-end">
              <button type="button" onClick={() => setEditId(null)}
                className="px-4 py-2 text-gray-600 bg-gray-100 rounded-lg text-sm hover:bg-gray-200">
                취소
              </button>
              <button type="button" onClick={handleEdit} disabled={saving}
                className="px-4 py-2 bg-yellow-500 text-white rounded-lg text-sm font-medium hover:bg-yellow-600 disabled:opacity-50">
                {saving ? '저장 중...' : '수정 저장'}
              </button>
            </div>
          </div>
        )}
      </>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">게시판 관리</h1>
          <p className="text-gray-500 text-sm">{posts.length} posts</p>
        </div>
        <div className="flex gap-2 items-center">
          {orderChanged && (
            <>
              <span className="text-xs text-blue-600">순서 변경됨</span>
              <button type="button" onClick={() => setLocalPosts(null)}
                className="px-3 py-2 rounded-full text-sm font-medium bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors">
                되돌리기
              </button>
              <button type="button" onClick={handleSaveOrder} disabled={savingOrder}
                className="px-4 py-2 rounded-full text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors">
                {savingOrder ? '저장 중...' : '순서 저장'}
              </button>
            </>
          )}
          <button type="button" onClick={() => setShowForm(!showForm)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              showForm ? 'bg-gray-200 text-gray-700' : 'bg-[#1d1d1f] text-white hover:bg-[#424245]'
            }`}>
            {showForm ? '취소' : '+ 새 게시물'}
          </button>
          <button type="button" onClick={fetchPosts} className="text-sm text-blue-600 hover:underline px-2">↻ 새로고침</button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="flex gap-3">
        <input
          className="flex-1 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          placeholder="제목/본문 검색..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') fetchPosts() }}
        />
        <button type="button" onClick={fetchPosts}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors">
          검색
        </button>
      </div>

      {/* New Post Form */}
      {showForm && (
        <div className="card border-2 border-blue-200 bg-blue-50/30 space-y-4">
          <h2 className="font-bold text-gray-900">새 게시물 작성</h2>
          <div className="flex gap-3">
            <div className="w-40">
              <label className="block text-xs font-medium text-gray-500 mb-1">게시판</label>
              <select value={newBoard} onChange={(e) => setNewBoard(e.target.value)}
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
                {BOARDS.filter(b => b !== 'all').map((b) => (
                  <option key={b} value={b}>{boardLabel(b)}</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-500 mb-1">제목</label>
              <input value={newTitle} onChange={(e) => setNewTitle(e.target.value)}
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="게시물 제목" maxLength={200} />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1 mb-2">
              <button type="button" onClick={() => setNewTab('write')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  newTab === 'write' ? 'bg-[#1d1d1f] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}>작성</button>
              <button type="button" onClick={() => setNewTab('preview')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  newTab === 'preview' ? 'bg-[#1d1d1f] text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}>미리보기</button>
              <div className="ml-auto flex items-center gap-1 bg-gray-100 rounded-md p-0.5">
                <button type="button" onClick={() => setNewContentType('markdown')}
                  className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
                    newContentType === 'markdown' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
                  }`}>MD</button>
                <button type="button" onClick={() => setNewContentType('html')}
                  className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
                    newContentType === 'html' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
                  }`}>HTML</button>
              </div>
            </div>
            {newTab === 'write' ? (
              <>
                <textarea value={newBody} onChange={(e) => setNewBody(e.target.value)}
                  className="w-full h-48 rounded-lg border border-gray-200 bg-white px-3 py-3 text-sm font-mono resize-y focus:outline-none focus:ring-2 focus:ring-blue-400"
                  placeholder={newContentType === 'html' ? '<p>HTML 내용을 입력하세요...</p>' : '## 제목\n\n본문 내용을 입력하세요...'}
                  maxLength={10000} />
                <div className="text-right text-xs text-gray-400 mt-1">{newBody.length}/10,000</div>
              </>
            ) : (
              <div className="w-full min-h-[192px] rounded-lg border border-gray-200 bg-white px-4 py-4 overflow-auto">
                {newBody.trim() ? (
                  newContentType === 'html' ? <HtmlPreview html={newBody} /> : <MarkdownBody text={newBody} />
                ) : <p className="text-gray-400 text-sm">미리보기할 내용이 없습니다.</p>}
              </div>
            )}
          </div>
          <div className="flex justify-end">
            <button type="button" onClick={handleCreate} disabled={posting}
              className="px-6 py-2 rounded-full bg-[#1d1d1f] text-white text-sm font-medium hover:bg-[#424245] disabled:opacity-50 transition-colors">
              {posting ? '게시 중...' : '게시하기'}
            </button>
          </div>
        </div>
      )}

      {/* Board filter */}
      <div className="flex gap-2 flex-wrap">
        {BOARDS.map((b) => (
          <button key={b} type="button" onClick={() => { setLocalPosts(null); setBoard(b) }}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              board === b ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}>
            {b === 'all' ? '전체' : boardLabel(b)}
          </button>
        ))}
      </div>

      {/* Bulk actions */}
      {selected.size > 0 && (
        <div className="card-flat bg-blue-50 border-blue-200 flex items-center gap-3 text-sm">
          <span className="font-medium text-blue-700">{selected.size}개 선택</span>
          <button type="button" onClick={() => bulkPin(1)}
            className="px-3 py-1 rounded border border-blue-300 text-blue-700 hover:bg-blue-100 transition-colors">
            📌 일괄 고정
          </button>
          <button type="button" onClick={() => bulkPin(0)}
            className="px-3 py-1 rounded border border-gray-300 text-gray-600 hover:bg-gray-100 transition-colors">
            📍 일괄 해제
          </button>
          <button type="button" onClick={bulkDelete}
            className="px-3 py-1 rounded border border-red-300 text-red-600 hover:bg-red-50 transition-colors">
            🗑 일괄 삭제
          </button>
          <button type="button" onClick={() => setSelected(new Set())}
            className="ml-auto text-gray-400 hover:text-gray-600">선택 해제</button>
        </div>
      )}

      {actionMsg && (
        <div className="card-flat bg-blue-50 border-blue-200 text-sm text-blue-700 flex justify-between items-center">
          <span>{actionMsg}</span>
          <button type="button" onClick={() => setActionMsg(null)} className="text-blue-500 hover:text-blue-700">×</button>
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
          {/* Select all */}
          <div className="flex items-center gap-2 px-2 text-xs text-gray-400">
            <input type="checkbox" checked={selected.size === posts.length && posts.length > 0}
              onChange={toggleAll} className="rounded" />
            <span>전체 선택</span>
            {board !== 'all' && (
              <span className="ml-auto text-gray-300">⠿ 드래그로 순서 변경 가능</span>
            )}
          </div>

          {board !== 'all' ? (
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={displayPosts.map(p => p.id)} strategy={verticalListSortingStrategy}>
                {displayPosts.map((p) => (
                  <SortablePostWrapper key={`${p.board}-${p.id}`} id={p.id} disabled={editId === p.id}>
                    {renderPost(p)}
                  </SortablePostWrapper>
                ))}
              </SortableContext>
            </DndContext>
          ) : (
            displayPosts.map((p) => (
              <div key={`${p.board}-${p.id}`}>
                {renderPost(p)}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
