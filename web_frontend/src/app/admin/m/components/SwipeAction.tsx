'use client'
import { useRef, useState, useCallback } from 'react'

interface SwipeActionProps {
  children: React.ReactNode
  leftActions?: React.ReactNode
  rightActions?: React.ReactNode
}

export default function SwipeAction({ children, leftActions, rightActions }: SwipeActionProps) {
  const [offsetX, setOffsetX] = useState(0)
  const startX = useRef(0)
  const startY = useRef(0)
  const swiping = useRef(false)
  const ACTION_WIDTH = 80

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    startX.current = e.touches[0].clientX
    startY.current = e.touches[0].clientY
    swiping.current = false
  }, [])

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    const dx = e.touches[0].clientX - startX.current
    const dy = e.touches[0].clientY - startY.current

    // If vertical scroll dominates, don't swipe
    if (!swiping.current && Math.abs(dy) > Math.abs(dx)) return
    swiping.current = true

    let bounded = dx
    if (!leftActions && dx > 0) bounded = 0
    if (!rightActions && dx < 0) bounded = 0
    bounded = Math.max(-ACTION_WIDTH * 1.2, Math.min(ACTION_WIDTH * 1.2, bounded))
    setOffsetX(bounded)
  }, [leftActions, rightActions])

  const handleTouchEnd = useCallback(() => {
    if (Math.abs(offsetX) >= ACTION_WIDTH * 0.5) {
      setOffsetX(offsetX > 0 ? ACTION_WIDTH : -ACTION_WIDTH)
    } else {
      setOffsetX(0)
    }
  }, [offsetX])

  const close = useCallback(() => setOffsetX(0), [])

  return (
    <div className="relative overflow-hidden rounded-2xl">
      {/* Left actions (shown on right swipe) */}
      {leftActions && (
        <div className="absolute inset-y-0 left-0 w-20 flex items-center justify-center bg-[#0071e3]"
          onClick={close}>
          {leftActions}
        </div>
      )}
      {/* Right actions (shown on left swipe) */}
      {rightActions && (
        <div className="absolute inset-y-0 right-0 w-20 flex items-center justify-center bg-[#ff9f0a]"
          onClick={close}>
          {rightActions}
        </div>
      )}
      {/* Main content */}
      <div className="relative bg-white transition-transform duration-200 ease-out"
        style={{ transform: `translateX(${offsetX}px)` }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}>
        {children}
      </div>
    </div>
  )
}
