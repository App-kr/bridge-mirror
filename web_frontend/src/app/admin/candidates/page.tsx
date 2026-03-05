'use client'

/**
 * /admin/candidates — 원어민 관리 (엑셀 완전 재현)
 * Full DB columns, dual scrollbar, column resize, row expand, add modal
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL
const PAGE_SIZE = 200

/* ─── Column definitions (DB 순서대로) ─── */
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
  // 기본 정보
  { header: '이름',       field: 'full_name',              width: 150, bold: true, stickyLeft: 0 },
  { header: '사진',       field: 'photo_url',              width: 60,  type: 'photo' },
  { header: '번호',       field: 'candidate_id',           width: 110, stickyLeft: 150 },
  { header: '메일',       field: 'email',                  width: 180 },
  { header: '국적',       field: 'nationality',            width: 70 },
  { header: '배경',       field: 'ancestry',               width: 80 },
  { header: '나이',       field: 'dob',                    width: 55,  type: 'age' },
  { header: '성별',       field: 'gender',                 width: 55 },
  { header: '현재위치',   field: 'current_location',       width: 100 },
  // 학력/자격
  { header: '학위',       field: 'education_level',        width: 80 },
  { header: '전공',       field: 'major',                  width: 80 },
  { header: '자격',       field: 'certification',          width: 100 },
  // 비자/서류
  { header: 'E비자',      field: 'e_visa',                 width: 70 },
  { header: 'ARC',        field: 'arc_holders',            width: 70 },
  { header: '여권',       field: 'passport',               width: 70 },
  { header: '범죄',       field: 'criminal_record',        width: 70 },
  { header: '서류',       field: 'documents',              width: 80 },
  { header: '서류상태',   field: 'doc_status',             width: 80 },
  { header: '범죄확인',   field: 'criminal_record_check',  width: 80 },
  // 채용 희망
  { header: '시작',       field: 'start_date',             width: 80 },
  { header: '대상',       field: 'target',                 width: 100 },
  { header: '지역',       field: 'area_prefs',             width: 100 },
  { header: '직무선호',   field: 'job_prefs',              width: 150, type: 'memo' },
  { header: '경력',       field: 'experience',             width: 80 },
  { header: '고용형태',   field: 'employment',             width: 80 },
  // 레퍼런스/급여
  { header: '레퍼런스',   field: 'reference',              width: 130 },
  { header: '현급',       field: 'current_salary',         width: 80 },
  { header: '희망',       field: 'desired_salary',         width: 80 },
  { header: '인터뷰',     field: 'interview_time',         width: 100, type: 'memo' },
  // 개인정보
  { header: '숙소',       field: 'housing',                width: 80 },
  { header: '배려사항',   field: 'personal_consideration', width: 120, type: 'memo' },
  { header: '종교',       field: 'religion',               width: 55 },
  { header: '건강',       field: 'health_info',            width: 70 },
  { header: '피어싱',     field: 'piercings',              width: 55 },
  { header: '타투',       field: 'tattoo',                 width: 55 },
  { header: '부양',       field: 'dependents',             width: 55 },
  { header: '반려',       field: 'pets',                   width: 55 },
  { header: '결혼',       field: 'married',                width: 55 },
  { header: '국범',       field: 'korean_criminal_record', width: 70 },
  // 연락처
  { header: '카톡',       field: 'kakaotalk',              width: 110 },
  { header: '전화',       field: 'mobile_phone',           width: 120 },
  { header: '동의',       field: 'consent',                width: 55 },
  { header: '팩트',       field: 'fact_check',             width: 55 },
  // 소스/날짜
  { header: '경로',       field: 'source',                 width: 80 },
  { header: '소스파일',   field: 'source_file',            width: 100 },
  { header: '등록일',     field: 'created_at',             width: 90 },
  { header: '경위',       field: 'how_to',                 width: 80 },
  { header: '메모',       field: 'notes',                  width: 200, type: 'memo' },
  // 운영 정보
  { header: '시간',       field: 'working_hours',          width: 70 },
  { header: '비자종류',   field: 'visa_type',              width: 70 },
  { header: '진행',       field: 'contract_progress',      width: 130 },
  { header: '채용처',     field: 'placed_company',         width: 120 },
  { header: '채용급',     field: 'placed_salary',          width: 80 },
  { header: '처리일',     field: 'process_date',           width: 80 },
  { header: '숙박유형',   field: 'housing_type',           width: 80 },
  { header: '수수료',     field: 'referral_fee',           width: 80 },
  { header: '최근활동',   field: 'last_activity',          width: 80 },
  { header: '과거배치',   field: 'past_placement',         width: 100 },
  { header: '계산서',     field: 'invoice',                width: 80 },
  { header: '리크루터메모', field: 'recruiter_memo',        width: 200, type: 'memo' },
  // 상태 (sticky right)
  { header: '상태',       field: 'status',                 width: 90,  stickyRight: 0 },
]

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

function fmtDate(d: string | null | undefined): string {
  const s = v(d)
  if (!s) return ''
  if (s.length > 10) return s.slice(0, 10)
  return s
}

/* ─── Scrollbar CSS ─── */
const SCROLL_CSS = `
.cand-scroll::-webkit-scrollbar { height: 10px }
.cand-scroll::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 5px }
.cand-scroll::-webkit-scrollbar-track { background: #e2e8f0 }
.cand-scroll { scrollbar-width: thin; scrollbar-color: #94a3b8 #e2e8f0 }
.col-resize-handle:hover { background: #3b82f6 !important }
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

  // Column resize state
  const [colWidths, setColWidths] = useState<Record<string, number>>(() => {
    const w: Record<string, number> = {}
    COLS.forEach(c => { w[c.field + '_' + c.header] = c.width })
    return w
  })

  // Row expand state
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  // Dual scrollbar refs
  const topScrollRef = useRef<HTMLDivElement>(null)
  const bottomScrollRef = useRef<HTMLDivElement>(null)
  const tableRef = useRef<HTMLTableElement>(null)
  const [tableWidth, setTableWidth] = useState(0)

  // Add modal
  const [showAddModal, setShowAddModal] = useState(false)

  // Measure table width for top scrollbar
  useEffect(() => {
    if (!tableRef.current) return
    const obs = new ResizeObserver(entries => {
      for (const e of entries) setTableWidth(e.contentRect.width)
    })
    obs.observe(tableRef.current)
    return () => obs.disconnect()
  }, [rows])

  // Compute total table width from colWidths
  const computedTableW = COLS.reduce((s, c) => s + (colWidths[c.field + '_' + c.header] || c.width), 0)

  /* ── Column Resize ── */
  const startResize = (e: React.MouseEvent, colKey: string, defaultW: number) => {
    e.preventDefault()
    e.stopPropagation()
    const startX = e.clientX
    const startWidth = colWidths[colKey] || defaultW
    const onMove = (ev: MouseEvent) => {
      const diff = ev.clientX - startX
      setColWidths(prev => ({ ...prev, [colKey]: Math.max(40, startWidth + diff) }))
    }
    const onUp = () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }

  /* ── Scroll Sync ── */
  const onTopScroll = () => {
    if (topScrollRef.current && bottomScrollRef.current) {
      bottomScrollRef.current.scrollLeft = topScrollRef.current.scrollLeft
    }
  }
  const onBottomScroll = () => {
    if (topScrollRef.current && bottomScrollRef.current) {
      topScrollRef.current.scrollLeft = bottomScrollRef.current.scrollLeft
    }
  }

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

  const createCandidate = async (data: Record<string, string>) => {
    const res = await fetch(`${API}/api/admin/candidates`, {
      method: 'POST', headers: headers(),
      body: JSON.stringify(data),
    })
    const json = await res.json()
    if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Error')
    setShowAddModal(false)
    setActionMsg('후보자 등록 완료')
    setTimeout(() => setActionMsg(null), 3000)
    fetchData(search, tab, page)
    fetchCounts()
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
            <button type="button" onClick={() => setShowAddModal(true)}
              className="px-4 py-2 bg-[#0071e3] text-white text-sm font-semibold rounded-xl hover:bg-[#0077ED] transition-colors">
              + 새 후보자
            </button>
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
            <span className="text-[11px] text-[#86868b]">더블클릭: 행 확장</span>
          </div>
        </div>

        {error && <div className="p-4 bg-red-50 text-red-600 text-sm rounded-2xl">{error}</div>}

        {loading ? (
          <div className="text-center py-16 text-[#86868b] animate-pulse text-sm">로딩 중...</div>
        ) : rows.length === 0 ? (
          <div className="text-center py-16 text-[#86868b] text-sm">해당 지원자가 없습니다.</div>
        ) : (
          <div className="bg-white border border-[#e5e5e7] rounded-2xl overflow-hidden">
            {/* Top scrollbar */}
            <div
              ref={topScrollRef}
              onScroll={onTopScroll}
              className="cand-scroll"
              style={{ overflowX: 'auto', overflowY: 'hidden', height: 14, borderBottom: '1px solid #e5e5e7' }}
            >
              <div style={{ width: Math.max(computedTableW, tableWidth), height: 1 }} />
            </div>

            {/* Table */}
            <div
              ref={bottomScrollRef}
              onScroll={onBottomScroll}
              className="cand-scroll overflow-x-auto overflow-y-auto"
              style={{ maxHeight: 'calc(100vh - 260px)' }}
            >
              <table
                ref={tableRef}
                style={{ tableLayout: 'fixed', width: `${computedTableW}px`, borderCollapse: 'separate', borderSpacing: 0 }}
              >
                <colgroup>
                  {COLS.map((col, i) => {
                    const key = col.field + '_' + col.header
                    return <col key={i} style={{ width: `${colWidths[key] || col.width}px` }} />
                  })}
                </colgroup>
                <thead>
                  <tr>
                    {COLS.map((col, i) => {
                      const colKey = col.field + '_' + col.header
                      const w = colWidths[colKey] || col.width
                      const sticky: React.CSSProperties = { position: 'sticky', top: 0, zIndex: 30, background: '#f5f5f7', width: w }
                      if (col.stickyLeft !== undefined) { sticky.left = col.stickyLeft; sticky.zIndex = 35 }
                      if (col.stickyRight !== undefined) { sticky.right = col.stickyRight; sticky.zIndex = 35 }
                      return (
                        <th key={i} style={sticky}
                          className="px-2 py-2.5 text-left text-[10px] text-[#86868b] font-semibold tracking-wider border-b border-[#e5e5e7] whitespace-nowrap select-none relative">
                          {col.header}
                          <div
                            className="col-resize-handle"
                            onMouseDown={e => startResize(e, colKey, col.width)}
                            style={{
                              position: 'absolute', right: 0, top: 0, bottom: 0, width: 5,
                              cursor: 'col-resize', background: 'transparent',
                            }}
                          />
                        </th>
                      )
                    })}
                  </tr>
                </thead>
                <tbody>
                  {rows.map(c => (
                    <CandRow
                      key={c.id}
                      c={c}
                      colWidths={colWidths}
                      expanded={expandedRows.has(c.id)}
                      onToggleExpand={() => {
                        setExpandedRows(prev => {
                          const next = new Set(prev)
                          next.has(c.id) ? next.delete(c.id) : next.add(c.id)
                          return next
                        })
                      }}
                      onPatch={patchField}
                      onStatusChange={updateStatus}
                    />
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

      {/* Add Modal */}
      {showAddModal && (
        <AddCandidateModal
          onClose={() => setShowAddModal(false)}
          onCreate={createCandidate}
        />
      )}
    </>
  )
}

/* ═══════════════════════════════════════════════════════════════════ */
/* Row component                                                      */
/* ═══════════════════════════════════════════════════════════════════ */
function CandRow({ c, colWidths, expanded, onToggleExpand, onPatch, onStatusChange }: {
  c: Candidate
  colWidths: Record<string, number>
  expanded: boolean
  onToggleExpand: () => void
  onPatch: (candidateId: string, field: string, value: string) => Promise<void>
  onStatusChange: (candidateId: string, status: string) => void
}) {
  const bg = rowBg(c)
  const cid = v(c.candidate_id) || c.id

  return (
    <tr
      style={{
        background: bg,
        height: expanded ? 'auto' : 48,
        maxHeight: expanded ? 'none' : 48,
      }}
      className="hover:brightness-[0.97] transition-all"
      onDoubleClick={onToggleExpand}
    >
      {COLS.map((col, i) => {
        const colKey = col.field + '_' + col.header
        const w = colWidths[colKey] || col.width
        const sty: React.CSSProperties = {
          width: w,
          maxWidth: w,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: expanded ? 'pre-wrap' : 'nowrap',
        }

        if (col.stickyLeft !== undefined) {
          sty.position = 'sticky'; sty.left = col.stickyLeft; sty.zIndex = 15
          sty.background = bg; sty.boxShadow = '2px 0 4px rgba(0,0,0,0.04)'
        }
        if (col.stickyRight !== undefined) {
          sty.position = 'sticky'; sty.right = col.stickyRight; sty.zIndex = 15
          sty.background = bg; sty.boxShadow = '-2px 0 4px rgba(0,0,0,0.04)'
        }
        if (col.bold) sty.fontWeight = 600

        // Photo
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

        // Age
        if (col.type === 'age') {
          return (
            <td key={i} className="px-2 py-1.5 text-[12px] text-[#424245] border-b border-[#f0f0f2]" style={sty}>
              {calcAge(c[col.field])}
            </td>
          )
        }

        // Memo (inline editable)
        if (col.type === 'memo') {
          return (
            <td key={i} className="px-2 py-1.5 border-b border-[#f0f0f2]"
              style={{ ...sty, whiteSpace: 'pre-wrap', overflow: expanded ? 'visible' : 'hidden', maxHeight: expanded ? 'none' : 60 }}>
              <MemoCell
                value={v(c[col.field])}
                width={w}
                onSave={async (val: string) => { await onPatch(cid, col.field, val) }}
              />
            </td>
          )
        }

        // Status select
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

        // Candidate ID → link
        if (col.field === 'candidate_id') {
          return (
            <td key={i} className="px-2 py-1.5 text-[12px] border-b border-[#f0f0f2]" style={sty}>
              <a
                href={`/admin/matching?candidate=${encodeURIComponent(cid)}`}
                className="text-[#0071e3] hover:underline font-medium"
                title="프로필 매칭"
              >
                {v(c[col.field])}
              </a>
            </td>
          )
        }

        // created_at → date format
        if (col.field === 'created_at') {
          return (
            <td key={i} className="px-2 py-1.5 text-[12px] text-[#424245] border-b border-[#f0f0f2]" style={sty}
              title={v(c[col.field])}>
              {fmtDate(c[col.field])}
            </td>
          )
        }

        // Default
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

/* ═══════════════════════════════════════════════════════════════════ */
/* Add Candidate Modal                                                */
/* ═══════════════════════════════════════════════════════════════════ */
const ADD_FIELDS = [
  { key: 'full_name', label: '이름 *', required: true },
  { key: 'email', label: '이메일' },
  { key: 'nationality', label: '국적' },
  { key: 'gender', label: '성별' },
  { key: 'dob', label: '생년월일', placeholder: 'YYYY-MM-DD' },
  { key: 'mobile_phone', label: '전화번호' },
  { key: 'kakaotalk', label: '카카오톡' },
  { key: 'current_location', label: '현재 위치' },
  { key: 'start_date', label: '시작 가능일' },
  { key: 'target', label: '대상 (유아/초등/중등)' },
  { key: 'area_prefs', label: '지역 선호' },
  { key: 'education_level', label: '학위' },
  { key: 'major', label: '전공' },
  { key: 'certification', label: '자격증' },
  { key: 'experience', label: '경력' },
  { key: 'e_visa', label: 'E비자' },
  { key: 'visa_type', label: '비자 종류' },
  { key: 'notes', label: '메모', textarea: true },
]

function AddCandidateModal({ onClose, onCreate }: {
  onClose: () => void
  onCreate: (data: Record<string, string>) => Promise<void>
}) {
  const [form, setForm] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const handleSave = async () => {
    if (!(form.full_name ?? '').trim()) { setErr('이름은 필수입니다.'); return }
    setSaving(true)
    setErr(null)
    try {
      await onCreate(form)
    } catch (e) {
      setErr(e instanceof Error ? e.message : '등록 실패')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[85vh] flex flex-col"
        onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#e5e5e7]">
          <h2 className="text-lg font-bold text-[#1d1d1f]">새 후보자 추가</h2>
          <button type="button" onClick={onClose}
            className="text-[#86868b] hover:text-[#1d1d1f] text-xl font-bold w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100">
            ✕
          </button>
        </div>

        {/* Form */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
          {ADD_FIELDS.map(f => (
            <div key={f.key}>
              <label className="block text-xs font-semibold text-[#86868b] mb-1">{f.label}</label>
              {f.textarea ? (
                <textarea
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400 resize-none"
                  rows={3}
                  value={form[f.key] ?? ''}
                  onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                />
              ) : (
                <input
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400"
                  placeholder={f.placeholder ?? ''}
                  value={form[f.key] ?? ''}
                  onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                />
              )}
            </div>
          ))}
          {err && <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-xl">{err}</div>}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#e5e5e7]">
          <button type="button" onClick={onClose}
            className="px-5 py-2 text-sm font-semibold text-[#86868b] hover:text-[#1d1d1f] rounded-xl hover:bg-gray-100 transition-colors">
            취소
          </button>
          <button type="button" onClick={handleSave} disabled={saving}
            className="px-5 py-2 text-sm font-semibold text-white bg-[#0071e3] rounded-xl hover:bg-[#0077ED] disabled:opacity-50 transition-colors">
            {saving ? '저장 중...' : '저장'}
          </button>
        </div>
      </div>
    </div>
  )
}
