'use client'

/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet v4 — Google Sheets Style
   - 전체 데이터 자동 로드 (3000+건)
   - 고정 뷰포트 (Canvas 내부만 스크롤)
   - 행번호 클릭 선택 + 코너 전체선택
   - Google Sheets 스타일 툴바 (Undo/Redo/Zoom/Font/Size/B/I/S/Color/Align)
   - 메일 모달 + 진행단계 + 발송상태 태그
   - 사진 Ctrl+V 붙여넣기 + 업로드
   - 셀 서식 (굵게, 기울임, 글자색, 배경색, 글자크기, 정렬)
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
interface TagPopup { rowIdx: number; x: number; y: number }

const API = API_URL
const PAGE_SIZE = 150

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
    mgtNum: c.sheet_number != null ? String(c.sheet_number) : String(c.row_id ?? ''),
    arc: String(c.arc_holders ?? ''),
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
  const [zoomLevel, setZoomLevel] = useState(100)
  const [fontFamily, setFontFamily] = useState('system')
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
  const [tagPopup, setTagPopup] = useState<TagPopup | null>(null)

  // Text/Bg color pickers (Google Sheets style)
  const [showTextColor, setShowTextColor] = useState(false)
  const [showBgColor, setShowBgColor] = useState(false)

  // Memo area
  const [memo, setMemo] = useState('')
  const [memoStyle, setMemoStyle] = useState({ fontSize: 13, bold: false, color: '#111' })
  const [memoHeight, setMemoHeight] = useState(60)
  const memoTimer = useRef<ReturnType<typeof setTimeout>>(undefined)

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

    // 암호화 값 판별 (AES-256-GCM base64: 40자 이상 + base64 문자만)
    const isStaleEncrypted = (v: unknown): boolean =>
      typeof v === 'string' && v.length > 40 && /^[A-Za-z0-9+/]{38,}={0,2}$/.test(v)

    // editsRef: 암호화된 stale 값 제거
    const rawEdits = pm.loadEdits() as Record<string, EditOverride>
    for (const cid of Object.keys(rawEdits)) {
      const ov = rawEdits[cid] as Record<string, unknown>
      for (const k of Object.keys(ov)) {
        if (isStaleEncrypted(ov[k])) delete ov[k]
      }
    }
    editsRef.current = rawEdits

    // savedData: DataRow 내 암호화된 stale 값 빈 문자열로 교체
    const savedData = pm.loadTabData<DataStore>()
    if (savedData && (savedData.active?.length || savedData.past?.length || savedData.blacklist?.length)) {
      const cleanRows = (rows: DataRow[]): DataRow[] =>
        rows.map(r => {
          const cleaned: DataRow = { ...r }
          for (const k of Object.keys(r)) {
            if (isStaleEncrypted(r[k])) (cleaned as Record<string, unknown>)[k] = ''
          }
          return cleaned
        })
      setData({
        active: cleanRows(savedData.active || []),
        past: cleanRows(savedData.past || []),
        blacklist: cleanRows(savedData.blacklist || []),
      })
    }

    setRowHeights(pm.loadRowHeights())

    // Memo restore
    try {
      const savedMemo = localStorage.getItem('bridge_sheet_memo')
      if (savedMemo) {
        const mp = JSON.parse(savedMemo)
        if (mp.memo) setMemo(mp.memo)
        if (mp.style) setMemoStyle(mp.style)
      }
    } catch { /* ignore */ }

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
    if (dbAll.length === 0) {
      // 로딩 중: localStorage 캐시로 즉시 표시
      rows = tab === 'all'
        ? [...(data.active || []), ...(data.past || []), ...(data.blacklist || [])]
        : (data[tab] || [])
    } else {
      // 로드 완료: 항상 서버에서 받은 복호화된 최신 데이터 사용
      rows = tab === 'all' ? dbAll : dbAll.filter(r => r.category === tab)
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

  /* ── Clipboard paste (image) — 사진 칸 캡쳐 붙여넣기 ── */
  useEffect(() => {
    const h = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items
      if (!items) return
      for (const item of Array.from(items)) {
        if (item.type.startsWith('image/')) {
          e.preventDefault()
          const blob = item.getAsFile()
          if (!blob) return
          // active cell 우선, 없으면 첫 번째 선택 행
          const engine = engineRef.current
          const ac = engine?.selection.getActiveCell()
          const targetIdx = ac?.row ?? [...selectedRows][0]
          if (targetIdx === undefined || targetIdx < 0) return
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
    const selectedRowSet = engine.selection.getSelectedRows()

    if (ac) {
      // 셀/컬럼 선택 모드: ac.col 기준 컬럼에 색상 적용
      const colKey = visCols[ac.col]?.key
      if (!colKey) return
      // 전체 행 선택(열 헤더 클릭) → 전체 열 / 부분 선택 → 선택 행만
      const isAllRows = selectedRowSet.size >= rows.length && rows.length > 0
      const targetRows = isAllRows
        ? rows
        : [...selectedRowSet].map(ri => rows[ri]).filter((r): r is DataRow => Boolean(r))
      for (const row of targetRows) {
        const cid = String(row._cid ?? '')
        if (cid) engine.styleManager.setStyle(cid, colKey, style)
      }
    } else if (selectedRowSet.size > 0) {
      // 행 체크박스 선택 모드: 선택된 행의 모든 컬럼에 색상 적용 (Excel 행 색상 동작)
      const targetRows = [...selectedRowSet].map(ri => rows[ri]).filter((r): r is DataRow => Boolean(r))
      for (const row of targetRows) {
        const cid = String(row._cid ?? '')
        if (cid) {
          for (const col of visCols) {
            if (col.key !== 'rowNum' && col.key !== 'photo') {
              engine.styleManager.setStyle(cid, col.key, style)
            }
          }
        }
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
    onTagCellClick: (rowIdx: number, _row: DataRow, x: number, y: number) => {
      setTagPopup({ rowIdx, x, y })
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
    onRowHeightChange: () => {
      const engine = engineRef.current
      if (!engine) return
      const allHeights = engine.getRowHeightsMap()
      setRowHeights(allHeights)
      prefsRef.current.saveRowHeights(allHeights)
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

  /* ── Memo save ── */
  const saveMemo = useCallback((m: string, s: { fontSize: number; bold: boolean; color: string }) => {
    const data = { memo: m, style: s }
    localStorage.setItem('bridge_sheet_memo', JSON.stringify(data))
  }, [])

  /* ── StyleManager getAllIds ── */
  useEffect(() => {
    const engine = engineRef.current
    if (!engine) return
    engine.styleManager.setGetAllIds(() =>
      dbAllRef.current.map(r => String(r._cid ?? r.id))
    )
  }, [ready])

  /* ── Close popups on outside click ── */
  useEffect(() => {
    if (!ctx && !filterPopup && !headerMenu && !tagPopup) return
    const h = () => { setCtx(null); setFilterPopup(null); setHeaderMenu(null); setShowTextColor(false); setShowBgColor(false); setTagPopup(null) }
    document.addEventListener('click', h)
    return () => document.removeEventListener('click', h)
  }, [ctx, filterPopup, headerMenu, tagPopup])

  /* ── Tab counts ── */
  const tabCounts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const t of TABS) {
      if (t.key === 'all') {
        c[t.key] = dbAll.length || (data.active?.length || 0) + (data.past?.length || 0) + (data.blacklist?.length || 0)
      } else {
        c[t.key] = dbAll.length > 0
          ? dbAll.filter(r => r.category === t.key).length
          : (data[t.key]?.length ?? 0)
      }
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

      {/* ── Toolbar Row 1: actions ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px',
        background: '#fff', borderBottom: '1px solid #e2e8f0', flexShrink: 0,
      }}>
        <div style={{ position: 'relative', flex: '0 0 200px' }}>
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
            🔍
          </span>
        </div>

        <span style={{ fontSize: 13, fontWeight: 700, color: '#111' }}>
          {loading
            ? <span style={{ color: '#2563eb' }}>{loaded.toLocaleString()} / {dbTotal.toLocaleString()}건 로드 중...</span>
            : <span>{dbAll.length.toLocaleString()} / {dbTotal.toLocaleString()}건</span>
          }
        </span>
        {lastSync && <span style={{ fontSize: 11, fontWeight: 600, color: '#666' }}> · {lastSync}</span>}
        {newCount > 0 && <span style={{ fontSize: 13, fontWeight: 700, color: '#ef4444' }}> · 신규 {newCount}</span>}

        <div style={{ flex: 1 }} />

        {selectedRows.size > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '3px 10px', background: '#dbeafe', borderRadius: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#1d4ed8' }}>선택 {selectedRows.size}명</span>
            <button
              onClick={() => { const rows = [...selectedRows].map(i => displayRowsRef.current[i]).filter(Boolean); if (rows.length) openMailModal(rows) }}
              style={{ ...tbBtn, background: '#2563eb', color: '#fff', borderColor: '#2563eb' }}
            >✉ 메일</button>
          </div>
        )}

        <button onClick={() => setFrozenCols(p => p === 0 ? 3 : 0)} style={tbBtn}>{frozenCols > 0 ? '🔒 고정' : '🔓 해제'}</button>
        <button onClick={fullReload} style={tbBtn}>↻ DB동기화</button>
        <button onClick={exportCsv} style={tbBtn}>↓CSV</button>
        <button onClick={addNewRow} style={{ ...tbBtn, background: '#2563eb', color: '#fff', borderColor: '#2563eb' }}>+새후보자</button>
        {hiddenCount > 0 && (
          <button onClick={showAllCols} style={{ ...tbBtn, borderColor: '#06b6d4', color: '#0e7490' }}>숨긴{hiddenCount}열</button>
        )}
      </div>

      {/* ── Toolbar Row 2: Google Sheets formatting bar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 4, padding: '3px 12px',
        background: '#f8fafc', borderBottom: '1.5px solid #d1d5db', flexShrink: 0,
      }}>
        {/* Undo / Redo */}
        <button onClick={undo} style={fmtBtn} title="Ctrl+Z (실행취소)">↩</button>
        <button onClick={redo} style={fmtBtn} title="Ctrl+Y (다시실행)">↪</button>

        <span style={{ width: 1, height: 20, background: '#d1d5db', margin: '0 2px' }} />

        {/* Zoom */}
        <select
          value={zoomLevel}
          onChange={e => setZoomLevel(Number(e.target.value))}
          style={{ height: 26, fontSize: 12, border: '1px solid #ccc', borderRadius: 3, padding: '0 4px', width: 60 }}
          title="확대/축소"
        >
          {[50, 75, 90, 100, 110, 125, 150].map(n => <option key={n} value={n}>{n}%</option>)}
        </select>

        <span style={{ width: 1, height: 20, background: '#d1d5db', margin: '0 2px' }} />

        {/* Font family */}
        <select
          value={fontFamily}
          onChange={e => setFontFamily(e.target.value)}
          style={{ height: 26, fontSize: 12, border: '1px solid #ccc', borderRadius: 3, padding: '0 4px', width: 90 }}
          title="글꼴"
        >
          <option value="system">System UI</option>
          <option value="arial">Arial</option>
          <option value="nanum">나눔고딕</option>
          <option value="mono">Monospace</option>
        </select>

        {/* Font size */}
        <select
          onChange={e => applyStyleToSelection({ fontSize: Number(e.target.value) })}
          defaultValue=""
          style={{ height: 26, fontSize: 12, border: '1px solid #ccc', borderRadius: 3, padding: '0 4px', width: 52 }}
          title="글자 크기"
        >
          <option value="" disabled>크기</option>
          {[8, 9, 10, 11, 12, 14, 16, 18, 20, 24].map(n => <option key={n} value={n}>{n}</option>)}
        </select>

        <span style={{ width: 1, height: 20, background: '#d1d5db', margin: '0 2px' }} />

        {/* B / I / S */}
        <button onClick={() => applyStyleToSelection({ bold: true })} style={{ ...fmtBtn, fontWeight: 700 }} title="Bold (Ctrl+B)">B</button>
        <button onClick={() => applyStyleToSelection({ italic: true })} style={{ ...fmtBtn, fontStyle: 'italic' }} title="Italic (Ctrl+I)">I</button>
        <button onClick={() => applyStyleToSelection({ strikethrough: true })} style={{ ...fmtBtn, textDecoration: 'line-through' }} title="취소선">S</button>

        <span style={{ width: 1, height: 20, background: '#d1d5db', margin: '0 2px' }} />

        {/* Text color */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={e => { e.stopPropagation(); setShowTextColor(v => !v); setShowBgColor(false) }}
            style={{ ...fmtBtn, borderBottom: '3px solid #000', paddingBottom: 1 }}
            title="글자색"
          >A</button>
          {showTextColor && (
            <ColorPalette
              onSelect={c => { applyStyleToSelection({ color: c }); setShowTextColor(false) }}
              onReset={() => { applyStyleToSelection({ color: '#000000' }); setShowTextColor(false) }}
              onClose={() => setShowTextColor(false)}
            />
          )}
        </div>

        {/* Bg color */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={e => { e.stopPropagation(); setShowBgColor(v => !v); setShowTextColor(false) }}
            style={{ ...fmtBtn, borderBottom: '3px solid transparent', paddingBottom: 1 }}
            title="배경색"
          >🎨</button>
          {showBgColor && (
            <ColorPalette
              onSelect={c => { applyStyleToSelection({ bgColor: c }); setShowBgColor(false) }}
              onReset={() => { applyStyleToSelection({ bgColor: '' }); setShowBgColor(false) }}
              onClose={() => setShowBgColor(false)}
            />
          )}
        </div>

        <span style={{ width: 1, height: 20, background: '#d1d5db', margin: '0 2px' }} />

        {/* Alignment */}
        <button onClick={() => applyStyleToSelection({ align: 'left' })} style={fmtBtn} title="왼쪽 정렬">⬅</button>
        <button onClick={() => applyStyleToSelection({ align: 'center' })} style={fmtBtn} title="가운데 정렬">≡</button>
        <button onClick={() => applyStyleToSelection({ align: 'right' })} style={fmtBtn} title="오른쪽 정렬">➡</button>

        <span style={{ width: 1, height: 20, background: '#d1d5db', margin: '0 2px' }} />

        {/* Row height */}
        <select
          value={rowHeight}
          onChange={e => setRowHeight(Number(e.target.value))}
          style={{ height: 26, fontSize: 12, border: '1px solid #ccc', borderRadius: 3, padding: '0 4px' }}
          title="행 높이"
        >
          <option value={28}>낮게</option>
          <option value={40}>보통</option>
          <option value={56}>높게</option>
          <option value={72}>사진</option>
        </select>
      </div>

      {/* ── Memo Area ── */}
      <div style={{
        flexShrink: 0, background: '#FFFDE7',
        borderBottom: '2px solid #F9A825',
        display: 'flex', flexDirection: 'column',
        height: memoHeight, minHeight: 40, maxHeight: 200,
        position: 'relative',
      }}>
        <div style={{ display: 'flex', gap: 4, padding: '2px 8px', borderBottom: '1px solid #F9A825', alignItems: 'center' }}>
          <select
            value={memoStyle.fontSize}
            onChange={e => { const s = { ...memoStyle, fontSize: +e.target.value }; setMemoStyle(s); saveMemo(memo, s) }}
            style={{ fontSize: 11, padding: '0 2px', border: '1px solid #e0d78a', borderRadius: 3 }}
          >
            {[10, 11, 12, 13, 14, 16, 18].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
          <button
            onClick={() => { const s = { ...memoStyle, bold: !memoStyle.bold }; setMemoStyle(s); saveMemo(memo, s) }}
            style={{ fontWeight: memoStyle.bold ? 700 : 400, width: 22, height: 22, border: '1px solid #e0d78a', borderRadius: 3, background: memoStyle.bold ? '#fff3cd' : 'transparent', cursor: 'pointer', fontSize: 12 }}
          >B</button>
          <input
            type="color" value={memoStyle.color}
            onChange={e => { const s = { ...memoStyle, color: e.target.value }; setMemoStyle(s); saveMemo(memo, s) }}
            style={{ width: 22, height: 22, border: 'none', padding: 0, cursor: 'pointer' }}
            title="글자색"
          />
        </div>
        <textarea
          value={memo}
          onChange={e => { setMemo(e.target.value); saveMemo(e.target.value, memoStyle) }}
          placeholder="메모를 입력하세요..."
          style={{
            flex: 1, border: 'none', outline: 'none', resize: 'none',
            padding: '4px 8px', background: 'transparent',
            fontSize: memoStyle.fontSize, fontWeight: memoStyle.bold ? 700 : 400,
            color: memoStyle.color, fontFamily: 'system-ui, sans-serif',
          }}
        />
        <div
          onMouseDown={e => {
            const startY = e.clientY; const startH = memoHeight
            const onMove = (me: MouseEvent) => setMemoHeight(Math.max(40, Math.min(200, startH + (me.clientY - startY))))
            const onUp = () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
            window.addEventListener('mousemove', onMove)
            window.addEventListener('mouseup', onUp)
          }}
          style={{ height: 5, cursor: 'row-resize', background: '#F9A825', opacity: 0.4 }}
        />
      </div>

      {/* ── Canvas Container (fills remaining space) ── */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden', minHeight: 0 }}>
        <div
          ref={containerRef}
          style={{
            position: 'absolute', inset: 0,
            transformOrigin: 'top left',
            transform: zoomLevel !== 100 ? `scale(${zoomLevel / 100})` : undefined,
            width: zoomLevel !== 100 ? `${10000 / zoomLevel}%` : '100%',
            height: zoomLevel !== 100 ? `${10000 / zoomLevel}%` : '100%',
          }}
        />
      </div>

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
          <CtxItem label="✉ 메일 발송" onClick={() => ctxAction('mail')} />
          <CtxItem label="📋 행 복사" onClick={() => ctxAction('copy_row')} />
          <CtxItem label="📧 이메일 복사" onClick={() => ctxAction('copy_email')} />
          <CtxItem label="+ 아래 행 추가" onClick={() => ctxAction('add_row')} />
          <div style={{ height: 1, background: '#e5e7eb', margin: '3px 0' }} />
          <CtxItem label="👤 구직활동중으로" onClick={() => ctxAction('to_active')} />
          <CtxItem label="✅ 체결완료로" onClick={() => ctxAction('to_past')} />
          <CtxItem label="⛔ 블랙리스트로" onClick={() => ctxAction('to_blacklist')} />
          <div style={{ height: 1, background: '#e5e7eb', margin: '3px 0' }} />
          {STAGES.filter(s => s.key !== 'none').map(s => (
            <CtxItem key={s.key} label={`→ ${s.label}`} onClick={() => {
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
          <CtxItem label="👁 컬럼 숨기기" onClick={() => toggleColVisibility(headerMenu.colKey)} />
          {hiddenCount > 0 && (
            <CtxItem label="👁 숨긴 열 모두 표시" onClick={() => { showAllCols(); setHeaderMenu(null) }} />
          )}
        </div>
      )}

      {/* ── Tag Selection Popup ── */}
      {tagPopup && (() => {
        const popRow = displayRows[tagPopup.rowIdx]
        if (!popRow) return null
        const activeTags = String(popRow.mailStatus || '').split(',').filter(Boolean)
        return (
          <div
            onClick={e => e.stopPropagation()}
            style={{
              position: 'fixed', left: tagPopup.x, top: tagPopup.y, zIndex: 150,
              background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8,
              boxShadow: '0 4px 20px rgba(0,0,0,0.15)', minWidth: 200, maxHeight: 340,
              overflow: 'auto',
            }}
          >
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '6px 10px 6px 12px', borderBottom: '1px solid #f1f5f9',
            }}>
              <b style={{ fontSize: 13, color: '#111' }}>태그 · 역할 선택</b>
              <span
                onClick={() => setTagPopup(null)}
                style={{ fontSize: 16, cursor: 'pointer', color: '#64748b', lineHeight: 1, padding: '0 2px' }}
              >✕</span>
            </div>
            <div style={{ padding: '4px 0' }}>
              {MTAGS.map(mt => (
                <label key={mt.key} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '4px 12px', cursor: 'pointer', fontSize: 13,
                }}>
                  <input
                    type="checkbox"
                    checked={activeTags.includes(mt.key)}
                    onChange={() => {
                      const row = displayRowsRef.current[tagPopup.rowIdx]
                      if (!row) return
                      const cid = String(row._cid ?? '')
                      const tags = String(row.mailStatus || '').split(',').filter(Boolean)
                      const ms = (tags.includes(mt.key)
                        ? tags.filter(t => t !== mt.key)
                        : [...tags, mt.key]).join(',')
                      pushHistory()
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
                    }}
                    style={{ width: 14, height: 14, accentColor: mt.c }}
                  />
                  <span style={{ color: mt.c, fontWeight: 700 }}>{mt.label}</span>
                </label>
              ))}
            </div>
          </div>
        )
      })()}

      {/* ── Tabs (bottom) ── */}
      <div style={{
        display: 'flex', gap: 0, flexShrink: 0, paddingLeft: 4,
        borderTop: '1px solid #ccc', background: '#37474F',
      }}>
        {TABS.map(t => {
          const active = tab === t.key
          return (
            <button key={t.key} onClick={() => { setTab(t.key); setSelectedRows(new Set()); setFilters({}) }} style={{
              padding: '6px 16px', fontSize: 13, fontWeight: 400,
              color: active ? '#fff' : '#ccc',
              background: active ? t.bg : '#546E7A',
              border: 'none',
              borderBottom: active ? `2px solid ${t.accent}` : '2px solid transparent',
              cursor: 'pointer', transition: 'background 0.15s',
            }}>
              {t.icon} {t.label}
              <span style={{
                marginLeft: 6, fontSize: 11, fontWeight: 600,
                background: active ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.15)',
                color: active ? '#fff' : '#aaa',
                padding: '1px 6px', borderRadius: 10,
              }}>
                {tabCounts[t.key] ?? 0}
              </span>
            </button>
          )
        })}
        {loading && (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', paddingRight: 12, paddingLeft: 12 }}>
            <div style={{ flex: 1, height: 3, background: 'rgba(255,255,255,0.15)', borderRadius: 2 }}>
              <div style={{
                width: dbTotal > 0 ? `${(loaded / dbTotal) * 100}%` : '0%',
                height: '100%', background: '#64b5f6', borderRadius: 2, transition: 'width 0.3s',
              }} />
            </div>
          </div>
        )}
      </div>

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
        getHeaders={() => hdrsRef.current()}
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

/* ── Color Palette (Google Sheets style) ── */
const GPALETTE = [
  ['#000000','#434343','#666666','#999999','#b7b7b7','#cccccc','#d9d9d9','#efefef','#f3f3f3','#ffffff'],
  ['#ff0000','#ff9900','#ffff00','#00ff00','#00ffff','#4a86e8','#0000ff','#9900ff','#ff00ff','#980000'],
  ['#ea9999','#f9cb9c','#ffe599','#b6d7a8','#a2c4c9','#9fc5e8','#b4a7d6','#d5a6bd','#e6b8af','#f4cccc'],
  ['#e06666','#f6b26b','#ffd966','#93c47d','#76a5af','#6fa8dc','#8e7cc3','#c27ba0','#dd7e6b','#ea9999'],
  ['#cc0000','#e69138','#f1c232','#6aa84f','#45818e','#3d85c8','#674ea7','#a64d79','#b45f06','#990000'],
  ['#660000','#783f04','#7f6000','#274e13','#0c343d','#1c4587','#20124d','#4c1130','#351c75','#741b47'],
]

function ColorPalette({ onSelect, onReset, onClose }: {
  onSelect: (c: string) => void; onReset: () => void; onClose: () => void
}) {
  useEffect(() => {
    const handler = () => onClose()
    const t = setTimeout(() => document.addEventListener('click', handler), 0)
    return () => { clearTimeout(t); document.removeEventListener('click', handler) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return (
    <div onClick={e => e.stopPropagation()} style={{
      position: 'absolute', top: '100%', left: 0, zIndex: 2000,
      background: '#fff', border: '1px solid #ddd', borderRadius: 4,
      padding: 8, boxShadow: '0 4px 20px rgba(0,0,0,0.2)', width: 230,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        <span style={{ fontSize: 11, color: '#555' }}>재설정</span>
        <div onClick={onReset} title="색상 제거"
          style={{ width: 18, height: 18, cursor: 'pointer', border: '1px solid #ccc', borderRadius: 2,
          background: 'linear-gradient(135deg,#fff 45%,#f00 45%,#f00 55%,#fff 55%)' }} />
      </div>
      {GPALETTE.map((row, ri) => (
        <div key={ri} style={{ display: 'flex', gap: 2, marginBottom: 2 }}>
          {row.map(color => (
            <div key={color} onClick={() => onSelect(color)}
              style={{ width: 18, height: 18, background: color, cursor: 'pointer',
              border: '1px solid rgba(0,0,0,0.15)', borderRadius: 2, flexShrink: 0 }} />
          ))}
        </div>
      ))}
    </div>
  )
}

/* ── Style constants ── */
const tbBtn: React.CSSProperties = {
  padding: '4px 10px', border: '1.5px solid #bbb', borderRadius: 4,
  background: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 700,
  color: '#111', lineHeight: 1, letterSpacing: '-0.3px',
}

const fmtBtn: React.CSSProperties = {
  width: 26, height: 26, border: '1px solid #ccc', borderRadius: 3,
  background: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600,
  color: '#333', lineHeight: 1, textAlign: 'center', display: 'inline-flex',
  alignItems: 'center', justifyContent: 'center',
}
