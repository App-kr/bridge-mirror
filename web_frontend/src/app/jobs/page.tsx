'use client'

/**
 * /jobs — Job Board with hero, category tabs, redesigned cards
 *
 * Security: reads `public_jobs` VIEW (anon key, no PII)
 * UX: client-side filtering (instant), Quick Apply panel (no redirect)
 * Motion: stagger card entrance, skeleton wave loading
 */

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import JobCard from '@/components/JobCard'
import ApplyPanel from '@/components/ApplyPanel'
const API = ''
import { fadeInUp, staggerContainer, defaultViewport } from '@/lib/animations'
import type { AgeGroup, PublicJob } from '@/types'

// ── Category tabs ──
const CATEGORIES = [
  { label: 'All', value: 'all' },
  { label: 'Seoul', value: 'Seoul' },
  { label: 'Gyeonggi', value: 'Gyeonggi' },
  { label: 'Busan', value: 'Busan' },
  { label: 'Incheon', value: 'Incheon' },
  { label: 'Kindergarten', value: 'kindergarten' },
  { label: 'Elementary', value: 'elementary' },
]

const SORT_OPTIONS = [
  { label: 'HOT first', value: 'hot' },
  { label: 'Salary high', value: 'salary' },
  { label: 'Fewest hours', value: 'hours' },
]

function salaryNum(job: PublicJob): number {
  const m = (job.monthly_salary ?? '').replace(/,/g, '').match(/\d+/)
  return m ? parseInt(m[0], 10) : 0
}

export default function JobsPage() {
  const [allJobs, setAllJobs] = useState<PublicJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [panelJob, setPanelJob] = useState<PublicJob | null>(null)

  // Filters
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')
  const [hotOnly, setHotOnly] = useState(false)
  const [sortBy, setSortBy] = useState('hot')

  // ── Load + URL params ──
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const c = params.get('city')
    const a = params.get('age') as AgeGroup | null
    if (c) {
      const match = CATEGORIES.find((cat) => cat.value.toLowerCase() === c.toLowerCase())
      if (match) setCategory(match.value)
    }
    if (a) {
      const match = CATEGORIES.find((cat) => cat.value === a)
      if (match) setCategory(match.value)
    }

    setLoading(true)
    fetch(`${API}/api/jobs?limit=500`)
      .then((r) => r.json())
      .then((j) => {
        if (j.success && Array.isArray(j.data)) {
          setAllJobs(j.data)
          setError(null)
        } else {
          setError('Failed to load positions. Please try again.')
        }
      })
      .catch(() => setError('Failed to load positions. Please try again.'))
      .finally(() => setLoading(false))
  }, [])

  // ── Filtering ──
  const filtered = useMemo<PublicJob[]>(() => {
    let jobs = allJobs

    if (hotOnly) jobs = jobs.filter((j) => j.is_hot)

    // Category can be a city or an age group
    if (category !== 'all') {
      const isAge = ['kindergarten', 'elementary', 'pre_k', 'middle', 'high'].includes(category)
      if (isAge) {
        jobs = jobs.filter((j) => (j.teaching_age ?? []).includes(category as AgeGroup))
      } else {
        jobs = jobs.filter((j) =>
          (j.location ?? '').toLowerCase().includes(category.toLowerCase())
        )
      }
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase()
      jobs = jobs.filter((j) =>
        (j.location ?? '').toLowerCase().includes(q) ||
        (j.job_id ?? '').toLowerCase().includes(q) ||
        (j.preferences ?? '').toLowerCase().includes(q) ||
        (j.teaching_age ?? []).some((g) => g.toLowerCase().includes(q))
      )
    }

    if (sortBy === 'salary') jobs = [...jobs].sort((a, b) => salaryNum(b) - salaryNum(a))
    else if (sortBy === 'hours') jobs = [...jobs].sort((a, b) => (a.hours_per_day ?? 99) - (b.hours_per_day ?? 99))
    else jobs = [...jobs].sort((a, b) => {
      if (b.is_hot !== a.is_hot) return Number(b.is_hot) - Number(a.is_hot)
      return (a.hours_per_day ?? 99) - (b.hours_per_day ?? 99)
    })

    return jobs
  }, [allJobs, hotOnly, category, search, sortBy])

  const hasFilters = category !== 'all' || hotOnly || search.trim()
  const clearFilters = () => { setCategory('all'); setHotOnly(false); setSearch('') }

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
            Verified ESL teaching jobs across Korea.
            Updated daily.
          </motion.p>

          {/* Search bar */}
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
              <button
                type="button"
                onClick={() => setSearch('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-white/40 hover:text-white"
              >
                ✕
              </button>
            )}
          </motion.div>
        </div>
      </motion.section>

      {/* ── Main content ── */}
      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 py-8">

        {/* Category tabs */}
        <div className="flex items-center gap-2 flex-wrap mb-6">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              type="button"
              onClick={() => setCategory(cat.value)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
                category === cat.value
                  ? 'bg-[#1d1d1f] text-white'
                  : 'bg-[#f5f5f7] text-[#424245] hover:bg-[#e8e8ed]'
              }`}
            >
              {cat.label}
            </button>
          ))}

          {/* HOT toggle */}
          <button
            type="button"
            onClick={() => setHotOnly((v) => !v)}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition-all duration-200 ml-1 ${
              hotOnly
                ? 'bg-red-600 text-white'
                : 'bg-[#f5f5f7] text-[#424245] hover:bg-red-50 hover:text-red-600'
            }`}
          >
            🔥 HOT
          </button>

          {/* Sort */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="ml-auto bg-[#f5f5f7] text-[#424245] text-sm font-medium rounded-full
                       px-4 py-2 focus:outline-none focus:ring-2 focus:ring-[#0071e3] cursor-pointer
                       border-0"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* Results count + clear */}
        <div className="flex items-center justify-between mb-6">
          <div className="text-sm text-[#86868b]">
            {loading ? (
              <span className="animate-pulse">Loading positions...</span>
            ) : (
              <span>
                <span className="text-[#1d1d1f] font-semibold">{filtered.length}</span>
                {' '}of {allJobs.length} positions
              </span>
            )}
          </div>
          {hasFilters && (
            <button
              type="button"
              onClick={clearFilters}
              className="text-xs text-[#0071e3] hover:underline"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Skeleton loading with wave effect */}
        {loading && (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="rounded-2xl p-5 space-y-3">
                <div className="skeleton h-4 w-1/3" />
                <div className="skeleton h-5 w-3/4" />
                <div className="skeleton h-4 w-1/2" />
                <div className="skeleton h-4 w-2/3" />
                <div className="skeleton h-10 w-full mt-2" />
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

        {!loading && !error && filtered.length === 0 && (
          <div className="text-center py-20 space-y-3">
            <p className="text-[#86868b] text-lg">No positions match your filters.</p>
            {hasFilters && (
              <button type="button" onClick={clearFilters} className="text-sm text-[#0071e3] hover:underline">
                Clear all filters →
              </button>
            )}
          </div>
        )}

        {/* Job grid — stagger entrance */}
        {!loading && filtered.length > 0 && (
          <motion.div
            className="grid md:grid-cols-2 lg:grid-cols-3 gap-4"
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.1 }}
          >
            {filtered.map((job) => (
              <motion.div key={job.job_id} variants={fadeInUp}>
                <JobCard
                  job={job}
                  onQuickApply={() => setPanelJob(job)}
                />
              </motion.div>
            ))}
          </motion.div>
        )}

        {/* Apply CTA */}
        {!loading && filtered.length > 0 && (
          <motion.div
            className="text-center mt-12 mb-4"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <Link href="/apply" className="btn-primary text-base px-8 py-3">
              Apply to All Positions →
            </Link>
            <p className="text-xs text-[#86868b] mt-3">
              One application covers all open positions. We match you with the best fit.
            </p>
          </motion.div>
        )}
      </div>

      {/* Quick Apply slide panel */}
      <ApplyPanel job={panelJob} onClose={() => setPanelJob(null)} />
    </>
  )
}
