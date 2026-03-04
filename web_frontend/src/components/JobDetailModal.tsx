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
    <div className="flex items-baseline" style={{ height: 44 }}>
      <span style={{ fontSize: 14, color: '#9ca3af', width: 120, flexShrink: 0 }}>{label}</span>
      <span style={{ fontSize: 15, color: '#111827', fontWeight: 500 }}>{value}</span>
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
      style={{ backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      {/* Overlay */}
      <div className="absolute inset-0" style={{ background: 'rgba(0,0,0,0.4)' }} />

      {/* Modal */}
      <div
        className="relative w-full overflow-y-auto z-10"
        style={{
          background: '#fff',
          maxWidth: 480,
          maxHeight: '90vh',
          borderRadius: 16,
          padding: 36,
          boxShadow: '0 25px 50px rgba(0,0,0,0.25)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute border-0 bg-transparent cursor-pointer"
          style={{ top: 20, right: 24, fontSize: 20, color: '#9ca3af', lineHeight: 1 }}
          onMouseEnter={(e) => { e.currentTarget.style.color = '#111' }}
          onMouseLeave={(e) => { e.currentTarget.style.color = '#9ca3af' }}
        >
          &#x2715;
        </button>

        {/* Header */}
        <div style={{ paddingRight: 40 }}>
          <div className="flex items-center justify-between">
            <h2 style={{ fontSize: 24, fontWeight: 700, color: '#111827', margin: 0 }}>
              {job.location || 'Korea'}
            </h2>
            <span style={{ fontSize: 22, fontWeight: 300, color: '#9ca3af', letterSpacing: '-0.02em' }}>
              {job.job_id}
            </span>
          </div>
          <div className="flex items-center gap-3" style={{ marginTop: 8 }}>
            <span style={{ fontSize: 12, fontWeight: 600, letterSpacing: '0.05em', color: '#16a34a', textTransform: 'uppercase' }}>
              Open
            </span>
            {isHot && (
              <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.05em', color: '#ea580c', textTransform: 'uppercase' }}>
                &#x1F525; Hot
              </span>
            )}
          </div>
        </div>

        <hr style={{ border: 'none', borderTop: '1px solid #e5e7eb', margin: '20px 0' }} />

        {/* Detail rows */}
        <div>
          <DetailRow label="Target" value={ageLabel} />
          <DetailRow label="Schedule" value={job.working_hours} />
          <DetailRow label="Start" value={job.starting_date} />
          <DetailRow label="Salary" value={job.monthly_salary} />
          <DetailRow label="Avg Hours" value={job.teaching_hours_per_week} />
          <DetailRow label="Vacation" value={job.vacation} />
          <DetailRow label="Native Tchr" value={job.native_teacher_count} />
          <DetailRow label="Housing" value={job.housing} />
          <DetailRow label="Class Size" value={job.class_size} />
          <DetailRow label="Preference" value={job.preferences} />
        </div>

        {/* Additional Info (notes) */}
        {notes.length > 0 && (
          <>
            <hr style={{ border: 'none', borderTop: '1px solid #e5e7eb', margin: '20px 0' }} />
            <p style={{ fontSize: 14, fontWeight: 700, color: '#374151', margin: '0 0 8px' }}>Additional Info</p>
            <div style={{
              fontSize: 14,
              color: '#92400e',
              background: '#fffbeb',
              padding: '12px 16px',
              borderRadius: 8,
            }}>
              {notes.map((n, i) => (
                <p key={i} style={{ margin: 0, marginBottom: i < notes.length - 1 ? 6 : 0, lineHeight: 1.6 }}>
                  &middot; {n}
                </p>
              ))}
            </div>
          </>
        )}

        {/* Benefits checklist */}
        {benefits.length > 0 && (
          <>
            <hr style={{ border: 'none', borderTop: '1px solid #e5e7eb', margin: '20px 0' }} />
            <p style={{ fontSize: 14, fontWeight: 700, color: '#374151', margin: '0 0 8px' }}>Benefits</p>
            <div className="grid grid-cols-1 sm:grid-cols-2" style={{ gap: 0 }}>
              {benefits.map((b, i) => (
                <p key={i} style={{ fontSize: 14, color: '#374151', lineHeight: 2, margin: 0 }}>
                  <span style={{ color: '#16a34a', marginRight: 6 }}>&#x2713;</span>
                  {b}
                </p>
              ))}
            </div>
          </>
        )}

        <hr style={{ border: 'none', borderTop: '1px solid #e5e7eb', margin: '20px 0' }} />

        {/* Action buttons */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 cursor-pointer"
            style={{
              background: '#fff',
              border: '1px solid #d1d5db',
              color: '#374151',
              borderRadius: 8,
              padding: '12px 24px',
              fontSize: 14,
              fontWeight: 600,
              transition: 'background 0.15s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = '#f9fafb' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = '#fff' }}
          >
            Close
          </button>
          <Link
            href="/apply"
            className="flex-1 text-center no-underline"
            style={{
              background: '#111827',
              color: '#fff',
              borderRadius: 8,
              padding: '12px 32px',
              fontSize: 14,
              fontWeight: 600,
              transition: 'background 0.15s',
              display: 'block',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = '#1f2937' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = '#111827' }}
          >
            Apply &rarr;
          </Link>
        </div>
      </div>
    </div>
  )
}
