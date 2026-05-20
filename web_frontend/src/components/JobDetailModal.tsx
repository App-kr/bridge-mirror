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
  'start date':                          'Starting Date',
  'teaching age':                        'Teaching Age',
  'age':                                 'Teaching Age',
  'class size':                          'Class size',
  'class':                               'Class size',
  'working hours':                       'Working Hours',
  'working hour':                        'Working Hours',
  'work hours':                          'Working Hours',
  'hours':                               'Working Hours',
  'monthly salary':                      'Monthly Salary',
  'salary':                              'Monthly Salary',
  'pay':                                 'Monthly Salary',
  'average teaching hours per week':     'Average Teaching Hours per Week',
  'avg teaching hours per week':         'Average Teaching Hours per Week',
  'average teaching hours':              'Average Teaching Hours per Week',
  'teaching hours per week':             'Average Teaching Hours per Week',
  'teaching hours':                      'Average Teaching Hours per Week',
  'vacation':                            'Vacation',
  'vacation days':                       'Vacation',
  'paid vacation':                       'Vacation',
  'native teacher (numbers can change)': 'Native Teacher (Numbers can change)',
  'native teacher':                      'Native Teacher (Numbers can change)',
  'native teachers':                     'Native Teacher (Numbers can change)',
  'housing':                             'Housing',
  'house':                               'Housing',
  'preference':                          'Preference',
  'preferences':                         'Preference',
  'preferred':                           'Preference',
}

// 모달 본문 순서 (사용자 요청 기준)
const FIELD_ORDER = [
  'Starting Date',
  'Teaching Age',
  'Class size',
  'Working Hours',
  'Monthly Salary',
  'Average Teaching Hours per Week',
  'Housing',
  'Native Teacher (Numbers can change)',
  'Vacation',
  'Preference',
]

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
   FieldLine — 백틱 프리픽스 한 줄 형태
   예) `Starting Date : March, August
───────────────────────────────────────────── */
function FieldLine({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: 'flex',
        gap: 6,
        padding: '3px 0',
        fontSize: 14,
        lineHeight: 1.65,
        color: '#374151',
        fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif',
      }}
    >
      <span style={{ color: '#cbd5e1', flexShrink: 0, userSelect: 'none' }}>`</span>
      <span>
        <span style={{ color: '#6b7280' }}>{label} : </span>
        <span style={{ color: '#1f2937' }}>{value}</span>
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

  // DB 구조화 필드 (항상 평가 — raw_text와 병합 대상)
  const dbFields: { label: string; value: string }[] = [
    { label: 'Starting Date',                    value: job.starting_date || '' },
    { label: 'Teaching Age',                     value: job.teaching_age_raw || (job.teaching_age ?? []).map(g => AGE_SHORT[g as AgeGroup] ?? g).join(' - ') },
    { label: 'Class size',                       value: job.class_size || '' },
    { label: 'Working Hours',                    value: job.working_hours || '' },
    { label: 'Monthly Salary',                   value: job.monthly_salary || '' },
    { label: 'Average Teaching Hours per Week',  value: job.teaching_hours_per_week || '' },
    { label: 'Vacation',                         value: job.vacation || '' },
    { label: 'Native Teacher (Numbers can change)', value: job.native_teacher_count || '' },
    { label: 'Housing',                          value: job.housing || '' },
  ].filter(f => !!f.value)

  // 라벨 정규화 — DB와 raw_text 양쪽이 다른 표기 써도 동일 라벨로 합치기
  const normLabel = (s: string): string => {
    const k = s.toLowerCase().trim().replace(/\s+/g, ' ')
    return LABEL_MAP[k] ?? s.trim()
  }
  // 병합: raw_text 파싱 결과 우선, 부족한 라벨은 DB로 보완
  const byLabel = new Map<string, { label: string; value: string }>()
  for (const f of dbFields) byLabel.set(normLabel(f.label), { label: normLabel(f.label), value: f.value })
  if (parsed) {
    for (const f of parsed.fields) {
      const k = normLabel(f.label)
      // raw_text의 값이 있으면 덮어쓰기 (관리자가 raw_text에 직접 적은 값을 우선)
      if (f.value) byLabel.set(k, { label: k, value: f.value })
    }
  }

  // 정해진 순서로 정렬 (지정 외 필드는 뒤로)
  const fields = Array.from(byLabel.values()).sort((a, b) => {
    const ai = FIELD_ORDER.indexOf(a.label)
    const bi = FIELD_ORDER.indexOf(b.label)
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
  })

  const notes    = parsed?.notes ?? (Array.isArray(job.notes) ? job.notes : [])
  const benefits = parsed?.benefits.length
    ? parsed.benefits
    : (Array.isArray(job.employee_benefits)
        ? job.employee_benefits
        : (job.employee_benefits
            ? String(job.employee_benefits).split(',').map(s => s.trim()).filter(Boolean)
            : []))

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
          <h2 style={{ fontSize: 18, fontWeight: 600, color: '#1f2937', margin: 0, letterSpacing: '-0.01em' }}>
            {job.location || 'Korea'}
          </h2>
          <div className="flex items-center gap-3" style={{ marginTop: 4 }}>
            <span style={{ fontSize: 13, color: '#9ca3af', fontWeight: 500 }}>
              Job. {(job.job_id || '').replace(/^Job\.?\s*/i, '')}
            </span>
            {isHot && (
              <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', color: '#ea580c', textTransform: 'uppercase' }}>
                🔥 Hot
              </span>
            )}
          </div>
        </div>

        <hr style={{ border: 'none', borderTop: '1px solid #e5e7eb', margin: '18px 0' }} />

        {/* ── 본문 — 백틱 프리픽스 한 줄씩 ── */}
        <>
          {fields.length > 0 && (
            <div style={{ paddingLeft: 4 }}>
              {fields.map((f, i) => (
                <FieldLine key={i} label={f.label} value={f.value} />
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
              <p style={{ fontSize: 15, fontWeight: 700, color: '#374151', margin: '0 0 10px' }}>
                Benefits
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5">
                {benefits.map((b, i) => (
                  <div
                    key={i}
                    style={{ fontSize: 15, color: '#374151', lineHeight: 1.8, display: 'flex', alignItems: 'flex-start', gap: 6 }}
                  >
                    <span style={{ color: '#16a34a', flexShrink: 0, marginTop: 2, fontSize: 15 }}>✓</span>
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
