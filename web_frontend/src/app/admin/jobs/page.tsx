'use client'

/**
 * /admin/jobs — Job Management
 * Open/Close 토글, HOT 토글, 검색, 필터, 페이지네이션
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import AdminNav from '@/components/admin/AdminNav'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import type { PublicJob, AgeGroup } from '@/types'

const API = API_URL
const PER_PAGE = 30

const AGE_LABEL: Record<AgeGroup, string> = {
  pre_k: 'Pre-K', kindergarten: 'Kinder', elementary: 'Elem',
  middle: 'Middle', high: 'High', adult: 'Adult',
}

const STATUS_FILTERS = [
  { label: 'All', value: 'all' },
  { label: 'Open', value: 'open' },
  { label: 'Closed', value: 'closed' },
]

export default function AdminJobsPage() {
  const { authed, login, signedFetch, waking } = useAdminAuth()

  const [jobs, setJobs] = useState<PublicJob[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(1)

  // toggling states
  const [togglingStatus, setTogglingStatus] = useState<Set<string>>(new Set())
  const [togglingHot, setTogglingHot] = useState<Set<string>>(new Set())

  const fetchJobs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await signedFetch(`${API}/api/jobs?limit=2000`)
      const json = await res.json()
      if (json.success && Array.isArray(json.data)) {
        setJobs(json.data)
      } else {
        setError('Failed to load jobs')
      }
    } catch {
      setError('Failed to load jobs')
    } finally {
      setLoading(false)
    }
  }, [signedFetch])

  useEffect(() => {
    if (authed) fetchJobs()
  }, [authed, fetchJobs])

  // Filtered + searched
  const filtered = useMemo(() => {
    let list = jobs

    if (statusFilter !== 'all') {
      list = list.filter((j) => (j.status ?? 'open') === statusFilter)
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase()
      list = list.filter((j) =>
        (j.job_id ?? '').toLowerCase().includes(q) ||
        (j.location ?? '').toLowerCase().includes(q) ||
        (j.monthly_salary ?? '').toLowerCase().includes(q) ||
        (j.teaching_age ?? []).some((g) => g.toLowerCase().includes(q))
      )
    }

    return list
  }, [jobs, statusFilter, search])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE))
  const pageJobs = useMemo(() => {
    const start = (page - 1) * PER_PAGE
    return filtered.slice(start, start + PER_PAGE)
  }, [filtered, page])

  useEffect(() => { setPage(1) }, [search, statusFilter])

  const flash = (msg: string) => {
    setActionMsg(msg)
    setTimeout(() => setActionMsg(null), 3000)
  }

  // Toggle status (open ↔ closed)
  const toggleStatus = useCallback(async (job: PublicJob) => {
    const jobId = job.job_id.replace(/\D/g, '')
    if (!jobId) return
    const newStatus = (job.status ?? 'open') === 'open' ? 'closed' : 'open'

    setTogglingStatus((s) => new Set(s).add(job.job_id))
    try {
      const res = await signedFetch(`${API}/api/admin/jobs/${jobId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status: newStatus }),
      })
      if (res.ok) {
        setJobs((prev) => prev.map((j) => j.job_id === job.job_id ? { ...j, status: newStatus } : j))
        flash(`${job.job_id} → ${newStatus}`)
      } else {
        const err = await res.json().catch(() => null)
        flash(`Error: ${err?.message ?? res.statusText}`)
      }
    } catch {
      flash('Network error')
    } finally {
      setTogglingStatus((s) => { const n = new Set(s); n.delete(job.job_id); return n })
    }
  }, [signedFetch])

  // Toggle HOT
  const toggleHot = useCallback(async (job: PublicJob) => {
    const jobId = job.job_id.replace(/\D/g, '')
    if (!jobId) return

    setTogglingHot((s) => new Set(s).add(job.job_id))
    try {
      const res = await signedFetch(`${API}/api/admin/jobs/${jobId}/hot`, {
        method: 'PUT',
      })
      if (res.ok) {
        setJobs((prev) => prev.map((j) => j.job_id === job.job_id ? { ...j, is_hot: !j.is_hot } : j))
        flash(`${job.job_id} HOT → ${!job.is_hot ? 'ON' : 'OFF'}`)
      } else {
        const err = await res.json().catch(() => null)
        flash(`Error: ${err?.message ?? res.statusText}`)
      }
    } catch {
      flash('Network error')
    } finally {
      setTogglingHot((s) => { const n = new Set(s); n.delete(job.job_id); return n })
    }
  }, [signedFetch])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  const openCount = jobs.filter((j) => (j.status ?? 'open') === 'open').length
  const closedCount = jobs.filter((j) => (j.status ?? 'open') === 'closed').length

  return (
    <div className="max-w-[1400px] mx-auto px-6 py-8">
      <AdminNav active="/admin/jobs" />

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Jobs Management</h1>
          <p className="text-sm text-gray-500 mt-1">
            Total {jobs.length} &middot; Open {openCount} &middot; Closed {closedCount}
          </p>
        </div>
        {actionMsg && (
          <div className="text-sm font-medium text-green-700 bg-green-50 border border-green-200 px-4 py-2 rounded-lg">
            {actionMsg}
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search job code, city, age..."
          className="input max-w-xs text-sm"
        />

        <div className="flex gap-1">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => setStatusFilter(f.value)}
              className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
                statusFilter === f.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <span className="text-sm text-gray-400 ml-auto">
          {filtered.length} results &middot; Page {page}/{totalPages}
        </span>
      </div>

      {loading && <p className="text-center py-10 text-gray-400 animate-pulse">Loading...</p>}
      {error && <p className="text-center py-10 text-red-500">{error}</p>}

      {!loading && !error && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="py-3 px-3">Job Code</th>
                <th className="py-3 px-3">Location</th>
                <th className="py-3 px-3">Age Group</th>
                <th className="py-3 px-3">Start</th>
                <th className="py-3 px-3">Hours</th>
                <th className="py-3 px-3">Salary</th>
                <th className="py-3 px-3 text-center">HOT</th>
                <th className="py-3 px-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody>
              {pageJobs.map((job) => {
                const ages = (job.teaching_age ?? []).map((g) => AGE_LABEL[g as AgeGroup] ?? g).join(', ')
                const isOpen = (job.status ?? 'open') === 'open'
                let infoCount = 0
                if (job.starting_date) infoCount++
                if (job.working_hours) infoCount++
                if (job.monthly_salary) infoCount++
                if (job.teaching_age && job.teaching_age.length > 0) infoCount++
                const lowInfo = infoCount < 3
                return (
                  <tr key={job.job_id} className={`border-b border-gray-100 hover:bg-gray-50 transition-colors ${!isOpen ? 'opacity-50' : ''}`}>
                    <td className="py-3 px-3 font-bold text-blue-600">
                      {job.job_id}
                      {lowInfo && <span className="ml-1 text-[10px] text-amber-600 font-normal" title="정보 부족 — Job Board에 미표시">⚠</span>}
                    </td>
                    <td className="py-3 px-3 text-gray-700">{job.location ?? '-'}</td>
                    <td className="py-3 px-3 text-gray-700">{ages || '-'}</td>
                    <td className="py-3 px-3 text-gray-600">{job.starting_date ?? '-'}</td>
                    <td className="py-3 px-3 text-gray-600">{job.working_hours ?? '-'}</td>
                    <td className="py-3 px-3 text-gray-600">{job.monthly_salary ?? '-'}</td>
                    <td className="py-3 px-3 text-center">
                      <button
                        type="button"
                        onClick={() => toggleHot(job)}
                        disabled={togglingHot.has(job.job_id)}
                        className={`px-2 py-1 text-xs rounded-full font-semibold transition-colors ${
                          job.is_hot
                            ? 'bg-red-100 text-red-700 hover:bg-red-200'
                            : 'bg-gray-100 text-gray-400 hover:bg-gray-200'
                        } disabled:opacity-50`}
                      >
                        {togglingHot.has(job.job_id) ? '...' : job.is_hot ? '🔥 HOT' : '—'}
                      </button>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <button
                        type="button"
                        onClick={() => toggleStatus(job)}
                        disabled={togglingStatus.has(job.job_id)}
                        className={`px-3 py-1 text-xs rounded-full font-semibold transition-colors ${
                          isOpen
                            ? 'bg-green-100 text-green-700 hover:bg-green-200'
                            : 'bg-gray-200 text-gray-500 hover:bg-gray-300'
                        } disabled:opacity-50`}
                      >
                        {togglingStatus.has(job.job_id) ? '...' : isOpen ? 'Open' : 'Closed'}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <nav className="flex items-center justify-center gap-1 mt-6">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-3 py-2 text-sm rounded-lg disabled:opacity-30 text-gray-600 hover:bg-gray-100"
          >
            ← Prev
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
                <button
                  key={item}
                  type="button"
                  onClick={() => setPage(item as number)}
                  className={`w-9 h-9 text-sm rounded-lg font-medium transition-colors ${
                    page === item ? 'bg-[#1d1d1f] text-white' : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {item}
                </button>
              )
            )}
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-3 py-2 text-sm rounded-lg disabled:opacity-30 text-gray-600 hover:bg-gray-100"
          >
            Next →
          </button>
        </nav>
      )}
    </div>
  )
}
