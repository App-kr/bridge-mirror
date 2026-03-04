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

export default function JobCard({
  job,
  isHot,
  onClick,
}: {
  job: PublicJob
  isHot?: boolean
  onClick?: () => void
}) {
  const ageLabels = (job.teaching_age ?? [])
    .map((g) => AGE_LABEL[g as AgeGroup] ?? g)
    .join(' / ')

  return (
    <article
      className={`relative bg-white rounded-2xl border transition-all duration-200 cursor-pointer
        hover:shadow-lg hover:-translate-y-1 flex flex-col p-5 gap-2.5
        ${isHot ? 'border-orange-300 shadow-md ring-1 ring-orange-100' : 'border-gray-200 shadow-sm'}`}
      onClick={onClick}
    >
      {/* HOT bar */}
      {isHot && (
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-red-500 via-orange-400 to-yellow-400 rounded-t-2xl" />
      )}

      {/* Job ID + HOT badge */}
      <div className="flex items-center justify-between">
        <span className="text-lg font-extrabold text-blue-600 tracking-tight">{job.job_id}</span>
        {isHot && (
          <span className="text-xs font-bold bg-red-600 text-white px-2.5 py-0.5 rounded-full flex items-center gap-1">
            <span>🔥</span> HOT
          </span>
        )}
      </div>

      {/* Title */}
      <h3 className="text-[15px] font-bold text-gray-900 leading-snug">
        {ageLabels ? `${ageLabels} Teacher` : 'Teaching Position'}
      </h3>

      {/* Location */}
      <p className="text-sm text-gray-500">{job.location || 'Korea'}</p>

      {/* Key info — Start & Hours */}
      <div className="mt-auto pt-2 space-y-1.5">
        {job.starting_date && (
          <div className="flex justify-between items-baseline">
            <span className="text-xs text-gray-400">Start</span>
            <span className="text-sm font-semibold text-gray-900">{job.starting_date}</span>
          </div>
        )}
        {job.working_hours && (
          <div className="flex justify-between items-baseline">
            <span className="text-xs text-gray-400">Hours</span>
            <span className="text-sm font-semibold text-gray-900">{job.working_hours}</span>
          </div>
        )}
      </div>
    </article>
  )
}
