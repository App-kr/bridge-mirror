'use client'

/**
 * /community/[board] — Dynamic board page with layout-specific scroll animations
 * Simplified: shared BoardHeader + stripMarkdown utility
 */

import { useEffect, useRef, useState } from 'react'
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

const API = ''

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

  const [posts, setPosts] = useState<Post[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [faqItems, setFaqItems] = useState<FaqItem[]>([])

  useEffect(() => {
    if (!config) return
    // Fetch main posts
    fetch(`${API}/api/community/${board}?limit=50`)
      .then((r) => r.json())
      .then((j) => { if (j.success) { setPosts(j.data.posts); setTotal(j.data.total) } })
      .finally(() => setLoading(false))

    // Fetch FAQ for support boards
    const faqCat = board === 'support' ? 'faq-teacher' : board === 'support_kr' ? 'faq-employer' : null
    if (faqCat) {
      fetch(`${API}/api/community/${board}?category=${faqCat}`)
        .then((r) => r.json())
        .then((j) => {
          if (j.success && j.data.posts.length > 0) {
            const body = j.data.posts[0].body ?? ''
            setFaqItems(parseFaqBody(body))
          }
        })
        .catch(() => {})
    }
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

  const props: LayoutProps = { config, posts, total, board, faqItems }

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
  // Filter out FAQ-tagged posts from the main list
  const regularPosts = posts.filter((p) => !p.title.toLowerCase().includes('faq'))

  // FAQ color themes + hardcoded data
  const faqConfig = board === 'support'
    ? { bg: 'bg-[#0a1628]', accent: '#3b82f6', label: 'Teacher FAQ', badgeBg: 'bg-blue-500/20', badgeText: 'text-blue-300', items: TEACHER_FAQ }
    : board === 'support_kr'
    ? { bg: 'bg-[#0a1f12]', accent: '#22c55e', label: '자주 묻는 질문', badgeBg: 'bg-green-500/20', badgeText: 'text-green-300', items: EMPLOYER_FAQ }
    : null

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
              <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                {faqConfig.label}
              </h2>
            </motion.div>

            <motion.div
              className="space-y-3"
              variants={staggerContainer} initial="hidden" animate="visible"
            >
              {faqConfig.items.map((item, i) => (
                <FaqAccordionItem key={i} item={item} index={i} accent={faqConfig.accent} />
              ))}
            </motion.div>

            {/* 업무지원 하단 문의 안내 */}
            {board === 'support_kr' && (
              <motion.div
                className="mt-10 text-center"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                <p className="text-white/50 text-sm mb-3">기타 궁금한 사항은 문의하기 페이지를 통해 연락 주세요.</p>
                <a href="/inquiry"
                  className="inline-block px-5 py-2.5 bg-[#22c55e] text-white text-sm font-medium rounded-full hover:bg-[#16a34a] transition-colors">
                  문의하기
                </a>
              </motion.div>
            )}
          </div>
        </section>
      )}

      {/* ── Regular Post List ── */}
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
        <BoardHeader config={config} />
        {regularPosts.length === 0 ? (
          <p className="text-[#86868b] text-center py-16">No posts yet.</p>
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
                  <span className="arrow">→</span>
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
function FaqAccordionItem({ item, index, accent }: { item: FaqItem; index: number; accent: string }) {
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
          <p className="text-sm text-white/60 leading-relaxed whitespace-pre-line">{item.a}</p>
        </motion.div>
      )}
    </motion.div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// HERO-CARDS — About BRIDGE (전면 개편)
// ══════════════════════════════════════════════════════════════════════════════
function HeroCardsLayout({ posts, board }: LayoutProps) {
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

  // Filter out FAQ posts (moved to Support)
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
            <motion.div
              className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4"
              variants={staggerContainer} initial="hidden" whileInView="visible" viewport={defaultViewport}
            >
              {aboutPosts.map((p, i) => (
                <motion.div key={p.id} variants={scaleIn}>
                  <Link
                    href={`/community/${board}/${p.id}`}
                    className="group flex items-center gap-4 bg-white rounded-2xl p-5
                               border border-transparent hover:border-[#0071e3]/20
                               hover:shadow-[0_4px_20px_rgba(0,0,0,0.04)]
                               transition-all duration-200"
                  >
                    <span className="text-2xl">{HERO_ICONS[i] ?? '📄'}</span>
                    <span className="text-[15px] font-semibold text-[#1d1d1f] group-hover:text-[#0071e3] transition-colors">
                      {p.title}
                    </span>
                  </Link>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>
      )}

      {/* ── Contact + Registration ── */}
      <section className="py-20 sm:py-28">
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

          {/* Registration info — small, subtle */}
          <motion.div
            className="mt-16 pt-8 border-t border-[#e5e5e5]"
            variants={fadeInUp} initial="hidden" whileInView="visible" viewport={defaultViewport}
          >
            <p className="text-xs text-[#86868b] leading-relaxed">
              BRIDGE Recruitment · 사업자등록번호 000-00-00000
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
