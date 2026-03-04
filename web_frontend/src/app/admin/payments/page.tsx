'use client'

/**
 * /admin/payments — Payment Management
 * 결제 기록 목록 + 상태 변경
 */

import { useCallback, useEffect, useState } from 'react'
import AdminNav from '@/components/admin/AdminNav'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'

import { API_URL } from '@/lib/api'

const API = API_URL

const PAYMENT_STATUS = ['pending', 'confirmed', 'refunded', 'cancelled'] as const

interface Payment {
  id: string
  inquiry_id: string
  school_name: string
  amount: number
  method: string
  status: string
  paid_at: string | null
  confirmed_at: string | null
  created_at: string
  memo: string | null
}

const statusColors: Record<string, string> = {
  pending:   'bg-yellow-50 text-yellow-700 border-yellow-200',
  confirmed: 'bg-green-50 text-green-700 border-green-200',
  refunded:  'bg-orange-50 text-orange-700 border-orange-200',
  cancelled: 'bg-red-50 text-red-700 border-red-200',
}

export default function AdminPaymentsPage() {
  const { authed, login, headers, waking } = useAdminAuth()

  const [payments, setPayments] = useState<Payment[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  const fetchPayments = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/payments`, { headers: headers() })
      if (res.status === 403) { setError('관리자 키가 올바르지 않습니다.'); return }
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Error')
      setPayments(json.data ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => {
    if (authed) fetchPayments()
  }, [authed, fetchPayments])

  const updateStatus = async (id: string, newStatus: string) => {
    try {
      const res = await fetch(`${API}/api/admin/payments/${id}`, {
        method: 'PATCH', headers: headers(),
        body: JSON.stringify({ status: newStatus }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`Payment ${id} → ${newStatus}`)
      fetchPayments()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  const filtered = statusFilter === 'all' ? payments : payments.filter((p) => p.status === statusFilter)
  const totalAmount = payments.filter((p) => p.status === 'confirmed').reduce((s, p) => s + (p.amount || 0), 0)

  return (
    <div className="space-y-6">
      <AdminNav active="/admin/payments" />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">결제 관리</h1>
          <p className="text-gray-500 text-sm">결제 기록 및 상태 관리</p>
        </div>
        <button type="button" onClick={fetchPayments} className="text-sm text-blue-600 hover:underline">↻ 새로고침</button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card text-center">
          <div className="text-2xl font-bold text-gray-900">{payments.length}</div>
          <div className="text-sm text-gray-500">전체</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-green-600">{payments.filter(p => p.status === 'confirmed').length}</div>
          <div className="text-sm text-gray-500">확인완료</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-yellow-600">{payments.filter(p => p.status === 'pending').length}</div>
          <div className="text-sm text-gray-500">대기중</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-blue-600">{totalAmount.toLocaleString()}원</div>
          <div className="text-sm text-gray-500">확인 합계</div>
        </div>
      </div>

      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        {['all', ...PAYMENT_STATUS].map((s) => (
          <button key={s} type="button" onClick={() => setStatusFilter(s)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              statusFilter === s ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}>
            {s === 'all' ? '전체' : s === 'confirmed' ? '확인완료' : s === 'pending' ? '대기' : s === 'refunded' ? '환불' : '취소'}
          </button>
        ))}
      </div>

      {actionMsg && (
        <div className="card-flat bg-blue-50 border-blue-200 text-sm text-blue-700 flex justify-between items-center">
          <span>{actionMsg}</span>
          <button type="button" onClick={() => setActionMsg(null)} className="text-blue-500">×</button>
        </div>
      )}

      {loading ? (
        <div className="text-center py-16 text-gray-400 animate-pulse">로딩 중...</div>
      ) : error ? (
        <div className="text-center py-16 text-red-500">{error}</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 space-y-3">
          <p className="text-gray-400">결제 기록이 없습니다.</p>
          <p className="text-xs text-gray-400">
            구인자 문의 접수 후 결제가 확인되면 여기에 표시됩니다.
            <br />향후 Stripe 결제 연동 예정
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((p) => (
            <div key={p.id} className="card !py-3 flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`badge text-[10px] border ${statusColors[p.status] ?? 'bg-gray-50 text-gray-600 border-gray-200'}`}>
                    {p.status}
                  </span>
                  <span className="font-semibold text-gray-900">{p.school_name || 'N/A'}</span>
                  <span className="text-sm font-bold text-blue-600">{(p.amount || 0).toLocaleString()}원</span>
                </div>
                <p className="text-xs text-gray-400">
                  {p.method || 'bank_transfer'}
                  {p.paid_at && ` · 입금: ${new Date(p.paid_at).toLocaleDateString('ko-KR')}`}
                  {' · '}등록: {new Date(p.created_at).toLocaleDateString('ko-KR')}
                  {p.memo && ` · ${p.memo}`}
                </p>
              </div>
              <select
                className="text-xs border border-gray-200 rounded px-2 py-1 bg-white text-gray-700"
                value={p.status}
                onChange={(e) => updateStatus(p.id, e.target.value)}
              >
                {PAYMENT_STATUS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
      )}

      <div className="text-center text-xs text-gray-400 border-t border-gray-100 pt-4">
        결제 수단: 무통장 입금 / PayPal · 향후 Stripe 연동 예정
      </div>
    </div>
  )
}
