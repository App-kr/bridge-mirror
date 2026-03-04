'use client'

import { useEffect, useCallback } from 'react'
import Link from 'next/link'
import type { PublicJob, AgeGroup } from '@/types'

const AGE_SHORT: Record<AgeGroup, string> = {
  pre_k: 'Pre-K', kindergarten: 'Kindy', elementary: 'Elem',
  middle: 'Middle', high: 'High', adult: 'Adult',
}

function DetailRow({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null
  return (
    <div className="flex justify-between items-baseline py-2 border-b border-gray-50 last:border-0">
      <span className="text-sm text-[#86868b] shrink-0">{label}</span>
      <span className="text-base font-semibold text-[#1d1d1f] text-right ml-4 max-w-[65%]">{value}</span>
    </div>
  )
}

export default function JobDetailModal({
  job,
  isHot,
  onClose,
}: {
  job: PublicJob
  isHot?: boolean
  onClose: () => void
}) {
  const ageLabel = job.teaching_age_raw
    || (job.teaching_age ?? []).map(g => AGE_SHORT[g as AgeGroup] ?? g).join(' - ')
    || null

  const benefits: string[] = Array.isArray(job.employee_benefits)
    ? job.employee_benefits
    : (job.employee_benefits ? String(job.employee_benefits).split(',').map(s => s.trim()).filter(Boolean) : [])

  const notes: string[] = Array.isArray(job.notes) ? job.notes : []

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [handleKeyDown])

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6"
      onClick={onClose}
    >
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/50" />

      {/* Modal */}
      <div
        className="job-modal-content relative bg-white rounded-2xl w-full max-w-[520px] max-h-[90vh] overflow-y-auto p-8 z-10"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-full bg-gray-100 hover:bg-gray-200 text-gray-500 text-sm transition-colors"
        >
          &#x2715;
        </button>

        {/* Header */}
        <div className="pr-10 mb-1">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-[#1d1d1f]">{job.location || 'Korea'}</h2>
            <span className="text-lg font-extrabold text-[#1d1d1f]">{job.job_id}</span>
          </div>
          <div className="flex items-center gap-1.5 mt-2">
            <span className="text-[11px] font-bold bg-emerald-500 text-white px-2.5 py-[3px] rounded-full">OPEN</span>
            {isHot && <span className="text-[11px] font-bold bg-orange-500 text-white px-2.5 py-[3px] rounded-full">HOT</span>}
          </div>
        </div>

        <hr className="my-5 border-gray-200" />

        {/* Detail rows */}
        <div className="space-y-0">
          <DetailRow label="Target" value={ageLabel} />
          <DetailRow label="Schedule" value={job.working_hours} />
          <DetailRow label="Start" value={job.starting_date} />
          <DetailRow label="Salary" value={job.monthly_salary} />
          <DetailRow label="Avg Hrs/wk" value={job.teaching_hours_per_week} />
          <DetailRow label="Vacation" value={job.vacation} />
          <DetailRow label="Native Tchr" value={job.native_teacher_count} />
          <DetailRow label="Housing" value={job.housing} />
          <DetailRow label="Class Size" value={job.class_size} />
        </div>

        {/* Notes */}
        {notes.length > 0 && (
          <>
            <hr className="my-5 border-gray-200" />
            <div className="space-y-1.5">
              {notes.map((n, i) => (
                <p key={i} className="text-sm text-amber-700">&#x26A0; {n}</p>
              ))}
            </div>
          </>
        )}

        {/* Benefits */}
        {benefits.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {benefits.map((b, i) => (
              <span key={i} className="text-xs bg-gray-100 text-gray-600 px-3 py-1.5 rounded-full">{b}</span>
            ))}
          </div>
        )}

        <hr className="my-5 border-gray-200" />

        {/* Action buttons */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-3 rounded-xl border border-gray-300 text-sm font-semibold text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
          <Link
            href="/apply"
            className="flex-1 py-3 rounded-xl bg-[#1d1d1f] text-white text-sm font-semibold text-center hover:bg-[#424245] transition-colors"
          >
            Apply &#x2192;
          </Link>
        </div>
      </div>
    </div>
  )
}
