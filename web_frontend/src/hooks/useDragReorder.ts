'use client'

import { useCallback, useRef, useState } from 'react'

export interface DragState {
  dragIndex: number | null
  overIndex: number | null
}

export interface UseDragReorderResult<T> {
  items: T[]
  dragState: DragState
  handleDragStart: (index: number) => void
  handleDragOver: (e: React.DragEvent, index: number) => void
  handleDrop: (e: React.DragEvent, index: number) => void
  handleDragEnd: () => void
  handleMoveUp: (index: number) => void
  handleMoveDown: (index: number) => void
  setItems: (items: T[]) => void
}

/**
 * useDragReorder — HTML5 Drag and Drop + ▲▼ button reorder hook.
 * Local state only (no API call). Caller persists via onReorder callback.
 */
export function useDragReorder<T>(
  initialItems: T[],
  onReorder?: (items: T[]) => void,
): UseDragReorderResult<T> {
  const [items, setItemsState] = useState<T[]>(initialItems)
  const [dragState, setDragState] = useState<DragState>({ dragIndex: null, overIndex: null })
  const dragIndexRef = useRef<number | null>(null)

  // Sync external items when they change
  const setItems = useCallback((next: T[]) => {
    setItemsState(next)
  }, [])

  const swap = useCallback((fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex) return
    if (fromIndex < 0 || toIndex < 0) return
    setItemsState(prev => {
      if (fromIndex >= prev.length || toIndex >= prev.length) return prev
      const next = [...prev]
      const [moved] = next.splice(fromIndex, 1)
      next.splice(toIndex, 0, moved)
      onReorder?.(next)
      return next
    })
  }, [onReorder])

  const handleDragStart = useCallback((index: number) => {
    dragIndexRef.current = index
    setDragState({ dragIndex: index, overIndex: null })
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent, index: number) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragState(prev => ({ ...prev, overIndex: index }))
  }, [])

  const handleDrop = useCallback((e: React.DragEvent, index: number) => {
    e.preventDefault()
    const from = dragIndexRef.current
    if (from !== null && from !== index) {
      swap(from, index)
    }
    dragIndexRef.current = null
    setDragState({ dragIndex: null, overIndex: null })
  }, [swap])

  const handleDragEnd = useCallback(() => {
    dragIndexRef.current = null
    setDragState({ dragIndex: null, overIndex: null })
  }, [])

  const handleMoveUp = useCallback((index: number) => {
    if (index <= 0) return
    swap(index, index - 1)
  }, [swap])

  const handleMoveDown = useCallback((index: number) => {
    setItemsState(prev => {
      if (index >= prev.length - 1) return prev
      const next = [...prev]
      const [moved] = next.splice(index, 1)
      next.splice(index + 1, 0, moved)
      onReorder?.(next)
      return next
    })
  }, [onReorder])

  return {
    items, dragState,
    handleDragStart, handleDragOver, handleDrop, handleDragEnd,
    handleMoveUp, handleMoveDown, setItems,
  }
}
