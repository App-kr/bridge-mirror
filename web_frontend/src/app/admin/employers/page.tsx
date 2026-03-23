'use client'

import { Component, type ReactNode } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import EmployerManagement from './EmployerManagement'

// ── Error Boundary: 런타임 에러 시 전체 크래시 방지 ──
class EmployerErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[employers] Error caught by boundary:', error, info)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, textAlign: 'center' }}>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: 12 }}>
            페이지 로드 중 오류가 발생했습니다
          </h2>
          <p style={{ color: '#666', marginBottom: 16, fontSize: '0.9rem' }}>
            {this.state.error?.message || '알 수 없는 오류'}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null })
              window.location.reload()
            }}
            style={{
              padding: '8px 24px',
              background: '#2563eb',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              fontSize: '0.9rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            새로고침
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

export default function AdminEmployersPage() {
  const { authed, login, waking } = useAdminAuth()

  if (!authed) {
    return <AdminAuth onLogin={login} waking={waking} />
  }

  return (
    <EmployerErrorBoundary>
      <EmployerManagement />
    </EmployerErrorBoundary>
  )
}
