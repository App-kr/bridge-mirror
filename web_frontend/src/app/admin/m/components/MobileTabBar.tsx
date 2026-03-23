'use client'

import { useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Home, Users, MessageSquare, Mail, MoreHorizontal, Video, Monitor, LogOut, Settings } from 'lucide-react'
import { useAdminAuth } from '@/hooks/useAdminAuth'

interface Tab {
  key: string
  label: string
  href: string
  icon: typeof Home
}

const TABS: Tab[] = [
  { key: 'home', label: '\uD648', href: '/admin/m', icon: Home },
  { key: 'candidates', label: '\uC811\uC218', href: '/admin/m/candidates', icon: Users },
  { key: 'inquiries', label: '\uBB38\uC758', href: '/admin/m/inquiries', icon: MessageSquare },
  { key: 'mail', label: '\uBA54\uC77C', href: '/admin/m/mail', icon: Mail },
]

export default function MobileTabBar() {
  const pathname = usePathname()
  const router = useRouter()
  const { logout } = useAdminAuth()
  const [moreOpen, setMoreOpen] = useState(false)

  const isActive = (href: string) => {
    if (href === '/admin/m') return pathname === '/admin/m'
    return pathname?.startsWith(href) ?? false
  }

  const handleDesktopMode = () => {
    localStorage.setItem('bridge_prefer_desktop', '1')
    router.push('/admin')
  }

  const handleLogout = () => {
    logout()
    router.push('/')
  }

  return (
    <>
      {/* More menu backdrop + sheet */}
      {moreOpen && (
        <div className="fixed inset-0 z-50">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/30 backdrop-blur-sm"
            onClick={() => setMoreOpen(false)}
          />
          {/* Bottom sheet */}
          <div
            className="absolute bottom-0 left-0 right-0 bg-white rounded-t-2xl shadow-xl animate-slide-up"
            style={{ paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 16px)' }}
          >
            <div className="flex justify-center pt-3 pb-2">
              <div className="w-10 h-1 bg-[#e5e5e7] rounded-full" />
            </div>
            <nav className="px-4 pb-2">
              <button
                onClick={() => { setMoreOpen(false); router.push('/admin/m/interviews') }}
                className="flex items-center gap-3 w-full px-4 py-3.5 rounded-xl text-[#1d1d1f] hover:bg-[#f5f5f7] active:bg-[#e5e5e7] transition-colors"
              >
                <Video size={20} className="text-[#86868b]" />
                <span className="text-[15px] font-medium">인터뷰 관리</span>
              </button>
              <button
                onClick={() => { setMoreOpen(false); router.push('/admin/m/settings') }}
                className="flex items-center gap-3 w-full px-4 py-3.5 rounded-xl text-[#1d1d1f] hover:bg-[#f5f5f7] active:bg-[#e5e5e7] transition-colors"
              >
                <Settings size={20} className="text-[#86868b]" />
                <span className="text-[15px] font-medium">설정</span>
              </button>
              <button
                onClick={() => { setMoreOpen(false); handleDesktopMode() }}
                className="flex items-center gap-3 w-full px-4 py-3.5 rounded-xl text-[#1d1d1f] hover:bg-[#f5f5f7] active:bg-[#e5e5e7] transition-colors"
              >
                <Monitor size={20} className="text-[#86868b]" />
                <span className="text-[15px] font-medium">데스크톱 모드</span>
              </button>
              <div className="h-px bg-[#e5e5e7] mx-4 my-1" />
              <button
                onClick={() => { setMoreOpen(false); handleLogout() }}
                className="flex items-center gap-3 w-full px-4 py-3.5 rounded-xl text-red-500 hover:bg-red-50 active:bg-red-100 transition-colors"
              >
                <LogOut size={20} />
                <span className="text-[15px] font-medium">로그아웃</span>
              </button>
            </nav>
          </div>
        </div>
      )}

      {/* Tab Bar */}
      <div
        className="fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur-xl border-t border-[#e5e5e7] z-40 flex items-end justify-around"
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      >
        {TABS.map((tab) => {
          const active = isActive(tab.href)
          const Icon = tab.icon
          return (
            <Link
              key={tab.key}
              href={tab.href}
              className="flex flex-col items-center justify-center gap-0.5 min-w-[56px] py-1 pt-2 relative"
            >
              <Icon
                size={22}
                className={active ? 'text-[#0071e3]' : 'text-[#86868b]'}
                strokeWidth={active ? 2.2 : 1.8}
              />
              <span className={`text-[10px] font-medium ${active ? 'text-[#0071e3]' : 'text-[#86868b]'}`}>
                {tab.label}
              </span>
              {active && (
                <div className="absolute -top-px left-1/2 -translate-x-1/2 w-4 h-[2px] bg-[#0071e3] rounded-full" />
              )}
            </Link>
          )
        })}
        {/* More tab */}
        <button
          onClick={() => setMoreOpen(true)}
          className="flex flex-col items-center justify-center gap-0.5 min-w-[56px] py-1 pt-2"
        >
          <MoreHorizontal
            size={22}
            className={moreOpen ? 'text-[#0071e3]' : 'text-[#86868b]'}
            strokeWidth={1.8}
          />
          <span className={`text-[10px] font-medium ${moreOpen ? 'text-[#0071e3]' : 'text-[#86868b]'}`}>
            더보기
          </span>
        </button>
      </div>

      {/* Slide-up animation */}
      <style jsx global>{`
        @keyframes slide-up {
          from { transform: translateY(100%); }
          to { transform: translateY(0); }
        }
        .animate-slide-up {
          animation: slide-up 0.3s cubic-bezier(0.32, 0.72, 0, 1);
        }
      `}</style>
    </>
  )
}
