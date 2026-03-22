'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import AdminAuth from '@/components/admin/AdminAuth'
import PullToRefresh from '../components/PullToRefresh'
import CandidateCard from '../components/CandidateCard'
import CandidateDetail from '../components/CandidateDetail'
import { Search, ArrowLeft, Loader2 } from 'lucide-react'
import Link from 'next/link'

const API = API_URL
const PAGE_SIZE = 20

const FILTER_TABS = [
  { label: 'All', value: '' },
  { label: 'New', value: 'new' },
  { label: 'Interview', value: 'interview' },
  { label: 'Contract', value: 'contract' },
  { label: 'Hired', value: 'hired' },
]

interface CandidateRow {
  id: number
  name: string
  email: string | null
  nationality: string | null
  phone: string | null
  photo_url: string | null
  stage: string | null
  submitted_at: string | null
  kakao_id: string | null
}

/* ── Skeleton Card ── */
function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl border border-[#e5e5e7] px-4 py-3 flex items-center gap-3 animate-pulse">
      <div className="w-12 h-12 rounded-full bg-[#f5f5f7] shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="h-3.5 w-28 bg-[#f5f5f7] rounded" />
        <div className="h-2.5 w-20 bg-[#f5f5f7] rounded" />
      </div>
      <div className="h-5 w-16 bg-[#f5f5f7] rounded-full" />
    </div>
  )
}

export default function CandidatesPage() {
  const { authed, waking, login, adminFetch, signedFetch } = useAdminAuth()

  const [candidates, setCandidates] = useState<CandidateRow[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('')
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const sentinelRef = useRef<HTMLDivElement>(null)
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ── Fetch candidates ──
  const fetchCandidates = useCallback(async (reset: boolean = true) => {
    const newOffset = reset ? 0 : offset
    if (reset) {
      setLoading(true)
    } else {
      setLoadingMore(true)
    }
    setError(null)

    try {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(newOffset),
      })
      if (search.trim()) params.set('q', search.trim())
      if (filter) params.set('stage', filter)

      const res = await adminFetch(`${API}/api/admin/candidates?${params}`)
      const json = await res.json()

      if (json.success) {
        const rows: CandidateRow[] = json.data ?? []
        if (reset) {
          setCandidates(rows)
          setOffset(PAGE_SIZE)
        } else {
          setCandidates(prev => [...prev, ...rows])
          setOffset(prev => prev + PAGE_SIZE)
        }
        setHasMore(rows.length >= PAGE_SIZE)
      } else {
        setError('Failed to load candidates')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load candidates')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [offset, search, filter, adminFetch])

  // Initial fetch + filter/search change
  useEffect(() => {
    if (!authed) return
    fetchCandidates(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed, filter])

  // Debounced search
  const handleSearchChange = useCallback((value: string) => {
    setSearch(value)
    if (searchTimeout.current) clearTimeout(searchTimeout.current)
    searchTimeout.current = setTimeout(() => {
      setOffset(0)
      setHasMore(true)
      // trigger refetch - will happen via the effect below
    }, 400)
  }, [])

  // Refetch when search changes (debounced)
  useEffect(() => {
    if (!authed) return
    const timer = setTimeout(() => {
      fetchCandidates(true)
    }, 400)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search])

  // ── Infinite scroll ──
  useEffect(() => {
    if (!sentinelRef.current || !hasMore || loading || loadingMore) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore) {
          fetchCandidates(false)
        }
      },
      { threshold: 0.1 }
    )

    observer.observe(sentinelRef.current)
    return () => observer.disconnect()
  }, [hasMore, loading, loadingMore, fetchCandidates])

  // ── Stage change handler ──
  const handleStageChange = useCallback(async (id: number, stage: string) => {
    try {
      await signedFetch(`${API}/api/admin/candidates/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ stage }),
      })
      setCandidates(prev =>
        prev.map(c => c.id === id ? { ...c, stage } : c)
      )
    } catch {
      // silent
    }
  }, [signedFetch])

  // ── Pull to refresh ──
  const handleRefresh = useCallback(async () => {
    await fetchCandidates(true)
  }, [fetchCandidates])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <PullToRefresh onRefresh={handleRefresh}>
        <div className="px-4 pb-8 pt-safe">

          {/* ── Header ── */}
          <div className="flex items-center gap-3 pt-4 pb-3">
            <Link
              href="/admin/m"
              className="w-9 h-9 rounded-full bg-white border border-[#e5e5e7] flex items-center justify-center shrink-0"
            >
              <ArrowLeft size={16} className="text-[#1d1d1f]" />
            </Link>
            <h1 className="text-xl font-bold text-[#1d1d1f]">Candidates</h1>
            <span className="text-sm text-[#86868b] ml-auto">
              {!loading && candidates.length > 0 && `${candidates.length}+`}
            </span>
          </div>

          {/* ── Search bar ── */}
          <div className="sticky top-0 z-20 bg-[#f5f5f7] pb-2 pt-1">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#86868b]" />
              <input
                type="text"
                value={search}
                onChange={(e) => handleSearchChange(e.target.value)}
                placeholder="Search by name, nationality..."
                className="w-full pl-9 pr-4 py-2.5 rounded-full bg-white border border-[#e5e5e7] text-sm text-[#1d1d1f] placeholder-[#86868b] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 min-h-[44px]"
              />
            </div>
          </div>

          {/* ── Filter tabs ── */}
          <div className="flex gap-2 overflow-x-auto pb-3 scrollbar-hide">
            {FILTER_TABS.map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() => setFilter(tab.value)}
                className={`shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-colors min-h-[36px] ${
                  filter === tab.value
                    ? 'bg-[#1d1d1f] text-white'
                    : 'bg-white border border-[#e5e5e7] text-[#1d1d1f]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* ── Card list ── */}
          <div className="space-y-2">
            {loading ? (
              [1, 2, 3, 4, 5, 6].map(i => <SkeletonCard key={i} />)
            ) : error ? (
              <div className="bg-white rounded-2xl border border-[#e5e5e7] p-8 text-center">
                <p className="text-red-500 text-sm mb-3">{error}</p>
                <button
                  type="button"
                  onClick={() => fetchCandidates(true)}
                  className="px-4 py-2 rounded-full bg-[#0071e3] text-white text-sm font-medium min-h-[44px]"
                >
                  Retry
                </button>
              </div>
            ) : candidates.length === 0 ? (
              <div className="bg-white rounded-2xl border border-[#e5e5e7] p-8 text-center">
                <p className="text-[#86868b] text-sm">No candidates found</p>
                {(search || filter) && (
                  <button
                    type="button"
                    onClick={() => { setSearch(''); setFilter('') }}
                    className="mt-3 text-sm text-[#0071e3] font-medium"
                  >
                    Clear filters
                  </button>
                )}
              </div>
            ) : (
              <>
                {candidates.map((c) => (
                  <CandidateCard
                    key={c.id}
                    candidate={c}
                    onTap={setSelectedId}
                    onStageChange={handleStageChange}
                  />
                ))}

                {/* Infinite scroll sentinel */}
                {hasMore && (
                  <div ref={sentinelRef} className="flex items-center justify-center py-4">
                    {loadingMore && (
                      <Loader2 size={20} className="animate-spin text-[#86868b]" />
                    )}
                  </div>
                )}
              </>
            )}
          </div>

        </div>
      </PullToRefresh>

      {/* ── Candidate Detail slide-up ── */}
      {selectedId !== null && (
        <CandidateDetail
          candidateId={selectedId}
          onClose={() => setSelectedId(null)}
          onStageChange={handleStageChange}
        />
      )}
    </div>
  )
}
