import Link from 'next/link'

const HUB_CARDS = [
  {
    slug: 'korea',
    emoji: '🇰🇷',
    title: 'Life in Korea',
    titleKr: '한국 생활 정보',
    description: 'City guides, living tips, culture, food, healthcare, and everything about life in Korea.',
    gradient: 'from-rose-50 to-pink-50',
    hoverBorder: 'hover:border-rose-300',
    iconBg: 'bg-rose-100',
  },
  {
    slug: 'testimonials',
    emoji: '💬',
    title: 'Testimonials',
    titleKr: '후기',
    description: 'Real stories from teachers who found their career through BRIDGE.',
    gradient: 'from-sky-50 to-blue-50',
    hoverBorder: 'hover:border-sky-300',
    iconBg: 'bg-sky-100',
  },
  {
    slug: 'tips',
    emoji: '💡',
    title: 'Tips',
    titleKr: '교사 팁',
    description: 'Photo tips, TEFL certification, interview advice, and professional development.',
    gradient: 'from-amber-50 to-orange-50',
    hoverBorder: 'hover:border-amber-300',
    iconBg: 'bg-amber-100',
  },
]

export default function CommunityPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
      {/* Header */}
      <div className="text-center mb-16">
        <h1 className="text-4xl sm:text-5xl font-bold text-[#1d1d1f] tracking-tight mb-4">
          Community
        </h1>
        <p className="text-lg text-[#86868b] max-w-lg mx-auto">
          Stories, answers, and tips from our teaching community.
        </p>
      </div>

      {/* Hub Cards */}
      <div className="flex flex-col sm:flex-row justify-center gap-6 max-w-2xl mx-auto">
        {HUB_CARDS.map((card) => (
          <Link
            key={card.slug}
            href={`/community/${card.slug}`}
            className={`group relative flex flex-col items-center text-center rounded-3xl border border-gray-200 ${card.hoverBorder} bg-gradient-to-b ${card.gradient} p-8 sm:p-10 transition-all duration-300 hover:shadow-lg hover:-translate-y-1 flex-1`}
          >
            {/* Icon */}
            <div className={`${card.iconBg} w-16 h-16 rounded-2xl flex items-center justify-center mb-6 transition-transform duration-300 group-hover:scale-110`}>
              <span className="text-3xl">{card.emoji}</span>
            </div>

            {/* Title */}
            <h2 className="text-xl font-bold text-[#1d1d1f] mb-1 group-hover:text-[#0071e3] transition-colors">
              {card.title}
            </h2>
            <span className="text-xs text-[#86868b] mb-4">{card.titleKr}</span>

            {/* Description */}
            <p className="text-sm text-[#6e6e73] leading-relaxed flex-1 mb-6">
              {card.description}
            </p>

            {/* CTA */}
            <span className="text-sm font-medium text-[#0071e3] group-hover:underline">
              Browse →
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}
