'use client'

/**
 * /admin/candidates — 원어민 관리 (엑셀 완전 재현)
 * 51-column horizontal scroll table, no detail view
 * Sticky: 이름+번호 left, 상태 right, header top
 * Inline memo editing, photo avatars, age calc, row color coding
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL
const PAGE_SIZE = 200

/* ─── Column definitions ─── */
interface ColDef {
  header: string
  field: string
  width: number
  bold?: boolean
  stickyLeft?: number
  stickyRight?: number
  type?: 'photo' | 'age' | 'memo'
}

const COLS: ColDef[] = [
  { header: '메일',                  field: 'email',                  width: 180 },
  { header: '이름',                  field: 'full_name',              width: 150, bold: true, stickyLeft: 0 },
  { header: '사진',                  field: 'photo_url',              width: 60,  type: 'photo' },
  { header: '번호',                  field: 'candidate_id',           width: 110, stickyLeft: 150 },
  { header: '국적',                  field: 'nationality',            width: 70 },
  { header: '배경',                  field: 'ancestry',               width: 80 },
  { header: '나이',                  field: 'dob',                    width: 55,  type: 'age' },
  { header: '성별',                  field: 'gender',                 width: 55 },
  { header: '현재',                  field: 'current_location',       width: 100 },
  { header: '시작',                  field: 'start_date',             width: 80 },
  { header: '대상',                  field: 'target',                 width: 100 },
  { header: '지역',                  field: 'area_prefs',             width: 100 },
  { header: '레퍼런스/근무처확인',   field: 'reference',              width: 130 },
  { header: '경력',                  field: 'experience',             width: 80 },
  { header: '한국',                  field: 'e_visa',                 width: 70 },
  { header: '선호/리크루터인터뷰',   field: 'job_prefs',              width: 150 },
  { header: '지원한곳/인터뷰',       field: 'interview_time',         width: 150, type: 'memo' },
  { header: '포지션제안/진행',       field: 'contract_progress',      width: 130 },
  { header: '현급',                  field: 'current_salary',         width: 80 },
  { header: '희망',                  field: 'desired_salary',         width: 80 },
  { header: '시간',                  field: 'working_hours',          width: 70 },
  { header: '학위',                  field: 'education_level',        width: 80 },
  { header: '전공',                  field: 'major',                  width: 80 },
  { header: '자격',                  field: 'certification',          width: 100 },
  { header: '서류',                  field: 'documents',              width: 80 },
  { header: '건강',                  field: 'health_info',            width: 70 },
  { header: '타투',                  field: 'tattoo',                 width: 55 },
  { header: '피어',                  field: 'piercings',              width: 55 },
  { header: '가족',                  field: 'dependents',             width: 55 },
  { header: '결혼',                  field: 'married',                width: 55 },
  { header: '숙소',                  field: 'housing',                width: 80 },
  { header: '종교',                  field: 'religion',               width: 55 },
  { header: '비자',                  field: 'visa_type',              width: 70 },
  { header: '카톡',                  field: 'kakaotalk',              width: 110 },
  { header: '번호',                  field: 'mobile_phone',           width: 120 },
  { header: '범죄',                  field: 'criminal_record',        width: 70 },
  { header: '국범',                  field: 'korean_criminal_record', width: 70 },
  { header: '정보',                  field: 'consent',                width: 55 },
  { header: '사실',                  field: 'fact_check',             width: 55 },
  { header: '경로',                  field: 'source',                 width: 80 },
  { header: '타임',                  field: 'interview_time',         width: 100 },
  { header: '채용',                  field: 'placed_company',         width: 120 },
  { header: '임금',                  field: 'placed_salary',          width: 80 },
  { header: '개시',                  field: 'process_date',           width: 80 },
  { header: '숙박',                  field: 'housing_type',           width: 80 },
  { header: '비용',                  field: 'referral_fee',           width: 80 },
  { header: '처리',                  field: 'last_activity',          width: 80 },
  { header: '과거',                  field: 'past_placement',         width: 100 },
  { header: '계산서',                field: 'invoice',                width: 80 },
  { header: '메모',                  field: 'recruiter_memo',         width: 200, type: 'memo' },
  { header: '상태',                  field: 'status',                 width: 90,  stickyRight: 0 },
]

const TABLE_W = COLS.reduce((s, c) => s + c.width, 0)

/* ─── Status ─── */
const STATUS_VALUES = ['Active', 'Inactive', 'new', 'reviewing', 'interviewing', 'offered', 'placed', 'rejected', 'withdrawn', 'blacklisted']
const statusColors: Record<string, string> = {
  Active:       'bg-blue-100 text-blue-700',
  new:          'bg-blue-100 text-blue-700',
  reviewing:    'bg-yellow-100 text-yellow-700',
  interviewing: 'bg-indigo-100 text-indigo-700',
  offered:      'bg-violet-100 text-violet-700',
  placed:       'bg-green-100 text-green-700',
  rejected:     'bg-red-100 text-red-700',
  withdrawn:    'bg-gray-200 text-gray-500',
  Inactive:     'bg-gray-100 text-gray-500',
  blacklisted:  'bg-red-200 text-red-800',
}

type TabType = 'all' | 'Active' | 'Inactive'

interface Candidate {
  id: string
  candidate_id?: string
  full_name?: string
  nationality?: string
  status: string
  [key: string]: string | null | undefined
}

/* ─── Helpers ─── */
function v(s: string | null | undefined): string {
  if (!s || s.trim() === '' || s.trim() === 'None' || s.trim() === 'N/A') return ''
  return s.trim()
}

function calcAge(dob: string | null | undefined): string {
  if (!v(dob)) return ''
  const d = new Date(dob!)
  if (isNaN(d.getTime())) return ''
  const t = new Date()
  let a = t.getFullYear() - d.getFullYear()
  if (t.getMonth() < d.getMonth() || (t.getMonth() === d.getMonth() && t.getDate() < d.getDate())) a--
  return String(a)
}

function getInitial(name: string | null | undefined): string {
  const n = v(name)
  return n ? n[0].toUpperCase() : '?'
}

function natColor(nat: string | null | undefined): string {
  const n = (nat ?? '').toLowerCase()
  if (/american|usa|united states|^us$/i.test(n)) return '#3b82f6'
  if (/british|uk|united kingdom|english/i.test(n)) return '#ef4444'
  if (/canadian|canada/i.test(n)) return '#dc2626'
  if (/australian|australia/i.test(n)) return '#16a34a'
  if (/south.african|south.africa/i.test(n)) return '#a855f7'
  return '#6b7280'
}

function rowBg(c: Candidate): string {
  if (v(c.placed_company)) return '#fef9c3'
  if (c.contract_offered === 'Y') return '#ffedd5'
  if (v(c.contract_progress)) return '#fae8ff'
  if (c.status === 'Active') return '#ffffff'
  return '#f8fafc'
}

/* ─── Scrollbar CSS ─── */
const SCROLL_CSS = `
.cand-scroll::-webkit-scrollbar { height: 10px }
.cand-scroll::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 5px }
.cand-scroll::-webkit-scrollbar-track { background: #e2e8f0 }
.cand-scroll { scrollbar-width: thin; scrollbar-color: #94a3b8 #e2e8f0 }
`

/* ═══════════════════════════════════════════════════════════════════ */
export default function CandidatesPage() {
  const { authed, login, headers, waking } = useAdminAuth()

  const [rows, setRows] = useState<Candidate[]>([])
  const [total, setTotal] = useState(0)
  const [activeCnt, setActiveCnt] = useState(0)
  const [inactiveCnt, setInactiveCnt] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  const [tab, setTab] = useState<TabType>('Active')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  /* ── Fetch ── */
  const fetchData = useCallback(async (q: string = '', statusTab: TabType = tab, pg: number = page) => {
    setLoading(true)
    setError(null)
    try {
      const offset = (pg - 1) * PAGE_SIZE
      const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) })
      if (statusTab !== 'all') params.set('status', statusTab)
      if (q) params.set('search', q)
      const res = await fetch(`${API}/api/admin/candidates?${params}`, { headers: headers() })
      if (res.status === 403) { setError('Invalid admin key.'); return }
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Error')
      setRows(json.data?.candidates ?? [])
      setTotal(json.data?.total ?? 0)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [headers, tab, page])

  const fetchCounts = useCallback(async () => {
    try {
      const [rA, rI] = await Promise.all([
        fetch(`${API}/api/admin/candidates?status=Active&limit=0&offset=0`, { headers: headers() }),
        fetch(`${API}/api/admin/candidates?status=Inactive&limit=0&offset=0`, { headers: headers() }),
      ])
      const [jA, jI] = await Promise.all([rA.json(), rI.json()])
      setActiveCnt(jA.data?.total ?? 0)
      setInactiveCnt(jI.data?.total ?? 0)
    } catch { /* ignore */ }
  }, [headers])

  useEffect(() => {
    if (authed) { fetchData(search, tab, page); fetchCounts() }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed, tab, page])

  /* ── Actions ── */
  const handleTabChange = (t: TabType) => { setTab(t); setPage(1); fetchData(search, t, 1) }
  const handleSearch = () => { setPage(1); fetchData(search, tab, 1) }

  const patchField = async (candidateId: string, field: string, value: string) => {
    const res = await fetch(`${API}/api/admin/candidates/${candidateId}`, {
      method: 'PATCH', headers: headers(),
      body: JSON.stringify({ [field]: value }),
    })
    if (!res.ok) throw new Error('Failed')
    setRows(prev => prev.map(r => r.candidate_id === candidateId ? { ...r, [field]: value } : r))
  }

  const updateStatus = async (candidateId: string, newStatus: string) => {
    try {
      await patchField(candidateId, 'status', newStatus)
      setActionMsg(`${candidateId} → ${newStatus}`)
      setTimeout(() => setActionMsg(null), 3000)
      fetchCounts()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: SCROLL_CSS }} />
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-[#1d1d1f]">원어민 관리</h1>
            <p className="text-sm text-[#86868b] mt-0.5">
              {loading ? '로딩 중...' : `${total.toLocaleString()}명`}
              {total > rows.length ? ` (표시: ${rows.length}명)` : ''}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {actionMsg && <span className="text-sm text-green-600 font-medium">{actionMsg}</span>}
            <button type="button" onClick={() => fetchData(search, tab, page)}
              className="text-sm text-[#0071e3] hover:underline font-medium">새로고침</button>
          </div>
        </div>

        {/* Tabs + Search */}
        <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex bg-gray-100 rounded-xl p-0.5">
              {([
                { key: 'all' as TabType, label: '전체', count: activeCnt + inactiveCnt },
                { key: 'Active' as TabType, label: 'Active', count: activeCnt },
                { key: 'Inactive' as TabType, label: 'Inactive', count: inactiveCnt },
              ]).map(t => (
                <button key={t.key} type="button" onClick={() => handleTabChange(t.key)}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                    tab === t.key ? 'bg-white text-[#1d1d1f] shadow-sm' : 'text-[#86868b] hover:text-[#424245]'
                  }`}>
                  {t.label}
                  <span className="ml-1.5 text-[11px] text-[#86868b]">{t.count.toLocaleString()}</span>
                </button>
              ))}
            </div>
            <div className="h-6 w-px bg-gray-200" />
            <input
              className="px-4 py-2 text-sm border border-gray-200 rounded-xl w-56 focus:outline-none focus:ring-2 focus:ring-blue-400"
              placeholder="이름, 이메일, 국적..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleSearch() }}
            />
            <button type="button" onClick={handleSearch}
              className="text-sm text-[#0071e3] hover:underline font-medium">검색</button>
          </div>
        </div>

        {error && <div className="p-4 bg-red-50 text-red-600 text-sm rounded-2xl">{error}</div>}

        {loading ? (
          <div className="text-center py-16 text-[#86868b] animate-pulse text-sm">로딩 중...</div>
        ) : rows.length === 0 ? (
          <div className="text-center py-16 text-[#86868b] text-sm">해당 지원자가 없습니다.</div>
        ) : (
          <div className="bg-white border border-[#e5e5e7] rounded-2xl overflow-hidden">
            <div className="cand-scroll overflow-x-scroll overflow-y-auto" style={{ maxHeight: 'calc(100vh - 220px)' }}>
              <table style={{ tableLayout: 'fixed', width: `${TABLE_W}px`, borderCollapse: 'separate', borderSpacing: 0 }}>
                <colgroup>
                  {COLS.map((col, i) => <col key={i} style={{ width: `${col.width}px` }} />)}
                </colgroup>
                <thead>
                  <tr>
                    {COLS.map((col, i) => {
                      const sticky: React.CSSProperties = { position: 'sticky', top: 0, zIndex: 30, background: '#f5f5f7' }
                      if (col.stickyLeft !== undefined) { sticky.left = col.stickyLeft; sticky.zIndex = 35 }
                      if (col.stickyRight !== undefined) { sticky.right = col.stickyRight; sticky.zIndex = 35 }
                      return (
                        <th key={i} style={sticky}
                          className="px-2 py-2.5 text-left text-[10px] text-[#86868b] font-semibold tracking-wider border-b border-[#e5e5e7] whitespace-nowrap">
                          {col.header}
                        </th>
                      )
                    })}
                  </tr>
                </thead>
                <tbody>
                  {rows.map(c => (
                    <CandRow key={c.id} c={c} onPatch={patchField} onStatusChange={updateStatus} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-1 py-2">
            <button type="button" disabled={page === 1}
              onClick={() => { setPage(page - 1); fetchData(search, tab, page - 1) }}
              className="px-3 py-1.5 rounded-lg text-sm font-medium disabled:opacity-30 hover:bg-gray-100 text-gray-600">&laquo;</button>
            {Array.from({ length: Math.min(totalPages, 9) }, (_, i) => {
              let p: number
              if (totalPages <= 9) p = i + 1
              else if (page <= 5) p = i + 1
              else if (page >= totalPages - 4) p = totalPages - 8 + i
              else p = page - 4 + i
              return (
                <button key={p} type="button" onClick={() => { setPage(p); fetchData(search, tab, p) }}
                  className={`w-9 h-9 rounded-lg text-sm font-semibold transition-all ${
                    p === page ? 'bg-[#0071e3] text-white shadow-md' : 'text-gray-600 hover:bg-gray-100'
                  }`}>{p}</button>
              )
            })}
            <button type="button" disabled={page === totalPages}
              onClick={() => { setPage(page + 1); fetchData(search, tab, page + 1) }}
              className="px-3 py-1.5 rounded-lg text-sm font-medium disabled:opacity-30 hover:bg-gray-100 text-gray-600">&raquo;</button>
          </div>
        )}
      </div>
    </>
  )
}

/* ═══════════════════════════════════════════════════════════════════ */
/* Row component                                                      */
/* ═══════════════════════════════════════════════════════════════════ */
function CandRow({ c, onPatch, onStatusChange }: {
  c: Candidate
  onPatch: (candidateId: string, field: string, value: string) => Promise<void>
  onStatusChange: (candidateId: string, status: string) => void
}) {
  const bg = rowBg(c)
  const cid = v(c.candidate_id) || c.id

  return (
    <tr style={{ background: bg }} className="hover:brightness-[0.97] transition-all">
      {COLS.map((col, i) => {
        const sty: React.CSSProperties = {
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }

        // Sticky positions
        if (col.stickyLeft !== undefined) {
          sty.position = 'sticky'; sty.left = col.stickyLeft; sty.zIndex = 15
          sty.background = bg; sty.boxShadow = '2px 0 4px rgba(0,0,0,0.04)'
        }
        if (col.stickyRight !== undefined) {
          sty.position = 'sticky'; sty.right = col.stickyRight; sty.zIndex = 15
          sty.background = bg; sty.boxShadow = '-2px 0 4px rgba(0,0,0,0.04)'
        }

        // Font
        if (col.bold) sty.fontWeight = 600

        // Photo column
        if (col.type === 'photo') {
          const url = v(c.photo_url)
          const bgColor = natColor(c.nationality)
          return (
            <td key={i} className="px-2 py-1.5 border-b border-[#f0f0f2]" style={sty}>
              {url ? (
                <img src={url} alt="" style={{ width: 38, height: 38, borderRadius: '50%', objectFit: 'cover' }} />
              ) : (
                <div style={{
                  width: 38, height: 38, borderRadius: '50%', background: bgColor,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#fff', fontSize: 14, fontWeight: 700,
                }}>
                  {getInitial(c.full_name)}
                </div>
              )}
            </td>
          )
        }

        // Age column
        if (col.type === 'age') {
          return (
            <td key={i} className="px-2 py-1.5 text-[12px] text-[#424245] border-b border-[#f0f0f2]" style={sty}>
              {calcAge(c[col.field])}
            </td>
          )
        }

        // Memo column (inline editable)
        if (col.type === 'memo') {
          return (
            <td key={i} className="px-2 py-1.5 border-b border-[#f0f0f2]"
              style={{ ...sty, whiteSpace: 'pre-wrap', overflow: 'hidden', maxHeight: 60 }}>
              <MemoCell
                value={v(c[col.field])}
                width={col.width}
                onSave={async (val: string) => { await onPatch(cid, col.field, val) }}
              />
            </td>
          )
        }

        // Status column
        if (col.field === 'status') {
          return (
            <td key={i} className="px-2 py-1.5 border-b border-[#f0f0f2]" style={sty}>
              <select
                className={`text-[11px] px-2 py-1 rounded-full font-semibold border-0 cursor-pointer ${statusColors[c.status] ?? 'bg-gray-100 text-gray-600'}`}
                value={c.status}
                onChange={e => onStatusChange(cid, e.target.value)}>
                {STATUS_VALUES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </td>
          )
        }

        // Default text cell
        return (
          <td key={i} className="px-2 py-1.5 text-[12px] text-[#424245] border-b border-[#f0f0f2]" style={sty}
            title={v(c[col.field])}>
            {v(c[col.field])}
          </td>
        )
      })}
    </tr>
  )
}

/* ═══════════════════════════════════════════════════════════════════ */
/* Memo inline edit cell                                              */
/* ═══════════════════════════════════════════════════════════════════ */
function MemoCell({ value, width, onSave }: {
  value: string; width: number
  onSave: (val: string) => Promise<void>
}) {
  const [editing, setEditing] = useState(false)
  const [text, setText] = useState(value)
  const [flash, setFlash] = useState<'ok' | 'err' | null>(null)
  const ref = useRef<HTMLTextAreaElement>(null)
  const saving = useRef(false)

  useEffect(() => { setText(value) }, [value])
  useEffect(() => { if (editing && ref.current) ref.current.focus() }, [editing])

  const save = async () => {
    if (saving.current) return
    saving.current = true
    setEditing(false)
    if (text === value) { saving.current = false; return }
    try {
      await onSave(text)
      setFlash('ok')
    } catch {
      setFlash('err')
      setText(value)
    }
    setTimeout(() => setFlash(null), 800)
    saving.current = false
  }

  if (editing) {
    return (
      <textarea
        ref={ref}
        value={text}
        onChange={e => setText(e.target.value)}
        onBlur={save}
        onKeyDown={e => { if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); save() } }}
        style={{ width: width - 16, height: 60, fontSize: 12, padding: 4, resize: 'none' }}
        className="border border-blue-400 rounded focus:outline-none"
      />
    )
  }

  return (
    <div
      onClick={e => { e.stopPropagation(); setEditing(true) }}
      style={{
        whiteSpace: 'pre-wrap', maxHeight: 60, overflow: 'hidden',
        cursor: 'text', fontSize: 12, minHeight: 20,
        background: flash === 'ok' ? '#dcfce7' : flash === 'err' ? '#fee2e2' : undefined,
        transition: 'background 0.3s', borderRadius: 2,
      }}
    >
      {value || '\u00A0'}
    </div>
  )
}
