'use client'

/**
 * TurnstileCaptcha.tsx — Cloudflare Turnstile widget wrapper.
 *
 * 무료 무제한 봇 검증. 대부분 invisible (사용자 화면에 퍼즐 거의 안 뜸).
 *
 * 활성화 조건: NEXT_PUBLIC_TURNSTILE_SITE_KEY 환경변수 설정.
 * 미설정 시 PuzzleCaptcha 컴포넌트가 자동 폴백 처리.
 */

import { useEffect, useRef, useId } from 'react'

interface TurnstileProps {
  siteKey: string
  onVerified: (token: string) => void
  onError?: (error: string) => void
}

declare global {
  interface Window {
    turnstile?: {
      render: (
        container: HTMLElement | string,
        opts: {
          sitekey: string
          callback: (token: string) => void
          'error-callback'?: (err: string) => void
          'expired-callback'?: () => void
          theme?: 'light' | 'dark' | 'auto'
          size?: 'normal' | 'compact' | 'invisible'
        },
      ) => string
      reset: (widgetId?: string) => void
      remove: (widgetId?: string) => void
    }
  }
}

const SCRIPT_SRC = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'

export default function TurnstileCaptcha({ siteKey, onVerified, onError }: TurnstileProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const widgetIdRef = useRef<string | null>(null)
  const reactId = useId()

  useEffect(() => {
    let cancelled = false
    let pollHandle: ReturnType<typeof setInterval> | null = null

    const renderWidget = () => {
      if (cancelled || !containerRef.current || !window.turnstile) return
      try {
        widgetIdRef.current = window.turnstile.render(containerRef.current, {
          sitekey: siteKey,
          theme: 'light',
          size: 'normal',
          callback: (token) => onVerified(token),
          'error-callback': (err) => onError?.(`Turnstile error: ${err}`),
          'expired-callback': () => onError?.('CAPTCHA expired. Please refresh.'),
        })
      } catch (e) {
        onError?.(`Turnstile init failed: ${e instanceof Error ? e.message : 'unknown'}`)
      }
    }

    const ensureScript = () => {
      if (window.turnstile) {
        renderWidget()
        return
      }
      // 이미 로드 중인 스크립트 있는지 확인
      const existing = document.querySelector<HTMLScriptElement>(`script[src^="${SCRIPT_SRC.split('?')[0]}"]`)
      if (existing) {
        pollHandle = setInterval(() => {
          if (window.turnstile) {
            if (pollHandle) clearInterval(pollHandle)
            renderWidget()
          }
        }, 100)
        return
      }
      const s = document.createElement('script')
      s.src = SCRIPT_SRC
      s.async = true
      s.defer = true
      s.onload = renderWidget
      s.onerror = () => onError?.('Turnstile script load failed')
      document.head.appendChild(s)
    }

    ensureScript()

    return () => {
      cancelled = true
      if (pollHandle) clearInterval(pollHandle)
      if (widgetIdRef.current && window.turnstile) {
        try { window.turnstile.remove(widgetIdRef.current) } catch { /* ignore */ }
      }
    }
    // siteKey 변경 시에만 재마운트 — onVerified/onError 변경은 무시 (재렌더 방지)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteKey])

  return (
    <div className="flex justify-center my-4">
      <div ref={containerRef} id={`turnstile-${reactId}`} />
    </div>
  )
}
