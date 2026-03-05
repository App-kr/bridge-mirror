'use client'

import { useCallback, useState } from 'react'
import { arrayMove } from '@dnd-kit/sortable'

export interface UseDragReorderResult<T> {
  items: T[]
  handleMoveUp: (index: number) => void
  handleMoveDown: (index: number) => void
  handleDndMove: (fromIndex: number, toIndex: number) => void
  setItems: (items: T[]) => void
}

/**
 * useDragReorder — ▲▼ buttons + @dnd-kit reorder hook.
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
      const next = arrayMove(prev, index, index - 1)
      onReorder?.(next)
      return next
    })
  }, [onReorder])

  const handleMoveDown = useCallback((index: number) => {
    setItemsState(prev => {
      if (index >= prev.length - 1) return prev
      const next = arrayMove(prev, index, index + 1)
      onReorder?.(next)
      return next
    })
  }, [onReorder])

  const handleDndMove = useCallback((fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0) return
    setItemsState(prev => {
      if (fromIndex >= prev.length || toIndex >= prev.length) return prev
      const next = arrayMove(prev, fromIndex, toIndex)
      onReorder?.(next)
      return next
    })
  }, [onReorder])

  return { items, handleMoveUp, handleMoveDown, handleDndMove, setItems }
}
