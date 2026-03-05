'use client'

import { useEffect } from 'react'
import { usePathname } from 'next/navigation'

/**
 * 페이지 방문 추적 — referrer, UTM 파라미터, 검색어 자동 수집.
 * layout.tsx에 한 번 넣으면 모든 페이지 전환 시 자동 기록.
 */
export default function PageTracker() {
  const pathname = usePathname()

  useEffect(() => {
    // admin 페이지는 추적하지 않음
    if (pathname?.startsWith('/admin')) return

    // 세션 중 이미 첫 방문 기록했으면 referrer만 다시 보내지 않음
    // (SPA 내부 이동은 referrer가 자기 사이트이므로 의미 없음)
    const isFirstLoad = !sessionStorage.getItem('_bridge_tracked')

    const referrer = isFirstLoad ? document.referrer : ''
    const params = new URLSearchParams(window.location.search)

    // 첫 방문이거나 UTM 파라미터가 있을 때만 기록
    const hasUtm = params.has('utm_source') || params.has('utm_campaign') || params.has('utm_term')
    if (!isFirstLoad && !hasUtm) return

    const payload: Record<string, string> = {
      referrer,
      page: pathname || '/',
    }

    // UTM 파라미터 수집
    for (const key of ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term']) {
      const val = params.get(key)
      if (val) payload[key] = val
    }

    // 비동기 전송 (실패해도 무시)
    fetch('/api/track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).catch(() => {})

    sessionStorage.setItem('_bridge_tracked', '1')
  }, [pathname])

  return null
}
