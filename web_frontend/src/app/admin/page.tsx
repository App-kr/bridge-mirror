'use client'

/**
 * /admin — Dashboard (종합 현황)
 * 통계 카드 + 빠른 액션 + 최근 활동 피드
 */

import { useCallback, useEffect, useState } from 'react'
import AdminNav from '@/components/admin/AdminNav'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface DashboardStats {
  candidates?: number
  candidates_active?: number
  interviews_scheduled?: number
  posts?: number
  ad_posts?: number
  payments_total?: number
  payments_confirmed?: number
  revenue?: number
}

interface ActivityItem {
  type: string
  id: number
  title?: string
  board?: string
  candidate_name?: string
  interview_date?: string
  interview_time?: string
  status?: string
  created_at?: string
}

export default function AdminDashboardPage() {
  const { authed, login, headers } = useAdminAuth()

  const [stats, setStats] = useState<DashboardStats>({})
  const [activity, setActivity] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchDashboard = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/dashboard`, { headers: headers() })
      const json = await res.json()
      if (res.status === 403) { setError('관리자 키가 올바르지 않습니다.'); return }
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Error')
      setStats(json.data?.stats ?? {})
      setActivity(json.data?.recent_activity ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : '대시보드 로드 실패')
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => {
    if (authed) fetchDashboard()
  }, [authed, fetchDashboard])

  if (!authed) return <AdminAuth onLogin={login} error={error} />

  const statCards = [
    { label: '교사 지원자', value: stats.candidates ?? 0, color: 'text-blue-600', icon: '👥' },
    { label: '대기 중 (Active)', value: stats.candidates_active ?? 0, color: 'text-emerald-600', icon: '⏳' },
    { label: '예정 인터뷰', value: stats.interviews_scheduled ?? 0, color: 'text-violet-600', icon: '🎥' },
    { label: '게시글', value: stats.posts ?? 0, color: 'text-orange-600', icon: '📝' },
    { label: '매출', value: `${((stats.revenue ?? 0) / 10000).toFixed(0)}만원`, color: 'text-green-600', icon: '💰' },
  ]

  return (
    <div className="space-y-8">
      <AdminNav active="/admin" />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-0.5">bridgejob.co.kr 운영 현황</p>
        </div>
        <button type="button" onClick={fetchDashboard} className="text-sm text-blue-600 hover:underline">
          ↻ 새로고침
        </button>
      </div>

      {loading ? (
        <div className="text-center py-32 text-gray-400 animate-pulse">대시보드 로딩 중…</div>
      ) : error ? (
        <div className="text-center py-32 space-y-4">
          <p className="text-red-500">{error}</p>
          <button type="button" className="btn-primary" onClick={fetchDashboard}>재시도</button>
        </div>
      ) : (
        <>
          {/* Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {statCards.map((s) => (
              <div key={s.label} className="card text-center">
                <div className="text-2xl mb-1">{s.icon}</div>
                <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
                <div className="text-xs text-gray-500 mt-1">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Quick Actions */}
          <div className="flex gap-3 flex-wrap">
            <a href="/admin/interviews"
              className="px-4 py-2 rounded-full bg-[#1d1d1f] text-white text-sm font-medium hover:bg-[#424245] transition-colors">
              + 인터뷰 예약
            </a>
            <a href="/admin/posts"
              className="px-4 py-2 rounded-full bg-[#1d1d1f] text-white text-sm font-medium hover:bg-[#424245] transition-colors">
              + 게시글 작성
            </a>
            <a href="/admin/candidates"
              className="px-4 py-2 rounded-full border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 transition-colors">
              지원자 보기
            </a>
            <a href="/admin/ad-posts"
              className="px-4 py-2 rounded-full border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 transition-colors">
              Ad Posts
            </a>
          </div>

          {/* Two-column layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Recent Activity */}
            <div className="lg:col-span-2 card">
              <h2 className="font-bold text-gray-900 mb-4">최근 활동</h2>
              {activity.length === 0 ? (
                <p className="text-gray-400 text-sm py-8 text-center">최근 활동이 없습니다.</p>
              ) : (
                <div className="space-y-3">
                  {activity.map((item, idx) => (
                    <div key={`${item.type}-${item.id}-${idx}`}
                      className="flex items-start gap-3 py-2 border-b border-gray-50 last:border-0">
                      <span className="text-lg shrink-0">
                        {item.type === 'post' ? '📝' : '🎥'}
                      </span>
                      <div className="flex-1 min-w-0">
                        {item.type === 'post' ? (
                          <>
                            <p className="text-sm font-medium text-gray-900 truncate">{item.title}</p>
                            <p className="text-xs text-gray-400">
                              {item.board} · {item.created_at ? new Date(item.created_at).toLocaleDateString('ko-KR') : '—'}
                            </p>
                          </>
                        ) : (
                          <>
                            <p className="text-sm font-medium text-gray-900">
                              인터뷰: {item.candidate_name || 'N/A'}
                            </p>
                            <p className="text-xs text-gray-400">
                              {item.interview_date} {item.interview_time}
                              {item.status && ` · ${item.status}`}
                            </p>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Status Summary */}
            <div className="card">
              <h2 className="font-bold text-gray-900 mb-4">현황 요약</h2>
              <div className="space-y-4">
                <SummaryRow label="Ad Posts" value={stats.ad_posts ?? 0} color="bg-blue-500" />
                <SummaryRow label="결제 전체" value={stats.payments_total ?? 0} color="bg-gray-400" />
                <SummaryRow label="결제 확인" value={stats.payments_confirmed ?? 0} color="bg-green-500" />
                <SummaryRow label="인터뷰 예정" value={stats.interviews_scheduled ?? 0} color="bg-violet-500" />
                <SummaryRow label="게시글" value={stats.posts ?? 0} color="bg-orange-500" />
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function SummaryRow({ label, value, color }: { label: string; value: number; color: string }) {
  const max = Math.max(value, 1)
  const width = Math.min((value / max) * 100, 100)
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium text-gray-900">{value}</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${width}%` }} />
      </div>
    </div>
  )
}
