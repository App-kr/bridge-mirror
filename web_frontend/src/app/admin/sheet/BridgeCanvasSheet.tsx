'use client'

/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet v3 — React Wrapper
   - 전체 데이터 자동 로드 (3000+건)
   - 고정 뷰포트 (브라우저 스크롤 차단, Canvas 내부만 스크롤)
   - 체크박스 + 전체선택
   - 메일 모달
   - 진행단계 드롭다운
   - 발송상태 태그 토글
   - 사진 붙여넣기 + 업로드 + 줌
   - 셀 서식 (굵게, 기울임, 글자색, 배경색, 글자크기)
   - 컬럼 필터 + 헤더 우클릭 메뉴
   ═══════════════════════════════════════════════════════ */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { API_URL } from '@/lib/api'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { GridEngine } from './engine/GridEngine'
import { PrefsManager } from './engine/PrefsManager'
import { HistoryManager } from './engine/HistoryManager'
import MailModal from './MailModal'
import type { ColDef, DataRow, TabKey, CategoryKey, GridCallbacks, CellStyle } from './engine/types'
import { defaultCols, STAGES, TABS, MTAGS } from './engine/types'

/* ── Types ── */
interface DataStore { active: DataRow[]; past: DataRow[]; blacklist: DataRow[] }
type EditOverride = Partial<Pick<DataRow, 'stage' | 'mailStatus' | 'proposal' | 'notice' | 'applied' | 'history' | 'reference' | 'photoUrl' | 'photoSize' | 'category'>>
interface CtxMenu { x: number; y: number; rowIdx: number; row: DataRow }
interface FilterPopup { colKey: string; x: number; y: number }
interface HeaderMenu { colKey: string; x: number; y: number }

const API = API_URL
const PAGE_SIZE = 150

const PALETTE = ['#000', '#fff', '#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#ec4899', '#6b7280', '#fef9c3', '#dbeafe']

/* ── DB → DataRow mapping ── */
function mapRow(c: Record<string, unknown>, idx: number, edits: Record<string, EditOverride>): DataRow {
  const cid = String(c.candidate_id ?? c.id ?? '')
  const ov = edits[cid] || {}
  const cat: CategoryKey = String(c.status) === 'Active' ? 'active' : 'past'
  const tattoo = [c.tattoo, c.piercings].filter(Boolean).join('/')
  const ts = String(c.created_at ?? '').slice(0, 10).replace(/-/g, '.').slice(2)
  const isWebForm = String(c.source) === 'web_form'
  return {
    id: idx + 1, _cid: cid,
    category: (ov.category as string) ?? cat,
    stage: (ov.stage as string) ?? 'none',
    mailStatus: (ov.mailStatus as string) ?? '',
    photoUrl: (() => {
      const raw = String(c.photo_url ?? ov.photoUrl ?? '')
      if (!raw) return ''
      return raw.startsWith('http') ? raw : `${API}${raw}`
    })(),
    photoSize: Number(ov.photoSize ?? 50),
    email: String(c.email ?? ''), name: String(c.full_name ?? ''),
    mgtNum: cid.slice(-4), arc: String(c.arc_holders ?? ''),
    nationality: String(c.nationality ?? ''), background: String(c.ancestry ?? ''),
    age: String(c.dob ?? ''), gender: String(c.gender ?? ''),
    currentLoc: String(c.current_location ?? ''), startDate: String(c.start_date ?? ''),
    university: String(c.target ?? ''), prefRegion: String(c.area_prefs ?? ''),
    reference: (ov.reference as string) ?? String(c.reference ?? ''),
    totalExp: String(c.experience ?? ''), notice: (ov.notice as string) ?? '',
    preference: String(c.preferences ?? ''),
    applied: (ov.applied as string) ?? String(c.job_prefs ?? ''),
    proposal: (ov.proposal as string) ?? '', mailAction: '',
    curSalary: String(c.current_salary ?? ''), hopeSalary: String(c.desired_salary ?? ''),
    interviewCol: String(c.interview_time ?? ''), degree: String(c.education_level ?? ''),
    major: String(c.major ?? ''), cert: String(c.certification ?? ''),
    docs: String(c.doc_status ?? c.documents ?? ''), health: String(c.health_info ?? ''),
    tattooPiercing: tattoo, family: String(c.dependents ?? ''),
    married: String(c.married ?? ''), housing: String(c.housing ?? c.housing_type ?? ''),
    religion: String(c.religion ?? ''), e2visa: String(c.e_visa ?? c.visa_type ?? ''),
    kakao: String(c.kakaotalk ?? ''), phone: String(c.mobile_phone ?? ''),
    crimCheck: String(c.criminal_record_check ?? c.criminal_record ?? ''),
    domesticCrim: String(c.korean_criminal_record ?? ''),
    infoProvide: String(c.consent ?? ''), verified: String(c.fact_check ?? ''),
    source: isWebForm ? '\u2605NEW' : String(c.how_to ?? c.source ?? ''),
    timestamp: ts, hired: String(c.placed_company ?? ''),
    wage: String(c.placed_salary ?? ''), moveIn: String(c.start_month ?? ''),
    housingCost: String(c.housing_detail ?? ''), introFee: String(c.referral_fee ?? ''),
    process: String(c.process_date ?? ''),
    history: (ov.history as string) ?? String(c.past_placement ?? ''),
  }
}

/* ═══════════════════════════════════════
   Component
   ═══════════════════════════════════════ */
export default function BridgeCanvasSheet() {
  const { headers: authHeaders, adminKey } = useAdminAuth()

  const [data, setData] = useState<DataStore>({ active: [], past: [], blacklist: [] })
  const [dbAll, setDbAll] = useState<DataRow[]>([])
  const [dbTotal, setDbTotal] = useState(0)
  const [loaded, setLoaded] = useState(0)
  const [tab, setTab] = useState<TabKey>('active')
  const [cols, setCols] = useState<ColDef[]>(() => defaultCols())
  const [frozenCols, setFrozenCols] = useState(3)
  const [rowHeight, setRowHeight] = useState(36)
  const [q, setQ] = useState('')
  const [sortKey, setSortKey] = useState('')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [ctx, setCtx] = useState<CtxMenu | null>(null)
  const [loading, setLoading] = useState(false)
  const [lastSync, setLastSync] = useState('')
  const [newCount, setNewCount] = useState(0)
  const [ready, setReady] = useState(false)
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set())

  // Mail modal
  const [mailOpen, setMailOpen] = useState(false)
  const [mailRecipients, setMailRecipients] = useState<DataRow[]>([])

  // Filter popup
  const [filterPopup, setFilterPopup] = useState<FilterPopup | null>(null)
  const [filters, setFilters] = useState<Record<string, Set<string>>>({})

  // Header context menu
  const [headerMenu, setHeaderMenu] = useState<HeaderMenu | null>(null)

  // Formatting toolbar state
  const [showStyleBar, setShowStyleBar] = useState(true)
  const [colorPicker, setColorPicker] = useState<'text' | 'bg' | null>(null)

  // Per-row custom heights
  const [rowHeights, setRowHeights] = useState<Record<string, number>>({})

  const containerRef = useRef<HTMLDivElement>(null)
  const engineRef = useRef<GridEngine | null>(null)
  const prefsRef = useRef(new PrefsManager())
  const historyRef = useRef(new HistoryManager<{ data: DataStore; dbAll: DataRow[] }>(20))
  const editsRef = useRef<Record<string, EditOverride>>({})
  const photoRef = useRef<HTMLInputElement>(null)
  const photoTargetRef = useRef<number>(-1)

  /* ── Refs for stable callbacks ── */
  const dbAllRef = useRef(dbAll)
  const dataRef = useRef(data)
  const displayRowsRef = useRef<DataRow[]>([])
  const colsRef = useRef(cols)
  const hdrsRef = useRef(() => authHeaders())
  useEffect(() => { dbAllRef.current = dbAll }, [dbAll])
  useEffect(() => { dataRef.current = data }, [data])
  useEffect(() => { colsRef.current = cols }, [cols])
  useEffect(() => { hdrsRef.current = () => authHeaders() }, [authHeaders])

  /* ── Prefs restore ── */
  useEffect(() => {
    const pm = prefsRef.current
    const { cols: restored, frozenCols: fc } = pm.load(defaultCols())
    setCols(restored)
    setFrozenCols(fc)
    editsRef.current = pm.loadEdits() as Record<string, EditOverride>
    const savedData = pm.loadTabData<DataStore>()
    if (savedData && (savedData.active?.length || savedData.past?.length || savedData.blacklist?.length)) {
      setData(savedData)
    }
    setRowHeights(pm.loadRowHeights())
    setReady(true)
  }, [])

  useEffect(() => { if (ready) prefsRef.current.save(cols, frozenCols) }, [cols, frozenCols, ready])
  useEffect(() => { if (ready) prefsRef.current.saveTabData(data) }, [data, ready])

  /* ── Data fetching: AUTO-LOAD ALL ── */
  const loadAllData = useCallback(async () => {
    setLoading(true)
    let offset = 0
    const edits = editsRef.current
    const hdrs = hdrsRef.current
    const allRows: DataRow[] = []

    while (true) {
      try {
        const res = await fetch(
          `${API}/api/admin/candidates?limit=${PAGE_SIZE}&offset=${offset}`,
          { headers: hdrs() },
        )
        if (!res.ok) break
        const json = await res.json()
        const raw: Record<string, unknown>[] = json.data?.candidates ?? []
        const total: number = json.data?.total ?? 0
        setDbTotal(total)

        const newRows = raw.map((c, i) => mapRow(c, offset + i, edits))
        allRows.push(...newRows)
        offset += raw.length
        setLoaded(allRows.length)
        setDbAll([...allRows])

        if (offset === 0) {
          const nc = raw.filter(r => String(r.source ?? r.how_to ?? '') === 'web_form').length
          setNewCount(nc)
        }
        if (raw.length < PAGE_SIZE || offset >= total) break
      } catch { break }
    }
    setLoading(false)
    setLastSync(new Date().toLocaleTimeString())
  }, [])

  useEffect(() => {
    if (ready) loadAllData()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready])

  useEffect(() => {
    const iv = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/admin/candidates?status=Active&limit=50`, { headers: hdrsRef.current() })
        if (!res.ok) return
        const json = await res.json()
        const rows: Record<string, unknown>[] = json.data?.candidates ?? []
        setNewCount(rows.filter(r => String(r.source ?? r.how_to ?? '') === 'web_form').length)
      } catch { /* ignore */ }
    }, 60_000)
    return () => clearInterval(iv)
  }, [])

  /* ── Filtered + sorted rows ── */
  const displayRows = useMemo(() => {
    let rows: DataRow[]
    if (tab === 'all') {
      rows = dbAll
    } else {
      const manual = data[tab] || []
      const fromDb = dbAll.filter(r => r.category === tab)
      const manualIds = new Set(manual.map(r => r._cid))
      rows = [...manual, ...fromDb.filter(r => !manualIds.has(r._cid))]
    }
    // Apply filters
    for (const [colKey, vals] of Object.entries(filters)) {
      if (vals.size > 0) {
        rows = rows.filter(r => vals.has(String(r[colKey] ?? '')))
      }
    }
    if (q) {
      const lq = q.toLowerCase()
      rows = rows.filter(r => Object.values(r).some(v => v != null && String(v).toLowerCase().includes(lq)))
    }
    if (sortKey) {
      rows = [...rows].sort((a, b) => {
        const cmp = String(a[sortKey] ?? '').localeCompare(String(b[sortKey] ?? ''), 'ko', { numeric: true })
        return sortDir === 'asc' ? cmp : -cmp
      })
    }
    return rows
  }, [tab, data, dbAll, q, sortKey, sortDir, filters])

  useEffect(() => { displayRowsRef.current = displayRows }, [displayRows])

  /* ── Undo/Redo ── */
  const pushHistory = useCallback(() => {
    historyRef.current.push({
      data: JSON.parse(JSON.stringify(dataRef.current)),
      dbAll: JSON.parse(JSON.stringify(dbAllRef.current)),
    })
  }, [])

  const undo = useCallback(() => {
    const prev = historyRef.current.undo({ data: dataRef.current, dbAll: dbAllRef.current })
    if (prev) { setData(prev.data); setDbAll(prev.dbAll) }
  }, [])

  const redo = useCallback(() => {
    const next = historyRef.current.redo({ data: dataRef.current, dbAll: dbAllRef.current })
    if (next) { setData(next.data); setDbAll(next.dbAll) }
  }, [])

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) { e.preventDefault(); undo() }
      if ((e.ctrlKey || e.metaKey) && e.key === 'y') { e.preventDefault(); redo() }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'Z') { e.preventDefault(); redo() }
    }
    document.addEventListener('keydown', h)
    return () => document.removeEventListener('keydown', h)
  }, [undo, redo])

  /* ── Clipboard paste (image) ── */
  useEffect(() => {
    const h = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items
      if (!items) return
      for (const item of Array.from(items)) {
        if (item.type.startsWith('image/')) {
          e.preventDefault()
          const blob = item.getAsFile()
          if (!blob) return
          const targetIdx = [...selectedRows][0]
          if (targetIdx === undefined) return
          const targetRow = displayRowsRef.current[targetIdx]
          if (!targetRow) return
          const cid = String(targetRow._cid ?? '')

          // Try server upload first
          const fd = new FormData()
          fd.append('file', blob)
          fetch(`${API}/api/admin/upload-image`, {
            method: 'POST', headers: hdrsRef.current(), body: fd,
          }).then(r => r.ok ? r.json() : null).then(j => {
            const url: string = j?.data?.url ?? ''
            if (url) {
              const fullUrl = url.startsWith('http') ? url : `${API}${url}`
              pushHistory()
              setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, photoUrl: fullUrl } : r))
              if (cid) {
                const edits = editsRef.current
                edits[cid] = { ...(edits[cid] || {}), photoUrl: fullUrl } as EditOverride
                prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
              }
            }
          }).catch(() => {
            // base64 fallback
            const rd = new FileReader()
            rd.onload = ev2 => {
              pushHistory()
              const dataUrl = ev2.target?.result as string
              setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, photoUrl: dataUrl } : r))
            }
            rd.readAsDataURL(blob)
          })
          break
        }
      }
    }
    document.addEventListener('paste', h)
    return () => document.removeEventListener('paste', h)
  }, [selectedRows, pushHistory])

  /* ── Server save ── */
  const saveToServer = useCallback(async (cid: string, field: string, value: string) => {
    try {
      await fetch(`${API}/api/admin/candidates/${encodeURIComponent(cid)}`, {
        method: 'PATCH',
        headers: { ...hdrsRef.current(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ [field]: value }),
      })
    } catch { /* offline */ }
  }, [])

  /* ── Photo upload handler ── */
  const handlePhotoUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const rowIdx = photoTargetRef.current
    if (rowIdx < 0) return
    const row = displayRowsRef.current[rowIdx]
    if (!row) return
    const cid = String(row._cid ?? '')

    const fd = new FormData()
    fd.append('file', file)
    fetch(`${API}/api/admin/upload-image`, {
      method: 'POST', headers: hdrsRef.current(), body: fd,
    }).then(r => r.ok ? r.json() : null).then(async j => {
      const url: string = j?.data?.url ?? ''
      const fullUrl = url.startsWith('http') ? url : `${API}${url}`
      pushHistory()
      setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, photoUrl: fullUrl } : r))
      if (cid && url) {
        await fetch(`${API}/api/admin/candidates/${cid}`, {
          method: 'PATCH',
          headers: { ...hdrsRef.current(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ photo_url: url }),
        })
        const edits = editsRef.current
        edits[cid] = { ...(edits[cid] || {}), photoUrl: fullUrl } as EditOverride
        prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
      }
    }).catch(() => {
      const rd = new FileReader()
      rd.onload = ev2 => {
        pushHistory()
        setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, photoUrl: ev2.target?.result as string } : r))
      }
      rd.readAsDataURL(file)
    })
    e.target.value = ''
  }, [pushHistory])

  /* ── Mail modal ── */
  const openMailModal = useCallback((rows: DataRow[]) => {
    setMailRecipients(rows)
    setMailOpen(true)
  }, [])

  const handleMailSend = useCallback((subject: string, body: string, _files: File[], recipients: DataRow[]) => {
    // TODO: integrate with real email API
    alert(`발송: ${recipients.map(r => r.email).join(', ')}\n${subject}`)
  }, [])

  /* ── Style apply helper ── */
  const applyStyleToSelection = useCallback((style: CellStyle) => {
    const engine = engineRef.current
    if (!engine) return
    const rows = displayRowsRef.current
    const visCols = engine.getVisibleCols()
    const ac = engine.selection.getActiveCell()
    if (!ac) return
    const selectedRowSet = engine.selection.getSelectedRows()
    const colKey = visCols[ac.col]?.key
    if (!colKey) return

    // Apply to all selected rows at the active column
    for (const ri of selectedRowSet) {
      const row = rows[ri]
      if (row) {
        const cid = String(row._cid ?? '')
        if (cid) engine.styleManager.setStyle(cid, colKey, style)
      }
    }
    engine.refresh()
  }, [])

  /* ── Stable GridEngine callbacks ── */
  const stableCallbacks = useMemo<GridCallbacks>(() => ({
    onCellChange: (rowIdx: number, colKey: string, value: string) => {
      pushHistory()
      const row = displayRowsRef.current[rowIdx]
      if (!row) return
      const cid = String(row._cid ?? '')
      setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, [colKey]: value } : r))
      setData(prev => {
        const u = { ...prev }
        for (const k of ['active', 'past', 'blacklist'] as CategoryKey[])
          u[k] = prev[k].map(r => r._cid === cid ? { ...r, [colKey]: value } : r)
        return u
      })
      if (cid) {
        const edits = editsRef.current
        edits[cid] = { ...(edits[cid] || {}), [colKey]: value } as EditOverride
        prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
        const fieldMap: Record<string, string> = {
          reference: 'reference', proposal: 'proposal', notice: 'notice',
          applied: 'job_prefs', history: 'past_placement', housing: 'housing',
          introFee: 'referral_fee', process: 'process_date',
        }
        const dbField = fieldMap[colKey]
        if (dbField) saveToServer(cid, dbField, value)
      }
    },
    onCellClick: () => {},
    onSelectionChange: (rows: Set<number>) => {
      setSelectedRows(new Set(rows))
    },
    onContextMenu: (e: MouseEvent, rowIdx: number, row: DataRow) => {
      setCtx({ x: e.clientX, y: e.clientY, rowIdx, row })
    },
    onSort: (colKey: string) => {
      setSortKey(prev => {
        if (prev === colKey) { setSortDir(d => d === 'asc' ? 'desc' : 'asc'); return colKey }
        setSortDir('asc'); return colKey
      })
    },
    onColumnResize: (colKey: string, width: number) => {
      setCols(prev => prev.map(c => c.key === colKey ? { ...c, w: width } : c))
    },
    onRequestMore: () => {},
    onPhotoClick: () => {},
    onMailClick: (_ri: number, row: DataRow) => {
      openMailModal([row])
    },
    onStageChange: (rowIdx: number, stage: string) => {
      pushHistory()
      const row = displayRowsRef.current[rowIdx]
      if (!row) return
      const cid = String(row._cid ?? '')
      setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, stage } : r))
      setData(prev => {
        const u = { ...prev }
        for (const k of ['active', 'past', 'blacklist'] as CategoryKey[])
          u[k] = prev[k].map(r => r._cid === cid ? { ...r, stage } : r)
        return u
      })
      if (cid) {
        const edits = editsRef.current
        edits[cid] = { ...(edits[cid] || {}), stage } as EditOverride
        prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
      }
    },
    onTagToggle: (rowIdx: number, tagKey: string) => {
      pushHistory()
      const row = displayRowsRef.current[rowIdx]
      if (!row) return
      const cid = String(row._cid ?? '')
      const tags = String(row.mailStatus || '').split(',').filter(Boolean)
      const ms = (tags.includes(tagKey) ? tags.filter(t => t !== tagKey) : [...tags, tagKey]).join(',')
      setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, mailStatus: ms } : r))
      setData(prev => {
        const u = { ...prev }
        for (const k of ['active', 'past', 'blacklist'] as CategoryKey[])
          u[k] = prev[k].map(r => r._cid === cid ? { ...r, mailStatus: ms } : r)
        return u
      })
      if (cid) {
        const edits = editsRef.current
        edits[cid] = { ...(edits[cid] || {}), mailStatus: ms } as EditOverride
        prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
      }
    },
    onPhotoUpload: (rowIdx: number) => {
      photoTargetRef.current = rowIdx
      photoRef.current?.click()
    },
    onPhotoWheel: (rowIdx: number, delta: number) => {
      const row = displayRowsRef.current[rowIdx]
      if (!row) return
      const cid = String(row._cid ?? '')
      const newSize = Math.max(30, Math.min(120, (Number(row.photoSize) || 50) + delta))
      setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, photoSize: newSize } : r))
      if (cid) {
        const edits = editsRef.current
        edits[cid] = { ...(edits[cid] || {}), photoSize: newSize } as EditOverride
        prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
      }
    },
    onHeaderCheckToggle: () => {
      const engine = engineRef.current
      if (!engine) return
      const rows = displayRowsRef.current
      if (engine.selection.isAllSelected(rows.length)) {
        engine.selection.clearSelection()
      } else {
        engine.selection.selectAll(rows.length)
      }
      setSelectedRows(engine.selection.getSelectedRows())
    },
    onAddRow: () => {
      // Will be called from toolbar
    },
    onFilterClick: (colKey: string, x: number, y: number) => {
      setFilterPopup(prev => prev?.colKey === colKey ? null : { colKey, x, y })
    },
    onHeaderContextMenu: (e: MouseEvent, colKey: string) => {
      setHeaderMenu({ colKey, x: e.clientX, y: e.clientY })
    },
    onRowHeightChange: (cid: string, height: number) => {
      setRowHeights(prev => {
        const next = { ...prev, [cid]: height }
        prefsRef.current.saveRowHeights(next)
        return next
      })
    },
  }), [pushHistory, saveToServer, openMailModal])

  /* ── Engine init (once) ── */
  useEffect(() => {
    if (!containerRef.current || !ready) return
    const engine = new GridEngine(containerRef.current, stableCallbacks)
    engine.setHeaderGetter(() => hdrsRef.current())
    engineRef.current = engine
    return () => { engine.destroy(); engineRef.current = null }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready])

  /* ── Sync data/cols/sort/rowHeight to engine ── */
  useEffect(() => {
    const e = engineRef.current
    if (!e) return
    e.setCols(cols)
    e.setData(displayRows)
    e.setFrozenCols(frozenCols)
    e.setSort(sortKey, sortDir)
    e.setRowHeight(rowHeight)
    e.setRowHeights(rowHeights)
  }, [displayRows, cols, frozenCols, sortKey, sortDir, rowHeight, rowHeights])

  /* ── Context menu ── */
  const ctxAction = useCallback((action: string) => {
    if (!ctx) return
    const { row } = ctx
    const cid = String(row._cid ?? '')
    pushHistory()
    switch (action) {
      case 'to_active': case 'to_past': case 'to_blacklist': {
        const newCat = action.replace('to_', '') as CategoryKey
        setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, category: newCat } : r))
        setData(prev => {
          const u: DataStore = { active: [], past: [], blacklist: [] }
          for (const k of ['active', 'past', 'blacklist'] as CategoryKey[])
            u[k] = prev[k].filter(r => r._cid !== cid)
          u[newCat] = [...u[newCat], { ...row, category: newCat }]
          return u
        })
        const edits = editsRef.current
        edits[cid] = { ...(edits[cid] || {}), category: newCat } as EditOverride
        prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
        break
      }
      case 'copy_email':
        navigator.clipboard.writeText(String(row.email ?? '')).catch(() => {})
        break
      case 'copy_row': {
        const vc = colsRef.current.filter(c => c.v !== false)
        navigator.clipboard.writeText(vc.map(c => String(row[c.key] ?? '')).join('\t')).catch(() => {})
        break
      }
      case 'mail':
        openMailModal([row])
        break
      case 'add_row': {
        const newId = Math.max(...dbAllRef.current.map(r => r.id), 0) + 1
        const tt: CategoryKey = tab === 'all' ? 'active' : tab as CategoryKey
        const newRow: DataRow = {
          id: newId, _cid: '', category: tt, stage: 'none', mailStatus: '',
          photoUrl: '', photoSize: 50,
        }
        defaultCols().forEach(c => {
          if (!['rowNum', 'stage', 'mailStatus', 'photo'].includes(c.key) && !(c.key in newRow)) {
            (newRow as Record<string, unknown>)[c.key] = ''
          }
        })
        setDbAll(prev => {
          const idx = prev.findIndex(r => r._cid === cid)
          if (idx >= 0) {
            const arr = [...prev]
            arr.splice(idx + 1, 0, newRow)
            return arr
          }
          return [...prev, newRow]
        })
        break
      }
    }
    setCtx(null)
  }, [ctx, pushHistory, tab, openMailModal])

  /* ── Add new row ── */
  const addNewRow = useCallback(() => {
    pushHistory()
    const newId = Math.max(...dbAllRef.current.map(r => r.id), 0) + 1
    const tt: CategoryKey = tab === 'all' ? 'active' : tab as CategoryKey
    const newRow: DataRow = {
      id: newId, _cid: '', category: tt, stage: 'none', mailStatus: '',
      photoUrl: '', photoSize: 50,
    }
    defaultCols().forEach(c => {
      if (!['rowNum', 'stage', 'mailStatus', 'photo'].includes(c.key) && !(c.key in newRow)) {
        (newRow as Record<string, unknown>)[c.key] = ''
      }
    })
    setDbAll(prev => [...prev, newRow])
  }, [pushHistory, tab])

  /* ── CSV Export ── */
  const exportCsv = useCallback(() => {
    const vc = cols.filter(c => c.v !== false)
    const header = vc.map(c => c.label).join(',')
    const body = displayRows.map(r => vc.map(c => `"${String(r[c.key] ?? '').replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob(['\uFEFF' + header + '\n' + body], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
    a.download = `bridge_${tab}_${new Date().toISOString().slice(0, 10)}.csv`; a.click()
  }, [cols, displayRows, tab])

  /* ── Full reload ── */
  const fullReload = useCallback(() => { setDbAll([]); setLoaded(0); loadAllData() }, [loadAllData])

  /* ── Close popups on outside click ── */
  useEffect(() => {
    if (!ctx && !filterPopup && !headerMenu) return
    const h = () => { setCtx(null); setFilterPopup(null); setHeaderMenu(null); setColorPicker(null) }
    document.addEventListener('click', h)
    return () => document.removeEventListener('click', h)
  }, [ctx, filterPopup, headerMenu])

  /* ── Tab counts ── */
  const tabCounts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const t of TABS) {
      if (t.key === 'all') c[t.key] = dbAll.length
      else c[t.key] = dbAll.filter(r => r.category === t.key).length + (data[t.key]?.length ?? 0)
    }
    return c
  }, [dbAll, data])

  /* ── Filter unique values ── */
  const getFilterOptions = useCallback((colKey: string): string[] => {
    const vals = new Set<string>()
    displayRows.forEach(r => {
      const v = String(r[colKey] ?? '')
      if (v) vals.add(v)
    })
    return [...vals].sort()
  }, [displayRows])

  /* ── Column visibility toggle ── */
  const toggleColVisibility = useCallback((colKey: string) => {
    setCols(prev => prev.map(c => c.key === colKey ? { ...c, v: false } : c))
    setHeaderMenu(null)
  }, [])

  const showAllCols = useCallback(() => {
    setCols(prev => prev.map(c => ({ ...c, v: true })))
  }, [])

  if (!adminKey) {
    return <div style={{ padding: 40, textAlign: 'center', color: '#64748b' }}>관리자 인증이 필요합니다.</div>
  }

  const hiddenCount = cols.filter(c => !c.v).length

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', overflow: 'hidden',
      background: '#fff',
    }}>
      {/* Hidden file input for photo upload */}
      <input ref={photoRef} type="file" accept="image/*" onChange={handlePhotoUpload} style={{ display: 'none' }} />

      {/* ── Toolbar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px',
        background: '#fff', borderBottom: '1.5px solid #d1d5db', flexShrink: 0,
      }}>
        <div style={{ position: 'relative', flex: '0 0 220px' }}>
          <input
            type="text" placeholder="검색..."
            value={q} onChange={e => setQ(e.target.value)}
            style={{
              width: '100%', padding: '5px 10px 5px 28px',
              border: '1.5px solid #bbb', borderRadius: 4,
              fontSize: 13, fontWeight: 600, color: '#111', outline: 'none',
            }}
          />
          <span style={{ position: 'absolute', left: 7, top: '50%', transform: 'translateY(-50%)', color: '#666', fontSize: 13 }}>
            \uD83D\uDD0D
          </span>
        </div>

        <span style={{ fontSize: 13, fontWeight: 700, color: '#111', marginLeft: 6 }}>
          {loading
            ? <span style={{ color: '#2563eb' }}>{loaded.toLocaleString()} / {dbTotal.toLocaleString()}건 로드 중...</span>
            : <span>{dbAll.length.toLocaleString()} / {dbTotal.toLocaleString()}건</span>
          }
        </span>
        {lastSync && <span style={{ fontSize: 11, fontWeight: 600, color: '#666' }}> \xB7 {lastSync}</span>}
        {newCount > 0 && <span style={{ fontSize: 13, fontWeight: 700, color: '#ef4444' }}> \xB7 신규 {newCount}</span>}

        <div style={{ flex: 1 }} />

        {/* Selection bar */}
        {selectedRows.size > 0 && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '3px 10px', background: '#dbeafe', borderRadius: 6,
          }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#1d4ed8' }}>
              선택 {selectedRows.size}명
            </span>
            <button
              onClick={() => {
                const rows = [...selectedRows].map(i => displayRowsRef.current[i]).filter(Boolean)
                if (rows.length) openMailModal(rows)
              }}
              style={{ ...tbBtn, background: '#2563eb', color: '#fff', borderColor: '#2563eb' }}
            >
              \u2709 메일 발송
            </button>
          </div>
        )}

        <button onClick={addNewRow} style={{ ...tbBtn, background: '#2563eb', color: '#fff', borderColor: '#2563eb' }}>
          \uD83D\uDC64+ 신규
        </button>
        <button onClick={fullReload} style={tbBtn} title="새로고침">\u21BB 새로고침</button>
        <button onClick={undo} style={tbBtn} title="실행취소 (Ctrl+Z)">\u2936 되돌리기</button>
        <button onClick={redo} style={tbBtn} title="다시실행 (Ctrl+Y)">\u293B 다시</button>
        <button onClick={exportCsv} style={tbBtn} title="CSV 내보내기">\uD83D\uDCCA CSV</button>
        <button onClick={() => setFrozenCols(p => p === 0 ? 3 : 0)} style={tbBtn} title="고정열 토글">
          {frozenCols > 0 ? '\uD83D\uDD12 고정' : '\uD83D\uDD13 해제'}
        </button>
        {hiddenCount > 0 && (
          <button onClick={showAllCols} style={{ ...tbBtn, borderColor: '#06b6d4', color: '#0e7490' }}>
            숨긴{hiddenCount}열 표시
          </button>
        )}

        <select
          value={rowHeight}
          onChange={e => setRowHeight(Number(e.target.value))}
          style={{ ...tbBtn, padding: '4px 6px', fontSize: 12 }}
        >
          <option value={28}>행 낮게</option>
          <option value={36}>행 보통</option>
          <option value={56}>행 높게</option>
          <option value={72}>행 사진</option>
        </select>

        <button onClick={() => setShowStyleBar(p => !p)} style={tbBtn} title="서식 도구바 토글">
          {showStyleBar ? '\uD83C\uDFA8 서식' : '\uD83C\uDFA8'}
        </button>
      </div>

      {/* ── Style Toolbar ── */}
      {showStyleBar && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '4px 12px',
          background: '#f8fafc', borderBottom: '1px solid #e2e8f0', flexShrink: 0,
          flexWrap: 'wrap',
        }}>
          <button
            onClick={() => applyStyleToSelection({ bold: true })}
            style={{ ...styleTbBtn, fontWeight: 900 }}
            title="굵게 (Ctrl+B)"
          >B</button>
          <button
            onClick={() => applyStyleToSelection({ italic: true })}
            style={{ ...styleTbBtn, fontStyle: 'italic' }}
            title="기울임 (Ctrl+I)"
          >I</button>

          <span style={{ width: 1, height: 20, background: '#d1d5db', margin: '0 4px' }} />

          <select
            onChange={e => applyStyleToSelection({ fontSize: Number(e.target.value) })}
            defaultValue=""
            style={{ fontSize: 12, padding: '3px 6px', border: '1px solid #d1d5db', borderRadius: 4 }}
          >
            <option value="" disabled>글자크기</option>
            {[10, 12, 13, 14, 16, 18, 20].map(s => (
              <option key={s} value={s}>{s}px</option>
            ))}
          </select>

          <span style={{ width: 1, height: 20, background: '#d1d5db', margin: '0 4px' }} />

          {/* Text color */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={e => { e.stopPropagation(); setColorPicker(p => p === 'text' ? null : 'text') }}
              style={{ ...styleTbBtn, color: '#ef4444' }}
              title="글자색"
            >A</button>
            {colorPicker === 'text' && (
              <div onClick={e => e.stopPropagation()} style={paletteStyle}>
                {PALETTE.map(c => (
                  <div
                    key={c}
                    onClick={() => { applyStyleToSelection({ color: c }); setColorPicker(null) }}
                    style={{ width: 22, height: 22, background: c, border: '1px solid #d1d5db', borderRadius: 3, cursor: 'pointer' }}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Bg color */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={e => { e.stopPropagation(); setColorPicker(p => p === 'bg' ? null : 'bg') }}
              style={{ ...styleTbBtn, background: '#fef9c3' }}
              title="배경색"
            >\u2B1B</button>
            {colorPicker === 'bg' && (
              <div onClick={e => e.stopPropagation()} style={paletteStyle}>
                {PALETTE.map(c => (
                  <div
                    key={c}
                    onClick={() => { applyStyleToSelection({ bgColor: c }); setColorPicker(null) }}
                    style={{ width: 22, height: 22, background: c, border: '1px solid #d1d5db', borderRadius: 3, cursor: 'pointer' }}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Tabs ── */}
      <div style={{
        display: 'flex', gap: 0, background: '#fff',
        borderBottom: '1.5px solid #d1d5db', flexShrink: 0, paddingLeft: 8,
      }}>
        {TABS.map(t => {
          const active = tab === t.key
          return (
            <button key={t.key} onClick={() => { setTab(t.key); setSelectedRows(new Set()); setFilters({}) }} style={{
              padding: '7px 16px', fontSize: 13, fontWeight: 700,
              color: active ? t.color : '#555',
              background: active ? t.bg : 'transparent',
              border: 'none', borderBottom: active ? `2px solid ${t.accent}` : '2px solid transparent',
              cursor: 'pointer',
            }}>
              {t.icon} {t.label}
              <span style={{
                marginLeft: 6, fontSize: 11, fontWeight: 700,
                background: active ? t.accent + '20' : '#eee',
                color: active ? t.accent : '#888',
                padding: '1px 6px', borderRadius: 10,
              }}>
                {tabCounts[t.key] ?? 0}
              </span>
            </button>
          )
        })}
        {loading && (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', paddingRight: 12 }}>
            <div style={{ flex: 1, height: 4, background: '#e2e8f0', borderRadius: 2 }}>
              <div style={{
                width: dbTotal > 0 ? `${(loaded / dbTotal) * 100}%` : '0%',
                height: '100%', background: '#3b82f6', borderRadius: 2, transition: 'width 0.3s',
              }} />
            </div>
          </div>
        )}
      </div>

      {/* ── Canvas Container (fills remaining space) ── */}
      <div
        ref={containerRef}
        style={{
          flex: 1,
          position: 'relative',
          overflow: 'hidden',
          minHeight: 0,
        }}
      />

      {/* ── Context Menu ── */}
      {ctx && (
        <div
          style={{
            position: 'fixed', left: ctx.x, top: ctx.y, zIndex: 100,
            background: '#fff', border: '1px solid #d1d5db', borderRadius: 6,
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)', padding: '4px 0', minWidth: 190,
          }}
          onClick={e => e.stopPropagation()}
        >
          <CtxItem label="\u2709 메일 발송" onClick={() => ctxAction('mail')} />
          <CtxItem label="\uD83D\uDCCB 행 복사" onClick={() => ctxAction('copy_row')} />
          <CtxItem label="\uD83D\uDCE7 이메일 복사" onClick={() => ctxAction('copy_email')} />
          <CtxItem label="+ 아래 행 추가" onClick={() => ctxAction('add_row')} />
          <div style={{ height: 1, background: '#e5e7eb', margin: '3px 0' }} />
          <CtxItem label="\uD83D\uDC64 구직활동중으로" onClick={() => ctxAction('to_active')} />
          <CtxItem label="\u2705 체결완료로" onClick={() => ctxAction('to_past')} />
          <CtxItem label="\u26D4 블랙리스트로" onClick={() => ctxAction('to_blacklist')} />
          <div style={{ height: 1, background: '#e5e7eb', margin: '3px 0' }} />
          {STAGES.filter(s => s.key !== 'none').map(s => (
            <CtxItem key={s.key} label={`\u2192 ${s.label}`} onClick={() => {
              const cid = String(ctx.row._cid ?? '')
              pushHistory()
              setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, stage: s.key } : r))
              const edits = editsRef.current
              edits[cid] = { ...(edits[cid] || {}), stage: s.key } as EditOverride
              prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
              setCtx(null)
            }} />
          ))}
        </div>
      )}

      {/* ── Filter Popup ── */}
      {filterPopup && (
        <div
          onClick={e => e.stopPropagation()}
          style={{
            position: 'fixed', left: filterPopup.x, top: filterPopup.y, zIndex: 100,
            background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8,
            boxShadow: '0 4px 20px rgba(0,0,0,0.12)', minWidth: 180, maxHeight: 280,
            overflow: 'auto', padding: 6,
          }}
        >
          <div style={{ padding: '6px 10px', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between' }}>
            <b style={{ fontSize: 13 }}>{cols.find(c => c.key === filterPopup.colKey)?.label}</b>
            {filters[filterPopup.colKey]?.size ? (
              <span
                onClick={() => setFilters(p => { const n = { ...p }; delete n[filterPopup.colKey]; return n })}
                style={{ fontSize: 12, color: '#2563eb', cursor: 'pointer' }}
              >초기화</span>
            ) : null}
          </div>
          {getFilterOptions(filterPopup.colKey).map(opt => (
            <label key={opt} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', cursor: 'pointer', fontSize: 13 }}>
              <input
                type="checkbox"
                checked={!!filters[filterPopup.colKey]?.has(opt)}
                onChange={() => {
                  setFilters(prev => {
                    const s = prev[filterPopup.colKey] ? new Set(prev[filterPopup.colKey]) : new Set<string>()
                    if (s.has(opt)) s.delete(opt); else s.add(opt)
                    const n = { ...prev }
                    if (s.size === 0) delete n[filterPopup.colKey]; else n[filterPopup.colKey] = s
                    return n
                  })
                }}
                style={{ width: 14, height: 14 }}
              />
              {opt}
            </label>
          ))}
        </div>
      )}

      {/* ── Header Context Menu ── */}
      {headerMenu && (
        <div
          onClick={e => e.stopPropagation()}
          style={{
            position: 'fixed', left: headerMenu.x, top: headerMenu.y, zIndex: 100,
            background: '#fff', border: '1px solid #d1d5db', borderRadius: 6,
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)', padding: '4px 0', minWidth: 170,
          }}
        >
          <CtxItem label="\uD83D\uDC41 컬럼 숨기기" onClick={() => toggleColVisibility(headerMenu.colKey)} />
          {hiddenCount > 0 && (
            <CtxItem label="\uD83D\uDC41 숨긴 열 모두 표시" onClick={() => { showAllCols(); setHeaderMenu(null) }} />
          )}
        </div>
      )}

      {/* ── Footer Legend ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '4px 12px',
        background: '#fff', borderTop: '1px solid #e2e8f0', fontSize: 11,
        fontWeight: 600, color: '#555', flexShrink: 0,
      }}>
        {STAGES.filter(s => s.key !== 'none').map(s => (
          <span key={s.key} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: s.color, border: '1px solid #d1d5db' }} />
            {s.label}
          </span>
        ))}
        <span style={{ marginLeft: 'auto' }}>
          {MTAGS.map(m => <span key={m.key} style={{ color: m.c, fontWeight: 700, marginLeft: 8 }}>{m.label}</span>)}
        </span>
      </div>

      {/* ── Mail Modal ── */}
      <MailModal
        open={mailOpen}
        recipients={mailRecipients}
        onClose={() => setMailOpen(false)}
        onSend={handleMailSend}
      />
    </div>
  )
}

/* ── Context menu item ── */
function CtxItem({ label, onClick }: { label: string; onClick: () => void }) {
  const [hover, setHover] = useState(false)
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{
        padding: '5px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
        background: hover ? '#f1f5f9' : 'transparent', color: '#111',
      }}
    >{label}</div>
  )
}

/* ── Style constants ── */
const tbBtn: React.CSSProperties = {
  padding: '4px 10px', border: '1.5px solid #bbb', borderRadius: 4,
  background: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 700,
  color: '#111', lineHeight: 1, letterSpacing: '-0.3px',
}

const styleTbBtn: React.CSSProperties = {
  padding: '3px 8px', border: '1px solid #d1d5db', borderRadius: 4,
  background: '#fff', cursor: 'pointer', fontSize: 14, fontWeight: 600,
  color: '#333', lineHeight: 1, minWidth: 28, textAlign: 'center',
}

const paletteStyle: React.CSSProperties = {
  position: 'absolute', top: '100%', left: 0, zIndex: 200,
  background: '#fff', border: '1px solid #d1d5db', borderRadius: 8,
  boxShadow: '0 4px 12px rgba(0,0,0,0.15)', padding: 8,
  display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 4,
  minWidth: 160,
}
