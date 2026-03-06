'use client'

/**
 * FaqDndList — FAQ 게시글 드래그앤드롭 순서 변경
 * @dnd-kit/core + @dnd-kit/sortable 사용
 * API: PATCH /api/admin/community-reorder/{board}
 * body: { items: [{ id: number, sort_order: number }] }
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
import { useState } from 'react'

export interface FaqPost {
  id: number
  title: string
  board: string
  sort_order?: number
}

interface FaqDndListProps {
  posts: FaqPost[]
  board: string
  apiBase: string
  authHeaders: () => Record<string, string>
  onSaved: () => void
  onCancel: () => void
}

/* ── 드래그 핸들 포함 개별 행 ── */
function SortableRow({ post }: { post: FaqPost }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: post.id })

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 999 : undefined,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center gap-3 px-4 py-3 bg-white border border-gray-200 rounded-xl mb-2 select-none ${
        isDragging ? 'shadow-xl ring-2 ring-blue-400' : 'hover:bg-gray-50'
      }`}
    >
      {/* 드래그 핸들 */}
      <button
        type="button"
        {...attributes}
        {...listeners}
        className="text-gray-300 hover:text-gray-500 cursor-grab active:cursor-grabbing p-1 -ml-1 touch-none"
        title="드래그하여 순서 변경"
        style={{ touchAction: 'none' }}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <rect x="4" y="3" width="2" height="2" rx="1" />
          <rect x="4" y="7" width="2" height="2" rx="1" />
          <rect x="4" y="11" width="2" height="2" rx="1" />
          <rect x="10" y="3" width="2" height="2" rx="1" />
          <rect x="10" y="7" width="2" height="2" rx="1" />
          <rect x="10" y="11" width="2" height="2" rx="1" />
        </svg>
      </button>

      <span className="text-[11px] text-gray-300 font-mono w-8 shrink-0">#{post.id}</span>
      <span className="flex-1 text-[13px] text-gray-800 truncate">{post.title}</span>
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
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

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
  }

  const handleSave = async () => {
    setSaving(true)
    setMsg(null)
    try {
      // sort_order: 높을수록 먼저 표시 → 첫 번째 아이템이 가장 높은 값
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
      setMsg('순서 저장 완료!')
      setTimeout(() => { onSaved() }, 800)
    } catch (e) {
      setMsg(`오류: ${e instanceof Error ? e.message : '저장 실패'}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-3">
      {/* 안내 배너 */}
      <div className="flex items-center gap-3 px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-xl text-[12px] text-blue-700">
        <span>⠿ 드래그하여 FAQ 순서를 변경하세요. 위쪽이 먼저 표시됩니다.</span>
        <div className="flex-1" />
        <span className="text-blue-400">{items.length}개</span>
      </div>

      {msg && (
        <div className={`px-4 py-2 rounded-lg text-[12px] font-medium ${
          msg.startsWith('오류') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-700'
        }`}>
          {msg}
        </div>
      )}

      {/* 드래그 목록 */}
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={items.map(p => p.id)} strategy={verticalListSortingStrategy}>
          <div>
            {items.map(post => (
              <SortableRow key={post.id} post={post} />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {/* 저장 / 취소 */}
      <div className="flex gap-2 pt-1">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="px-5 py-2 bg-[#1d1d1f] text-white text-[13px] font-semibold rounded-lg hover:bg-[#424245] disabled:opacity-50 transition-colors"
        >
          {saving ? '저장 중...' : '순서 저장'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-5 py-2 bg-gray-100 text-gray-600 text-[13px] font-medium rounded-lg hover:bg-gray-200 transition-colors"
        >
          취소
        </button>
      </div>
    </div>
  )
}
