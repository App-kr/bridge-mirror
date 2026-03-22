'use client'

import { useCallback, useEffect, useState, useMemo } from 'react'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import AdminAuth from '@/components/admin/AdminAuth'
import PullToRefresh from '../components/PullToRefresh'
import InterviewCard from '../components/InterviewCard'
import { ChevronLeft } from 'lucide-react'
import Link from 'next/link'

const API = API_URL

interface Interview {
  id: number
  candidate_name: string
  candidate_email: string
  candidate_id: string
  employer_name: string
  interview_date: string
  interview_time: string
  meet_link: string
  status: string
  notes: string
  duration_minutes: number
  email_sent_candidate: number
  email_sent_employer: number
  created_at: string
}

const FILTER_TABS = [
  { key: 'all', label: '전체' },
  { key: 'scheduled', label: '예정' },
  { key: 'completed', label: '완료' },
  { key: 'cancelled', label: '취소' },
]

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

function formatDateHeader(dateStr: string): string {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const target = new Date(dateStr + 'T00:00:00')
  target.setHours(0, 0, 0, 0)
  const diff = Math.round((target.getTime() - today.getTime()) / 86400000)

  if (diff === 0) return '오늘'
  if (diff === 1) return '내일'

  const m = target.getMonth() + 1
  const d = target.getDate()
  const wd = WEEKDAYS[target.getDay()]
  return `${m}월 ${d}일 (${wd})`
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl border border-[#e5e5e7] border-l-4 border-l-[#e5e5e7] px-4 py-3 animate-pulse space-y-2">
      <div className="flex items-center justify-between">
        <div className="h-4 w-12 bg-[#f5f5f7] rounded-full" />
        <div className="h-4 w-10 bg-[#f5f5f7] rounded-full" />
      </div>
      <div className="h-5 w-40 bg-[#f5f5f7] rounded" />
      <div className="h-3 w-28 bg-[#f5f5f7] rounded" />
      <div className="h-3 w-24 bg-[#f5f5f7] rounded" />
    </div>
  )
}

export default function InterviewsPage() {
  const { authed, waking, login, adminFetch, signedFetch } = useAdminAuth()
  const [interviews, setInterviews] = useState<Interview[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  const fetchInterviews = useCallback(async () => {
    setLoading(true)
    try {
      const res = await adminFetch(`${API}/api/admin/interviews`)
      const json = await res.json()
      if (json.success) {
        setInterviews(json.data ?? [])
      }
    } catch {
      // silent, user can pull to refresh
    } finally {
      setLoading(false)
    }
  }, [adminFetch])

  useEffect(() => {
    if (authed) fetchInterviews()
  }, [authed, fetchInterviews])

  const handleStatusChange = useCallback(async (id: number, status: string) => {
    try {
      await signedFetch(`${API}/api/admin/interviews/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      })
      setInterviews(prev =>
        prev.map(iv => iv.id === id ? { ...iv, status } : iv)
      )
    } catch {
      // silent
    }
  }, [signedFetch])

  // Filter + group by date
  const grouped = useMemo(() => {
    const filtered = filter === 'all'
      ? interviews
      : interviews.filter(iv => iv.status === filter)

    // Split into upcoming and past
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const todayStr = today.toISOString().slice(0, 10)

    const upcoming = filtered
      .filter(iv => iv.interview_date >= todayStr)
      .sort((a, b) => {
        const cmp = a.interview_date.localeCompare(b.interview_date)
        if (cmp !== 0) return cmp
        return (a.interview_time || '').localeCompare(b.interview_time || '')
      })

    const past = filtered
      .filter(iv => iv.interview_date < todayStr)
      .sort((a, b) => {
        const cmp = b.interview_date.localeCompare(a.interview_date)
        if (cmp !== 0) return cmp
        return (b.interview_time || '').localeCompare(a.interview_time || '')
      })

    const sorted = [...upcoming, ...past]

    // Group by date
    const groups: { date: string; label: string; items: Interview[] }[] = []
    for (const iv of sorted) {
      const dateKey = iv.interview_date
      const existing = groups.find(g => g.date === dateKey)
      if (existing) {
        existing.items.push(iv)
      } else {
        groups.push({
          date: dateKey,
          label: formatDateHeader(dateKey),
          items: [iv],
        })
      }
    }

    return groups
  }, [interviews, filter])

  const totalFiltered = grouped.reduce((sum, g) => sum + g.items.length, 0)

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <PullToRefresh onRefresh={fetchInterviews}>
        <div className="px-4 pb-8 pt-safe">

          {/* Header */}
          <div className="flex items-center gap-3 pt-4 pb-3">
            <Link
              href="/admin/m"
              className="w-9 h-9 flex items-center justify-center rounded-full bg-white border border-[#e5e5e7] shrink-0"
            >
              <ChevronLeft size={18} className="text-[#1d1d1f]" />
            </Link>
            <div className="flex-1">
              <h1 className="text-xl font-bold text-[#1d1d1f]">인터뷰 관리</h1>
              <p className="text-xs text-[#86868b]">{totalFiltered}건</p>
            </div>
          </div>

          {/* Filter tabs */}
          <div className="flex gap-2 overflow-x-auto pb-3 -mx-4 px-4 scrollbar-hide">
            {FILTER_TABS.map(tab => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setFilter(tab.key)}
                className={`shrink-0 px-3.5 py-1.5 rounded-full text-sm font-medium min-h-[36px] transition-colors ${
                  filter === tab.key
                    ? 'bg-[#1d1d1f] text-white'
                    : 'bg-white border border-[#e5e5e7] text-[#86868b]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Interview timeline */}
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => <SkeletonCard key={i} />)}
            </div>
          ) : grouped.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-[#86868b] text-sm">예정된 인터뷰가 없습니다</p>
            </div>
          ) : (
            <div className="space-y-4">
              {grouped.map(group => (
                <div key={group.date}>
                  {/* Date header */}
                  <div className="flex items-center gap-2 mb-2 px-1">
                    <h2 className="text-sm font-semibold text-[#1d1d1f]">{group.label}</h2>
                    <span className="text-xs text-[#aeaeb2]">{group.items.length}건</span>
                  </div>

                  {/* Cards */}
                  <div className="space-y-3">
                    {group.items.map(iv => (
                      <InterviewCard
                        key={iv.id}
                        interview={iv}
                        onStatusChange={handleStatusChange}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </PullToRefresh>
    </div>
  )
}
