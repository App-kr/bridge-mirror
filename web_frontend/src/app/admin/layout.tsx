"use client"

import { useEffect } from "react"
import AdminSidebar from "@/components/admin/AdminSidebar"
import { useAdminAuth } from "@/hooks/useAdminAuth"

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { authed } = useAdminAuth()

  useEffect(() => {
    document.body.style.filter = ""
  }, [])

  if (!authed) {
    return (
      <div className="min-h-screen bg-[#f5f5f7]">
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
