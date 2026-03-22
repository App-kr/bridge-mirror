'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import AdminAuth from '@/components/admin/AdminAuth'
import PullToRefresh from './components/PullToRefresh'
import {
  Users, MessageSquare, CalendarCheck, Briefcase,
  ChevronRight, RefreshCw, Clock
} from 'lucide-react'

const API = API_URL

interface DashboardStats {
  total_candidates?: number
  new_candidates?: number
  this_month_candidates?: number
  total_inquiries?: number
  this_month_inquiries?: number
  active_jobs?: number
}

interface ActivityItem {
  type: string
  id: number
  title?: string
  candidate_name?: string
  status?: string
  created_at?: string
}

function formatKoreanDate(): string {
  const now = new Date()
  const days = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일']
  const month = now.getMonth() + 1
  const date = now.getDate()
  const day = days[now.getDay()]
  return `${month}월 ${date}일 ${day}`
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '방금'
  if (mins < 60) return `${mins}분 전`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}시간 전`
  const days = Math.floor(hours / 24)
  return `${days}일 전`
}

/* ── Skeleton Card ── */
function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4 animate-pulse">
      <div className="h-8 w-16 bg-[#f5f5f7] rounded-lg mb-2" />
      <div className="h-3 w-20 bg-[#f5f5f7] rounded" />
    </div>
  )
}

function SkeletonActivity() {
  return (
    <div className="flex items-center gap-3 px-4 py-3 animate-pulse">
      <div className="w-8 h-8 bg-[#f5f5f7] rounded-full shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="h-3 w-3/4 bg-[#f5f5f7] rounded" />
        <div className="h-2 w-1/2 bg-[#f5f5f7] rounded" />
      </div>
    </div>
  )
}

export default function MobileDashboardPage() {
  const { authed, waking, login, adminFetch } = useAdminAuth()
  const [stats, setStats] = useState<DashboardStats>({})
  const [newInquiryCount, setNewInquiryCount] = useState(0)
  const [activity, setActivity] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [statsRes, dashRes, inquiryRes] = await Promise.all([
        adminFetch(`${API}/api/admin/stats`),
        adminFetch(`${API}/api/admin/dashboard`),
        adminFetch(`${API}/api/admin/inquiries/new-count`),
      ])

      const [statsJson, dashJson, inquiryJson] = await Promise.all([
        statsRes.json(),
        dashRes.json(),
        inquiryRes.json(),
      ])

      if (statsJson.success) setStats(statsJson.data ?? {})
      if (dashJson.success) setActivity(dashJson.data?.recent_activity?.slice(0, 5) ?? [])
      if (inquiryJson.success) setNewInquiryCount(inquiryJson.data?.count ?? 0)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }, [adminFetch])

  useEffect(() => {
    if (authed) fetchData()
  }, [authed, fetchData])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  const summaryCards = [
    {
      label: '신규 접수',
      value: stats.new_candidates ?? 0,
      icon: Users,
      color: '#0071e3',
      bg: '#eff6ff',
    },
    {
      label: '신규 문의',
      value: newInquiryCount,
      icon: MessageSquare,
      color: '#ff9f0a',
      bg: '#fff7ed',
    },
    {
      label: '이번달 접수',
      value: stats.this_month_candidates ?? 0,
      icon: CalendarCheck,
      color: '#34c759',
      bg: '#ecfdf5',
    },
    {
      label: '활성 구인',
      value: stats.active_jobs ?? 0,
      icon: Briefcase,
      color: '#af52de',
      bg: '#faf5ff',
    },
  ]

  const quickActions = [
    { label: '후보자 보기', href: '/admin/m/candidates', color: '#0071e3', bg: '#eff6ff' },
    { label: '문의 확인', href: '/admin/m/inquiries', color: '#ff9f0a', bg: '#fff7ed' },
    { label: '메일 발송', href: '/admin/m/mail', color: '#34c759', bg: '#ecfdf5' },
    { label: '인터뷰', href: '/admin/m/interviews', color: '#af52de', bg: '#faf5ff' },
  ]

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <PullToRefresh onRefresh={fetchData}>
        <div className="px-4 pb-8 pt-safe">

          {/* ── Welcome Section ── */}
          <div className="pt-6 pb-4">
            <p className="text-sm text-[#86868b]">{formatKoreanDate()}</p>
            <h1 className="text-2xl font-bold text-[#1d1d1f] mt-1">BRIDGE Admin</h1>
          </div>

          {/* ── Summary Cards 2x2 ── */}
          {loading ? (
            <div className="grid grid-cols-2 gap-3 mb-6">
              {[1, 2, 3, 4].map(i => <SkeletonCard key={i} />)}
            </div>
          ) : error ? (
            <div className="bg-white rounded-2xl border border-[#e5e5e7] p-6 mb-6 text-center">
              <p className="text-red-500 text-sm mb-3">{error}</p>
              <button
                type="button"
                onClick={fetchData}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#0071e3] text-white text-sm font-medium"
              >
                <RefreshCw size={14} />
                Retry
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3 mb-6">
              {summaryCards.map((card) => {
                const Icon = card.icon
                return (
                  <div
                    key={card.label}
                    className="bg-white rounded-2xl border border-[#e5e5e7] p-4 relative overflow-hidden"
                  >
                    <div
                      className="absolute top-3 right-3 w-8 h-8 rounded-full flex items-center justify-center"
                      style={{ backgroundColor: card.bg }}
                    >
                      <Icon size={16} style={{ color: card.color }} />
                    </div>
                    <div className="text-3xl font-bold text-[#1d1d1f] tabular-nums">
                      {card.value}
                    </div>
                    <div className="text-xs text-[#86868b] mt-1 font-medium">
                      {card.label}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* ── Quick Actions ── */}
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-[#86868b] uppercase tracking-wider mb-3 px-1">
              Quick Actions
            </h2>
            <div className="flex gap-3 overflow-x-auto pb-1 -mx-4 px-4 scrollbar-hide">
              {quickActions.map((action) => (
                <Link
                  key={action.label}
                  href={action.href}
                  className="flex-shrink-0 flex items-center gap-2 px-4 py-3 rounded-2xl bg-white border border-[#e5e5e7] text-sm font-medium text-[#1d1d1f] min-h-[44px] active:scale-[0.97] transition-transform"
                >
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: action.color }}
                  />
                  {action.label}
                  <ChevronRight size={14} className="text-[#86868b]" />
                </Link>
              ))}
            </div>
          </div>

          {/* ── Recent Activity ── */}
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-[#86868b] uppercase tracking-wider mb-3 px-1">
              Recent Activity
            </h2>
            <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden divide-y divide-[#f5f5f7]">
              {loading ? (
                [1, 2, 3, 4, 5].map(i => <SkeletonActivity key={i} />)
              ) : activity.length === 0 ? (
                <div className="px-4 py-8 text-center text-[#86868b] text-sm">
                  No recent activity
                </div>
              ) : (
                activity.map((item, idx) => (
                  <div key={`${item.id}-${idx}`} className="flex items-center gap-3 px-4 py-3">
                    <div className="w-8 h-8 rounded-full bg-[#f5f5f7] flex items-center justify-center shrink-0">
                      <Clock size={14} className="text-[#86868b]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-[#1d1d1f] font-medium truncate">
                        {item.candidate_name || item.title || `Activity #${item.id}`}
                      </p>
                      <p className="text-xs text-[#86868b]">
                        {item.type}
                        {item.created_at ? ` - ${timeAgo(item.created_at)}` : ''}
                      </p>
                    </div>
                    {item.status && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-[#f5f5f7] text-[#86868b] font-medium shrink-0">
                        {item.status}
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

        </div>
      </PullToRefresh>
    </div>
  )
}
