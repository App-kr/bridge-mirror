'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import type { PublicJob, AgeGroup } from '@/types'

const AGE_SHORT: Record<AgeGroup, string> = {
  pre_k: 'Pre-K', kindergarten: 'Kindy', elementary: 'Elem',
  middle: 'Middle', high: 'High', adult: 'Adult',
}

function Row({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null
  return (
    <div className="flex justify-between items-baseline py-[3px]">
      <span className="text-[11px] text-[#86868b] shrink-0">{label}</span>
      <span className="text-[13px] font-semibold text-[#1d1d1f] text-right ml-3 max-w-[65%] truncate">{value}</span>
    </div>
  )
}

export default function JobCard({ job, isHot }: { job: PublicJob; isHot?: boolean }) {
  const [flipped, setFlipped] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const ageLabel = job.teaching_age_raw
    || (job.teaching_age ?? []).map(g => AGE_SHORT[g as AgeGroup] ?? g).join('-')
    || ''

  const benefits: string[] = Array.isArray(job.employee_benefits)
    ? job.employee_benefits
    : (job.employee_benefits ? String(job.employee_benefits).split(',').map(s => s.trim()).filter(Boolean) : [])

  const notes: string[] = Array.isArray(job.notes) ? job.notes : []

  // Click outside → flip back
  useEffect(() => {
    if (!flipped) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setFlipped(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [flipped])

  const border = isHot ? 'border-orange-300 ring-1 ring-orange-100' : 'border-gray-200'

  return (
    <div className="job-card-wrap" ref={ref}>
      <div className={`job-card-inner${flipped ? ' flipped' : ''}`}>

        {/* ══ FRONT ══ */}
        <div className={`job-card-face bg-white rounded-2xl border ${border} flex flex-col p-5`}>
          {isHot && <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-red-500 via-orange-400 to-yellow-400 rounded-t-2xl" />}

          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-bold bg-emerald-500 text-white px-2 py-[2px] rounded-full">OPEN</span>
              {isHot && <span className="text-[11px] font-bold bg-red-600 text-white px-2 py-[2px] rounded-full">🔥 HOT</span>}
            </div>
            <span className="text-[17px] font-extrabold text-[#1d1d1f] tracking-tight">{job.job_id}</span>
          </div>

          <h3 className="text-xl font-bold text-[#1d1d1f] leading-tight">{job.location || 'Korea'}</h3>
          {ageLabel && <p className="text-sm text-[#6e6e73] mt-0.5">{ageLabel}</p>}

          <div className="mt-auto pt-3 space-y-0.5">
            <Row label="Schedule" value={job.working_hours} />
            <Row label="Start" value={job.starting_date} />
          </div>

          <button
            type="button"
            onClick={() => setFlipped(true)}
            className="mt-3 pt-2.5 border-t border-gray-100 text-center text-sm font-semibold text-[#0071e3] hover:text-[#0077ED] transition-colors w-full"
          >
            Details
          </button>
        </div>

        {/* ══ BACK ══ */}
        <div
          className={`job-card-face bg-white rounded-2xl border ${border} flex flex-col p-4 overflow-y-auto`}
          style={{ transform: 'rotateY(180deg)' }}
        >
          <button
            type="button"
            onClick={() => setFlipped(false)}
            className="absolute top-2.5 right-2.5 z-10 w-6 h-6 flex items-center justify-center rounded-full bg-gray-100 hover:bg-gray-200 text-gray-500 text-xs"
          >
            ✕
          </button>

          <div className="flex items-center justify-between mb-0.5 pr-7">
            <h3 className="text-[15px] font-bold text-[#1d1d1f] truncate">{job.location || 'Korea'}</h3>
            <span className="text-xs font-extrabold text-[#1d1d1f] shrink-0 ml-2">{job.job_id}</span>
          </div>
          <div className="mb-2">
            <span className="text-[10px] font-bold bg-emerald-500 text-white px-2 py-[1px] rounded-full">OPEN</span>
          </div>

          <div className="space-y-0 flex-1 min-h-0">
            <Row label="Target" value={ageLabel || null} />
            <Row label="Schedule" value={job.working_hours} />
            <Row label="Start" value={job.starting_date} />
            <Row label="Salary" value={job.monthly_salary} />
            <Row label="Avg Hrs/wk" value={job.teaching_hours_per_week} />
            <Row label="Vacation" value={job.vacation} />
            <Row label="Native Tchr" value={job.native_teacher_count} />
            <Row label="Housing" value={job.housing} />
            <Row label="Class Size" value={job.class_size} />
          </div>

          {notes.length > 0 && (
            <div className="mt-1.5 space-y-0.5">
              {notes.map((n, i) => (
                <p key={i} className="text-[10px] text-amber-700 bg-amber-50 rounded px-2 py-0.5">⚠ {n}</p>
              ))}
            </div>
          )}

          {benefits.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {benefits.map((b, i) => (
                <span key={i} className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-[1px] rounded-full">{b}</span>
              ))}
            </div>
          )}

          <Link
            href="/apply"
            className="mt-2 pt-2 border-t border-gray-100 block text-center text-sm font-semibold
                       bg-[#1d1d1f] text-white rounded-xl py-2 hover:bg-[#424245] transition-colors shrink-0"
            onClick={(e) => e.stopPropagation()}
          >
            Quick Apply
          </Link>
        </div>
      </div>
    </div>
  )
}
