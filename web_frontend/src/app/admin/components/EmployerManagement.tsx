'use client'

/**
 * EmployerManagement — 구인자관리 메인 컴포넌트
 * 워드뷰 + 엑셀뷰 + 블랙리스트
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import ExcelFilter from './ExcelFilter'
import ColumnManager, { type ColumnDef } from './ColumnManager'
import DocBlock, { type EmployerApp, maskEmail, maskPhone, maskName, v } from './DocBlock'
import MailComposer from './MailComposer'
import LinkPanel from './LinkPanel'

const API = API_URL

// ─── 상수 ────────────────────────────────────────────
const PAGE_BREAK_EVERY = 2  // 워드뷰 페이지 구분선 간격
const SCROLL_CHUNK = 50     // 무한 스크롤 1회 추가 렌더링 수

type TabKey = 'active' | 'all' | 'blacklist'
type ViewMode = 'word' | 'excel'

const STATUS_FLOW = ['open', 'contacted', 'hired', 'hold', 'closed', 'blacklist'] as const
const STATUS_LABEL: Record<string, string> = {
  open: 'Open', contacted: 'Contacted', hired: 'Hired',
  hold: 'Hold', closed: 'Closed', blacklist: 'Blacklist',
  new: 'New', interviewing: 'Interviewing', rejected: 'Rejected',
}
const STATUS_COLORS: Record<string, string> = {
  open: 'bg-sky-100 text-sky-700',
  contacted: 'bg-yellow-100 text-yellow-700',
  hired: 'bg-green-100 text-green-700',
  hold: 'bg-gray-100 text-gray-500',
  closed: 'bg-gray-200 text-gray-600',
  blacklist: 'bg-red-200 text-red-800',
  new: 'bg-sky-100 text-sky-700',
  interviewing: 'bg-blue-100 text-blue-700',
  rejected: 'bg-red-100 text-red-700',
}

/* ══════ 지역 정규화 ══════ */
const REGION_NORMALIZE: Record<string, string> = {
  '경기남부': '경기', '경기북부': '경기',
  '서울남동': '서울', '서울남서': '서울', '서울북동': '서울', '서울북서': '서울',
}
const CITY_TO_PROVINCE: Record<string, string> = {
  '고양': '경기', '수원': '경기', '성남': '경기', '용인': '경기', '화성': '경기',
  '파주': '경기', '김포': '경기', '안산': '경기', '안양': '경기', '평택': '경기',
  '의정부': '경기', '군포': '경기', '구리': '경기', '남양주': '경기', '하남': '경기',
  '오산': '경기', '이천': '경기', '광명': '경기', '동두천': '경기', '의왕': '경기',
  '과천': '경기', '수지': '경기', '분당': '경기', '동탄': '경기', '광교': '경기',
  '일산': '경기', '판교': '경기', '위례': '경기',
  'Suwon': '경기', 'Goyang': '경기', 'Seongnam': '경기', 'Paju': '경기',
  'Pyeongtaek': '경기', 'Bucheon': '경기',
  '천안': '충남', '아산': '충남', '청주': '충북', '충주': '충북',
  '전주': '전북', '군산': '전북', '순천': '전남', '목포': '전남', '여수': '전남',
  '포항': '경북', '구미': '경북', '경주': '경북', '안동': '경북',
  '창원': '경남', '거제': '경남', '양산': '경남', '진주': '경남', '김해': '경남',
  '강릉': '강원', '춘천': '강원', '원주': '강원', '속초': '강원',
  '서귀포': '제주',
  '강남구': '서울', '강동구': '서울', '강북구': '서울', '강서구': '서울',
  '관악구': '서울', '광진구': '서울', '구로구': '서울', '마포구': '서울',
  '서초구': '서울', '송파구': '서울', '영등포구': '서울', '용산구': '서울',
  'Gangnam-gu': '서울', 'Seoul': '서울', 'Busan': '부산', 'Daegu': '대구',
  'Incheon': '인천', 'Gwangju': '광주', 'Daejeon': '대전', 'Jeju': '제주',
  'Changwon': '경남', 'Gyeongju': '경북',
}
const PROVINCE_RE = /^(서울[남북][동서]?|경기[남북]부|서울특별시|서울시|서울|부산광역시|부산시|부산|대구시|대구|인천광역시|인천시|인천|광주광역시|광주|대전|울산|세종시|세종|경기도|경기|강원도|강원|충북|충남|전남|전북|경북|경남|제주도|제주시|제주|Seoul|SEOUL|Busan|Daegu|Incheon|Gwangju|Daejeon|Ulsan|Sejong|Gyeonggi|Gangwon|Chungbuk|Chungnam|Jeonbuk|Jeonnam|Gyeongbuk|Gyeongnam|Jeju)/i
const PREFIX_NORMALIZE: Record<string, string> = {
  '서울특별시': '서울', '서울시': '서울', 'SEOUL': '서울',
  '부산광역시': '부산', '부산시': '부산', '대구시': '대구',
  '인천광역시': '인천', '인천시': '인천', '광주광역시': '광주',
  '세종시': '세종', '경기도': '경기', '강원도': '강원', '제주도': '제주', '제주시': '제주',
}

function extractProvince(loc: string | null | undefined): string {
  if (!loc) return ''
  const s = loc.trim()
  if (!s) return ''
  const match = s.match(PROVINCE_RE)
  if (match) {
    const raw = match[1]
    return REGION_NORMALIZE[raw] || PREFIX_NORMALIZE[raw] || raw
  }
  const parts = s.split(',').map(p => p.trim()).filter(p => p && p !== 'Republic of Korea' && p !== 'Korea')
  for (let idx = parts.length - 1; idx >= 0; idx--) {
    const m2 = parts[idx].match(PROVINCE_RE)
    if (m2) return REGION_NORMALIZE[m2[1]] || PREFIX_NORMALIZE[m2[1]] || m2[1]
    if (CITY_TO_PROVINCE[parts[idx]]) return CITY_TO_PROVINCE[parts[idx]]
  }
  const glued = s.match(/^(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)/)
  if (glued) return glued[1]
  const firstWord = s.split(/[\s,]/)[0]
  if (firstWord && CITY_TO_PROVINCE[firstWord]) return CITY_TO_PROVINCE[firstWord]
  for (const [city, prov] of Object.entries(CITY_TO_PROVINCE)) {
    if (s.includes(city)) return prov
  }
  return ''
}

const PROVINCE_STRIP_RE = /^(?:서울[남북][동서]?|경기[남북]부|서울특별시|서울시|서울|부산광역시|부산시|부산|대구시|대구|인천광역시|인천시|인천|광주광역시|광주|대전|울산|세종시|세종|경기도|경기|강원도|강원|충북|충남|전남|전북|경북|경남|제주도|제주시|제주)\s*/i

function extractCity(loc: string | null | undefined): string {
  if (!loc) return ''
  const s = loc.trim()
  const stripped = s.replace(PROVINCE_STRIP_RE, '')
  if (stripped && stripped !== s) {
    const fp = stripped.split(/[,\s]/)[0]?.trim()
    if (fp) return fp
  }
  const parts = s.split(',').map(p => p.trim())
  if (parts.length >= 2) return parts[0]
  const words = s.split(/\s+/)
  if (words.length >= 2 && CITY_TO_PROVINCE[words[0]]) return words.slice(1).join(' ')
  return ''
}

function extractAgeLabels(age: string | null | undefined): string[] {
  if (!age) return []
  const result: string[] = []
  const l = age.toLowerCase()
  if (l.includes('pre-k') || l.includes('유아')) result.push('Pre-K')
  if (l.includes('kindergarten') || l.includes('kindy') || l.includes('유치원')) result.push('유치원')
  if (l.includes('elementary') || l.includes('elem') || l.includes('초등')) result.push('초등')
  if (l.includes('middle') || l.includes('중학')) result.push('중학')
  if (l.includes('high') || l.includes('고등')) result.push('고등')
  if (l.includes('adult') || l.includes('성인')) result.push('성인')
  if (result.length === 0 && age.trim()) result.push(age.trim())
  return result
}

/* ══════ Job 번호 ══════
 * 우선순위:
 *   1. job_code (DB 원본 — "1003", "N1101" 등)
 *   2. raw_text에서 "Job. XXXX" 파싱 → 4자리 숫자
 *   3. client_inquiries (inq_ prefix) → N{number}
 *   4. 기타 fallback
 */
function jobNo(app: EmployerApp): string {
  if (v(app.job_code)) return app.job_code as string
  // raw_text에서 "Job. 1003" 형식 파싱
  if (app.raw_text) {
    const m = app.raw_text.match(/Job\.\s*(\d{3,6})/i)
    if (m) return m[1]
  }
  // client_inquiries 신규 접수 → N{숫자}
  if (app.id.startsWith('inq_')) return `N${app.id.replace('inq_', '')}`
  const src = app.source_file || ''
  if (src.startsWith('BRIDGE_clients')) return `F-${app.id}`
  if (src === 'memo_extract') return `M-${app.id}`
  return app.id
}

function isNewJobCode(code: string): boolean { return /^N\d+/.test(code) }

/* ══════ Confirmed IDs (localStorage) ══════ */
const CONFIRMED_KEY = 'bridge_employer_confirmed'
function loadConfirmed(): Set<string> {
  if (typeof window === 'undefined') return new Set()
  try {
    const raw = localStorage.getItem(CONFIRMED_KEY)
    return raw ? new Set(JSON.parse(raw)) : new Set()
  } catch { return new Set() }
}
function saveConfirmed(set: Set<string>) {
  if (typeof window !== 'undefined') {
    localStorage.setItem(CONFIRMED_KEY, JSON.stringify([...set]))
  }
}

/* ══════ Employer Order (localStorage) ══════ */
const ORDER_KEY = 'bridge_employer_order'
function loadOrder(): string[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(ORDER_KEY)
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}
function saveOrder(ids: string[]) {
  if (typeof window !== 'undefined') {
    localStorage.setItem(ORDER_KEY, JSON.stringify(ids))
  }
}

/* ══════ 기본 열 정의 ══════ */
const DEFAULT_COLUMNS: ColumnDef[] = [
  { key: 'province', label: '지역', visible: true, width: 70 },
  { key: 'city', label: '도시', visible: true, width: 90 },
  { key: 'name', label: '업체명', visible: true, width: 220 },
  { key: 'age', label: '연령', visible: true, width: 120 },
  { key: 'email', label: '이메일', visible: true, width: 170 },
  { key: 'phone', label: '연락처', visible: true, width: 120 },
  { key: 'salary', label: '급여', visible: true, width: 120 },
  { key: 'start', label: '시작일', visible: true, width: 100 },
  { key: 'status', label: '상태', visible: true, width: 100 },
]

/* ══════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════════════════ */
export default function EmployerManagement() {
  const { authed, headers, signedFetch } = useAdminAuth()

  /* ── State ── */
  const [employers, setEmployers] = useState<EmployerApp[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  const [tab, setTab] = useState<TabKey>('active')
  const [viewMode, setViewMode] = useState<ViewMode>('word')
  // 어드민 페이지: PII 기본값 ON
  const [showPII, setShowPII] = useState(true)

  // 필터
  const [filterProvince, setFilterProvince] = useState<string[]>([])
  const [filterCity, setFilterCity] = useState<string[]>([])
  const [filterAge, setFilterAge] = useState<string[]>([])
  const [filterStatus, setFilterStatus] = useState<string[]>([])

  // Ctrl+F 검색
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const searchInputRef = useRef<HTMLInputElement>(null)
  const wakeRetryRef = useRef(0)

  // NEW 확인
  const [confirmedIds, setConfirmedIds] = useState<Set<string>>(loadConfirmed)

  // 순서 변경 추적
  const [orderChanged, setOrderChanged] = useState(false)

  // 메일
  const [showMailComposer, setShowMailComposer] = useState(false)
  const [mailRecipients, setMailRecipients] = useState<EmployerApp[]>([])

  // 연동 패널
  const [linkPanel, setLinkPanel] = useState<{
    jobNumber: string; jobTitle: string; region: string; teachingAge: string
  } | null>(null)

  // 열 관리
  const [columns, setColumns] = useState<ColumnDef[]>(DEFAULT_COLUMNS)
  const [showColumnMgr, setShowColumnMgr] = useState(false)

  // 열 리사이즈
  const [resizingCol, setResizingCol] = useState<string | null>(null)
  const resizeStartX = useRef(0)
  const resizeStartW = useRef(0)

  // 무한 스크롤 (클라이언트 사이드 — 렌더링 가상화)
  const [visibleCount, setVisibleCount] = useState(SCROLL_CHUNK)
  const sentinelRef = useRef<HTMLDivElement>(null)

  const flash = (msg: string) => { setActionMsg(msg); setTimeout(() => setActionMsg(null), 3000) }

  /* ── Ctrl+F 가로채기 ── */
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault()
        setSearchOpen(true)
        setTimeout(() => searchInputRef.current?.focus(), 50)
      }
      if (e.key === 'Escape') {
        setSearchOpen(false)
        setSearchQuery('')
      }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])

  /* ── Fetch (type=employer → 구인자만, 구직자 스킵) ── */
  const fetchEmployers = useCallback(async () => {
    setLoading(true)
    setError(null)
    const ctrl = new AbortController()
    const ctrlTimer = setTimeout(() => ctrl.abort(), 5000)
    let res: Response
    try {
      res = await fetch(`${API}/api/admin/applications?type=employer`, { headers: headers(), signal: ctrl.signal })
      clearTimeout(ctrlTimer)
    } catch (e: unknown) {
      clearTimeout(ctrlTimer)
      setLoading(false)
      const isAbort = e instanceof DOMException && e.name === 'AbortError'
      wakeRetryRef.current += 1
      if (isAbort && wakeRetryRef.current <= 20) {
        setError(`서버 기동 중... (${wakeRetryRef.current}회 재시도)`)
        setTimeout(() => fetchEmployers(), 3000)
      } else {
        setError('서버 연결 실패 — 새로고침 후 재시도하세요')
      }
      return
    }
    wakeRetryRef.current = 0
    try {
      if (!res.ok) {
        if (res.status === 403) { setError('인증 오류. 다시 로그인해주세요.'); return }
        throw new Error('데이터 로딩 실패')
      }
      const json = await res.json()
      if (!json.success) throw new Error(json.message || 'Error')
      const all: EmployerApp[] = (json.data ?? []).filter((a: EmployerApp) => a.type === 'employer')
      // Apply saved order if available
      const savedOrder = loadOrder()
      if (savedOrder.length > 0) {
        const orderMap = new Map(savedOrder.map((id, idx) => [id, idx]))
        const sorted = [...all].sort((a, b) => {
          const ai = orderMap.has(a.id) ? orderMap.get(a.id)! : 9999
          const bi = orderMap.has(b.id) ? orderMap.get(b.id)! : 9999
          return ai - bi
        })
        setEmployers(sorted)
      } else {
        setEmployers(all)
      }
      setOrderChanged(false)
      setVisibleCount(SCROLL_CHUNK)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => { if (authed) fetchEmployers() }, [authed, fetchEmployers])

  /* ── 무한 스크롤: IntersectionObserver ── */
  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting) {
          setVisibleCount(prev => prev + SCROLL_CHUNK)
        }
      },
      { threshold: 0.1 },
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, []) // sentinel은 마운트 후 고정이므로 deps 불필요

  /* ── 필터/탭/검색 변경 시 visibleCount 리셋 ── */
  useEffect(() => {
    setVisibleCount(SCROLL_CHUNK)
  }, [tab, filterProvince, filterCity, filterAge, filterStatus, searchQuery])

  /* ── 상태 변경 ── */
  const updateStatus = useCallback(async (id: string, newStatus: string) => {
    try {
      const res = await fetch(`${API}/api/admin/applications/${id}`, {
        method: 'PATCH', headers: headers(),
        body: JSON.stringify({ status: newStatus, type: 'employer' }),
      })
      if (!res.ok) throw new Error('Failed')
      flash(`#${id} → ${STATUS_LABEL[newStatus] || newStatus}`)
      fetchEmployers()
    } catch {
      flash('상태 변경 실패')
    }
  }, [headers, fetchEmployers])

  /* ── NEW 확인 (단건) ── */
  const confirmNew = useCallback((id: string) => {
    setConfirmedIds(prev => {
      const next = new Set(prev)
      next.add(id)
      saveConfirmed(next)
      return next
    })
  }, [])

  /* ── 전체 NEW 확인 ── */
  const confirmAll = useCallback(() => {
    setConfirmedIds(prev => {
      const next = new Set(prev)
      employers.filter(e => e.status === 'new').forEach(e => next.add(e.id))
      saveConfirmed(next)
      return next
    })
  }, [employers])

  /* ── 워드뷰 이동 버튼 ── */
  const moveTop = useCallback((id: string) => {
    setEmployers(prev => {
      const idx = prev.findIndex(e => e.id === id)
      if (idx <= 0) return prev
      const next = [...prev]
      const [item] = next.splice(idx, 1)
      setOrderChanged(true)
      return [item, ...next]
    })
  }, [])

  const moveUp = useCallback((id: string) => {
    setEmployers(prev => {
      const idx = prev.findIndex(e => e.id === id)
      if (idx <= 0) return prev
      const next = [...prev]
      ;[next[idx - 1], next[idx]] = [next[idx], next[idx - 1]]
      setOrderChanged(true)
      return next
    })
  }, [])

  const moveDown = useCallback((id: string) => {
    setEmployers(prev => {
      const idx = prev.findIndex(e => e.id === id)
      if (idx >= prev.length - 1) return prev
      const next = [...prev]
      ;[next[idx], next[idx + 1]] = [next[idx + 1], next[idx]]
      setOrderChanged(true)
      return next
    })
  }, [])

  /* ── 메모/본문 인라인 편집 (로컬 + DB 저장) ── */
  const editMemo = useCallback((id: string, memo: string) => {
    setEmployers(prev => prev.map(e => e.id === id ? { ...e, memo } : e))
    fetch(`${API}/api/admin/applications/${id}`, {
      method: 'PATCH', headers: headers(),
      body: JSON.stringify({ memo, type: 'employer' }),
    }).catch(() => {})
  }, [headers])

  const editNotes = useCallback((id: string, notes: string) => {
    setEmployers(prev => prev.map(e => e.id === id ? { ...e, notes } : e))
    fetch(`${API}/api/admin/applications/${id}`, {
      method: 'PATCH', headers: headers(),
      body: JSON.stringify({ notes, type: 'employer' }),
    }).catch(() => {})
  }, [headers])

  /* ── 필터 옵션 계산 ── */
  const provinceOptions = useMemo(() => {
    const s = new Set<string>()
    employers.forEach(e => { const p = extractProvince(e.location); if (p) s.add(p) })
    return [...s].sort()
  }, [employers])

  const cityOptions = useMemo(() => {
    const s = new Set<string>()
    const src = filterProvince.length > 0
      ? employers.filter(e => filterProvince.includes(extractProvince(e.location)))
      : employers
    src.forEach(e => { const c = extractCity(e.location); if (c) s.add(c) })
    return [...s].sort()
  }, [employers, filterProvince])

  const ageOptions = useMemo(() => {
    const s = new Set<string>()
    employers.forEach(e => extractAgeLabels(e.teaching_age).forEach(a => s.add(a)))
    return [...s].sort()
  }, [employers])

  const statusOptions = useMemo(() => {
    const s = new Set<string>()
    employers.forEach(e => { if (e.status) s.add(e.status) })
    return [...s].sort()
  }, [employers])

  /* ── 탭 + 필터 + 검색 적용 ── */
  const filtered = useMemo(() => {
    let list = employers

    // 탭 필터
    if (tab === 'active') {
      list = list.filter(e => e.status !== 'blacklist' && ['open', 'contacted', 'new', 'interviewing'].includes(e.status))
    } else if (tab === 'blacklist') {
      list = list.filter(e => e.status === 'blacklist')
    }
    // 'all' → 전체

    // 다중선택 필터
    if (filterProvince.length > 0) list = list.filter(e => filterProvince.includes(extractProvince(e.location)))
    if (filterCity.length > 0) list = list.filter(e => filterCity.includes(extractCity(e.location)))
    if (filterAge.length > 0) list = list.filter(e => {
      const ages = extractAgeLabels(e.teaching_age)
      return filterAge.some(a => ages.includes(a))
    })
    if (filterStatus.length > 0) list = list.filter(e => filterStatus.includes(e.status))

    // Ctrl+F 검색
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      list = list.filter(e =>
        (e.school_name || '').toLowerCase().includes(q) ||
        (e.name || '').toLowerCase().includes(q) ||
        (e.memo || '').toLowerCase().includes(q) ||
        (e.notes || '').toLowerCase().includes(q) ||
        (e.raw_text || '').toLowerCase().includes(q) ||
        (e.job_code || '').toLowerCase().includes(q) ||
        e.id.toLowerCase().includes(q)
      )
    }

    return list
  }, [employers, tab, filterProvince, filterCity, filterAge, filterStatus, searchQuery])

  /* ── 렌더링할 visible 슬라이스 ── */
  const visibleFiltered = useMemo(
    () => filtered.slice(0, visibleCount),
    [filtered, visibleCount],
  )

  /* ── NEW 카운트 ── */
  const newUnconfirmedCount = useMemo(() => {
    return employers.filter(e => (e.status === 'new' || e.status === 'open') && !confirmedIds.has(e.id)).length
  }, [employers, confirmedIds])

  /* ── 메일 열기 ── */
  const openMailComposer = (list: EmployerApp[]) => {
    if (list.length === 0) { flash('수신자를 선택해주세요'); return }
    setMailRecipients(list)
    setShowMailComposer(true)
  }

  /* ── 열 리사이즈 ── */
  const startResize = (key: string, e: React.MouseEvent) => {
    e.preventDefault()
    setResizingCol(key)
    resizeStartX.current = e.clientX
    resizeStartW.current = columns.find(c => c.key === key)?.width ?? 100
  }

  useEffect(() => {
    if (!resizingCol) return
    const onMove = (e: MouseEvent) => {
      const diff = e.clientX - resizeStartX.current
      setColumns(prev => prev.map(c =>
        c.key === resizingCol ? { ...c, width: Math.max(50, resizeStartW.current + diff) } : c
      ))
    }
    const onUp = () => setResizingCol(null)
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    return () => { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
  }, [resizingCol])

  /* ── 엑셀 셀 값 ── */
  const cellValue = (app: EmployerApp, key: string): string => {
    const province = extractProvince(app.location)
    const city = extractCity(app.location)
    switch (key) {
      case 'province': return province
      case 'city': return city
      case 'name': {
        const nm = showPII ? (v(app.school_name) || v(app.name)) : maskName(app.school_name || app.name)
        return nm || v(app.job_code) || jobNo(app)
      }
      case 'age': return v(app.teaching_age)
      case 'email': return showPII ? v(app.email) : maskEmail(app.email)
      case 'phone': return showPII ? v(app.phone) : maskPhone(app.phone)
      case 'salary': return v(app.salary_raw)
      case 'start': return v(app.start_date)
      case 'status': return STATUS_LABEL[app.status] || app.status
      default: return ''
    }
  }

  const visibleCols = columns.filter(c => c.visible)
  const hasFilters = filterProvince.length > 0 || filterCity.length > 0 || filterAge.length > 0 || filterStatus.length > 0

  const TABS = [
    { key: 'active' as TabKey, label: '활발한 채용보기' },
    { key: 'all' as TabKey, label: '전체보기' },
    { key: 'blacklist' as TabKey, label: '블랙리스트' },
  ]

  /* ══════ RENDER ══════ */
  return (
    <div className="space-y-5">
      {/* 애니메이션 */}
      <style>{`
        @keyframes search-pop { from{opacity:0;transform:translateY(-8px)} to{opacity:1;transform:translateY(0)} }
      `}</style>

      {/* Ctrl+F 검색 팝업 */}
      {searchOpen && (
        <div
          className="fixed top-16 right-5 z-[9999] bg-white rounded-xl shadow-2xl border-2 border-blue-500 flex items-center gap-2 px-3 py-2.5"
          style={{ animation: 'search-pop 0.2s ease', minWidth: 280 }}
        >
          <span className="text-blue-500 text-[14px]">🔍</span>
          <input
            ref={searchInputRef}
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="이름, Job번호, 메모, 본문 검색..."
            className="flex-1 outline-none text-[13px] text-gray-800 bg-transparent"
          />
          {searchQuery && (
            <span className="text-[11px] text-blue-600 font-bold whitespace-nowrap">{filtered.length}건</span>
          )}
          <button
            type="button"
            onClick={() => { setSearchOpen(false); setSearchQuery('') }}
            className="text-gray-400 hover:text-gray-600 text-[16px] leading-none ml-1"
          >
            ✕
          </button>
        </div>
      )}

      {/* ── 헤더 ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[22px] font-bold text-[#1d1d1f] tracking-tight">구인자관리</h1>
          <p className="text-[13px] text-[#86868b] mt-0.5">
            {hasFilters || searchQuery
              ? `${filtered.length} / ${employers.length}건`
              : `${employers.length}건`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {actionMsg && <span className="text-[12px] text-green-600 font-medium bg-green-50 px-3 py-1 rounded-lg">{actionMsg}</span>}

          {orderChanged && (
            <button type="button"
              onClick={() => { saveOrder(employers.map(e => e.id)); setOrderChanged(false); flash('저장 완료') }}
              className="px-3 py-1.5 bg-blue-600 text-white text-[12px] font-semibold rounded-lg hover:bg-blue-700">
              저장
            </button>
          )}

          {newUnconfirmedCount > 0 && (
            <button type="button" onClick={confirmAll}
              className="px-3 py-1.5 bg-gray-800 text-white text-[12px] font-semibold rounded-lg hover:bg-gray-900">
              NEW 전체확인 ({newUnconfirmedCount})
            </button>
          )}

          <button type="button" onClick={fetchEmployers}
            className="px-3 py-1.5 border border-gray-200 text-[12px] text-gray-600 font-medium rounded-lg hover:bg-gray-50">
            새로고침
          </button>
        </div>
      </div>

      {/* ── 탭 ── */}
      <div className="flex items-end gap-1">
        {TABS.map(t => (
          <button key={t.key} type="button"
            onClick={() => { setTab(t.key); setSearchQuery('') }}
            className={`px-4 py-2 text-[13px] font-semibold rounded-t-lg transition-colors border border-b-0 ${
              tab === t.key
                ? 'bg-white text-[#1d1d1f] border-gray-200'
                : 'bg-gray-50 text-gray-400 border-transparent hover:text-gray-600'
            }`}
          >
            {t.label}
            {t.key === 'active' && newUnconfirmedCount > 0 && (
              <span className="ml-1.5 bg-blue-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                {newUnconfirmedCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── 필터 + 뷰 토글 바 ── */}
      <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4">
        <div className="flex flex-wrap items-center gap-2">
          {/* 뷰 모드 */}
          <div className="flex bg-gray-100 rounded-xl p-0.5">
            <button type="button" onClick={() => setViewMode('word')}
              className={`px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-colors ${
                viewMode === 'word' ? 'bg-white text-[#1d1d1f] shadow-sm' : 'text-[#86868b]'
              }`}>워드뷰</button>
            <button type="button" onClick={() => setViewMode('excel')}
              className={`px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-colors ${
                viewMode === 'excel' ? 'bg-white text-[#1d1d1f] shadow-sm' : 'text-[#86868b]'
              }`}>엑셀뷰</button>
          </div>
          <div className="h-6 w-px bg-gray-200" />

          {/* 공통 필터 드롭다운 */}
          <ExcelFilter label="전체 지역" options={provinceOptions} selected={filterProvince} onChange={v => { setFilterProvince(v); setFilterCity([]) }} />
          <ExcelFilter label="전체 도시" options={cityOptions} selected={filterCity} onChange={setFilterCity} />
          <ExcelFilter label="전체 대상" options={ageOptions} selected={filterAge} onChange={setFilterAge} />
          <ExcelFilter label="상태" options={statusOptions} selected={filterStatus} onChange={setFilterStatus} />

          {hasFilters && (
            <button type="button" onClick={() => { setFilterProvince([]); setFilterCity([]); setFilterAge([]); setFilterStatus([]) }}
              className="text-[11px] text-red-500 hover:text-red-700 font-medium">초기화</button>
          )}

          <span className="text-[11px] text-gray-400 ml-1">Ctrl+F 검색</span>

          <div className="flex-1" />

          {/* PII 토글 (기본값 ON) */}
          <label className="flex items-center gap-1.5 text-[12px] text-gray-500 cursor-pointer select-none">
            <input type="checkbox" checked={showPII} onChange={e => setShowPII(e.target.checked)}
              className="w-3.5 h-3.5 rounded border-gray-300 text-red-600 focus:ring-red-500" />
            PII 표시
          </label>

          {/* 열 관리 (엑셀뷰에서만) */}
          {viewMode === 'excel' && (
            <button type="button" onClick={() => setShowColumnMgr(true)}
              className="text-[11px] text-gray-500 hover:text-gray-700 font-medium border border-gray-200 px-2 py-1 rounded-lg">
              열 관리
            </button>
          )}
        </div>
      </div>

      {/* ── 에러 / 로딩 ── */}
      {error && <div className="p-4 bg-red-50 text-red-600 text-[13px] rounded-2xl">{error}</div>}
      {loading && (
        <div className="text-center py-16 text-[#86868b] text-[14px]">
          <div className="animate-spin inline-block w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mb-3" />
          <div className="animate-pulse">로딩 중...</div>
        </div>
      )}

      {/* ── 콘텐츠 ── */}
      {!loading && !error && (
        <>
          {/* ── 워드뷰 ── */}
          {viewMode === 'word' && (
            <div className="space-y-4">
              {filtered.length === 0 && (
                <div className="text-center py-16 text-[#86868b] text-[14px]">데이터가 없습니다.</div>
              )}
              {visibleFiltered.map((app, visIdx) => (
                <DocBlock
                  key={app.id}
                  employer={app}
                  isNew={app.status === 'new'}
                  isConfirmed={confirmedIds.has(app.id)}
                  isBlacklist={app.status === 'blacklist'}
                  showPII={showPII}
                  province={extractProvince(app.location)}
                  city={extractCity(app.location)}
                  jobNo={jobNo(app)}
                  searchQuery={searchQuery}
                  onConfirm={confirmNew}
                  onStatusChange={updateStatus}
                  onEditMemo={editMemo}
                  onEditNotes={editNotes}
                  onMoveTop={() => moveTop(app.id)}
                  onMoveUp={() => moveUp(app.id)}
                  onMoveDown={() => moveDown(app.id)}
                  isFirst={visIdx === 0}
                  isLast={visIdx === filtered.length - 1}
                  showDivider={(visIdx + 1) % PAGE_BREAK_EVERY === 0 && visIdx < visibleFiltered.length - 1}
                  onOpenMail={() => openMailComposer([app])}
                  onLinkPanel={() => setLinkPanel({ jobNumber: jobNo(app), jobTitle: app.school_name || app.name || '', region: extractProvince(app.location), teachingAge: app.teaching_age || '' })}
                  onEditJobCode={(id, code) => setEmployers(prev => prev.map(e => e.id === id ? { ...e, job_code: code } : e))}
                  onEditName={(id, name) => setEmployers(prev => prev.map(e => e.id === id ? { ...e, school_name: name } : e))}
                />
              ))}

              {/* 무한 스크롤 sentinel */}
              {visibleCount < filtered.length ? (
                <div ref={sentinelRef} className="h-10 flex items-center justify-center gap-2 py-4">
                  <div className="w-4 h-4 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
                  <span className="text-[12px] text-gray-400">{visibleCount} / {filtered.length}건 표시 중...</span>
                </div>
              ) : (
                filtered.length > 0 && (
                  <div className="text-center py-4 text-[11px] text-gray-300">
                    — 전체 {filtered.length}건 표시 완료 —
                  </div>
                )
              )}
            </div>
          )}

          {/* ── 엑셀뷰 ── */}
          {viewMode === 'excel' && (
            <div className="bg-white border border-[#e5e5e7] rounded-2xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full" style={{ tableLayout: 'fixed', minWidth: `${visibleCols.reduce((a, c) => a + c.width, 0) + 156}px` }}>
                  <colgroup>
                    <col style={{ width: '36px' }} />
                    {visibleCols.map(c => <col key={c.key} style={{ width: `${c.width}px` }} />)}
                    <col style={{ width: '120px' }} />
                  </colgroup>
                  <thead>
                    {/* 열 문자 행 A, B, C... */}
                    <tr className="bg-[#ebebed] text-[10px] text-[#aaa]" style={{ position: 'sticky', top: 0, zIndex: 21 }}>
                      <th className="px-1 py-0.5 text-center border-r border-gray-200" />
                      {visibleCols.map((c, i) => (
                        <th key={c.key} className="px-1 py-0.5 text-center font-normal">{String.fromCharCode(65 + i)}</th>
                      ))}
                      <th className="px-1 py-0.5 text-center font-normal">{String.fromCharCode(65 + visibleCols.length)}</th>
                    </tr>
                    {/* 열 이름 행 */}
                    <tr className="bg-[#f5f5f7] text-[11px] text-[#86868b] uppercase tracking-wider" style={{ position: 'sticky', top: '22px', zIndex: 20 }}>
                      <th className="px-1 py-3 text-center text-[9px] text-gray-300 border-r border-gray-100 select-none" />
                      {visibleCols.map(c => (
                        <th key={c.key} className="px-3 py-3 text-left font-semibold relative group">
                          {c.label}
                          <div
                            className="absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize opacity-0 group-hover:opacity-100 hover:bg-blue-300 transition-opacity"
                            onMouseDown={e => startResize(c.key, e)}
                          />
                        </th>
                      ))}
                      <th className="px-2 py-3 text-center font-semibold">액션</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#f0f0f2]">
                    {filtered.map((app, rowIdx) => {
                      const isBlacklist = app.status === 'blacklist'
                      const isNew = app.status === 'new' && !confirmedIds.has(app.id)
                      const no = jobNo(app)
                      const isNewCode = isNewJobCode(no)
                      const sq = searchQuery.toLowerCase()
                      const isHl = sq && (
                        (app.school_name || '').toLowerCase().includes(sq) ||
                        (app.name || '').toLowerCase().includes(sq) ||
                        (app.memo || '').toLowerCase().includes(sq) ||
                        (app.job_code || '').toLowerCase().includes(sq) ||
                        app.id.toLowerCase().includes(sq)
                      )
                      return (
                        <tr
                          key={app.id}
                          className={`transition-colors ${
                            isBlacklist ? 'bg-[rgba(220,38,38,0.04)]' : isHl ? 'bg-yellow-50' : 'hover:bg-[#f0f4ff]'
                          } ${isNew ? '' : ''}`}
                          style={isBlacklist ? { borderLeft: '3px solid rgba(220,38,38,0.4)' } : undefined}
                        >
                          <td className="px-1 py-2.5 text-center text-[10px] text-gray-300 border-r border-gray-100 select-none">{rowIdx + 1}</td>
                          {visibleCols.map(c => (
                            <td key={c.key} className="px-3 py-2.5 text-[13px] truncate" title={cellValue(app, c.key)}>
                              {c.key === 'status' ? (
                                <select
                                  className={`text-[11px] px-2 py-1 rounded-full font-semibold border-0 cursor-pointer ${
                                    STATUS_COLORS[app.status] || 'bg-gray-100 text-gray-600'
                                  }`}
                                  value={app.status}
                                  onChange={e => updateStatus(app.id, e.target.value)}
                                  onClick={e => e.stopPropagation()}
                                >
                                  {STATUS_FLOW.map(s => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
                                </select>
                              ) : (
                                <span className={`${c.key === 'name' ? 'font-semibold text-[#1d1d1f]' : 'text-[#424245]'}`}>
                                  {cellValue(app, c.key)}
                                </span>
                              )}
                              {c.key === 'status' && isBlacklist && (
                                <span className="ml-1 px-1 py-0.5 bg-red-100 text-red-700 text-[9px] font-bold rounded">BLOCK</span>
                              )}
                            </td>
                          ))}
                          {/* 액션 버튼 — 항상 표시 */}
                          <td className="px-2 py-2.5 text-center">
                            <div className="flex items-center justify-center gap-1">
                              <button
                                type="button"
                                onClick={() => openMailComposer([app])}
                                className="px-2 py-1 bg-blue-50 text-blue-600 text-[11px] font-semibold rounded-lg hover:bg-blue-100 transition-colors"
                              >
                                메일
                              </button>
                              <button
                                type="button"
                                onClick={() => setLinkPanel({ jobNumber: jobNo(app), jobTitle: app.school_name || app.name || '', region: extractProvince(app.location), teachingAge: app.teaching_age || '' })}
                                className="px-2 py-1 bg-green-50 text-green-700 text-[11px] font-semibold rounded-lg hover:bg-green-100 transition-colors"
                                title="매칭 연동 패널"
                              >
                                연동
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                    {filtered.length === 0 && (
                      <tr>
                        <td colSpan={visibleCols.length + 1} className="text-center py-16 text-[#86868b] text-[14px]">
                          데이터가 없습니다.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── 모달: 열 관리 ── */}
      {showColumnMgr && (
        <ColumnManager
          columns={columns}
          onChange={setColumns}
          onClose={() => setShowColumnMgr(false)}
        />
      )}

      {/* ── 모달: 메일 작성 ── */}
      {showMailComposer && (
        <MailComposer
          recipients={mailRecipients}
          extractProvince={extractProvince}
          extractCity={extractCity}
          onClose={() => setShowMailComposer(false)}
        />
      )}

      {/* ── 연동 패널 ── */}
      {linkPanel && (
        <LinkPanel
          mode="employer"
          jobNumber={linkPanel.jobNumber}
          jobTitle={linkPanel.jobTitle}
          region={linkPanel.region}
          teachingAge={linkPanel.teachingAge}
          onClose={() => setLinkPanel(null)}
        />
      )}
    </div>
  )
}
