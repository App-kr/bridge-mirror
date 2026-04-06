'use client'

/**
 * /admin/talent-auth — 인재 게시판 접근 요청 관리
 * 요청 목록 조회 + 매직 링크 발송 + 직접 이메일 발송
 */

import { useEffect, useState } from 'react'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import AdminAuth from '@/components/admin/AdminAuth'
import { API_URL } from '@/lib/api'

interface AuthRequest {
  id: number
  email: string
  company_name: string
  requested_at: string
  status: string
  sent_at: string | null
  notes: string
}

const STATUS_LABEL: Record<string, { label: string; color: string }> = {
  pending:  { label: '대기중', color: '#F59E0B' },
  sent:     { label: '발송됨', color: '#3B82F6' },
  approved: { label: '승인됨', color: '#10B981' },
  rejected: { label: '거부됨', color: '#EF4444' },
}

export default function TalentAuthPage() {
  const { authed, login, waking } = useAdminAuth()
  if (!authed) return <AdminAuth onLogin={login} waking={waking} />
  return <TalentAuthContent />
}

function TalentAuthContent() {
  const { adminFetch } = useAdminAuth()
  const [requests, setRequests] = useState<AuthRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [sendingId, setSendingId] = useState<number | null>(null)
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null)

  // 직접 발송 폼
  const [directEmail, setDirectEmail] = useState('')
  const [sendingDirect, setSendingDirect] = useState(false)

  function showToast(msg: string, ok = true) {
    setToast({ msg, ok })
    setTimeout(() => setToast(null), 3500)
  }

  async function loadRequests() {
    setLoading(true)
    try {
      const res = await adminFetch(`${API_URL}/api/admin/talent-auth/requests`)
      const data = await res.json()
      setRequests(data?.data ?? [])
    } catch {
      showToast('목록을 불러오지 못했습니다.', false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadRequests() }, [])

  async function handleSendLink(req: AuthRequest) {
    if (!confirm(`${req.email} 에 매직 링크를 발송할까요?`)) return
    setSendingId(req.id)
    try {
      const res = await adminFetch(`${API_URL}/api/admin/talent-auth/send-link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_id: req.id }),
      })
      const data = await res.json()
      if (res.ok) {
        showToast(data?.message || '발송 완료')
        loadRequests()
      } else {
        showToast(data?.detail || '발송 실패', false)
      }
    } catch {
      showToast('서버 오류', false)
    } finally {
      setSendingId(null)
    }
  }

  async function handleSendDirect() {
    if (!directEmail.trim()) return
    if (!confirm(`${directEmail} 에 매직 링크를 발송할까요?`)) return
    setSendingDirect(true)
    try {
      const res = await adminFetch(`${API_URL}/api/admin/talent-auth/send-link-direct`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: directEmail.trim() }),
      })
      const data = await res.json()
      if (res.ok) {
        showToast(data?.message || '발송 완료')
        setDirectEmail('')
      } else {
        showToast(data?.detail || '발송 실패', false)
      }
    } catch {
      showToast('서버 오류', false)
    } finally {
      setSendingDirect(false)
    }
  }

  async function handleRevoke(email: string) {
    if (!confirm(`${email} 의 세션을 취소할까요?\n다음 접속 시 새 링크 필요.`)) return
    try {
      const res = await adminFetch(
        `${API_URL}/api/admin/talent-auth/sessions/${encodeURIComponent(email)}`,
        { method: 'DELETE' }
      )
      const data = await res.json()
      showToast(data?.message || '취소 완료', res.ok)
    } catch {
      showToast('서버 오류', false)
    }
  }

  const fmt = (s: string | null) => s ? new Date(s).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '28px 20px' }}>
      <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>강사 게시판 접근 관리</h1>
      <p style={{ color: '#6B7280', fontSize: 13, marginBottom: 28 }}>
        요청 검토 후 매직 링크를 발송하세요. 링크는 15분 유효, 세션은 30일.
      </p>

      {/* 직접 발송 박스 */}
      <div style={{
        background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: 12,
        padding: '18px 20px', marginBottom: 28, display: 'flex', gap: 10, alignItems: 'flex-end',
        flexWrap: 'wrap',
      }}>
        <div style={{ flex: '1 1 260px' }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 5 }}>
            직접 이메일 발송 (요청 없이도 가능)
          </label>
          <input
            type="email"
            placeholder="recipient@school.com"
            value={directEmail}
            onChange={e => setDirectEmail(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSendDirect()}
            style={{
              width: '100%', padding: '9px 12px', border: '1px solid #D1D5DB',
              borderRadius: 8, fontSize: 14, outline: 'none', boxSizing: 'border-box',
            }}
          />
        </div>
        <button
          onClick={handleSendDirect}
          disabled={sendingDirect || !directEmail.trim()}
          style={{
            padding: '9px 20px', background: '#111', color: '#fff', border: 'none',
            borderRadius: 8, fontWeight: 600, fontSize: 13,
            cursor: sendingDirect || !directEmail.trim() ? 'not-allowed' : 'pointer',
            opacity: sendingDirect || !directEmail.trim() ? 0.6 : 1,
            whiteSpace: 'nowrap',
          }}
        >
          {sendingDirect ? '발송 중...' : '링크 발송'}
        </button>
      </div>

      {/* 요청 목록 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700 }}>접근 요청 목록 ({requests.length})</h2>
        <button
          onClick={loadRequests}
          style={{
            padding: '6px 14px', background: '#F3F4F6', border: '1px solid #D1D5DB',
            borderRadius: 7, fontSize: 12, cursor: 'pointer', color: '#374151',
          }}
        >
          새로고침
        </button>
      </div>

      {loading ? (
        <div style={{ padding: '40px 0', textAlign: 'center', color: '#9CA3AF', fontSize: 14 }}>
          로딩 중...
        </div>
      ) : requests.length === 0 ? (
        <div style={{ padding: '40px 0', textAlign: 'center', color: '#9CA3AF', fontSize: 14 }}>
          접근 요청이 없습니다.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {requests.map(req => {
            const st = STATUS_LABEL[req.status] ?? { label: req.status, color: '#6B7280' }
            const isPending = req.status === 'pending'
            return (
              <div key={req.id} style={{
                background: '#fff', border: '1px solid #E5E7EB', borderRadius: 12,
                padding: '16px 18px', display: 'flex', gap: 14,
                alignItems: 'center', flexWrap: 'wrap',
                borderLeft: isPending ? '3px solid #F59E0B' : '3px solid #E5E7EB',
              }}>
                {/* 상태 배지 */}
                <span style={{
                  fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
                  background: st.color + '18', color: st.color, whiteSpace: 'nowrap',
                }}>
                  {st.label}
                </span>

                {/* 이메일 + 업체 */}
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{req.email}</div>
                  {req.company_name && (
                    <div style={{ color: '#6B7280', fontSize: 12, marginTop: 2 }}>{req.company_name}</div>
                  )}
                </div>

                {/* 시간 */}
                <div style={{ color: '#9CA3AF', fontSize: 12, whiteSpace: 'nowrap' }}>
                  요청: {fmt(req.requested_at)}
                  {req.sent_at && <span style={{ display: 'block' }}>발송: {fmt(req.sent_at)}</span>}
                </div>

                {/* 액션 버튼 */}
                <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                  <button
                    onClick={() => handleSendLink(req)}
                    disabled={sendingId === req.id}
                    style={{
                      padding: '7px 14px', background: '#111', color: '#fff',
                      border: 'none', borderRadius: 7, fontWeight: 600,
                      fontSize: 12, cursor: sendingId === req.id ? 'not-allowed' : 'pointer',
                      opacity: sendingId === req.id ? 0.6 : 1, whiteSpace: 'nowrap',
                    }}
                  >
                    {sendingId === req.id ? '발송중...' : '링크 발송'}
                  </button>
                  <button
                    onClick={() => handleRevoke(req.email)}
                    style={{
                      padding: '7px 14px', background: '#FEF2F2', color: '#DC2626',
                      border: '1px solid #FECACA', borderRadius: 7, fontWeight: 600,
                      fontSize: 12, cursor: 'pointer', whiteSpace: 'nowrap',
                    }}
                  >
                    세션 취소
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* 토스트 */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
          background: toast.ok ? '#111' : '#DC2626', color: '#fff',
          padding: '12px 20px', borderRadius: 10, fontSize: 14, fontWeight: 600,
          boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
          animation: 'fadeIn 0.2s ease',
        }}>
          {toast.msg}
        </div>
      )}
      <style>{`@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }`}</style>
    </div>
  )
}
