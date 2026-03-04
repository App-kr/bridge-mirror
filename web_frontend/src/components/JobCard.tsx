'use client'

import type { PublicJob, AgeGroup } from '@/types'

const AGE_SHORT: Record<AgeGroup, string> = {
  pre_k: 'Pre-K', kindergarten: 'Kindy', elementary: 'Elem',
  middle: 'Middle', high: 'High', adult: 'Adult',
}

export default function JobCard({
  job,
  isHot,
  onDetails,
}: {
  job: PublicJob
  isHot?: boolean
  onDetails: () => void
}) {
  const ageLabel = job.teaching_age_raw
    || (job.teaching_age ?? []).map(g => AGE_SHORT[g as AgeGroup] ?? g).join(' - ')
    || ''

  return (
    <div
      className={`bg-white rounded-2xl border border-[#e5e7eb] p-7 flex flex-col transition-all duration-200
        hover:shadow-lg hover:-translate-y-[3px] cursor-default
        ${isHot ? 'border-l-4 border-l-orange-400' : ''}`}
      style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
    >
      {/* Badges + Job ID */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-bold bg-emerald-500 text-white px-2.5 py-[3px] rounded-full">OPEN</span>
          {isHot && <span className="text-[11px] font-bold bg-orange-500 text-white px-2.5 py-[3px] rounded-full">HOT</span>}
        </div>
        <span className="text-[28px] font-normal text-[#333] tracking-tight">{job.job_id}</span>
      </div>

      {/* City */}
      <h3 className="text-2xl font-bold text-[#1d1d1f] leading-tight">{job.location || 'Korea'}</h3>

      {/* Job title / age */}
      {ageLabel && (
        <p className="text-lg text-[#6e6e73] mt-1">{ageLabel} Teacher</p>
      )}

      {/* Info rows */}
      <div className="mt-auto pt-5 space-y-2">
        {job.working_hours && (
          <p className="text-base text-[#424245]">
            <span className="mr-2">&#x23F0;</span>{job.working_hours}
          </p>
        )}
        {job.starting_date && (
          <p className="text-base text-[#424245]">
            <span className="mr-2">&#x1F4C5;</span>{job.starting_date}
          </p>
        )}
        {job.monthly_salary && (
          <p className="text-base font-semibold text-[#1d1d1f]">
            <span className="mr-2">&#x1F4B0;</span>{job.monthly_salary}
          </p>
        )}
      </div>

      {/* Details button */}
      <button
        type="button"
        onClick={onDetails}
        className="mt-5 w-full py-2.5 rounded-xl border border-[#e5e7eb] text-sm font-semibold text-[#0071e3] hover:bg-[#f5f5f7] transition-colors"
      >
        Details
      </button>
    </div>
  )
}
