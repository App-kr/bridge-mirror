"use client"

import { useEffect } from "react"
import { usePathname, useRouter } from "next/navigation"
import AdminSidebar from "@/components/admin/AdminSidebar"
import AdminAuthModal from "@/components/admin/AdminAuthModal"
import { useAdminAuth } from "@/hooks/useAdminAuth"

// DEV_MODE: true = 캡쳐 보호 OFF (개발용), false = 보호 ON (운영용)
const DEV_MODE = false

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { authed, login, waking } = useAdminAuth()
  const pathname = usePathname()
  const router = useRouter()
  const isFullWidth = pathname === '/admin/sheet' || pathname === '/admin/employers'
  const isMobilePath = pathname === '/admin/m' || pathname?.startsWith('/admin/m/')

  useEffect(() => {
    document.body.style.filter = ""
  }, [])

  // Auto-redirect mobile devices to /admin/m
  useEffect(() => {
    if (typeof window === 'undefined') return
    if (pathname?.startsWith('/admin/m')) return
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent) && window.innerWidth < 768
    const preferDesktop = localStorage.getItem('bridge_prefer_desktop')
    if (isMobile && !preferDesktop) {
      router.replace('/admin/m')
    }
  }, [pathname, router])

  if (!authed) {
    return (
      <div className="min-h-screen bg-[#f5f5f7]">
        <AdminAuthModal
          onLogin={login}
          waking={waking}
          onClose={() => {}}
        />
      </div>
    )
  }

  // Mobile paths: skip desktop sidebar, let mobile layout handle UI
  if (isMobilePath) {
    return <>{children}</>
  }

  const isSubPage = pathname !== '/admin'

  return (
    <div className="fixed inset-0 bg-[#f5f5f7] flex flex-col lg:flex-row overflow-hidden z-50">
      <AdminSidebar />

      {/* ── 중/소 화면 상단 네비바 (lg 미만) ── */}
      {isSubPage && (
        <div className="lg:hidden flex items-center gap-2 px-4 py-2.5 bg-white border-b border-[#e5e5e7] shrink-0 z-40"
             style={{ paddingLeft: 52 }}>
          <button
            type="button"
            onClick={() => router.push('/admin')}
            className="flex items-center gap-1.5 text-[13px] font-medium text-blue-600 hover:text-blue-700 transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 11L5 7L9 3"/>
            </svg>
            대시보드
          </button>
          <span className="text-[11px] text-[#aaa]">/</span>
          <span className="text-[12px] text-[#555] font-medium truncate">
            {pathname?.split('/').pop()?.replace(/-/g, ' ')}
          </span>
        </div>
      )}

      <main className="flex-1 min-w-0 overflow-hidden h-full">
        {isFullWidth ? (
          <div className="w-full h-full">
            {children}
          </div>
        ) : (
          <div className="max-w-6xl mx-auto px-4 lg:px-8 py-6 lg:py-8 h-full overflow-y-auto">
            {children}
          </div>
        )}
      </main>
    </div>
  )
}
