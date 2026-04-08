'use client'

import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'

export default function ESLCafePage() {
  const { authed, login, waking } = useAdminAuth()

  if (!authed) {
    return <AdminAuth onLogin={login} waking={waking} />
  }

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 10 }}>
      <iframe
        src="/eslcafe.html"
        style={{ width: '100%', height: '100%', border: 'none', display: 'block' }}
        title="BRIDGE ESLCafe Ad Manager"
        allow="clipboard-write"
      />
    </div>
  )
}
