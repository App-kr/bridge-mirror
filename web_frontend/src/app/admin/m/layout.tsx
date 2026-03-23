'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import MobileTabBar from './components/MobileTabBar'
import { Bell, BellOff } from 'lucide-react'

function NotificationIndicator() {
  const [hasPermission, setHasPermission] = useState<boolean | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined' || !('Notification' in window)) return
    setHasPermission(Notification.permission === 'granted')
  }, [])

  if (hasPermission === null) return null

  return (
    <Link
      href="/admin/m/settings"
      className="w-8 h-8 rounded-full bg-[#f5f5f7] flex items-center justify-center relative"
    >
      {hasPermission ? (
        <Bell size={16} className="text-[#1d1d1f]" />
      ) : (
        <BellOff size={16} className="text-[#86868b]" />
      )}
      {!hasPermission && (
        <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-[#ff3b30] border-2 border-white" />
      )}
    </Link>
  )
}

export default function MobileLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col h-screen bg-[#f5f5f7]">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-[#e5e5e7] px-4 py-3 flex items-center justify-between sticky top-0 z-30"
        style={{ paddingTop: 'calc(env(safe-area-inset-top, 0px) + 12px)' }}
      >
        <div>
          <span className="text-[15px] font-bold text-[#1d1d1f] tracking-tight">BRIDGE</span>
          <span className="text-[11px] text-[#86868b] ml-1.5 font-medium">Admin</span>
        </div>
        <NotificationIndicator />
      </header>

      {/* Content */}
      <main className="flex-1 overflow-y-auto pb-[calc(56px+env(safe-area-inset-bottom))]">
        {children}
      </main>

      {/* Tab Bar */}
      <MobileTabBar />
    </div>
  )
}
