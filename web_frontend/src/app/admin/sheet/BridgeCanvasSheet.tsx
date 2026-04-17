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
import * as XLSX from 'xlsx'

/* ── Types ── */
interface DataStore { active: DataRow[]; past: DataRow[]; blacklist: DataRow[] }
type EditOverride = Partial<DataRow>
interface CtxMenu { x: number; y: number; rowIdx: number; row: DataRow }
interface FilterPopup { colKey: string; x: number; y: number }
interface HeaderMenu { colKey: string; x: number; y: number }
interface TagPopup { rowIdx: number; x: number; y: number }

const API = API_URL
const PAGE_SIZE = 150
const PARALLEL   = 5    // 동시 요청 수 — 3000행 기준 ~4배 빠름, 행수 무제한
/* ── Google Meet Pool (localStorage) ── */
const MEET_POOL_KEY = 'bridge_meet_pool'
const DEFAULT_MEET_POOL: string[] = [
  'https://meet.google.com/kmt-ydhj-fmf',
]
function loadMeetPool(): string[] {
  if (typeof window === 'undefined') return DEFAULT_MEET_POOL
  try { const s = localStorage.getItem(MEET_POOL_KEY); if (s) { const a = JSON.parse(s); if (Array.isArray(a) && a.length) return a } } catch { /* */ }
  return DEFAULT_MEET_POOL
}
function pickRandomMeet(): string {
  const pool = loadMeetPool()
  return pool[Math.floor(Math.random() * pool.length)]
}
/** Google Calendar 이벤트 생성 URL (Meet 자동 포함) */
function buildGCalUrl(title: string, date: string, time: string, durationMin: number, guestEmail?: string): string {
  // date=YYYY-MM-DD, time=HH:MM → UTC ISO
  const [y, mo, d] = date.split('-').map(Number)
  const [h, mi] = time.split(':').map(Number)
  const start = new Date(y, mo - 1, d, h, mi)
  const end = new Date(start.getTime() + durationMin * 60000)
  const fmt = (dt: Date) => dt.toISOString().replace(/[-:]/g, '').replace(/\.\d+/, '')
  let url = `https://calendar.google.com/calendar/u/0/r/eventedit?text=${encodeURIComponent(title)}&dates=${fmt(start)}/${fmt(end)}&details=${encodeURIComponent('BRIDGE Recruitment Interview')}`
  if (guestEmail) url += `&add=${encodeURIComponent(guestEmail)}`
  return url
}

/* ── Interview defaults persistence ── */
const IV_PREFS_KEY = 'bridge_iv_prefs'
interface IvPrefs { time: string; duration: number; autoSend: boolean }
function loadIvPrefs(): IvPrefs {
  if (typeof window === 'undefined') return { time: '14:00', duration: 20, autoSend: true }
  try { const s = localStorage.getItem(IV_PREFS_KEY); if (s) return JSON.parse(s) } catch { /* */ }
  return { time: '14:00', duration: 20, autoSend: true }
}
function saveIvPrefs(p: IvPrefs) { if (typeof window !== 'undefined') localStorage.setItem(IV_PREFS_KEY, JSON.stringify(p)) }

/* ── 집중관리 탭 필터 — 진행중/계약중 강사 ── */
const FOCUS_STAGES = new Set(['interview', 'proposal', 'signed', 'guide_sent', 'guide_done', 'caution'])
const isFocusRow = (r: DataRow): boolean =>
  r.category === 'past' ||
  (r.category === 'active' && FOCUS_STAGES.has(r.stage as string))

/* ── DB → DataRow mapping ── */
function mapRow(c: Record<string, unknown>, idx: number, edits: Record<string, EditOverride>): DataRow {
  const cid = String(c.candidate_id ?? c.id ?? '')
  const ov = edits[cid] || {}
  const st = String(c.status ?? '')
  const cat: CategoryKey = st === 'Active' ? 'active' : st === 'Blacklist' ? 'blacklist' : 'past'
  const tattoo = [c.tattoo, c.piercings].filter(Boolean).join('/')
  const ts = String(c.created_at ?? '').slice(0, 10).replace(/-/g, '.').slice(2)
  const isWebForm = String(c.source) === 'web_form'
  return {
    id: idx + 1, _cid: cid,
    category: (ov.category as string) ?? cat,
    stage: (ov.stage as string) ?? String(c.stage ?? 'none'),
    mailStatus: (ov.mailStatus as string) ?? String(c.mail_tags ?? ''),
    photoUrl: (() => {
      const raw = String(c.photo_url ?? ov.photoUrl ?? '')
      if (!raw) return ''
      return raw.startsWith('http') ? raw : `${API}${raw}`
    })(),
    photoSize: Number(ov.photoSize ?? 50),
    email: (ov.email as string) ?? String(c.email ?? ''),
    name: (ov.name as string) ?? String(c.full_name ?? ''),
    mgtNum: c.sheet_number != null ? String(c.sheet_number) : String(c.row_id ?? ''),
    arc: (ov.arc as string) ?? String(c.arc_holders ?? ''),
    nationality: ((ov.nationality as string) ?? String(c.nationality_plain || c.nationality || '')).replace(/[\r\n]+/g, ' ').trim(),
    background: (ov.background as string) ?? String(c.ancestry ?? ''),
    age: (ov.age as string) ?? String(c.dob ?? ''),
    gender: (ov.gender as string) ?? String(c.gender ?? ''),
    currentLoc: ((ov.currentLoc as string) ?? String(c.current_location ?? '')).replace(/[\r\n]+/g, ' ').trim(),
    startDate: (ov.startDate as string) ?? String(c.start_date ?? ''),
    university: (ov.university as string) ?? String(c.target ?? ''),
    prefRegion: (ov.prefRegion as string) ?? String(c.area_prefs ?? ''),
    reference: (ov.reference as string) ?? String(c.reference ?? ''),
    totalExp: (ov.totalExp as string) ?? String(c.experience ?? ''),
    employment: (ov.employment as string) ?? String(c.employment ?? ''),
    notice: (ov.notice as string) ?? String(c.dislikes ?? ''),
    preference: (ov.preference as string) ?? String(c.preferences ?? ''),
    applied: (ov.applied as string) ?? String(c.job_prefs ?? ''),
    contractOffer: (ov.contractOffer as string) ?? String(c.contract_offered ?? ''),
    proposal: (ov.proposal as string) ?? String(c.recruiter_memo ?? ''), mailAction: '',
    resumeStatus: String(c.resume_status ?? 'pending'),
    curSalary: (ov.curSalary as string) ?? String(c.current_salary ?? ''),
    hopeSalary: (ov.hopeSalary as string) ?? String(c.desired_salary ?? ''),
    interviewCol: (ov.interviewCol as string) ?? String(c.interview_time ?? ''),
    degree: (ov.degree as string) ?? String(c.education_level ?? ''),
    major: (ov.major as string) ?? String(c.major ?? ''),
    cert: (ov.cert as string) ?? String(c.certification ?? ''),
    docs: (ov.docs as string) ?? String(c.doc_status ?? c.documents ?? ''),
    health: (ov.health as string) ?? String(c.health_info ?? ''),
    personalNote: (ov.personalNote as string) ?? String(c.personal_consideration ?? ''),
    tattooPiercing: (ov.tattooPiercing as string) ?? tattoo,
    family: (ov.family as string) ?? String(c.dependents ?? ''),
    married: (ov.married as string) ?? String(c.married ?? ''),
    housing: (ov.housing as string) ?? String(c.housing ?? c.housing_type ?? ''),
    religion: (ov.religion as string) ?? String(c.religion ?? ''),
    e2visa: (ov.e2visa as string) ?? String(c.e_visa ?? c.visa_type ?? ''),
    kakao: (ov.kakao as string) ?? String(c.kakaotalk ?? ''),
    phone: (ov.phone as string) ?? String(c.mobile_phone ?? ''),
    crimCheck: (ov.crimCheck as string) ?? String(c.criminal_record_check ?? c.criminal_record ?? ''),
    domesticCrim: (ov.domesticCrim as string) ?? String(c.korean_criminal_record ?? ''),
    infoProvide: (ov.infoProvide as string) ?? String(c.consent ?? ''),
    verified: (ov.verified as string) ?? String(c.fact_check ?? ''),
    source: (ov.source as string) ?? (isWebForm ? '\u2605NEW' : String(c.how_to ?? c.source ?? '')),
    timestamp: ts,
    hired: (ov.hired as string) ?? String(c.placed_company ?? ''),
    wage: (ov.wage as string) ?? String(c.placed_salary ?? ''),
    moveIn: (ov.moveIn as string) ?? String(c.start_month ?? ''),
    housingCost: (ov.housingCost as string) ?? String(c.housing_detail ?? ''),
    introFee: (ov.introFee as string) ?? String(c.referral_fee ?? ''),
    process: (ov.process as string) ?? String(c.process_date ?? ''),
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
  const [photoToast, setPhotoToast] = useState<{ msg: string; ok: boolean } | null>(null)
  const [loading, setLoading] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [lastSync, setLastSync] = useState('')
  const [newCount, setNewCount] = useState(0)
  const [ready, setReady] = useState(false)
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set())
  const [newBanner, setNewBanner] = useState(0)  // 신규 접수 배너 카운트
  const [bannerDismissed, setBannerDismissed] = useState(false)
  const [pipelineStage, setPipelineStage] = useState<string | null>(null) // 파이프라인 상태표시줄

  // Tab customization (label rename + drag reorder)
  const TAB_PREFS_KEY = 'bridge_sheet_tab_prefs'
  const loadTabPrefs = useCallback(() => {
    try {
      const raw = localStorage.getItem(TAB_PREFS_KEY)
      if (!raw) return { order: TABS.map(t => t.key), labels: {} as Record<string, string> }
      const p = JSON.parse(raw)
      return { order: p.order ?? TABS.map(t => t.key), labels: p.labels ?? {} }
    } catch { return { order: TABS.map(t => t.key), labels: {} as Record<string, string> } }
  }, [])
  const [tabOrder, setTabOrder] = useState<string[]>(() => loadTabPrefs().order)
  const [tabLabels, setTabLabels] = useState<Record<string, string>>(() => loadTabPrefs().labels)
  const [editingTab, setEditingTab] = useState<string | null>(null)
  const [dragTab, setDragTab] = useState<string | null>(null)
  const orderedTabs = useMemo(() => tabOrder.map(k => TABS.find(t => t.key === k)).filter(Boolean) as typeof TABS, [tabOrder])
  const saveTabPrefs = useCallback((order: string[], labels: Record<string, string>) => {
    try { localStorage.setItem(TAB_PREFS_KEY, JSON.stringify({ order, labels })) } catch {}
  }, [])

  // Mail modal
  const [mailOpen, setMailOpen] = useState(false)
  const [mailRecipients, setMailRecipients] = useState<DataRow[]>([])

  // Interview modal (bridge / school)
  const [ivModal, setIvModal] = useState(false)
  const [ivType, setIvType] = useState<'bridge' | 'school'>('bridge')
  const [ivTarget, setIvTarget] = useState<DataRow | null>(null)
  const [ivDate, setIvDate] = useState('')
  const [ivTime, setIvTime] = useState('14:00')
  const [ivDuration, setIvDuration] = useState(20)
  const [ivNotes, setIvNotes] = useState('')
  const [ivAutoSend, setIvAutoSend] = useState(true)
  const [ivMeetLink, setIvMeetLink] = useState('')
  const [ivLoading, setIvLoading] = useState(false)
  const [ivResult, setIvResult] = useState<{ id: number; emailSent: boolean; meetLink: string } | null>(null)
  const [ivMeetPool, setIvMeetPool] = useState<string[]>([])
  const [ivNewLink, setIvNewLink] = useState('')
  const [ivEmployerName, setIvEmployerName] = useState('')

  // Filter popup
  const [filterPopup, setFilterPopup] = useState<FilterPopup | null>(null)
  const [filters, setFilters] = useState<Record<string, Set<string>>>({})
  const [filterSearch, setFilterSearch] = useState('')

  // Header context menu
  const [headerMenu, setHeaderMenu] = useState<HeaderMenu | null>(null)
  const [tagPopup, setTagPopup] = useState<TagPopup | null>(null)

  // Text/Bg color pickers (Google Sheets style)
  const [showTextColor, setShowTextColor] = useState(false)
  const [showBgColor, setShowBgColor] = useState(false)

  // Memo area
  const [memo, setMemo] = useState('')
  const [memoStyle, setMemoStyle] = useState({ fontSize: 13, bold: false, color: '#111', bgColor: '#FFFDE7' })
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

  /* ── 세션 중 삭제된 CID 추적 — 리로드 시 복원 방지 ── */
  const deletedCidsRef = useRef<Set<string>>(new Set())

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
        if (mp.style) setMemoStyle({ fontSize: 13, bold: false, color: '#111', bgColor: '#FFFDE7', ...mp.style })
      }
    } catch { /* ignore */ }

    setReady(true)
  }, [])

  useEffect(() => { if (ready) prefsRef.current.save(cols, frozenCols) }, [cols, frozenCols, ready])
  useEffect(() => { if (ready) prefsRef.current.saveTabData(data) }, [data, ready])

  /* ── Data fetching: AUTO-LOAD ALL ── */
  /* ── 로딩 상태 refs (중복 방지 + scroll-triggered lazy load) ── */
  const loadOffsetRef    = useRef(0)
  const isLoadingMoreRef = useRef(false)
  const dbTotalRef       = useRef(0)
  const loadAllDataRef   = useRef<(() => Promise<void>) | null>(null)
  const lastPollTotalRef = useRef(0)
  const wakeRetryRef     = useRef(0)

  const loadAllData = useCallback(async () => {
    setLoading(true)
    setFetchError(null)
    loadOffsetRef.current    = 0
    isLoadingMoreRef.current = true
    const edits   = editsRef.current
    const hdrs    = hdrsRef.current
    const allRows: DataRow[] = []

    /* ① 첫 페이지 — 5초 timeout + 자동 재시도 (Render cold start 대응) */
    const ctrl = new AbortController()
    const ctrlTimer = setTimeout(() => ctrl.abort(), 5000)
    let res0: Response
    try {
      res0 = await fetch(
        `${API}/api/admin/candidates?limit=${PAGE_SIZE}&offset=0`,
        { headers: hdrs(), signal: ctrl.signal },
      )
      clearTimeout(ctrlTimer)
    } catch (e: unknown) {
      clearTimeout(ctrlTimer)
      const isAbort = e instanceof DOMException && e.name === 'AbortError'
      wakeRetryRef.current += 1
      if (isAbort && wakeRetryRef.current <= 20) {
        setFetchError(`서버 기동 중... (${wakeRetryRef.current}회 재시도) — 잠시 기다려 주세요`)
      } else {
        setFetchError('서버 연결 실패 — 새로고침 후 재시도하세요')
      }
      setLoading(false)
      isLoadingMoreRef.current = false
      if (isAbort && wakeRetryRef.current <= 20) {
        setTimeout(() => loadAllDataRef.current?.(), 3000)
      }
      return
    }
    wakeRetryRef.current = 0
    try {
    if (!res0.ok) {
        const msg = res0.status === 403
          ? `인증 오류 (403) — 재로그인 후 시도`
          : res0.status >= 500
          ? `서버 오류 (${res0.status}) — Render 서버 기동 중일 수 있음`
          : `HTTP ${res0.status} 오류`
        setFetchError(msg)
        setLoading(false)
        isLoadingMoreRef.current = false
        return
      }
      const json0  = await res0.json()
      const raw0: Record<string, unknown>[] = json0.data?.candidates ?? []
      const total: number = json0.data?.total ?? 0
      setDbTotal(total)
      dbTotalRef.current = total

      raw0.forEach((c, i) => allRows.push(mapRow(c, i, edits)))
      loadOffsetRef.current = raw0.length
      setLoaded(allRows.length)
      const dc0 = deletedCidsRef.current
      setDbAll(dc0.size > 0 ? allRows.filter(r => !dc0.has(String(r._cid ?? ''))) : [...allRows])
      setNewCount(raw0.filter(r => String(r.source ?? r.how_to ?? '') === 'web_form').length)

      if (raw0.length < PAGE_SIZE || allRows.length >= total) {
        setLoading(false)
        setLastSync(new Date().toLocaleTimeString())
        isLoadingMoreRef.current = false
        return
      }

      /* ② 나머지 — PARALLEL 페이지씩 병렬 로딩 (행수 무제한) */
      while (loadOffsetRef.current < total) {
        const batchOffsets: number[] = []
        for (let i = 0; i < PARALLEL; i++) {
          const off = loadOffsetRef.current + i * PAGE_SIZE
          if (off >= total) break
          batchOffsets.push(off)
        }
        if (batchOffsets.length === 0) break

        const results = await Promise.all(
          batchOffsets.map(async off => {
            try {
              const r = await fetch(
                `${API}/api/admin/candidates?limit=${PAGE_SIZE}&offset=${off}`,
                { headers: hdrs() },
              )
              if (!r.ok) return { off, rows: [] as Record<string, unknown>[] }
              const j = await r.json()
              return { off, rows: (j.data?.candidates ?? []) as Record<string, unknown>[] }
            } catch {
              return { off, rows: [] as Record<string, unknown>[] }
            }
          })
        )

        // 오프셋 순서 보장 후 allRows에 삽입
        results.sort((a, b) => a.off - b.off)
        for (const { off, rows } of results) {
          rows.forEach((c, i) => allRows.push(mapRow(c, off + i, edits)))
        }

        loadOffsetRef.current += batchOffsets.length * PAGE_SIZE
        setLoaded(allRows.length)
        const dc = deletedCidsRef.current
        setDbAll(dc.size > 0 ? allRows.filter(r => !dc.has(String(r._cid ?? ''))) : [...allRows])

        // 마지막 배치가 PAGE_SIZE 미만이면 서버 데이터 소진
        if (results.some(r => r.rows.length < PAGE_SIZE)) break
      }
    } catch (e) {
      setFetchError(e instanceof Error ? `데이터 로딩 오류: ${e.message}` : '서버 연결 실패')
    }

    setLoading(false)
    setLastSync(new Date().toLocaleTimeString())
    isLoadingMoreRef.current = false
  }, [])

  useEffect(() => { loadAllDataRef.current = loadAllData }, [loadAllData])

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
        const serverTotal: number = json.data?.total ?? 0
        setNewCount(rows.filter(r => String(r.source ?? r.how_to ?? '') === 'web_form').length)

        // 신규 제출 감지 → 자동 리로드 (즉각 sheet 반영)
        if (lastPollTotalRef.current > 0 && serverTotal > lastPollTotalRef.current) {
          loadAllDataRef.current?.()
        }
        lastPollTotalRef.current = serverTotal

        // 신규 접수 배너 감지 — localStorage 마지막 방문 이후 신규 항목
        const lastVisit = localStorage.getItem('bridge_last_sheet_visit') ?? ''
        const freshRows = rows.filter(r => {
          const created = String(r.created_at ?? '')
          return created > lastVisit && String(r.source ?? r.how_to ?? '') === 'web_form'
        })
        if (freshRows.length > 0) {
          setNewBanner(freshRows.length)
          setBannerDismissed(false)
        }
      } catch { /* ignore */ }
    }, 30_000)
    // 페이지 진입 시 방문 시각 기록
    localStorage.setItem('bridge_last_sheet_visit', new Date().toISOString())
    return () => clearInterval(iv)
  }, [])

  /* ── Filtered + sorted rows ── */
  const displayRows = useMemo(() => {
    let rows: DataRow[]
    if (dbAll.length === 0) {
      // 로딩 중: localStorage 캐시로 즉시 표시
      if (tab === 'all') {
        rows = [...(data.active || []), ...(data.past || []), ...(data.blacklist || [])]
      } else if (tab === 'focus') {
        rows = [
          ...(data.active || []).filter(r => FOCUS_STAGES.has(r.stage as string)),
          ...(data.past || []),
        ]
      } else {
        rows = (data[tab] || [])
      }
    } else {
      // 로드 완료: 항상 서버에서 받은 복호화된 최신 데이터 사용
      if (tab === 'all') {
        rows = dbAll
      } else if (tab === 'focus') {
        rows = dbAll.filter(isFocusRow)
      } else {
        rows = dbAll.filter(r => r.category === tab)
      }
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
    if (prev) {
      // undo로 복원된 CID는 삭제 추적에서 제거 — 되돌리기 허용
      const curCids = new Set(dbAllRef.current.map(r => String(r._cid ?? '')))
      const prevCids = prev.dbAll.map(r => String(r._cid ?? ''))
      for (const cid of prevCids) {
        if (!curCids.has(cid)) deletedCidsRef.current.delete(cid)
      }
      setData(prev.data); setDbAll(prev.dbAll)
    }
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

  /* ── Photo toast helper ── */
  const showPhotoToast = useCallback((msg: string, ok = true) => {
    setPhotoToast({ msg, ok })
    setTimeout(() => setPhotoToast(null), 3000)
  }, [])

  /* ── Clipboard paste (image) — 사진 칸 캡쳐 붙여넣기 ── */
  useEffect(() => {
    const h = (e: ClipboardEvent) => {
      // 메모 textarea에 포커스가 있을 때는 일반 붙여넣기 허용
      const target = e.target as HTMLElement
      if (target && (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT')) return

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
          // FormData needs auto Content-Type (multipart boundary) — only pass auth header
          const { 'Content-Type': _, ...uploadHdrs } = hdrsRef.current()
          const doBase64 = () => {
            const rd = new FileReader()
            rd.onload = ev2 => {
              pushHistory()
              const dataUrl = ev2.target?.result as string
              setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, photoUrl: dataUrl } : r))
              if (cid) {
                const edits = editsRef.current
                edits[cid] = { ...(edits[cid] || {}), photoUrl: dataUrl } as EditOverride
                prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
              }
              showPhotoToast('사진 저장 완료 ✓')
            }
            rd.readAsDataURL(blob)
          }
          fetch(`${API}/api/admin/upload-image`, {
            method: 'POST', headers: uploadHdrs, body: fd,
          }).then(r => r.ok ? r.json() : null).then(async j => {
            const url: string = j?.data?.url ?? ''
            if (!url) { doBase64(); return }
            const fullUrl = url.startsWith('http') ? url : `${API}${url}`
            pushHistory()
            setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, photoUrl: fullUrl } : r))
            if (cid) {
              await fetch(`${API}/api/admin/candidates/${cid}`, {
                method: 'PATCH',
                headers: { ...hdrsRef.current(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ photo_url: url }),
              }).catch(() => {})
              const edits = editsRef.current
              edits[cid] = { ...(edits[cid] || {}), photoUrl: fullUrl } as EditOverride
              prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
            }
            showPhotoToast('사진 저장 완료 ✓')
          }).catch(() => doBase64())
          break
        }
      }
    }
    document.addEventListener('paste', h)
    return () => document.removeEventListener('paste', h)
  }, [selectedRows, pushHistory, showPhotoToast])

  /* ── Server save ── */
  const saveToServer = useCallback(async (cid: string, field: string, value: string | number) => {
    try {
      const res = await fetch(`${API}/api/admin/candidates/${encodeURIComponent(cid)}`, {
        method: 'PATCH',
        headers: { ...hdrsRef.current(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ [field]: value }),
      })
      if (!res.ok) {
        console.error(`[PATCH] ${field} 저장 실패: ${res.status}`)
        showPhotoToast(`저장 실패: ${field}`, false)
      }
    } catch {
      console.error(`[PATCH] ${field} 네트워크 오류`)
      showPhotoToast('네트워크 오류 — 저장 실패', false)
    }
  }, [showPhotoToast])

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
    const { 'Content-Type': _ct, ...fileHdrs } = hdrsRef.current()
    fetch(`${API}/api/admin/upload-image`, {
      method: 'POST', headers: fileHdrs, body: fd,
    }).then(r => r.ok ? r.json() : null).then(async j => {
      const url: string = j?.data?.url ?? ''
      if (!url) { showPhotoToast('사진 업로드 실패', false); return }
      const fullUrl = url.startsWith('http') ? url : `${API}${url}`
      pushHistory()
      setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, photoUrl: fullUrl } : r))
      if (cid) {
        await fetch(`${API}/api/admin/candidates/${cid}`, {
          method: 'PATCH',
          headers: { ...hdrsRef.current(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ photo_url: url }),
        })
        const edits = editsRef.current
        edits[cid] = { ...(edits[cid] || {}), photoUrl: fullUrl } as EditOverride
        prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
      }
      showPhotoToast('사진 저장 완료 ✓')
    }).catch(() => {
      const rd = new FileReader()
      rd.onload = ev2 => {
        pushHistory()
        setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, photoUrl: ev2.target?.result as string } : r))
        showPhotoToast('사진 저장 (로컬)')
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

  /* ── Style apply helper (with toggle support) ── */
  const applyStyleToSelection = useCallback((style: CellStyle) => {
    const engine = engineRef.current
    if (!engine) return
    const rows = displayRowsRef.current
    const visCols = engine.getVisibleCols()
    const ac = engine.selection.getActiveCell()
    const selectedRowSet = engine.selection.getSelectedRows()
    const hasColSel = engine.selection.hasColSelection()
    const isAllRows = selectedRowSet.size >= rows.length && rows.length > 0
    const styleCols = visCols.filter(c => c.key !== 'rowNum' && c.key !== 'photo')

    // 열 전체 선택 → 선택된 열 × 전체 displayRows 대상
    if (hasColSel) {
      const selCols = visCols.filter((_, vi) => engine.selection.isColSelected(vi))
        .filter(c => c.key !== 'rowNum' && c.key !== 'photo')
      if (selCols.length === 0) return
      const entries: Array<{ cid: string; colKey: string }> = []
      for (const row of rows) {
        const cid = String(row._cid ?? '')
        if (!cid) continue
        for (const col of selCols) entries.push({ cid, colKey: col.key })
      }
      if (entries.length > 0) engine.styleManager.batchSet(entries, style)
      engine.refresh()
      showPhotoToast('서식 적용 완료', true)
      return
    }

    if (isAllRows || selectedRowSet.size > 0) {
      // 전체 선택 또는 행 선택 → 선택된 모든 행 × 모든 컬럼에 일괄 적용
      const targetRows = isAllRows
        ? rows
        : [...selectedRowSet].map(ri => rows[ri]).filter((r): r is DataRow => Boolean(r))
      const entries: Array<{ cid: string; colKey: string }> = []
      for (const row of targetRows) {
        const cid = String(row._cid ?? '')
        if (!cid) continue
        for (const col of styleCols) entries.push({ cid, colKey: col.key })
      }
      if (entries.length > 0) engine.styleManager.batchSet(entries, style)
    } else if (ac) {
      // 단일 셀 선택 → 해당 셀만 적용
      const colKey = visCols[ac.col]?.key
      if (!colKey) return
      const row = rows[ac.row]
      const cid = String(row?._cid ?? '')
      if (cid) engine.styleManager.setStyle(cid, colKey, style)
    }
    engine.refresh()
    showPhotoToast('서식 적용 완료', true)
  }, [showPhotoToast])

  /* ── Read current active cell style (for toggle) ── */
  const getCurrentStyle = useCallback((): CellStyle => {
    const engine = engineRef.current
    if (!engine) return {}
    const rows = displayRowsRef.current
    const visCols = engine.getVisibleCols()
    const selectedRowSet = engine.selection.getSelectedRows()
    const ac = engine.selection.getActiveCell()
    // Prefer first selected row, fallback to active cell
    let cid = ''
    let colKey = ''
    if (selectedRowSet.size > 0) {
      const firstRowIdx = [...selectedRowSet][0]
      const row = rows[firstRowIdx]
      cid = String(row?._cid ?? '')
      // use first non-system col
      const firstCol = visCols.find(c => c.key !== 'rowNum' && c.key !== 'photo')
      colKey = firstCol?.key ?? ''
    } else if (ac) {
      const row = rows[ac.row]
      cid = String(row?._cid ?? '')
      colKey = visCols[ac.col]?.key ?? ''
    }
    if (!cid || !colKey) return {}
    return engine.styleManager.getStyle(cid, colKey) ?? {}
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
          // 기본 정보
          email: 'email', name: 'full_name', nationality: 'nationality',
          background: 'ancestry', age: 'dob', gender: 'gender',
          currentLoc: 'current_location', startDate: 'start_date',
          university: 'target', prefRegion: 'area_prefs',
          totalExp: 'experience', employment: 'employment', source: 'how_to',
          // 급여·채용
          curSalary: 'current_salary', hopeSalary: 'desired_salary',
          hired: 'placed_company', wage: 'placed_salary',
          moveIn: 'start_month', housingCost: 'housing_detail',
          // 자격·서류
          degree: 'education_level', major: 'major', cert: 'certification',
          docs: 'doc_status', health: 'health_info',
          e2visa: 'visa_type', crimCheck: 'criminal_record_check',
          domesticCrim: 'korean_criminal_record',
          // 연락처·기타
          kakao: 'kakaotalk', phone: 'mobile_phone',
          arc: 'arc_holders', married: 'married', religion: 'religion',
          family: 'dependents', tattooPiercing: 'tattoo',
          infoProvide: 'consent', verified: 'fact_check',
          interviewCol: 'interview_time',
          // 관리 필드
          reference: 'reference', proposal: 'recruiter_memo',
          notice: 'dislikes', preference: 'preferences',
          applied: 'job_prefs', contractOffer: 'contract_offered',
          personalNote: 'personal_consideration', history: 'past_placement',
          housing: 'housing', introFee: 'referral_fee',
          process: 'process_date',
        }
        const dbField = fieldMap[colKey]
        if (dbField) saveToServer(cid, dbField, value)
      }
    },
    onCellClick: (_rowIdx: number, colKey: string, row: DataRow) => {
      if (colKey === 'resumeStatus' && row.resumeStatus === 'done' && row._cid) {
        window.open(`${API}/api/admin/candidates/${row._cid}/processed-cv`, '_blank')
      }
    },
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
    onRequestMore: () => {
      // 이미 로딩 중이거나 전체 완료 시 무시
      if (isLoadingMoreRef.current) return
      if (dbTotalRef.current > 0 && dbAllRef.current.length >= dbTotalRef.current) return
      // 미완료 데이터가 있으면 전체 로드 재개
      if (dbAllRef.current.length < dbTotalRef.current) loadAllData()
    },
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
        // DB PATCH
        fetch(`${API}/api/admin/candidates/${encodeURIComponent(cid)}`, {
          method: 'PATCH',
          headers: { ...hdrsRef.current(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ stage }),
        }).catch(() => {})
      }
      // 상태별 행 색상 자동 적용
      const stageInfo = STAGES.find(s => s.key === stage)
      if (stageInfo && stageInfo.key !== 'none' && cid) {
        const engine = engineRef.current
        if (engine) {
          const visCols = engine.getVisibleCols()
          const styleCols = visCols.filter(c => c.key !== 'rowNum' && c.key !== 'photo')
          const entries = styleCols.map(c => ({ cid, colKey: c.key }))
          engine.styleManager.batchSet(entries, { bgColor: stageInfo.color + '18' })
          engine.refresh()
        }
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
        // DB PATCH
        fetch(`${API}/api/admin/candidates/${encodeURIComponent(cid)}`, {
          method: 'PATCH',
          headers: { ...hdrsRef.current(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ mail_tags: ms }),
        }).catch(() => {})
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
      setFilterSearch('')
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
    // 열 드래그 순서 변경 콜백
    engine.onColReorder = (newCols) => {
      setCols(newCols.filter(c => defaultCols().some(d => d.key === c.key)) as typeof newCols)
      prefsRef.current.save(newCols as ColDef[], frozenCols)
    }
    engineRef.current = engine
    // 엔진 생성 직후 초기 데이터 동기화 (race condition 방지)
    engine.setCols(cols)
    engine.setData(displayRows)
    engine.setFrozenCols(frozenCols)
    engine.setSort(sortKey, sortDir)
    engine.setRowHeight(rowHeight)
    engine.setRowHeights(rowHeights)
    engine.setActiveFilters(filters)
    return () => { engine.destroy(); engineRef.current = null }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready])

  /* ── Sync data/cols/sort/rowHeight/filters to engine ── */
  useEffect(() => {
    const e = engineRef.current
    if (!e) return
    e.setCols(cols)
    e.setData(displayRows)
    e.setFrozenCols(frozenCols)
    e.setSort(sortKey, sortDir)
    e.setRowHeight(rowHeight)
    e.setRowHeights(rowHeights)
    e.setActiveFilters(filters)
  }, [ready, displayRows, cols, frozenCols, sortKey, sortDir, rowHeight, rowHeights, filters])

  /* ── Context menu ── */
  const ctxAction = useCallback((action: string) => {
    if (!ctx) return
    const { row } = ctx
    const cid = String(row._cid ?? '')
    pushHistory()
    switch (action) {
      case 'to_active': case 'to_past': case 'to_blacklist': {
        const newCat = action.replace('to_', '') as CategoryKey
        // 선택된 모든 행 이동 (단일행이면 ctx.row만)
        const engine = engineRef.current
        const selRows = engine?.selection.getSelectedRows() ?? new Set<number>()
        const targetCids = new Set<string>()
        if (selRows.size > 1) {
          for (const ri of selRows) {
            const r = displayRowsRef.current[ri]
            if (r) targetCids.add(String(r._cid ?? ''))
          }
        } else {
          targetCids.add(cid)
        }
        setDbAll(prev => prev.map(r => targetCids.has(String(r._cid ?? '')) ? { ...r, category: newCat } : r))
        setData(prev => {
          const u: DataStore = { active: [], past: [], blacklist: [] }
          for (const k of ['active', 'past', 'blacklist'] as CategoryKey[])
            u[k] = prev[k].filter(r => !targetCids.has(String(r._cid ?? '')))
          for (const tc of targetCids) {
            const found = dbAllRef.current.find(r => String(r._cid ?? '') === tc)
            if (found) u[newCat].push({ ...found, category: newCat })
          }
          return u
        })
        const edits = editsRef.current
        for (const tc of targetCids) {
          edits[tc] = { ...(edits[tc] || {}), category: newCat } as EditOverride
          // DB에도 category PATCH (status 필드)
          if (tc) {
            fetch(`${API}/api/admin/candidates/${encodeURIComponent(tc)}`, {
              method: 'PATCH',
              headers: { ...hdrsRef.current(), 'Content-Type': 'application/json' },
              body: JSON.stringify({ status: newCat === 'active' ? 'Active' : newCat === 'past' ? 'Past' : 'Blacklist' }),
            }).catch(() => {})
          }
        }
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
      case 'photo_upload':
        photoTargetRef.current = ctx.rowIdx
        photoRef.current?.click()
        return  // don't setCtx(null) — file dialog takes over
      case 'photo_delete': {
        setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, photoUrl: '' } : r))
        if (cid) {
          fetch(`${API}/api/admin/candidates/${cid}`, {
            method: 'PATCH',
            headers: { ...hdrsRef.current(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ photo_url: '' }),
          }).catch(() => {})
          const edits = editsRef.current
          edits[cid] = { ...(edits[cid] || {}), photoUrl: '' } as EditOverride
          prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
        }
        showPhotoToast('사진 삭제 완료')
        break
      }
      case 'add_row': {
        const newId = Math.max(...dbAllRef.current.map(r => r.id), 0) + 1
        const tt: CategoryKey = (tab === 'all' || tab === 'focus') ? 'active' : tab as CategoryKey
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
    const tt: CategoryKey = (tab === 'all' || tab === 'focus') ? 'active' : tab as CategoryKey
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

  /* ── Client-side Export (현재 보기 기준: 필터·정렬·컬럼순서 반영) ── */
  const exportClientSide = useCallback((format: 'csv' | 'xlsx') => {
    try {
      // photo/idx 컬럼 제외, 현재 표시 중인 컬럼만, 순서대로
      const exportCols = cols.filter(c => c.v !== false && c.key !== 'idx' && c.key !== 'photo' && c.key !== 'mail')
      const headers = exportCols.map(c => c.label)
      const rowData = displayRowsRef.current.map(row =>
        exportCols.map(c => {
          const v = row[c.key]
          return v == null ? '' : String(v)
        })
      )
      const today = new Date().toISOString().slice(0, 10)
      const filterCount = Object.keys(filters).length
      const suffix = filterCount > 0 ? `_필터${filterCount}` : ''
      const filename = `bridge_${today}${suffix}`

      if (format === 'csv') {
        const escape = (s: string) => `"${s.replace(/"/g, '""')}"`
        const lines = [headers, ...rowData].map(r => r.map(escape).join(','))
        const blob = new Blob(['\uFEFF' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' })
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = `${filename}.csv`
        a.click()
        URL.revokeObjectURL(a.href)
      } else {
        const ws = XLSX.utils.aoa_to_sheet([headers, ...rowData])
        // 컬럼 너비 자동 설정 (최대 40자)
        ws['!cols'] = exportCols.map(c => ({ wch: Math.min(40, Math.max(10, c.label.length + 4)) }))
        const wb = XLSX.utils.book_new()
        XLSX.utils.book_append_sheet(wb, ws, 'Candidates')
        XLSX.writeFile(wb, `${filename}.xlsx`)
      }
    } catch (e) {
      console.error('Export failed:', e)
      alert('내보내기에 실패했습니다.')
    }
  }, [cols, filters])
  const exportCsv = useCallback(() => exportClientSide('csv'), [exportClientSide])
  const exportXlsx = useCallback(() => exportClientSide('xlsx'), [exportClientSide])

  /* ── Delete rows ── */
  const deleteRows = useCallback(async (rowIndices: Set<number>) => {
    if (rowIndices.size === 0) return
    const rows = displayRowsRef.current
    const cidsToDelete = new Set([...rowIndices].map(i => String(rows[i]?._cid ?? '')).filter(Boolean))
    if (cidsToDelete.size === 0) return
    // 세션 중 삭제 CID 추적 — 리로드 시에도 복원 방지
    for (const cid of cidsToDelete) deletedCidsRef.current.add(cid)
    pushHistory()
    setDbAll(prev => prev.filter(r => !cidsToDelete.has(String(r._cid ?? ''))))
    setData(prev => {
      const u: DataStore = { active: [], past: [], blacklist: [] }
      for (const k of ['active', 'past', 'blacklist'] as CategoryKey[])
        u[k] = prev[k].filter(r => !cidsToDelete.has(String(r._cid ?? '')))
      return u
    })
    // Soft-delete via DELETE endpoint (sets status='Deleted')
    let failCount = 0
    for (const cid of cidsToDelete) {
      if (!cid) continue
      try {
        const res = await fetch(`${API}/api/admin/candidates/${encodeURIComponent(cid)}`, {
          method: 'DELETE',
          headers: hdrsRef.current(),
        })
        if (!res.ok) failCount++
      } catch { failCount++ }
    }
    if (failCount > 0) showPhotoToast(`삭제 실패 ${failCount}건 — 새로고침 후 재시도`, false)
    else showPhotoToast(`${cidsToDelete.size}건 삭제 완료`, true)
  }, [pushHistory, showPhotoToast])

  /* ── Full reload ── */
  const fullReload = useCallback(() => { setDbAll([]); setLoaded(0); loadAllData() }, [loadAllData])

  /* ── Memo save ── */
  const saveMemo = useCallback((m: string, s: { fontSize: number; bold: boolean; color: string; bgColor: string }) => {
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
      } else if (t.key === 'focus') {
        c[t.key] = dbAll.length > 0
          ? dbAll.filter(isFocusRow).length
          : (data.active?.filter(r => FOCUS_STAGES.has(r.stage as string)).length || 0) + (data.past?.length || 0)
      } else {
        c[t.key] = dbAll.length > 0
          ? dbAll.filter(r => r.category === t.key).length
          : (data[t.key]?.length ?? 0)
      }
    }
    return c
  }, [dbAll, data])

  /* ── Pipeline 상태표시줄 데이터 ── */
  const PIPELINE_STAGES = useMemo(() => [
    { key: 'interview', label: '인터뷰 대기', color: '#d97706' },
    { key: 'proposal',  label: '제안 중',    color: '#ca8a04' },
    { key: 'signed',    label: '서명 완료',  color: '#16a34a' },
    { key: 'guide_sent',label: '배치 대기',  color: '#2563eb' },
    { key: 'guide_done',label: '완료',       color: '#1d4ed8' },
  ], [])

  const pipelineData = useMemo(() => {
    const src = dbAll.length > 0 ? dbAll : [...(data.active || []), ...(data.past || []), ...(data.blacklist || [])]
    const result: Record<string, { total: number; byCompany: Array<{ company: string; candidates: DataRow[] }> }> = {}
    for (const ps of PIPELINE_STAGES) {
      const rows = src.filter(r => r.stage === ps.key)
      // 업체별 그룹핑: proposal 첫 줄에서 회사명 추출
      const companyMap = new Map<string, DataRow[]>()
      for (const r of rows) {
        const prop = String(r.proposal || r.hired || '').trim()
        const firstLine = prop.split(/[\n\r]/)[0].trim()
        const match = firstLine.match(/^([^:\-\(\)]{2,25})/)
        const company = (match ? match[1].trim() : '') || (r.hired ? String(r.hired).trim() : '미분류')
        if (!companyMap.has(company)) companyMap.set(company, [])
        companyMap.get(company)!.push(r)
      }
      result[ps.key] = {
        total: rows.length,
        byCompany: Array.from(companyMap.entries()).map(([company, candidates]) => ({ company, candidates })),
      }
    }
    return result
  }, [dbAll, data, PIPELINE_STAGES])

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

  /* ── Column reorder (left / right) ── */
  const moveColLeft = useCallback((colKey: string) => {
    setCols(prev => {
      const visCols = prev.filter(c => c.v !== false)
      const visIdx = visCols.findIndex(c => c.key === colKey)
      if (visIdx <= 0) return prev  // already leftmost or not found
      // swap with previous visible column
      const swapKey = visCols[visIdx - 1].key
      const allIdx = prev.findIndex(c => c.key === colKey)
      const swapAllIdx = prev.findIndex(c => c.key === swapKey)
      if (allIdx < 0 || swapAllIdx < 0) return prev
      const next = [...prev]
      ;[next[allIdx], next[swapAllIdx]] = [next[swapAllIdx], next[allIdx]]
      return next
    })
    setHeaderMenu(null)
  }, [])

  const moveColRight = useCallback((colKey: string) => {
    setCols(prev => {
      const visCols = prev.filter(c => c.v !== false)
      const visIdx = visCols.findIndex(c => c.key === colKey)
      if (visIdx < 0 || visIdx >= visCols.length - 1) return prev  // already rightmost
      const swapKey = visCols[visIdx + 1].key
      const allIdx = prev.findIndex(c => c.key === colKey)
      const swapAllIdx = prev.findIndex(c => c.key === swapKey)
      if (allIdx < 0 || swapAllIdx < 0) return prev
      const next = [...prev]
      ;[next[allIdx], next[swapAllIdx]] = [next[swapAllIdx], next[allIdx]]
      return next
    })
    setHeaderMenu(null)
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

      {/* ── 사진 업로드 토스트 ── */}
      {photoToast && (
        <div style={{
          position: 'fixed', bottom: 28, left: '50%', transform: 'translateX(-50%)',
          zIndex: 99999, padding: '10px 22px', borderRadius: 24,
          background: photoToast.ok ? '#16a34a' : '#dc2626',
          color: '#fff', fontSize: 14, fontWeight: 600,
          boxShadow: '0 4px 20px rgba(0,0,0,0.25)',
          pointerEvents: 'none', whiteSpace: 'nowrap',
          animation: 'fadeInUp 0.2s ease',
        }}>
          {photoToast.msg}
        </div>
      )}

      {/* ── 신규 접수 알림 배너 ── */}
      {newBanner > 0 && !bannerDismissed && (
        <div
          onClick={() => { setTab('active'); setBannerDismissed(true); setNewBanner(0) }}
          style={{
            flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
            padding: '8px 20px',
            background: '#dc2626',
            color: '#fff',
            fontSize: 13, fontWeight: 700,
            cursor: 'pointer',
            animation: 'bridge-blink 1.2s step-end infinite',
          }}
        >
          <span>신규 접수 {newBanner}건 — 클릭하여 확인</span>
          <span
            onClick={e => { e.stopPropagation(); setBannerDismissed(true); setNewBanner(0) }}
            style={{ marginLeft: 8, fontSize: 16, lineHeight: 1, opacity: 0.8, cursor: 'pointer' }}
          >✕</span>
        </div>
      )}
      <style>{`
        @keyframes bridge-blink { 0%,100%{opacity:1} 50%{opacity:0.6} }
        @keyframes fadeInUp { from { opacity:0; transform:translateX(-50%) translateY(12px) } to { opacity:1; transform:translateX(-50%) translateY(0) } }
      `}</style>

      {/* ── Pipeline 상태표시줄 ── */}
      <div style={{
        flexShrink: 0, background: '#fff', borderBottom: '1px solid #e5e7eb',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* 버튼 행 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: '#9ca3af', marginRight: 4, letterSpacing: 1.5 }}>
            PIPELINE
          </span>
          {PIPELINE_STAGES.map(ps => {
            const pd = pipelineData[ps.key]
            const isOpen = pipelineStage === ps.key
            const cnt = pd?.total ?? 0
            return (
              <button
                key={ps.key}
                onClick={() => setPipelineStage(isOpen ? null : ps.key)}
                style={{
                  padding: '4px 14px', fontSize: 13, fontWeight: 500, border: 'none', borderRadius: 6,
                  cursor: 'pointer', transition: 'all 0.15s',
                  background: isOpen ? `${ps.color}18` : '#f5f5f7',
                  color: isOpen ? ps.color : '#555',
                  outline: isOpen ? `1.5px solid ${ps.color}50` : 'none',
                  display: 'flex', alignItems: 'center', gap: 6,
                }}
              >
                {ps.label}
                <span style={{
                  fontSize: 12, fontWeight: 600,
                  background: cnt > 0 ? (isOpen ? `${ps.color}20` : '#e5e7eb') : 'transparent',
                  color: cnt > 0 ? (isOpen ? ps.color : '#374151') : '#ccc',
                  padding: cnt > 0 ? '1px 7px' : '0',
                  borderRadius: 10, minWidth: 18, textAlign: 'center' as const,
                }}>
                  {cnt}
                </span>
              </button>
            )
          })}
          {pipelineStage && (
            <button
              onClick={() => setPipelineStage(null)}
              style={{ marginLeft: 'auto', fontSize: 14, color: '#9ca3af', background: 'none', border: 'none', cursor: 'pointer', lineHeight: 1 }}
            >
              ✕
            </button>
          )}
        </div>

        {/* 펼쳐진 패널 */}
        {pipelineStage && pipelineData[pipelineStage] && (
          <div style={{
            padding: '6px 12px 8px',
            background: '#f9fafb',
            borderTop: '1px solid #f3f4f6',
            display: 'flex', flexWrap: 'wrap', gap: '6px 16px',
            maxHeight: 120, overflowY: 'auto',
          }}>
            {pipelineData[pipelineStage].byCompany.length === 0 ? (
              <span style={{ fontSize: 12, color: '#9ca3af' }}>해당 단계 후보자 없음</span>
            ) : pipelineData[pipelineStage].byCompany.map(({ company, candidates }) => (
              <div key={company} style={{ display: 'flex', alignItems: 'baseline', gap: 6, flexShrink: 0 }}>
                <span style={{ fontSize: 11, fontWeight: 500, color: '#6b7280', maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {company}
                </span>
                <span style={{ fontSize: 10, color: '#d1d5db' }}>—</span>
                {candidates.map(c => (
                  <button
                    key={c._cid || c.id}
                    onClick={() => {
                      setQ(String(c.mgtNum || c.name || ''))
                    }}
                    style={{
                      fontSize: 11, fontWeight: 500, padding: '1px 6px',
                      background: '#fff', border: '1px solid #e5e7eb',
                      borderRadius: 4, color: '#374151', cursor: 'pointer',
                    }}
                    title={`${c.name} (${c.nationality})`}
                  >
                    #{c.mgtNum || c.id}
                  </button>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

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
        {fetchError && (
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ color: '#dc2626', fontSize: 12, fontWeight: 600 }}>⚠ {fetchError}</span>
            <button
              onClick={() => { setFetchError(null); loadAllData() }}
              style={{ fontSize: 12, color: '#2563eb', cursor: 'pointer', background: 'none', border: '1px solid #2563eb', borderRadius: 4, padding: '2px 8px', fontWeight: 600 }}
            >
              재시도
            </button>
          </span>
        )}
        {lastSync && !fetchError && <span style={{ fontSize: 11, fontWeight: 600, color: '#666' }}> · {lastSync}</span>}
        {newCount > 0 && <span style={{ fontSize: 13, fontWeight: 700, color: '#ef4444' }}> · 신규 {newCount}</span>}

        {/* 활성 필터 배지 */}
        {Object.keys(filters).length > 0 && (
          <span style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '3px 10px', background: '#eff6ff', border: '1px solid #93c5fd', borderRadius: 6, fontSize: 12 }}>
            <span style={{ color: '#2563eb', fontWeight: 700 }}>필터 {Object.keys(filters).length}개 적용</span>
            <span
              onClick={() => setFilters({})}
              style={{ color: '#2563eb', cursor: 'pointer', fontWeight: 700, marginLeft: 2 }}
              title="전체 필터 초기화"
            >×</span>
          </span>
        )}

        <div style={{ flex: 1 }} />

        {selectedRows.size > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px', background: '#f1f5f9', borderRadius: 8, border: '1px solid #e2e8f0' }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#334155', marginRight: 4 }}>선택 {selectedRows.size}명</span>
            <button
              onClick={() => { const rows = [...selectedRows].map(i => displayRowsRef.current[i]).filter(Boolean); if (rows.length) openMailModal(rows) }}
              style={{ padding: '5px 14px', fontSize: 13, fontWeight: 600, borderRadius: 6, border: '1px solid #cbd5e1', cursor: 'pointer', background: '#fff', color: '#1e293b' }}
            >메일 발송</button>
            <button
              onClick={() => {
                const row = displayRowsRef.current[[...selectedRows][0]]
                if (!row) return
                setIvType('bridge'); setIvTarget(row); setIvEmployerName('')
                const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1)
                setIvDate(tomorrow.toISOString().slice(0, 10))
                const prefs = loadIvPrefs()
                setIvTime(prefs.time); setIvDuration(prefs.duration); setIvAutoSend(prefs.autoSend)
                setIvNotes(''); setIvResult(null)
                setIvMeetLink(pickRandomMeet())
                setIvModal(true)
              }}
              style={{ padding: '5px 14px', fontSize: 13, fontWeight: 600, borderRadius: 6, border: '1px solid #cbd5e1', cursor: 'pointer', background: '#1e293b', color: '#fff' }}
            >브릿지 인터뷰</button>
            <button
              onClick={() => {
                const row = displayRowsRef.current[[...selectedRows][0]]
                if (!row) return
                setIvType('school'); setIvTarget(row); setIvEmployerName('')
                const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1)
                setIvDate(tomorrow.toISOString().slice(0, 10))
                const prefs = loadIvPrefs()
                setIvTime(prefs.time); setIvDuration(prefs.duration); setIvAutoSend(prefs.autoSend)
                setIvNotes(''); setIvResult(null)
                setIvMeetLink(pickRandomMeet())
                setIvModal(true)
              }}
              style={{ padding: '5px 14px', fontSize: 13, fontWeight: 600, borderRadius: 6, border: '1px solid #cbd5e1', cursor: 'pointer', background: '#fff', color: '#1e293b' }}
            >학교 인터뷰</button>
            <button
              onClick={() => {
                const nums = [...selectedRows]
                  .map(i => displayRowsRef.current[i])
                  .filter(Boolean)
                  .map(r => r.sheet_number)
                  .filter(n => n != null && String(n).trim() !== '')
                  .map(n => String(n))
                if (nums.length === 0) { alert('sheet_number가 있는 행을 선택하세요.'); return }
                window.open(`/admin/introduce-mail?candidates=${encodeURIComponent(nums.join(','))}`, '_blank')
              }}
              style={{ padding: '5px 14px', fontSize: 13, fontWeight: 600, borderRadius: 6, border: '1px solid #0ea5e9', cursor: 'pointer', background: '#0ea5e9', color: '#fff' }}
            >소개발송</button>
          </div>
        )}

        <button onClick={() => setFrozenCols(p => p === 0 ? 3 : 0)} style={tbBtn}>{frozenCols > 0 ? '🔒 고정' : '🔓 해제'}</button>
        <button onClick={fullReload} style={tbBtn}>↻ DB동기화</button>
        <button
          onClick={exportCsv}
          style={tbBtn}
          title={`현재 보기 ${displayRowsRef.current.length}건 CSV 내보내기`}
        >↓CSV</button>
        <button
          onClick={exportXlsx}
          style={tbBtn}
          title={`현재 보기 ${displayRowsRef.current.length}건 Excel 내보내기`}
        >↓Excel</button>
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

        {/* B / I / S — toggle style */}
        <button onClick={() => { const cur = getCurrentStyle(); applyStyleToSelection({ bold: !cur.bold }) }} style={{ ...fmtBtn, fontWeight: 700 }} title="Bold (Ctrl+B)">B</button>
        <button onClick={() => { const cur = getCurrentStyle(); applyStyleToSelection({ italic: !cur.italic }) }} style={{ ...fmtBtn, fontStyle: 'italic' }} title="Italic (Ctrl+I)">I</button>
        <button onClick={() => { const cur = getCurrentStyle(); applyStyleToSelection({ strikethrough: !cur.strikethrough }) }} style={{ ...fmtBtn, textDecoration: 'line-through' }} title="취소선">S</button>

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

        <div style={{ display: 'flex', alignItems: 'center', gap: 4, borderLeft: '1px solid #ddd', paddingLeft: 8 }}>
          <span style={{ fontSize: 11, color: '#555', whiteSpace: 'nowrap' }}>행높이</span>
          <input
            type="number" min={4} max={400}
            value={rowHeight}
            onChange={e => {
              const v = Number(e.target.value)
              if (v >= 4 && v <= 400) {
                setRowHeight(v)
                setRowHeights({})
                prefsRef.current.saveRowHeights({})
              }
            }}
            style={{ width: 44, height: 22, textAlign: 'center', border: '1px solid #ddd', borderRadius: 3, fontSize: 11 }}
          />
          <span style={{ fontSize: 11, color: '#555', whiteSpace: 'nowrap', marginLeft: 4 }}>열너비</span>
          <input
            type="number" min={4} max={600}
            placeholder="일괄"
            onKeyDown={e => {
              if (e.key === 'Enter') {
                const v = Number((e.target as HTMLInputElement).value)
                if (v >= 4 && v <= 600) {
                  setCols(prev => prev.map(c => c.type === 'idx' ? c : { ...c, w: v }))
                }
              }
            }}
            style={{ width: 44, height: 22, textAlign: 'center', border: '1px solid #ddd', borderRadius: 3, fontSize: 11 }}
          />
        </div>
      </div>

      {/* ── Memo Area ── */}
      <div style={{
        flexShrink: 0, background: memoStyle.bgColor || '#FFFDE7',
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
          <input
            type="color" value={memoStyle.bgColor || '#FFFDE7'}
            onChange={e => { const s = { ...memoStyle, bgColor: e.target.value }; setMemoStyle(s); saveMemo(memo, s) }}
            style={{ width: 22, height: 22, border: 'none', padding: 0, cursor: 'pointer' }}
            title="메모 배경색"
          />
          <button
            onClick={() => { setMemo(''); saveMemo('', memoStyle) }}
            style={{ marginLeft: 4, padding: '1px 6px', fontSize: 11, border: '1px solid #e0d78a', borderRadius: 3, background: 'transparent', cursor: 'pointer', color: '#b45309' }}
            title="메모 초기화"
          >지우기</button>
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
            position: 'fixed', left: ctx.x, top: ctx.y, zIndex: 9999,
            background: '#fff', borderRadius: 8,
            boxShadow: '0 8px 24px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.10)',
            padding: '4px 0', minWidth: 200, border: 'none',
          }}
          onClick={e => e.stopPropagation()}
        >
          {/* 행 조작 */}
          <CtxItem label="위에 행 삽입" onClick={() => {
            const cid = String(ctx.row._cid ?? '')
            pushHistory()
            const tt: CategoryKey = (tab === 'all' || tab === 'focus') ? 'active' : tab as CategoryKey
            const newRow: DataRow = { id: 0, _cid: '', category: tt, stage: 'none', mailStatus: '', photoUrl: '', photoSize: 50 }
            defaultCols().forEach(c => { if (!['rowNum','stage','mailStatus','photo'].includes(c.key) && !(c.key in newRow)) (newRow as Record<string, unknown>)[c.key] = '' })
            setDbAll(prev => { const idx = prev.findIndex(r => r._cid === cid); if (idx >= 0) { const a = [...prev]; a.splice(idx, 0, newRow); return a }; return [newRow, ...prev] })
            setCtx(null)
          }} />
          <CtxItem label="아래에 행 삽입" onClick={() => ctxAction('add_row')} />
          <CtxItem label="행 삭제" onClick={() => {
            const engine = engineRef.current
            const selRows = engine?.selection.getSelectedRows() ?? new Set<number>()
            const rowsToDelete = selRows.size > 0 ? selRows : new Set([ctx.rowIdx])
            deleteRows(rowsToDelete)
            setCtx(null)
          }} />
          <div style={{ height: 1, background: '#f3f4f6', margin: '3px 0' }} />
          {/* 셀 조작 */}
          <CtxItem label="셀 복사" onClick={() => {
            const engine = engineRef.current
            const ac = engine?.selection.getActiveCell()
            if (!ac) return
            const visCols = engine!.getVisibleCols()
            const col = visCols[ac.col]
            if (col) navigator.clipboard.writeText(String(ctx.row[col.key] ?? '')).catch(() => {})
            setCtx(null)
          }} />
          <CtxItem label="셀 지우기" onClick={() => {
            const engine = engineRef.current
            const ac = engine?.selection.getActiveCell()
            if (!ac) return
            const visCols = engine!.getVisibleCols()
            const col = visCols[ac.col]
            if (col) stableCallbacks.onCellChange(ctx.rowIdx, col.key, '')
            setCtx(null)
          }} />
          <div style={{ height: 1, background: '#f3f4f6', margin: '3px 0' }} />
          {/* 사진 */}
          <CtxItem label="📷 사진 파일 선택..." onClick={() => ctxAction('photo_upload')} />
          {ctx.row.photoUrl && <CtxItem label="🗑 사진 삭제" onClick={() => ctxAction('photo_delete')} />}
          <div style={{ height: 1, background: '#f3f4f6', margin: '3px 0' }} />
          {/* 틀고정 */}
          <CtxItem label={frozenCols > 0 ? '틀 고정 해제' : '틀 고정 설정'} onClick={() => { setFrozenCols(p => p === 0 ? 3 : 0); setCtx(null) }} />
          <div style={{ height: 1, background: '#f3f4f6', margin: '3px 0' }} />
          {/* 메일 & 복사 */}
          <CtxItem label="메일 발송" onClick={() => ctxAction('mail')} />
          <CtxItem label="행 복사 (탭구분)" onClick={() => ctxAction('copy_row')} />
          <CtxItem label="이메일 주소 복사" onClick={() => ctxAction('copy_email')} />
          <div style={{ height: 1, background: '#f3f4f6', margin: '3px 0' }} />
          {/* 탭 이동 */}
          <CtxItem label="구직자 탭으로 이동" onClick={() => ctxAction('to_active')} />
          <CtxItem label="체결완료 탭으로 이동" onClick={() => ctxAction('to_past')} />
          <CtxItem label="블랙리스트로 이동" onClick={() => ctxAction('to_blacklist')} />
          <div style={{ height: 1, background: '#f3f4f6', margin: '3px 0' }} />
          {/* 진행단계 */}
          {STAGES.filter(s => s.key !== 'none').map(s => (
            <CtxItem key={s.key} label={`→ ${s.label}`} onClick={() => {
              const cid = String(ctx.row._cid ?? '')
              pushHistory()
              setDbAll(prev => prev.map(r => r._cid === cid ? { ...r, stage: s.key } : r))
              const edits = editsRef.current
              edits[cid] = { ...(edits[cid] || {}), stage: s.key } as EditOverride
              prefsRef.current.saveEdits(edits as Record<string, Record<string, string>>)
              if (cid) {
                fetch(`${API}/api/admin/candidates/${encodeURIComponent(cid)}`, {
                  method: 'PATCH',
                  headers: { ...hdrsRef.current(), 'Content-Type': 'application/json' },
                  body: JSON.stringify({ stage: s.key }),
                }).catch(() => {})
              }
              setCtx(null)
            }} />
          ))}
        </div>
      )}

      {/* ── Filter Popup ── */}
      {filterPopup && (() => {
        const allOpts = getFilterOptions(filterPopup.colKey)
        const visOpts = filterSearch ? allOpts.filter(o => o.toLowerCase().includes(filterSearch.toLowerCase())) : allOpts
        const activeSet = filters[filterPopup.colKey] ?? new Set<string>()
        const allChecked = activeSet.size === 0  // 0 = no filter = "전체"
        // Viewport clamp: popup 228px wide, 340px max height
        const POPUP_W = 228, POPUP_H = 340
        const clampedLeft = Math.min(filterPopup.x, (typeof window !== 'undefined' ? window.innerWidth : 1200) - POPUP_W - 8)
        const clampedTop = Math.min(filterPopup.y, (typeof window !== 'undefined' ? window.innerHeight : 800) - POPUP_H - 8)
        return (
          <div
            onClick={e => e.stopPropagation()}
            style={{
              position: 'fixed', left: clampedLeft, top: clampedTop, zIndex: 200,
              background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8,
              boxShadow: '0 4px 24px rgba(0,0,0,0.14)', width: POPUP_W,
              display: 'flex', flexDirection: 'column', maxHeight: POPUP_H,
              fontFamily: '-apple-system,"Segoe UI",sans-serif',
            }}
          >
            {/* 헤더 */}
            <div style={{ padding: '8px 12px', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
              <b style={{ fontSize: 13, color: '#0f172a' }}>{cols.find(c => c.key === filterPopup.colKey)?.label}</b>
              {activeSet.size > 0 && (
                <span
                  onClick={() => setFilters(p => { const n = { ...p }; delete n[filterPopup.colKey!]; return n })}
                  style={{ fontSize: 12, color: '#2563eb', cursor: 'pointer', fontWeight: 600 }}
                >초기화</span>
              )}
            </div>
            {/* 검색창 (옵션 6개 초과 시) */}
            {allOpts.length > 6 && (
              <div style={{ padding: '6px 10px', borderBottom: '1px solid #f1f5f9', flexShrink: 0 }}>
                <input
                  autoFocus
                  value={filterSearch}
                  onChange={e => setFilterSearch(e.target.value)}
                  placeholder="검색..."
                  style={{
                    width: '100%', boxSizing: 'border-box', padding: '4px 8px',
                    border: '1px solid #cbd5e1', borderRadius: 5, fontSize: 12,
                    outline: 'none', color: '#334155',
                  }}
                />
              </div>
            )}
            {/* 전체 선택/해제 */}
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', cursor: 'pointer', fontSize: 13, borderBottom: '1px solid #f1f5f9', flexShrink: 0, fontWeight: 600, color: '#334155' }}>
              <input
                type="checkbox"
                checked={allChecked}
                onChange={() => {
                  if (!allChecked) {
                    setFilters(p => { const n = { ...p }; delete n[filterPopup.colKey!]; return n })
                  }
                }}
                style={{ width: 14, height: 14 }}
              />
              전체 ({allOpts.length})
            </label>
            {/* 옵션 목록 */}
            <div style={{ overflowY: 'auto', flex: 1 }}>
              {visOpts.length === 0 && (
                <div style={{ padding: '10px 12px', fontSize: 12, color: '#94a3b8', textAlign: 'center' }}>검색 결과 없음</div>
              )}
              {visOpts.map(opt => (
                <label key={opt} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px', cursor: 'pointer', fontSize: 13, color: '#334155' }}>
                  <input
                    type="checkbox"
                    checked={activeSet.has(opt)}
                    onChange={() => {
                      setFilters(prev => {
                        const s = prev[filterPopup.colKey!] ? new Set(prev[filterPopup.colKey!]) : new Set<string>()
                        if (s.has(opt)) s.delete(opt); else s.add(opt)
                        const n = { ...prev }
                        if (s.size === 0) delete n[filterPopup.colKey!]; else n[filterPopup.colKey!] = s
                        return n
                      })
                    }}
                    style={{ width: 14, height: 14 }}
                  />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{opt}</span>
                </label>
              ))}
            </div>
          </div>
        )
      })()}

      {/* ── Header Context Menu ── */}
      {headerMenu && (
        <div
          onClick={e => e.stopPropagation()}
          style={{
            position: 'fixed', left: headerMenu.x, top: headerMenu.y, zIndex: 9999,
            background: '#fff', borderRadius: 8,
            boxShadow: '0 8px 24px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.10)',
            padding: '4px 0', minWidth: 200, border: 'none',
          }}
        >
          <CtxItem label="열 숨기기" onClick={() => toggleColVisibility(headerMenu.colKey)} />
          <CtxItem label="열 너비 초기화" onClick={() => {
            const defW = defaultCols().find(c => c.key === headerMenu.colKey)?.w ?? 100
            setCols(prev => prev.map(c => c.key === headerMenu.colKey ? { ...c, w: defW } : c))
            setHeaderMenu(null)
          }} />
          {hiddenCount > 0 && (
            <CtxItem label="숨긴 열 모두 표시" onClick={() => { showAllCols(); setHeaderMenu(null) }} />
          )}
          <div style={{ height: 1, background: '#f3f4f6', margin: '3px 0' }} />
          <CtxItem label="열 왼쪽으로" onClick={() => moveColLeft(headerMenu.colKey)} />
          <CtxItem label="열 오른쪽으로" onClick={() => moveColRight(headerMenu.colKey)} />
          <div style={{ height: 1, background: '#f3f4f6', margin: '3px 0' }} />
          <CtxItem label={frozenCols > 0 ? '틀 고정 해제' : '이 열까지 틀 고정'} onClick={() => {
            if (frozenCols > 0) {
              setFrozenCols(0)
            } else {
              const visIdx = cols.filter(c => c.v !== false).findIndex(c => c.key === headerMenu.colKey)
              if (visIdx >= 0) setFrozenCols(visIdx + 1)
            }
            setHeaderMenu(null)
          }} />
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
                        fetch(`${API}/api/admin/candidates/${encodeURIComponent(cid)}`, {
                          method: 'PATCH',
                          headers: { ...hdrsRef.current(), 'Content-Type': 'application/json' },
                          body: JSON.stringify({ mail_tags: ms }),
                        }).catch(() => {})
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

      {/* ── Tabs (bottom) — drag-reorder + double-click rename ── */}
      <div style={{
        display: 'flex', gap: 0, flexShrink: 0,
        borderTop: '1px solid #e5e7eb', background: '#fff',
      }}>
        {orderedTabs.map(t => {
          const active = tab === t.key
          const displayLabel = tabLabels[t.key] || t.label
          const isDragging = dragTab === t.key
          return (
            <div
              key={t.key}
              draggable
              onDragStart={(e) => { setDragTab(t.key); e.dataTransfer.effectAllowed = 'move' }}
              onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move' }}
              onDrop={(e) => {
                e.preventDefault()
                if (!dragTab || dragTab === t.key) return
                const newOrder = [...tabOrder]
                const fromIdx = newOrder.indexOf(dragTab)
                const toIdx = newOrder.indexOf(t.key)
                if (fromIdx < 0 || toIdx < 0) return
                newOrder.splice(fromIdx, 1)
                newOrder.splice(toIdx, 0, dragTab)
                setTabOrder(newOrder)
                saveTabPrefs(newOrder, tabLabels)
                setDragTab(null)
              }}
              onDragEnd={() => setDragTab(null)}
              onClick={() => { if (!editingTab) { setTab(t.key); setSelectedRows(new Set()); setFilters({}) } }}
              onDoubleClick={(e) => { e.stopPropagation(); setEditingTab(t.key) }}
              style={{
                padding: '8px 18px', fontSize: 13, fontWeight: active ? 700 : 500,
                color: active ? '#1d1d1f' : '#6b7280',
                background: active ? '#fff' : isDragging ? '#f0f0f0' : 'transparent',
                border: 'none',
                borderTop: active ? `3px solid ${t.bg}` : '3px solid transparent',
                cursor: editingTab === t.key ? 'text' : 'pointer',
                transition: 'all 0.15s',
                display: 'flex', alignItems: 'center', gap: 6,
                opacity: isDragging ? 0.5 : 1,
                userSelect: 'none',
              }}
            >
              <span style={{ fontSize: 14 }}>{t.icon}</span>
              {editingTab === t.key ? (
                <input
                  autoFocus
                  defaultValue={displayLabel}
                  onBlur={(e) => {
                    const v = e.target.value.trim() || t.label
                    const next = { ...tabLabels, [t.key]: v === t.label ? undefined! : v }
                    if (v === t.label) delete next[t.key]
                    setTabLabels(next)
                    saveTabPrefs(tabOrder, next)
                    setEditingTab(null)
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
                    if (e.key === 'Escape') { setEditingTab(null) }
                  }}
                  onClick={(e) => e.stopPropagation()}
                  style={{
                    border: 'none', borderBottom: '1.5px solid #2563eb',
                    outline: 'none', fontSize: 13, fontWeight: 600, color: '#1d1d1f',
                    background: 'transparent', width: Math.max(40, displayLabel.length * 14),
                    padding: 0,
                  }}
                />
              ) : (
                <span>{displayLabel}</span>
              )}
              <span style={{
                fontSize: 11, fontWeight: 600,
                background: active ? `${t.bg}18` : '#f0f0f0',
                color: active ? t.bg : '#9ca3af',
                padding: '1px 8px', borderRadius: 10, minWidth: 20, textAlign: 'center' as const,
              }}>
                {tabCounts[t.key] ?? 0}
              </span>
            </div>
          )
        })}
        {loading && (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', paddingRight: 12, paddingLeft: 12 }}>
            <div style={{ flex: 1, height: 3, background: '#f3f4f6', borderRadius: 2 }}>
              <div style={{
                width: dbTotal > 0 ? `${(loaded / dbTotal) * 100}%` : '0%',
                height: '100%', background: '#3b82f6', borderRadius: 2, transition: 'width 0.3s',
              }} />
            </div>
          </div>
        )}
      </div>

      {/* ── Footer Legend ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '4px 12px',
        background: '#fff', borderTop: '1px solid #f3f4f6', fontSize: 11,
        fontWeight: 400, color: '#6b7280', flexShrink: 0,
      }}>
        {STAGES.filter(s => s.key !== 'none').map(s => (
          <span key={s.key} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: s.color, border: '1px solid #e5e7eb' }} />
            {s.label}
          </span>
        ))}
        <span style={{ marginLeft: 'auto' }}>
          {MTAGS.map(m => <span key={m.key} style={{ color: m.c, fontWeight: 500, marginLeft: 8 }}>{m.label}</span>)}
        </span>
      </div>

      {/* ── Interview Modal — Compact 2-column (Bridge / School) ── */}
      {ivModal && ivTarget && (() => {
        const pool = ivMeetPool.length ? ivMeetPool : loadMeetPool()
        const removeLink = (i: number) => {
          if (pool.length <= 1) return
          const np = pool.filter((_, idx) => idx !== i)
          setIvMeetPool(np); localStorage.setItem(MEET_POOL_KEY, JSON.stringify(np))
          if (pool[i] === ivMeetLink) setIvMeetLink(np[0])
        }
        const addLink = () => {
          const raw = ivNewLink.trim()
          if (!raw) return
          // 여러 줄 또는 공백으로 구분된 링크도 한번에 추가
          const links = raw.split(/[\n\r\s,]+/).map(s => s.trim()).filter(s => s.startsWith('http') && s.includes('meet.google.com/'))
          if (!links.length) return
          const unique = links.filter(l => !pool.includes(l))
          if (!unique.length) { setIvNewLink(''); return }
          const np = [...pool, ...unique]
          setIvMeetPool(np); localStorage.setItem(MEET_POOL_KEY, JSON.stringify(np))
          setIvNewLink('')
        }
        const getMeetCode = (url: string) => { const m = url.match(/meet\.(?:google\.com|jit\.si)\/([a-zA-Z0-9\-]+)/); return m ? m[1] : '' }
        const firstName = String(ivTarget.name || '').split(/\s+/).pop() || String(ivTarget.name || '-')
        const defaultSubject = `[BRIDGE] Interview — ${firstName}`
        const defaultBody = `Dear ${firstName},\n\nYour interview has been scheduled.\n\nDate: ${ivDate || '(TBD)'}\nTime: ${ivTime || '(TBD)'} KST\nDuration: ${ivDuration} minutes\n\nMeet Link: ${ivMeetLink}\n\nPlease join 2-3 minutes early.\n\nBest regards,\nBRIDGE Recruitment`
        const F = '"Pretendard Variable", Pretendard, -apple-system, "Noto Sans KR", "Malgun Gothic", sans-serif'
        const prefMemo = String(ivTarget.preference || ivTarget.applied || ivTarget.proposal || '')
        const datePreview = (() => {
          if (!ivDate || !ivTime) return null
          const d = new Date(`${ivDate}T${ivTime}`)
          const weekdays = ['일', '월', '화', '수', '목', '금', '토']
          const mo = d.getMonth() + 1, day = d.getDate(), wd = weekdays[d.getDay()]
          const [h, min] = ivTime.split(':').map(Number)
          const ampm = h < 12 ? '오전' : '오후'
          const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h
          return `${mo}월 ${day}일 (${wd}) ${ampm} ${h12}:${String(min).padStart(2,'0')} KST`
        })()
        return (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.35)', backdropFilter: 'blur(4px)', padding: 12 }}
          onClick={e => { if (e.target === e.currentTarget) setIvModal(false) }}>
          <div style={{ background: '#fff', borderRadius: 16, width: '96vw', maxWidth: 920, maxHeight: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 60px rgba(0,0,0,0.2)', overflow: 'hidden', fontFamily: F }}>

            {/* Header — date preview top + title */}
            <div style={{ padding: '14px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <span style={{ fontWeight: 600, fontSize: 18, color: '#000' }}>{ivType === 'school' ? '학교 인터뷰 생성' : '브릿지 인터뷰 생성'}</span>
                {datePreview && (
                  <span style={{ padding: '4px 14px', background: '#EEF2FF', border: '1px solid #C7D2FE', borderRadius: 8, fontSize: 15, fontWeight: 500, color: '#3730A3' }}>
                    {datePreview} &middot; {ivDuration}분
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <button onClick={() => setIvModal(false)} style={{ padding: '6px 16px', background: '#f3f4f6', color: '#000', borderRadius: 8, fontSize: 13, fontWeight: 500, border: 'none', cursor: 'pointer', fontFamily: F }}>취소</button>
                <button
                  disabled={ivLoading || !ivDate || !ivTime}
                  onClick={async () => {
                    setIvLoading(true)
                    try {
                      const emailSubject = (document.getElementById('iv-email-subject') as HTMLInputElement)?.value || defaultSubject
                      const emailBody = (document.getElementById('iv-email-body') as HTMLTextAreaElement)?.value || defaultBody
                      const res = await fetch(`${API}/api/admin/interviews`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
                        body: JSON.stringify({
                          candidate_name: ivTarget.name || '',
                          candidate_email: ivTarget.email || '',
                          candidate_id: ivTarget._cid || String(ivTarget.mgtNum || ''),
                          employer_name: ivType === 'school' ? ivEmployerName : '', employer_email: '',
                          interview_date: ivDate, interview_time: ivTime,
                          meet_link: ivMeetLink,
                          notes: ivNotes, duration_minutes: ivDuration,
                          auto_send_email: ivAutoSend && !!ivTarget.email,
                          email_subject: emailSubject,
                          email_body: emailBody,
                        }),
                      })
                      const json = await res.json()
                      if (!res.ok) throw new Error(json.detail ?? 'Failed')
                      setIvResult({ id: json.data?.id, emailSent: json.data?.email_result?.status === 'sent', meetLink: ivMeetLink })
                    } catch (e) { showPhotoToast(e instanceof Error ? e.message : 'Error') }
                    finally { setIvLoading(false) }
                  }}
                  style={{ padding: '6px 20px', borderRadius: 8, fontSize: 13, fontWeight: 600, border: 'none', cursor: 'pointer', fontFamily: F, background: ivLoading ? '#9ca3af' : '#000', color: '#fff', opacity: (!ivDate || !ivTime) ? 0.4 : 1 }}>
                  {ivLoading ? '생성중...' : '생성'}
                </button>
              </div>
            </div>

            <div style={{ flex: 1, overflow: 'auto', padding: '16px 24px' }}>
              {ivResult ? (
                <div style={{ textAlign: 'center', padding: '36px 0' }}>
                  <div style={{ fontSize: 56, marginBottom: 14 }}>✅</div>
                  <div style={{ fontWeight: 600, fontSize: 20, color: '#000' }}>인터뷰 #{ivResult.id} 생성 완료</div>
                  <div style={{ fontSize: 14, color: '#555', marginTop: 8 }}>
                    {ivResult.emailSent ? '후보자에게 이메일이 발송되었습니다' : '이메일은 별도로 발송해주세요'}
                  </div>
                  <div style={{ marginTop: 24, display: 'flex', gap: 10, justifyContent: 'center' }}>
                    <a href={ivResult.meetLink} target="_blank" rel="noopener noreferrer"
                      style={{ padding: '10px 24px', background: '#000', color: '#fff', borderRadius: 8, fontSize: 14, fontWeight: 500, textDecoration: 'none', fontFamily: F }}>Meet 참가</a>
                    <button onClick={() => setIvModal(false)}
                      style={{ padding: '10px 24px', background: '#f3f4f6', color: '#000', borderRadius: 8, fontSize: 14, fontWeight: 500, border: 'none', cursor: 'pointer', fontFamily: F }}>닫기</button>
                  </div>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                  {/* ═══ LEFT COLUMN ═══ */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {/* Candidate info — compact inline */}
                    <div style={{ background: '#f8f9fa', borderRadius: 10, padding: '14px 16px', border: '1px solid #eee' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 12px', fontSize: 13, alignItems: 'baseline' }}>
                        <span style={{ color: '#888' }}>번호</span><span style={{ color: '#000', fontWeight: 500 }}>#{ivTarget.mgtNum || ivTarget._cid || ivTarget.id}</span>
                        <span style={{ color: '#888' }}>이름</span><span style={{ color: '#000', fontWeight: 500 }}>{firstName}</span>
                        <span style={{ color: '#888' }}>국적</span><span style={{ color: '#000' }}>{String(ivTarget.nationality || '-')}</span>
                        <span style={{ color: '#888' }}>이메일</span><span style={{ color: '#000', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{String(ivTarget.email || '(없음)')}</span>
                        <span style={{ color: '#888' }}>시작일</span><span style={{ color: '#000' }}>{String(ivTarget.startDate || '-')}</span>
                      </div>
                      {prefMemo && (
                        <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #eee' }}>
                          <div style={{ fontSize: 11, color: '#888', marginBottom: 3 }}>메모 / 선호 인터뷰 시간</div>
                          <div style={{ fontSize: 13, color: '#000', lineHeight: 1.5, whiteSpace: 'pre-wrap', maxHeight: 80, overflow: 'auto' }}>{prefMemo}</div>
                        </div>
                      )}
                    </div>

                    {/* Employer name (school type only) */}
                    {ivType === 'school' && (
                      <div>
                        <label style={{ fontSize: 12, color: '#666', display: 'block', marginBottom: 4 }}>학교/학원명</label>
                        <input type="text" value={ivEmployerName} onChange={e => setIvEmployerName(e.target.value)} placeholder="업체명 입력"
                          style={{ width: '100%', padding: '10px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14, color: '#000', background: '#fff', boxSizing: 'border-box', fontFamily: F }} />
                      </div>
                    )}

                    {/* Date & Time */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                      <div>
                        <label style={{ fontSize: 12, color: '#666', display: 'block', marginBottom: 4 }}>날짜</label>
                        <input type="date" value={ivDate} onChange={e => setIvDate(e.target.value)}
                          style={{ width: '100%', padding: '10px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14, color: '#000', background: '#fff', boxSizing: 'border-box', fontFamily: F }} />
                      </div>
                      <div>
                        <label style={{ fontSize: 12, color: '#666', display: 'block', marginBottom: 4 }}>시간 (KST)</label>
                        <input type="time" value={ivTime} onChange={e => { setIvTime(e.target.value); saveIvPrefs({ time: e.target.value, duration: ivDuration, autoSend: ivAutoSend }) }}
                          style={{ width: '100%', padding: '10px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14, color: '#000', background: '#fff', boxSizing: 'border-box', fontFamily: F }} />
                      </div>
                    </div>

                    {/* Duration */}
                    <div>
                      <label style={{ fontSize: 12, color: '#666', display: 'block', marginBottom: 6 }}>면접 시간</label>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {[15, 20, 30, 45].map(d => (
                          <button key={d} onClick={() => { setIvDuration(d); saveIvPrefs({ time: ivTime, duration: d, autoSend: ivAutoSend }) }}
                            style={{
                              flex: 1, padding: '8px 0', borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: 'pointer', fontFamily: F,
                              border: ivDuration === d ? '2px solid #000' : '1px solid #ddd',
                              background: ivDuration === d ? '#000' : '#fff',
                              color: ivDuration === d ? '#fff' : '#000',
                            }}>{d}분</button>
                        ))}
                      </div>
                    </div>

                    {/* Notes */}
                    <div>
                      <label style={{ fontSize: 12, color: '#666', display: 'block', marginBottom: 4 }}>메모</label>
                      <textarea value={ivNotes} onChange={e => setIvNotes(e.target.value)} rows={2} placeholder="추가 메모..."
                        style={{ width: '100%', padding: '10px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 13, color: '#000', resize: 'vertical', boxSizing: 'border-box', fontFamily: F }} />
                    </div>

                    {/* Auto send */}
                    <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', padding: '10px 14px', background: ivAutoSend ? '#f0f9ff' : '#f8f8f8', borderRadius: 10, border: ivAutoSend ? '1px solid #93c5fd' : '1px solid #eee' }}>
                      <input type="checkbox" checked={ivAutoSend} onChange={e => { setIvAutoSend(e.target.checked); saveIvPrefs({ time: ivTime, duration: ivDuration, autoSend: e.target.checked }) }}
                        style={{ width: 18, height: 18, accentColor: '#000' }} />
                      <span style={{ fontSize: 13, fontWeight: 500, color: '#000' }}>이메일 자동 발송</span>
                      {!ivTarget.email && <span style={{ fontSize: 12, color: '#ef4444' }}>(이메일 없음)</span>}
                    </label>

                    {ivAutoSend && ivTarget.email && (
                      <div style={{ padding: '12px 14px', background: '#f8f8f8', border: '1px solid #eee', borderRadius: 10 }}>
                        <label style={{ fontSize: 11, color: '#888', display: 'block', marginBottom: 4 }}>제목</label>
                        <input id="iv-email-subject" defaultValue={defaultSubject}
                          style={{ width: '100%', padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6, fontSize: 13, color: '#000', boxSizing: 'border-box', fontFamily: F, marginBottom: 8 }} />
                        <label style={{ fontSize: 11, color: '#888', display: 'block', marginBottom: 4 }}>본문</label>
                        <textarea id="iv-email-body" defaultValue={defaultBody} rows={5}
                          style={{ width: '100%', padding: '8px 10px', border: '1px solid #ddd', borderRadius: 6, fontSize: 12, color: '#000', resize: 'vertical', boxSizing: 'border-box', fontFamily: F, lineHeight: 1.7 }} />
                      </div>
                    )}
                  </div>

                  {/* ═══ RIGHT COLUMN — Google Meet ═══ */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {/* Google Calendar에서 Meet 생성 */}
                    <div>
                      <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>Google Meet 링크</div>
                      <a
                        href={buildGCalUrl(
                          `BRIDGE Interview — ${firstName}`,
                          ivDate || new Date().toISOString().slice(0, 10),
                          ivTime || '14:00',
                          ivDuration,
                          String(ivTarget.email || '')
                        )}
                        target="_blank" rel="noopener noreferrer"
                        style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 16px', background: '#1a73e8', color: '#fff', borderRadius: 10, textDecoration: 'none', fontFamily: F, cursor: 'pointer' }}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M19 4H5c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H5V8l7 4 7-4v10z" fill="#fff"/></svg>
                        <div>
                          <div style={{ fontSize: 14, fontWeight: 600 }}>Google Calendar에서 Meet 생성</div>
                          <div style={{ fontSize: 11, opacity: 0.8, marginTop: 2 }}>캘린더 열림 → Meet 자동 포함 → 링크 복사</div>
                        </div>
                      </a>
                    </div>

                    {/* 현재 Meet 링크 */}
                    <div>
                      <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>Meet 링크 입력</div>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <input value={ivMeetLink} onChange={e => setIvMeetLink(e.target.value)}
                          placeholder="캘린더에서 복사한 Meet 링크 붙여넣기"
                          style={{ flex: 1, padding: '10px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 13, color: '#000', boxSizing: 'border-box', fontFamily: F }} />
                        {ivMeetLink && (
                          <button onClick={() => { navigator.clipboard?.writeText(ivMeetLink); showPhotoToast('복사됨') }}
                            style={{ padding: '10px 12px', background: '#f3f4f6', color: '#000', borderRadius: 8, fontSize: 12, fontWeight: 500, border: '1px solid #e5e7eb', cursor: 'pointer', fontFamily: F, flexShrink: 0 }}>복사</button>
                        )}
                      </div>
                      {ivMeetLink && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8, padding: '10px 12px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8 }}>
                          <div style={{ width: 8, height: 8, borderRadius: 4, background: '#22c55e', flexShrink: 0 }} />
                          <span style={{ flex: 1, fontSize: 12, color: '#000', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ivMeetLink}</span>
                          <a href={ivMeetLink} target="_blank" rel="noopener noreferrer"
                            style={{ padding: '4px 10px', background: '#000', color: '#fff', borderRadius: 6, fontSize: 11, fontWeight: 500, textDecoration: 'none', fontFamily: F }}>입장</a>
                        </div>
                      )}
                    </div>

                    {/* 저장된 풀에서 선택 */}
                    {pool.length > 0 && (
                      <details style={{ border: '1px solid #e5e7eb', borderRadius: 10, overflow: 'hidden' }}>
                        <summary style={{ padding: '10px 14px', fontSize: 12, fontWeight: 500, color: '#555', cursor: 'pointer', background: '#fafafa', userSelect: 'none' }}>
                          저장된 Meet 풀 ({pool.length})
                        </summary>
                        <div style={{ maxHeight: 180, overflow: 'auto' }}>
                          {pool.map((link, i) => {
                            const code = getMeetCode(link) || link.replace(/^https?:\/\//, '').slice(0, 30)
                            const selected = link === ivMeetLink
                            return (
                              <div key={i} style={{
                                display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px',
                                background: selected ? '#e8f4fd' : (i % 2 === 0 ? '#fff' : '#fafafa'),
                                borderBottom: '1px solid #f0f0f0', cursor: 'pointer', fontSize: 12,
                              }} onClick={() => setIvMeetLink(link)}>
                                <div style={{ width: 14, height: 14, borderRadius: 7, border: selected ? '2px solid #000' : '2px solid #ccc', background: selected ? '#000' : '#fff', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                  {selected && <div style={{ width: 6, height: 6, borderRadius: 3, background: '#fff' }} />}
                                </div>
                                <span style={{ flex: 1, color: '#000', fontWeight: selected ? 600 : 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{code}</span>
                                <button onClick={e => { e.stopPropagation(); removeLink(i) }} disabled={pool.length <= 1}
                                  style={{ width: 20, height: 20, borderRadius: 4, border: 'none', background: 'transparent', color: pool.length <= 1 ? '#ddd' : '#ef4444', fontSize: 14, cursor: pool.length <= 1 ? 'default' : 'pointer', flexShrink: 0, fontFamily: F }}>&times;</button>
                              </div>
                            )
                          })}
                        </div>
                        <div style={{ padding: '8px 12px', borderTop: '1px solid #e5e7eb', display: 'flex', gap: 6 }}>
                          <input value={ivNewLink} onChange={e => setIvNewLink(e.target.value)}
                            placeholder="Meet 링크 추가"
                            style={{ flex: 1, padding: '6px 8px', border: '1px solid #ddd', borderRadius: 6, fontSize: 11, color: '#000', boxSizing: 'border-box', fontFamily: F }}
                            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addLink() } }} />
                          <button onClick={addLink}
                            style={{ padding: '6px 10px', background: '#000', color: '#fff', borderRadius: 6, fontSize: 11, fontWeight: 500, border: 'none', cursor: 'pointer', fontFamily: F }}>+</button>
                        </div>
                      </details>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
        )
      })()}

      {/* ── Mail Modal ── */}
      <MailModal
        open={mailOpen}
        recipients={mailRecipients}
        onClose={() => setMailOpen(false)}
        adminKey={adminKey}
        apiUrl={API}
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
