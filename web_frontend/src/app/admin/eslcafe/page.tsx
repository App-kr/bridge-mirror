'use client'

import AdminAuth from '@/components/admin/AdminAuth'

export default function ESLCafePage() {
  return (
    <AdminAuth>
      <div style={{ position: 'fixed', inset: 0, zIndex: 10 }}>
        <iframe
          src="/eslcafe.html"
          style={{ width: '100%', height: '100%', border: 'none', display: 'block' }}
          title="BRIDGE ESLCafe Ad Manager"
          allow="clipboard-write"
        />
      </div>
    </AdminAuth>
  )
}
