'use client'

import { useEffect, useCallback } from 'react'
import Link from 'next/link'
import type { PublicJob, AgeGroup } from '@/types'

/* ─────────────────────────────────────────────
   raw_text 파서
   "필드명 : 값" → fields[]
   "Employee Benefits : ..." → benefits[]
   콜론 없는 줄 → notes[]
───────────────────────────────────────────── */
interface Parsed {
  fields:   { label: string; value: string }[]
  notes:    string[]
  benefits: string[]
}

const LABEL_MAP: Record<string, string> = {
  'starting date':                       'Starting Date',
  'teaching age':                        'Teaching Age',
  'class size':                          'Class Size',
  'working hours':                       'Working Hours',
  'monthly salary':                      'Monthly Salary',
  'average teaching hours per week':     'Avg Teaching Hrs / Week',
  'average teaching hours':              'Avg Teaching Hrs / Week',
  'vacation':                            'Vacation',
  'native teacher (numbers can change)': 'Native Teachers',
  'native teacher':                      'Native Teachers',
  'housing':                             'Housing',
  'preference':                          'Preference',
  'preferences':                         'Preference',
}

function normalizeLabel(raw: string): string {
  return LABEL_MAP[raw.toLowerCase().trim()] ?? raw.trim()
}

function parseRawText(raw: string): Parsed {
  const fields:   { label: string; value: string }[] = []
  const notes:    string[] = []
  const benefits: string[] = []

  const lines = raw
    .split('\n')
    .map(l => l.replace(/^[`"'\s]+/, '').replace(/[`"'\s]+$/, '').trim())
    .filter(Boolean)

  for (const line of lines) {
    // 첫 줄 "Job. XXXX" 스킵
    if (/^Job\.\s*\d+/i.test(line)) continue
    // 괄호 내부 내용 스킵 (이미 서버에서 제거되나 이중 방어)
    if (/^\(.*\)$/.test(line)) continue

    // "필드명 : 값" 또는 "필드명: 값" 패턴
    const m = line.match(/^(.+?)\s*:\s+(.+)$/)
    if (m) {
      const label = m[1].trim()
      const value = m[2].trim()
      if (/employee\s*benefit/i.test(label)) {
        benefits.push(...value.split(',').map(s => s.trim()).filter(Boolean))
      } else {
        fields.push({ label: normalizeLabel(label), value })
      }
    } else if (line.length > 3) {
      // 콜론 없는 줄 → 특이사항
      notes.push(line)
    }
  }

  return { fields, notes, benefits }
}

/* ─────────────────────────────────────────────
   FieldRow — 2컬럼 그리드 행
───────────────────────────────────────────── */
function FieldRow({
  label,
  value,
  zebra,
}: {
  label: string
  value: string
  zebra: boolean
}) {
  return (
    <div
      className="flex flex-col sm:flex-row gap-x-2 gap-y-0.5 px-2 py-[9px] border-b border-[#f3f4f6]"
      style={{ background: zebra ? '#fafafa' : '#fff' }}
    >
      <span className="text-[13px] text-[#6b7280] sm:w-40 sm:shrink-0 sm:text-right sm:pr-3.5 leading-[1.6]">
        {label}
      </span>
      <span style={{ fontSize: 14, color: '#111827', fontWeight: 500, lineHeight: 1.6 }}>
        {value}
      </span>
    </div>
  )
}

/* ─────────────────────────────────────────────
   메인 모달
───────────────────────────────────────────── */
const AGE_SHORT: Record<AgeGroup, string> = {
  pre_k: 'Pre-K', kindergarten: 'Kindy', elementary: 'Elem',
  middle: 'Middle', high: 'High', adult: 'Adult',
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
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() },
    [onClose],
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [handleKeyDown])

  /* ── 데이터 준비 ── */
  const rawText = job.raw_text ?? ''
  const parsed  = rawText ? parseRawText(rawText) : null

  // raw_text 파싱 결과 사용, 없으면 DB 구조화 필드로 fallback
  const fields = parsed?.fields ?? [
    { label: 'Starting Date',           value: job.starting_date },
    { label: 'Teaching Age',            value: job.teaching_age_raw || (job.teaching_age ?? []).map(g => AGE_SHORT[g as AgeGroup] ?? g).join(' - ') },
    { label: 'Class Size',              value: job.class_size },
    { label: 'Working Hours',           value: job.working_hours },
    { label: 'Monthly Salary',          value: job.monthly_salary },
    { label: 'Avg Teaching Hrs / Week', value: job.teaching_hours_per_week },
    { label: 'Vacation',                value: job.vacation },
    { label: 'Native Teachers',         value: job.native_teacher_count },
    { label: 'Housing',                 value: job.housing },
  ].filter((f): f is { label: string; value: string } => !!f.value)

  const notes    = parsed?.notes ?? (Array.isArray(job.notes) ? job.notes : [])
  const benefits = parsed?.benefits.length
    ? parsed.benefits
    : (Array.isArray(job.employee_benefits)
        ? job.employee_benefits
        : (job.employee_benefits
            ? String(job.employee_benefits).split(',').map(s => s.trim()).filter(Boolean)
            : []))

  const isOpen = !job.status || job.status === 'open'

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6"
      style={{ backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      {/* 오버레이 */}
      <div className="absolute inset-0" style={{ background: 'rgba(0,0,0,0.4)' }} />

      {/* 모달 본체 */}
      <div
        className="relative w-full z-10 overflow-y-auto px-5 pt-7 pb-7 sm:px-9 sm:pt-8"
        style={{
          background: '#fff',
          maxWidth: 560,
          maxHeight: '80vh',
          borderRadius: 16,
          boxShadow: '0 25px 50px rgba(0,0,0,0.25)',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* 닫기 버튼 */}
        <button
          type="button"
          onClick={onClose}
          className="absolute border-0 bg-transparent cursor-pointer"
          style={{ top: 20, right: 24, fontSize: 20, color: '#9ca3af', lineHeight: 1 }}
          onMouseEnter={e => { e.currentTarget.style.color = '#111' }}
          onMouseLeave={e => { e.currentTarget.style.color = '#9ca3af' }}
        >
          &#x2715;
        </button>

        {/* ── 헤더 ── */}
        <div style={{ paddingRight: 40 }}>
          <div className="flex items-baseline justify-between">
            <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', margin: 0 }}>
              {job.location || 'Korea'}
            </h2>
            <span style={{ fontSize: 14, color: '#9ca3af', fontWeight: 300, letterSpacing: '-0.02em' }}>
              {job.job_id}
            </span>
          </div>
          <div className="flex items-center gap-3" style={{ marginTop: 8 }}>
            <span
              style={{
                fontSize: 12, fontWeight: 700, letterSpacing: '0.06em',
                textTransform: 'uppercase',
                color: isOpen ? '#16a34a' : '#9ca3af',
              }}
            >
              {isOpen ? 'Open' : 'Closed'}
            </span>
            {isHot && (
              <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', color: '#ea580c', textTransform: 'uppercase' }}>
                🔥 Hot
              </span>
            )}
          </div>
        </div>

        <hr style={{ border: 'none', borderTop: '1px solid #e5e7eb', margin: '18px 0' }} />

        {/* ── 본문 ── */}
        <>
          {fields.length > 0 && (
            <div style={{ borderTop: '1px solid #f3f4f6' }}>
              {fields.map((f, i) => (
                <FieldRow key={i} label={f.label} value={f.value} zebra={i % 2 === 1} />
              ))}
            </div>
          )}
          {notes.length > 0 && (
            <>
              <hr style={{ border: 'none', borderTop: '1px solid #e5e7eb', margin: '18px 0' }} />
              <div
                style={{
                  background: '#EFF6FF',
                  borderLeft: '4px solid #60a5fa',
                  borderRadius: 8,
                  padding: '12px 16px',
                  fontSize: 13,
                  color: '#1e40af',
                  lineHeight: 1.7,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {notes.join('\n')}
              </div>
            </>
          )}
          {benefits.length > 0 && (
            <>
              <hr style={{ border: 'none', borderTop: '1px solid #e5e7eb', margin: '18px 0' }} />
              <p style={{ fontSize: 13, fontWeight: 700, color: '#374151', margin: '0 0 10px' }}>
                Benefits
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1">
                {benefits.map((b, i) => (
                  <div
                    key={i}
                    style={{ fontSize: 13, color: '#374151', lineHeight: 1.8, display: 'flex', alignItems: 'flex-start', gap: 6 }}
                  >
                    <span style={{ color: '#16a34a', flexShrink: 0, marginTop: 2 }}>✓</span>
                    <span>{b}</span>
                  </div>
                ))}
              </div>
            </>
          )}
          {fields.length === 0 && notes.length === 0 && benefits.length === 0 && (
            <p style={{ fontSize: 14, color: '#9ca3af', textAlign: 'center', padding: '16px 0' }}>
              상세 정보를 불러오는 중입니다.
            </p>
          )}
        </>

        <hr style={{ border: 'none', borderTop: '1px solid #e5e7eb', margin: '18px 0' }} />

        {/* ── 액션 버튼 ── */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 cursor-pointer"
            style={{
              background: '#fff', border: '1px solid #d1d5db', color: '#374151',
              borderRadius: 8, padding: '11px 24px', fontSize: 14, fontWeight: 600,
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#f9fafb' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#fff' }}
          >
            Close
          </button>
          <Link
            href="/apply"
            className="flex-1 text-center no-underline"
            style={{
              background: '#111827', color: '#fff', borderRadius: 8,
              padding: '11px 32px', fontSize: 14, fontWeight: 600, display: 'block',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#1f2937' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#111827' }}
          >
            Apply &rarr;
          </Link>
        </div>
      </div>
    </div>
  )
}
