'use client'

import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import EmployerManagement from './EmployerManagement'

export default function AdminEmployersPage() {
  const { authed, login, waking } = useAdminAuth()

  if (!authed) {
    return <AdminAuth onLogin={login} waking={waking} />
  }

  return <EmployerManagement />
}
