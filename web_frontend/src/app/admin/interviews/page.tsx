'use client'

/**
 * /admin/interviews — 인터뷰 파이프라인 칸반 + 테이블 뷰 (Sprint C-FINAL)
 * API: GET/POST /api/admin/interviews, GET /api/admin/interviews/pipeline
 *      PATCH /api/admin/interviews/{id}/status, POST /api/admin/interviews/{id}/retry
 */

import { useState, useEffect, useCallback } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = `${API_URL}/api/admin`

// ─── 파이프라인 단계 ─────────────────────────────────────────
const PIPELINE_STAGES = [
  { key: 'pending',           label: '대기',    color: '#94a3b8' },
  { key: 'scheduled',         label: '예정',    color: '#3b82f6' },
  { key: 'completed',         label: '완료',    color: '#22c55e' },
  { key: 'contract_offered',  label: '계약제안', color: '#f59e0b' },
  { key: 'under_review',      label: '검토중',  color: '#f97316' },
  { key: 'contract_signed',   label: '계약수락', color: '#10b981' },
  { key: 'placement_pending', label: '배치대기', color: '#8b5cf6' },
  { key: 'placed',            label: '배치완료', color: '#059669' },
]

const NEGATIVE_STAGES = [
  { key: 'no_show_teacher',  label: '구직자노쇼', color: '#ef4444' },
  { key: 'no_show_employer', label: '구인자노쇼',  color: '#ef4444' },
  { key: 'no_show',          label: '노쇼',       color: '#ef4444' },
  { key: 'cancelled',        label: '취소',       color: '#6b7280' },
  { key: 'rejected',         label: '불합격',     color: '#dc2626' },
  { key: 'fallen_through',   label: '파기',       color: '#991b1b' },
]

const ALL_STATUSES = [...PIPELINE_STAGES, ...NEGATIVE_STAGES]

interface Interview {
  id: number
  candidate_number?: number
  candidate_name?: string
  candidate_email?: string
  candidate_id?: string
  job_number?: number
  employer_name?: string
  interview_date: string
  interview_time: string
  meet_link?: string
  status: string
  notes?: string
  result_notes?: string
}

// ─── 메인 컴포넌트 ────────────────────────────────────────────
export default function InterviewsPage() {
  const { adminKey, authed, login, waking } = useAdminAuth()
  const [interviews, setInterviews] = useState<Interview[]>([])
  const [view, setView] = useState<'pipeline' | 'table'>('pipeline')
  const [showForm, setShowForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [toast, setToast] = useState('')

  const [formData, setFormData] = useState({
    candidate_number: '', job_number: '',
    date: '', time: '10:00', duration: 30,
  })
  const [bulkMode, setBulkMode] = useState(false)
  const [bulkItems, setBulkItems] = useState<typeof formData[]>([])

  const hdrs = useCallback(() => ({
    'Content-Type': 'application/json',
    'x-admin-key': adminKey,
  }), [adminKey])

  const flash = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 2800)
  }

  const fetchAll = useCallback(async () => {
    if (!adminKey) return
    try {
      const res = await fetch(`${API}/interviews`, { headers: { 'x-admin-key': adminKey } })
      const data = await res.json()
      setInterviews(data.interviews || data.data?.interviews || [])
    } catch { /* silent */ }
    finally { setLoading(false) }
  }, [adminKey])

  useEffect(() => { if (authed) fetchAll() }, [authed, fetchAll])

  // ─── 상태 변경 ──────────────────────────────────────────────
  const changeStatus = async (ivId: number, newStatus: string, memo = '') => {
    try {
      const res = await fetch(`${API}/interviews/${ivId}/status`, {
        method: 'PATCH',
        headers: hdrs(),
        body: JSON.stringify({ status: newStatus, memo }),
      })
      if (!res.ok) { const d = await res.json(); flash(`오류: ${d.detail || res.status}`); return }
      flash(`상태 → ${ALL_STATUSES.find(s => s.key === newStatus)?.label || newStatus}`)
      fetchAll()
    } catch { flash('상태 변경 실패') }
  }

  // ─── 재시도 ─────────────────────────────────────────────────
  const retryInterview = async (ivId: number) => {
    try {
      await fetch(`${API}/interviews/${ivId}/retry`, { method: 'POST', headers: hdrs() })
      flash('재처리 시작')
      fetchAll()
    } catch { flash('재시도 실패') }
  }

  // ─── 인터뷰 생성 ─────────────────────────────────────────────
  const createInterview = async () => {
    const items = bulkMode ? bulkItems : [formData]
    if (!items.length || !items[0].candidate_number) { flash('구직자 번호를 입력하세요'); return }
    if (!items[0].date) { flash('날짜를 입력하세요'); return }

    let created = 0
    for (const item of items) {
      if (!item.candidate_number || !item.date) continue
      try {
        const res = await fetch(`${API}/interviews`, {
          method: 'POST',
          headers: hdrs(),
          body: JSON.stringify({
            candidate_id: String(item.candidate_number),
            candidate_name: `#${item.candidate_number}`,
            candidate_email: '',
            employer_name: item.job_number ? `Job#${item.job_number}` : '',
            employer_email: '',
            interview_date: item.date,
            interview_time: item.time || '10:00',
            duration_minutes: item.duration || 30,
            notes: item.job_number ? `job_number:${item.job_number}` : '',
          }),
        })
        if (res.ok) created++
      } catch { /* collect errors */ }
    }

    flash(`${created}건 인터뷰 생성 완료`)
    setShowForm(false)
    setFormData({ candidate_number: '', job_number: '', date: '', time: '10:00', duration: 30 })
    setBulkItems([])
    fetchAll()
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  const filtered = filter ? interviews.filter(iv => iv.status === filter) : interviews

  return (
    <div style={{ padding: '20px 24px', fontFamily: '-apple-system,sans-serif', maxWidth: 1500, margin: '0 auto' }}>

      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', top: 20, right: 24, zIndex: 9999,
          background: '#1d1d1f', color: '#fff', padding: '10px 18px',
          borderRadius: 8, fontSize: 13, fontWeight: 500,
          boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
        }}>{toast}</div>
      )}

      {/* 헤더 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>인터뷰 관리</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          {(['pipeline', 'table'] as const).map(v => (
            <button key={v} type="button" onClick={() => setView(v)} style={{
              padding: '6px 14px', borderRadius: 6, border: '1px solid #ddd',
              background: view === v ? '#2563eb' : '#fff',
              color: view === v ? '#fff' : '#333',
              cursor: 'pointer', fontSize: 13,
            }}>
              {v === 'pipeline' ? '파이프라인' : '테이블'}
            </button>
          ))}
          <button type="button" onClick={() => { setShowForm(!showForm); setBulkMode(false) }} style={{
            padding: '6px 14px', borderRadius: 6, border: 'none',
            background: '#22c55e', color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: 13,
          }}>
            + 인터뷰 생성
          </button>
          <button type="button" onClick={fetchAll} style={{
            padding: '6px 12px', borderRadius: 6, border: '1px solid #ddd',
            background: '#fff', cursor: 'pointer', fontSize: 13,
          }}>
            새로고침
          </button>
        </div>
      </div>

      {/* 생성 폼 */}
      {showForm && (
        <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 20, marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ margin: 0, fontSize: 15 }}>
              {bulkMode ? `일괄 생성 (${bulkItems.length}건)` : '인터뷰 생성'}
            </h3>
            <label style={{ fontSize: 13, cursor: 'pointer' }}>
              <input type="checkbox" checked={bulkMode} onChange={e => {
                setBulkMode(e.target.checked)
                if (e.target.checked && bulkItems.length === 0)
                  setBulkItems([{ candidate_number: '', job_number: '', date: '', time: '10:00', duration: 30 }])
              }} style={{ marginRight: 4 }} />
              일괄 모드
            </label>
          </div>

          {!bulkMode ? (
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end' }}>
              {[
                { label: '구직자 번호', key: 'candidate_number', ph: '10001', w: 90, type: 'number' },
                { label: 'Job#',       key: 'job_number',        ph: '1003',  w: 90, type: 'number' },
                { label: '날짜',       key: 'date',              ph: '',      w: 130, type: 'date' },
                { label: '시간',       key: 'time',              ph: '',      w: 100, type: 'time' },
              ].map(f => (
                <div key={f.key}>
                  <div style={{ fontSize: 12, color: '#666', marginBottom: 2 }}>{f.label}</div>
                  <input
                    type={f.type} placeholder={f.ph}
                    value={(formData as Record<string, string | number>)[f.key] as string}
                    onChange={e => setFormData({ ...formData, [f.key]: e.target.value })}
                    style={{ padding: '6px 10px', border: '1px solid #ddd', borderRadius: 4, width: f.w }}
                  />
                </div>
              ))}
              <button type="button" onClick={createInterview} style={{
                padding: '6px 20px', background: '#2563eb', color: '#fff',
                border: 'none', borderRadius: 4, cursor: 'pointer', fontWeight: 600, fontSize: 13,
              }}>생성</button>
            </div>
          ) : (
            <div>
              {bulkItems.map((item, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 6, alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: '#999', width: 20 }}>{i + 1}</span>
                  {(['candidate_number', 'job_number'] as const).map(k => (
                    <input key={k} type="number" placeholder={k === 'candidate_number' ? '구직자#' : 'Job#'}
                      value={item[k] as string}
                      onChange={e => {
                        const n = [...bulkItems]; n[i] = { ...n[i], [k]: e.target.value }; setBulkItems(n)
                      }}
                      style={{ padding: '4px 8px', border: '1px solid #ddd', borderRadius: 4, width: 80 }} />
                  ))}
                  <input type="date" value={item.date}
                    onChange={e => { const n = [...bulkItems]; n[i] = { ...n[i], date: e.target.value }; setBulkItems(n) }}
                    style={{ padding: '4px 8px', border: '1px solid #ddd', borderRadius: 4 }} />
                  <input type="time" value={item.time}
                    onChange={e => { const n = [...bulkItems]; n[i] = { ...n[i], time: e.target.value }; setBulkItems(n) }}
                    style={{ padding: '4px 8px', border: '1px solid #ddd', borderRadius: 4, width: 90 }} />
                  <button type="button" onClick={() => setBulkItems(bulkItems.filter((_, j) => j !== i))}
                    style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: 16 }}>✕</button>
                </div>
              ))}
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button type="button" onClick={() => setBulkItems([...bulkItems, { candidate_number: '', job_number: '', date: '', time: '10:00', duration: 30 }])}
                  style={{ padding: '4px 12px', border: '1px dashed #aaa', borderRadius: 4, background: '#fff', cursor: 'pointer', fontSize: 12 }}>
                  + 행 추가
                </button>
                <button type="button" onClick={createInterview} style={{
                  padding: '4px 16px', background: '#2563eb', color: '#fff',
                  border: 'none', borderRadius: 4, cursor: 'pointer', fontWeight: 600, fontSize: 13,
                }}>
                  {bulkItems.length}건 일괄 생성
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {loading && <div style={{ padding: 40, textAlign: 'center', color: '#888' }}>로딩 중...</div>}

      {/* 파이프라인 뷰 */}
      {!loading && view === 'pipeline' && (
        <div style={{ display: 'flex', gap: 10, overflowX: 'auto', paddingBottom: 20 }}>
          {PIPELINE_STAGES.map(stage => {
            const items = interviews.filter(iv => iv.status === stage.key)
            return (
              <div key={stage.key} style={{ minWidth: 175, maxWidth: 210, flex: '0 0 auto' }}>
                <div style={{
                  background: stage.color, color: '#fff', padding: '7px 10px',
                  borderRadius: '7px 7px 0 0', fontSize: 12, fontWeight: 600,
                  display: 'flex', justifyContent: 'space-between',
                }}>
                  <span>{stage.label}</span>
                  <span style={{ background: 'rgba(255,255,255,0.3)', borderRadius: 10, padding: '0 5px', fontSize: 11 }}>
                    {items.length}
                  </span>
                </div>
                <div style={{
                  background: '#f1f5f9', borderRadius: '0 0 7px 7px',
                  padding: 6, minHeight: 100, display: 'flex', flexDirection: 'column', gap: 5,
                }}>
                  {items.map(iv => (
                    <InterviewCard key={iv.id} iv={iv} allStatuses={ALL_STATUSES}
                      onChangeStatus={changeStatus} onRetry={retryInterview} />
                  ))}
                  {items.length === 0 && (
                    <div style={{ color: '#bbb', fontSize: 11, textAlign: 'center', padding: 16 }}>없음</div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* 테이블 뷰 */}
      {!loading && view === 'table' && (
        <div>
          <div style={{ marginBottom: 10, display: 'flex', gap: 8, alignItems: 'center' }}>
            <select value={filter} onChange={e => setFilter(e.target.value)}
              style={{ padding: '6px 10px', border: '1px solid #ddd', borderRadius: 4, fontSize: 13 }}>
              <option value="">전체 ({interviews.length}건)</option>
              {ALL_STATUSES.map(s => (
                <option key={s.key} value={s.key}>
                  {s.label} ({interviews.filter(iv => iv.status === s.key).length})
                </option>
              ))}
            </select>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f1f5f9' }}>
                {['ID', '구직자#', 'Job#', '날짜', '시간', '상태', 'Meet', '메모', '액션'].map(h => (
                  <th key={h} style={{ padding: '8px 10px', textAlign: 'left', borderBottom: '2px solid #e2e8f0', fontSize: 12 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(iv => {
                const st = ALL_STATUSES.find(s => s.key === iv.status)
                return (
                  <tr key={iv.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '6px 10px', color: '#888', fontSize: 11 }}>{iv.id}</td>
                    <td style={{ padding: '6px 10px', fontWeight: 700 }}>
                      {iv.candidate_number || iv.candidate_id || '-'}
                    </td>
                    <td style={{ padding: '6px 10px' }}>{iv.job_number || '-'}</td>
                    <td style={{ padding: '6px 10px' }}>{iv.interview_date}</td>
                    <td style={{ padding: '6px 10px' }}>{iv.interview_time}</td>
                    <td style={{ padding: '6px 10px' }}>
                      <span style={{
                        background: st?.color || '#999', color: '#fff',
                        padding: '2px 8px', borderRadius: 4, fontSize: 11,
                      }}>{st?.label || iv.status}</span>
                    </td>
                    <td style={{ padding: '6px 10px' }}>
                      {iv.meet_link
                        ? <a href={iv.meet_link} target="_blank" rel="noreferrer" style={{ color: '#2563eb', fontSize: 12 }}>참가</a>
                        : '-'}
                    </td>
                    <td style={{
                      padding: '6px 10px', maxWidth: 180, overflow: 'hidden',
                      textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 12, color: '#666',
                    }}>
                      {iv.notes || iv.result_notes || '-'}
                    </td>
                    <td style={{ padding: '6px 10px' }}>
                      <StatusSelect iv={iv} allStatuses={ALL_STATUSES} onChangeStatus={changeStatus} />
                      {(iv.status === 'pending' || iv.status === 'pending_retry') && (
                        <button type="button" onClick={() => retryInterview(iv.id)} style={{
                          marginLeft: 4, padding: '2px 6px', fontSize: 11,
                          border: '1px solid #f59e0b', borderRadius: 4, background: '#fffbeb', cursor: 'pointer',
                        }}>재시도</button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div style={{ textAlign: 'center', color: '#aaa', padding: 40, fontSize: 13 }}>
              {filter ? `'${ALL_STATUSES.find(s => s.key === filter)?.label}' 상태 없음` : '인터뷰 없음'}
            </div>
          )}
        </div>
      )}
    </div>
  )
}


// ─── 칸반 카드 ────────────────────────────────────────────────
function InterviewCard({ iv, allStatuses, onChangeStatus, onRetry }: {
  iv: Interview
  allStatuses: typeof ALL_STATUSES
  onChangeStatus: (id: number, status: string, memo: string) => void
  onRetry: (id: number) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [memo, setMemo] = useState('')

  return (
    <div style={{
      background: '#fff', borderRadius: 6, padding: '8px 10px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.07)', cursor: 'pointer', fontSize: 12,
    }} onClick={() => setExpanded(!expanded)}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ fontWeight: 700 }}>#{iv.candidate_number || iv.candidate_id}</span>
        <span style={{ fontSize: 11, color: '#888' }}>{iv.interview_date}</span>
      </div>
      <div style={{ color: '#555', marginTop: 2 }}>
        {iv.job_number ? `Job#${iv.job_number}` : (iv.employer_name || '—')} · {iv.interview_time}
      </div>
      {iv.meet_link && (
        <a href={iv.meet_link} target="_blank" rel="noreferrer"
          onClick={e => e.stopPropagation()}
          style={{ color: '#2563eb', fontSize: 11 }}>Meet 참가</a>
      )}
      {(iv.status === 'pending' || iv.status === 'pending_retry') && (
        <button type="button" onClick={e => { e.stopPropagation(); onRetry(iv.id) }} style={{
          marginTop: 4, padding: '2px 8px', fontSize: 10,
          border: '1px solid #f59e0b', borderRadius: 4, background: '#fffbeb', cursor: 'pointer', display: 'block',
        }}>재시도</button>
      )}
      {expanded && (
        <div style={{ marginTop: 8, borderTop: '1px solid #f1f5f9', paddingTop: 6 }}
          onClick={e => e.stopPropagation()}>
          {iv.notes && <div style={{ fontSize: 11, color: '#666', marginBottom: 4 }}>{iv.notes}</div>}
          <input
            type="text" placeholder="메모 (선택)" value={memo}
            onChange={e => setMemo(e.target.value)}
            style={{ width: '100%', padding: '4px 6px', border: '1px solid #ddd', borderRadius: 4, fontSize: 11, marginBottom: 4, boxSizing: 'border-box' }}
            onClick={e => e.stopPropagation()}
          />
          <select defaultValue="" onChange={e => {
            if (e.target.value) { onChangeStatus(iv.id, e.target.value, memo); setMemo(''); e.target.value = '' }
          }} style={{ width: '100%', padding: '4px', fontSize: 11, border: '1px solid #ddd', borderRadius: 4 }}>
            <option value="">→ 상태 변경</option>
            {allStatuses.filter(s => s.key !== iv.status).map(s => (
              <option key={s.key} value={s.key}>{s.label}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  )
}


// ─── 테이블용 상태 셀렉트 ─────────────────────────────────────
function StatusSelect({ iv, allStatuses, onChangeStatus }: {
  iv: Interview
  allStatuses: typeof ALL_STATUSES
  onChangeStatus: (id: number, status: string, memo: string) => void
}) {
  const [memo, setMemo] = useState('')
  const [open, setOpen] = useState(false)

  return (
    <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
      <select defaultValue="" onChange={e => {
        if (e.target.value) { onChangeStatus(iv.id, e.target.value, memo); e.target.value = '' }
      }} style={{ padding: '2px 4px', fontSize: 11, border: '1px solid #ddd', borderRadius: 4 }}>
        <option value="">변경</option>
        {allStatuses.filter(s => s.key !== iv.status).map(s => (
          <option key={s.key} value={s.key}>{s.label}</option>
        ))}
      </select>
      {open
        ? <input type="text" placeholder="메모" value={memo} autoFocus
            onChange={e => setMemo(e.target.value)}
            onBlur={() => setOpen(false)}
            style={{ padding: '2px 4px', fontSize: 11, border: '1px solid #ddd', borderRadius: 4, width: 80 }} />
        : <button type="button" onClick={() => setOpen(true)}
            style={{ padding: '2px 5px', fontSize: 10, border: '1px solid #ddd', borderRadius: 4, background: '#f8fafc', cursor: 'pointer' }}>
            메모
          </button>
      }
    </span>
  )
}
