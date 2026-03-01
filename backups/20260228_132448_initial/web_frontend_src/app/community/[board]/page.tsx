'use client'

/**
 * /community/[board] — Dynamic board page with layout-specific scroll animations
 * Simplified: shared BoardHeader + stripMarkdown utility
 */

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { getBoardConfig, type BoardConfig } from '@/lib/boards'
import {
  fadeInUp,
  staggerContainer,
  scaleIn,
  slideInLeft,
  slideInRight,
  defaultViewport,
} from '@/lib/animations'

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface Post {
  id: number
  title: string
  preview: string
  author_hash: string
  pinned: number
  views: number
  created_at: string
}

interface LayoutProps {
  config: BoardConfig
  posts: Post[]
  total: number
  board: string
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

// ── Shared Board Header ──
function BoardHeader({ config }: { config: BoardConfig }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <h1 className="text-3xl font-bold text-[#1d1d1f] mb-2">{config.label}</h1>
      <p className="text-[#86868b] text-sm mb-8">{config.description}</p>
      {config.notice && (
        <div className="bg-[#f5f5f7] rounded-xl px-5 py-4 text-sm text-[#6e6e73] -mt-4 mb-8">
          {config.notice}
        </div>
      )}
    </motion.div>
  )
}

// ── Constants ──
const KOREA_IMAGES: Record<string, string> = {
  Seoul: 'https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?w=480&h=320&fit=crop',
  Gyeonggi: 'https://images.unsplash.com/photo-1578637387939-43c525550085?w=480&h=320&fit=crop',
  Incheon: 'https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?w=480&h=320&fit=crop',
  Busan: 'https://images.unsplash.com/photo-1590559899731-a382839e5549?w=480&h=320&fit=crop',
  Daegu: 'https://images.unsplash.com/photo-1517154421773-0529f29ea451?w=480&h=320&fit=crop',
}
const KOREA_MAP_LINKS: Record<string, string> = {
  Seoul: 'https://maps.google.com/?q=Seoul,Korea',
  Gyeonggi: 'https://maps.google.com/?q=Gyeonggi-do,Korea',
  Incheon: 'https://maps.google.com/?q=Incheon,Korea',
  Busan: 'https://maps.google.com/?q=Busan,Korea',
  Daegu: 'https://maps.google.com/?q=Daegu,Korea',
}
const TIPS_COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1']
const TIPS_EMOJIS = ['📸', '🎓', '🎤']
const HERO_ICONS = ['🏢', '📋', '🆕', '📝', '💰']
const AVATAR_COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1']
const CITY_KEYS = Object.keys(KOREA_IMAGES)

// ══════════════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ══════════════════════════════════════════════════════════════════════════════
export default function BoardPage() {
  const { board } = useParams<{ board: string }>()
  const config = getBoardConfig(board)

  const [posts, setPosts] = useState<Post[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!config) return
    fetch(`${API}/api/community/${board}?limit=50`)
      .then((r) => r.json())
      .then((j) => { if (j.success) { setPosts(j.data.posts); setTotal(j.data.total) } })
      .finally(() => setLoading(false))
  }, [board, config])

  if (!config) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center">
        <p className="text-[#86868b] text-lg">Board not found.</p>
        <Link href="/community" className="text-[#0071e3] text-sm mt-2 block">← Back to Community</Link>
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

  const props: LayoutProps = { config, posts, total, board }

  switch (config.layout) {
    case 'list':         return <ListLayout {...props} />
    case 'hero-cards':   return <HeroCardsLayout {...props} />
    case 'card-grid':    return <CardGridLayout {...props} />
    case 'photo-cards':  return <PhotoCardsLayout {...props} />
    case 'testimonial':
    case 'testimonials': return <TestimonialLayout {...props} />
    default:             return <ListLayout {...props} />
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// LIST — Visa / Support / 업무지원
// ══════════════════════════════════════════════════════════════════════════════
function ListLayout({ config, posts, board }: LayoutProps) {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
      <BoardHeader config={config} />
      {posts.length === 0 ? (
        <p className="text-[#86868b] text-center py-16">No posts yet.</p>
      ) : (
        <motion.div variants={staggerContainer} initial="hidden" animate="visible">
          {posts.map((p) => (
            <motion.div key={p.id} variants={fadeInUp}>
              <Link
                href={`/community/${board}/${p.id}`}
                className="board-list-item group"
                style={{ '--accent-color': accentHex(config.accentColor) } as React.CSSProperties}
              >
                <span className="text-[15px] text-[#1d1d1f] font-medium group-hover:text-inherit">{p.title}</span>
                <span className="arrow">→</span>
              </Link>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// HERO-CARDS — About
// ══════════════════════════════════════════════════════════════════════════════
function HeroCardsLayout({ config, posts, board }: LayoutProps) {
  const stats = [
    { label: 'Years', value: '10+' },
    { label: 'Teachers', value: '5,000+' },
    { label: 'Workplaces', value: '2,000+' },
    { label: 'Countries', value: '7' },
  ]

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      {/* Hero */}
      <motion.div className="text-center mb-16" initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}>
        <h1 className="text-6xl font-black text-[#1d1d1f] mb-4">BRIDGE</h1>
        <p className="text-lg text-[#6e6e73] max-w-xl mx-auto leading-relaxed">
          대한민국 원어민 영어강사 채용 전문 에이전시.
          학교와 강사를 연결하는 가장 신뢰할 수 있는 파트너.
        </p>
      </motion.div>

      {/* Stats */}
      <motion.div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-16" variants={staggerContainer} initial="hidden" whileInView="visible" viewport={defaultViewport}>
        {stats.map((s) => (
          <motion.div key={s.label} className="text-center" variants={scaleIn}>
            <div className="text-3xl font-bold text-[#1d1d1f]">{s.value}</div>
            <div className="text-sm text-[#86868b] mt-1">{s.label}</div>
          </motion.div>
        ))}
      </motion.div>

      {/* Cards */}
      <motion.div variants={fadeInUp} initial="hidden" whileInView="visible" viewport={defaultViewport}>
        <h2 className="text-sm font-semibold text-[#86868b] uppercase tracking-wider mb-6">Information</h2>
      </motion.div>
      <motion.div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4" variants={staggerContainer} initial="hidden" whileInView="visible" viewport={defaultViewport}>
        {posts.map((p, i) => (
          <motion.div key={p.id} variants={scaleIn}>
            <Link href={`/community/${board}/${p.id}`} className="card group flex items-center gap-4 !rounded-2xl">
              <span className="text-2xl">{HERO_ICONS[i] ?? '📄'}</span>
              <span className="text-[15px] font-semibold text-[#1d1d1f] group-hover:text-[#0071e3] transition-colors">{p.title}</span>
            </Link>
          </motion.div>
        ))}
      </motion.div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// CARD-GRID — Tips
// ══════════════════════════════════════════════════════════════════════════════
function CardGridLayout({ config, posts, board }: LayoutProps) {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      <BoardHeader config={config} />
      <motion.div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6" variants={staggerContainer} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.1 }}>
        {posts.map((p, i) => (
          <motion.div key={p.id} variants={fadeInUp}>
            <Link href={`/community/${board}/${p.id}`} className="tips-card group block">
              <div className="h-1 -mx-5 -mt-5 mb-5 rounded-t-[20px]" style={{ background: TIPS_COLORS[i % TIPS_COLORS.length] }} />
              <div className="text-3xl mb-3">{TIPS_EMOJIS[i % TIPS_EMOJIS.length]}</div>
              <h3 className="text-[17px] font-bold text-[#1d1d1f] mb-2 group-hover:text-[#0071e3] transition-colors">{p.title}</h3>
              <p className="text-sm text-[#6e6e73] line-clamp-3 mb-4">{stripMd(p.preview)}</p>
              <span className="text-sm font-medium text-[#0071e3]">Read more →</span>
            </Link>
          </motion.div>
        ))}
      </motion.div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// PHOTO-CARDS — Korea
// ══════════════════════════════════════════════════════════════════════════════
function PhotoCardsLayout({ config, posts, board }: LayoutProps) {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      <BoardHeader config={config} />
      <div className="space-y-5">
        {posts.map((p, i) => {
          const city = CITY_KEYS[i % CITY_KEYS.length]
          const variant = i % 2 === 0 ? slideInLeft : slideInRight

          return (
            <motion.div key={p.id} variants={variant} initial="hidden" whileInView="visible" viewport={defaultViewport}>
              <Link href={`/community/${board}/${p.id}`} className="korea-card group">
                <div className="w-60 h-44 shrink-0 overflow-hidden">
                  <img src={KOREA_IMAGES[city]} alt={p.title} className="korea-img w-full h-full object-cover" />
                </div>
                <div className="flex-1 p-5 flex flex-col justify-center">
                  <h3 className="text-lg font-bold text-[#1d1d1f] mb-2 group-hover:text-[#0071e3] transition-colors">{p.title}</h3>
                  <p className="text-sm text-[#6e6e73] line-clamp-2 mb-2">{stripMd(p.preview, 150)}</p>
                  {KOREA_MAP_LINKS[city] && (
                    <a href={KOREA_MAP_LINKS[city]} target="_blank" rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-[#0071e3] hover:underline mt-1"
                      onClick={(e) => e.stopPropagation()}>
                      <span>📍</span> View on Map
                    </a>
                  )}
                </div>
              </Link>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// TESTIMONIALS
// ══════════════════════════════════════════════════════════════════════════════
function TestimonialLayout({ config, posts, board }: LayoutProps) {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      <BoardHeader config={config} />
      <motion.div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6" variants={staggerContainer} initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.1 }}>
        {posts.map((p, i) => {
          const name = p.title.split('—')[0]?.trim() ?? p.title
          return (
            <motion.div key={p.id} variants={fadeInUp}>
              <Link href={`/community/${board}/${p.id}`} className="testimonial-card group block">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-[52px] h-[52px] rounded-full flex items-center justify-center text-white text-lg font-bold shrink-0"
                    style={{ background: AVATAR_COLORS[i % AVATAR_COLORS.length] }}>
                    {name.charAt(0)}
                  </div>
                  <div>
                    <div className="font-semibold text-[#1d1d1f] text-sm">{name}</div>
                    <div className="text-xs text-[#86868b]">English Teacher · BRIDGE</div>
                  </div>
                </div>
                <div className="mb-4">
                  <span className="text-3xl text-[#d1d1d6] leading-none">&ldquo;</span>
                  <p className="text-sm text-[#424245] italic line-clamp-4 mt-1">{stripMd(p.preview, 150)}</p>
                </div>
                <span className="text-sm font-medium text-[#0071e3] group-hover:underline">Read full story →</span>
              </Link>
            </motion.div>
          )
        })}
      </motion.div>
    </div>
  )
}
