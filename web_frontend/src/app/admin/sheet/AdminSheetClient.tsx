'use client'

import { useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import BridgeAdminSheet from '../components/BridgeAdminSheet'

/**
 * AdminSheetClient — 완전 클라이언트 전용 렌더링.
 * page.tsx에서 dynamic(..., { ssr: false })로 import → SSR 완전 차단.
 * hydration mismatch (React #418) 방지.
 */
export default function AdminSheetClient() {
  const { authed, login, waking } = useAdminAuth()
  const [mounted, setMounted] = useState(false)

  useEffect(() => { setMounted(true) }, [])

  if (!mounted) return null

  if (!authed) {
    return <AdminAuth onLogin={login} waking={waking} />
  }

  return <BridgeAdminSheet />
}
