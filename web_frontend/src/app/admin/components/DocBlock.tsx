'use client'

import { useState, useEffect } from 'react'

/* ── PII 마스킹 유틸 ── */
export function maskEmail(email: string | null | undefined): string {
  if (!email || email === 'None') return '—'
  const at = email.indexOf('@')
  if (at <= 1) return '****@****'
  return email[0] + '****' + email.slice(at)
}

export function maskPhone(phone: string | null | undefined): string {
  if (!phone || phone === 'None') return '—'
  const digits = phone.replace(/\D/g, '')
  if (digits.length < 8) return '****'
  return digits.slice(0, 3) + '-****-' + digits.slice(-4)
}

export function maskName(name: string | null | undefined): string {
  if (!name || name === 'None') return '—'
  if (name.length <= 2) return name.slice(0, 1) + '***'
  return name.slice(0, Math.max(1, name.length - 2)) + '***'
}

export function v(s: string | null | undefined): string {
  if (!s || s.trim() === '' || s.trim() === 'None') return ''
  return s.trim()
}

export interface EmployerApp {
  id: string
  type: 'employer'
  name: string
  email: string
  status: string
  created_at: string
  school_name?: string
  contact_name?: string | null
  job_code?: string | null
  source_file?: string | null
  phone?: string | null
  location?: string | null
  start_date?: string | null
  vacancies?: string | null
  teaching_age?: string | null
  schedule?: string | null
  working_hours?: string | null
  salary_raw?: string | null
  housing_type?: string | null
  housing_detail?: string | null
  travel_support?: string | null
  benefits?: string | null
  vacation?: string | null
  sick_leave?: string | null
  meal?: string | null
  memo?: string | null
  notes?: string | null
  assigned_to?: string | null
}

/* ── 상태 색상/라벨 ── */
const statusColors: Record<string, string> = {
  new: 'bg-sky-100 text-sky-700',
  contacted: 'bg-yellow-100 text-yellow-700',
  interviewing: 'bg-blue-100 text-blue-700',
  hired: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  hold: 'bg-gray-100 text-gray-500',
  blacklist: 'bg-red-200 text-red-800',
}
const statusLabel: Record<string, string> = {
  new: 'New', contacted: 'Contacted', interviewing: 'Interviewing',
  hired: 'Hired', rejected: 'Rejected', hold: 'Hold', blacklist: 'Blacklist',
}

/* ── 문서 라인 렌더 (archive JSX 방식) ── */
function DocLines({ text }: { text: string }) {
  const lines = text.split('\n')
  return (
    <div style={{ fontFamily: "'Malgun Gothic', sans-serif", fontSize: '0.92rem', lineHeight: 1.85, color: '#111' }}>
      {lines.map((line, i) => {
        const t = line.trim()
        if (!t) return <div key={i} style={{ height: 6 }} />
        const kv = t.match(/^(.+?)\s*:\s*(.+)$/)
        if (kv) return (
          <div key={i} style={{ display: 'flex', gap: 6, wordBreak: 'break-word' }}>
            <span style={{ color: '#555', fontWeight: 600, minWidth: 260, flexShrink: 0 }}>{kv[1]} :</span>
            <span style={{ color: '#111', fontWeight: 500 }}>{kv[2]}</span>
          </div>
        )
        return <div key={i} style={{ fontWeight: 500 }}>{t}</div>
      })}
    </div>
  )
}

/* ── DocBlock 컴포넌트 ── */
interface DocBlockProps {
  employer: EmployerApp
  isNew: boolean
  isConfirmed: boolean
  isBlacklist: boolean
  showPII: boolean
  province: string
  city: string
  onConfirm: (id: string) => void
  onStatusChange: (id: string, status: string) => void
  onEditMemo?: (id: string, memo: string) => void
  onMoveTop?: () => void
  onMoveUp?: () => void
  onMoveDown?: () => void
  isFirst?: boolean
  isLast?: boolean
  showDivider: boolean
}

export default function DocBlock({
  employer, isNew, isConfirmed, isBlacklist, showPII,
  province, city, onConfirm, onStatusChange, onEditMemo,
  onMoveTop, onMoveUp, onMoveDown, isFirst, isLast,
  showDivider,
}: DocBlockProps) {
  const shouldBlink = isNew && !isConfirmed

  /* ── 메모 인라인 편집 ── */
  const [editingMemo, setEditingMemo] = useState(false)
  const [memoVal, setMemoVal] = useState(employer.memo || '')
  useEffect(() => { setMemoVal(employer.memo || '') }, [employer.memo])

  /* ── rawText (notes 필드) ── */
  const rawText = v(employer.notes) || ''

  /* ── 메모/MEMO 표시용: 괄호 내용 추출 ── */
  const memoText = v(employer.memo) || ''

  /* ── Job 번호 ── */
  const src = employer.source_file || ''
  let jobNoStr = v(employer.job_code) || ''
  if (!jobNoStr) {
    if (src.startsWith('BRIDGE_clients')) jobNoStr = `F-${employer.id}`
    else if (src === 'memo_extract') jobNoStr = `M-${employer.id}`
    else jobNoStr = employer.id
  }
  const isNewCode = /^N\d+/.test(jobNoStr)

  /* ── 업체명 ── */
  const schoolName = showPII
    ? (v(employer.school_name) || v(employer.name))
    : maskName(employer.school_name || employer.name)

  return (
    <>
      <div
        id={`job-${jobNoStr}`}
        style={{
          marginBottom: 16,
          padding: '20px 28px',
          background: shouldBlink ? '#eff6ff' : isBlacklist ? '#fff5f5' : '#fff',
          borderLeft: shouldBlink ? '5px solid #2563eb' : isBlacklist ? '5px solid #dc2626' : '5px solid #e5e5e5',
          position: 'relative',
          animation: shouldBlink ? 'employer-blink-glow 1.2s ease-in-out infinite' : 'none',
          boxShadow: shouldBlink ? '0 0 18px rgba(37,99,235,0.3)' : '0 1px 3px rgba(0,0,0,0.06)',
        }}
      >
        {isBlacklist && (
          <div style={{ position: 'absolute', inset: 0, background: 'rgba(220,38,38,0.06)', pointerEvents: 'none' }} />
        )}

        {/* ── NEW 확인 버튼 ── */}
        {shouldBlink && (
          <button
            type="button"
            onClick={() => onConfirm(employer.id)}
            style={{ position: 'absolute', top: 10, right: 10, background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, padding: '7px 18px', fontSize: '0.85rem', fontWeight: 700, cursor: 'pointer', animation: 'employer-blink 0.8s step-end infinite', zIndex: 2 }}
          >
            ★ NEW — 확인
          </button>
        )}

        {/* ── 이동 버튼 ⤒ ↑ ↓ ── */}
        <div style={{ position: 'absolute', top: 10, right: shouldBlink ? 170 : 10, display: 'flex', gap: 3, zIndex: 2 }}>
          {!isFirst && onMoveTop && (
            <button type="button" onClick={onMoveTop} title="맨위로"
              style={{ padding: '3px 7px', border: '1px solid #ddd', borderRadius: 4, background: '#f8f8f8', cursor: 'pointer', fontSize: '0.75rem', color: '#666' }}>⤒</button>
          )}
          {!isFirst && onMoveUp && (
            <button type="button" onClick={onMoveUp} title="위로"
              style={{ padding: '3px 7px', border: '1px solid #ddd', borderRadius: 4, background: '#f8f8f8', cursor: 'pointer', fontSize: '0.75rem', color: '#666' }}>↑</button>
          )}
          {!isLast && onMoveDown && (
            <button type="button" onClick={onMoveDown} title="아래로"
              style={{ padding: '3px 7px', border: '1px solid #ddd', borderRadius: 4, background: '#f8f8f8', cursor: 'pointer', fontSize: '0.75rem', color: '#666' }}>↓</button>
          )}
        </div>

        {/* ── 헤더: Job번호 + 지역 + 도시 + 업체명 ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8, position: 'relative', zIndex: 1, paddingRight: shouldBlink ? 200 : 90 }}>
          <span style={{
            fontFamily: "'Consolas', monospace", fontSize: '1.05rem', fontWeight: 800,
            background: isNewCode ? '#2563eb' : '#111', color: '#fff',
            padding: '3px 14px', borderRadius: 5,
          }}>{jobNoStr}</span>
          {province && <span style={{ fontSize: '0.95rem', color: '#444', fontWeight: 600 }}>{province}</span>}
          {city && <span style={{ fontSize: '0.95rem', color: '#444', fontWeight: 600 }}>{city}</span>}
          <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#111' }}>{schoolName}</span>
          {isBlacklist && (
            <span style={{ fontSize: '0.75rem', background: '#dc2626', color: '#fff', padding: '3px 10px', borderRadius: 999, fontWeight: 800 }}>BLACKLIST</span>
          )}
          {/* 상태 뱃지 */}
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${statusColors[employer.status] || 'bg-gray-100 text-gray-600'}`}>
            {statusLabel[employer.status] || employer.status}
          </span>
        </div>

        {/* ── MEMO 섹션 (노란 박스) ── */}
        <div style={{ position: 'relative', zIndex: 1, marginBottom: 12 }}>
          {editingMemo ? (
            <div style={{ background: '#fffde7', border: '1px solid #f0e68c', padding: '10px 14px', borderRadius: 5 }}>
              <span style={{ fontWeight: 800, color: '#b8860b', fontSize: '0.75rem', display: 'block', marginBottom: 6 }}>MEMO</span>
              <textarea
                value={memoVal}
                onChange={e => setMemoVal(e.target.value)}
                style={{ width: '100%', minHeight: 80, border: '1px solid #f0e68c', borderRadius: 4, padding: '6px', fontSize: '0.88rem', background: '#fffff0', resize: 'vertical', outline: 'none' }}
              />
              <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                <button type="button"
                  onClick={() => { onEditMemo?.(employer.id, memoVal); setEditingMemo(false) }}
                  style={{ padding: '4px 12px', border: 'none', borderRadius: 4, background: '#2563eb', color: '#fff', fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer' }}>저장</button>
                <button type="button"
                  onClick={() => { setMemoVal(employer.memo || ''); setEditingMemo(false) }}
                  style={{ padding: '4px 12px', border: '1px solid #ccc', borderRadius: 4, background: '#fff', color: '#666', fontSize: '0.78rem', cursor: 'pointer' }}>취소</button>
              </div>
            </div>
          ) : memoText ? (
            <div style={{ background: '#fffde7', border: '1px solid #f0e68c', padding: '10px 14px', borderRadius: 5, fontSize: '0.9rem', lineHeight: 1.7, color: '#5d4e0f', position: 'relative' }}>
              <span style={{ fontWeight: 800, color: '#b8860b', fontSize: '0.75rem', marginRight: 8 }}>MEMO</span>
              {memoText}
              <button type="button"
                onClick={() => setEditingMemo(true)}
                style={{ position: 'absolute', top: 8, right: 10, padding: '2px 8px', border: '1px solid #d4b44a', borderRadius: 4, background: '#fff', fontSize: '0.72rem', cursor: 'pointer', color: '#a08020' }}>
                ✏ 메모수정
              </button>
            </div>
          ) : (
            <button type="button" onClick={() => setEditingMemo(true)}
              style={{ padding: '3px 10px', border: '1px dashed #ccc', borderRadius: 4, background: 'transparent', fontSize: '0.72rem', cursor: 'pointer', color: '#aaa' }}>
              + 메모 추가
            </button>
          )}
        </div>

        {/* ── 본문 (notes → rawText 방식 렌더) ── */}
        {rawText ? (
          <div style={{ position: 'relative', zIndex: 1, marginBottom: 12 }}>
            <DocLines text={rawText} />
          </div>
        ) : (
          /* notes가 없으면 구조화 필드 표시 */
          <div style={{ position: 'relative', zIndex: 1, marginBottom: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 32px', fontSize: '0.9rem', lineHeight: 1.8 }}>
              {[
                { label: 'Teaching Age', value: v(employer.teaching_age) },
                { label: 'Starting Date', value: v(employer.start_date) },
                { label: 'Working Hours', value: v(employer.working_hours) },
                { label: 'Monthly Salary', value: v(employer.salary_raw) },
                { label: 'Housing', value: [v(employer.housing_type), v(employer.housing_detail)].filter(Boolean).join(' — ') },
                { label: 'Vacation', value: v(employer.vacation) },
                { label: 'Benefits', value: v(employer.benefits) },
                { label: 'Meal', value: v(employer.meal) },
                { label: 'Schedule', value: v(employer.schedule) },
                { label: 'Vacancies', value: v(employer.vacancies) },
              ].filter(r => r.value).map(row => (
                <div key={row.label} style={{ display: 'flex', gap: 6, wordBreak: 'break-word' }}>
                  <span style={{ color: '#555', fontWeight: 600, minWidth: 140, flexShrink: 0 }}>{row.label} :</span>
                  <span style={{ color: '#111', fontWeight: 500 }}>{row.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── CONTACT 섹션 ── */}
        <div style={{ marginTop: 14, paddingTop: 10, borderTop: '1px solid #ebebeb', position: 'relative', zIndex: 1 }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#bbb', letterSpacing: '0.1em', display: 'block', marginBottom: 5 }}>
            CONTACT {showPII ? '(OPEN)' : '(MASKED)'}
          </span>
          {[
            { label: '업체명', value: showPII ? (v(employer.school_name) || v(employer.name)) : maskName(employer.school_name || employer.name) },
            { label: '이메일', value: showPII ? v(employer.email) : maskEmail(employer.email) },
            { label: '전화', value: showPII ? v(employer.phone) : maskPhone(employer.phone) },
          ].filter(r => r.value && r.value !== '—').map(row => (
            <div key={row.label} style={{ display: 'flex', gap: 6, fontSize: '0.85rem', marginBottom: 3 }}>
              <span style={{ color: '#888', fontWeight: 600, minWidth: 260, flexShrink: 0 }}>{row.label} :</span>
              <span style={{ color: '#444' }}>{row.value}</span>
            </div>
          ))}
        </div>

        {/* ── 상태 변경 ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, paddingTop: 10, borderTop: '1px solid #f0f0f0', position: 'relative', zIndex: 1 }}>
          <span style={{ fontSize: '0.72rem', color: '#aaa' }}>상태:</span>
          <select
            value={employer.status}
            onChange={e => onStatusChange(employer.id, e.target.value)}
            className={`text-[11px] px-2.5 py-1 rounded-full font-semibold border-0 cursor-pointer ${statusColors[employer.status] || 'bg-gray-100 text-gray-600'}`}
          >
            {Object.entries(statusLabel).map(([k, l]) => (
              <option key={k} value={k}>{l}</option>
            ))}
          </select>
          <span style={{ fontSize: '0.72rem', color: '#ccc', marginLeft: 'auto' }}>
            {employer.created_at?.slice(0, 10)}
          </span>
        </div>
      </div>

      {/* ── 페이지 구분선 ── */}
      {showDivider && (
        <div className="my-8 relative" style={{ borderTop: '2px dashed #ccc' }}>
          <span className="absolute left-1/2 -translate-x-1/2 -top-3 bg-[#f5f5f7] px-3 text-[11px] text-gray-300 font-mono">— page break —</span>
        </div>
      )}
    </>
  )
}
