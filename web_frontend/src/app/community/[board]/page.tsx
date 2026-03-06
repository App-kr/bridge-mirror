'use client'

/**
 * /community/[board] — Dynamic board page with layout-specific scroll animations
 * Simplified: shared BoardHeader + stripMarkdown utility
 */

import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { getBoardConfig, type BoardConfig } from '@/lib/boards'
import {
  fadeInUp,
  staggerContainer,
  scaleIn,
  slideInLeft,
  slideInRight,
  defaultViewport,
} from '@/lib/animations'
import EditModeBar, { useEditMode, NewPostButton } from '@/components/EditModeBar'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import SplitEditor, { type PostData } from '@/components/admin/SplitEditor'
import { API_URL } from '@/lib/api'
import { useDragReorder } from '@/hooks/useDragReorder'
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import AvatarPlaceholder from '@/components/ui/AvatarPlaceholder'
import {
  Eye, Pencil, Trash2, GripVertical, ChevronUp, ChevronDown,
  Check, Plus,
} from 'lucide-react'

const API = API_URL

interface Post {
  id: number
  title: string
  preview: string
  body?: string
  author_hash: string
  pinned: number
  views: number
  created_at: string
  category?: string | null
}

interface FaqItem { q: string; a: string }

interface LayoutProps {
  config: BoardConfig
  posts: Post[]
  total: number
  board: string
  faqItems?: FaqItem[]
  editMode?: boolean
  selectedIds?: Set<number>
  onToggleSelect?: (id: number) => void
  onEdit?: (post: Post) => void
  onDelete?: (postId: number) => void
  onMoveUp?: (postId: number) => void
  onMoveDown?: (postId: number) => void
  onDndMove?: (activeId: string, overId: string) => void
  onNewPost?: () => void
  onFaqEdit?: (index: number) => void
  onFaqAdd?: () => void
  onFaqDelete?: (index: number) => void
  onFaqReorder?: (index: number, direction: 'up' | 'down') => void
  faqSectionTitle?: string
  onFaqSectionTitleChange?: (title: string) => void
  orderDirty?: boolean
  orderSaving?: boolean
  onSaveOrder?: () => void
}

/** Strip markdown syntax for preview text */
function stripMd(text: string | undefined, max = 120) {
  return text?.replace(/#+\s/g, '').replace(/\*+/g, '').slice(0, max) ?? ''
}

/** Resolve accent hex from Tailwind class name */
function accentHex(color: string) {
  if (color.includes('emerald')) return '#34d399'
  if (color.includes('orange')) return '#f97316'
  return '#0071e3'
}

/** Parse FAQ markdown body into Q/A pairs */
function parseFaqBody(body: string): FaqItem[] {
  const items: FaqItem[] = []
  const blocks = body.split(/###\s+Q\d+\.?\s*/i).filter(Boolean)
  for (const block of blocks) {
    const lines = block.trim().split('\n')
    const q = lines[0]?.replace(/^#+\s*/, '').trim()
    if (!q) continue
    const rest = lines.slice(1).join('\n')
    const a = rest.replace(/^\s*\*?\*?A\.?\*?\*?\s*/m, '').trim()
    if (a) items.push({ q, a })
  }
  return items
}

// ── @dnd-kit sortable wrappers ─────────────────────────────────────────────

// Context passes drag handle props from SortableItem → SortHandle's GripVertical
const DragHandleCtx = createContext<Record<string, unknown> | null>(null)

function SortableContainer({ items, onDragEnd, children }: {
  items: string[]; onDragEnd: (e: DragEndEvent) => void; children: React.ReactNode
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  )
  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
      <SortableContext items={items} strategy={verticalListSortingStrategy}>
        {children}
      </SortableContext>
    </DndContext>
  )
}

function SortableItem({ id, children }: { id: string; children: React.ReactNode }) {
  const {
    attributes, listeners, setNodeRef, transform, transition, isDragging,
  } = useSortable({ id })
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.45 : 1,
    position: 'relative',
    zIndex: isDragging ? 10 : undefined,
  }
  return (
    <DragHandleCtx.Provider value={{ ...attributes, ...listeners }}>
      <div ref={setNodeRef} style={style}>
        {children}
      </div>
    </DragHandleCtx.Provider>
  )
}

// ── Admin UI Components ──────────────────────────────────────────────────────

function AdminCheckbox({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <span onClick={(e) => { e.preventDefault(); e.stopPropagation() }}>
      <button type="button" onClick={onChange}
        className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors shrink-0 ${
          checked ? 'bg-blue-600 border-blue-600' : 'border-zinc-400 hover:border-zinc-300 bg-transparent'
        }`}>
        {checked && <Check size={12} className="text-white" strokeWidth={3} />}
      </button>
    </span>
  )
}

function SortHandle({ onMoveUp, onMoveDown, isFirst, isLast }: {
  onMoveUp: () => void; onMoveDown: () => void
  isFirst?: boolean; isLast?: boolean
}) {
  const dragProps = useContext(DragHandleCtx)
  return (
    <span className="inline-flex items-center gap-0.5 shrink-0"
      onClick={(e) => { e.preventDefault(); e.stopPropagation() }}>
      {dragProps && (
        <span {...dragProps}
          className="cursor-grab active:cursor-grabbing p-1 rounded hover:bg-zinc-700/50 transition-colors touch-none"
          title="Drag to reorder">
          <GripVertical size={14} className="text-zinc-400" />
        </span>
      )}
      <button type="button" onClick={onMoveUp} disabled={isFirst}
        className={`p-1 rounded transition-colors ${isFirst ? 'opacity-20 cursor-default' : 'text-zinc-400 hover:text-white hover:bg-zinc-700/50'}`}
        title="Move up">
        <ChevronUp size={16} />
      </button>
      <button type="button" onClick={onMoveDown} disabled={isLast}
        className={`p-1 rounded transition-colors ${isLast ? 'opacity-20 cursor-default' : 'text-zinc-400 hover:text-white hover:bg-zinc-700/50'}`}
        title="Move down">
        <ChevronDown size={16} />
      </button>
    </span>
  )
}

function InlineAdminActions({ post, board, onEdit, onDelete }: {
  post: Post; board: string; onEdit: (post: Post) => void; onDelete: (postId: number) => void
}) {
  return (
    <span className="inline-flex items-center gap-0.5 ml-auto shrink-0"
      onClick={(e) => { e.preventDefault(); e.stopPropagation() }}>
      <button type="button"
        onClick={() => window.open(`/community/${board}/${post.id}`, '_blank')}
        className="p-1.5 rounded text-zinc-400 hover:text-white hover:bg-zinc-700/50 transition-colors" title="View">
        <Eye size={15} />
      </button>
      <button type="button" onClick={() => onEdit(post)}
        className="p-1.5 rounded text-zinc-400 hover:text-blue-400 hover:bg-zinc-700/50 transition-colors" title="Edit">
        <Pencil size={15} />
      </button>
      <button type="button" onClick={() => onDelete(post.id)}
        className="p-1.5 rounded text-zinc-400 hover:text-red-400 hover:bg-zinc-700/50 transition-colors" title="Delete">
        <Trash2 size={15} />
      </button>
    </span>
  )
}

function BulkActionBar({ count, totalCount, onSelectAll, onClearSelection, onBulkDelete, onBulkPin }: {
  count: number; totalCount: number
  onSelectAll: () => void; onClearSelection: () => void
  onBulkDelete: () => void; onBulkPin: () => void
}) {
  return (
    <div className="bg-zinc-800 border-b border-zinc-700 px-6 py-2.5 flex items-center gap-4 text-sm">
      <span className="text-zinc-300 font-medium">{count} selected</span>
      <button type="button" onClick={onBulkPin}
        className="flex items-center gap-1.5 px-3 py-1.5 text-blue-400 hover:bg-blue-500/10 rounded transition-colors">
        <ChevronUp size={14} /> Bulk Pin
      </button>
      <button type="button" onClick={onBulkDelete}
        className="flex items-center gap-1.5 px-3 py-1.5 text-red-400 hover:bg-red-500/10 rounded transition-colors">
        <Trash2 size={14} /> Bulk Delete
      </button>
      <div className="ml-auto">
        <button type="button"
          onClick={count === totalCount ? onClearSelection : onSelectAll}
          className="text-zinc-400 hover:text-white transition-colors">
          {count === totalCount ? 'Deselect All' : 'Select All'}
        </button>
      </div>
    </div>
  )
}

// ── Shared Board Header ──
function BoardHeader({ config, board, editMode, onNewPost, orderDirty, orderSaving, onSaveOrder }: {
  config: BoardConfig; board?: string; editMode?: boolean; onNewPost?: () => void
  orderDirty?: boolean; orderSaving?: boolean; onSaveOrder?: () => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-3xl font-bold text-[#1d1d1f]">{config.label}</h1>
        <div className="flex items-center gap-2">
          {editMode && orderDirty && onSaveOrder && (
            <button type="button" onClick={onSaveOrder} disabled={orderSaving}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-orange-500 hover:bg-orange-600 disabled:opacity-60 text-white text-sm font-medium rounded-full transition-colors">
              {orderSaving ? '저장 중...' : '💾 순서 저장'}
            </button>
          )}
          {editMode && onNewPost ? (
            <button type="button" onClick={onNewPost}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0071e3] text-white text-sm font-medium rounded-full hover:bg-[#0077ED] transition-colors">
              <Plus size={14} /> New Post
            </button>
          ) : (
            board && <NewPostButton board={board} />
          )}
        </div>
      </div>
      <p className="text-[#86868b] text-sm mb-8">{config.description}</p>
      {config.notice && (
        <div className="bg-[#f5f5f7] rounded-xl px-5 py-4 text-sm text-[#6e6e73] -mt-4 mb-8">
          {config.notice}
        </div>
      )}
    </motion.div>
  )
}

// ── Hardcoded FAQ Data ──
const TEACHER_FAQ: FaqItem[] = [
  {
    q: 'Do I need teaching experience to apply?',
    a: 'No. While experience is preferred, BRIDGE will match you with positions that fit your experience level.\n\n경력이 없어도 지원할 수 있나요? 네. 경력이 있으면 유리하지만, 경력 없이도 지원 가능합니다.',
  },
  {
    q: 'Which nationalities are eligible for E-2 visas?',
    a: "Citizens of USA, Canada, UK, Ireland, Australia, New Zealand, and South Africa. Must hold a bachelor's degree.\n\nE-2 비자 대상 국적은 미국, 캐나다, 영국, 아일랜드, 호주, 뉴질랜드, 남아공. 4년제 학위 필요.",
  },
  {
    q: 'How long does the process take?',
    a: 'Outside Korea: 6-10 weeks. Already in Korea with valid visa: 2-4 weeks.\n\n해외 거주자 6~10주, 국내 거주자(비자 보유) 2~4주.',
  },
  {
    q: 'Is housing provided?',
    a: 'Most positions include furnished housing or a housing allowance, though not mandatory.\n\n의무는 아니지만 대부분 숙소 제공 또는 주거수당 포함.',
  },
  {
    q: 'Can I choose which city I work in?',
    a: 'Yes. State your preference, BRIDGE will prioritize. Being flexible increases options.\n\n네. 희망 지역 우선 매칭. 유연할수록 선택지 넓어짐.',
  },
]

const EMPLOYER_FAQ: FaqItem[] = [
  {
    q: '채용 의뢰 비용이 있나요?',
    a: '미등록 기관 등 특수 상황에 상담비 발생 가능. 채용수수료는 채용 과정에서 발생.',
  },
  {
    q: '후보자를 직접 선택할 수 있나요?',
    a: '물론. BRIDGE가 추천하지만 최종 결정은 교육기관에서 인터뷰를 통해 직접.',
  },
  {
    q: '성사된 강사가 조기 퇴사하면?',
    a: '고용주 측 문제 없음에도 1개월 내 퇴사 시 환불 가능. 보증 조건은 계약서 명시.',
  },
  {
    q: '비자 서류는 누가 준비?',
    a: '강사 해외 서류는 BRIDGE 안내, 고용주 한국 서류도 함께 안내.',
  },
]

// ── Constants ──
const POST_IMAGES: Record<string, string> = {
  Seoul:      'https://images.unsplash.com/photo-1541694764078-df09dec4f9c8?w=480&h=320&fit=crop',
  Gyeonggi:   'https://images.unsplash.com/photo-1584527810790-01a904be796b?w=480&h=320&fit=crop',
  Incheon:    'https://images.unsplash.com/photo-1610870596605-d293eaf5a1ad?w=480&h=320&fit=crop',
  Busan:      'https://images.unsplash.com/photo-1592158072350-aa83a6d9dd50?w=480&h=320&fit=crop',
  Daegu:      'https://images.unsplash.com/photo-1741042174069-65868336324a?w=480&h=320&fit=crop',
  Daejeon:    'https://images.unsplash.com/photo-1687722157890-9f58d5cd26d4?w=480&h=320&fit=crop',
  Jeju:       'https://images.unsplash.com/photo-1730898652585-bda492ae1b41?w=480&h=320&fit=crop',
  Food:       'https://images.unsplash.com/photo-1532347231146-80afc9e3df2b?w=480&h=320&fit=crop',
  Healthcare: 'https://images.unsplash.com/photo-1516841273335-e39b37888115?w=480&h=320&fit=crop',
  Banking:    'https://images.unsplash.com/photo-1750262701487-4ca222c89ef4?w=480&h=320&fit=crop',
  Transport:  'https://images.unsplash.com/photo-1588043213440-fd9c881853e9?w=480&h=320&fit=crop',
  Phone:      'https://images.unsplash.com/photo-1731616103660-eb50daa4696d?w=480&h=320&fit=crop',
}
const KOREA_MAP_LINKS: Record<string, string> = {
  Seoul: 'https://maps.google.com/?q=Seoul,Korea',
  Gyeonggi: 'https://maps.google.com/?q=Gyeonggi-do,Korea',
  Incheon: 'https://maps.google.com/?q=Incheon,Korea',
  Busan: 'https://maps.google.com/?q=Busan,Korea',
  Daegu: 'https://maps.google.com/?q=Daegu,Korea',
  Daejeon: 'https://maps.google.com/?q=Daejeon,Korea',
  Jeju: 'https://maps.google.com/?q=Jeju,Korea',
}

/** Match post title to image key — check specific keywords before generic ones */
function getPostImageKey(title: string): string {
  const t = title.toLowerCase()
  if (t.includes('transport') || t.includes('getting around') || t.includes('교통')) return 'Transport'
  if (t.includes('phone') || t.includes('internet') || t.includes('통신') || t.includes('digital')) return 'Phone'
  if (t.includes('food') || t.includes('음식')) return 'Food'
  if (t.includes('health') || t.includes('의료')) return 'Healthcare'
  if (t.includes('bank') || t.includes('금융') || t.includes('money')) return 'Banking'
  if (t.includes('gyeonggi') || t.includes('경기')) return 'Gyeonggi'
  if (t.includes('incheon') || t.includes('인천')) return 'Incheon'
  if (t.includes('busan') || t.includes('부산')) return 'Busan'
  if (t.includes('daegu') || t.includes('대구')) return 'Daegu'
  if (t.includes('daejeon') || t.includes('대전')) return 'Daejeon'
  if (t.includes('jeju') || t.includes('제주')) return 'Jeju'
  if (t.includes('seoul') || t.includes('서울')) return 'Seoul'
  return 'Seoul'
}

const TIPS_COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1']
const TIPS_EMOJIS = ['📸', '🎓', '🎤']
const HERO_ICONS = ['🏢', '📋', '🆕', '📝', '💰']
// ── Animated counter hook (for About page stats) ──
function useAnimatedCounter(target: number, duration: number, start: boolean) {
  const [value, setValue] = useState(0)
  useEffect(() => {
    if (!start) return
    let t0: number | null = null
    let frame: number
    const step = (ts: number) => {
      if (!t0) t0 = ts
      const p = Math.min((ts - t0) / duration, 1)
      setValue(Math.floor((1 - Math.pow(1 - p, 3)) * target))
      if (p < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [target, duration, start])
  return value
}

/** Calculate dynamic stat values based on base date 2026-03-03 */
function getDynamicStats() {
  const baseDate = new Date('2026-03-03')
  const now = new Date()
  const weeksDiff = Math.max(0, Math.floor((now.getTime() - baseDate.getTime()) / (7 * 24 * 60 * 60 * 1000)))
  const monthsDiff = Math.max(0, (now.getFullYear() - baseDate.getFullYear()) * 12 + (now.getMonth() - baseDate.getMonth()))
  return [
    { label: 'Years Experience', target: 15, suffix: '+' },
    { label: 'Countries', target: 7, suffix: '' },
    { label: 'Partner Schools', target: 6222 + weeksDiff * 5, suffix: '+' },
    { label: 'Teachers Placed', target: 17938 + monthsDiff * 100, suffix: '+' },
  ]
}

// ── Why BRIDGE cards ──
const WHY_BRIDGE = [
  {
    icon: '👥',
    title: 'Candidate Pool',
    desc: '소개 전 기본적인 학위, 교육배경 등을 확인합니다.',
  },
  {
    icon: '🎯',
    title: 'Matching',
    desc: '충분히 좋은 공고를 가진 기관과는 당일 매치도 가능하며 철저한 필터링으로 빠른 매칭을 선사합니다.',
  },
  {
    icon: '🏆',
    title: 'Expertise',
    desc: '각 리크루터가 최소 10년 이상 경력의 전문가로서, 다양한 변화에 빠른 대응이 가능합니다.',
  },
  {
    icon: '💬',
    title: 'Communication',
    desc: '채용 전후 사후관리에 고용주와 피고용인 모두 지속 관리합니다.',
  },
]

// ══════════════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ══════════════════════════════════════════════════════════════════════════════
export default function BoardPage() {
  const { board } = useParams<{ board: string }>()
  const config = getBoardConfig(board)
  const editMode = useEditMode()
  const { signedFetch } = useAdminAuth()

  const [posts, setPosts] = useState<Post[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [faqItems, setFaqItems] = useState<FaqItem[]>([])
  const [faqPostId, setFaqPostId] = useState<number | null>(null)
  const [faqSectionTitle, setFaqSectionTitle] = useState('')

  // Unified editor state
  const [editorOpen, setEditorOpen] = useState(false)
  const [editorInitialData, setEditorInitialData] = useState<{ title: string; content: string }>({ title: '', content: '' })
  const [editorPreviewType, setEditorPreviewType] = useState<'faq' | 'list' | 'card' | 'testimonial'>('list')
  const [editorCtx, setEditorCtx] = useState<{
    type: 'post-create' | 'post-edit' | 'faq-new' | 'faq-edit'
    postId?: number
    faqIndex?: number
  }>({ type: 'post-create' })

  // Selection state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  const refreshPosts = useCallback(() => {
    if (!config) return
    fetch(`${API}/api/community/${board}?limit=50`)
      .then((r) => r.json())
      .then((j) => { if (j.success) { setPosts(j.data.posts); setTotal(j.data.total) } })
  }, [board, config])

  useEffect(() => {
    if (!config) return
    fetch(`${API}/api/community/${board}?limit=50`)
      .then((r) => r.json())
      .then((j) => { if (j.success) { setPosts(j.data.posts); setTotal(j.data.total) } })
      .finally(() => setLoading(false))

    const faqCat = board === 'support' ? 'faq-teacher' : board === 'support_kr' ? 'faq-employer' : null
    const defaultFaq = board === 'support' ? TEACHER_FAQ : board === 'support_kr' ? EMPLOYER_FAQ : []
    if (faqCat) {
      fetch(`${API}/api/community/${board}?category=${faqCat}`)
        .then((r) => r.json())
        .then((j) => {
          if (j.success && j.data.posts.length > 0) {
            const post = j.data.posts[0]
            setFaqPostId(post.id)
            if (post.title) setFaqSectionTitle(post.title)
            const parsed = parseFaqBody(post.body ?? '')
            setFaqItems(parsed.length > 0 ? parsed : defaultFaq)
          } else {
            setFaqItems(defaultFaq)
          }
        })
        .catch(() => { setFaqItems(defaultFaq) })
    }
  }, [board, config])

  // ── Admin handlers ──
  const getPostPreviewType = useCallback((): 'list' | 'card' | 'testimonial' => {
    switch (config?.layout) {
      case 'card-grid': return 'card'
      case 'photo-cards': return 'card'
      case 'testimonial':
      case 'testimonials': return 'testimonial'
      default: return 'list'
    }
  }, [config])

  const handleNewPost = useCallback(() => {
    setEditorInitialData({ title: '', content: '' })
    setEditorPreviewType(getPostPreviewType())
    setEditorCtx({ type: 'post-create' })
    setEditorOpen(true)
  }, [getPostPreviewType])

  const handleEdit = useCallback(async (post: Post) => {
    const pvType = getPostPreviewType()
    try {
      const res = await fetch(`${API}/api/community/${board}/${post.id}`)
      const j = await res.json()
      if (j.success) {
        setEditorInitialData({ title: j.data.title ?? post.title, content: j.data.body ?? '' })
      } else {
        setEditorInitialData({ title: post.title, content: post.preview ?? '' })
      }
    } catch {
      setEditorInitialData({ title: post.title, content: post.preview ?? '' })
    }
    setEditorPreviewType(pvType)
    setEditorCtx({ type: 'post-edit', postId: post.id })
    setEditorOpen(true)
  }, [board, getPostPreviewType])

  const handleDelete = useCallback(async (postId: number) => {
    if (!confirm('Delete this post?')) return
    try {
      const res = await signedFetch(`${API_URL}/api/community/${board}/${postId}`, { method: 'DELETE' })
      if (res.ok) {
        setSelectedIds((prev) => { const n = new Set(prev); n.delete(postId); return n })
        refreshPosts()
      }
    } catch { /* noop */ }
  }, [board, signedFetch, refreshPosts])

  // Post drag reorder — explicit save button
  const [orderDirty, setOrderDirty] = useState(false)
  const [orderSaving, setOrderSaving] = useState(false)

  const onReorderLocal = useCallback(() => {
    setOrderDirty(true)
  }, [])

  const postDrag = useDragReorder<Post>(posts, onReorderLocal)

  const handleSaveOrder = useCallback(async () => {
    const items = postDrag.items.map((p, i) => ({ id: p.id, sort_order: (postDrag.items.length - i) * 10 }))
    setOrderSaving(true)
    try {
      const res = await signedFetch(`${API_URL}/api/admin/community-reorder/${board}`, {
        method: 'PATCH',
        body: JSON.stringify({ items }),
      })
      if (res.ok) {
        setOrderDirty(false)
        refreshPosts()
      }
    } catch { /* noop */ }
    setOrderSaving(false)
  }, [postDrag.items, board, signedFetch, refreshPosts])

  // Sync posts from API into drag hook
  useEffect(() => {
    postDrag.setItems(posts)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [posts])

  const handleMoveUp = useCallback((postId: number) => {
    const idx = postDrag.items.findIndex(p => p.id === postId)
    if (idx > 0) postDrag.handleMoveUp(idx)
  }, [postDrag])

  const handleMoveDown = useCallback((postId: number) => {
    const idx = postDrag.items.findIndex(p => p.id === postId)
    if (idx >= 0) postDrag.handleMoveDown(idx)
  }, [postDrag])

  const handleDndMove = useCallback((activeId: string, overId: string) => {
    const fromIdx = postDrag.items.findIndex(p => String(p.id) === activeId)
    const toIdx = postDrag.items.findIndex(p => String(p.id) === overId)
    if (fromIdx >= 0 && toIdx >= 0) postDrag.handleDndMove(fromIdx, toIdx)
  }, [postDrag])

  // Selection handlers
  const toggleSelect = useCallback((id: number) => {
    setSelectedIds((prev) => {
      const n = new Set(prev)
      if (n.has(id)) n.delete(id); else n.add(id)
      return n
    })
  }, [])

  const selectAll = useCallback(() => {
    setSelectedIds(new Set(posts.map((p) => p.id)))
  }, [posts])

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set())
  }, [])

  const handleBulkDelete = useCallback(async () => {
    if (!confirm(`Delete ${selectedIds.size} posts?`)) return
    for (const id of selectedIds) {
      await signedFetch(`${API_URL}/api/community/${board}/${id}`, { method: 'DELETE' }).catch(() => {})
    }
    setSelectedIds(new Set())
    refreshPosts()
  }, [selectedIds, board, signedFetch, refreshPosts])

  const handleBulkPin = useCallback(async () => {
    for (const id of selectedIds) {
      await signedFetch(`${API_URL}/api/admin/community/posts/${id}/pin`, {
        method: 'PATCH', body: JSON.stringify({ pinned: 1 }),
      }).catch(() => {})
    }
    setSelectedIds(new Set())
    refreshPosts()
  }, [selectedIds, signedFetch, refreshPosts])

  // ── FAQ handlers ──
  const serializeFaq = (items: FaqItem[]): string => {
    return items.map((item, i) => `### Q${i + 1}. ${item.q}\n**A.** ${item.a}`).join('\n\n')
  }

  const saveFaqToApi = useCallback(async (items: FaqItem[], titleOverride?: string) => {
    const defaultTitle = board === 'support' ? 'Teacher FAQ' : 'Employer FAQ'
    const title = titleOverride || faqSectionTitle || defaultTitle
    const category = board === 'support' ? 'faq-teacher' : 'faq-employer'
    const body = serializeFaq(items)
    try {
      if (faqPostId) {
        await signedFetch(`${API_URL}/api/admin/community/${board}/${faqPostId}`, {
          method: 'PATCH',
          body: JSON.stringify({ title, body, category }),
        })
      } else {
        const res = await signedFetch(`${API_URL}/api/community/${board}`, {
          method: 'POST',
          body: JSON.stringify({ title, body, category }),
        })
        const j = await res.json().catch(() => ({}))
        if (j.success && j.data?.id) setFaqPostId(j.data.id)
      }
    } catch { /* noop */ }
  }, [board, faqPostId, faqSectionTitle, signedFetch])

  const handleFaqSectionTitleChange = useCallback(async (newTitle: string) => {
    setFaqSectionTitle(newTitle)
    await saveFaqToApi(faqItems, newTitle)
  }, [faqItems, saveFaqToApi])

  const handleEditorSave = useCallback(async (data: PostData) => {
    const { type, postId, faqIndex } = editorCtx

    if (type === 'faq-new' || type === 'faq-edit') {
      let updated: FaqItem[]
      if (type === 'faq-new') {
        updated = [...faqItems, { q: data.title, a: data.content }]
      } else {
        updated = faqItems.map((item, i) =>
          i === faqIndex ? { q: data.title, a: data.content } : item
        )
      }
      setFaqItems(updated)
      setEditorOpen(false)
      await saveFaqToApi(updated)
    } else if (type === 'post-create') {
      const res = await signedFetch(`${API_URL}/api/community/${board}`, {
        method: 'POST',
        body: JSON.stringify({ title: data.title, body: data.content, content_type: data.contentType }),
      })
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(j.detail || j.error || `Error ${res.status}`)
      }
      setEditorOpen(false)
      refreshPosts()
    } else if (type === 'post-edit' && postId) {
      const res = await signedFetch(`${API_URL}/api/admin/community/${board}/${postId}`, {
        method: 'PATCH',
        body: JSON.stringify({ title: data.title, body: data.content, content_type: data.contentType }),
      })
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(j.detail || j.error || `Error ${res.status}`)
      }
      setEditorOpen(false)
      refreshPosts()
    }
  }, [editorCtx, faqItems, saveFaqToApi, board, signedFetch, refreshPosts])

  const handleFaqItemEdit = useCallback((index: number) => {
    const item = faqItems[index]
    if (!item) return
    setEditorInitialData({ title: item.q, content: item.a })
    setEditorPreviewType('faq')
    setEditorCtx({ type: 'faq-edit', faqIndex: index })
    setEditorOpen(true)
  }, [faqItems])

  const handleFaqItemAdd = useCallback(() => {
    setEditorInitialData({ title: '', content: '' })
    setEditorPreviewType('faq')
    setEditorCtx({ type: 'faq-new' })
    setEditorOpen(true)
  }, [])

  const handleFaqItemDelete = useCallback(async (index: number) => {
    if (!confirm('Delete this FAQ item?')) return
    const updated = faqItems.filter((_, i) => i !== index)
    setFaqItems(updated)
    await saveFaqToApi(updated)
  }, [faqItems, saveFaqToApi])

  const handleFaqItemReorder = useCallback(async (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1
    if (newIndex < 0 || newIndex >= faqItems.length) return
    const updated = [...faqItems]
    ;[updated[index], updated[newIndex]] = [updated[newIndex], updated[index]]
    setFaqItems(updated)
    await saveFaqToApi(updated)
  }, [faqItems, saveFaqToApi])

  if (!config) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center">
        <p className="text-[#86868b] text-lg">Board not found.</p>
        <Link href="/community" className="text-[#0071e3] text-sm mt-2 block">&larr; Back to Community</Link>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => <div key={i} className="skeleton h-14 w-full" />)}
        </div>
      </div>
    )
  }

  const displayPosts = editMode ? postDrag.items : posts

  const props: LayoutProps = {
    config, posts: displayPosts, total, board, faqItems,
    editMode,
    selectedIds,
    onToggleSelect: toggleSelect,
    onEdit: handleEdit,
    onDelete: handleDelete,
    onMoveUp: handleMoveUp,
    onMoveDown: handleMoveDown,
    onDndMove: handleDndMove,
    onNewPost: handleNewPost,
    onFaqEdit: handleFaqItemEdit,
    onFaqAdd: handleFaqItemAdd,
    onFaqDelete: handleFaqItemDelete,
    onFaqReorder: handleFaqItemReorder,
    faqSectionTitle,
    onFaqSectionTitleChange: handleFaqSectionTitleChange,
  }

  const Layout = (() => {
    switch (config.layout) {
      case 'list':         return ListLayout
      case 'hero-cards':   return HeroCardsLayout
      case 'card-grid':    return CardGridLayout
      case 'photo-cards':  return PhotoCardsLayout
      case 'testimonial':
      case 'testimonials': return TestimonialLayout
      default:             return ListLayout
    }
  })()

  return (
    <>
      <EditModeBar />
      {editMode && selectedIds.size > 0 && (
        <BulkActionBar
          count={selectedIds.size}
          totalCount={posts.length}
          onSelectAll={selectAll}
          onClearSelection={clearSelection}
          onBulkDelete={handleBulkDelete}
          onBulkPin={handleBulkPin}
        />
      )}
      <Layout {...props} />
      {editMode && orderDirty && (
        <button
          type="button"
          onClick={handleSaveOrder}
          disabled={orderSaving}
          className="fixed bottom-14 right-5 z-[9998] flex items-center gap-2 px-4 py-2.5 bg-orange-500 hover:bg-orange-600 disabled:opacity-60 text-white text-sm font-bold rounded-full shadow-lg transition-colors animate-pulse"
        >
          {orderSaving ? '저장 중...' : '💾 순서 저장'}
        </button>
      )}
      {editorOpen && (
        <SplitEditor
          isOpen={true}
          initialData={editorInitialData}
          previewType={editorPreviewType}
          onSave={handleEditorSave}
          onClose={() => setEditorOpen(false)}
        />
      )}
    </>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// LIST — Visa / Support / 업무지원
// ══════════════════════════════════════════════════════════════════════════════
function ListLayout({ config, posts, board, faqItems, editMode, selectedIds, onToggleSelect, onEdit, onDelete, onMoveUp, onMoveDown, onDndMove, onNewPost, onFaqEdit, onFaqAdd, onFaqDelete, onFaqReorder, faqSectionTitle, onFaqSectionTitleChange }: LayoutProps) {
  const regularPosts = posts.filter((p) => !p.title.toLowerCase().includes('faq'))
  const [editingTitle, setEditingTitle] = useState(false)
  const [titleDraft, setTitleDraft] = useState('')

  const defaultLabel = board === 'support' ? 'Teacher FAQ' : board === 'support_kr' ? '자주 묻는 질문' : ''
  const sectionLabel = faqSectionTitle || defaultLabel

  const faqConfig = board === 'support'
    ? { bg: 'bg-[#0a1628]', accent: '#3b82f6', label: sectionLabel, badgeBg: 'bg-blue-500/20', badgeText: 'text-blue-300', items: faqItems && faqItems.length > 0 ? faqItems : TEACHER_FAQ }
    : board === 'support_kr'
    ? { bg: 'bg-[#0a1f12]', accent: '#22c55e', label: sectionLabel, badgeBg: 'bg-green-500/20', badgeText: 'text-green-300', items: faqItems && faqItems.length > 0 ? faqItems : EMPLOYER_FAQ }
    : null

  const handleTitleSave = () => {
    const trimmed = titleDraft.trim()
    if (trimmed && trimmed !== sectionLabel && onFaqSectionTitleChange) {
      onFaqSectionTitleChange(trimmed)
    }
    setEditingTitle(false)
  }

  return (
    <div>
      {/* ── FAQ Accordion Section ── */}
      {faqConfig && faqConfig.items.length > 0 && (
        <section className={`${faqConfig.bg} py-16 sm:py-20`}>
          <div className="max-w-3xl mx-auto px-4 sm:px-6">
            <motion.div
              className="text-center mb-10"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${faqConfig.badgeBg} ${faqConfig.badgeText} mb-4`}>
                FAQ
              </span>
              {editMode && editingTitle ? (
                <input
                  type="text"
                  value={titleDraft}
                  onChange={(e) => setTitleDraft(e.target.value)}
                  onBlur={handleTitleSave}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleTitleSave() }}
                  autoFocus
                  className="text-2xl sm:text-3xl font-bold text-white tracking-tight bg-transparent border-b-2 border-white/40 outline-none text-center w-full max-w-md mx-auto block"
                />
              ) : (
                <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight inline-flex items-center gap-2 justify-center">
                  {faqConfig.label}
                  {editMode && onFaqSectionTitleChange && (
                    <button type="button"
                      onClick={() => { setTitleDraft(sectionLabel); setEditingTitle(true) }}
                      className="p-1.5 rounded text-white/40 hover:text-white hover:bg-white/10 transition-colors"
                      title="Edit section title">
                      <Pencil size={16} />
                    </button>
                  )}
                </h2>
              )}
            </motion.div>

            <motion.div
              className="space-y-3"
              variants={staggerContainer} initial="hidden" animate="visible"
            >
              {faqConfig.items.map((item, i) => (
                <FaqAccordionItem key={i} item={item} index={i} accent={faqConfig.accent}
                  editMode={editMode}
                  onEdit={onFaqEdit ? () => onFaqEdit(i) : undefined}
                  onDelete={onFaqDelete ? () => onFaqDelete(i) : undefined}
                  onMoveUp={onFaqReorder ? () => onFaqReorder(i, 'up') : undefined}
                  onMoveDown={onFaqReorder ? () => onFaqReorder(i, 'down') : undefined}
                  isFirst={i === 0}
                  isLast={i === faqConfig.items.length - 1}
                />
              ))}
              {editMode && onFaqAdd && (
                <motion.div variants={fadeInUp}>
                  <button type="button" onClick={onFaqAdd}
                    className="w-full flex items-center justify-center gap-2 px-5 py-4 rounded-xl border-2 border-dashed border-white/20 text-white/50 hover:border-white/40 hover:text-white/70 transition-colors text-sm font-medium">
                    <Plus size={16} /> 질문 추가
                  </button>
                </motion.div>
              )}
            </motion.div>

            {board === 'support_kr' && (
              <motion.div
                className="mt-10 text-center"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                <p className="text-white/50 text-sm mb-3">기타 궁금한 사항은 카카오톡 채널로 문의해주세요.</p>
                <a href="http://pf.kakao.com/_tBxhxkK/chat" target="_blank" rel="noopener noreferrer"
                  className="inline-block px-5 py-2.5 bg-[#FEE500] text-[#191919] text-sm font-medium rounded-full hover:bg-[#F5DC00] transition-colors">
                  카카오톡 문의하기
                </a>
              </motion.div>
            )}
          </div>
        </section>
      )}

      {/* ── Regular Post List ── */}
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
        <BoardHeader config={config} board={board} editMode={editMode} onNewPost={onNewPost} />
        {regularPosts.length === 0 ? (
          <p className="text-[#86868b] text-center py-16">No posts yet.</p>
        ) : editMode ? (
          <SortableContainer
            items={regularPosts.map(p => String(p.id))}
            onDragEnd={(e) => { if (e.over && e.active.id !== e.over.id) onDndMove?.(String(e.active.id), String(e.over.id)) }}
          >
            {regularPosts.map((p, i) => (
              <SortableItem key={p.id} id={String(p.id)}>
                <div className="flex items-center gap-1.5">
                  {onMoveUp && onMoveDown && (
                    <SortHandle
                      onMoveUp={() => onMoveUp(p.id)} onMoveDown={() => onMoveDown(p.id)}
                      isFirst={i === 0} isLast={i === regularPosts.length - 1}
                    />
                  )}
                  {onToggleSelect && (
                    <AdminCheckbox checked={selectedIds?.has(p.id) ?? false} onChange={() => onToggleSelect(p.id)} />
                  )}
                  <Link
                    href={`/community/${board}/${p.id}`}
                    className="board-list-item group flex-1"
                    style={{ '--accent-color': accentHex(config.accentColor) } as React.CSSProperties}
                  >
                    <span className="text-[15px] text-[#1d1d1f] font-medium group-hover:text-inherit">{p.title}</span>
                    {onEdit && onDelete && (
                      <InlineAdminActions post={p} board={board} onEdit={onEdit} onDelete={onDelete} />
                    )}
                  </Link>
                </div>
              </SortableItem>
            ))}
          </SortableContainer>
        ) : (
          <motion.div variants={staggerContainer} initial="hidden" animate="visible">
            {regularPosts.map((p) => (
              <motion.div key={p.id} variants={fadeInUp}>
                <Link
                  href={`/community/${board}/${p.id}`}
                  className="board-list-item group"
                  style={{ '--accent-color': accentHex(config.accentColor) } as React.CSSProperties}
                >
                  <span className="text-[15px] text-[#1d1d1f] font-medium group-hover:text-inherit">{p.title}</span>
                  <span className="arrow">&rarr;</span>
                </Link>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </div>
  )
}

// ── FAQ Accordion Item ──
function FaqAccordionItem({ item, index, accent, editMode, onEdit, onDelete, onMoveUp, onMoveDown, isFirst, isLast }: {
  item: FaqItem; index: number; accent: string; editMode?: boolean
  onEdit?: () => void; onDelete?: () => void
  onMoveUp?: () => void; onMoveDown?: () => void
  isFirst?: boolean; isLast?: boolean
}) {
  const [open, setOpen] = useState(false)

  return (
    <motion.div
      className="rounded-xl overflow-hidden"
      style={{
        background: 'rgba(255,255,255,0.05)',
        border: `1px solid rgba(255,255,255,0.08)`,
        borderLeft: `3px solid ${accent}`,
      }}
      variants={fadeInUp}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.2 }}
    >
      <button
        type="button"
        className="w-full flex items-center gap-3 px-5 py-4 text-left group"
        onClick={() => setOpen((v) => !v)}
      >
        <span
          className="shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white"
          style={{ background: accent }}
        >
          {index + 1}
        </span>
        <span className="text-[15px] font-medium text-white/90 flex-1 group-hover:text-white transition-colors">
          {item.q}
        </span>
        {editMode && (
          <span className="inline-flex items-center gap-0.5 mr-2"
            onClick={(e) => { e.stopPropagation() }}>
            {onMoveUp && !isFirst && (
              <button type="button" onClick={onMoveUp}
                className="p-1.5 rounded text-zinc-400 hover:text-white hover:bg-zinc-700/50 transition-colors" title="Move Up">
                <ChevronUp size={15} />
              </button>
            )}
            {onMoveDown && !isLast && (
              <button type="button" onClick={onMoveDown}
                className="p-1.5 rounded text-zinc-400 hover:text-white hover:bg-zinc-700/50 transition-colors" title="Move Down">
                <ChevronDown size={15} />
              </button>
            )}
            {onEdit && (
              <button type="button" onClick={onEdit}
                className="p-1.5 rounded text-zinc-400 hover:text-blue-400 hover:bg-zinc-700/50 transition-colors" title="Edit FAQ">
                <Pencil size={15} />
              </button>
            )}
            {onDelete && (
              <button type="button" onClick={onDelete}
                className="p-1.5 rounded text-zinc-400 hover:text-red-400 hover:bg-zinc-700/50 transition-colors" title="Delete FAQ">
                <Trash2 size={15} />
              </button>
            )}
          </span>
        )}
        <span
          className="text-lg shrink-0 transition-transform duration-300"
          style={{ color: accent, transform: open ? 'rotate(45deg)' : 'rotate(0deg)' }}
        >
          +
        </span>
      </button>
      {open && (
        <motion.div
          className="px-5 pb-4 pl-[52px]"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          transition={{ duration: 0.3 }}
        >
          <p className="text-sm text-white/60 leading-relaxed whitespace-pre-line break-words">{item.a}</p>
        </motion.div>
      )}
    </motion.div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// HERO-CARDS — About BRIDGE (전면 개편)
// ══════════════════════════════════════════════════════════════════════════════
function HeroCardsLayout({ posts, board, editMode, selectedIds, onToggleSelect, onEdit, onDelete, onMoveUp, onMoveDown, onDndMove, onNewPost }: LayoutProps) {
  const stats = getDynamicStats()
  const statsRef = useRef<HTMLDivElement>(null)
  const [statsVisible, setStatsVisible] = useState(false)

  useEffect(() => {
    const el = statsRef.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setStatsVisible(true) },
      { threshold: 0.3 }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const cv = [
    useAnimatedCounter(stats[0].target, 1500, statsVisible),
    useAnimatedCounter(stats[1].target, 1200, statsVisible),
    useAnimatedCounter(stats[2].target, 2200, statsVisible),
    useAnimatedCounter(stats[3].target, 2500, statsVisible),
  ]

  const aboutPosts = posts.filter(p => !p.title.toLowerCase().includes('faq'))

  return (
    <div>
      {/* ── Section A: Hero ── */}
      <section className="bg-[#f5f5f7] py-20 sm:py-28">
        <motion.div
          className="max-w-[980px] mx-auto px-5 sm:px-8 text-center"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold text-[#1d1d1f] tracking-tight leading-[1.05] mb-5">
            About BRIDGE
          </h1>
          <p className="text-lg sm:text-xl text-[#6e6e73] max-w-[600px] mx-auto leading-relaxed">
            Connecting the world to Korea&apos;s classrooms.
          </p>
        </motion.div>
      </section>

      {/* ── Section B: Company Intro ── */}
      <section className="py-20 sm:py-28">
        <div className="max-w-[680px] mx-auto px-5 sm:px-8">
          <motion.div
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <p className="text-[#6e6e73] text-xs font-semibold uppercase tracking-[0.2em] mb-6">Who We Are</p>
          </motion.div>

          <div className="space-y-6">
            <motion.p
              className="text-[17px] sm:text-[19px] text-[#1d1d1f] leading-[1.7] font-normal"
              variants={fadeInUp} initial="hidden" whileInView="visible" viewport={defaultViewport}
            >
              BRIDGE는 수많은 경험을 가진 리크루터들이 함께 모여 설립한 전문 채용 에이전시입니다.
            </motion.p>
            <motion.p
              className="text-[17px] sm:text-[19px] text-[#424245] leading-[1.7]"
              variants={fadeInUp} initial="hidden" whileInView="visible" viewport={defaultViewport}
            >
              정부기관, 영어마을, 교육센터, 어학원, 유치원, 국제학교, 일반학교, 기업체 등 다양한 교육기관에 맞춤형 인재를 소개합니다.
            </motion.p>
            <motion.p
              className="text-[17px] sm:text-[19px] text-[#424245] leading-[1.7]"
              variants={fadeInUp} initial="hidden" whileInView="visible" viewport={defaultViewport}
            >
              서류부터 실무 배치까지, 채용의 전 과정을 전문적으로 지원합니다.
            </motion.p>
          </div>
        </div>
      </section>

      {/* ── Section C: Why BRIDGE — 4 cards ── */}
      <section className="bg-[#f5f5f7] py-20 sm:py-28">
        <div className="max-w-[980px] mx-auto px-5 sm:px-8">
          <motion.div
            className="text-center mb-14"
            variants={fadeInUp} initial="hidden" whileInView="visible" viewport={defaultViewport}
          >
            <p className="text-[#6e6e73] text-xs font-semibold uppercase tracking-[0.2em] mb-3">Our Strengths</p>
            <h2 className="text-3xl sm:text-4xl font-bold text-[#1d1d1f] tracking-tight">Why BRIDGE?</h2>
          </motion.div>

          <motion.div
            className="grid sm:grid-cols-2 gap-5"
            variants={staggerContainer} initial="hidden" whileInView="visible" viewport={defaultViewport}
          >
            {WHY_BRIDGE.map((card) => (
              <motion.div
                key={card.title}
                className="bg-white rounded-2xl p-7 sm:p-8
                           border border-transparent
                           hover:scale-[1.03] hover:border-[#0071e3]/20 hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)]
                           transition-all duration-300 ease-out cursor-default"
                variants={scaleIn}
              >
                <span className="text-3xl block mb-4">{card.icon}</span>
                <h3 className="text-lg font-semibold text-[#1d1d1f] mb-2">{card.title}</h3>
                <p className="text-sm text-[#6e6e73] leading-relaxed">{card.desc}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── Section D: Stats — animated counters ── */}
      <section className="py-20 sm:py-28" ref={statsRef}>
        <div className="max-w-[980px] mx-auto px-5 sm:px-8">
          <motion.div
            className="grid grid-cols-2 md:grid-cols-4 gap-8"
            variants={staggerContainer} initial="hidden" whileInView="visible" viewport={defaultViewport}
          >
            {stats.map((s, i) => (
              <motion.div key={s.label} className="text-center" variants={scaleIn}>
                <div className="text-4xl sm:text-5xl font-bold text-[#1d1d1f] tabular-nums tracking-tight">
                  {cv[i].toLocaleString('en-US')}{s.suffix}
                </div>
                <div className="text-sm text-[#86868b] mt-2 font-medium">{s.label}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── Posts grid ── */}
      {aboutPosts.length > 0 && (
        <section className="bg-[#f5f5f7] py-20 sm:py-28">
          <div className="max-w-[980px] mx-auto px-5 sm:px-8">
            <motion.div variants={fadeInUp} initial="hidden" whileInView="visible" viewport={defaultViewport}>
              <p className="text-[#6e6e73] text-xs font-semibold uppercase tracking-[0.2em] mb-6">Information</p>
            </motion.div>
            {editMode ? (
              <SortableContainer
                items={aboutPosts.map(p => String(p.id))}
                onDragEnd={(e) => { if (e.over && e.active.id !== e.over.id) onDndMove?.(String(e.active.id), String(e.over.id)) }}
              >
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {aboutPosts.map((p, i) => (
                    <SortableItem key={p.id} id={String(p.id)}>
                      <div className="flex items-center gap-1.5">
                        {onMoveUp && onMoveDown && (
                          <SortHandle
                            onMoveUp={() => onMoveUp(p.id)} onMoveDown={() => onMoveDown(p.id)}
                            isFirst={i === 0} isLast={i === aboutPosts.length - 1}
                          />
                        )}
                        {onToggleSelect && (
                          <AdminCheckbox checked={selectedIds?.has(p.id) ?? false} onChange={() => onToggleSelect(p.id)} />
                        )}
                        <Link
                          href={`/community/${board}/${p.id}`}
                          className="group flex items-center gap-4 bg-white rounded-2xl p-5 border border-transparent hover:border-[#0071e3]/20 hover:shadow-[0_4px_20px_rgba(0,0,0,0.04)] transition-all duration-200 flex-1"
                        >
                          <span className="text-2xl">{HERO_ICONS[i] ?? '📄'}</span>
                          <span className="text-[15px] font-semibold text-[#1d1d1f] group-hover:text-[#0071e3] transition-colors flex-1">
                            {p.title}
                          </span>
                          {onEdit && onDelete && (
                            <InlineAdminActions post={p} board={board} onEdit={onEdit} onDelete={onDelete} />
                          )}
                        </Link>
                      </div>
                    </SortableItem>
                  ))}
                  {onNewPost && (
                    <button type="button" onClick={onNewPost}
                      className="flex items-center justify-center gap-2 w-full bg-zinc-100 rounded-2xl p-5 border-2 border-dashed border-zinc-300 text-zinc-500 hover:border-blue-400 hover:text-blue-600 transition-colors text-sm font-medium">
                      <Plus size={16} /> New Post
                    </button>
                  )}
                </div>
              </SortableContainer>
            ) : (
              <motion.div
                className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4"
                variants={staggerContainer} initial="hidden" whileInView="visible" viewport={defaultViewport}
              >
                {aboutPosts.map((p, i) => (
                  <motion.div key={p.id} variants={scaleIn}>
                    <Link
                      href={`/community/${board}/${p.id}`}
                      className="group flex items-center gap-4 bg-white rounded-2xl p-5 border border-transparent hover:border-[#0071e3]/20 hover:shadow-[0_4px_20px_rgba(0,0,0,0.04)] transition-all duration-200"
                    >
                      <span className="text-2xl">{HERO_ICONS[i] ?? '📄'}</span>
                      <span className="text-[15px] font-semibold text-[#1d1d1f] group-hover:text-[#0071e3] transition-colors flex-1">
                        {p.title}
                      </span>
                    </Link>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </div>
        </section>
      )}

      {/* ── Settling In — Internet & Social ── */}
      <section className="py-20 sm:py-28">
        <div className="max-w-[980px] mx-auto px-5 sm:px-8">
          <motion.div
            className="text-center mb-12"
            variants={fadeInUp} initial="hidden" whileInView="visible" viewport={defaultViewport}
          >
            <p className="text-[#6e6e73] text-xs font-semibold uppercase tracking-[0.2em] mb-3">Settling In</p>
            <h2 className="text-3xl sm:text-4xl font-bold text-[#1d1d1f] tracking-tight mb-3">
              Life in Korea
            </h2>
            <p className="text-[15px] text-[#86868b] max-w-md mx-auto">
              We help you get connected from day one.
            </p>
          </motion.div>

          {/* Internet providers */}
          <motion.div
            className="grid grid-cols-3 gap-2 sm:gap-4 max-w-[520px] mx-auto mb-16"
            variants={staggerContainer} initial="hidden" whileInView="visible" viewport={defaultViewport}
          >
            {[
              { name: 'KT', sub: 'olleh', color: '#e4002b' },
              { name: 'SK', sub: 'T world', color: '#e4002b' },
              { name: 'U+', sub: 'LG Uplus', color: '#e6007e' },
            ].map((p) => (
              <motion.div key={p.name} variants={scaleIn}
                className="bg-white rounded-2xl p-6 text-center border border-[#e5e5ea]
                           hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)] hover:scale-[1.04]
                           transition-all duration-300 cursor-default"
              >
                <div className="w-14 h-14 mx-auto mb-3 rounded-2xl flex items-center justify-center"
                  style={{ background: `${p.color}0D` }}>
                  <span className="font-black text-lg" style={{ color: p.color }}>{p.name}</span>
                </div>
                <p className="text-xs font-medium text-[#86868b]">{p.sub}</p>
              </motion.div>
            ))}
          </motion.div>

          {/* Social links */}
          <motion.div
            className="text-center"
            variants={fadeInUp} initial="hidden" whileInView="visible" viewport={defaultViewport}
          >
            <p className="text-xs font-semibold text-[#86868b] uppercase tracking-[0.15em] mb-5">Follow &amp; Connect</p>
            <div className="flex items-center justify-center gap-3">
              {[
                { href: 'https://youtube.com/@bridgejobkr', label: 'YouTube', hoverBg: '#ff0000', icon: 'M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z' },
                { href: 'https://facebook.com/bridgejobkr', label: 'Facebook', hoverBg: '#1877f2', icon: 'M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z' },
                { href: 'https://threads.net/@bridgejobkr', label: 'Threads', hoverBg: '#000000', icon: 'M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.59 12c.025 3.083.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.96-.065-1.182.408-2.26 1.332-3.031.88-.735 2.088-1.18 3.59-1.323.98-.094 1.975-.059 2.96.104.026-.82-.065-1.555-.267-2.186-.277-.865-.775-1.452-1.478-1.744-.758-.315-1.72-.327-2.86-.037l-.536-1.953c1.54-.39 2.946-.357 4.07.096 1.07.431 1.856 1.268 2.28 2.421.294.8.44 1.74.44 2.818l.002.348c.986.56 1.77 1.334 2.262 2.36.722 1.507.842 4.065-1.16 6.028-1.79 1.756-4.016 2.548-7.21 2.572zm2.032-8.081c-.94-.176-1.89-.218-2.828-.126-1.14.109-2.025.44-2.633.983-.55.49-.78 1.087-.648 1.684.166.752.86 1.336 1.885 1.59.423.104.88.154 1.347.154.609 0 1.235-.09 1.765-.266.89-.294 1.547-.834 1.96-1.604.37-.687.564-1.544.59-2.55a8.658 8.658 0 0 0-1.438.135z' },
                { href: 'https://reddit.com/r/bridgejobkr', label: 'Reddit', hoverBg: '#ff4500', icon: 'M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 .029-.463.33.33 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z' },
              ].map((s) => (
                <a key={s.label} href={s.href} target="_blank" rel="noopener noreferrer" aria-label={s.label}
                  className="group w-11 h-11 rounded-full bg-[#f5f5f7] border border-[#e5e5ea]
                             flex items-center justify-center
                             hover:border-transparent hover:shadow-md
                             transition-all duration-300"
                  style={{ ['--hover-bg' as string]: s.hoverBg }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = s.hoverBg; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = '#f5f5f7'; }}
                >
                  <svg className="w-[18px] h-[18px] text-[#86868b] group-hover:text-white transition-colors" viewBox="0 0 24 24" fill="currentColor">
                    <path d={s.icon} />
                  </svg>
                </a>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Contact + Registration ── */}
      <section className="bg-[#f5f5f7] py-20 sm:py-28">
        <div className="max-w-[680px] mx-auto px-5 sm:px-8 text-center">
          <motion.div variants={fadeInUp} initial="hidden" whileInView="visible" viewport={defaultViewport}>
            <p className="text-[#6e6e73] text-xs font-semibold uppercase tracking-[0.2em] mb-3">Contact</p>
            <h2 className="text-2xl sm:text-3xl font-bold text-[#1d1d1f] tracking-tight mb-4">
              Get in Touch
            </h2>
            <p className="text-[15px] text-[#6e6e73] leading-relaxed mb-8">
              채용 상담이나 서비스에 대한 문의는 아래 채널을 이용해 주세요.
            </p>
            <a
              href="mailto:bridgejobkr@gmail.com"
              className="inline-flex items-center gap-2 text-[#0071e3] text-base font-semibold hover:underline"
            >
              bridgejobkr@gmail.com
            </a>
          </motion.div>

          <motion.div
            className="mt-16 pt-8 border-t border-[#e5e5e5]"
            variants={fadeInUp} initial="hidden" whileInView="visible" viewport={defaultViewport}
          >
            <p className="text-xs text-[#86868b] leading-relaxed">
              BRIDGE Recruitment &middot; 사업자등록번호 000-00-00000
            </p>
          </motion.div>
        </div>
      </section>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// CARD-GRID — Tips
// ══════════════════════════════════════════════════════════════════════════════
function CardGridLayout({ config, posts, board, editMode, selectedIds, onToggleSelect, onEdit, onDelete, onMoveUp, onMoveDown, onDndMove, onNewPost }: LayoutProps) {
  const cardContent = (p: Post, i: number) => (
    <Link href={`/community/${board}/${p.id}`} className="tips-card group block relative">
      <div className="h-1 -mx-5 -mt-5 mb-5 rounded-t-[20px]" style={{ background: TIPS_COLORS[i % TIPS_COLORS.length] }} />
      <div className="text-3xl mb-3">{TIPS_EMOJIS[i % TIPS_EMOJIS.length]}</div>
      <h3 className="text-[17px] font-bold text-[#1d1d1f] mb-2 group-hover:text-[#0071e3] transition-colors">{p.title}</h3>
      <p className="text-sm text-[#6e6e73] line-clamp-3 mb-4">{stripMd(p.preview)}</p>
      <span className="text-sm font-medium text-[#0071e3]">Read more &rarr;</span>
      {editMode && (
        <div className="flex items-center gap-1 mt-3 pt-3 border-t border-zinc-200"
          onClick={(e) => { e.preventDefault(); e.stopPropagation() }}>
          {onToggleSelect && (
            <AdminCheckbox checked={selectedIds?.has(p.id) ?? false} onChange={() => onToggleSelect(p.id)} />
          )}
          {onMoveUp && onMoveDown && (
            <SortHandle
              onMoveUp={() => onMoveUp(p.id)} onMoveDown={() => onMoveDown(p.id)}
              isFirst={i === 0} isLast={i === posts.length - 1}
            />
          )}
          <span className="flex-1" />
          {onEdit && onDelete && (
            <InlineAdminActions post={p} board={board} onEdit={onEdit} onDelete={onDelete} />
          )}
        </div>
      )}
    </Link>
  )

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      <BoardHeader config={config} board={board} editMode={editMode} onNewPost={onNewPost} />
      {editMode ? (
        <SortableContainer
          items={posts.map(p => String(p.id))}
          onDragEnd={(e) => { if (e.over && e.active.id !== e.over.id) onDndMove?.(String(e.active.id), String(e.over.id)) }}
        >
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {posts.map((p, i) => (
              <SortableItem key={p.id} id={String(p.id)}>
                {cardContent(p, i)}
              </SortableItem>
            ))}
          </div>
        </SortableContainer>
      ) : (
        <motion.div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6" variants={staggerContainer} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.1 }}>
          {posts.map((p, i) => (
            <motion.div key={p.id} variants={fadeInUp}>
              {cardContent(p, i)}
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// PHOTO-CARDS — Korea
// ══════════════════════════════════════════════════════════════════════════════
function PhotoCardsLayout({ config, posts, board, editMode, selectedIds, onToggleSelect, onEdit, onDelete, onMoveUp, onMoveDown, onDndMove, onNewPost }: LayoutProps) {
  const photoCard = (p: Post, i: number) => {
    const imgKey = getPostImageKey(p.title)
    return (
      <Link href={`/community/${board}/${p.id}`}
        className={`korea-card group flex-col sm:flex-row ${editMode ? 'flex-1' : ''}`}
      >
        <div className="w-full sm:w-60 h-40 sm:h-44 shrink-0 overflow-hidden">
          <img src={POST_IMAGES[imgKey]} alt={p.title} className="korea-img w-full h-full object-cover" />
        </div>
        <div className="flex-1 p-4 sm:p-5 flex flex-col justify-center">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-bold text-[#1d1d1f] mb-2 group-hover:text-[#0071e3] transition-colors flex-1">{p.title}</h3>
            {editMode && onEdit && onDelete && (
              <InlineAdminActions post={p} board={board} onEdit={onEdit} onDelete={onDelete} />
            )}
          </div>
          <p className="text-sm text-[#6e6e73] line-clamp-2 mb-2">{stripMd(p.preview, 150)}</p>
          {KOREA_MAP_LINKS[imgKey] && (
            <a href={KOREA_MAP_LINKS[imgKey]} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-[#0071e3] hover:underline mt-1"
              onClick={(e) => e.stopPropagation()}>
              View on Map
            </a>
          )}
        </div>
      </Link>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      <BoardHeader config={config} board={board} editMode={editMode} onNewPost={onNewPost} />
      {editMode ? (
        <SortableContainer
          items={posts.map(p => String(p.id))}
          onDragEnd={(e) => { if (e.over && e.active.id !== e.over.id) onDndMove?.(String(e.active.id), String(e.over.id)) }}
        >
          <div className="space-y-5">
            {posts.map((p, i) => (
              <SortableItem key={p.id} id={String(p.id)}>
                <div className="flex items-center gap-1.5">
                  {onMoveUp && onMoveDown && (
                    <SortHandle
                      onMoveUp={() => onMoveUp(p.id)} onMoveDown={() => onMoveDown(p.id)}
                      isFirst={i === 0} isLast={i === posts.length - 1}
                    />
                  )}
                  {onToggleSelect && (
                    <AdminCheckbox checked={selectedIds?.has(p.id) ?? false} onChange={() => onToggleSelect(p.id)} />
                  )}
                  {photoCard(p, i)}
                </div>
              </SortableItem>
            ))}
          </div>
        </SortableContainer>
      ) : (
        <div className="space-y-5">
          {posts.map((p, i) => {
            const variant = i % 2 === 0 ? slideInLeft : slideInRight
            return (
              <motion.div key={p.id} variants={variant} initial="hidden" whileInView="visible" viewport={defaultViewport}>
                {photoCard(p, i)}
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// TESTIMONIALS — 팝업 카드 방식
// ══════════════════════════════════════════════════════════════════════════════

interface Testimonial {
  id: number
  name: string
  country: string
  photo_url: string | null
  rating: number
  review_text: string
  sort_order: number
  created_at: string
}

const PER_PAGE = 5

function TestimonialLayout({ config, board, editMode, onNewPost }: LayoutProps) {
  const [testimonials, setTestimonials] = useState<Testimonial[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [tLoading, setTLoading] = useState(true)
  const [selectedReview, setSelectedReview] = useState<Testimonial | null>(null)

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  useEffect(() => {
    setTLoading(true)
    const offset = (page - 1) * PER_PAGE
    fetch(`${API}/api/testimonials?limit=${PER_PAGE}&offset=${offset}`)
      .then((r) => r.json())
      .then((j) => {
        if (j.success) {
          setTestimonials(j.data.testimonials)
          setTotal(j.data.total)
        }
      })
      .finally(() => setTLoading(false))
  }, [page])

  const goPage = (p: number) => {
    if (p >= 1 && p <= totalPages) {
      setPage(p)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  const pageNumbers = (() => {
    const pages: number[] = []
    const maxVisible = 5
    let start = Math.max(1, page - Math.floor(maxVisible / 2))
    const end = Math.min(totalPages, start + maxVisible - 1)
    start = Math.max(1, end - maxVisible + 1)
    for (let i = start; i <= end; i++) pages.push(i)
    return pages
  })()

  return (
    <div>
      {/* ── Hero header ── */}
      <section className="bg-gradient-to-b from-[#f5f5f7] to-white py-16 sm:py-20">
        <div className="max-w-[980px] mx-auto px-5 sm:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <p className="text-[#0071e3] text-sm font-semibold uppercase tracking-[0.2em] mb-3">Testimonials</p>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-[#1d1d1f] tracking-tight mb-4">
              Hear from Our Teachers
            </h1>
            <p className="text-[#86868b] text-base sm:text-lg max-w-[500px] mx-auto">
              Real stories from teachers who found their place in Korea through BRIDGE.
            </p>
            {editMode && onNewPost && (
              <button type="button" onClick={onNewPost}
                className="mt-6 inline-flex items-center gap-1.5 px-4 py-2 bg-[#0071e3] text-white text-sm font-medium rounded-full hover:bg-[#0077ED] transition-colors">
                <Plus size={14} /> New Post
              </button>
            )}
          </motion.div>
        </div>
      </section>

      {/* ── Testimonial list ── */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        {tLoading ? (
          <div className="space-y-4">
            {[...Array(PER_PAGE)].map((_, i) => (
              <div key={i} className="flex gap-4 animate-pulse">
                <div className="w-[100px] h-[100px] rounded-xl bg-[#f0f0f0] shrink-0" />
                <div className="flex-1 space-y-3 py-2">
                  <div className="h-4 bg-[#f0f0f0] rounded w-1/3" />
                  <div className="h-3 bg-[#f0f0f0] rounded w-full" />
                  <div className="h-3 bg-[#f0f0f0] rounded w-4/5" />
                </div>
              </div>
            ))}
          </div>
        ) : testimonials.length === 0 ? (
          <p className="text-[#86868b] text-center py-16">No reviews yet.</p>
        ) : (
          <motion.div
            className="space-y-5"
            variants={staggerContainer} initial="hidden" animate="visible"
          >
            {testimonials.map((t) => (
              <motion.div key={t.id} variants={fadeInUp}>
                <button
                  type="button"
                  onClick={() => setSelectedReview(t)}
                  className="w-full flex gap-4 sm:gap-5 p-4 sm:p-5 bg-white rounded-2xl border border-[#e5e5ea] text-left group
                             hover:shadow-[0_4px_20px_rgba(0,0,0,0.06)] hover:border-[#d1d1d6] hover:-translate-y-0.5
                             transition-all duration-300 cursor-pointer"
                >
                  {/* Left: Avatar */}
                  <div className="shrink-0">
                    <AvatarPlaceholder name={t.name} photoUrl={t.photo_url} size={100} />
                  </div>

                  {/* Right: Info */}
                  <div className="flex-1 min-w-0 py-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold text-[16px] text-[#1d1d1f]">{t.name}</span>
                      <span className="text-sm text-[#86868b]">({t.country})</span>
                    </div>
                    <div className="flex gap-0.5 mb-2">
                      {Array.from({ length: 5 }).map((_, s) => (
                        <svg key={s} className="w-3.5 h-3.5" viewBox="0 0 20 20" fill={s < t.rating ? '#facc15' : '#e5e5ea'}>
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                      ))}
                    </div>
                    <p className="text-sm text-[#424245] leading-relaxed line-clamp-2">{t.review_text}</p>
                    <span className="text-xs text-[#0071e3] font-medium mt-1.5 block group-hover:underline">Read more</span>
                  </div>
                </button>
              </motion.div>
            ))}
          </motion.div>
        )}

        {/* ── Pagination ── */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-1.5 mt-10">
            <button
              type="button"
              onClick={() => goPage(1)}
              disabled={page === 1}
              className="px-2.5 py-1.5 text-sm rounded-lg text-[#86868b] hover:bg-[#f5f5f7] disabled:opacity-30 disabled:cursor-default transition-colors"
            >
              &laquo;
            </button>
            <button
              type="button"
              onClick={() => goPage(page - 1)}
              disabled={page === 1}
              className="px-2.5 py-1.5 text-sm rounded-lg text-[#86868b] hover:bg-[#f5f5f7] disabled:opacity-30 disabled:cursor-default transition-colors"
            >
              &lsaquo;
            </button>
            {pageNumbers.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => goPage(p)}
                className={`w-9 h-9 text-sm rounded-lg font-medium transition-colors ${
                  p === page
                    ? 'bg-[#0071e3] text-white'
                    : 'text-[#424245] hover:bg-[#f5f5f7]'
                }`}
              >
                {p}
              </button>
            ))}
            <button
              type="button"
              onClick={() => goPage(page + 1)}
              disabled={page === totalPages}
              className="px-2.5 py-1.5 text-sm rounded-lg text-[#86868b] hover:bg-[#f5f5f7] disabled:opacity-30 disabled:cursor-default transition-colors"
            >
              &rsaquo;
            </button>
            <button
              type="button"
              onClick={() => goPage(totalPages)}
              disabled={page === totalPages}
              className="px-2.5 py-1.5 text-sm rounded-lg text-[#86868b] hover:bg-[#f5f5f7] disabled:opacity-30 disabled:cursor-default transition-colors"
            >
              &raquo;
            </button>
          </div>
        )}
      </section>

      {/* ── Popup modal ── */}
      <AnimatePresence>
        {selectedReview && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setSelectedReview(null)} />
            <motion.div
              className="relative bg-white rounded-2xl shadow-2xl max-w-lg w-full p-8 sm:p-10"
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              transition={{ duration: 0.25, ease: [0.25, 0.1, 0.25, 1] }}
            >
              <button
                type="button"
                onClick={() => setSelectedReview(null)}
                className="absolute top-4 right-4 w-8 h-8 rounded-full bg-[#f5f5f7] flex items-center justify-center text-[#86868b] hover:bg-[#e5e5ea] hover:text-[#1d1d1f] transition-colors"
              >
                &times;
              </button>

              <div className="flex items-center gap-4 mb-6">
                <AvatarPlaceholder name={selectedReview.name} photoUrl={selectedReview.photo_url} size={72} />
                <div>
                  <div className="font-bold text-[#1d1d1f] text-lg">{selectedReview.name}</div>
                  <div className="text-sm text-[#86868b]">{selectedReview.country}</div>
                </div>
              </div>

              <div className="flex gap-1 mb-5">
                {Array.from({ length: 5 }).map((_, s) => (
                  <svg key={s} className="w-4 h-4" viewBox="0 0 20 20" fill={s < selectedReview.rating ? '#facc15' : '#e5e5ea'}>
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </div>

              <div className="border-t border-[#f5f5f7] pt-5">
                <span className="text-3xl text-[#d1d1d6] leading-none font-serif">&ldquo;</span>
                <p className="text-[15px] text-[#424245] leading-[1.8] mt-2">{selectedReview.review_text}</p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
