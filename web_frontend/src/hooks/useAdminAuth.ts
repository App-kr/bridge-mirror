'use client'

import { useState, useCallback, useEffect } from 'react'
import { API_URL } from '@/lib/api'

const STORAGE_KEY = 'bridge_admin_key'
const MAX_WAKE_RETRIES = 3
const WAKE_DELAY = 3000

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
  const [adminKey, setAdminKey] = useState('')
  const [authed, setAuthed] = useState(false)
  const [waking, setWaking] = useState(false)

  // sessionStorage에서 복원
  useEffect(() => {
    const stored = sessionStorage.getItem(STORAGE_KEY)
    if (stored !== null) {
      setAdminKey(stored)
      setAuthed(true)
    }
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
      sessionStorage.setItem(STORAGE_KEY, key)
      return null // 성공
    } catch (e) {
      setWaking(false)
      return e instanceof Error ? e.message : '로그인 실패'
    }
  }, [])

  const logout = useCallback(() => {
    setAdminKey('')
    setAuthed(false)
    sessionStorage.removeItem(STORAGE_KEY)
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
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (adminKey) h['x-admin-key'] = adminKey

    if (method !== 'GET' && method !== 'HEAD' && adminKey) {
      const body = typeof options?.body === 'string' ? options.body : ''
      const sig = await createHmacSignature(adminKey, body)
      h['X-Bridge-Signature'] = sig
    }

    return fetchWithWake(
      url,
      { ...options, headers: { ...h, ...(options?.headers as Record<string, string> ?? {}) } },
      onWaking,
    )
  }, [adminKey])

  /** 일반 GET fetch + Render wake-up */
  const adminFetch = useCallback(async (
    url: string,
    options?: RequestInit,
    onWaking?: (attempt: number) => void,
  ): Promise<Response> => {
    const h = { 'Content-Type': 'application/json', ...(adminKey ? { 'x-admin-key': adminKey } : {}) }
    return fetchWithWake(
      url,
      { ...options, headers: { ...h, ...(options?.headers as Record<string, string> ?? {}) } },
      onWaking,
    )
  }, [adminKey])

  return { adminKey, authed, waking, login, logout, headers, signedFetch, adminFetch }
}
