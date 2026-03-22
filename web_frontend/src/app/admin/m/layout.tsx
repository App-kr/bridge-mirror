'use client'

import MobileTabBar from './components/MobileTabBar'

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
