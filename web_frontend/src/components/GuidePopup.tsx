'use client'

import { useEffect, useState } from 'react'

interface GuidePopupProps {
  storageKey: string
  title: string
  items: string[]
  cta?: string
}

export default function GuidePopup({ storageKey, title, items, cta = 'Got it' }: GuidePopupProps) {
  const [show, setShow] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem(storageKey)) setShow(true)
  }, [storageKey])

  if (!show) return null

  const dismiss = () => {
    localStorage.setItem(storageKey, '1')
    setShow(false)
  }

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40 p-4" onClick={dismiss}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 pt-6 pb-4">
          <h2 className="text-lg font-bold text-[#1d1d1f] mb-4">{title}</h2>
          <ul className="space-y-2.5">
            {items.map((item, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm text-[#424245] leading-relaxed">
                <span className="shrink-0 w-5 h-5 rounded-full bg-[#0071e3]/10 text-[#0071e3] text-[11px] font-bold flex items-center justify-center mt-0.5">
                  {i + 1}
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="px-6 pb-6 pt-2">
          <button
            type="button"
            onClick={dismiss}
            className="w-full py-3 bg-[#0071e3] text-white text-sm font-semibold rounded-xl hover:bg-[#0077ED] transition-colors"
          >
            {cta}
          </button>
        </div>
      </div>
    </div>
  )
}
