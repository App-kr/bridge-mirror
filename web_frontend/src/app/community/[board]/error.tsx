'use client'

/**
 * Community board error boundary — catches client-side render exceptions
 * and shows a friendly recovery UI instead of the generic "Application error" page.
 */

import { useEffect } from 'react'
import Link from 'next/link'

export default function BoardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log to console for debugging without exposing to users
    console.error('[Community Board Error]', error)
  }, [error])

  return (
    <div className="max-w-2xl mx-auto px-4 py-24 text-center">
      <p className="text-4xl mb-4">😕</p>
      <h2 className="text-xl font-bold text-[#1d1d1f] mb-2">
        Something went wrong
      </h2>
      <p className="text-[#86868b] text-sm mb-8">
        This page ran into an unexpected error. Try refreshing or come back later.
      </p>
      <div className="flex items-center justify-center gap-3">
        <button
          type="button"
          onClick={reset}
          className="px-5 py-2 bg-[#0071e3] text-white text-sm font-medium rounded-full hover:bg-[#0077ED] transition-colors"
        >
          Try again
        </button>
        <Link
          href="/community"
          className="px-5 py-2 bg-[#f5f5f7] text-[#1d1d1f] text-sm font-medium rounded-full hover:bg-[#e5e5ea] transition-colors"
        >
          Back to Community
        </Link>
      </div>
    </div>
  )
}
