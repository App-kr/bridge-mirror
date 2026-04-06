'use client'

/**
 * /talents/auth?token=XXX — Magic Link 콜백 페이지
 * URL 토큰 → /api/talent-auth/verify (Next.js route) → 쿠키 설정 → /talents 리다이렉트
 */

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense } from 'react'

function TalentsAuthInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying')
  const [message, setMessage] = useState('')

  useEffect(() => {
    const token = searchParams.get('token')
    if (!token) {
      setMessage('링크가 올바르지 않습니다.')
      setStatus('error')
      return
    }

    fetch('/api/talent-auth/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
      .then(async res => {
        const data = await res.json()
        if (data?.success) {
          setStatus('success')
          setTimeout(() => router.replace('/talents'), 800)
        } else {
          setMessage(data?.message || '링크가 유효하지 않습니다.')
          setStatus('error')
        }
      })
      .catch(() => {
        setMessage('서버에 연결할 수 없습니다.')
        setStatus('error')
      })
  }, [searchParams, router])

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 20,
    }}>
      <div style={{
        background: '#fff', borderRadius: 20, width: '100%', maxWidth: 380,
        padding: '40px 36px', boxShadow: '0 32px 80px rgba(0,0,0,0.5)',
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.5px', marginBottom: 28 }}>
          BRIDGE
        </div>

        {status === 'verifying' && (
          <>
            <div style={{
              width: 40, height: 40, border: '3px solid #E5E7EB',
              borderTop: '3px solid #111', borderRadius: '50%',
              margin: '0 auto 16px',
              animation: 'spin 0.8s linear infinite',
            }} />
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            <p style={{ color: '#6B7280', fontSize: 14 }}>인증 중입니다...</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div style={{
              width: 56, height: 56, borderRadius: '50%',
              background: '#F0FDF4', border: '2px solid #86EFAC',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 16px', fontSize: 26,
            }}>
              ✓
            </div>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 6 }}>인증 성공</h2>
            <p style={{ color: '#6B7280', fontSize: 13 }}>강사 게시판으로 이동합니다...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div style={{
              width: 56, height: 56, borderRadius: '50%',
              background: '#FEF2F2', border: '2px solid #FCA5A5',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 16px', fontSize: 26, color: '#DC2626',
            }}>
              ✕
            </div>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: '#DC2626' }}>
              인증 실패
            </h2>
            <p style={{ color: '#6B7280', fontSize: 14, lineHeight: 1.6, marginBottom: 24 }}>
              {message}
            </p>
            <button
              onClick={() => router.push('/talents/login')}
              style={{
                padding: '11px 28px', background: '#111', color: '#fff',
                border: 'none', borderRadius: 8, fontWeight: 600,
                fontSize: 14, cursor: 'pointer',
              }}
            >
              다시 요청하기
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default function TalentsAuthPage() {
  return (
    <Suspense fallback={
      <div style={{ minHeight: '100vh', background: '#0f172a', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: '#fff', fontSize: 14 }}>로딩 중...</div>
      </div>
    }>
      <TalentsAuthInner />
    </Suspense>
  )
}
