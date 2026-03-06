'use client'

import { useState } from 'react'

export interface ColumnDef {
  key: string
  label: string
  visible: boolean
  width: number
}

interface ColumnManagerProps {
  columns: ColumnDef[]
  onChange: (columns: ColumnDef[]) => void
  onClose: () => void
}

export default function ColumnManager({ columns, onChange, onClose }: ColumnManagerProps) {
  const [local, setLocal] = useState<ColumnDef[]>(() => columns.map(c => ({ ...c })))
  const [dragIdx, setDragIdx] = useState<number | null>(null)

  const toggleVisible = (idx: number) => {
    const next = [...local]
    next[idx] = { ...next[idx], visible: !next[idx].visible }
    setLocal(next)
  }

  const moveUp = (idx: number) => {
    if (idx === 0) return
    const next = [...local]
    const tmp = next[idx - 1]
    next[idx - 1] = next[idx]
    next[idx] = tmp
    setLocal(next)
  }

  const moveDown = (idx: number) => {
    if (idx === local.length - 1) return
    const next = [...local]
    const tmp = next[idx + 1]
    next[idx + 1] = next[idx]
    next[idx] = tmp
    setLocal(next)
  }

  const handleDragStart = (idx: number) => setDragIdx(idx)

  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault()
    if (dragIdx === null || dragIdx === idx) return
    const next = [...local]
    const [moved] = next.splice(dragIdx, 1)
    next.splice(idx, 0, moved)
    setLocal(next)
    setDragIdx(idx)
  }

  const handleDragEnd = () => setDragIdx(null)

  const apply = () => { onChange(local); onClose() }

  const reset = () => setLocal(local.map(c => ({ ...c, visible: true })))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-96 max-h-[80vh] overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="text-[15px] font-bold text-[#1d1d1f]">열 관리</h3>
          <button type="button" onClick={onClose} className="w-7 h-7 flex items-center justify-center text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 text-sm">&#10005;</button>
        </div>
        <div className="p-4 max-h-[50vh] overflow-y-auto space-y-1">
          {local.map((col, idx) => (
            <div
              key={col.key}
              draggable
              onDragStart={() => handleDragStart(idx)}
              onDragOver={(e) => handleDragOver(e, idx)}
              onDragEnd={handleDragEnd}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${
                dragIdx === idx ? 'border-blue-300 bg-blue-50' : 'border-gray-100 bg-white'
              } cursor-grab hover:bg-gray-50 transition-colors`}
            >
              <span className="text-gray-300 cursor-grab select-none">&#9776;</span>
              <input
                type="checkbox"
                checked={col.visible}
                onChange={() => toggleVisible(idx)}
                className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600"
              />
              <span className="text-[13px] text-gray-700 flex-1">{col.label}</span>
              <button type="button" onClick={() => moveUp(idx)} disabled={idx === 0}
                className="text-gray-300 hover:text-gray-500 text-[10px] disabled:opacity-30">&#9650;</button>
              <button type="button" onClick={() => moveDown(idx)} disabled={idx === local.length - 1}
                className="text-gray-300 hover:text-gray-500 text-[10px] disabled:opacity-30">&#9660;</button>
            </div>
          ))}
        </div>
        <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between">
          <button type="button" onClick={reset} className="text-[12px] text-gray-500 hover:text-gray-700 font-medium">초기화</button>
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="px-3 py-1.5 text-[12px] text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">취소</button>
            <button type="button" onClick={apply} className="px-4 py-1.5 text-[12px] bg-[#0071E3] text-white rounded-lg hover:bg-[#0066CC] font-medium transition-colors">적용</button>
          </div>
        </div>
      </div>
    </div>
  )
}
