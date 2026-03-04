"use client"

import { useEffect } from "react"

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  // Screen protection temporarily disabled for development
  useEffect(() => {
    document.body.style.filter = ""
  }, [])

  return (
    <div
      className="min-h-screen bg-[#f5f5f7]"
      style={{}}
    >
      <div className="max-w-7xl mx-auto px-4 py-6">
        {children}
      </div>
    </div>
  )
}
