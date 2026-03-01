'use client'

import { useState, useCallback, useEffect } from 'react'

const STORAGE_KEY = 'bridge_admin_key'

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

  return { adminKey, authed, login, logout, headers }
}
