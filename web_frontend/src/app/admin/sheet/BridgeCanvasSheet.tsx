'use client'

/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet — React Wrapper
   Data fetching, tabs, toolbar, context menu, mail modal
   Zero external dependencies — pure Canvas engine
   ═══════════════════════════════════════════════════════ */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { API_URL } from '@/lib/api'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { GridEngine } from './engine/GridEngine'
import { PrefsManager } from './engine/PrefsManager'
import { HistoryManager } from './engine/HistoryManager'
import type { ColDef, DataRow, TabKey, CategoryKey, GridCallbacks } from './engine/types'
import { defaultCols, STAGES, TABS, MTAGS } from './engine/types'

/* ── Types ── */
interface DataStore { active: DataRow[]; past: DataRow[]; blacklist: DataRow[] }
type EditOverride = Partial<Pick<DataRow, 'stage' | 'mailStatus' | 'proposal' | 'notice' | 'applied' | 'history' | 'reference' | 'photoUrl' | 'photoSize' | 'category'>>
interface CtxMenu { x: number; y: number; rowIdx: number; row: DataRow }

const API = API_URL
const PAGE_SIZE = 150

/* ── DB → DataRow mapping (matches existing logic) ── */
function mapRow(c: Record<string, unknown>, idx: number, edits: Record<string, EditOverride>): DataRow {
  const cid = String(c.candidate_id ?? c.id ?? '')
  const ov = edits[cid] || {}
  const cat: CategoryKey = String(c.status) === 'Active' ? 'active' : 'past'
  const tattoo = [c.tattoo, c.piercings].filter(Boolean).join('/')
  const ts = String(c.created_at ?? '').slice(0, 10).replace(/-/g, '.').slice(2)
  const isWebForm = String(c.source) === 'web_form'
  return {
    id: idx + 1,
    _cid: cid,
    category: (ov.category as string) ?? cat,
    stage: (ov.stage as string) ?? 'none',
    mailStatus: (ov.mailStatus as string) ?? '',
    photoUrl: (() => {
      const raw = String(c.photo_url ?? ov.photoUrl ?? '')
      if (!raw) return ''
      return raw.startsWith('http') ? raw : `${API}${raw}`
    })(),
    photoSize: Number(ov.photoSize ?? 50),
    email: String(c.email ?? ''),
    name: String(c.full_name ?? ''),
    mgtNum: cid.slice(-4),
    arc: String(c.arc_holders ?? ''),
    nationality: String(c.nationality ?? ''),
    background: String(c.ancestry ?? ''),
    age: String(c.dob ?? ''),
    gender: String(c.gender ?? ''),
    currentLoc: String(c.current_location ?? ''),
    startDate: String(c.start_date ?? ''),
    university: String(c.target ?? ''),
    prefRegion: String(c.area_prefs ?? ''),
    reference: (ov.reference as string) ?? String(c.reference ?? ''),
    totalExp: String(c.experience ?? ''),
    notice: (ov.notice as string) ?? '',
    preference: String(c.preferences ?? ''),
    applied: (ov.applied as string) ?? String(c.job_prefs ?? ''),
    proposal: (ov.proposal as string) ?? '',
    mailAction: '',
    curSalary: String(c.current_salary ?? ''),
    hopeSalary: String(c.desired_salary ?? ''),
    interviewCol: String(c.interview_time ?? ''),
    degree: String(c.education_level ?? ''),
    major: String(c.major ?? ''),
    cert: String(c.certification ?? ''),
    docs: String(c.doc_status ?? c.documents ?? ''),
    health: String(c.health_info ?? ''),
    tattooPiercing: tattoo,
    family: String(c.dependents ?? ''),
    married: String(c.married ?? ''),
    housing: String(c.housing ?? c.housing_type ?? ''),
    religion: String(c.religion ?? ''),
    e2visa: String(c.e_visa ?? c.visa_type ?? ''),
    kakao: String(c.kakaotalk ?? ''),
    phone: String(c.mobile_phone ?? ''),
    crimCheck: String(c.criminal_record_check ?? c.criminal_record ?? ''),
    domesticCrim: String(c.korean_criminal_record ?? ''),
    infoProvide: String(c.consent ?? ''),
    verified: String(c.fact_check ?? ''),
    source: isWebForm ? '★NEW' : String(c.how_to ?? c.source ?? ''),
    timestamp: ts,
    hired: String(c.placed_company ?? ''),
    wage: String(c.placed_salary ?? ''),
    moveIn: String(c.start_month ?? ''),
    housingCost: String(c.housing_detail ?? ''),
    introFee: String(c.referral_fee ?? ''),
    process: String(c.process_date ?? ''),
    history: (ov.history as string) ?? String(c.past_placement ?? ''),
  }
}

/* ── Component ── */
export default function BridgeCanvasSheet() {
  const { headers: authHeaders, adminKey } = useAdminAuth()

  /* ── State ── */
  const [data, setData] = useState<DataStore>({ active: [], past: [], blacklist: [] })
  const [dbAll, setDbAll] = useState<DataRow[]>([])
  const [dbTotal, setDbTotal] = useState(0)
  const [tab, setTab] = useState<TabKey>('active')
  const [cols, setCols] = useState<ColDef[]>(() => defaultCols())
  const [frozenCols, setFrozenCols] = useState(3)
  const [q, setQ] = useState('')
  const [sortKey, setSortKey] = useState('')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [ctx, setCtx] = useState<CtxMenu | null>(null)
  const [loading, setLoading] = useState(false)
  const [lastSync, setLastSync] = useState('')
  const [newCount, setNewCount] = useState(0)
  const [ready, setReady] = useState(false)

  /* ── Refs ── */
  const containerRef = useRef<HTMLDivElement>(null)
  const engineRef = useRef<GridEngine | null>(null)
  const prefsRef = useRef(new PrefsManager())
  const historyRef = useRef(new HistoryManager<{ data: DataStore; dbAll: DataRow[] }>(20))
  const dbFetchingRef = useRef(false)
  const dbOffsetRef = useRef(0)
  const allLoadedRef = useRef(false)
  const editsRef = useRef<Record<string, EditOverride>>({})

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
    setReady(true)
  }, [])

  /* ── Save prefs on change ── */
  useEffect(() => {
    if (!ready) return
    prefsRef.current.save(cols, frozenCols)
  }, [cols, frozenCols, ready])

  useEffect(() => {
    if (!ready) return
    prefsRef.current.saveTabData(data)
  }, [data, ready])

  /* ── Headers helper ── */
  const hdrs = useCallback(() => authHeaders(), [authHeaders])

  /* ── Data fetching ── */
  const loadMore = useCallback(async () => {
    if (dbFetchingRef.current || allLoadedRef.current) return
    dbFetchingRef.current = true
    setLoading(true)
    const offset = dbOffsetRef.current
    const edits = editsRef.current
    try {
      const res = await fetch(
        `${API}/api/admin/candidates?limit=${PAGE_SIZE}&offset=${offset}`,
        { headers: hdrs() },
      )
      if (!res.ok) return
      const json = await res.json()
      const raw: Record<string, unknown>[] = json.data?.candidates ?? []
      const total: number = json.data?.total ?? 0
      setDbTotal(total)
      const newRows = raw.map((c, i) => mapRow(c, offset + i, edits))
      setDbAll(prev => {
        const combined = [...prev, ...newRows]
        dbOffsetRef.current = combined.length
        return combined
      })
      if (raw.length < PAGE_SIZE) allLoadedRef.current = true
      if (offset === 0) {
        const nc = raw.filter(r => String(r.source ?? r.how_to ?? '') === 'web_form').length
        setNewCount(nc)
      }
      setLastSync(new Date().toLocaleTimeString())
    } catch { /* network error */ } finally {
      dbFetchingRef.current = false
      setLoading(false)
    }
  }, [hdrs])

  useEffect(() => {
    loadMore()
    const iv = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/admin/candidates?status=Active&limit=50`, { headers: hdrs() })
        if (!res.ok) return
        const json = await res.json()
        const rows: Record<string, unknown>[] = json.data?.candidates ?? []
        const nc = rows.filter(r => String(r.source ?? r.how_to ?? '') === 'web_form').length
        setNewCount(nc)
      } catch { /* ignore */ }
    }, 60_000)
    return () => clearInterval(iv)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /* ── Filtered + sorted rows ── */
  const displayRows = useMemo(() => {
    let rows: DataRow[]
    if (tab === 'all') {
      rows = dbAll
    } else {
      const manual = data[tab] || []
      const fromDb = dbAll.filter(r => r.category === tab)
      // Merge: manual rows (by _cid) + db rows not in manual
      const manualIds = new Set(manual.map(r => r._cid))
      rows = [...manual, ...fromDb.filter(r => !manualIds.has(r._cid))]
    }

    // Search filter
    if (q) {
      const lq = q.toLowerCase()
      rows = rows.filter(r =>
        Object.values(r).some(v => v != null && String(v).toLowerCase().includes(lq))
      )
    }

    // Sort
    if (sortKey) {
      rows = [...rows].sort((a, b) => {
        const va = String(a[sortKey] ?? '')
        const vb = String(b[sortKey] ?? '')
        const cmp = va.localeCompare(vb, 'ko', { numeric: true })
        return sortDir === 'asc' ? cmp : -cmp
      })
    }

    return rows
  }, [tab, data, dbAll, q, sortKey, sortDir])

  /* ── Undo ── */
  const pushHistory = useCallback(() => {
    historyRef.current.push({
      data: JSON.parse(JSON.stringify(data)),
      dbAll: JSON.parse(JSON.stringify(dbAll)),
    })
  }, [data, dbAll])

  const undo = useCallback(() => {
    const prev = historyRef.current.undo({ data, dbAll })
    if (!prev) return
    setData(prev.data)
    setDbAll(prev.dbAll)
  }, [data, dbAll])

  const redo = useCallback(() => {
    const next = historyRef.current.redo({ data, dbAll })
    if (!next) return
    setData(next.data)
    setDbAll(next.dbAll)
  }, [data, dbAll])

  /* ── Ctrl+Z / Ctrl+Y ── */
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') { e.preventDefault(); undo() }
      if ((e.ctrlKey || e.metaKey) && e.key === 'y') { e.preventDefault(); redo() }
    }
    document.addEventListener('keydown', h)
    return () => document.removeEventListener('keydown', h)
  }, [undo, redo])

  /* ── Server save ── */
  const saveToServer = useCallback(async (cid: string, field: string, value: string) => {
    try {
      await fetch(`${API}/api/admin/candidates/${encodeURIComponent(cid)}`, {
        method: 'PATCH',
        headers: { ...hdrs(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ [field]: value }),
      })
    } catch { /* offline — edit saved locally */ }
  }, [hdrs])

  /* ── GridEngine callbacks ── */
  const gridCallbacks = useMemo<GridCallbacks>(() => ({
    onCellChange: (rowIdx: number, colKey: string, value: string) => {
      pushHistory()
      const row = displayRows[rowIdx]
      if (!row) return
      // Update in dbAll
      setDbAll(prev => prev.map(r => r._cid === row._cid ? { ...r, [colKey]: value } : r))
      // Update in manual data
      setData(prev => {
        const u = { ...prev }
        for (const k of ['active', 'past', 'blacklist'] as CategoryKey[]) {
          u[k] = prev[k].map(r => r._cid === row._cid ? { ...r, [colKey]: value } : r)
        }
        return u
      })
      // Save edit overlay
      const cid = String(row._cid ?? '')
      if (cid) {
        const edits = editsRef.current
        edits[cid] = { ...(edits[cid] || {}), [colKey]: value } as EditOverride
        prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
        // DB field mapping for server save
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
    onSelectionChange: () => {},
    onContextMenu: (e: MouseEvent, rowIdx: number, row: DataRow) => {
      setCtx({ x: e.clientX, y: e.clientY, rowIdx, row })
    },
    onSort: (colKey: string) => {
      setSortKey(prev => {
        if (prev === colKey) {
          setSortDir(d => d === 'asc' ? 'desc' : 'asc')
          return colKey
        }
        setSortDir('asc')
        return colKey
      })
    },
    onColumnResize: (colKey: string, width: number) => {
      setCols(prev => prev.map(c => c.key === colKey ? { ...c, w: width } : c))
    },
    onRequestMore: () => { loadMore() },
    onPhotoClick: () => {},
    onMailClick: (_rowIdx: number, row: DataRow) => {
      const email = String(row.email ?? '')
      if (email) window.open(`mailto:${email}`, '_blank')
    },
    onStageChange: (rowIdx: number, stage: string) => {
      pushHistory()
      const row = displayRows[rowIdx]
      if (!row) return
      const cid = String(row._cid ?? '')
      setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, stage } : r))
      setData(prev => {
        const u = { ...prev }
        for (const k of ['active', 'past', 'blacklist'] as CategoryKey[]) {
          u[k] = prev[k].map(r => r._cid === cid ? { ...r, stage } : r)
        }
        return u
      })
      if (cid) {
        const edits = editsRef.current
        edits[cid] = { ...(edits[cid] || {}), stage } as EditOverride
        prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
      }
    },
  }), [displayRows, pushHistory, loadMore, saveToServer])

  /* ── Engine init ── */
  useEffect(() => {
    if (!containerRef.current || !ready) return
    const engine = new GridEngine(containerRef.current, gridCallbacks)
    engine.setHeaderGetter(hdrs)
    engineRef.current = engine
    return () => { engine.destroy(); engineRef.current = null }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready])

  /* ── Update engine when callbacks change ── */
  useEffect(() => {
    // GridEngine stores callbacks reference — need to recreate on change
    // For now, we keep the engine stable and update data only
  }, [gridCallbacks])

  /* ── Sync data to engine ── */
  useEffect(() => {
    const e = engineRef.current
    if (!e) return
    const visCols = cols.filter(c => c.v !== false)
    e.setCols(cols)
    e.setData(displayRows)
    e.setFrozenCols(frozenCols)
    e.setSort(sortKey, sortDir)
    void visCols // used in setCols
  }, [displayRows, cols, frozenCols, sortKey, sortDir])

  /* ── Context menu actions ── */
  const ctxAction = useCallback((action: string) => {
    if (!ctx) return
    const { row } = ctx
    const cid = String(row._cid ?? '')
    pushHistory()

    switch (action) {
      case 'to_active':
      case 'to_past':
      case 'to_blacklist': {
        const newCat = action.replace('to_', '') as CategoryKey
        setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, category: newCat } : r))
        setData(prev => {
          const u: DataStore = { active: [], past: [], blacklist: [] }
          for (const k of ['active', 'past', 'blacklist'] as CategoryKey[]) {
            u[k] = prev[k].filter(r => r._cid !== cid)
          }
          const moved = { ...row, category: newCat }
          u[newCat] = [...u[newCat], moved]
          return u
        })
        const edits = editsRef.current
        edits[cid] = { ...(edits[cid] || {}), category: newCat } as EditOverride
        prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
        break
      }
      case 'copy_email': {
        const email = String(row.email ?? '')
        if (email) navigator.clipboard.writeText(email).catch(() => {})
        break
      }
      case 'copy_row': {
        const visCols = cols.filter(c => c.v !== false)
        const text = visCols.map(c => String(row[c.key] ?? '')).join('\t')
        navigator.clipboard.writeText(text).catch(() => {})
        break
      }
    }
    setCtx(null)
  }, [ctx, cols, pushHistory])

  /* ── CSV Export ── */
  const exportCsv = useCallback(() => {
    const visCols = cols.filter(c => c.v !== false)
    const header = visCols.map(c => c.label).join(',')
    const body = displayRows.map(r =>
      visCols.map(c => {
        const v = String(r[c.key] ?? '').replace(/"/g, '""')
        return `"${v}"`
      }).join(',')
    ).join('\n')
    const blob = new Blob(['\uFEFF' + header + '\n' + body], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bridge_${tab}_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }, [cols, displayRows, tab])

  /* ── Full reload ── */
  const fullReload = useCallback(() => {
    dbOffsetRef.current = 0
    allLoadedRef.current = false
    setDbAll([])
    loadMore()
  }, [loadMore])

  /* ── Close context menu on click outside ── */
  useEffect(() => {
    if (!ctx) return
    const h = () => setCtx(null)
    document.addEventListener('click', h)
    return () => document.removeEventListener('click', h)
  }, [ctx])

  /* ── Tab counts ── */
  const tabCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const t of TABS) {
      if (t.key === 'all') counts[t.key] = dbAll.length
      else counts[t.key] = dbAll.filter(r => r.category === t.key).length + (data[t.key]?.length ?? 0)
    }
    return counts
  }, [dbAll, data])

  if (!adminKey) {
    return <div style={{ padding: 40, textAlign: 'center', color: '#64748b' }}>관리자 인증이 필요합니다.</div>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#f8fafc' }}>
      {/* ── Toolbar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
        background: '#fff', borderBottom: '1px solid #e2e8f0', flexShrink: 0,
      }}>
        {/* Search */}
        <div style={{ position: 'relative', flex: '0 0 240px' }}>
          <input
            type="text" placeholder="검색..."
            value={q} onChange={e => setQ(e.target.value)}
            style={{
              width: '100%', padding: '6px 10px 6px 30px', border: '1px solid #e2e8f0',
              borderRadius: 6, fontSize: 13, outline: 'none', background: '#f8fafc',
            }}
          />
          <span style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', fontSize: 14 }}>🔍</span>
        </div>

        {/* Sync info */}
        <span style={{ fontSize: 11, color: '#94a3b8', marginLeft: 4 }}>
          {loading ? '로딩...' : `${dbAll.length}/${dbTotal}`}
          {lastSync && ` · ${lastSync}`}
          {newCount > 0 && <span style={{ color: '#ef4444', fontWeight: 700 }}> · 신규 {newCount}</span>}
        </span>

        <div style={{ flex: 1 }} />

        {/* Actions */}
        <button onClick={fullReload} style={btnStyle} title="새로고침">↻</button>
        <button onClick={undo} disabled={!historyRef.current.canUndo} style={btnStyle} title="실행취소">⤺</button>
        <button onClick={redo} disabled={!historyRef.current.canRedo} style={btnStyle} title="다시실행">⤻</button>
        <button onClick={exportCsv} style={btnStyle} title="CSV 내보내기">📊</button>
        <button onClick={() => setFrozenCols(p => p === 0 ? 3 : 0)} style={btnStyle} title="고정열 토글">
          {frozenCols > 0 ? '🔒' : '🔓'}
        </button>
      </div>

      {/* ── Tabs ── */}
      <div style={{
        display: 'flex', gap: 0, background: '#fff', borderBottom: '1px solid #e2e8f0',
        flexShrink: 0, paddingLeft: 8,
      }}>
        {TABS.map(t => {
          const active = tab === t.key
          return (
            <button key={t.key} onClick={() => setTab(t.key)} style={{
              padding: '8px 16px', fontSize: 13, fontWeight: active ? 700 : 400,
              color: active ? t.color : '#64748b',
              background: active ? t.bg : 'transparent',
              border: 'none', borderBottom: active ? `2px solid ${t.accent}` : '2px solid transparent',
              cursor: 'pointer', transition: 'all 0.15s',
            }}>
              {t.icon} {t.label}
              <span style={{
                marginLeft: 6, fontSize: 11, fontWeight: 700,
                background: active ? t.accent + '20' : '#f1f5f9',
                color: active ? t.accent : '#94a3b8',
                padding: '1px 6px', borderRadius: 10,
              }}>
                {tabCounts[t.key] ?? 0}
              </span>
            </button>
          )
        })}
      </div>

      {/* ── Canvas Container ── */}
      <div
        ref={containerRef}
        style={{ flex: 1, position: 'relative', minHeight: 0 }}
      />

      {/* ── Context Menu ── */}
      {ctx && (
        <div
          style={{
            position: 'fixed', left: ctx.x, top: ctx.y, zIndex: 100,
            background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8,
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)', padding: '4px 0', minWidth: 180,
          }}
          onClick={e => e.stopPropagation()}
        >
          <CtxItem label="📋 행 복사" onClick={() => ctxAction('copy_row')} />
          <CtxItem label="📧 이메일 복사" onClick={() => ctxAction('copy_email')} />
          <div style={{ height: 1, background: '#e2e8f0', margin: '4px 0' }} />
          <CtxItem label="👤 구직활동중으로" onClick={() => ctxAction('to_active')} />
          <CtxItem label="✅ 체결완료로" onClick={() => ctxAction('to_past')} />
          <CtxItem label="⛔ 블랙리스트로" onClick={() => ctxAction('to_blacklist')} />
          <div style={{ height: 1, background: '#e2e8f0', margin: '4px 0' }} />
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

      {/* Legend bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '4px 12px',
        background: '#fff', borderTop: '1px solid #e2e8f0', fontSize: 11, color: '#64748b',
        flexShrink: 0,
      }}>
        {STAGES.filter(s => s.key !== 'none').map(s => (
          <span key={s.key} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: s.color, border: '1px solid #e2e8f0' }} />
            {s.label}
          </span>
        ))}
        <span style={{ marginLeft: 'auto' }}>
          {MTAGS.map(m => (
            <span key={m.key} style={{ color: m.c, marginLeft: 8 }}>{m.label}</span>
          ))}
        </span>
      </div>
    </div>
  )
}

/* ── Context menu item ── */
function CtxItem({ label, onClick }: { label: string; onClick: () => void }) {
  const [hover, setHover] = useState(false)
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        padding: '6px 14px', fontSize: 13, cursor: 'pointer',
        background: hover ? '#f1f5f9' : 'transparent',
        color: '#1e293b',
      }}
    >
      {label}
    </div>
  )
}

/* ── Button style ── */
const btnStyle: React.CSSProperties = {
  padding: '5px 10px', border: '1px solid #e2e8f0', borderRadius: 6,
  background: '#fff', cursor: 'pointer', fontSize: 14,
  color: '#475569', lineHeight: 1,
}
