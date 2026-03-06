'use client'

/**
 * EmployerManagement — 구인자관리 메인 컴포넌트
 * 워드뷰 + 엑셀뷰 + 메일링 + 블랙리스트
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import ExcelFilter from './ExcelFilter'
import ColumnManager, { type ColumnDef } from './ColumnManager'
import DocBlock, { type EmployerApp, maskEmail, maskPhone, maskName, v } from './DocBlock'
import MailComposer from './MailComposer'

const API = API_URL
type TabKey = 'active' | 'all' | 'mailing' | 'blacklist'
type ViewMode = 'word' | 'excel'

const STATUS_FLOW = ['new', 'contacted', 'interviewing', 'hired', 'rejected', 'hold', 'blacklist'] as const
const STATUS_LABEL: Record<string, string> = {
  new: 'New', contacted: 'Contacted', interviewing: 'Interviewing',
  hired: 'Hired', rejected: 'Rejected', hold: 'Hold', blacklist: 'Blacklist',
}
const STATUS_COLORS: Record<string, string> = {
  new: 'bg-sky-100 text-sky-700',
  contacted: 'bg-yellow-100 text-yellow-700',
  interviewing: 'bg-blue-100 text-blue-700',
  hired: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  hold: 'bg-gray-100 text-gray-500',
  blacklist: 'bg-red-200 text-red-800',
}

/* ══════ 지역 정규화 (기존 로직 재사용) ══════ */
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

/* ══════ Job 번호 ══════ */
function jobNo(app: EmployerApp): string {
  if (v(app.job_code)) return app.job_code as string
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

/* ══════ 기본 열 정의 ══════ */
const DEFAULT_COLUMNS: ColumnDef[] = [
  { key: 'no', label: 'No.', visible: true, width: 90 },
  { key: 'province', label: '지역', visible: true, width: 70 },
  { key: 'city', label: '도시', visible: true, width: 90 },
  { key: 'name', label: '업체명', visible: true, width: 160 },
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
  const [showPII, setShowPII] = useState(false)

  // 필터
  const [filterProvince, setFilterProvince] = useState<string[]>([])
  const [filterCity, setFilterCity] = useState<string[]>([])
  const [filterAge, setFilterAge] = useState<string[]>([])
  const [filterStatus, setFilterStatus] = useState<string[]>([])

  // NEW 확인
  const [confirmedIds, setConfirmedIds] = useState<Set<string>>(loadConfirmed)

  // 메일링
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [showMailComposer, setShowMailComposer] = useState(false)
  const [mailRecipients, setMailRecipients] = useState<EmployerApp[]>([])

  // 열 관리
  const [columns, setColumns] = useState<ColumnDef[]>(DEFAULT_COLUMNS)
  const [showColumnMgr, setShowColumnMgr] = useState(false)

  // 열 리사이즈
  const [resizingCol, setResizingCol] = useState<string | null>(null)
  const resizeStartX = useRef(0)
  const resizeStartW = useRef(0)

  const flash = (msg: string) => { setActionMsg(msg); setTimeout(() => setActionMsg(null), 3000) }

  /* ── Fetch ── */
  const fetchEmployers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/applications`, { headers: headers() })
      if (!res.ok) {
        if (res.status === 403) {
          setError('인증 오류. 다시 로그인해주세요.')
          return
        }
        throw new Error('데이터 로딩 실패')
      }
      const json = await res.json()
      if (!json.success) throw new Error(json.message || 'Error')
      const all: EmployerApp[] = (json.data ?? []).filter((a: EmployerApp) => a.type === 'employer')
      setEmployers(all)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => { if (authed) fetchEmployers() }, [authed, fetchEmployers])

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

  /* ── NEW 확인 ── */
  const confirmNew = useCallback((id: string) => {
    setConfirmedIds(prev => {
      const next = new Set(prev)
      next.add(id)
      saveConfirmed(next)
      return next
    })
  }, [])

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

  /* ── 탭 + 필터 적용 ── */
  const filtered = useMemo(() => {
    let list = employers

    // 탭 필터
    if (tab === 'active') {
      list = list.filter(e => e.status !== 'blacklist' && ['new', 'contacted', 'interviewing'].includes(e.status))
    } else if (tab === 'mailing') {
      list = list.filter(e => e.status !== 'blacklist')
    } else if (tab === 'blacklist') {
      list = list.filter(e => e.status === 'blacklist')
    }
    // 'all' → 전체

    // 다수선택 필터
    if (filterProvince.length > 0) {
      list = list.filter(e => filterProvince.includes(extractProvince(e.location)))
    }
    if (filterCity.length > 0) {
      list = list.filter(e => filterCity.includes(extractCity(e.location)))
    }
    if (filterAge.length > 0) {
      list = list.filter(e => {
        const ages = extractAgeLabels(e.teaching_age)
        return filterAge.some(a => ages.includes(a))
      })
    }
    if (filterStatus.length > 0) {
      list = list.filter(e => filterStatus.includes(e.status))
    }

    return list
  }, [employers, tab, filterProvince, filterCity, filterAge, filterStatus])

  /* ── NEW 카운트 ── */
  const newUnconfirmedCount = useMemo(() => {
    return employers.filter(e => e.status === 'new' && !confirmedIds.has(e.id)).length
  }, [employers, confirmedIds])

  /* ── 메일링 선택 ── */
  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectAll = () => {
    const ids = filtered.map(e => e.id)
    setSelectedIds(new Set(ids))
  }

  const selectNone = () => setSelectedIds(new Set())

  const selectFirst10 = () => {
    const ids = filtered.slice(0, 10).map(e => e.id)
    setSelectedIds(new Set(ids))
  }

  const openMailComposer = (list?: EmployerApp[]) => {
    const targets = list || filtered.filter(e => selectedIds.has(e.id))
    if (targets.length === 0) { flash('수신자를 선택해주세요'); return }
    setMailRecipients(targets)
    setShowMailComposer(true)
  }

  /* ── 탭 전환 ── */
  const switchTab = (t: TabKey) => {
    setTab(t)
    if (t === 'mailing') {
      setViewMode('excel')
    }
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
      case 'no': return jobNo(app)
      case 'province': return province
      case 'city': return city
      case 'name': return showPII ? (v(app.school_name) || v(app.name)) : maskName(app.school_name || app.name)
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
  const isMailing = tab === 'mailing'
  const isBlacklistTab = tab === 'blacklist'
  const hasFilters = filterProvince.length > 0 || filterCity.length > 0 || filterAge.length > 0 || filterStatus.length > 0

  /* ══════ RENDER ══════ */
  return (
    <div className="space-y-5">
      {/* Blink 애니메이션 */}
      <style>{`
        @keyframes employer-blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
        .employer-blink { animation: employer-blink 0.8s ease-in-out infinite; }
      `}</style>

      {/* ── 헤더 ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[22px] font-bold text-[#1d1d1f] tracking-tight">구인자관리</h1>
          <p className="text-[13px] text-[#86868b] mt-0.5">
            {hasFilters ? `${filtered.length} / ${employers.length}건` : `${employers.length}건`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {actionMsg && <span className="text-[12px] text-green-600 font-medium bg-green-50 px-3 py-1 rounded-lg">{actionMsg}</span>}
          <button type="button" onClick={fetchEmployers} className="text-[12px] text-[#0071e3] hover:underline font-medium">새로고침</button>
        </div>
      </div>

      {/* ── 상단 탭 4개 ── */}
      <div className="flex items-end gap-1">
        {([
          { key: 'active' as TabKey, label: '활발한 채용보기' },
          { key: 'all' as TabKey, label: '전체보기' },
          { key: 'mailing' as TabKey, label: '메일링' },
          { key: 'blacklist' as TabKey, label: '블랙리스트' },
        ]).map(t => (
          <div key={t.key} className="relative">
            {/* NEW 뱃지 */}
            {t.key === 'active' && newUnconfirmedCount > 0 && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full employer-blink whitespace-nowrap">
                NEW {newUnconfirmedCount}
              </span>
            )}
            <button
              type="button"
              onClick={() => switchTab(t.key)}
              className={`px-4 py-2.5 text-[13px] font-semibold rounded-t-xl transition-colors border border-b-0 ${
                tab === t.key
                  ? 'bg-white text-[#1d1d1f] border-gray-200'
                  : 'bg-gray-100 text-gray-500 border-transparent hover:text-gray-700'
              }`}
            >
              {t.label}
            </button>
          </div>
        ))}
      </div>

      {/* ── 필터 + 뷰 토글 바 ── */}
      <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4">
        <div className="flex flex-wrap items-center gap-2">
          {/* 뷰 모드 (메일링탭이 아닐 때만) */}
          {!isMailing && (
            <>
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
            </>
          )}

          {/* 엑셀 스타일 다수선택 필터 */}
          <ExcelFilter label="전체 지역" options={provinceOptions} selected={filterProvince} onChange={v => { setFilterProvince(v); setFilterCity([]) }} />
          <ExcelFilter label="전체 도시" options={cityOptions} selected={filterCity} onChange={setFilterCity} />
          <ExcelFilter label="전체 대상" options={ageOptions} selected={filterAge} onChange={setFilterAge} />
          <ExcelFilter label="상태" options={statusOptions} selected={filterStatus} onChange={setFilterStatus} />

          {hasFilters && (
            <button type="button" onClick={() => { setFilterProvince([]); setFilterCity([]); setFilterAge([]); setFilterStatus([]) }}
              className="text-[11px] text-red-500 hover:text-red-700 font-medium">초기화</button>
          )}

          <div className="flex-1" />

          {/* PII 토글 */}
          <label className="flex items-center gap-1.5 text-[12px] text-gray-500 cursor-pointer select-none">
            <input type="checkbox" checked={showPII} onChange={e => setShowPII(e.target.checked)}
              className="w-3.5 h-3.5 rounded border-gray-300 text-red-600 focus:ring-red-500" />
            PII 표시
          </label>

          {/* 열 관리 (엑셀뷰에서만) */}
          {(viewMode === 'excel' || isMailing) && (
            <button type="button" onClick={() => setShowColumnMgr(true)}
              className="text-[11px] text-gray-500 hover:text-gray-700 font-medium border border-gray-200 px-2 py-1 rounded-lg">
              열 관리
            </button>
          )}
        </div>

        {/* 메일링 탭: 선택 버튼 */}
        {isMailing && (
          <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100">
            <button type="button" onClick={selectAll} className="text-[11px] px-2.5 py-1 bg-gray-100 rounded-lg hover:bg-gray-200 font-medium">전체선택</button>
            <button type="button" onClick={selectNone} className="text-[11px] px-2.5 py-1 bg-gray-100 rounded-lg hover:bg-gray-200 font-medium">선택취소</button>
            <button type="button" onClick={selectFirst10} className="text-[11px] px-2.5 py-1 bg-gray-100 rounded-lg hover:bg-gray-200 font-medium">10개선택</button>
            <span className="text-[12px] text-blue-600 font-semibold ml-2">{selectedIds.size}명 선택</span>
            <div className="flex-1" />
            <button
              type="button"
              onClick={() => openMailComposer()}
              disabled={selectedIds.size === 0}
              className="px-4 py-2 bg-[#0071E3] text-white text-[12px] font-semibold rounded-lg hover:bg-[#0066CC] transition-colors disabled:opacity-40"
            >
              메일 보내기 ({selectedIds.size}명)
            </button>
          </div>
        )}
      </div>

      {/* ── 에러 / 로딩 ── */}
      {error && <div className="p-4 bg-red-50 text-red-600 text-[13px] rounded-2xl">{error}</div>}
      {loading && <div className="text-center py-16 text-[#86868b] animate-pulse text-[14px]">로딩 중...</div>}

      {/* ── 콘텐츠 ── */}
      {!loading && !error && (
        <>
          {/* ── 워드뷰 ── */}
          {viewMode === 'word' && !isMailing && (
            <div className="space-y-4">
              {filtered.length === 0 && (
                <div className="text-center py-16 text-[#86868b] text-[14px]">데이터가 없습니다.</div>
              )}
              {filtered.map((app, idx) => (
                <DocBlock
                  key={app.id}
                  employer={app}
                  isNew={app.status === 'new'}
                  isConfirmed={confirmedIds.has(app.id)}
                  isBlacklist={app.status === 'blacklist'}
                  showPII={showPII}
                  province={extractProvince(app.location)}
                  city={extractCity(app.location)}
                  onConfirm={confirmNew}
                  onStatusChange={updateStatus}
                  showDivider={(idx + 1) % 2 === 0 && idx < filtered.length - 1}
                />
              ))}
            </div>
          )}

          {/* ── 엑셀뷰 / 메일링뷰 ── */}
          {(viewMode === 'excel' || isMailing) && (
            <div className="bg-white border border-[#e5e5e7] rounded-2xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full" style={{ tableLayout: 'fixed', minWidth: `${visibleCols.reduce((a, c) => a + c.width, 0) + (isMailing ? 120 : 0)}px` }}>
                  <colgroup>
                    {isMailing && <col style={{ width: '50px' }} />}
                    {visibleCols.map(c => <col key={c.key} style={{ width: `${c.width}px` }} />)}
                    {isMailing && <col style={{ width: '70px' }} />}
                  </colgroup>
                  <thead>
                    <tr className="bg-[#f5f5f7] text-[11px] text-[#86868b] uppercase tracking-wider" style={{ position: 'sticky', top: 0, zIndex: 20 }}>
                      {isMailing && (
                        <th className="px-2 py-3 text-center">
                          <input
                            type="checkbox"
                            checked={selectedIds.size === filtered.length && filtered.length > 0}
                            onChange={() => selectedIds.size === filtered.length ? selectNone() : selectAll()}
                            className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600"
                          />
                        </th>
                      )}
                      {visibleCols.map(c => (
                        <th key={c.key} className="px-3 py-3 text-left font-semibold relative group">
                          {c.label}
                          {/* 리사이즈 핸들 */}
                          <div
                            className="absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize opacity-0 group-hover:opacity-100 hover:bg-blue-300 transition-opacity"
                            onMouseDown={e => startResize(c.key, e)}
                          />
                        </th>
                      ))}
                      {isMailing && (
                        <th className="px-2 py-3 text-center font-semibold">메뉴</th>
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#f0f0f2]">
                    {filtered.map(app => {
                      const isBlacklist = app.status === 'blacklist'
                      const isNew = app.status === 'new' && !confirmedIds.has(app.id)
                      const no = jobNo(app)
                      const isNewCode = isNewJobCode(no)
                      return (
                        <tr
                          key={app.id}
                          className={`transition-colors ${
                            isBlacklist ? 'bg-[rgba(220,38,38,0.04)]' : 'hover:bg-[#f0f4ff]'
                          } ${isNew ? 'employer-blink' : ''}`}
                          style={isBlacklist ? { borderLeft: '3px solid rgba(220,38,38,0.4)' } : undefined}
                        >
                          {isMailing && (
                            <td className="px-2 py-2.5 text-center">
                              <input
                                type="checkbox"
                                checked={selectedIds.has(app.id)}
                                onChange={() => toggleSelect(app.id)}
                                className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600"
                              />
                            </td>
                          )}
                          {visibleCols.map(c => (
                            <td key={c.key} className="px-3 py-2.5 text-[13px] truncate" title={cellValue(app, c.key)}>
                              {c.key === 'no' ? (
                                <code className={`px-1.5 py-0.5 text-[11px] font-bold rounded ${
                                  isNewCode ? 'bg-blue-600 text-white' : 'bg-[#1d1d1f] text-white'
                                }`} style={{ fontFamily: 'Consolas, monospace' }}>{no}</code>
                              ) : c.key === 'status' ? (
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
                              {/* NEW 확인 버튼 (No. 열 옆) */}
                              {c.key === 'no' && isNew && (
                                <button
                                  type="button"
                                  onClick={() => confirmNew(app.id)}
                                  className="ml-2 px-1.5 py-0.5 bg-red-500 text-white text-[9px] font-bold rounded hover:bg-red-600 employer-blink"
                                >
                                  NEW
                                </button>
                              )}
                              {/* 블랙리스트 뱃지 */}
                              {c.key === 'status' && isBlacklist && (
                                <span className="ml-1 px-1 py-0.5 bg-red-100 text-red-700 text-[9px] font-bold rounded">BLOCK</span>
                              )}
                            </td>
                          ))}
                          {isMailing && (
                            <td className="px-2 py-2.5 text-center">
                              <button
                                type="button"
                                onClick={() => openMailComposer([app])}
                                className="px-2 py-1 bg-blue-50 text-blue-600 text-[11px] font-semibold rounded-lg hover:bg-blue-100 transition-colors"
                              >
                                메일
                              </button>
                            </td>
                          )}
                        </tr>
                      )
                    })}
                    {filtered.length === 0 && (
                      <tr>
                        <td colSpan={visibleCols.length + (isMailing ? 2 : 0)} className="text-center py-16 text-[#86868b] text-[14px]">
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
    </div>
  )
}
