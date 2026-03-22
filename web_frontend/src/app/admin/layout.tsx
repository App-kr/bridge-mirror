"use client"

import { useEffect } from "react"
import { usePathname } from "next/navigation"
import AdminSidebar from "@/components/admin/AdminSidebar"
import AdminAuthModal from "@/components/admin/AdminAuthModal"
import { useAdminAuth } from "@/hooks/useAdminAuth"

// DEV_MODE: true = 캡쳐 보호 OFF (개발용), false = 보호 ON (운영용)
const DEV_MODE = false

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { authed, login, waking } = useAdminAuth()
  const pathname = usePathname()
  const isFullWidth = pathname === '/admin/sheet' || pathname === '/admin/employers'

  useEffect(() => {
    document.body.style.filter = ""
  }, [])

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
