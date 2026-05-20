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
      className="bg-white flex flex-col cursor-default"
      style={{
        borderRadius: 12,
        padding: 32,
        boxShadow: '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)',
        transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
        borderLeft: isHot ? '5px solid #ea580c' : '5px solid transparent',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 10px 40px rgba(0,0,0,0.12)'
        e.currentTarget.style.transform = 'translateY(-2px)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)'
        e.currentTarget.style.transform = 'translateY(0)'
      }}
    >
      {/* HOT badge (좌) + Job ID (우) */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {isHot && (
            <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.05em', color: '#ea580c', textTransform: 'uppercase' }}>
              &#x1F525; Hot
            </span>
          )}
        </div>
        <span style={{ fontSize: 22, fontWeight: 600, color: '#6b7280', letterSpacing: '-0.02em' }}>
          {job.job_id}
        </span>
      </div>

      {/* City */}
      <h3 style={{ fontSize: 20, fontWeight: 600, color: '#111827', marginTop: 16, lineHeight: 1.2 }}>
        {job.location || 'Korea'}
      </h3>

      {/* Age / title */}
      {ageLabel && (
        <p style={{ fontSize: 16, fontWeight: 400, color: '#6b7280', marginTop: 4 }}>
          {ageLabel} Teacher
        </p>
      )}

      {/* Info */}
      <div className="mt-auto" style={{ paddingTop: 20 }}>
        {job.working_hours && (
          <p style={{ fontSize: 15, color: '#374151', lineHeight: 2 }}>{job.working_hours}</p>
        )}
        {job.starting_date && (
          <p style={{ fontSize: 15, color: '#374151', lineHeight: 2 }}>{job.starting_date}</p>
        )}
        {job.monthly_salary && (
          <p style={{ fontSize: 17, fontWeight: 600, color: '#111827', lineHeight: 2 }}>{job.monthly_salary}</p>
        )}
      </div>

      {/* Separator */}
      <div style={{ borderTop: '1px dashed #e5e7eb', margin: '20px 0 16px' }} />

      {/* Details link */}
      <button
        type="button"
        onClick={onDetails}
        className="bg-transparent border-0 cursor-pointer text-center"
        style={{ fontSize: 14, color: '#2563EB', fontWeight: 500 }}
        onMouseEnter={(e) => { e.currentTarget.style.textDecoration = 'underline' }}
        onMouseLeave={(e) => { e.currentTarget.style.textDecoration = 'none' }}
      >
        Details &rarr;
      </button>
    </div>
  )
}
