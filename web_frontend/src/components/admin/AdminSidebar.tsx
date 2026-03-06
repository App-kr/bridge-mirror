'use client'

import { useState } from 'react'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Users,
  Building2,
  Video,
  MessageSquare,
  Mail,
  FileText,
  MailCheck,
  Link2,
  Image,
  Megaphone,
  Handshake,
  Settings,
  CreditCard,
  Brain,
} from 'lucide-react'

interface NavItem {
  href: string
  label: string
  icon: React.ReactNode
}

interface NavCategory {
  title: string
  items: NavItem[]
}

const ICON_SIZE = 17

const NAV_CATEGORIES: NavCategory[] = [
  {
    title: '',
    items: [
      { href: '/admin', label: '대시보드', icon: <LayoutDashboard size={ICON_SIZE} /> },
    ],
  },
  {
    title: '인력 관리',
    items: [
      { href: '/admin/candidates', label: '원어민 관리', icon: <Users size={ICON_SIZE} /> },
      { href: '/admin/employers', label: '구인자 관리', icon: <Building2 size={ICON_SIZE} /> },
      { href: '/admin/interviews', label: '인터뷰 세팅', icon: <Video size={ICON_SIZE} /> },
      { href: '/admin/inquiries', label: '문의', icon: <MessageSquare size={ICON_SIZE} /> },
    ],
  },
  {
    title: '메일 관리',
    items: [
      { href: '/admin/mail-send', label: '메일 발송', icon: <Mail size={ICON_SIZE} /> },
      { href: '/admin/email-templates', label: '이메일 템플릿', icon: <FileText size={ICON_SIZE} /> },
      { href: '/admin/mail-logs', label: '메일 수발신 관리', icon: <MailCheck size={ICON_SIZE} /> },
    ],
  },
  {
    title: '게시판 관리',
    items: [
      { href: '/admin/posts', label: '전체 게시물', icon: <FileText size={ICON_SIZE} /> },
      { href: '/admin/guide-links', label: '링크 관리', icon: <Link2 size={ICON_SIZE} /> },
    ],
  },
  {
    title: '광고 관리',
    items: [
      { href: '/admin/banners', label: '배너 관리', icon: <Image size={ICON_SIZE} /> },
      { href: '/admin/ad-posts', label: 'AD 광고 관리', icon: <Megaphone size={ICON_SIZE} /> },
    ],
  },
  {
    title: '사이트 관리',
    items: [
      { href: '/admin/partners', label: '파트너', icon: <Handshake size={ICON_SIZE} /> },
      { href: '/admin/settings', label: '기본 설정', icon: <Settings size={ICON_SIZE} /> },
      { href: '/admin/payments', label: '결제', icon: <CreditCard size={ICON_SIZE} /> },
      { href: '/admin/matching', label: '프로필 매칭 (AI)', icon: <Brain size={ICON_SIZE} /> },
    ],
  },
]

export default function AdminSidebar() {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)

  const isActive = (href: string) => {
    if (href === '/admin') return pathname === '/admin'
    return pathname?.startsWith(href) ?? false
  }

  const sidebarContent = (
    <nav className="flex flex-col h-full">
      {/* Logo */}
      <div className="px-5 pt-6 pb-4">
        <a href="/admin" className="block">
          <span className="text-[17px] font-bold tracking-tight text-[#1d1d1f]">BRIDGE</span>
          <span className="text-[13px] text-[#86868b] ml-1.5 font-medium">Admin</span>
        </a>
      </div>

      {/* Nav Items */}
      <div className="flex-1 overflow-y-auto px-3 pb-6">
        {NAV_CATEGORIES.map((cat) => (
          <div key={cat.title || '_dashboard'}>
            {cat.title && (
              <div className="px-2 mb-1 mt-5 text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
                {cat.title}
              </div>
            )}
            <div className="space-y-0.5">
              {cat.items.map((item) => {
                const active = isActive(item.href)
                return (
                  <a
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={`
                      group flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[14px] font-medium transition-all duration-150
                      ${active
                        ? 'bg-blue-50 text-blue-600'
                        : 'text-[#424245] hover:bg-blue-50/50 hover:text-[#1d1d1f]'
                      }
                    `}
                  >
                    {active && (
                      <span className="absolute left-0 w-[3px] h-5 bg-blue-600 rounded-r-full" />
                    )}
                    <span className={`shrink-0 ${active ? 'text-blue-600' : 'text-zinc-400 group-hover:text-zinc-600'}`}>
                      {item.icon}
                    </span>
                    <span>{item.label}</span>
                  </a>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </nav>
  )

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-[240px] shrink-0 border-r border-[#e5e5e7] bg-white h-screen sticky top-0 flex-col relative">
        {sidebarContent}
      </aside>

      {/* Mobile hamburger */}
      <div className="lg:hidden fixed top-3 left-3 z-50">
        <button
          type="button"
          onClick={() => setMobileOpen(!mobileOpen)}
          className="w-10 h-10 flex items-center justify-center rounded-xl bg-white/90 backdrop-blur-sm shadow-sm border border-[#e5e5e7] text-[#1d1d1f]"
          aria-label="Toggle menu"
        >
          {mobileOpen ? (
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M4.5 4.5L13.5 13.5M4.5 13.5L13.5 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M3 5.5H15M3 9H15M3 12.5H15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
          )}
        </button>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div
            className="lg:hidden fixed inset-0 bg-black/30 backdrop-blur-sm z-40"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="lg:hidden fixed inset-y-0 left-0 w-[280px] bg-white z-50 shadow-2xl relative">
            {sidebarContent}
          </aside>
        </>
      )}
    </>
  )
}
