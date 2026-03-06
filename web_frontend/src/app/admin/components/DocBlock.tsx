'use client'

import { useState, useEffect } from 'react'

/* ── PII 마스킹 ── */
export function maskEmail(email: string | null | undefined): string {
  if (!email) return '—'
  const at = email.indexOf('@')
  if (at < 0) return email
  return email[0] + '****' + email.slice(at)
}

export function maskPhone(phone: string | null | undefined): string {
  if (!phone) return '—'
  return phone.replace(/(\d{2,4})-(\d{3,4})-(\d{4})/, '$1-****-$3')
}

export function maskName(name: string | null | undefined): string {
  if (!name) return '—'
  if (name.length <= 2) return name
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

interface DocBlockProps {
  employer: EmployerApp
  isNew: boolean
  isConfirmed: boolean
  isBlacklist: boolean
  showPII: boolean
  province: string
  city: string
  jobNo: string
  searchQuery: string
  onConfirm: (id: string) => void
  onStatusChange: (id: string, status: string) => void
  onEditMemo?: (id: string, memo: string) => void
  onEditNotes?: (id: string, notes: string) => void
  onMoveTop?: () => void
  onMoveUp?: () => void
  onMoveDown?: () => void
  isFirst: boolean
  isLast: boolean
  showDivider: boolean
}

/* 구조화 필드 → 워드뷰 rawText 합성 (notes가 비어있으면 개별 필드로 생성) */
function buildRawText(emp: EmployerApp, province: string, city: string, jobNo: string): string {
  if (emp.notes && emp.notes.trim()) return emp.notes.trim()
  const rows: string[] = []
  if (province || city) rows.push(`${province} ${city}`.trim())
  if (jobNo) rows.push(`Job. ${jobNo}`)
  if (v(emp.start_date)) rows.push(`Starting Date : ${v(emp.start_date)}`)
  if (v(emp.vacancies)) rows.push(`Open Positions : ${v(emp.vacancies)}`)
  if (v(emp.teaching_age)) rows.push(`Teaching Age : ${v(emp.teaching_age)}`)
  if (v(emp.schedule)) rows.push(`Schedule : ${v(emp.schedule)}`)
  if (v(emp.working_hours)) rows.push(`Working Hours : ${v(emp.working_hours)}`)
  if (v(emp.salary_raw)) rows.push(`Monthly Salary : ${v(emp.salary_raw)}`)
  if (v(emp.housing_type)) rows.push(`Housing : ${v(emp.housing_type)}`)
  if (v(emp.housing_detail)) rows.push(`Housing Details : ${v(emp.housing_detail)}`)
  if (v(emp.travel_support)) rows.push(`Travel Support : ${v(emp.travel_support)}`)
  if (v(emp.benefits)) rows.push(`Employee Benefits : ${v(emp.benefits)}`)
  if (v(emp.vacation)) rows.push(`Vacation : ${v(emp.vacation)}`)
  if (v(emp.sick_leave)) rows.push(`Sick Leave : ${v(emp.sick_leave)}`)
  if (v(emp.meal)) rows.push(`Meal : ${v(emp.meal)}`)
  return rows.join('\n')
}

export default function DocBlock({
  employer, isNew, isConfirmed, isBlacklist, showPII,
  province, city, jobNo, searchQuery,
  onConfirm, onStatusChange, onEditMemo, onEditNotes,
  onMoveTop, onMoveUp, onMoveDown, isFirst, isLast,
  showDivider,
}: DocBlockProps) {
  /* JSX와 동일한 변수명 */
  const rawText = buildRawText(employer, province, city, jobNo)
  const lines = rawText ? rawText.split('\n') : []
  const isGlow = isNew && !isConfirmed
  const sq = (searchQuery || '').toLowerCase()
  const isHl = sq && (
    rawText.toLowerCase().includes(sq) ||
    (employer.memo || '').toLowerCase().includes(sq) ||
    (employer.school_name || employer.name || '').toLowerCase().includes(sq) ||
    jobNo.toLowerCase().includes(sq)
  )

  const [editingMemo, setEditingMemo] = useState(false)
  const [editingRaw, setEditingRaw] = useState(false)
  const [memoVal, setMemoVal] = useState(employer.memo || '')
  const [rawVal, setRawVal] = useState(rawText)

  useEffect(() => {
    setMemoVal(employer.memo || '')
    setRawVal(buildRawText(employer, province, city, jobNo))
  }, [employer, province, city, jobNo])

  const displayName = employer.school_name || employer.name || ''
  const isNewCode = jobNo.startsWith('N')

  return (
    <>
      {/* JSX DocBlock 그대로 */}
      <div
        id={`job-${jobNo}`}
        style={{
          marginBottom: 16,
          padding: '20px 28px',
          background: isHl ? '#fffff0' : '#fff',
          borderLeft: isGlow ? '5px solid #2563eb' : isBlacklist ? '5px solid #dc2626' : '5px solid #e5e5e5',
          position: 'relative',
          animation: isGlow ? 'glow 1.2s ease-in-out infinite' : 'none',
          boxShadow: isGlow ? '0 0 18px rgba(37,99,235,0.35)' : '0 1px 3px rgba(0,0,0,0.06)',
          outline: isHl ? '2px solid #f59e0b' : 'none',
        }}
      >
        {isBlacklist && (
          <div style={{ position: 'absolute', inset: 0, background: 'rgba(220,38,38,0.06)', pointerEvents: 'none', border: '1px solid rgba(220,38,38,0.15)' }} />
        )}

        {/* NEW 확인 버튼 */}
        {isGlow && (
          <button
            type="button"
            onClick={() => onConfirm(employer.id)}
            style={{ position: 'absolute', top: 10, right: 10, background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, padding: '7px 18px', fontSize: '0.85rem', fontWeight: 700, cursor: 'pointer', animation: 'blink 0.8s step-end infinite', zIndex: 2 }}
          >
            ★ NEW — 확인
          </button>
        )}

        {/* 이동 버튼 (⤒ ↑ ↓) */}
        <div style={{ position: 'absolute', top: 10, right: isGlow ? 170 : 10, display: 'flex', gap: 3, zIndex: 2 }}>
          {!isFirst && (
            <button type="button" onClick={onMoveTop} title="맨위로" style={{ padding: '3px 7px', border: '1px solid #ddd', borderRadius: 4, background: '#f8f8f8', cursor: 'pointer', fontSize: '0.75rem', color: '#666' }}>⤒</button>
          )}
          {!isFirst && (
            <button type="button" onClick={onMoveUp} title="위로" style={{ padding: '3px 7px', border: '1px solid #ddd', borderRadius: 4, background: '#f8f8f8', cursor: 'pointer', fontSize: '0.75rem', color: '#666' }}>↑</button>
          )}
          {!isLast && (
            <button type="button" onClick={onMoveDown} title="아래로" style={{ padding: '3px 7px', border: '1px solid #ddd', borderRadius: 4, background: '#f8f8f8', cursor: 'pointer', fontSize: '0.75rem', color: '#666' }}>↓</button>
          )}
        </div>

        {/* 헤더: Job번호 + 지역 + 업체명 + 블랙리스트 뱃지 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8, position: 'relative', zIndex: 1, paddingRight: isGlow ? 200 : 90 }}>
          <span style={{ fontFamily: "'Consolas',monospace", fontSize: '1.05rem', fontWeight: 800, background: isNewCode ? '#2563eb' : '#111', color: '#fff', padding: '3px 14px', borderRadius: 5 }}>
            {jobNo}
          </span>
          <span style={{ fontSize: '0.95rem', color: '#444', fontWeight: 600 }}>{province} {city}</span>
          <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#111' }}>{displayName}</span>
          {isBlacklist && (
            <span style={{ fontSize: '0.75rem', background: '#dc2626', color: '#fff', padding: '3px 10px', borderRadius: 999, fontWeight: 800 }}>BLACKLIST</span>
          )}
        </div>

        {/* MEMO */}
        <div style={{ position: 'relative', zIndex: 1, marginBottom: 12 }}>
          {editingMemo ? (
            <div style={{ background: '#fffde7', border: '1px solid #f0e68c', padding: '10px 14px', borderRadius: 5 }}>
              <span style={{ fontWeight: 800, color: '#b8860b', fontSize: '0.75rem', marginRight: 8, display: 'block', marginBottom: 6 }}>MEMO</span>
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
          ) : employer.memo ? (
            <div style={{ background: '#fffde7', border: '1px solid #f0e68c', padding: '10px 14px', borderRadius: 5, fontSize: '0.9rem', lineHeight: 1.7, color: '#5d4e0f', animation: isGlow ? 'blink 0.8s step-end infinite' : 'none', position: 'relative' }}>
              <span style={{ fontWeight: 800, color: '#b8860b', fontSize: '0.75rem', marginRight: 8 }}>MEMO</span>{employer.memo}
              <button type="button" onClick={() => setEditingMemo(true)}
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

        {/* rawText (notes) 전체 파싱 표시 */}
        {editingRaw ? (
          <div style={{ position: 'relative', zIndex: 1 }}>
            <textarea
              value={rawVal}
              onChange={e => setRawVal(e.target.value)}
              style={{ width: '100%', minHeight: 120, border: '1px solid #ccc', borderRadius: 4, padding: '8px', fontSize: '0.88rem', fontFamily: "'Consolas',monospace", resize: 'vertical', outline: 'none' }}
            />
            <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
              <button type="button"
                onClick={() => { onEditNotes?.(employer.id, rawVal); setEditingRaw(false) }}
                style={{ padding: '4px 12px', border: 'none', borderRadius: 4, background: '#2563eb', color: '#fff', fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer' }}>저장</button>
              <button type="button"
                onClick={() => { setRawVal(employer.notes || ''); setEditingRaw(false) }}
                style={{ padding: '4px 12px', border: '1px solid #ccc', borderRadius: 4, background: '#fff', color: '#666', fontSize: '0.78rem', cursor: 'pointer' }}>취소</button>
            </div>
          </div>
        ) : (
          <div style={{ fontFamily: "'Malgun Gothic',sans-serif", fontSize: '0.92rem', lineHeight: 1.85, color: '#111', position: 'relative', zIndex: 1 }}>
            {lines.map((line, i) => {
              const t = line.trim()
              if (!t) return <div key={i} style={{ height: 6 }} />
              const kv = t.match(/^(.+?)\s*:\s*(.+)$/)
              if (kv) return (
                <div key={i} style={{ display: 'flex', gap: 6, wordBreak: 'break-word' }}>
                  <span style={{ color: '#555', fontWeight: 600, minWidth: 280, flexShrink: 0 }}>{kv[1]} :</span>
                  <span style={{ color: '#111', fontWeight: 500 }}>{kv[2]}</span>
                </div>
              )
              return <div key={i} style={{ fontWeight: 500, width: '100%' }}>{t}</div>
            })}
            <button type="button" onClick={() => setEditingRaw(true)}
              style={{ marginTop: 8, padding: '3px 10px', border: '1px solid #ddd', borderRadius: 4, background: '#f8f8f8', fontSize: '0.72rem', cursor: 'pointer', color: '#666' }}>
              ✏ 본문수정
            </button>
          </div>
        )}

        {/* CONTACT 섹션 — PII 마스킹 */}
        <div style={{ marginTop: 14, paddingTop: 10, borderTop: '1px solid #ebebeb', position: 'relative', zIndex: 1 }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#bbb', letterSpacing: '0.1em', display: 'block', marginBottom: 5 }}>CONTACT</span>
          {[
            { label: '업체명', value: showPII ? (employer.school_name || employer.name) : maskName(employer.school_name || employer.name) },
            { label: '이메일', value: showPII ? employer.email : maskEmail(employer.email) },
            { label: '전화', value: showPII ? (employer.phone || '—') : maskPhone(employer.phone) },
          ].map(row => (
            <div key={row.label} style={{ display: 'flex', gap: 6, fontSize: '0.85rem', marginBottom: 3 }}>
              <span style={{ color: '#888', fontWeight: 600, minWidth: 280, flexShrink: 0 }}>{row.label} :</span>
              <span style={{ color: '#444' }}>{row.value}</span>
            </div>
          ))}
        </div>

        {/* 상태 변경 (production 전용) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, paddingTop: 8, borderTop: '1px solid #f0f0f0', position: 'relative', zIndex: 1 }}>
          <span style={{ fontSize: '0.72rem', color: '#aaa' }}>상태:</span>
          <select
            value={employer.status}
            onChange={e => onStatusChange(employer.id, e.target.value)}
            style={{ fontSize: '0.78rem', padding: '2px 8px', borderRadius: 4, border: '1px solid #ddd', background: '#fafafa', cursor: 'pointer' }}
          >
            {['new','contacted','interviewing','hired','rejected','hold','blacklist'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <span style={{ fontSize: '0.72rem', color: '#ccc', marginLeft: 'auto' }}>{employer.created_at?.slice(0, 10)}</span>
        </div>
      </div>

      {/* 페이지 구분선 */}
      {showDivider && (
        <div style={{ display: 'flex', alignItems: 'center', padding: '12px 0' }}>
          <div style={{ flex: 1, height: 1, background: '#ccc' }} />
          <span style={{ padding: '0 14px', fontSize: '0.7rem', color: '#aaa', fontFamily: 'monospace' }}>— page break —</span>
          <div style={{ flex: 1, height: 1, background: '#ccc' }} />
        </div>
      )}
    </>
  )
}
