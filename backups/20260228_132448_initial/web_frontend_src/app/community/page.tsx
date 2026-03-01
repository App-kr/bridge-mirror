import Link from 'next/link'
import { BOARDS, type BoardConfig } from '@/lib/boards'

/* ── 카테고리별 분류 ── */
const CATEGORIES: { title: string; titleKr: string; boards: string[] }[] = [
  {
    title: 'About & Living',
    titleKr: '소개 · 생활',
    boards: ['about', 'korea'],
  },
  {
    title: 'Visa & Support',
    titleKr: '비자 · 업무지원',
    boards: ['visa', 'support', 'support_kr'],
  },
  {
    title: 'Tips & Stories',
    titleKr: '팁 · 후기',
    boards: ['tips', 'testimonials'],
  },
]

const BOARD_MAP = Object.fromEntries(BOARDS.map((b) => [b.slug, b]))

export default function CommunityPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12">

      <div className="text-center mb-14">
        <h1 className="text-4xl font-bold text-[#1d1d1f] mb-3">Community</h1>
        <p className="text-[#86868b] max-w-md mx-auto">
          Resources, guides, and stories for teachers and schools.
        </p>
      </div>

      {/* ── 카테고리별 섹션 ── */}
      <div className="space-y-12">
        {CATEGORIES.map((cat) => (
          <section key={cat.title}>
            <div className="flex items-baseline gap-3 mb-5">
              <h2 className="text-lg font-bold text-[#1d1d1f]">{cat.title}</h2>
              <span className="text-xs text-[#86868b]">{cat.titleKr}</span>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {cat.boards.map((slug) => {
                const b = BOARD_MAP[slug]
                if (!b) return null
                return <BoardCard key={slug} board={b} />
              })}
            </div>
          </section>
        ))}
      </div>

    </div>
  )
}

function BoardCard({ board }: { board: BoardConfig }) {
  return (
    <Link
      href={`/community/${board.slug}`}
      className="card group !rounded-2xl flex flex-col"
    >
      <div className="flex items-center gap-3 mb-3">
        <span className="text-3xl">{board.emoji}</span>
        <div>
          <h3 className="text-[17px] font-bold text-[#1d1d1f] group-hover:text-[#0071e3] transition-colors">
            {board.label}
          </h3>
          <span className="text-xs text-[#86868b]">{board.descriptionKr}</span>
        </div>
      </div>
      <p className="text-sm text-[#6e6e73] line-clamp-2 mb-4 flex-1">
        {board.description}
      </p>
      <div className="flex items-center justify-between">
        <span className={`inline-block text-xs px-2 py-0.5 rounded-full border ${board.badgeClass}`}>
          {board.labelNav}
        </span>
        <span className="text-sm font-medium text-[#0071e3]">Browse →</span>
      </div>
    </Link>
  )
}
