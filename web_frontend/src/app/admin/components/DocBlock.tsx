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
  city?: string | null
  start_date?: string | null
  vacancies?: string | null
  teaching_age?: string | null
  class_size?: string | null
  schedule?: string | null
  working_hours?: string | null
  teach_hrs_week?: string | null
  salary_raw?: string | null
  housing?: string | null
  housing_type?: string | null
  housing_detail?: string | null
  travel_support?: string | null
  native_count?: string | null
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

/* 구조화 필드 → 워드뷰 rawText — 샘플 포맷 순서 그대로 */
function buildRawText(emp: EmployerApp, province: string, city: string, jobNo: string): string {
  if (emp.notes && emp.notes.trim()) return emp.notes.trim()
  const rows: string[] = []
  const loc = v(emp.location) || `${province} ${city}`.trim()
  if (loc) rows.push(loc)
  const jc = v(emp.job_code)
  if (jc) rows.push(jc)
  else if (jobNo) rows.push(`Job. ${jobNo}`)
  if (v(emp.start_date)) rows.push(`Starting Date : ${v(emp.start_date)}`)
  if (v(emp.teaching_age)) rows.push(`Teaching Age : ${v(emp.teaching_age)}`)
  if (v(emp.class_size)) rows.push(`Class size : ${v(emp.class_size)}`)
  if (v(emp.working_hours)) rows.push(`Working Hours : ${v(emp.working_hours)}`)
  if (v(emp.salary_raw)) rows.push(`Monthly Salary : ${v(emp.salary_raw)}`)
  if (v(emp.teach_hrs_week)) rows.push(`Average Teaching Hours per Week : ${v(emp.teach_hrs_week)}`)
  if (v(emp.vacation)) rows.push(`Vacation : ${v(emp.vacation)}`)
  if (v(emp.native_count)) rows.push(`Native Teacher (Numbers can change) : ${v(emp.native_count)}`)
  if (v(emp.housing)) rows.push(`Housing: ${v(emp.housing)}`)
  if (v(emp.housing_detail)) rows.push(`Housing Details : ${v(emp.housing_detail)}`)
  if (v(emp.schedule)) rows.push(`Schedule : ${v(emp.schedule)}`)
  if (v(emp.travel_support)) rows.push(`Travel Support : ${v(emp.travel_support)}`)
  if (v(emp.benefits)) rows.push(`Employee Benefits : ${v(emp.benefits)}`)
  if (v(emp.sick_leave)) rows.push(`Sick Leave : ${v(emp.sick_leave)}`)
  if (v(emp.meal)) rows.push(`Meal : ${v(emp.meal)}`)
  if (v(emp.vacancies)) rows.push(`Open Positions : ${v(emp.vacancies)}`)
  return rows.join('\n')
}

/* ── 버튼 공통 스타일 헬퍼 ── */
const btnBase: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 3,
  padding: '4px 10px', border: '1px solid #ddd', borderRadius: 5,
  background: '#f8f8f8', cursor: 'pointer', fontSize: '0.75rem',
  color: '#555', fontWeight: 600, whiteSpace: 'nowrap',
}
const btnBlue: React.CSSProperties = {
  ...btnBase, background: '#2563eb', color: '#fff', border: 'none', fontWeight: 700,
}
const btnGhost: React.CSSProperties = {
  ...btnBase, background: '#fff', color: '#888',
}

export default function DocBlock({
  employer, isNew, isConfirmed, isBlacklist, showPII,
  province, city, jobNo, searchQuery,
  onConfirm, onStatusChange, onEditMemo, onEditNotes,
  onMoveTop, onMoveUp, onMoveDown, isFirst, isLast,
  showDivider,
}: DocBlockProps) {
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
      <div
        id={`job-${jobNo}`}
        style={{
          marginBottom: 16,
          padding: '18px 24px 14px',
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

        {/* ── 헤더 행: Job번호 + 지역 + 업체명 + 이동버튼 ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, position: 'relative', zIndex: 2 }}>
          {/* Job 번호 뱃지 */}
          <span style={{
            fontFamily: "'Consolas',monospace", fontSize: '1.0rem', fontWeight: 800,
            background: isNewCode ? '#2563eb' : '#111', color: '#fff',
            padding: '3px 13px', borderRadius: 5, flexShrink: 0,
          }}>
            {jobNo}
          </span>

          {/* 지역 + 업체명 */}
          <span style={{ fontSize: '0.9rem', color: '#666', fontWeight: 600 }}>{province} {city}</span>
          <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#111', flex: 1 }}>{displayName}</span>

          {isBlacklist && (
            <span style={{ fontSize: '0.72rem', background: '#dc2626', color: '#fff', padding: '2px 9px', borderRadius: 999, fontWeight: 800, flexShrink: 0 }}>BLACKLIST</span>
          )}

          {/* ── 이동 버튼 (맨위로 / 위로 / 아래로) ── */}
          <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
            {!isFirst && (
              <button type="button" onClick={onMoveTop} style={btnBase} title="맨 위로">
                ⤒ 맨위로
              </button>
            )}
            {!isFirst && (
              <button type="button" onClick={onMoveUp} style={btnBase} title="위로">
                ↑ 위로
              </button>
            )}
            {!isLast && (
              <button type="button" onClick={onMoveDown} style={btnBase} title="아래로">
                ↓ 아래로
              </button>
            )}
          </div>

          {/* NEW 확인 버튼 */}
          {isGlow && (
            <button
              type="button"
              onClick={() => onConfirm(employer.id)}
              style={{
                background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8,
                padding: '6px 16px', fontSize: '0.83rem', fontWeight: 700, cursor: 'pointer',
                animation: 'blink 0.8s step-end infinite', flexShrink: 0,
              }}
            >
              ★ NEW — 확인
            </button>
          )}
        </div>

        {/* ── MEMO 박스 (항상 표시 — 옅은 노랑) ── */}
        <div style={{ position: 'relative', zIndex: 1, marginBottom: 14 }}>
          {editingMemo ? (
            <div style={{ background: '#fffde7', border: '1px solid #e8d87a', borderRadius: 6, padding: '10px 14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span style={{ fontWeight: 800, color: '#b8860b', fontSize: '0.73rem', letterSpacing: '0.08em' }}>MEMO</span>
              </div>
              <textarea
                value={memoVal}
                onChange={e => setMemoVal(e.target.value)}
                autoFocus
                placeholder="내부 메모를 입력하세요 (예: 원장 연락처, 특이사항 등)"
                style={{
                  width: '100%', minHeight: 90, border: '1px solid #e0cc6a', borderRadius: 4,
                  padding: '8px 10px', fontSize: '0.88rem', background: '#fffff5',
                  resize: 'vertical', outline: 'none', lineHeight: 1.7, fontFamily: 'inherit',
                }}
              />
              <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                <button type="button"
                  onClick={() => { onEditMemo?.(employer.id, memoVal); setEditingMemo(false) }}
                  style={btnBlue}>
                  💾 저장
                </button>
                <button type="button"
                  onClick={() => { setMemoVal(employer.memo || ''); setEditingMemo(false) }}
                  style={btnGhost}>
                  취소
                </button>
              </div>
            </div>
          ) : (
            <div
              style={{
                background: '#fffde7', border: '1px solid #e8d87a', borderRadius: 6,
                padding: '9px 14px', position: 'relative',
                animation: isGlow ? 'blink 0.8s step-end infinite' : 'none',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <span style={{ fontWeight: 800, color: '#b8860b', fontSize: '0.73rem', letterSpacing: '0.08em', paddingTop: 2, flexShrink: 0 }}>MEMO</span>
                <span style={{
                  flex: 1, fontSize: '0.9rem', lineHeight: 1.7, color: employer.memo ? '#5d4e0f' : '#c8b870',
                  fontStyle: employer.memo ? 'normal' : 'italic',
                  whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                }}>
                  {employer.memo || '메모를 추가하려면 ✏ 편집을 클릭하세요'}
                </span>
                <button type="button" onClick={() => setEditingMemo(true)}
                  style={{ ...btnBase, background: '#fff7d6', border: '1px solid #d4b44a', color: '#a08020', flexShrink: 0 }}>
                  ✏ 편집
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── 본문 (rawText 워드뷰) ── */}
        <div style={{ position: 'relative', zIndex: 1 }}>
          {editingRaw ? (
            <div>
              <textarea
                value={rawVal}
                onChange={e => setRawVal(e.target.value)}
                autoFocus
                style={{
                  width: '100%', minHeight: 180, border: '1px solid #bbb', borderRadius: 5,
                  padding: '10px 12px', fontSize: '0.88rem', fontFamily: "'Consolas',monospace",
                  resize: 'vertical', outline: 'none', background: '#fafafa', lineHeight: 1.8,
                }}
              />
              <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                <button type="button"
                  onClick={() => { onEditNotes?.(employer.id, rawVal); setEditingRaw(false) }}
                  style={btnBlue}>
                  💾 저장
                </button>
                <button type="button"
                  onClick={() => { setRawVal(rawText); setEditingRaw(false) }}
                  style={btnGhost}>
                  취소
                </button>
              </div>
            </div>
          ) : (
            <div style={{ fontFamily: "'Malgun Gothic',sans-serif", fontSize: '0.92rem', lineHeight: 1.9, color: '#111' }}>
              {lines.map((line, i) => {
                const t = line.trim()
                if (!t) return <div key={i} style={{ height: 5 }} />
                const kv = t.match(/^(.+?)\s*:\s*(.+)$/)
                if (kv) return (
                  <div key={i} style={{ display: 'flex', gap: 8, wordBreak: 'break-word' }}>
                    <span style={{ color: '#555', fontWeight: 600, minWidth: 260, flexShrink: 0 }}>{kv[1]} :</span>
                    <span style={{ color: '#111', fontWeight: 400 }}>{kv[2]}</span>
                  </div>
                )
                return <div key={i} style={{ fontWeight: 500, width: '100%', color: '#222' }}>{t}</div>
              })}
              <button type="button" onClick={() => setEditingRaw(true)}
                style={{ ...btnBase, marginTop: 10, background: '#f4f4f4' }}>
                ✏ 본문 편집
              </button>
            </div>
          )}
        </div>

        {/* ── CONTACT 섹션 — PII 마스킹 ── */}
        <div style={{ marginTop: 16, paddingTop: 10, borderTop: '1px solid #ebebeb', position: 'relative', zIndex: 1 }}>
          <span style={{ fontSize: '0.68rem', fontWeight: 800, color: '#bbb', letterSpacing: '0.12em', display: 'block', marginBottom: 6 }}>CONTACT</span>
          {[
            { label: '업체명', value: showPII ? (employer.school_name || employer.name) : maskName(employer.school_name || employer.name) },
            { label: '이메일', value: showPII ? employer.email : maskEmail(employer.email) },
            { label: '전화', value: showPII ? (employer.phone || '—') : maskPhone(employer.phone) },
          ].map(row => (
            <div key={row.label} style={{ display: 'flex', gap: 8, fontSize: '0.85rem', marginBottom: 3 }}>
              <span style={{ color: '#888', fontWeight: 600, minWidth: 120, flexShrink: 0 }}>{row.label} :</span>
              <span style={{ color: '#444' }}>{row.value}</span>
            </div>
          ))}
        </div>

        {/* ── 상태 변경 ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, paddingTop: 8, borderTop: '1px solid #f0f0f0', position: 'relative', zIndex: 1 }}>
          <span style={{ fontSize: '0.72rem', color: '#aaa' }}>상태:</span>
          <select
            value={employer.status}
            onChange={e => onStatusChange(employer.id, e.target.value)}
            style={{ fontSize: '0.78rem', padding: '2px 8px', borderRadius: 4, border: '1px solid #ddd', background: '#fafafa', cursor: 'pointer' }}
          >
            {['open', 'contacted', 'hired', 'hold', 'closed', 'blacklist'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <span style={{ fontSize: '0.72rem', color: '#ccc', marginLeft: 'auto' }}>{employer.created_at?.slice(0, 10)}</span>
        </div>
      </div>

      {/* 페이지 구분선 */}
      {showDivider && (
        <div style={{ display: 'flex', alignItems: 'center', padding: '14px 0' }}>
          <div style={{ flex: 1, height: 1, background: '#ddd' }} />
          <span style={{ padding: '0 16px', fontSize: '0.68rem', color: '#bbb', fontFamily: 'monospace' }}>— page break —</span>
          <div style={{ flex: 1, height: 1, background: '#ddd' }} />
        </div>
      )}
    </>
  )
}
