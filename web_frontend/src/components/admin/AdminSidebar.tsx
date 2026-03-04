'use client'

import { useState } from 'react'
import { usePathname } from 'next/navigation'

interface NavItem {
  href: string
  label: string
}

interface NavCategory {
  title: string
  items: NavItem[]
}

const NAV_CATEGORIES: NavCategory[] = [
  {
    title: '',
    items: [
      { href: '/admin', label: '대시보드' },
    ],
  },
  {
    title: '인력 관리',
    items: [
      { href: '/admin/inbox', label: '수신함' },
      { href: '/admin/candidates', label: '원어민 관리' },
      { href: '/admin/applications', label: '업체관리' },
      { href: '/admin/interviews', label: '인터뷰' },
    ],
  },
  {
    title: '게시판 관리',
    items: [
      { href: '/admin/posts', label: '게시글' },
      { href: '/admin/boards', label: '보드 관리' },
      { href: '/admin/banners', label: '배너' },
      { href: '/admin/guide-links', label: '가이드 링크' },
    ],
  },
  {
    title: '광고 관리',
    items: [
      { href: '/admin/ad-posts', label: 'Ad Posts' },
      { href: '/admin/email-templates', label: '이메일 템플릿' },
    ],
  },
  {
    title: '운영',
    items: [
      { href: '/admin/jobs', label: '구인 관리' },
      { href: '/admin/payments', label: '결제' },
      { href: '/admin/inquiries', label: '문의' },
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
          <span className="text-[15px] font-bold tracking-tight text-[#1d1d1f]">BRIDGE</span>
          <span className="text-[11px] text-[#86868b] ml-1.5 font-medium">Admin</span>
        </a>
      </div>

      {/* Nav Items */}
      <div className="flex-1 overflow-y-auto px-3 pb-6 space-y-5">
        {NAV_CATEGORIES.map((cat) => (
          <div key={cat.title || '_dashboard'}>
            {cat.title && (
              <div className="px-2 mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[#86868b]">
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
                      group flex items-center px-2.5 py-2 rounded-lg text-[13px] font-medium transition-all duration-150
                      ${active
                        ? 'bg-[#0071e3]/10 text-[#0071e3]'
                        : 'text-[#424245] hover:bg-[#f5f5f7] hover:text-[#1d1d1f]'
                      }
                    `}
                  >
                    {active && (
                      <span className="w-[3px] h-4 bg-[#0071e3] rounded-full mr-2 shrink-0" />
                    )}
                    <span className={active ? '' : 'ml-[11px]'}>{item.label}</span>
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
      <aside className="hidden lg:flex w-[240px] shrink-0 border-r border-[#e5e5e7] bg-white/80 backdrop-blur-xl h-screen sticky top-0 flex-col">
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
          <aside className="lg:hidden fixed inset-y-0 left-0 w-[280px] bg-white z-50 shadow-2xl">
            {sidebarContent}
          </aside>
        </>
      )}
    </>
  )
}
