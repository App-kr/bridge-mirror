'use client'

import { useState, useCallback, useEffect } from 'react'

const STORAGE_KEY = 'bridge_admin_key'

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

export function useAdminAuth() {
  const [adminKey, setAdminKey] = useState('')
  const [authed, setAuthed] = useState(false)

  // sessionStorage에서 복원
  useEffect(() => {
    const stored = sessionStorage.getItem(STORAGE_KEY)
    if (stored !== null) {
      setAdminKey(stored)
      setAuthed(true)
    }
  }, [])

  const login = useCallback((key: string) => {
    setAdminKey(key)
    setAuthed(true)
    sessionStorage.setItem(STORAGE_KEY, key)
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

  /** HMAC 서명 포함 fetch — POST/PUT/PATCH/DELETE 시 자동 서명 */
  const signedFetch = useCallback(async (url: string, options?: RequestInit): Promise<Response> => {
    const method = (options?.method ?? 'GET').toUpperCase()
    const h: Record<string, string> = { 'Content-Type': 'application/json' }
    if (adminKey) h['x-admin-key'] = adminKey

    if (method !== 'GET' && method !== 'HEAD' && adminKey) {
      const body = typeof options?.body === 'string' ? options.body : ''
      const sig = await createHmacSignature(adminKey, body)
      h['X-Bridge-Signature'] = sig
    }

    return fetch(url, { ...options, headers: { ...h, ...(options?.headers as Record<string, string> ?? {}) } })
  }, [adminKey])

  return { adminKey, authed, login, logout, headers, signedFetch }
}
