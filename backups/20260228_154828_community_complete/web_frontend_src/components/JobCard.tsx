'use client'

import Link from 'next/link'
import type { PublicJob, AgeGroup } from '@/types'

// ── Age-group display labels ───────────────────────────────────────────────────
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

// ── JobCard ───────────────────────────────────────────────────────────────────
// onQuickApply: if provided → opens slide panel (jobs page)
//               if omitted  → Quick Apply button links to /apply (homepage)
export default function JobCard({
  job,
  onQuickApply,
}: {
  job: PublicJob
  onQuickApply?: () => void
}) {
  const ageLabels = (job.teaching_age ?? [])
    .map((g) => AGE_LABEL[g as AgeGroup] ?? g)
    .join(' / ')

  const hv = housingVariant(job.housing)

  const benefits = Array.isArray(job.employee_benefits)
    ? job.employee_benefits as string[]
    : (job.employee_benefits ? String(job.employee_benefits).split(',').map((s) => s.trim()).filter(Boolean) : [])

  return (
    <article className="card group flex flex-col gap-3">

      {/* ── Badges ── */}
      <div className="flex flex-wrap items-center gap-1.5">
        {job.is_hot && <span className="badge-hot">🔥 HOT</span>}
        {job.employment_type === 'part_time' && <span className="badge-pt">Part-time</span>}
        <span className="badge-open">Open</span>
        {hv === 'provided'  && <span className="badge-visa">🏠 Housing</span>}
        {hv === 'allowance' && <span className="badge badge-open border-amber-200 bg-amber-50 text-amber-700">💰 Allowance</span>}
        {/visa sponsorship/i.test(job.preferences ?? '') && (
          <span className="badge-visa">E-2 Visa</span>
        )}
      </div>

      {/* ── Location & age group ── */}
      <div>
        <p className="text-xs text-gray-400 font-mono mb-0.5">{job.job_id}</p>
        <h3 className="text-base font-bold text-gray-900 leading-snug group-hover:text-blue-600 transition-colors">
          {ageLabels ? `${ageLabels} Teacher` : job.location}
        </h3>
        <p className="text-sm text-gray-500 mt-0.5">{job.location}</p>
      </div>

      {/* ── Core specs ── */}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <dt className="text-gray-400 text-xs">Monthly Salary</dt>
        <dd className="font-bold text-gray-900">{job.monthly_salary ?? '—'}</dd>

        {job.working_hours && (
          <>
            <dt className="text-gray-400 text-xs">Schedule</dt>
            <dd className="text-gray-700 text-xs truncate">{job.working_hours}</dd>
          </>
        )}
        {job.teaching_hours_per_week && (
          <>
            <dt className="text-gray-400 text-xs">Teaching hrs/wk</dt>
            <dd className="text-gray-700">{job.teaching_hours_per_week}</dd>
          </>
        )}
        {job.starting_date && (
          <>
            <dt className="text-gray-400 text-xs">Start</dt>
            <dd className="text-gray-700">{job.starting_date}</dd>
          </>
        )}
        {job.vacation && (
          <>
            <dt className="text-gray-400 text-xs">Vacation</dt>
            <dd className="text-gray-700">{job.vacation}</dd>
          </>
        )}
      </dl>

      {/* ── Housing detail ── */}
      {job.housing && hv !== 'none' && (
        <p className="text-xs text-emerald-700 bg-emerald-50 rounded-lg px-3 py-1.5 border border-emerald-200">
          {job.housing}
        </p>
      )}

      {/* ── Benefits pills ── */}
      {benefits.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {benefits.slice(0, 4).map((b, i) => (
            <span key={i} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
              {b}
            </span>
          ))}
          {benefits.length > 4 && (
            <span className="text-xs text-gray-400">+{benefits.length - 4} more</span>
          )}
        </div>
      )}

      {/* ── Preferences ── */}
      {job.preferences && (
        <p className="text-xs text-gray-400 italic border-t border-gray-100 pt-2">
          {job.preferences}
        </p>
      )}

      {/* ── Quick Apply ── */}
      <div className="mt-auto pt-3 border-t border-gray-100 flex justify-end">
        {onQuickApply ? (
          <button
            onClick={onQuickApply}
            className="btn-primary text-xs px-4 py-2"
          >
            Quick Apply
          </button>
        ) : (
          <Link
            href={`/apply?job=${encodeURIComponent(job.job_id ?? '')}`}
            className="btn-primary text-xs px-4 py-2"
          >
            Quick Apply
          </Link>
        )}
      </div>
    </article>
  )
}
