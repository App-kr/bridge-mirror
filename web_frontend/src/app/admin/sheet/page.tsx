'use client'

import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import BridgeAdminSheet from '../components/BridgeAdminSheet'

export default function AdminSheetPage() {
  const { authed, login, waking } = useAdminAuth()

  if (!authed) {
    return <AdminAuth onLogin={login} waking={waking} />
  }

  return <BridgeAdminSheet />
}
