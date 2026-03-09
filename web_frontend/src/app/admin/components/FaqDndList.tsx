'use client'

/**
 * FaqDndList — FAQ 게시글 드래그앤드롭 순서 변경 + 인라인 편집
 * @dnd-kit/core + @dnd-kit/sortable 사용
 * API: PATCH /api/admin/community-reorder/{board}      (순서저장)
 *      GET  /api/community/{board}/{id}                (본문 로드)
 *      PATCH /api/admin/community/{board}/{id}         (수정)
 *      DELETE /api/community/{board}/{id}              (삭제)
 * sort_order: 높을수록 먼저 표시 (ORDER BY sort_order DESC)
 */

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
import { useCallback, useEffect, useState } from 'react'

export interface FaqPost {
  id: number
  title: string
  board: string
  sort_order?: number
}

type SaveState = 'idle' | 'saving' | 'saved' | 'error'

interface FaqDndListProps {
  posts: FaqPost[]
  board: string
  apiBase: string
  authHeaders: () => Record<string, string>
  onSaved: () => void
  onCancel: () => void
}

/* ── 인라인 편집 포함 행 ── */
function SortableRow({
  post,
  apiBase,
  authHeaders,
  onDeleted,
  onTitleUpdated,
}: {
  post: FaqPost
  apiBase: string
  authHeaders: () => Record<string, string>
  onDeleted: (id: number) => void
  onTitleUpdated: (id: number, title: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(post.title)
  const [editBody, setEditBody] = useState('')
  const [loadingBody, setLoadingBody] = useState(false)
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const [deleting, setDeleting] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: post.id, disabled: editing })

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 999 : undefined,
  }

  const startEdit = async () => {
    setLoadingBody(true)
    setMsg(null)
    try {
      const res = await fetch(`${apiBase}/api/community/${post.board}/${post.id}`, {
        headers: authHeaders(),
      })
      const json = await res.json()
      if (json.success && json.data) {
        setEditTitle(json.data.title || post.title)
        setEditBody(json.data.body || '')
      }
    } catch {
      setEditTitle(post.title)
      setEditBody('')
    }
    setLoadingBody(false)
    setEditing(true)
  }

  const handleSave = async () => {
    if (!editTitle.trim()) return
    setSaveState('saving')
    setMsg(null)
    try {
      const res = await fetch(`${apiBase}/api/admin/community/${post.board}/${post.id}`, {
        method: 'PATCH',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: editTitle.trim(), body: editBody.trim() }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || json.error || `Error ${res.status}`)
      setSaveState('saved')
      onTitleUpdated(post.id, editTitle.trim())
      setTimeout(() => {
        setSaveState('idle')
        setEditing(false)
      }, 1200)
    } catch (e) {
      setSaveState('error')
      setMsg(`오류: ${e instanceof Error ? e.message : '저장 실패'}`)
      setTimeout(() => setSaveState('idle'), 3000)
    }
  }

  const handleDelete = async () => {
    if (!confirm(`"${post.title}" 게시물을 삭제하시겠습니까?`)) return
    setDeleting(true)
    try {
      const res = await fetch(`${apiBase}/api/community/${post.board}/${post.id}`, {
        method: 'DELETE',
        headers: authHeaders(),
      })
      if (!res.ok) {
        const json = await res.json().catch(() => ({}))
        throw new Error(json.detail || `Error ${res.status}`)
      }
      onDeleted(post.id)
    } catch (e) {
      setMsg(`삭제 오류: ${e instanceof Error ? e.message : '실패'}`)
    } finally {
      setDeleting(false)
    }
  }

  const saveBtnClass: Record<SaveState, string> = {
    idle:   'bg-blue-600 hover:bg-blue-700',
    saving: 'bg-yellow-500 animate-pulse cursor-wait',
    saved:  'bg-green-500',
    error:  'bg-red-500',
  }
  const saveBtnText: Record<SaveState, string> = {
    idle:   '💾 저장',
    saving: '저장 중...',
    saved:  '✓ 저장됨',
    error:  '✗ 실패',
  }

  return (
    <div ref={setNodeRef} style={style} className="mb-2" {...attributes}>
      {/* 메인 행 */}
      <div
        className={`flex items-center gap-2 px-3 py-2.5 bg-white border rounded-xl select-none ${
          isDragging
            ? 'shadow-xl ring-2 ring-blue-400 border-blue-200'
            : editing
            ? 'border-yellow-300 bg-yellow-50/40'
            : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
        }`}
      >
        {/* 드래그 핸들 */}
        <span
          {...listeners}
          className={`shrink-0 flex flex-col gap-[3px] p-2 rounded cursor-grab active:cursor-grabbing touch-none text-gray-400 hover:text-gray-600 transition-colors ${
            editing ? 'opacity-30 pointer-events-none' : ''
          }`}
          title="드래그하여 순서 변경"
        >
          <span className="pointer-events-none block w-4 h-0.5 bg-current rounded" />
          <span className="pointer-events-none block w-4 h-0.5 bg-current rounded" />
          <span className="pointer-events-none block w-4 h-0.5 bg-current rounded" />
        </span>

        {/* ID 뱃지 */}
        <span className="text-[10px] text-gray-300 font-mono w-7 shrink-0">#{post.id}</span>

        {/* 제목 */}
        <span className="flex-1 text-[13px] text-gray-800 truncate">{post.title}</span>

        {/* 액션 버튼 */}
        <div className="flex items-center gap-1 shrink-0">
          {loadingBody ? (
            <span className="text-[11px] text-gray-400">로딩...</span>
          ) : editing ? (
            <span className="text-[11px] text-yellow-600 font-medium">편집 중</span>
          ) : (
            <button
              type="button"
              onClick={startEdit}
              className="p-1.5 rounded-lg text-orange-500 hover:text-orange-700 hover:bg-orange-50 transition-colors text-[12px]"
              title="수정"
            >
              ✏️
            </button>
          )}
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting || editing}
            className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors text-[12px] disabled:opacity-30"
            title="삭제"
          >
            🗑
          </button>
        </div>
      </div>

      {/* 인라인 편집 폼 */}
      {editing && (
        <div className="mx-2 mt-1 p-3 bg-yellow-50 border border-yellow-200 rounded-xl space-y-2">
          {msg && (
            <p className="text-[11px] text-red-600 font-medium">{msg}</p>
          )}
          <div>
            <label className="block text-[10px] font-medium text-gray-500 mb-1">제목</label>
            <input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-[13px] focus:outline-none focus:ring-2 focus:ring-yellow-400"
              maxLength={200}
            />
          </div>
          <div>
            <label className="block text-[10px] font-medium text-gray-500 mb-1">본문</label>
            <textarea
              value={editBody}
              onChange={(e) => setEditBody(e.target.value)}
              rows={5}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-[12px] font-mono resize-y focus:outline-none focus:ring-2 focus:ring-yellow-400"
              maxLength={10000}
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => { setEditing(false); setMsg(null); setSaveState('idle') }}
              disabled={saveState === 'saving'}
              className="px-3 py-1.5 rounded-lg text-[12px] font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 transition-colors disabled:opacity-50"
            >
              취소
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saveState === 'saving' || saveState === 'saved' || !editTitle.trim()}
              className={`px-3 py-1.5 rounded-lg text-[12px] font-medium text-white transition-colors disabled:opacity-70 ${saveBtnClass[saveState]}`}
            >
              {saveBtnText[saveState]}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── 메인 컴포넌트 ── */
export default function FaqDndList({
  posts: initialPosts,
  board,
  apiBase,
  authHeaders,
  onSaved,
  onCancel,
}: FaqDndListProps) {
  const [items, setItems] = useState<FaqPost[]>(initialPosts)
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const [msg, setMsg] = useState<string | null>(null)
  const [orderChanged, setOrderChanged] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    setItems(prev => {
      const oldIdx = prev.findIndex(p => p.id === active.id)
      const newIdx = prev.findIndex(p => p.id === over.id)
      return arrayMove(prev, oldIdx, newIdx)
    })
    setOrderChanged(true)
  }

  const handleDeleted = (id: number) => {
    setItems(prev => prev.filter(p => p.id !== id))
    setOrderChanged(true)
  }

  const handleTitleUpdated = (id: number, title: string) => {
    setItems(prev => prev.map(p => p.id === id ? { ...p, title } : p))
  }

  const handleSaveOrder = useCallback(async (force = false) => {
    if (!force && !orderChanged) return
    setSaveState('saving')
    setMsg(null)
    try {
      const reorderItems = items.map((item, idx) => ({
        id: item.id,
        sort_order: items.length - idx,
      }))
      const res = await fetch(`${apiBase}/api/admin/community-reorder/${board}`, {
        method: 'PATCH',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: reorderItems }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || json.error || `Error ${res.status}`)
      setSaveState('saved')
      setOrderChanged(false)
      // 2초간 "✓ 저장됨" 표시 후 onSaved 호출 (깜박임 방지)
      setTimeout(() => {
        setSaveState('idle')
        onSaved()
      }, 2000)
    } catch (e) {
      setSaveState('error')
      setMsg(`오류: ${e instanceof Error ? e.message : '저장 실패'}`)
      setTimeout(() => setSaveState('idle'), 3000)
    }
  }, [orderChanged, items, apiBase, board, authHeaders, onSaved])

  // EditModeBar의 "순서 저장" 버튼 → bridge:saveOrder 이벤트 수신
  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault()
      handleSaveOrder(true)
    }
    document.addEventListener('bridge:saveOrder', handler)
    return () => document.removeEventListener('bridge:saveOrder', handler)
  }, [handleSaveOrder])

  const orderBtnClass: Record<SaveState, string> = {
    idle:   orderChanged ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-100 text-gray-400 cursor-default',
    saving: 'bg-yellow-500 text-white animate-pulse cursor-wait',
    saved:  'bg-green-500 text-white',
    error:  'bg-red-500 text-white',
  }
  const orderBtnText: Record<SaveState, string> = {
    idle:   '💾 순서 저장',
    saving: '저장 중...',
    saved:  '✓ 저장됨',
    error:  '✗ 실패',
  }

  return (
    <div className="space-y-3">
      {/* 안내 배너 */}
      <div className="flex items-center gap-3 px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-xl text-[12px] text-blue-700">
        <span>≡ 왼쪽 핸들을 잡아 드래그 · ✏️ 클릭하면 수정 가능</span>
        <div className="flex-1" />
        <span className="text-blue-400">{items.length}개</span>
      </div>

      {msg && (
        <div className={`px-4 py-2 rounded-lg text-[12px] font-medium flex justify-between items-center ${
          msg.startsWith('오류') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-700'
        }`}>
          <span>{msg}</span>
          <button type="button" onClick={() => setMsg(null)} className="ml-2 opacity-60 hover:opacity-100">×</button>
        </div>
      )}

      {/* 드래그 목록 */}
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={items.map(p => p.id)} strategy={verticalListSortingStrategy}>
          <div>
            {items.map(post => (
              <SortableRow
                key={post.id}
                post={post}
                apiBase={apiBase}
                authHeaders={authHeaders}
                onDeleted={handleDeleted}
                onTitleUpdated={handleTitleUpdated}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {items.length === 0 && (
        <p className="text-center text-gray-400 text-[13px] py-8">게시물이 없습니다.</p>
      )}

      {/* 순서 저장 / 닫기 */}
      <div className="flex gap-2 pt-1">
        <button
          type="button"
          onClick={() => handleSaveOrder()}
          disabled={saveState === 'saving' || saveState === 'saved' || (!orderChanged && saveState === 'idle')}
          className={`px-4 py-2 rounded-xl text-[13px] font-semibold transition-all duration-200 disabled:opacity-70 ${orderBtnClass[saveState]}`}
        >
          {orderBtnText[saveState]}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={saveState === 'saving'}
          className="px-4 py-2 rounded-xl text-[13px] font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 transition-colors disabled:opacity-50"
        >
          ✕ 닫기
        </button>
        {orderChanged && saveState === 'idle' && (
          <span className="flex items-center text-[11px] text-blue-600 ml-1">● 순서 변경됨</span>
        )}
      </div>
    </div>
  )
}
