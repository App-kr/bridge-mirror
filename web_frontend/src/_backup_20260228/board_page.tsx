'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { getBoardConfig, type BoardConfig } from '@/lib/boards'

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

function timeAgo(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

// ── Unsplash city images for Korea board ──
const KOREA_IMAGES: Record<string, string> = {
  'Seoul': 'https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?w=480&h=320&fit=crop',
  'Gyeonggi': 'https://images.unsplash.com/photo-1578637387939-43c525550085?w=480&h=320&fit=crop',
  'Incheon': 'https://images.unsplash.com/photo-1570077188670-e3a8d69ac5ff?w=480&h=320&fit=crop',
  'Busan': 'https://images.unsplash.com/photo-1590559899731-a382839e5549?w=480&h=320&fit=crop',
  'Daegu': 'https://images.unsplash.com/photo-1517154421773-0529f29ea451?w=480&h=320&fit=crop',
}

// ── Tips color bars ──
const TIPS_COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1']
const TIPS_EMOJIS = ['📸', '🎓', '🎤']

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
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-14 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  // Render based on layout type
  switch (config.layout) {
    case 'list':       return <ListLayout config={config} posts={posts} total={total} board={board} />
    case 'hero-cards': return <HeroCardsLayout config={config} posts={posts} total={total} board={board} />
    case 'card-grid':  return <CardGridLayout config={config} posts={posts} total={total} board={board} />
    case 'photo-cards': return <PhotoCardsLayout config={config} posts={posts} total={total} board={board} />
    case 'testimonial': return <TestimonialLayout config={config} posts={posts} total={total} board={board} />
    default:           return <ListLayout config={config} posts={posts} total={total} board={board} />
  }
}

// ── Layout Props ──
interface LayoutProps {
  config: BoardConfig
  posts: Post[]
  total: number
  board: string
}

// ══════════════════════════════════════════════════════════════════════════════
// LIST LAYOUT — Visa / Support / 업무지원
// 제목만 표시, 22px 행간, 우측 → 화살표, hover 시 좌 8px 슬라이드
// ══════════════════════════════════════════════════════════════════════════════
function ListLayout({ config, posts, board }: LayoutProps) {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
      <h1 className="text-3xl font-bold text-[#1d1d1f] mb-2">{config.label}</h1>
      <p className="text-[#86868b] text-sm mb-8">{config.description}</p>

      {config.notice && (
        <div className="bg-[#f5f5f7] rounded-xl px-5 py-4 text-sm text-[#6e6e73] mb-8">
          {config.notice}
        </div>
      )}

      {posts.length === 0 ? (
        <p className="text-[#86868b] text-center py-16">No posts yet.</p>
      ) : (
        <div>
          {posts.map((p) => (
            <Link
              key={p.id}
              href={`/community/${board}/${p.id}`}
              className="board-list-item group"
              style={{ '--accent-color': config.accentColor.includes('emerald') ? '#34d399'
                : config.accentColor.includes('blue') ? '#0071e3'
                : config.accentColor.includes('orange') ? '#f97316' : '#0071e3' } as React.CSSProperties}
            >
              <span className="text-[15px] text-[#1d1d1f] font-medium group-hover:text-inherit">
                {p.title}
              </span>
              <span className="arrow">→</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// HERO-CARDS LAYOUT — About
// 대형 타이틀 + 소개 텍스트 + 통계 + 카드 버튼
// ══════════════════════════════════════════════════════════════════════════════
function HeroCardsLayout({ config, posts, board }: LayoutProps) {
  const stats = [
    { label: 'Years', value: '10+' },
    { label: 'Teachers', value: '5,000+' },
    { label: 'Workplaces', value: '2,000+' },
    { label: 'Countries', value: '7' },
  ]
  const icons = ['🏢', '📋', '🆕', '📝', '💰']

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      {/* Hero */}
      <div className="text-center mb-16">
        <h1 className="text-6xl font-black text-[#1d1d1f] mb-4">BRIDGE</h1>
        <p className="text-lg text-[#6e6e73] max-w-xl mx-auto leading-relaxed">
          대한민국 원어민 영어강사 채용 전문 에이전시.
          학교와 강사를 연결하는 가장 신뢰할 수 있는 파트너.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-16">
        {stats.map((s) => (
          <div key={s.label} className="text-center">
            <div className="text-3xl font-bold text-[#1d1d1f]">{s.value}</div>
            <div className="text-sm text-[#86868b] mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Information Cards */}
      <h2 className="text-sm font-semibold text-[#86868b] uppercase tracking-wider mb-6">Information</h2>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {posts.map((p, i) => (
          <Link
            key={p.id}
            href={`/community/${board}/${p.id}`}
            className="card group flex items-center gap-4 !rounded-2xl"
          >
            <span className="text-2xl">{icons[i] ?? '📄'}</span>
            <span className="text-[15px] font-semibold text-[#1d1d1f] group-hover:text-[#0071e3] transition-colors">
              {p.title}
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// CARD-GRID LAYOUT — Tips
// 3열 그리드, 상단 4px 컬러바, 이모지 + 제목 + 미리보기 + Read more
// ══════════════════════════════════════════════════════════════════════════════
function CardGridLayout({ config, posts, board }: LayoutProps) {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      <h1 className="text-3xl font-bold text-[#1d1d1f] mb-2">{config.label}</h1>
      <p className="text-[#86868b] text-sm mb-8">{config.description}</p>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {posts.map((p, i) => (
          <Link key={p.id} href={`/community/${board}/${p.id}`} className="tips-card group">
            {/* Color bar */}
            <div className="h-1 -mx-5 -mt-5 mb-5 rounded-t-[20px]"
              style={{ background: TIPS_COLORS[i % TIPS_COLORS.length] }} />
            <div className="text-3xl mb-3">{TIPS_EMOJIS[i % TIPS_EMOJIS.length]}</div>
            <h3 className="text-[17px] font-bold text-[#1d1d1f] mb-2 group-hover:text-[#0071e3] transition-colors">
              {p.title}
            </h3>
            <p className="text-sm text-[#6e6e73] line-clamp-3 mb-4">
              {p.preview?.replace(/#+\s/g, '').replace(/\*+/g, '').slice(0, 120)}
            </p>
            <span className="text-sm font-medium text-[#0071e3]">Read more →</span>
          </Link>
        ))}
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// PHOTO-CARDS LAYOUT — Korea
// 가로 포토카드, 좌측 240px 이미지, 우측 제목+설명
// ══════════════════════════════════════════════════════════════════════════════
function PhotoCardsLayout({ config, posts, board }: LayoutProps) {
  const cityKeys = Object.keys(KOREA_IMAGES)

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      <h1 className="text-3xl font-bold text-[#1d1d1f] mb-2">{config.label}</h1>
      <p className="text-[#86868b] text-sm mb-8">{config.description}</p>

      <div className="space-y-5">
        {posts.map((p, i) => {
          const imgKey = cityKeys[i % cityKeys.length]
          const imgUrl = KOREA_IMAGES[imgKey]
          return (
            <Link key={p.id} href={`/community/${board}/${p.id}`} className="korea-card group">
              <div className="w-60 h-44 shrink-0 overflow-hidden">
                <img src={imgUrl} alt={p.title}
                  className="korea-img w-full h-full object-cover" />
              </div>
              <div className="flex-1 p-5 flex flex-col justify-center">
                <h3 className="text-lg font-bold text-[#1d1d1f] mb-2 group-hover:text-[#0071e3] transition-colors">
                  {p.title}
                </h3>
                <p className="text-sm text-[#6e6e73] line-clamp-2">
                  {p.preview?.replace(/#+\s/g, '').replace(/\*+/g, '').slice(0, 150)}
                </p>
              </div>
            </Link>
          )
        })}
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// TESTIMONIAL LAYOUT
// 3열 아바타 인용 카드
// ══════════════════════════════════════════════════════════════════════════════
function TestimonialLayout({ config, posts, board }: LayoutProps) {
  const avatarColors = ['#FF6B6B', '#4ECDC4', '#45B7D1']

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      <h1 className="text-3xl font-bold text-[#1d1d1f] mb-2">{config.label}</h1>
      <p className="text-[#86868b] text-sm mb-8">{config.description}</p>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {posts.map((p, i) => {
          // Extract name from title (e.g. "Sarah J. — USA → Yongin")
          const name = p.title.split('—')[0]?.trim() ?? p.title
          return (
            <Link key={p.id} href={`/community/${board}/${p.id}`} className="testimonial-card group">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-[52px] h-[52px] rounded-full flex items-center justify-center text-white text-lg font-bold shrink-0"
                  style={{ background: avatarColors[i % avatarColors.length] }}>
                  {name.charAt(0)}
                </div>
                <div>
                  <div className="font-semibold text-[#1d1d1f] text-sm">{name}</div>
                  <div className="text-xs text-[#86868b]">English Teacher · BRIDGE</div>
                </div>
              </div>
              <div className="mb-4">
                <span className="text-3xl text-[#d1d1d6] leading-none">&ldquo;</span>
                <p className="text-sm text-[#424245] italic line-clamp-4 mt-1">
                  {p.preview?.replace(/#+\s/g, '').replace(/\*+/g, '').slice(0, 150)}
                </p>
              </div>
              <span className="text-sm font-medium text-[#0071e3] group-hover:underline">
                Read full story →
              </span>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
