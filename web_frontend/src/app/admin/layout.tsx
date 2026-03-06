"use client"

import { useEffect } from "react"
import AdminSidebar from "@/components/admin/AdminSidebar"
import { useAdminAuth } from "@/hooks/useAdminAuth"

// DEV_MODE: true = 캡쳐 보호 OFF (개발용), false = 보호 ON (운영용)
const DEV_MODE = true

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { authed } = useAdminAuth()

  useEffect(() => {
    document.body.style.filter = ""
  }, [])

  if (!authed) {
    return (
      <div className="min-h-screen bg-[#f5f5f7]">
        {/* 비관리자 접근 경고 바 */}
        <div className="admin-warning-bar text-center py-3 px-4 text-sm font-medium text-red-700 border-b border-red-200">
          <span className="inline-flex items-center gap-1.5">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>
            관리자 전용 페이지입니다. 접근 기록이 저장됩니다.
          </span>
        </div>
        <div className="max-w-6xl mx-auto px-4 py-6">
          {children}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#f5f5f7] flex">
      <AdminSidebar />
      <main className="flex-1 min-w-0">
        <div className="max-w-6xl mx-auto px-4 lg:px-8 py-6 lg:py-8">
          {children}
        </div>
      </main>
    </div>
  )
}
