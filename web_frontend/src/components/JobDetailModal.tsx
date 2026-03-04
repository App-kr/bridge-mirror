'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import type { PublicJob, AgeGroup } from '@/types'

const AGE_LABEL: Record<AgeGroup, string> = {
  pre_k: 'Pre-K', kindergarten: 'Kindergarten', elementary: 'Elementary',
  middle: 'Middle School', high: 'High School', adult: 'Adult',
}

function InfoRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  return (
    <div className="flex justify-between items-baseline py-2.5 border-b border-gray-100">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-medium text-gray-900 text-right max-w-[60%]">{value}</span>
    </div>
  )
}

export default function JobDetailModal({
  job,
  isHot,
  onClose,
}: {
  job: PublicJob | null
  isHot?: boolean
  onClose: () => void
}) {
  useEffect(() => {
    if (!job) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handler)
      document.body.style.overflow = ''
    }
  }, [job, onClose])

  if (!job) return null

  const ageLabels = (job.teaching_age ?? []).map((g) => AGE_LABEL[g as AgeGroup] ?? g).join(', ')
  const benefits = Array.isArray(job.employee_benefits)
    ? job.employee_benefits as string[]
    : (job.employee_benefits ? String(job.employee_benefits).split(',').map((s) => s.trim()).filter(Boolean) : [])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto">
        {/* Header */}
        <div className={`sticky top-0 z-10 rounded-t-2xl px-6 py-5 ${isHot ? 'bg-gradient-to-r from-red-500 to-orange-400 text-white' : 'bg-[#1d1d1f] text-white'}`}>
          <button type="button" onClick={onClose}
            className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-full bg-white/20 hover:bg-white/30 text-white text-lg">
            &times;
          </button>
          <p className="text-lg font-extrabold opacity-90">{job.job_id}</p>
          <h2 className="text-xl font-bold mt-1">
            {ageLabels ? `${ageLabels} Teacher` : 'Teaching Position'}
          </h2>
          <p className="text-sm opacity-80 mt-0.5">{job.location}</p>
          {isHot && (
            <span className="inline-block mt-2 text-xs font-bold bg-white text-red-600 px-3 py-1 rounded-full">
              🔥 HOT POSITION
            </span>
          )}
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-0">
          <InfoRow label="Location" value={job.location} />
          <InfoRow label="Job Code" value={job.job_id} />
          <InfoRow label="Starting Date" value={job.starting_date} />
          <InfoRow label="Teaching Age" value={ageLabels || null} />
          <InfoRow label="Class Size" value={job.class_size} />
          <InfoRow label="Working Hours" value={job.working_hours} />
          <InfoRow label="Monthly Salary" value={job.monthly_salary} />
          <InfoRow label="Avg Teaching hrs/week" value={job.teaching_hours_per_week} />
          <InfoRow label="Vacation" value={job.vacation} />
          <InfoRow label="Native Teacher Count" value={job.native_teacher_count} />
          <InfoRow label="Housing" value={job.housing} />
          <InfoRow label="Special Notes" value={job.preferences} />
          <InfoRow label="Type" value={job.employment_type === 'part_time' ? 'Part-time' : 'Full-time'} />
        </div>

        {/* Benefits */}
        {benefits.length > 0 && (
          <div className="px-6 pb-5">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Employee Benefits</p>
            <div className="flex flex-wrap gap-1.5">
              {benefits.map((b, i) => (
                <span key={i} className="text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2.5 py-1 rounded-full">{b}</span>
              ))}
            </div>
          </div>
        )}

        {/* Apply CTA */}
        <div className="sticky bottom-0 bg-white border-t border-gray-100 px-6 py-4 flex gap-3 rounded-b-2xl">
          <button type="button" onClick={onClose}
            className="flex-1 text-sm font-medium text-gray-600 bg-gray-100 py-3 rounded-xl hover:bg-gray-200 transition-colors">
            Close
          </button>
          <Link href="/apply"
            className="flex-1 text-sm font-semibold text-white bg-[#1d1d1f] py-3 rounded-xl hover:bg-[#424245] transition-colors text-center">
            Apply Now
          </Link>
        </div>
      </div>
    </div>
  )
}
