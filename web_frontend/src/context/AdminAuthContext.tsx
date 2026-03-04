'use client'

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { API_URL } from '@/lib/api'

const MAX_WAKE_RETRIES = 3
const WAKE_DELAY = 3000
const STORAGE_KEY = 'bridge_admin_key'

async function createHmacSignature(key: string, body: string): Promise<string> {
  const ts = Math.floor(Date.now() / 1000).toString()
  const payload = `${ts}.${body}`
  const enc = new TextEncoder()
  const cryptoKey = await crypto.subtle.importKey(
    'raw', enc.encode(key), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'],
  )
  const sig = await crypto.subtle.sign('HMAC', cryptoKey, enc.encode(payload))
  const hex = Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('')
  return `t=${ts},v1=${hex}`
}

async function fetchWithWake(
  url: string,
  options?: RequestInit,
  onWaking?: (attempt: number) => void,
): Promise<Response> {
  for (let attempt = 1; attempt <= MAX_WAKE_RETRIES; attempt++) {
    try {
      return await fetch(url, options)
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

interface AdminAuthState {
  token: string
  isLoggedIn: boolean
  waking: boolean
  login: (password: string) => Promise<string | null>
  logout: () => void
  signedFetch: (url: string, options?: RequestInit, onWaking?: (a: number) => void) => Promise<Response>
  adminFetch: (url: string, options?: RequestInit, onWaking?: (a: number) => void) => Promise<Response>
}

const AdminAuthContext = createContext<AdminAuthState>({
  token: '',
  isLoggedIn: false,
  waking: false,
  login: async () => 'Not initialized',
  logout: () => {},
  signedFetch: () => Promise.reject('Not initialized'),
  adminFetch: () => Promise.reject('Not initialized'),
})

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string>(() => {
    if (typeof window === 'undefined') return ''
    return sessionStorage.getItem(STORAGE_KEY) ?? ''
  })
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return !!sessionStorage.getItem(STORAGE_KEY)
  })
  const [waking, setWaking] = useState(false)

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

      setToken(key)
      setIsLoggedIn(true)
      sessionStorage.setItem(STORAGE_KEY, key)
      return null
    } catch (e) {
      setWaking(false)
      return e instanceof Error ? e.message : '로그인 실패'
    }
  }, [])

  const logout = useCallback(() => {
    setToken('')
    setIsLoggedIn(false)
    sessionStorage.removeItem(STORAGE_KEY)
  }, [])

  const signedFetch = useCallback(async (
    url: string, options?: RequestInit, onWaking?: (a: number) => void,
  ): Promise<Response> => {
    const method = (options?.method ?? 'GET').toUpperCase()
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['x-admin-key'] = token

    if (method !== 'GET' && method !== 'HEAD' && token) {
      const body = typeof options?.body === 'string' ? options.body : ''
      const sig = await createHmacSignature(token, body)
      h['X-Bridge-Signature'] = sig
    }

    return fetchWithWake(
      url,
      { ...options, headers: { ...h, ...(options?.headers as Record<string, string> ?? {}) } },
      onWaking,
    )
  }, [token])

  const adminFetch = useCallback(async (
    url: string, options?: RequestInit, onWaking?: (a: number) => void,
  ): Promise<Response> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) h['x-admin-key'] = token
    return fetchWithWake(
      url,
      { ...options, headers: { ...h, ...(options?.headers as Record<string, string> ?? {}) } },
      onWaking,
    )
  }, [token])

  return (
    <AdminAuthContext.Provider value={{ token, isLoggedIn, waking, login, logout, signedFetch, adminFetch }}>
      {children}
    </AdminAuthContext.Provider>
  )
}

export function useAdminAuthContext() {
  return useContext(AdminAuthContext)
}

export default AdminAuthContext
