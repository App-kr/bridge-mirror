/**
 * Community Board Definitions — Claude.ai 설계 기준 7개 보드
 * 각 보드별 고유 레이아웃 타입 지정
 */

export type LayoutType = 'list' | 'hero-cards' | 'card-grid' | 'photo-cards' | 'testimonial' | 'testimonials'

export interface BoardConfig {
  slug: string
  label: string
  labelNav: string        // 네비게이션 표시명
  emoji: string
  description: string
  descriptionKr: string
  accentColor: string
  badgeClass: string
  borderColor: string
  markdown: boolean
  layout: LayoutType
  notice?: string          // 보드 상단 경고 배너
  noticeKr?: string
}

export const BOARDS: BoardConfig[] = [
  {
    slug: 'about',
    label: 'About BRIDGE',
    labelNav: 'About us',
    emoji: '🌉',
    description: 'About BRIDGE Recruitment — our mission, services, and how we connect teachers with schools.',
    descriptionKr: 'BRIDGE 소개',
    accentColor: 'text-violet-600',
    badgeClass: 'bg-violet-50 text-violet-700 border-violet-200',
    borderColor: 'hover:border-violet-400',
    markdown: true,
    layout: 'hero-cards',
  },
  {
    slug: 'korea',
    label: 'Life in Korea',
    labelNav: 'Korea',
    emoji: '🇰🇷',
    description: 'City guides, culture, living tips, and everything about life in Korea.',
    descriptionKr: '한국 생활 정보',
    accentColor: 'text-rose-600',
    badgeClass: 'bg-rose-50 text-rose-700 border-rose-200',
    borderColor: 'hover:border-rose-400',
    markdown: true,
    layout: 'photo-cards',
  },
  {
    slug: 'visa',
    label: 'Visa',
    labelNav: 'Visa',
    emoji: '🛂',
    description: 'E-2 visa guides, document requirements, background checks, and immigration procedures.',
    descriptionKr: '비자 정보',
    accentColor: 'text-emerald-600',
    badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    borderColor: 'hover:border-emerald-400',
    markdown: true,
    layout: 'list',
    notice: '⚠️ Information may change. Always verify with your local immigration office.',
    noticeKr: '⚠️ 정보가 변경될 수 있습니다. 반드시 관할 출입국관리사무소에서 확인하세요.',
  },
  {
    slug: 'support',
    label: 'Support',
    labelNav: 'Support',
    emoji: '📄',
    description: 'Arrival checklist, visa change, housing guide, and essential information for teachers.',
    descriptionKr: '지원 안내 (English)',
    accentColor: 'text-blue-600',
    badgeClass: 'bg-blue-50 text-blue-700 border-blue-200',
    borderColor: 'hover:border-blue-400',
    markdown: true,
    layout: 'list',
    notice: '⚠️ Information is for reference only. Please confirm details directly.',
    noticeKr: '⚠️ 게시물은 참고용입니다. 세부사항은 직접 확인하시기 바랍니다.',
  },
  {
    slug: 'support_kr',
    label: '업무지원',
    labelNav: '업무지원',
    emoji: '📋',
    description: '외국인 강사 체류 신고, 해외 초청 절차, 근로계약서 안내 등 업무 지원 자료입니다.',
    descriptionKr: '업무지원 (한국어)',
    accentColor: 'text-orange-600',
    badgeClass: 'bg-orange-50 text-orange-700 border-orange-200',
    borderColor: 'hover:border-orange-400',
    markdown: true,
    layout: 'list',
    notice: '⚠️ 게시물은 참고용입니다. 세부사항은 직접 확인하시기 바랍니다.',
  },
  {
    slug: 'tips',
    label: 'Tips',
    labelNav: 'Tips',
    emoji: '💡',
    description: 'Photo tips, TEFL certification, interview advice, and professional development.',
    descriptionKr: '교사 팁',
    accentColor: 'text-amber-600',
    badgeClass: 'bg-amber-50 text-amber-700 border-amber-200',
    borderColor: 'hover:border-amber-400',
    markdown: true,
    layout: 'card-grid',
  },
  {
    slug: 'information',
    label: 'Information',
    labelNav: 'Information',
    emoji: 'ℹ️',
    description: 'BRIDGE team, services, and agency information for teachers and schools.',
    descriptionKr: '팀·서비스·소개소 안내',
    accentColor: 'text-indigo-600',
    badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    borderColor: 'hover:border-indigo-400',
    markdown: true,
    layout: 'list',
  },
  {
    slug: 'testimonials',
    label: 'Testimonials',
    labelNav: 'Testimonials',
    emoji: '💬',
    description: 'Real stories from teachers who found their career through BRIDGE.',
    descriptionKr: '후기',
    accentColor: 'text-sky-600',
    badgeClass: 'bg-sky-50 text-sky-700 border-sky-200',
    borderColor: 'hover:border-sky-400',
    markdown: true,
    layout: 'testimonial',
  },
]

export const BOARD_MAP = Object.fromEntries(BOARDS.map((b) => [b.slug, b]))

export type BoardSlug = typeof BOARDS[number]['slug']

export function getBoardConfig(slug: string): BoardConfig | undefined {
  return BOARD_MAP[slug]
}

export function isValidBoard(slug: string): boolean {
  return slug in BOARD_MAP
}

// 네비게이션 표시 순서
export const NAV_BOARDS = ['about', 'korea', 'visa', 'support', 'support_kr'] as const

// Community 허브에 표시할 보드
export const COMMUNITY_HUB_BOARDS = ['testimonials', 'support', 'tips'] as const
