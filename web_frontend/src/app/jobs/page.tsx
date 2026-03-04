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
import type { AgeGroup, PublicJob } from '@/types'

const PER_PAGE = 10

// ── Filters ──
const REGIONS = [
  { label: 'All Regions', value: 'all' },
  { label: 'Seoul', value: 'Seoul' },
  { label: 'Gyeonggi', value: 'Gyeonggi' },
  { label: 'Incheon', value: 'Incheon' },
  { label: 'Busan', value: 'Busan' },
  { label: 'Daegu', value: 'Daegu' },
  { label: 'Daejeon', value: 'Daejeon' },
  { label: 'Gwangju', value: 'Gwangju' },
  { label: 'Other', value: '__other__' },
]
const JOB_TYPES = [
  { label: 'All Types', value: 'all' },
  { label: 'Kindergarten', value: 'kindergarten' },
  { label: 'Elementary', value: 'elementary' },
  { label: 'Middle School', value: 'middle' },
  { label: 'High School', value: 'high' },
  { label: 'Adult', value: 'adult' },
  { label: 'Part-time', value: 'part_time' },
]
const SORT_OPTIONS = [
  { label: 'HOT first', value: 'hot' },
  { label: 'Salary (high)', value: 'salary' },
  { label: 'Fewest hours', value: 'hours' },
  { label: 'Latest', value: 'latest' },
]
const MAJOR_CITIES = ['Seoul', 'Gyeonggi', 'Incheon', 'Busan', 'Daegu', 'Daejeon', 'Gwangju']

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

// ── HOT detection ──
function isAutoHot(job: PublicJob): boolean {
  const vac = job.vacation ?? ''
  const wkMatch = vac.match(/(\d+)\s*weeks?/i)
  if (wkMatch && parseInt(wkMatch[1], 10) * 5 >= 20) return true
  const nums = vac.match(/\d+/g)
  if (nums && Math.max(...nums.map(Number)) >= 20) return true
  if (job.hours_per_day != null && job.hours_per_day <= 8) return true
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

function salaryNum(job: PublicJob): number {
  const m = (job.monthly_salary ?? '').replace(/,/g, '').match(/\d+/)
  return m ? parseInt(m[0], 10) : 0
}

export default function JobsPage() {
  const [allJobs, setAllJobs] = useState<PublicJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [selectedJob, setSelectedJob] = useState<PublicJob | null>(null)

  const [search, setSearch] = useState('')
  const [region, setRegion] = useState('all')
  const [jobType, setJobType] = useState('all')
  const [hotOnly, setHotOnly] = useState(false)
  const [sortBy, setSortBy] = useState('hot')

  const hotSet = useMemo(() => {
    const s = new Set<string>()
    allJobs.forEach((j) => { if (isAutoHot(j)) s.add(j.job_id) })
    return s
  }, [allJobs])

  // Load jobs + URL params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const c = params.get('city')
    const a = params.get('age') as AgeGroup | null
    if (c) {
      const match = REGIONS.find((r) => r.value.toLowerCase() === c.toLowerCase())
      if (match) setRegion(match.value)
    }
    if (a) {
      const match = JOB_TYPES.find((t) => t.value === a)
      if (match) setJobType(match.value)
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

  // Filter + sort
  const filtered = useMemo<PublicJob[]>(() => {
    let jobs = allJobs
    if (hotOnly) jobs = jobs.filter((j) => hotSet.has(j.job_id))

    if (region !== 'all') {
      if (region === '__other__') {
        jobs = jobs.filter((j) => !MAJOR_CITIES.some((c) => (j.location ?? '').toLowerCase().includes(c.toLowerCase())))
      } else {
        jobs = jobs.filter((j) => (j.location ?? '').toLowerCase().includes(region.toLowerCase()))
      }
    }

    if (jobType !== 'all') {
      if (jobType === 'part_time') {
        jobs = jobs.filter((j) => j.employment_type === 'part_time')
      } else {
        jobs = jobs.filter((j) => (j.teaching_age ?? []).includes(jobType as AgeGroup))
      }
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

    if (sortBy === 'salary') jobs = [...jobs].sort((a, b) => salaryNum(b) - salaryNum(a))
    else if (sortBy === 'hours') jobs = [...jobs].sort((a, b) => (a.hours_per_day ?? 99) - (b.hours_per_day ?? 99))
    else if (sortBy === 'latest') { /* already shuffled */ }
    else jobs = [...jobs].sort((a, b) => {
      const aH = hotSet.has(a.job_id) ? 1 : 0
      const bH = hotSet.has(b.job_id) ? 1 : 0
      return bH - aH
    })

    return jobs
  }, [allJobs, hotOnly, region, jobType, search, sortBy, hotSet])

  // HOT interleave
  const interleaved = useMemo(() => {
    const regular = filtered.filter((j) => !hotSet.has(j.job_id))
    const hot = filtered.filter((j) => hotSet.has(j.job_id))
    return interleaveHot(regular, hot)
  }, [filtered, hotSet])

  // Pagination
  const totalPages = Math.max(1, Math.ceil(interleaved.length / PER_PAGE))
  const pageJobs = useMemo(() => {
    const start = (page - 1) * PER_PAGE
    return interleaved.slice(start, start + PER_PAGE)
  }, [interleaved, page])

  useEffect(() => { setPage(1) }, [search, region, jobType, hotOnly, sortBy])

  const hasFilters = region !== 'all' || jobType !== 'all' || hotOnly || search.trim()
  const clearFilters = useCallback(() => {
    setRegion('all'); setJobType('all'); setHotOnly(false); setSearch('')
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
            Verified ESL teaching jobs across Korea. Updated daily.
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

        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <select value={region} onChange={(e) => setRegion(e.target.value)}
            className="bg-[#f5f5f7] text-[#424245] text-sm font-medium rounded-full px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 border-0 cursor-pointer">
            {REGIONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
          <select value={jobType} onChange={(e) => setJobType(e.target.value)}
            className="bg-[#f5f5f7] text-[#424245] text-sm font-medium rounded-full px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 border-0 cursor-pointer">
            {JOB_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
          <button type="button" onClick={() => setHotOnly((v) => !v)}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition-all duration-200 ${
              hotOnly ? 'bg-red-600 text-white' : 'bg-[#f5f5f7] text-[#424245] hover:bg-red-50 hover:text-red-600'}`}>
            HOT
          </button>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}
            className="ml-auto bg-[#f5f5f7] text-[#424245] text-sm font-medium rounded-full px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 border-0 cursor-pointer">
            {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        {/* Tagline */}
        <div className="flex items-center justify-between mb-6">
          <p className="text-base text-[#86868b] italic">
            {loading
              ? 'Loading positions...'
              : 'We have over 3,000 positions available. Apply now and find your perfect match!'}
          </p>
          {hasFilters && (
            <button type="button" onClick={clearFilters} className="text-xs text-blue-600 hover:underline shrink-0 ml-4">Clear filters</button>
          )}
        </div>

        {/* Skeleton */}
        {loading && (
          <div className="grid md:grid-cols-2 gap-5">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="bg-white rounded-2xl border border-gray-200 p-7 space-y-4 h-[280px]">
                <div className="skeleton h-5 w-1/3" />
                <div className="skeleton h-6 w-3/4" />
                <div className="skeleton h-4 w-1/2" />
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
          <div className="grid md:grid-cols-2 gap-5">
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
              .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
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
            <p className="text-xs text-[#86868b] mt-3">One application covers all open positions. We match you with the best fit.</p>
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
