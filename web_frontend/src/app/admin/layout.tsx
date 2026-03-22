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
  const isMobilePath = pathname?.startsWith('/admin/m')

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

  return (
    <div className="fixed inset-0 bg-[#f5f5f7] flex overflow-hidden z-50">
      <AdminSidebar />
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
