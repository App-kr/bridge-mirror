'use client'

import { useCallback, useState } from 'react'

export interface UseDragReorderResult<T> {
  items: T[]
  handleMoveUp: (index: number) => void
  handleMoveDown: (index: number) => void
  setItems: (items: T[]) => void
}

/**
 * useDragReorder — ▲▼ button reorder hook (drag removed).
 * Local state only. Caller persists via onReorder callback.
 */
export function useDragReorder<T>(
  initialItems: T[],
  onReorder?: (items: T[]) => void,
): UseDragReorderResult<T> {
  const [items, setItemsState] = useState<T[]>(initialItems)

  const setItems = useCallback((next: T[]) => {
    setItemsState(next)
  }, [])

  const handleMoveUp = useCallback((index: number) => {
    if (index <= 0) return
    setItemsState(prev => {
      if (index >= prev.length) return prev
      const next = [...prev]
      ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
      onReorder?.(next)
      return next
    })
  }, [onReorder])

  const handleMoveDown = useCallback((index: number) => {
    setItemsState(prev => {
      if (index >= prev.length - 1) return prev
      const next = [...prev]
      ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
      onReorder?.(next)
      return next
    })
  }, [onReorder])

  return { items, handleMoveUp, handleMoveDown, setItems }
}
