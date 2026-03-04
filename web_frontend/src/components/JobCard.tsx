'use client'

import type { PublicJob, AgeGroup } from '@/types'

const AGE_LABEL: Record<AgeGroup, string> = {
  pre_k:        'Pre-K',
  kindergarten: 'Kindergarten',
  elementary:   'Elementary',
  middle:       'Middle School',
  high:         'High School',
  adult:        'Adult',
}

function housingVariant(housing: string | null): 'provided' | 'allowance' | 'none' {
  if (!housing || housing === 'Not provided') return 'none'
  if (/provid|furnished/i.test(housing)) return 'provided'
  return 'allowance'
}

export default function JobCard({
  job,
  onQuickApply,
  onDetail,
}: {
  job: PublicJob
  onQuickApply?: () => void
  onDetail?: () => void
}) {
  const ageLabels = (job.teaching_age ?? [])
    .map((g) => AGE_LABEL[g as AgeGroup] ?? g)
    .join(' / ')

  const hv = housingVariant(job.housing)
  const isHot = job.is_hot

  const benefits = Array.isArray(job.employee_benefits)
    ? job.employee_benefits as string[]
    : (job.employee_benefits ? String(job.employee_benefits).split(',').map((s) => s.trim()).filter(Boolean) : [])

  return (
    <article
      className={`relative bg-white rounded-2xl border transition-all duration-200 cursor-pointer
        hover:shadow-lg hover:-translate-y-1 flex flex-col p-5 gap-3
        ${isHot ? 'border-red-300 shadow-md ring-1 ring-red-100' : 'border-gray-200 shadow-sm'}`}
      onClick={onDetail}
    >
      {/* HOT gradient bar */}
      {isHot && (
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-red-500 via-orange-400 to-yellow-400 rounded-t-2xl" />
      )}

      {/* Badges */}
      <div className="flex flex-wrap items-center gap-1.5">
        {isHot && <span className="inline-flex items-center text-[10px] font-bold bg-red-600 text-white px-2 py-0.5 rounded-full">HOT</span>}
        {job.employment_type === 'part_time' && (
          <span className="text-[10px] font-medium bg-violet-50 text-violet-700 border border-violet-200 px-2 py-0.5 rounded-full">Part-time</span>
        )}
        {hv === 'provided'  && <span className="text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full">Housing</span>}
        {hv === 'allowance' && <span className="text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full">Allowance</span>}
      </div>

      {/* Title & Location */}
      <div>
        <p className="text-[10px] text-gray-400 font-mono tracking-wide">{job.job_id}</p>
        <h3 className="text-[15px] font-bold text-gray-900 leading-snug mt-0.5">
          {ageLabels ? `${ageLabels} Teacher` : job.location}
        </h3>
        <p className="text-sm text-gray-500 mt-0.5">{job.location}</p>
      </div>

      {/* Core specs */}
      <div className="space-y-1.5 text-sm">
        {job.monthly_salary && (
          <div className="flex justify-between items-baseline">
            <span className="text-gray-400 text-xs">Salary</span>
            <span className="font-bold text-gray-900 text-right">{job.monthly_salary}</span>
          </div>
        )}
        {job.working_hours && (
          <div className="flex justify-between items-baseline">
            <span className="text-gray-400 text-xs">Schedule</span>
            <span className="text-gray-700 text-xs text-right">{job.working_hours}</span>
          </div>
        )}
        {job.starting_date && (
          <div className="flex justify-between items-baseline">
            <span className="text-gray-400 text-xs">Start</span>
            <span className="text-gray-700 text-right">{job.starting_date}</span>
          </div>
        )}
      </div>

      {/* Benefits pills */}
      {benefits.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {benefits.slice(0, 3).map((b, i) => (
            <span key={i} className="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">{b}</span>
          ))}
          {benefits.length > 3 && (
            <span className="text-[10px] text-gray-400">+{benefits.length - 3}</span>
          )}
        </div>
      )}

      {/* Quick Apply button */}
      <div className="mt-auto pt-3 border-t border-gray-100 flex items-center justify-between">
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onDetail?.() }}
          className="text-xs text-blue-600 hover:underline"
        >
          Details
        </button>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onQuickApply?.() }}
          className="text-xs font-semibold bg-[#1d1d1f] text-white px-4 py-2 rounded-full hover:bg-[#424245] transition-colors"
        >
          Quick Apply
        </button>
      </div>
    </article>
  )
}
