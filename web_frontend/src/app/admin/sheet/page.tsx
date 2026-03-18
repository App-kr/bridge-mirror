'use client'

import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import BridgeCanvasSheet from './BridgeCanvasSheet'

export default function AdminSheetPage() {
  const { authed, login, waking } = useAdminAuth()

  if (!authed) {
    return <AdminAuth onLogin={login} waking={waking} />
  }

  return <BridgeCanvasSheet />
}
