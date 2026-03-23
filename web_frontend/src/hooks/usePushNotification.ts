'use client'

import { useState, useCallback, useEffect } from 'react'
import { API_URL } from '@/lib/api'

type PushState = 'loading' | 'unsupported' | 'denied' | 'prompt' | 'subscribed' | 'unsubscribed'

export function usePushNotification(adminKey: string) {
  const [state, setState] = useState<PushState>('loading')
  const [error, setError] = useState<string | null>(null)

  // Check current permission state on mount
  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator) || !('PushManager' in window)) {
      setState('unsupported')
      return
    }
    const perm = Notification.permission
    if (perm === 'denied') {
      setState('denied')
      return
    }

    // Check if already subscribed
    navigator.serviceWorker.ready.then(reg => {
      reg.pushManager.getSubscription().then(sub => {
        setState(sub ? 'subscribed' : (perm === 'granted' ? 'unsubscribed' : 'prompt'))
      })
    }).catch(() => setState('prompt'))
  }, [])

  const subscribe = useCallback(async () => {
    setError(null)
    try {
      // 1. Get VAPID public key from server
      const vapidRes = await fetch(`${API_URL}/api/admin/push/vapid-key`)
      const vapidJson = await vapidRes.json()
      if (!vapidJson.success) throw new Error('VAPID key not available')
      const publicKey = vapidJson.data.publicKey

      // 2. Convert base64url to Uint8Array
      const padding = '='.repeat((4 - publicKey.length % 4) % 4)
      const b64 = (publicKey + padding).replace(/-/g, '+').replace(/_/g, '/')
      const raw = atob(b64)
      const applicationServerKey = new Uint8Array(raw.length)
      for (let i = 0; i < raw.length; i++) applicationServerKey[i] = raw.charCodeAt(i)

      // 3. Subscribe via Push API
      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey,
      })

      // 4. Send subscription to server
      const subJson = sub.toJSON()
      const res = await fetch(`${API_URL}/api/admin/push/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-admin-key': adminKey,
        },
        body: JSON.stringify({
          endpoint: subJson.endpoint,
          keys: subJson.keys,
        }),
      })

      if (!res.ok) throw new Error('Server subscription failed')
      setState('subscribed')
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Subscription failed'
      setError(msg)
      if (Notification.permission === 'denied') setState('denied')
    }
  }, [adminKey])

  const unsubscribe = useCallback(async () => {
    setError(null)
    try {
      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.getSubscription()
      if (sub) {
        const endpoint = sub.endpoint
        await sub.unsubscribe()
        // Notify server
        await fetch(`${API_URL}/api/admin/push/unsubscribe`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            'x-admin-key': adminKey,
          },
          body: JSON.stringify({ endpoint }),
        }).catch(() => {})
      }
      setState('unsubscribed')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unsubscribe failed')
    }
  }, [adminKey])

  const testPush = useCallback(async () => {
    setError(null)
    try {
      const res = await fetch(`${API_URL}/api/admin/push/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-admin-key': adminKey,
        },
      })
      const json = await res.json()
      if (!json.success) throw new Error(json.message || 'Test failed')
      return json.data?.sent ?? 0
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Test push failed')
      return 0
    }
  }, [adminKey])

  return { state, error, subscribe, unsubscribe, testPush }
}
