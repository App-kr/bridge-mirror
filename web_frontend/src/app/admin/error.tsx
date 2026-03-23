'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function AdminError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  const router = useRouter()

  useEffect(() => {
    console.error('[Admin Error Boundary]', error)
  }, [error])

  return (
    <div className="flex items-center justify-center h-full min-h-[400px]">
      <div className="text-center max-w-md mx-auto px-6">
        <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center mx-auto mb-4">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <h2 className="text-[18px] font-bold text-[#1d1d1f] mb-2">
          페이지 오류
        </h2>
        <p className="text-[13px] text-[#86868b] mb-6 leading-relaxed">
          이 페이지에서 오류가 발생했습니다.
          <br />
          다시 시도하거나 대시보드로 돌아가세요.
        </p>
        <div className="flex gap-3 justify-center">
          <button
            type="button"
            onClick={reset}
            className="px-5 py-2.5 bg-[#0071e3] text-white text-[13px] font-semibold rounded-xl hover:bg-[#0077ed] transition-colors"
          >
            다시 시도
          </button>
          <button
            type="button"
            onClick={() => router.push('/admin')}
            className="px-5 py-2.5 bg-[#f5f5f7] text-[#1d1d1f] text-[13px] font-semibold rounded-xl hover:bg-[#e8e8ed] transition-colors"
          >
            대시보드로
          </button>
        </div>
      </div>
    </div>
  )
}
