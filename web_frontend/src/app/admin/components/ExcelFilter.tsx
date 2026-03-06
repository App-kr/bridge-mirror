'use client'

import { useEffect, useRef, useState } from 'react'

interface ExcelFilterProps {
  label: string
  options: string[]
  selected: string[]
  onChange: (selected: string[]) => void
}

export default function ExcelFilter({ label, options, selected, onChange }: ExcelFilterProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const filtered = search
    ? options.filter(o => o.toLowerCase().includes(search.toLowerCase()))
    : options

  const allSelected = selected.length === 0
  const hasSelection = selected.length > 0

  const toggleAll = () => onChange([])

  const toggle = (val: string) => {
    if (allSelected) {
      onChange(options.filter(o => o !== val))
    } else if (selected.includes(val)) {
      const next = selected.filter(s => s !== val)
      if (next.length === 0) onChange([])
      else onChange(next)
    } else {
      onChange([...selected, val])
    }
  }

  const isChecked = (val: string) => allSelected || selected.includes(val)

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`flex items-center gap-1.5 px-3 py-2 text-[12px] border rounded-lg font-medium transition-colors whitespace-nowrap ${
          hasSelection
            ? 'bg-blue-50 border-blue-300 text-blue-700'
            : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
        }`}
      >
        <span>{label}</span>
        {hasSelection && (
          <span className="bg-blue-600 text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold">
            {selected.length}
          </span>
        )}
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className={`transition-transform ${open ? 'rotate-180' : ''}`}>
          <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-56 bg-white rounded-xl border border-gray-200 shadow-xl z-50 overflow-hidden">
          <div className="p-2 border-b border-gray-100">
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="검색..."
              className="w-full px-2.5 py-1.5 text-[12px] border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-400"
              autoFocus
            />
          </div>

          <div
            className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 cursor-pointer border-b border-gray-100"
            onClick={toggleAll}
          >
            <input type="checkbox" checked={allSelected} readOnly className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600" />
            <span className="text-[12px] font-semibold text-gray-700">전체선택</span>
          </div>

          <div className="max-h-48 overflow-y-auto">
            {filtered.map(opt => (
              <div
                key={opt}
                className="flex items-center gap-2 px-3 py-1.5 hover:bg-blue-50 cursor-pointer"
                onClick={() => toggle(opt)}
              >
                <input type="checkbox" checked={isChecked(opt)} readOnly className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600" />
                <span className="text-[12px] text-gray-700 truncate">{opt}</span>
              </div>
            ))}
            {filtered.length === 0 && (
              <div className="px-3 py-3 text-[12px] text-gray-400 text-center">결과 없음</div>
            )}
          </div>

          {hasSelection && (
            <div className="p-2 border-t border-gray-100">
              <button
                type="button"
                onClick={() => { onChange([]); setOpen(false) }}
                className="w-full text-[11px] text-red-500 hover:text-red-700 font-medium py-1"
              >
                필터 초기화
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
