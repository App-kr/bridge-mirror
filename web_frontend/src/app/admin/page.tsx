'use client'

/**
 * /admin — Dashboard (종합 현황)
 * Apple 2026 미니멀: 최근 게시물 테이블 → 통계 카드 → 차트 → 노출 비중
 */

import { useCallback, useEffect, useState } from 'react'
import dynamic from 'next/dynamic'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

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

const EXPOSURE_DATA = [
  { channel: 'Google', pct: 42 },
  { channel: 'Naver', pct: 28 },
  { channel: 'Reddit', pct: 14 },
  { channel: 'Direct', pct: 9 },
  { channel: 'Craigslist', pct: 7 },
]

const boardLabel = (b: string) => {
  const map: Record<string, string> = {
    visa: 'Visa', support: 'Support(EN)', support_kr: '업무지원',
    about: 'About', korea: 'Korea', tips: 'Tips',
    testimonials: 'Testimonials', information: 'Information',
  }
  return map[b] ?? b
}

const boardColor = (b: string) => {
  const map: Record<string, string> = {
    visa: 'bg-emerald-50 text-emerald-700',
    support: 'bg-blue-50 text-blue-700',
    support_kr: 'bg-orange-50 text-orange-700',
    about: 'bg-violet-50 text-violet-700',
    korea: 'bg-rose-50 text-rose-700',
    tips: 'bg-amber-50 text-amber-700',
    testimonials: 'bg-cyan-50 text-cyan-700',
    information: 'bg-gray-100 text-gray-700',
  }
  return map[b] ?? 'bg-gray-100 text-gray-600'
}

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

  const thisMonthDelta = inboxStats.this_month_candidates ?? 0
  const lastMonthDelta = inboxStats.last_month_candidates ?? 0
  const deltaSign = thisMonthDelta > lastMonthDelta ? '+' : ''
  const deltaValue = thisMonthDelta - lastMonthDelta

  const statCards = [
    { label: '총 지원', value: inboxStats.total_candidates ?? 0, sub: `이번달 +${thisMonthDelta}` },
    { label: '신규 미처리', value: inboxStats.new_candidates ?? 0, sub: '' },
    { label: '이번달 유입', value: thisMonthDelta, sub: `전월 대비 ${deltaSign}${deltaValue}` },
    { label: '구인 문의', value: inboxStats.total_inquiries ?? 0, sub: `이번달 +${inboxStats.this_month_inquiries ?? 0}` },
    { label: '활성 구인', value: inboxStats.active_jobs ?? 0, sub: '' },
    { label: '커뮤니티', value: inboxStats.community_posts ?? 0, sub: '' },
  ]

  const recentPosts = activity.filter(a => a.type === 'post').slice(0, 10)

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#1d1d1f]">Dashboard</h1>
          <p className="text-[#86868b] text-sm mt-0.5">bridgejob.co.kr 운영 현황</p>
        </div>
        <button type="button" onClick={fetchAll} className="text-sm text-[#0071e3] hover:underline">
          새로고침
        </button>
      </div>

      {loading ? (
        <div className="text-center py-32 text-[#86868b] animate-pulse">
          {wakeMsg ? '서버 깨우는 중... 잠시만 기다려주세요' : '대시보드 로딩 중...'}
        </div>
      ) : error ? (
        <div className="text-center py-32 space-y-4">
          <p className="text-red-500">{error}</p>
          <button type="button" className="px-5 py-2 rounded-full bg-[#0071e3] text-white text-sm font-medium hover:bg-[#0077ED]" onClick={fetchAll}>재시도</button>
        </div>
      ) : (
        <>
          {/* ── 최근 게시물 테이블 ────────────────────────────── */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden">
            <div className="px-5 py-4 border-b border-[#f0f0f2]">
              <h2 className="text-[15px] font-semibold text-[#1d1d1f]">최근 게시물</h2>
            </div>
            {recentPosts.length === 0 ? (
              <div className="px-5 py-10 text-center text-[#86868b] text-sm">최근 게시물이 없습니다.</div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="text-[11px] font-medium text-[#86868b] uppercase tracking-wider">
                    <th className="text-left px-5 py-2.5">날짜</th>
                    <th className="text-left px-5 py-2.5">게시판</th>
                    <th className="text-left px-5 py-2.5">제목</th>
                    <th className="text-right px-5 py-2.5">액션</th>
                  </tr>
                </thead>
                <tbody>
                  {recentPosts.map((post, idx) => (
                    <tr key={`${post.id}-${idx}`} className="border-t border-[#f5f5f7] hover:bg-[#fafafa] transition-colors">
                      <td className="px-5 py-3 text-[13px] text-[#86868b] whitespace-nowrap">
                        {post.created_at ? new Date(post.created_at).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' }) : '-'}
                      </td>
                      <td className="px-5 py-3">
                        <span className={`inline-block px-2 py-0.5 rounded-md text-[11px] font-medium ${boardColor(post.board ?? '')}`}>
                          {boardLabel(post.board ?? '')}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-[13px] text-[#1d1d1f] font-medium truncate max-w-[300px]">
                        {post.title}
                      </td>
                      <td className="px-5 py-3 text-right whitespace-nowrap">
                        <a href={`/admin/posts?board=${post.board}&edit=${post.id}`}
                          className="text-[12px] text-[#0071e3] hover:underline mr-3">편집</a>
                        <a href={`/community/${post.board}`}
                          className="text-[12px] text-[#86868b] hover:text-[#1d1d1f]">보기</a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* ── 통계 카드 6개 (미니멀) ────────────────────────── */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {statCards.map((c) => (
              <div key={c.label} className="bg-white rounded-2xl border border-[#e5e5e7] px-4 py-4">
                <div className="text-2xl font-bold text-[#1d1d1f] tabular-nums">{c.value}</div>
                <div className="text-[12px] text-[#86868b] mt-1 font-medium">{c.label}</div>
                {c.sub && <div className="text-[10px] text-[#aeaeb2] mt-0.5">{c.sub}</div>}
              </div>
            ))}
          </div>

          {/* ── 차트 2개 ─────────────────────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
              <h2 className="text-[15px] font-semibold text-[#1d1d1f] mb-4">월별 접수 추이</h2>
              {monthly.length > 0 ? (
                <div style={{ width: '100%', height: 220 }}>
                  <ResponsiveContainer>
                    <BarChart data={monthly}>
                      <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#86868b' }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fontSize: 11, fill: '#86868b' }} axisLine={false} tickLine={false} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#0071e3" radius={[6, 6, 0, 0]} name="접수" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-[#86868b] text-sm py-8 text-center">데이터 없음</p>
              )}
            </div>

            <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
              <h2 className="text-[15px] font-semibold text-[#1d1d1f] mb-4">채널별 비율</h2>
              {sources.length > 0 ? (
                <div className="flex items-center gap-4">
                  <div style={{ width: 170, height: 170 }}>
                    <ResponsiveContainer>
                      <PieChart>
                        <Pie data={sources} dataKey="count" nameKey="label"
                          cx="50%" cy="50%" outerRadius={75} innerRadius={40}>
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
                        <span className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: PIE_COLORS[idx % PIE_COLORS.length] }} />
                        <span className="text-[#424245] text-[13px]">{s.label}</span>
                        <span className="font-semibold text-[#1d1d1f] text-[13px]">{s.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-[#86868b] text-sm py-8 text-center">데이터 없음</p>
              )}
            </div>
          </div>

          {/* ── 노출 비중 (placeholder) ──────────────────────── */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
            <h2 className="text-[15px] font-semibold text-[#1d1d1f] mb-4">노출 비중</h2>
            <div className="space-y-3">
              {EXPOSURE_DATA.map((d) => (
                <div key={d.channel} className="flex items-center gap-3">
                  <span className="text-[13px] text-[#424245] w-20 shrink-0">{d.channel}</span>
                  <div className="flex-1 h-[6px] bg-[#f5f5f7] rounded-full overflow-hidden">
                    <div className="h-full bg-[#0071e3] rounded-full transition-all duration-500"
                      style={{ width: `${d.pct}%` }} />
                  </div>
                  <span className="text-[12px] font-medium text-[#86868b] w-10 text-right tabular-nums">{d.pct}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* ── 현황 요약 ────────────────────────────────────── */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
            <h2 className="text-[15px] font-semibold text-[#1d1d1f] mb-4">현황 요약</h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <SummaryItem label="Ad Posts" value={stats.ad_posts ?? 0} />
              <SummaryItem label="결제 전체" value={stats.payments_total ?? 0} />
              <SummaryItem label="결제 확인" value={stats.payments_confirmed ?? 0} />
              <SummaryItem label="인터뷰 예정" value={stats.interviews_scheduled ?? 0} />
              <SummaryItem label="게시글" value={stats.posts ?? 0} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function SummaryItem({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center py-2">
      <div className="text-xl font-bold text-[#1d1d1f] tabular-nums">{value}</div>
      <div className="text-[11px] text-[#86868b] mt-0.5">{label}</div>
    </div>
  )
}
