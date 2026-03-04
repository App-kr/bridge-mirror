'use client'

/**
 * /admin — Dashboard (종합 현황)
 * 통합 통계 + 차트 + 기존 통계 카드 + 빠른 액션 + 최근 활동 피드
 */

import { useCallback, useEffect, useState } from 'react'
import dynamic from 'next/dynamic'
import AdminNav from '@/components/admin/AdminNav'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

// recharts dynamic import (SSR 비활성화)
const BarChart = dynamic(() => import('recharts').then(m => m.BarChart), { ssr: false })
const Bar = dynamic(() => import('recharts').then(m => m.Bar), { ssr: false })
const XAxis = dynamic(() => import('recharts').then(m => m.XAxis), { ssr: false })
const YAxis = dynamic(() => import('recharts').then(m => m.YAxis), { ssr: false })
const Tooltip = dynamic(() => import('recharts').then(m => m.Tooltip), { ssr: false })
const ResponsiveContainer = dynamic(() => import('recharts').then(m => m.ResponsiveContainer), { ssr: false })
const PieChart = dynamic(() => import('recharts').then(m => m.PieChart), { ssr: false })
const Pie = dynamic(() => import('recharts').then(m => m.Pie), { ssr: false })
const Cell = dynamic(() => import('recharts').then(m => m.Cell), { ssr: false })


const API = API_URL

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

interface InboxStats {
  total_candidates?: number
  new_candidates?: number
  this_month_candidates?: number
  last_month_candidates?: number
  total_inquiries?: number
  this_month_inquiries?: number
  active_jobs?: number
  community_posts?: number
  by_source?: Record<string, number>
  by_status?: Record<string, number>
}

interface MonthlyData {
  month: string
  label: string
  count: number
}

interface SourceData {
  source: string
  label: string
  count: number
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

const PIE_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']

export default function AdminDashboardPage() {
  const { authed, waking, login, adminFetch } = useAdminAuth()

  const [stats, setStats] = useState<DashboardStats>({})
  const [inboxStats, setInboxStats] = useState<InboxStats>({})
  const [monthly, setMonthly] = useState<MonthlyData[]>([])
  const [sources, setSources] = useState<SourceData[]>([])
  const [activity, setActivity] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [wakeMsg, setWakeMsg] = useState(false)

  const fetchAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    setWakeMsg(false)
    try {
      const onWaking = () => setWakeMsg(true)
      const [dashRes, statsRes, monthlyRes, sourceRes] = await Promise.all([
        adminFetch(`${API}/api/admin/dashboard`, undefined, onWaking),
        adminFetch(`${API}/api/admin/stats`, undefined, onWaking),
        adminFetch(`${API}/api/admin/stats/monthly`, undefined, onWaking),
        adminFetch(`${API}/api/admin/stats/by-source`, undefined, onWaking),
      ])
      setWakeMsg(false)

      if (dashRes.status === 403) {
        const errBody = await dashRes.json().catch(() => ({}))
        if (errBody.error?.includes?.('Access denied')) {
          setError('일시적으로 차단되었습니다. 자동 재시도 중...')
          const k = sessionStorage.getItem('bridge_admin_key') || ''
          await fetch(`${API}/api/admin/reset-blacklist`, { method: 'POST', headers: { 'x-admin-key': k } }).catch(() => {})
          setTimeout(() => window.location.reload(), 3000)
          return
        }
        setError('관리자 키가 올바르지 않습니다. 다시 로그인해주세요.')
        sessionStorage.removeItem('bridge_admin_key')
        return
      }

      const [dashJson, statsJson, monthlyJson, sourceJson] = await Promise.all([
        dashRes.json(), statsRes.json(), monthlyRes.json(), sourceRes.json(),
      ])

      if (dashJson.success) {
        setStats(dashJson.data?.stats ?? {})
        setActivity(dashJson.data?.recent_activity ?? [])
      }
      if (statsJson.success) setInboxStats(statsJson.data ?? {})
      if (monthlyJson.success) setMonthly(monthlyJson.data ?? [])
      if (sourceJson.success) setSources(sourceJson.data ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : '대시보드 로드 실패')
    } finally {
      setLoading(false)
      setWakeMsg(false)
    }
  }, [adminFetch])

  useEffect(() => {
    if (authed) fetchAll()
  }, [authed, fetchAll])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  const thisMonthDelta = (inboxStats.this_month_candidates ?? 0)
  const lastMonthDelta = (inboxStats.last_month_candidates ?? 0)
  const deltaSign = thisMonthDelta > lastMonthDelta ? '+' : ''
  const deltaValue = thisMonthDelta - lastMonthDelta

  const inboxCards = [
    { label: '총 지원', value: inboxStats.total_candidates ?? 0, sub: `이번달 +${thisMonthDelta}`, icon: '📋', color: 'text-blue-600' },
    { label: '신규 미처리', value: inboxStats.new_candidates ?? 0, sub: '', icon: '🟢', color: 'text-green-600' },
    { label: '이번달 이메일', value: thisMonthDelta, sub: `전월 대비 ${deltaSign}${deltaValue}`, icon: '📧', color: 'text-violet-600' },
    { label: '구인 문의', value: inboxStats.total_inquiries ?? 0, sub: `이번달 +${inboxStats.this_month_inquiries ?? 0}`, icon: '🏫', color: 'text-orange-600' },
    { label: '활성 구인', value: inboxStats.active_jobs ?? 0, sub: '', icon: '💼', color: 'text-emerald-600' },
    { label: '커뮤니티', value: inboxStats.community_posts ?? 0, sub: '', icon: '📝', color: 'text-gray-600' },
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
        <button type="button" onClick={fetchAll} className="text-sm text-blue-600 hover:underline">
          ↻ 새로고침
        </button>
      </div>

      {loading ? (
        <div className="text-center py-32 text-gray-400 animate-pulse">
          {wakeMsg ? '서버 깨우는 중... 잠시만 기다려주세요' : '대시보드 로딩 중…'}
        </div>
      ) : error ? (
        <div className="text-center py-32 space-y-4">
          <p className="text-red-500">{error}</p>
          <button type="button" className="btn-primary" onClick={fetchAll}>재시도</button>
        </div>
      ) : (
        <>
          {/* ── 통합 통계 카드 6개 ──────────────────────────────────────────── */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {inboxCards.map((c) => (
              <div key={c.label} className="card text-center">
                <div className="text-2xl mb-1">{c.icon}</div>
                <div className={`text-2xl font-bold ${c.color}`}>{c.value}</div>
                <div className="text-xs text-gray-500 mt-1">{c.label}</div>
                {c.sub && <div className="text-[10px] text-gray-400 mt-0.5">{c.sub}</div>}
              </div>
            ))}
          </div>

          {/* ── 차트 2개 ───────────────────────────────────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 월별 접수 추이 */}
            <div className="card">
              <h2 className="font-bold text-gray-900 mb-4">월별 접수 추이</h2>
              {monthly.length > 0 ? (
                <div style={{ width: '100%', height: 220 }}>
                  <ResponsiveContainer>
                    <BarChart data={monthly}>
                      <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} name="접수" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-gray-400 text-sm py-8 text-center">데이터 없음</p>
              )}
            </div>

            {/* 채널별 비율 */}
            <div className="card">
              <h2 className="font-bold text-gray-900 mb-4">채널별 비율</h2>
              {sources.length > 0 ? (
                <div className="flex items-center gap-4">
                  <div style={{ width: 180, height: 180 }}>
                    <ResponsiveContainer>
                      <PieChart>
                        <Pie
                          data={sources}
                          dataKey="count"
                          nameKey="label"
                          cx="50%"
                          cy="50%"
                          outerRadius={80}
                          innerRadius={40}
                        >
                          {sources.map((_, idx) => (
                            <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="space-y-2 text-sm">
                    {sources.map((s, idx) => (
                      <div key={s.source} className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full shrink-0"
                          style={{ backgroundColor: PIE_COLORS[idx % PIE_COLORS.length] }} />
                        <span className="text-gray-600">{s.label}</span>
                        <span className="font-medium text-gray-900">{s.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-gray-400 text-sm py-8 text-center">데이터 없음</p>
              )}
            </div>
          </div>

          {/* ── 빠른 액션 ──────────────────────────────────────────────────── */}
          <div className="flex gap-3 flex-wrap">
            <a href="/admin/inbox"
              className="px-4 py-2 rounded-full bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors">
              📧 수신함 열기
            </a>
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

          {/* ── 기존 하단: 최근 활동 + 현황 요약 ────────────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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
