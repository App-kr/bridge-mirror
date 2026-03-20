'use client'

import { useState, useCallback, useEffect } from 'react'
import { API_URL } from '@/lib/api'

const STORAGE_KEY = 'bridge_admin_key'
const EXPIRY_KEY = 'bridge_admin_key_expiry'
const KEY_TTL = 86400000 // 24시간 (ms)
const MAX_WAKE_RETRIES = 3
const WAKE_DELAY = 3000

/** localStorage에서 admin key 동기 로드 (만료 체크 포함) */
function getStoredKey(): string {
  if (typeof window === 'undefined') return ''
  const key = localStorage.getItem(STORAGE_KEY)
  const expiry = localStorage.getItem(EXPIRY_KEY)
  if (!key) return ''
  if (expiry && Date.now() > parseInt(expiry, 10)) {
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(EXPIRY_KEY)
    document.cookie = 'bridge_edit_mode=; path=/; max-age=0'
    return ''
  }
  return key
}

async function createHmacSignature(key: string, body: string): Promise<string> {
  const ts = Math.floor(Date.now() / 1000).toString()
  const payload = `${ts}.${body}`
  const enc = new TextEncoder()
  const cryptoKey = await crypto.subtle.importKey(
    'raw', enc.encode(key), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  )
  const sig = await crypto.subtle.sign('HMAC', cryptoKey, enc.encode(payload))
  const hex = Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('')
  return `t=${ts},v1=${hex}`
}

/** Render free tier wake-up: 재시도 래퍼 */
async function fetchWithWake(
  url: string,
  options?: RequestInit,
  onWaking?: (attempt: number) => void,
): Promise<Response> {
  for (let attempt = 1; attempt <= MAX_WAKE_RETRIES; attempt++) {
    try {
      const res = await fetch(url, options)
      return res
    } catch {
      if (attempt < MAX_WAKE_RETRIES) {
        onWaking?.(attempt)
        await new Promise(r => setTimeout(r, WAKE_DELAY))
      } else {
        throw new Error('서버 연결 실패. 잠시 후 다시 시도해주세요.')
      }
    }
  }
  throw new Error('서버 연결 실패')
}

export function useAdminAuth() {
  // 동기 초기화: localStorage에서 즉시 로드 (useEffect 지연 제거)
  const [adminKey, setAdminKey] = useState<string>(getStoredKey)
  const [authed, setAuthed] = useState<boolean>(() => !!getStoredKey())
  const [waking, setWaking] = useState(false)
  const [kakaoError, setKakaoError] = useState<string | null>(null)

  // 카카오 OAuth 콜백 처리: URL에 kakao_otc 또는 kakao_error 파라미터 확인
  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    const otc = params.get('kakao_otc')
    const err = params.get('kakao_error')

    // URL 파라미터 즉시 제거 (히스토리에 남지 않도록)
    if (otc || err) {
      window.history.replaceState({}, '', window.location.pathname)
    }

    if (err) {
      const msgs: Record<string, string> = {
        cancelled:      '카카오 로그인이 취소되었습니다.',
        not_configured: '카카오 로그인이 설정되지 않았습니다.',
        not_allowed:    '허가되지 않은 카카오 계정입니다.',
        token_failed:   '인증 토큰 발급에 실패했습니다.',
        network_error:  '카카오 서버 연결에 실패했습니다.',
      }
      setKakaoError(msgs[err] || '카카오 로그인 오류가 발생했습니다.')
      return
    }

    if (!otc) return

    // OTC → api_key 교환
    fetch(`${API_URL}/api/admin/kakao/exchange`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: otc }),
    })
      .then(r => r.json())
      .then(json => {
        const key = json?.data?.api_key
        if (key) {
          setAdminKey(key)
          setAuthed(true)
          localStorage.setItem(STORAGE_KEY, key)
          localStorage.setItem(EXPIRY_KEY, String(Date.now() + KEY_TTL))
          document.cookie = 'bridge_edit_mode=true; path=/; max-age=86400; SameSite=Lax'
        } else {
          setKakaoError('카카오 로그인 처리 중 오류가 발생했습니다.')
        }
      })
      .catch(() => setKakaoError('카카오 로그인 처리 중 오류가 발생했습니다.'))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /** 비밀번호로 서버 로그인 → API 키 받아서 저장 */
  const login = useCallback(async (password: string): Promise<string | null> => {
    setWaking(false)
    try {
      const res = await fetchWithWake(
        `${API_URL}/api/admin/login`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password }),
        },
        () => setWaking(true),
      )
      setWaking(false)

      if (res.status === 403) return '비밀번호가 올바르지 않습니다.'
      if (res.status === 429) return '로그인 시도가 너무 많습니다. 잠시 후 다시 시도해주세요.'
      if (!res.ok) return '서버 오류가 발생했습니다.'

      const json = await res.json()
      const key = json?.data?.api_key
      if (!key) return '서버 응답이 올바르지 않습니다.'

      setAdminKey(key)
      setAuthed(true)
      localStorage.setItem(STORAGE_KEY, key)
      localStorage.setItem(EXPIRY_KEY, String(Date.now() + KEY_TTL))
      document.cookie = 'bridge_edit_mode=true; path=/; max-age=86400; SameSite=Lax'

      // 로그인 성공 시 IP 블랙리스트 자동 초기화
      fetch(`${API_URL}/api/admin/reset-blacklist`, {
        method: 'POST',
        headers: { 'x-admin-key': key },
      }).catch(() => {})

      return null // 성공
    } catch (e) {
      setWaking(false)
      return e instanceof Error ? e.message : '로그인 실패'
    }
  }, [])

  const logout = useCallback(() => {
    setAdminKey('')
    setAuthed(false)
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(EXPIRY_KEY)
    document.cookie = 'bridge_edit_mode=; path=/; max-age=0'
  }, [])

  const headers = useCallback((): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (adminKey) h['x-admin-key'] = adminKey
    return h
  }, [adminKey])

  /** HMAC 서명 포함 fetch — POST/PUT/PATCH/DELETE 시 자동 서명 + Render wake-up */
  const signedFetch = useCallback(async (
    url: string,
    options?: RequestInit,
    onWaking?: (attempt: number) => void,
  ): Promise<Response> => {
    const method = (options?.method ?? 'GET').toUpperCase()
    const isFormData = typeof FormData !== 'undefined' && options?.body instanceof FormData
    const h: Record<string, string> = isFormData ? {} : { 'Content-Type': 'application/json' }
    if (adminKey) h['x-admin-key'] = adminKey

    if (method !== 'GET' && method !== 'HEAD' && adminKey) {
      const bodyStr = typeof options?.body === 'string' ? options.body : ''
      const sig = await createHmacSignature(adminKey, bodyStr)
      h['X-Bridge-Signature'] = sig
    }

    return fetchWithWake(
      url,
      { ...options, headers: { ...h, ...(options?.headers as Record<string, string> ?? {}) } },
      onWaking,
    )
  }, [adminKey])

  /** 일반 GET fetch + Render wake-up + 블랙리스트 403 자동 복구 */
  const adminFetch = useCallback(async (
    url: string,
    options?: RequestInit,
    onWaking?: (attempt: number) => void,
  ): Promise<Response> => {
    const h = { 'Content-Type': 'application/json', ...(adminKey ? { 'x-admin-key': adminKey } : {}) }
    const res = await fetchWithWake(
      url,
      { ...options, headers: { ...h, ...(options?.headers as Record<string, string> ?? {}) } },
      onWaking,
    )
    if (res.status === 403 && adminKey) {
      const body = await res.clone().json().catch(() => ({}))
      if (body.error && (body.error.includes('Access denied') || body.error.includes('access denied'))) {
        await fetch(`${API_URL}/api/admin/reset-blacklist`, {
          method: 'POST', headers: { 'x-admin-key': adminKey },
        }).catch(() => {})
        return fetchWithWake(
          url,
          { ...options, headers: { ...h, ...(options?.headers as Record<string, string> ?? {}) } },
          onWaking,
        )
      }
    }
    return res
  }, [adminKey])

  return { adminKey, authed, waking, kakaoError, login, logout, headers, signedFetch, adminFetch }
}
