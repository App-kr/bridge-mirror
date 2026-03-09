'use client'

/**
 * /jobs — Job Board
 * Weekly seeded shuffle · HOT interleaving · Popup modal · Info filtering
 */

import { useEffect, useMemo, useState, useCallback } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import JobCard from '@/components/JobCard'
import JobDetailModal from '@/components/JobDetailModal'
import { fadeInUp, defaultViewport } from '@/lib/animations'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import type { AgeGroup, PublicJob } from '@/types'

const PER_PAGE = 10

// ── Filters ──
const AGE_GROUPS = [
  { label: 'All Ages', value: 'all' },
  { label: 'Kindergarten', value: 'kindergarten' },
  { label: 'Elementary', value: 'elementary' },
  { label: 'Middle School', value: 'middle' },
  { label: 'High School', value: 'high' },
  { label: 'Adult', value: 'adult' },
]

// ── Weekly seed (Monday 00:00 KST) ──
function getWeekSeed(): number {
  const now = new Date()
  const utc = now.getTime() + now.getTimezoneOffset() * 60000
  const kst = new Date(utc + 9 * 3600000)
  const year = kst.getFullYear()
  const day = kst.getDay()
  const daysSinceMonday = (day + 6) % 7
  const monday = new Date(kst.getFullYear(), kst.getMonth(), kst.getDate() - daysSinceMonday)
  const jan1 = new Date(year, 0, 1)
  const weekNum = Math.ceil(((monday.getTime() - jan1.getTime()) / 86400000 + 1) / 7)
  return year * 100 + weekNum
}

function seededShuffle<T>(arr: T[], seed: number): T[] {
  const result = [...arr]
  let s = seed
  const rng = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 0x100000000 }
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[result[i], result[j]] = [result[j], result[i]]
  }
  return result
}

// ── HOT detection: working hours ≤7h OR vacation ≥20 days ──
function isAutoHot(job: PublicJob): boolean {
  // 1) Working hours ≤ 7h — parse "09:00~16:00" style
  const wh = job.working_hours ?? ''
  const timeMatch = wh.match(/(\d{1,2}):(\d{2})\s*[~\-–—]\s*(\d{1,2}):(\d{2})/)
  if (timeMatch) {
    const start = parseInt(timeMatch[1], 10) + parseInt(timeMatch[2], 10) / 60
    const end = parseInt(timeMatch[3], 10) + parseInt(timeMatch[4], 10) / 60
    if (end - start > 0 && end - start <= 7) return true
  }
  // 2) Vacation ≥ 20 days
  const vac = job.vacation ?? ''
  const wkMatch = vac.match(/(\d+)\s*weeks?/i)
  if (wkMatch && parseInt(wkMatch[1], 10) * 5 >= 20) return true
  const nums = vac.match(/\d+/g)
  if (nums && Math.max(...nums.map(Number)) >= 20) return true
  return false
}

// ── HOT interleaving: 3 regular → 1 HOT ──
function interleaveHot(regular: PublicJob[], hot: PublicJob[]): PublicJob[] {
  const result: PublicJob[] = []
  let ri = 0, hi = 0
  while (ri < regular.length) {
    for (let i = 0; i < 3 && ri < regular.length; i++) result.push(regular[ri++])
    if (hi < hot.length) result.push(hot[hi++])
  }
  while (hi < hot.length) result.push(hot[hi++])
  return result
}

// ── Info-sufficient filter (≥3 of 4 key fields) ──
function hasEnoughInfo(job: PublicJob): boolean {
  let c = 0
  if (job.starting_date) c++
  if (job.working_hours) c++
  if (job.monthly_salary) c++
  if (job.teaching_age && job.teaching_age.length > 0) c++
  return c >= 3
}

// ── Salary parser for sorting (returns millions, negative = low priority) ──
function parseSalaryMillions(salary: string | null): number {
  if (!salary) return -2
  const s = salary.toLowerCase()
  // Hourly rate → back
  if (s.includes('/hour') || s.includes('per hour') || s.includes('시간')) return -1
  // Extract numbers followed by 'm' (millions): "2,40m" "2.60m" "3.00m"
  const mParts = s.match(/(\d[.,]?\d*)\s*m/gi)
  if (mParts && mParts.length > 0) {
    const vals = mParts.map(p => parseFloat(p.replace(/m/i, '').replace(',', '.')))
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length
    if (avg > 0 && avg <= 1.5) return -3 // ≤1.5m → very back
    return avg
  }
  // Large plain numbers (2,400,000 etc)
  const plain = s.replace(/,/g, '').match(/(\d{6,})/)
  if (plain) {
    const m = parseInt(plain[1], 10) / 1000000
    if (m > 0 && m <= 1.5) return -3
    return m
  }
  return -2
}

export default function JobsPage() {
  const { authed } = useAdminAuth()
  const [allJobs, setAllJobs] = useState<PublicJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [selectedJob, setSelectedJob] = useState<PublicJob | null>(null)
  const [shuffleSeed, setShuffleSeed] = useState<number | null>(null)

  const [search, setSearch] = useState('')
  const [ageFilter, setAgeFilter] = useState('all')
  const [hotOnly, setHotOnly] = useState(false)

  const handleAdminShuffle = useCallback(() => {
    setShuffleSeed(Math.floor(Math.random() * 999999))
    setPage(1)
  }, [])

  const hotSet = useMemo(() => {
    const s = new Set<string>()
    allJobs.forEach((j) => { if (isAutoHot(j)) s.add(j.job_id) })
    return s
  }, [allJobs])

  // Load jobs + URL params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const a = params.get('age') as AgeGroup | null
    if (a) {
      const match = AGE_GROUPS.find((t) => t.value === a)
      if (match) setAgeFilter(match.value)
    }

    setLoading(true)
    fetch('/api/jobs?limit=2000')
      .then((r) => r.json())
      .then((j) => {
        if (j.success && Array.isArray(j.data)) {
          const sufficient = (j.data as PublicJob[]).filter(hasEnoughInfo)
          const shuffled = seededShuffle(sufficient, getWeekSeed())
          setAllJobs(shuffled)
          setError(null)
        } else {
          setError('Failed to load positions.')
        }
      })
      .catch(() => setError('Failed to load positions.'))
      .finally(() => setLoading(false))
  }, [])

  // Re-shuffle when admin presses shuffle button
  useEffect(() => {
    if (shuffleSeed === null) return
    setAllJobs(prev => seededShuffle([...prev], shuffleSeed))
  }, [shuffleSeed])

  // Filter
  const filtered = useMemo<PublicJob[]>(() => {
    let jobs = allJobs
    if (hotOnly) jobs = jobs.filter((j) => hotSet.has(j.job_id))

    if (ageFilter !== 'all') {
      jobs = jobs.filter((j) => (j.teaching_age ?? []).includes(ageFilter as AgeGroup))
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase()
      jobs = jobs.filter((j) =>
        (j.location ?? '').toLowerCase().includes(q) ||
        (j.job_id ?? '').toLowerCase().includes(q) ||
        (j.monthly_salary ?? '').toLowerCase().includes(q) ||
        (j.teaching_age ?? []).some((g) => g.toLowerCase().includes(q))
      )
    }

    return jobs
  }, [allJobs, hotOnly, ageFilter, search, hotSet])

  // Sort by salary desc, then HOT interleave
  const interleaved = useMemo(() => {
    const bySalary = (a: PublicJob, b: PublicJob) => {
      const aEmpty = !a.raw_text ? 1 : 0
      const bEmpty = !b.raw_text ? 1 : 0
      if (aEmpty !== bEmpty) return aEmpty - bEmpty
      return parseSalaryMillions(b.monthly_salary) - parseSalaryMillions(a.monthly_salary)
    }
    const regular = filtered.filter((j) => !hotSet.has(j.job_id)).sort(bySalary)
    const hot = filtered.filter((j) => hotSet.has(j.job_id)).sort(bySalary)
    return interleaveHot(regular, hot)
  }, [filtered, hotSet])

  // Pagination
  const totalPages = Math.max(1, Math.ceil(interleaved.length / PER_PAGE))
  const pageJobs = useMemo(() => {
    const start = (page - 1) * PER_PAGE
    return interleaved.slice(start, start + PER_PAGE)
  }, [interleaved, page])

  useEffect(() => { setPage(1) }, [search, ageFilter, hotOnly])

  const hasFilters = ageFilter !== 'all' || hotOnly || search.trim()
  const clearFilters = useCallback(() => {
    setAgeFilter('all'); setHotOnly(false); setSearch('')
  }, [])

  const goPage = useCallback((p: number) => {
    setPage(p)
    window.scrollTo({ top: 400, behavior: 'smooth' })
  }, [])

  return (
    <>
      {/* ── Hero ── */}
      <motion.section
        className="bg-[#1d1d1f] text-white py-16 sm:py-20"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <div className="max-w-[1100px] mx-auto px-4 sm:px-6 text-center">
          <motion.h1
            className="text-4xl sm:text-5xl font-black leading-tight mb-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            Open Positions
          </motion.h1>
          <motion.p
            className="text-white/60 text-lg max-w-xl mx-auto mb-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            Verified ESL teaching jobs across Korea
          </motion.p>
          <motion.div
            className="max-w-xl mx-auto relative"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by city, job code, age group..."
              className="w-full px-5 py-3.5 bg-white/10 border border-white/20 rounded-full
                         text-white placeholder:text-white/40 text-sm
                         focus:outline-none focus:bg-white/15 focus:border-white/40 transition-all"
            />
            {search && (
              <button type="button" onClick={() => setSearch('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-white/40 hover:text-white">&times;</button>
            )}
          </motion.div>
        </div>
      </motion.section>

      {/* ── Main ── */}
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 py-8">

        {/* Tagline + Filters */}
        <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
          <div>
            {loading ? (
              <p style={{ fontSize: 16, color: '#9ca3af' }}>Loading positions...</p>
            ) : (
              <>
                <p style={{ margin: 0, fontSize: 16, fontWeight: 400, color: '#9ca3af' }}>
                  {(interleaved.length + 4000).toLocaleString()} Jobs Available
                </p>
                <p style={{ margin: '4px 0 0', fontSize: 14, fontStyle: 'italic' }}>
                  <span style={{ background: 'linear-gradient(90deg, #6b7280, #2563EB)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    Welcome — we love teachers who are passionate about what they do.
                  </span>
                </p>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <select value={ageFilter} onChange={(e) => setAgeFilter(e.target.value)}
              className="cursor-pointer focus:outline-none"
              style={{
                border: '1px solid #e5e7eb',
                borderRadius: 8,
                padding: '8px 16px',
                fontSize: 14,
                color: '#374151',
                background: '#fff',
              }}>
              {AGE_GROUPS.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
            </select>
            <button type="button" onClick={() => setHotOnly((v) => !v)}
              className="cursor-pointer"
              style={{
                border: hotOnly ? '1px solid #ea580c' : '1px solid #e5e7eb',
                borderRadius: 8,
                padding: '8px 16px',
                fontSize: 14,
                fontWeight: 600,
                color: hotOnly ? '#ea580c' : '#374151',
                background: '#fff',
                transition: 'all 0.15s',
              }}>
              HOT
            </button>
            {authed && (
              <button
                type="button"
                onClick={handleAdminShuffle}
                title="관리자: 랜덤 셔플"
                style={{
                  border: '1px solid #7c3aed',
                  borderRadius: 8,
                  padding: '8px 14px',
                  fontSize: 13,
                  fontWeight: 600,
                  color: '#7c3aed',
                  background: '#faf5ff',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = '#ede9fe' }}
                onMouseLeave={e => { e.currentTarget.style.background = '#faf5ff' }}
              >
                ⇌ 바꾸기
              </button>
            )}
          </div>
        </div>

        {/* Skeleton */}
        {loading && (
          <div className="grid md:grid-cols-2 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="bg-white space-y-4 h-[280px]" style={{ borderRadius: 12, padding: 32, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
                <div className="skeleton h-4 w-1/4" />
                <div className="skeleton h-7 w-1/2" />
                <div className="skeleton h-4 w-1/3" />
                <div className="skeleton h-4 w-2/3 mt-auto" />
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="text-center py-20 text-red-500">
            {error}
            <button type="button" onClick={() => window.location.reload()} className="block mx-auto mt-2 text-sm underline">Retry</button>
          </div>
        )}

        {!loading && !error && interleaved.length === 0 && (
          <div className="text-center py-20 space-y-3">
            <p className="text-[#86868b] text-lg">No positions match your filters.</p>
            {hasFilters && (
              <button type="button" onClick={clearFilters} className="text-sm text-blue-600 hover:underline">Clear all filters</button>
            )}
          </div>
        )}

        {/* ── Job Grid: 2 columns desktop, 1 mobile ── */}
        {!loading && pageJobs.length > 0 && (
          <div className="grid md:grid-cols-2 gap-6">
            {pageJobs.map((job, i) => (
              <JobCard
                key={`${job.job_id}-${i}`}
                job={job}
                isHot={hotSet.has(job.job_id)}
                onDetails={() => setSelectedJob(job)}
              />
            ))}
          </div>
        )}

        {/* ── Pagination ── */}
        {!loading && totalPages > 1 && (
          <nav className="flex items-center justify-center gap-1 mt-10">
            <button type="button" onClick={() => goPage(page - 1)} disabled={page <= 1}
              className="px-3 py-2 text-sm rounded-lg disabled:opacity-30 disabled:cursor-not-allowed text-gray-600 hover:bg-gray-100 transition-colors">
              &laquo;
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter((p) => p === 1 || Math.abs(p - page) <= 2)
              .reduce<(number | string)[]>((acc, p, idx, arr) => {
                if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push('...')
                acc.push(p)
                return acc
              }, [])
              .map((item, idx) =>
                item === '...' ? (
                  <span key={`dot-${idx}`} className="px-2 text-gray-400 text-sm">...</span>
                ) : (
                  <button key={item} type="button" onClick={() => goPage(item as number)}
                    className={`w-9 h-9 text-sm rounded-lg font-medium transition-colors ${
                      page === item ? 'bg-[#1d1d1f] text-white' : 'text-gray-600 hover:bg-gray-100'}`}>
                    {item}
                  </button>
                )
              )}
            <button type="button" onClick={() => goPage(page + 1)} disabled={page >= totalPages}
              className="px-3 py-2 text-sm rounded-lg disabled:opacity-30 disabled:cursor-not-allowed text-gray-600 hover:bg-gray-100 transition-colors">
              &raquo;
            </button>
          </nav>
        )}

        {/* Apply CTA */}
        {!loading && interleaved.length > 0 && (
          <motion.div className="text-center mt-12 mb-4" variants={fadeInUp} initial="hidden" whileInView="visible" viewport={defaultViewport}>
            <Link href="/apply" className="btn-primary text-base px-8 py-3">Apply to All Positions</Link>
            <p className="text-xs text-[#86868b] mt-3">Apply now! We match you with the best fit.</p>
          </motion.div>
        )}
      </div>

      {/* ── Detail Modal ── */}
      {selectedJob && (
        <JobDetailModal
          job={selectedJob}
          isHot={hotSet.has(selectedJob.job_id)}
          onClose={() => setSelectedJob(null)}
        />
      )}
    </>
  )
}
