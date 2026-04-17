'use client'

import { useEffect, useState } from 'react'
import dynamic from 'next/dynamic'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'

// Canvas/virtualizer 컴포넌트는 SSR 비활성화 (hydration mismatch #418 방지)
const BridgeAdminSheet = dynamic(
  () => import('../components/BridgeAdminSheet'),
  { ssr: false, loading: () => null }
)

export default function AdminSheetPage() {
  const { authed, login, waking } = useAdminAuth()
  const [mounted, setMounted] = useState(false)

  useEffect(() => { setMounted(true) }, [])

  // SSR과 클라이언트 첫 렌더 일치 → hydration mismatch(#418) 방지
  if (!mounted) return null

  if (!authed) {
    return <AdminAuth onLogin={login} waking={waking} />
  }

  return <BridgeAdminSheet />
}
