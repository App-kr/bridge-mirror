'use client'

/**
 * /admin — Dashboard (종합 현황)
 * Apple 2026 미니멀: 최근 게시물 테이블 → 통계 카드 → 차트 → 노출 비중 그래프
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import dynamic from 'next/dynamic'
import Link from 'next/link'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

// ── 숫자 카운트업 애니메이션 ──
function CountUp({ value, duration = 1200 }: { value: number; duration?: number }) {
  const [display, setDisplay] = useState(0)
  const prev = useRef(0)

  useEffect(() => {
    if (value === prev.current) return
    const start = prev.current
    const diff = value - start
    const startTime = performance.now()

    const tick = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      // easeOutExpo — 슝~ 올라가는 느낌
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
      setDisplay(Math.round(start + diff * eased))
      if (progress < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
    prev.current = value
  }, [value, duration])

  return <>{display.toLocaleString()}</>
}

// ── 트렌드 인디케이터 (상승/하락) ──
function TrendBadge({ value, label }: { value: number; label: string }) {
  if (value === 0) return <span className="text-[10px] text-[#aeaeb2] mt-0.5 block">{label}</span>
  const isUp = value > 0
  return (
    <span className={`inline-flex items-center gap-0.5 text-[10px] mt-0.5 font-semibold ${
      isUp ? 'text-emerald-500' : 'text-red-400'
    }`}>
      <span className={`inline-block ${isUp ? 'anim-trend-up' : 'anim-trend-down'}`}>
        {isUp ? '↑' : '↓'}
      </span>
      {isUp ? '+' : ''}{value} {label}
    </span>
  )
}

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
const SEEN_POSTS_KEY = 'bridge_admin_seen_posts'
const SEEN_NEW_KEY = 'bridge_admin_seen_new'

function getSeenNew(): Record<string, number> {
  if (typeof window === 'undefined') return {}
  try {
    const stored = localStorage.getItem(SEEN_NEW_KEY)
    if (stored) return JSON.parse(stored)
  } catch { /* empty */ }
  return {}
}

function markNewSeen(key: string, count: number) {
  if (typeof window === 'undefined') return
  const seen = getSeenNew()
  seen[key] = count
  localStorage.setItem(SEEN_NEW_KEY, JSON.stringify(seen))
}

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

interface AnalyticsData {
  total_visits: number
  today_visits: number
  channels: { channel: string; count: number }[]
  keywords: { keyword: string; count: number }[]
  pages: { page: string; count: number }[]
  daily: { date: string; count: number }[]
  campaigns: { source: string; medium: string; campaign: string; count: number }[]
}

const PIE_COLORS = ['#0071e3', '#34c759', '#ff9f0a', '#ff3b30', '#af52de', '#ff2d55', '#5ac8fa']
const BAR_COLORS = ['#0071e3', '#34c759', '#ff9f0a', '#ff3b30', '#af52de', '#ff2d55', '#5ac8fa']

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

function getSeenPosts(): Set<string> {
  if (typeof window === 'undefined') return new Set()
  try {
    const stored = localStorage.getItem(SEEN_POSTS_KEY)
    if (stored) return new Set(JSON.parse(stored))
  } catch { /* empty */ }
  return new Set()
}

function markPostSeen(postId: number) {
  if (typeof window === 'undefined') return
  const seen = getSeenPosts()
  seen.add(String(postId))
  localStorage.setItem(SEEN_POSTS_KEY, JSON.stringify([...seen]))
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
  const [showCount, setShowCount] = useState(10)
  const [seenPosts, setSeenPosts] = useState<Set<string>>(new Set())
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [analyticsDays, setAnalyticsDays] = useState(30)
  const [kakaoUrl, setKakaoUrl] = useState<string>('')
  const [seenNew, setSeenNew] = useState<Record<string, number>>({})

  useEffect(() => {
    fetch(`${API}/api/settings`)
      .then(r => r.json())
      .then(j => { if (j.success) setKakaoUrl(j.data?.settings?.kakao_channel ?? '') })
      .catch(() => {})
  }, [])

  useEffect(() => {
    setSeenPosts(getSeenPosts())
    setSeenNew(getSeenNew())
  }, [])

  const fetchAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    setWakeMsg(false)
    try {
      const onWaking = () => setWakeMsg(true)
      const [dashRes, statsRes, monthlyRes, sourceRes, analyticsRes] = await Promise.all([
        adminFetch(`${API}/api/admin/dashboard`, undefined, onWaking),
        adminFetch(`${API}/api/admin/stats`, undefined, onWaking),
        adminFetch(`${API}/api/admin/stats/monthly`, undefined, onWaking),
        adminFetch(`${API}/api/admin/stats/by-source`, undefined, onWaking),
        adminFetch(`${API}/api/admin/analytics?days=${analyticsDays}`, undefined, onWaking),
      ])
      setWakeMsg(false)

      if (dashRes.status === 403) {
        const errBody = await dashRes.json().catch(() => ({}))
        if (errBody.error?.includes?.('Access denied')) {
          setError('일시적으로 차단되었습니다. 자동 재시도 중...')
          const k = localStorage.getItem('bridge_admin_key') || ''
          await fetch(`${API}/api/admin/reset-blacklist`, { method: 'POST', headers: { 'x-admin-key': k } }).catch(() => {})
          setTimeout(() => window.location.reload(), 3000)
          return
        }
        setError('관리자 키가 올바르지 않습니다. 다시 로그인해주세요.')
        localStorage.removeItem('bridge_admin_key')
        return
      }

      const [dashJson, statsJson, monthlyJson, sourceJson, analyticsJson] = await Promise.all([
        dashRes.json(), statsRes.json(), monthlyRes.json(), sourceRes.json(), analyticsRes.json(),
      ])

      if (dashJson.success) {
        setStats(dashJson.data?.stats ?? {})
        setActivity(dashJson.data?.recent_activity ?? [])
      }
      if (statsJson.success) setInboxStats(statsJson.data ?? {})
      if (monthlyJson.success) setMonthly(monthlyJson.data ?? [])
      if (sourceJson.success) setSources(sourceJson.data ?? [])
      if (analyticsJson.success) setAnalytics(analyticsJson.data ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : '대시보드 로드 실패')
    } finally {
      setLoading(false)
      setWakeMsg(false)
    }
  }, [adminFetch, analyticsDays])

  useEffect(() => {
    if (authed) fetchAll()
  }, [authed, fetchAll])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  const thisMonthDelta = inboxStats.this_month_candidates ?? 0
  const lastMonthDelta = inboxStats.last_month_candidates ?? 0
  const deltaSign = thisMonthDelta > lastMonthDelta ? '+' : ''
  const deltaValue = thisMonthDelta - lastMonthDelta

  const newCandidates = inboxStats.new_candidates ?? 0
  const newInquiries = inboxStats.this_month_inquiries ?? 0
  const unseenCandidates = Math.max(0, newCandidates - (seenNew.candidates ?? 0))
  const unseenInquiries = Math.max(0, newInquiries - (seenNew.inquiries ?? 0))

  const handleConfirmNew = (key: string, count: number) => {
    markNewSeen(key, count)
    setSeenNew(getSeenNew())
  }

  const statCards = [
    { label: '총 지원', value: inboxStats.total_candidates ?? 0, trend: thisMonthDelta, trendLabel: '이번달', newCount: unseenCandidates, newKey: 'candidates', newTotal: newCandidates },
    { label: '신규 미처리', value: inboxStats.new_candidates ?? 0, trend: 0, trendLabel: '' },
    { label: '이번달 유입', value: thisMonthDelta, trend: deltaValue, trendLabel: '전월 대비' },
    { label: '구인 문의', value: inboxStats.total_inquiries ?? 0, trend: inboxStats.this_month_inquiries ?? 0, trendLabel: '이번달', newCount: unseenInquiries, newKey: 'inquiries', newTotal: newInquiries },
    { label: '활성 구인', value: inboxStats.active_jobs ?? 0, trend: 0, trendLabel: '' },
    { label: '커뮤니티', value: inboxStats.community_posts ?? 0, trend: 0, trendLabel: '' },
  ] as Array<{ label: string; value: number; trend: number; trendLabel: string; newCount?: number; newKey?: string; newTotal?: number }>

  const recentPosts = activity.filter(a => a.type === 'post')
  const visiblePosts = recentPosts.slice(0, showCount)
  const hasMore = recentPosts.length > showCount

  const handleConfirm = (postId: number) => {
    markPostSeen(postId)
    setSeenPosts(getSeenPosts())
  }

  // 노출 비중: sources 데이터 기반 (실제 데이터)
  const totalSourceCount = sources.reduce((sum, s) => sum + s.count, 0)
  const exposureData = sources.map((s, idx) => ({
    label: s.label,
    count: s.count,
    pct: totalSourceCount > 0 ? Math.round((s.count / totalSourceCount) * 100) : 0,
    color: BAR_COLORS[idx % BAR_COLORS.length],
  }))

  return (
    <div className="space-y-8">
      {/* IP 경고 바 */}
      <div
        className="flex items-center gap-2.5 px-4 py-2.5 rounded-2xl text-[13px]"
        style={{ background: 'rgba(255, 59, 48, 0.06)', color: 'rgba(180, 40, 32, 0.85)' }}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ flexShrink: 0 }}>
          <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.3"/>
          <path d="M7 4.5V7.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
          <circle cx="7" cy="9.5" r="0.7" fill="currentColor"/>
        </svg>
        <span>IP 로그 기록 중 — 관리자가 아닌 경우 즉시 종료하십시오</span>
      </div>

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

      {/* 빠른 실행 */}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => {
            document.cookie = 'bridge_edit_mode=true; path=/; max-age=7200'
            window.open('/', '_blank')
          }}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-[13px] text-white bg-[#0071e3] shadow-sm hover:bg-[#0077ED] active:scale-[0.98] transition-all"
        >
          <span className="text-[14px] leading-none">⚙️</span>
          관리자로 메인가기
        </button>
        <a
          href="https://business.kakao.com/_tBxhxkK/chats"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-[13px] text-[#191919] shadow-sm hover:brightness-95 active:scale-[0.98] transition-all"
          style={{ background: '#FEE500' }}
        >
          <span className="text-[16px] leading-none">💬</span>
          카카오채널 가기
          <span className="text-[11px] opacity-50 ml-1">↗</span>
        </a>
        <a
          href="https://bridgejob.co.kr"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-[13px] font-medium text-[#424245] bg-white border border-[#e5e5e7] hover:bg-[#f5f5f7] transition-colors shadow-sm"
        >
          <span className="text-[14px] leading-none">🌐</span>
          홈페이지
          <span className="text-[11px] opacity-40 ml-1">↗</span>
        </a>
      </div>

      {/* ── 관리 메뉴 바로가기 ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {[
          { href: '/admin/sheet', label: '원어민 관리', desc: '전체 후보자 시트', icon: '👤' },
          { href: '/admin/employers', label: '구인자 관리', desc: '고용주 문의·매칭', icon: '🏢' },
          { href: '/admin/applications', label: '업체 관리', desc: '지원 현황', icon: '🏬' },
          { href: '/admin/jobs', label: '채용공고', desc: 'Job Board 관리', icon: '💼' },
          { href: '/admin/posts', label: '게시물 관리', desc: '전체 게시판 콘텐츠', icon: '📝' },
          { href: '/admin/mail-send', label: '메일 발송', desc: '이메일 작성·발송', icon: '📧' },
          { href: '/admin/banners', label: '배너 관리', desc: '사이트 배너 이미지', icon: '🖼️' },
          { href: '/admin/settings', label: '사이트 설정', desc: '이름·히어로·네비·CTA·SNS', icon: '⚙️' },
        ].map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="bg-white rounded-2xl border border-[#e5e5e7] px-4 py-4 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group"
          >
            <span className="text-[20px]">{item.icon}</span>
            <div className="text-[14px] font-semibold text-[#1d1d1f] mt-2 group-hover:text-[#0071e3] transition-colors">{item.label}</div>
            <div className="text-[11px] text-[#86868b] mt-0.5">{item.desc}</div>
          </Link>
        ))}
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
            <div className="px-5 py-4 border-b border-[#f0f0f2] flex items-center justify-between">
              <h2 className="text-[15px] font-semibold text-[#1d1d1f]">최근 게시물</h2>
              <span className="text-[12px] text-[#86868b]">{recentPosts.length}건</span>
            </div>
            {visiblePosts.length === 0 ? (
              <div className="px-5 py-10 text-center text-[#86868b] text-sm">최근 게시물이 없습니다.</div>
            ) : (
              <>
                <div className="overflow-x-auto">
                <table className="w-full min-w-[500px]">
                  <thead>
                    <tr className="text-[11px] font-medium text-[#86868b] uppercase tracking-wider">
                      <th className="text-left px-5 py-2.5">날짜</th>
                      <th className="text-left px-5 py-2.5">게시판</th>
                      <th className="text-left px-5 py-2.5">제목</th>
                      <th className="text-right px-5 py-2.5">액션</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visiblePosts.map((post, idx) => {
                      const isNew = !seenPosts.has(String(post.id))
                      return (
                        <tr key={`${post.id}-${idx}`} className="border-t border-[#f5f5f7] hover:bg-[#fafafa] transition-colors">
                          <td className="px-5 py-3 text-[13px] text-[#1d1d1f] whitespace-nowrap">
                            <span className="inline-flex items-center gap-1.5">
                              {post.created_at ? new Date(post.created_at).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' }) : '-'}
                              {isNew && (
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-red-500 text-white animate-pulse shadow-sm shadow-red-200">
                                  NEW
                                </span>
                              )}
                            </span>
                          </td>
                          <td className="px-5 py-3">
                            <span className={`inline-block px-2.5 py-0.5 rounded-md text-[13px] font-semibold ${boardColor(post.board ?? '')}`}>
                              {boardLabel(post.board ?? '')}
                            </span>
                          </td>
                          <td className="px-5 py-3 text-[13px] text-[#1d1d1f] font-medium truncate max-w-[300px]">
                            {post.title}
                          </td>
                          <td className="px-5 py-3 text-right whitespace-nowrap">
                            <div className="inline-flex items-center gap-1.5">
                              {isNew && (
                                <button type="button" onClick={() => handleConfirm(post.id)}
                                  className="px-2 py-1 rounded-md text-[11px] font-medium bg-emerald-50 text-emerald-600 hover:bg-emerald-100 transition-colors border border-emerald-200">
                                  확인
                                </button>
                              )}
                              <Link href={`/admin/posts?board=${post.board}&edit=${post.id}`}
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium bg-[#0071e3]/10 text-[#0071e3] hover:bg-[#0071e3]/20 transition-colors">
                                편집
                              </Link>
                              <a href={`/community/${post.board}`} target="_blank" rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium bg-[#f5f5f7] text-[#424245] hover:bg-[#e8e8ed] transition-colors">
                                보기 &rarr;
                              </a>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
                </div>
                {hasMore && (
                  <div className="px-5 py-3 border-t border-[#f5f5f7] text-center">
                    <button type="button" onClick={() => setShowCount(prev => prev + 10)}
                      className="text-[13px] text-[#0071e3] hover:underline font-medium">
                      더보기 ({recentPosts.length - showCount}건 남음)
                    </button>
                  </div>
                )}
              </>
            )}
          </div>

          {/* ── 통계 카드 6개 (애니메이션) ────────────────────── */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {statCards.map((c, i) => {
              const hasNew = (c.newCount ?? 0) > 0
              return (
                <div key={c.label}
                  className="bg-white rounded-2xl border border-[#e5e5e7] px-4 py-4 anim-card-in hover:shadow-md hover:-translate-y-0.5 transition-all duration-300"
                  style={{ animationDelay: `${i * 80}ms` }}>
                  <div className="flex items-baseline gap-2">
                    <div className="text-2xl font-bold text-[#1d1d1f] tabular-nums">
                      <CountUp value={c.value} />
                    </div>
                    {hasNew && (
                      <button
                        type="button"
                        onClick={() => c.newKey && handleConfirmNew(c.newKey, c.newTotal ?? 0)}
                        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[11px] font-bold tabular-nums cursor-pointer border-0 anim-pulse-blue"
                        style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6' }}
                        title="클릭하여 확인"
                      >
                        <span className="text-[10px]">N</span>
                        <span>+{c.newCount}</span>
                      </button>
                    )}
                  </div>
                  <div className="text-[12px] text-[#86868b] mt-1 font-medium">{c.label}</div>
                  {c.trend !== 0 && c.trendLabel && <TrendBadge value={c.trend} label={c.trendLabel} />}
                  {c.trend === 0 && c.trendLabel && <span className="text-[10px] text-[#aeaeb2] mt-0.5 block">{c.trendLabel}</span>}
                </div>
              )
            })}
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
                <div className="flex flex-col sm:flex-row items-center gap-4">
                  <div className="shrink-0" style={{ width: 150, height: 150 }}>
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

          {/* ── 유입 채널 비중 (실제 데이터 그래프) ────────────── */}
          {exposureData.length > 0 && (
            <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
              <h2 className="text-[15px] font-semibold text-[#1d1d1f] mb-5">유입 채널 비중</h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 가로 바 그래프 */}
                <div className="space-y-3">
                  {exposureData.map((d) => (
                    <div key={d.label} className="flex items-center gap-3">
                      <span className="text-[13px] text-[#424245] w-24 shrink-0 font-medium">{d.label}</span>
                      <div className="flex-1 h-[8px] bg-[#f5f5f7] rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all duration-700"
                          style={{ width: `${d.pct}%`, backgroundColor: d.color }} />
                      </div>
                      <span className="text-[12px] font-semibold text-[#1d1d1f] w-12 text-right tabular-nums">{d.pct}%</span>
                      <span className="text-[11px] text-[#86868b] w-10 text-right tabular-nums">{d.count}건</span>
                    </div>
                  ))}
                </div>
                {/* recharts 바 차트 */}
                <div style={{ width: '100%', height: 200 }}>
                  <ResponsiveContainer>
                    <BarChart data={exposureData} layout="vertical">
                      <XAxis type="number" tick={{ fontSize: 11, fill: '#86868b' }} axisLine={false} tickLine={false} />
                      <YAxis type="category" dataKey="label" tick={{ fontSize: 11, fill: '#424245' }} axisLine={false} tickLine={false} width={80} />
                      <Tooltip />
                      <Bar dataKey="count" radius={[0, 6, 6, 0]} name="유입">
                        {exposureData.map((d, idx) => (
                          <Cell key={idx} fill={d.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {/* ── 검색 유입 분석 ─────────────────────────────────── */}
          {analytics && (
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <h2 className="text-[17px] font-bold text-[#1d1d1f]">검색 유입 분석</h2>
                <div className="flex items-center gap-2">
                  {[7, 30, 90].map(d => (
                    <button key={d} type="button" onClick={() => setAnalyticsDays(d)}
                      className={`px-3 py-1 rounded-full text-[12px] font-medium transition-colors ${
                        analyticsDays === d
                          ? 'bg-[#0071e3] text-white'
                          : 'bg-[#f5f5f7] text-[#424245] hover:bg-[#e8e8ed]'
                      }`}>
                      {d}일
                    </button>
                  ))}
                </div>
              </div>

              {/* 방문 요약 카드 */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { value: analytics.total_visits, color: '#1d1d1f', label: `총 방문 (${analyticsDays}일)`, emoji: '' },
                  { value: analytics.today_visits, color: '#0071e3', label: '오늘 방문', emoji: analytics.today_visits > 0 ? '🔥' : '' },
                  { value: analytics.keywords.length, color: '#34c759', label: '검색어 종류', emoji: '' },
                  { value: analytics.channels.length, color: '#ff9f0a', label: '유입 채널', emoji: '' },
                ].map((card, i) => (
                  <div key={card.label}
                    className="bg-white rounded-2xl border border-[#e5e5e7] px-4 py-4 anim-card-in hover:shadow-md hover:-translate-y-0.5 transition-all duration-300"
                    style={{ animationDelay: `${i * 100}ms` }}>
                    <div className="text-2xl font-bold tabular-nums" style={{ color: card.color }}>
                      <CountUp value={card.value} /> {card.emoji}
                    </div>
                    <div className="text-[12px] text-[#86868b] mt-1 font-medium">{card.label}</div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* 채널별 유입 */}
                <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
                  <h3 className="text-[15px] font-semibold text-[#1d1d1f] mb-4">유입 채널</h3>
                  {analytics.channels.length > 0 ? (
                    <div className="space-y-2.5">
                      {analytics.channels.map((ch, idx) => {
                        const totalCh = analytics.channels.reduce((s, c) => s + c.count, 0)
                        const pct = totalCh > 0 ? Math.round((ch.count / totalCh) * 100) : 0
                        return (
                          <div key={ch.channel} className="flex items-center gap-3 anim-slide-in"
                            style={{ animationDelay: `${idx * 60}ms` }}>
                            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: BAR_COLORS[idx % BAR_COLORS.length] }} />
                            <span className="text-[13px] text-[#424245] w-20 shrink-0 font-medium capitalize">{ch.channel}</span>
                            <div className="flex-1 h-[6px] bg-[#f5f5f7] rounded-full overflow-hidden">
                              <div className="h-full rounded-full anim-bar-fill"
                                style={{ '--bar-width': `${pct}%`, backgroundColor: BAR_COLORS[idx % BAR_COLORS.length], animationDelay: `${idx * 60 + 200}ms` } as React.CSSProperties} />
                            </div>
                            <span className="text-[12px] font-semibold text-[#1d1d1f] w-8 text-right tabular-nums">{pct}%</span>
                            <span className="text-[11px] text-[#86868b] w-10 text-right tabular-nums">{ch.count}</span>
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    <p className="text-[#86868b] text-sm py-4 text-center">데이터 수집 중...</p>
                  )}
                </div>

                {/* 검색 키워드 TOP */}
                <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
                  <h3 className="text-[15px] font-semibold text-[#1d1d1f] mb-4">
                    검색 키워드 TOP
                    <span className="text-[11px] text-[#86868b] ml-2 font-normal">Naver · Daum · Google</span>
                  </h3>
                  {analytics.keywords.length > 0 ? (
                    <div className="space-y-1.5 max-h-[280px] overflow-y-auto">
                      {analytics.keywords.map((kw, idx) => (
                        <div key={kw.keyword} className="flex items-center gap-3 py-1 anim-slide-in"
                          style={{ animationDelay: `${idx * 40}ms` }}>
                          <span className="text-[11px] text-[#86868b] w-5 text-right shrink-0 tabular-nums font-bold">
                            {idx < 3 ? ['🥇','🥈','🥉'][idx] : idx + 1}
                          </span>
                          <span className="flex-1 text-[13px] text-[#1d1d1f] font-medium truncate">{kw.keyword}</span>
                          <span className="text-[12px] font-semibold text-[#0071e3] tabular-nums">{kw.count}회</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[#86868b] text-sm py-4 text-center">
                      검색어 데이터 수집 중...<br />
                      <span className="text-[11px]">Naver/Daum 검색 유입 시 자동 기록됩니다</span>
                    </p>
                  )}
                </div>
              </div>

              {/* 인기 페이지 + 일별 추이 */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
                  <h3 className="text-[15px] font-semibold text-[#1d1d1f] mb-4">인기 랜딩 페이지</h3>
                  {analytics.pages.length > 0 ? (
                    <div className="space-y-1.5 max-h-[240px] overflow-y-auto">
                      {analytics.pages.map((pg, idx) => {
                        const totalPg = analytics.pages.reduce((s, p) => s + p.count, 0)
                        const pct = totalPg > 0 ? Math.round((pg.count / totalPg) * 100) : 0
                        return (
                          <div key={pg.page} className="flex items-center gap-2 py-1">
                            <span className="text-[11px] text-[#86868b] w-5 text-right shrink-0 tabular-nums">{idx + 1}</span>
                            <span className="flex-1 text-[13px] text-[#424245] truncate font-mono">{pg.page}</span>
                            <span className="text-[11px] text-[#86868b] tabular-nums">{pct}%</span>
                            <span className="text-[12px] font-semibold text-[#1d1d1f] tabular-nums w-8 text-right">{pg.count}</span>
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    <p className="text-[#86868b] text-sm py-4 text-center">데이터 수집 중...</p>
                  )}
                </div>

                <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
                  <h3 className="text-[15px] font-semibold text-[#1d1d1f] mb-4">일별 방문 추이</h3>
                  {analytics.daily.length > 0 ? (
                    <div style={{ width: '100%', height: 220 }}>
                      <ResponsiveContainer>
                        <BarChart data={analytics.daily}>
                          <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#86868b' }} axisLine={false} tickLine={false}
                            tickFormatter={(v: string) => v.slice(5)} />
                          <YAxis tick={{ fontSize: 11, fill: '#86868b' }} axisLine={false} tickLine={false} />
                          <Tooltip />
                          <Bar dataKey="count" fill="#34c759" radius={[4, 4, 0, 0]} name="방문" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <p className="text-[#86868b] text-sm py-4 text-center">데이터 수집 중...</p>
                  )}
                </div>
              </div>

              {/* UTM 캠페인 */}
              {analytics.campaigns.length > 0 && (
                <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
                  <h3 className="text-[15px] font-semibold text-[#1d1d1f] mb-4">UTM 캠페인</h3>
                  <table className="w-full text-left">
                    <thead>
                      <tr className="text-[11px] font-medium text-[#86868b] uppercase tracking-wider">
                        <th className="px-3 py-2">Source</th>
                        <th className="px-3 py-2">Medium</th>
                        <th className="px-3 py-2">Campaign</th>
                        <th className="px-3 py-2 text-right">방문</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analytics.campaigns.map((c, idx) => (
                        <tr key={idx} className="border-t border-[#f5f5f7]">
                          <td className="px-3 py-2 text-[13px] text-[#1d1d1f]">{c.source || '-'}</td>
                          <td className="px-3 py-2 text-[13px] text-[#424245]">{c.medium || '-'}</td>
                          <td className="px-3 py-2 text-[13px] text-[#424245]">{c.campaign || '-'}</td>
                          <td className="px-3 py-2 text-[13px] font-semibold text-[#1d1d1f] text-right tabular-nums">{c.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

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
