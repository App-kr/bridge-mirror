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
  native_count?: string | null
  benefits?: string | null
  vacation?: string | null
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

/* 구조화 필드 → 워드뷰 rawText — 항상 실제 DB 필드 우선 */
function buildRawText(emp: EmployerApp, province: string, city: string, jobNo: string): string {
  // notes가 있으면 관리자 직접 편집본 사용
  if (emp.notes && emp.notes.trim()) return emp.notes.trim()
  const rows: string[] = []
  if (v(emp.vacancies)) rows.push(`Native Teacher (Numbers can change) : Approx. ${v(emp.vacancies)}`)
  if (v(emp.native_count)) rows.push(`Native Teacher (Numbers can change) : Approx. ${v(emp.native_count)}`)
  if (v(emp.start_date)) rows.push(`Starting Date : ${v(emp.start_date)}`)
  if (v(emp.teaching_age)) rows.push(`Teaching Age : ${v(emp.teaching_age)}`)
  if (v(emp.class_size)) rows.push(`Class size : around ~${v(emp.class_size)}`)
  if (v(emp.working_hours)) rows.push(`Working Hours : ${v(emp.working_hours)}`)
  if (v(emp.schedule)) rows.push(`Schedule : ${v(emp.schedule)}`)
  if (v(emp.salary_raw)) rows.push(`Monthly Salary : ${v(emp.salary_raw)}`)
  if (v(emp.teach_hrs_week)) rows.push(`Average Teaching Hours per Week : ${v(emp.teach_hrs_week)}`)
  if (v(emp.vacation)) rows.push(`Vacation : ${v(emp.vacation)}`)
  const housing = [v(emp.housing_type), v(emp.housing_detail), v(emp.housing)].filter(Boolean).join(', ')
  if (housing) rows.push(`Housing: ${housing}`)
  if (v(emp.benefits)) rows.push(`Employee Benefits : ${v(emp.benefits)}`)
  return rows.join('\n')
}

const STATUS_BTN: Record<string, { bg: string; color: string; border: string }> = {
  open:       { bg: '#e0f2fe', color: '#0369a1', border: '#7dd3fc' },
  contacted:  { bg: '#fef9c3', color: '#854d0e', border: '#fde047' },
  hired:      { bg: '#dcfce7', color: '#166534', border: '#86efac' },
  hold:       { bg: '#f3f4f6', color: '#6b7280', border: '#d1d5db' },
  closed:     { bg: '#e5e7eb', color: '#374151', border: '#9ca3af' },
  blacklist:  { bg: '#fee2e2', color: '#991b1b', border: '#fca5a5' },
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

        {/* ══ 1. MEMO 박스 (최상단 — 노랑) ══ */}
        <div style={{ position: 'relative', zIndex: 1, marginBottom: 10 }}>
          <div style={{
            background: '#fffde7', border: '1px solid #e8d87a', borderRadius: 6,
            padding: '10px 14px', animation: isGlow ? 'blink 0.8s step-end infinite' : 'none',
          }}>
            {/* 헤더 행: MEMO 레이블 + 버튼들 (항상 같은 위치) */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: editingMemo ? 8 : 0 }}>
              <span style={{ fontWeight: 800, color: '#92700a', fontSize: '0.72rem', letterSpacing: '0.1em', flexShrink: 0 }}>MEMO</span>
              <div style={{ flex: 1 }} />
              {editingMemo ? (
                <>
                  <button type="button"
                    onClick={() => { onEditMemo?.(employer.id, memoVal); setEditingMemo(false) }}
                    style={{ ...btnBlue, fontSize: '0.75rem', padding: '3px 12px' }}>
                    💾 저장
                  </button>
                  <button type="button"
                    onClick={() => { setMemoVal(employer.memo || ''); setEditingMemo(false) }}
                    style={{ ...btnGhost, fontSize: '0.75rem', padding: '3px 10px' }}>
                    취소
                  </button>
                </>
              ) : (
                <button type="button" onClick={() => setEditingMemo(true)}
                  style={{ ...btnBase, background: '#fff7ed', border: '1px solid #fed7aa', color: '#c2410c', fontSize: '0.75rem', padding: '3px 10px' }}>
                  수정
                </button>
              )}
            </div>
            {/* 본문: 편집 중이면 textarea, 아니면 텍스트 */}
            {editingMemo ? (
              <textarea
                value={memoVal}
                onChange={e => setMemoVal(e.target.value)}
                autoFocus
                placeholder="내부 메모 (원장 연락처, 특이사항 등)"
                style={{
                  width: '100%', minHeight: 80, border: '1px solid #e0cc6a', borderRadius: 4,
                  padding: '8px 10px', fontSize: '0.88rem', background: '#fffff5',
                  resize: 'vertical', outline: 'none', lineHeight: 1.7, fontFamily: 'inherit', color: '#111',
                }}
              />
            ) : (
              <span style={{
                display: 'block', fontSize: '0.9rem', lineHeight: 1.75,
                color: employer.memo ? '#111' : '#c8b870',
                fontStyle: employer.memo ? 'normal' : 'italic',
                whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                fontWeight: employer.memo ? 500 : 400,
              }}>
                {employer.memo || '메모를 추가하려면 수정을 클릭하세요'}
              </span>
            )}
          </div>
        </div>

        {/* ══ 2. 상태 버튼 (MEMO 바로 아래) ══ */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 14, flexWrap: 'wrap', position: 'relative', zIndex: 1 }}>
          <span style={{ fontSize: '0.7rem', color: '#aaa', fontWeight: 700, marginRight: 4 }}>상태</span>
          {(['open','contacted','hired','hold','closed','blacklist'] as const).map(s => {
            const active = employer.status === s
            const c = STATUS_BTN[s]
            return (
              <button key={s} type="button"
                onClick={() => onStatusChange(employer.id, s)}
                style={{
                  padding: '5px 14px', borderRadius: 20, fontSize: '0.78rem', fontWeight: active ? 800 : 500,
                  background: active ? c.bg : '#f5f5f5',
                  color: active ? c.color : '#aaa',
                  border: `1.5px solid ${active ? c.border : '#e5e5e5'}`,
                  cursor: 'pointer', transition: 'all 0.15s',
                  boxShadow: active ? '0 1px 4px rgba(0,0,0,0.10)' : 'none',
                }}>
                {s}
              </button>
            )
          })}
          <span style={{ fontSize: '0.7rem', color: '#ccc', marginLeft: 'auto' }}>{employer.created_at?.slice(0, 10)}</span>
        </div>

        {/* ══ 구분선 ══ */}
        <div style={{ borderTop: '1px dashed #d4c87a', marginBottom: 14, position: 'relative', zIndex: 1 }} />

        {/* ══ 3. 헤더: Job번호(초록+도시) + 업체명 + 이동버튼 ══ */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, position: 'relative', zIndex: 2 }}>
          <span style={{
            fontFamily: "'Consolas',monospace", fontSize: '1.0rem', fontWeight: 800,
            background: isNewCode ? '#2563eb' : '#f0fdf4',
            color: isNewCode ? '#fff' : '#166534',
            border: isNewCode ? 'none' : '1px solid #bbf7d0',
            padding: '4px 14px', borderRadius: 6, flexShrink: 0,
            display: 'inline-flex', alignItems: 'center', gap: 6,
          }}>
            {jobNo}
            {(province || city) && (
              <span style={{ fontWeight: 500, fontSize: '0.85rem', opacity: 0.8 }}>
                · {[province, city].filter(Boolean).join(' ')}
              </span>
            )}
          </span>
          <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#111', flex: 1 }}>{displayName}</span>
          {isBlacklist && (
            <span style={{ fontSize: '0.72rem', background: '#dc2626', color: '#fff', padding: '2px 9px', borderRadius: 999, fontWeight: 800, flexShrink: 0 }}>BLACKLIST</span>
          )}
          <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
            {!isFirst && <button type="button" onClick={onMoveTop} style={btnBase}>⤒ 맨위로</button>}
            {!isFirst && <button type="button" onClick={onMoveUp} style={btnBase}>↑ 위로</button>}
            {!isLast && <button type="button" onClick={onMoveDown} style={btnBase}>↓ 아래로</button>}
            {!editingRaw ? (
              <button type="button" onClick={() => setEditingRaw(true)}
                style={{ ...btnBase, background: '#fff7ed', border: '1px solid #fed7aa', color: '#c2410c' }}>
                본문 수정
              </button>
            ) : (
              <>
                <button type="button"
                  onClick={() => { onEditNotes?.(employer.id, rawVal); setEditingRaw(false) }}
                  style={{ ...btnBlue, fontSize: '0.75rem', padding: '3px 12px' }}>
                  💾 저장
                </button>
                <button type="button"
                  onClick={() => { setRawVal(rawText); setEditingRaw(false) }}
                  style={{ ...btnGhost, fontSize: '0.75rem', padding: '3px 10px' }}>
                  취소
                </button>
              </>
            )}
          </div>
          {isGlow && (
            <button type="button" onClick={() => onConfirm(employer.id)} style={{
              background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8,
              padding: '6px 16px', fontSize: '0.83rem', fontWeight: 700, cursor: 'pointer',
              animation: 'blink 0.8s step-end infinite', flexShrink: 0,
            }}>★ NEW — 확인</button>
          )}
        </div>

        {/* ══ 4. 본문 (실제 job 내용) ══ */}
        <div style={{ position: 'relative', zIndex: 1 }}>
          {editingRaw ? (
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
                return <div key={i} style={{ fontWeight: 500, color: '#222' }}>{t}</div>
              })}
            </div>
          )}
        </div>

        {/* ══ 5. CONTACT 섹션 (두꺼운 구분선 + 2컬럼) ══ */}
        <div style={{ marginTop: 18, paddingTop: 12, borderTop: '2.5px solid #e2e8f0', position: 'relative', zIndex: 1 }}>
          <span style={{ fontSize: '0.68rem', fontWeight: 800, color: '#94a3b8', letterSpacing: '0.15em', display: 'block', marginBottom: 10 }}>CONTACT INFO</span>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 24px' }}>
            {/* 왼쪽: 업체명 + 주소 */}
            <div>
              <div style={{ display: 'flex', gap: 8, fontSize: '0.86rem', marginBottom: 4 }}>
                <span style={{ color: '#64748b', fontWeight: 700, minWidth: 60, flexShrink: 0 }}>업체명</span>
                <span style={{ color: '#111', fontWeight: 600 }}>
                  {showPII ? (employer.school_name || employer.name || '—') : maskName(employer.school_name || employer.name)}
                </span>
              </div>
              <div style={{ display: 'flex', gap: 8, fontSize: '0.86rem' }}>
                <span style={{ color: '#64748b', fontWeight: 700, minWidth: 60, flexShrink: 0 }}>주소</span>
                <span style={{ color: '#333' }}>{v(employer.location) || [province, city].filter(Boolean).join(' ') || '—'}</span>
              </div>
            </div>
            {/* 오른쪽: 이메일 + 전화 */}
            <div>
              <div style={{ display: 'flex', gap: 8, fontSize: '0.86rem', marginBottom: 4 }}>
                <span style={{ color: '#64748b', fontWeight: 700, minWidth: 60, flexShrink: 0 }}>이메일</span>
                <span style={{ color: '#333' }}>{showPII ? (employer.email || '—') : maskEmail(employer.email)}</span>
              </div>
              <div style={{ display: 'flex', gap: 8, fontSize: '0.86rem' }}>
                <span style={{ color: '#64748b', fontWeight: 700, minWidth: 60, flexShrink: 0 }}>전화</span>
                <span style={{ color: '#333' }}>{showPII ? (employer.phone || '—') : maskPhone(employer.phone)}</span>
              </div>
            </div>
          </div>
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
