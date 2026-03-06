'use client'

import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import EmployerManagement from '../components/EmployerManagement'

export default function AdminEmployerPage() {
  const { authed, login, waking } = useAdminAuth()

  if (!authed) {
    return <AdminAuth onLogin={login} waking={waking} />
  }

  return <EmployerManagement />
}
