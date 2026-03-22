'use client'
import { useRef, useState, useCallback } from 'react'

interface PullToRefreshProps {
  children: React.ReactNode
  onRefresh: () => Promise<void>
  disabled?: boolean
}

export default function PullToRefresh({ children, onRefresh, disabled }: PullToRefreshProps) {
  const [pulling, setPulling] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [pullDistance, setPullDistance] = useState(0)
  const startY = useRef(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const THRESHOLD = 80

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (disabled || refreshing) return
    // Only activate if scrolled to top
    if (containerRef.current && containerRef.current.scrollTop > 0) return
    startY.current = e.touches[0].clientY
    setPulling(true)
  }, [disabled, refreshing])

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!pulling || refreshing) return
    const dy = e.touches[0].clientY - startY.current
    if (dy > 0) {
      // Diminishing pull effect
      setPullDistance(Math.min(dy * 0.5, 120))
    }
  }, [pulling, refreshing])

  const handleTouchEnd = useCallback(async () => {
    if (!pulling) return
    setPulling(false)
    if (pullDistance >= THRESHOLD) {
      setRefreshing(true)
      try { await onRefresh() } finally {
        setRefreshing(false)
        setPullDistance(0)
      }
    } else {
      setPullDistance(0)
    }
  }, [pulling, pullDistance, onRefresh])

  return (
    <div ref={containerRef} className="relative overflow-y-auto h-full"
      onTouchStart={handleTouchStart} onTouchMove={handleTouchMove} onTouchEnd={handleTouchEnd}>
      {/* Pull indicator */}
      <div className="flex items-center justify-center transition-all duration-200 overflow-hidden"
        style={{ height: refreshing ? 48 : pullDistance > 10 ? Math.min(pullDistance, 80) : 0 }}>
        <div className={`w-6 h-6 border-2 border-[#0071e3] border-t-transparent rounded-full ${refreshing ? 'animate-spin' : ''}`}
          style={{ opacity: Math.min(pullDistance / THRESHOLD, 1), transform: `rotate(${pullDistance * 3}deg)` }} />
      </div>
      {children}
    </div>
  )
}
