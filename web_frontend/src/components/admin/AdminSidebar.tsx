'use client'

import { useCallback, useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
import { API_URL } from '@/lib/api'
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
  Table2,
  HelpCircle,
  LogOut,
  KeyRound,
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
const ADMIN_KEY_STORAGE = 'bridge_admin_key'

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
      { href: '/admin/sheet', label: '원어민 스프레드시트', icon: <Table2 size={ICON_SIZE} /> },
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
      { href: '/admin/faq', label: 'FAQ 관리', icon: <HelpCircle size={ICON_SIZE} /> },
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
      { href: '/admin/kakao-setup', label: '카카오 로그인 설정', icon: <KeyRound size={ICON_SIZE} /> },
    ],
  },
]

const ADMIN_EXPIRY_STORAGE = 'bridge_admin_key_expiry'

export default function AdminSidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [kakaoUrl, setKakaoUrl] = useState<string>('')
  const [newCount, setNewCount] = useState(0)

  const handleLogout = () => {
    localStorage.removeItem(ADMIN_KEY_STORAGE)
    localStorage.removeItem(ADMIN_EXPIRY_STORAGE)
    document.cookie = 'bridge_edit_mode=; path=/; max-age=0'
    router.push('/')
  }

  useEffect(() => {
    fetch(`${API_URL}/api/settings`)
      .then(r => r.json())
      .then(j => { if (j.success) setKakaoUrl(j.data?.settings?.kakao_channel ?? '') })
      .catch(() => {})
  }, [])

  const pollNewCount = useCallback(() => {
    const key = typeof window !== 'undefined' ? localStorage.getItem(ADMIN_KEY_STORAGE) : ''
    if (!key) return
    fetch(`${API_URL}/api/admin/inquiries/new-count`, {
      headers: { 'x-admin-key': key },
    })
      .then(r => r.json())
      .then(j => { if (j.success) setNewCount(j.data?.count ?? 0) })
      .catch(() => {})
  }, [])

  useEffect(() => {
    pollNewCount()
    const timer = setInterval(pollNewCount, 5000)
    return () => clearInterval(timer)
  }, [pollNewCount])

  const isActive = (href: string) => {
    if (href === '/admin') return pathname === '/admin'
    return pathname?.startsWith(href) ?? false
  }

  const sidebarContent = (
    <nav className="flex flex-col h-full">
      {/* Logo — 클릭 시 항상 /admin 으로 이동 (같은 페이지여도 동작) */}
      <div className="px-5 pt-6 pb-4">
        <button
          type="button"
          onClick={() => { router.push('/admin'); router.refresh(); setMobileOpen(false) }}
          className="block text-left cursor-pointer"
        >
          <span className="text-[17px] font-bold tracking-tight text-[#1d1d1f]">BRIDGE</span>
          <span className="text-[13px] text-[#86868b] ml-1.5 font-medium">Admin</span>
        </button>
      </div>

      {/* Nav Items */}
      <div className="flex-1 overflow-y-auto px-3 pb-2">
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
                  <Link
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
                    <span className={`shrink-0 ${active ? 'text-blue-600' : item.href === '/admin/employers' && newCount > 0 ? 'text-blue-500' : 'text-zinc-400 group-hover:text-zinc-600'}`}>
                      {item.icon}
                    </span>
                    <span>{item.label}</span>
                    {item.href === '/admin/employers' && newCount > 0 && (
                      <span className="ml-auto shrink-0 text-[10px] font-bold text-white bg-blue-500 rounded-full px-1.5 py-0.5 animate-pulse leading-none">
                        {newCount}
                      </span>
                    )}
                  </Link>
                )
              })}

              {/* 사이트 관리 섹션 하단: 카카오 채널 */}
              {cat.title === '사이트 관리' && (
                <div className="mt-1">
                  {kakaoUrl ? (
                    <a
                      href={kakaoUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg w-full font-medium text-[14px] text-[#191919] transition-all hover:brightness-95 active:scale-[0.98]"
                      style={{ background: '#FEE500' }}
                      onClick={() => setMobileOpen(false)}
                    >
                      <span className="text-[15px] leading-none shrink-0">💬</span>
                      <span>카카오 채널</span>
                      <span className="ml-auto text-[11px] opacity-50">↗</span>
                    </a>
                  ) : (
                    <Link
                      href="/admin/settings"
                      className="group flex items-center gap-2.5 px-3 py-2.5 rounded-lg w-full text-[14px] font-medium text-[#86868b] hover:text-[#424245] transition-colors"
                      onClick={() => setMobileOpen(false)}
                    >
                      <span className="text-[15px] leading-none shrink-0">💬</span>
                      <span>카카오 채널 설정</span>
                    </Link>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* 하단: 로그아웃 */}
      <div className="px-3 pb-4 pt-2 border-t border-[#f0f0f2]">
        <button
          type="button"
          onClick={handleLogout}
          className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg w-full text-[14px] font-medium text-red-400 transition-colors"
          style={{ background: 'rgba(255, 59, 48, 0.06)' }}
        >
          <LogOut size={ICON_SIZE} className="shrink-0 text-red-300" />
          <span>로그아웃</span>
        </button>
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
