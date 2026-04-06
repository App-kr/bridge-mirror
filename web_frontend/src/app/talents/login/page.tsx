'use client'

/**
 * /talents/login — 인재 게시판 접근 요청 페이지
 * 이메일 입력 → 담당자 검토 → Magic Link 이메일 발송
 */

import { useState } from 'react'
import { API_URL } from '@/lib/api'

export default function TalentsLoginPage() {
  const [email, setEmail] = useState('')
  const [company, setCompany] = useState('')
  const [status, setStatus] = useState<'idle' | 'sending' | 'done' | 'error'>('idle')
  const [message, setMessage] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim()) return
    setStatus('sending')
    try {
      const res = await fetch(`${API_URL}/api/public/talent-auth/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), company_name: company.trim() }),
      })
      const data = await res.json()
      if (!res.ok) {
        setMessage(data?.detail || '오류가 발생했습니다.')
        setStatus('error')
      } else {
        setMessage(data?.message || '요청이 접수되었습니다.')
        setStatus('done')
      }
    } catch {
      setMessage('서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.')
      setStatus('error')
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 20,
    }}>
      <div style={{
        background: '#fff', borderRadius: 20, width: '100%', maxWidth: 420,
        padding: '40px 36px', boxShadow: '0 32px 80px rgba(0,0,0,0.5)',
      }}>
        {/* 로고 */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.5px' }}>BRIDGE</div>
          <div style={{ fontSize: 13, color: '#6B7280', marginTop: 4 }}>Teacher Board</div>
        </div>

        {status === 'done' ? (
          /* 완료 상태 */
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: 56, height: 56, borderRadius: '50%',
              background: '#F0FDF4', border: '2px solid #86EFAC',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 16px', fontSize: 24,
            }}>
              ✓
            </div>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>요청이 접수되었습니다</h2>
            <p style={{ color: '#6B7280', fontSize: 14, lineHeight: 1.6 }}>
              {message || '담당자 확인 후 입력하신 이메일로 접속 링크를 보내드립니다.'}
            </p>
            <p style={{ color: '#9CA3AF', fontSize: 12, marginTop: 16 }}>
              링크 발송까지 영업일 기준 1~2일 소요될 수 있습니다.
            </p>
          </div>
        ) : (
          /* 입력 폼 */
          <>
            <h1 style={{ fontSize: 19, fontWeight: 700, marginBottom: 6 }}>접근 요청</h1>
            <p style={{ color: '#6B7280', fontSize: 13, lineHeight: 1.6, marginBottom: 24 }}>
              학교·학원 담당자 전용 페이지입니다.<br />
              이메일 주소를 입력하시면 담당자 확인 후 접속 링크를 보내드립니다.
            </p>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, color: '#374151', fontWeight: 600, display: 'block', marginBottom: 5 }}>
                  이메일 주소 *
                </label>
                <input
                  type="email"
                  required
                  placeholder="school@example.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  style={inputStyle}
                  disabled={status === 'sending'}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, color: '#374151', fontWeight: 600, display: 'block', marginBottom: 5 }}>
                  학교 / 기관명
                </label>
                <input
                  type="text"
                  placeholder="OO초등학교 / OO어학원"
                  value={company}
                  onChange={e => setCompany(e.target.value)}
                  style={inputStyle}
                  disabled={status === 'sending'}
                />
              </div>

              {status === 'error' && (
                <p style={{ color: '#DC2626', fontSize: 13, margin: '4px 0' }}>
                  {message}
                </p>
              )}

              <button
                type="submit"
                disabled={status === 'sending' || !email.trim()}
                style={{
                  padding: '13px 0', background: '#111', color: '#fff',
                  border: 'none', borderRadius: 10, fontWeight: 700,
                  fontSize: 15, cursor: status === 'sending' || !email.trim() ? 'not-allowed' : 'pointer',
                  opacity: status === 'sending' || !email.trim() ? 0.6 : 1,
                  marginTop: 8, transition: 'opacity 0.15s',
                }}
              >
                {status === 'sending' ? '처리 중...' : '접근 요청하기'}
              </button>
            </form>

            <p style={{ fontSize: 11, color: '#9CA3AF', textAlign: 'center', marginTop: 20 }}>
              채용 목적 외 무단 접근은 법적 책임이 따를 수 있습니다.
            </p>
          </>
        )}
      </div>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '11px 13px', border: '1px solid #D1D5DB',
  borderRadius: 8, fontSize: 14, outline: 'none', boxSizing: 'border-box',
  transition: 'border-color 0.15s',
}
