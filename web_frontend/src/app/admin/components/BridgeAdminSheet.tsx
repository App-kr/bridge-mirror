'use client'

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { API_URL } from '@/lib/api'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import AllCandidatesGrid from './AllCandidatesGrid'
import SecureAdminImage from '@/components/SecureAdminImage'
import LinkPanel from './LinkPanel'
import '../sheet/google-sheets-theme.css'

/* ─── Types ─── */
type CategoryKey = 'active' | 'past' | 'blacklist'
type TabKey = 'active' | 'past' | 'blacklist' | 'all'
type ColType = 'idx' | 't' | 'photo' | 'long' | 'mail' | 'tags' | 'stage' | 'dropdown'

interface Stage { key: string; label: string; color: string; text: string }
interface MailTemplate { key: string; label: string; s: string; b: string }
interface MailTag { key: string; label: string; c: string }
interface TabDef { key: TabKey; label: string; color: string; bg: string; accent: string; icon: string }
interface ColDef { key: string; label: string; w: number; type: ColType; v: boolean; opts?: string[] }
interface StatusRow { id: string; label: string; bg: string; text: string; h: number }
type DataRow = { id: number; category: string; stage: string; mailStatus: string; photoUrl: string; photoSize: number; [key: string]: string | number }
interface DataStore { active: DataRow[]; past: DataRow[]; blacklist: DataRow[] }
interface UndoSnapshot { d: DataStore; s: StatusRow[]; db: DataRow[] }
interface EditCellState { id: number; key: string }
interface CtxMenu { x: number; y: number; row: DataRow }
interface ColMenuState { x: number; y: number; key: string }

/* ─── Constants ─── */
const STAGES: Stage[] = [
  { key: 'none', label: '—', color: '#fff', text: '#000' },
  { key: 'interview', label: '인터뷰', color: '#fef9c3', text: '#000' },
  { key: 'proposal', label: '계약제안', color: '#fde68a', text: '#000' },
  { key: 'signed', label: '서명완료', color: '#bbf7d0', text: '#000' },
  { key: 'guide_sent', label: '안내발송', color: '#93c5fd', text: '#000' },
  { key: 'guide_done', label: '안내완료', color: '#dbeafe', text: '#000' },
  { key: 'caution', label: '주의', color: '#fecaca', text: '#000' },
  { key: 'lost', label: '두절', color: '#e5e7eb', text: '#666' },
]
const MTP: MailTemplate[] = [
  { key: 'interview', label: 'Interview', s: '[BRIDGE] Interview', b: 'Dear {{name}},\n\nInterview arranged.\n\nBRIDGE' },
  { key: 'contract', label: 'Contract', s: '[BRIDGE] Contract', b: 'Dear {{name}},\n\nContract attached.\n\nBRIDGE' },
  { key: 'visa', label: 'Visa', s: '[BRIDGE] Visa Guide', b: 'Dear {{name}},\n\nVisa guide attached.\n\nBRIDGE' },
  { key: 'settle', label: 'Settlement', s: '[BRIDGE] Settlement', b: 'Dear {{name}},\n\nSettlement guide.\n\nBRIDGE' },
  { key: 'tax', label: 'Tax', s: '[BRIDGE] Tax Info', b: 'Dear {{name}},\n\nTax info.\n\nBRIDGE' },
  { key: 'transfer', label: 'Transfer', s: '[BRIDGE] Transfer', b: 'Dear {{name}},\n\nTransfer guide.\n\nBRIDGE' },
  { key: 'renewal', label: 'Renewal', s: '[BRIDGE] Renewal', b: 'Dear {{name}},\n\nRenewal info.\n\nBRIDGE' },
  { key: 'custom', label: 'Write', s: '', b: '' },
]
const MTAGS: MailTag[] = [
  { key: 'guide_done', label: '가이드✓', c: '#16a34a' },
  { key: 'contract_sent', label: '계약발송', c: '#2563eb' },
  { key: 'contract_done', label: '계약✓', c: '#16a34a' },
  { key: 'visa_sent', label: '비자✓', c: '#7c3aed' },
  { key: 'housing_sent', label: '숙소✓', c: '#0891b2' },
  { key: 'ot_done', label: 'OT✓', c: '#16a34a' },
]
const H_OPTS = ['숙소제공', '월세제공', '보증+월세', '불필요', '자체']
const FEE_OPTS = ['선금완료', '잔금완료', '일시납완료', '연체중', '14일연체', '장기연체']
const PROC_OPTS = ['진행중', '완료', '보류', '취소', '무단이탈']
const TABS: TabDef[] = [
  { key: 'active', label: '구직활동중', color: '#2563eb', bg: '#dbeafe', accent: '#1d4ed8', icon: '👤' },
  { key: 'past', label: '체결완료', color: '#16a34a', bg: '#dcfce7', accent: '#166534', icon: '✅' },
  { key: 'blacklist', label: '블랙리스트', color: '#dc2626', bg: '#fee2e2', accent: '#991b1b', icon: '⛔' },
  { key: 'all', label: '전체', color: '#0f172a', bg: '#e2e8f0', accent: '#020617', icon: '📋' },
]
const PC = ['#3b82f6', '#ef4444', '#22c55e', '#eab308', '#a855f7', '#06b6d4', '#f43e5e', '#84cc16', '#d946ef', '#14b8a6']
const SK = 'bridge-v10'
const SK_EDITS = 'bridge-v10-edits'   // {[cid]: {stage, mailStatus, ...}}
const SK_DATA  = 'bridge-v10-data'    // {active, past, blacklist} 수동 관리 탭
const PAGE_SIZE = 150
const API = API_URL

// 프론트엔드 필드명 → 백엔드 DB 컬럼명 매핑
const FB_MAP: Record<string, string> = {
  name: 'full_name', arc: 'arc_holders', background: 'ancestry',
  age: 'dob', currentLoc: 'current_location', startDate: 'start_date',
  university: 'target', prefRegion: 'area_prefs', totalExp: 'experience',
  preference: 'preferences', applied: 'job_prefs', proposal: 'recruiter_memo',
  curSalary: 'current_salary', hopeSalary: 'desired_salary',
  interviewCol: 'interview_time', degree: 'education_level',
  cert: 'certification', docs: 'doc_status', health: 'health_info',
  family: 'dependents', e2visa: 'visa_type', kakao: 'kakaotalk',
  phone: 'mobile_phone', crimCheck: 'criminal_record_check',
  domesticCrim: 'korean_criminal_record', infoProvide: 'consent',
  verified: 'fact_check', source: 'how_to',
  hired: 'placed_company', wage: 'placed_salary', moveIn: 'start_month',
  housingCost: 'housing_detail', introFee: 'referral_fee',
  process: 'process_date', history: 'past_placement',
}

/* ─── Override localStorage helpers ─── */
type EditOverride = Partial<Pick<DataRow, 'stage' | 'mailStatus' | 'proposal' | 'notice' | 'applied' | 'history' | 'reference' | 'photoUrl' | 'photoSize' | 'category'>>
function loadEdits(): Record<string, EditOverride> {
  try { return JSON.parse(localStorage.getItem(SK_EDITS) || '{}') } catch { return {} }
}
function saveEdit(cid: string, patch: EditOverride) {
  try {
    const edits = loadEdits()
    edits[cid] = { ...(edits[cid] || {}), ...patch }
    localStorage.setItem(SK_EDITS, JSON.stringify(edits))
  } catch { /* ignore */ }
}

/* ─── DB → DataRow mapping ─── */
function mapCandidateToRow(c: Record<string, unknown>, idx: number, edits: Record<string, EditOverride>): DataRow {
  const cid = String(c.candidate_id ?? c.id ?? '')
  const ov = edits[cid] || {}
  const dbStatus = String(c.status ?? '')
  const cat: CategoryKey = dbStatus === 'Active' ? 'active' :
    (dbStatus.toLowerCase() === 'blacklist' ? 'blacklist' : 'past')
  const tattoo = [c.tattoo, c.piercings].filter(Boolean).join('/')
  const ts = String(c.created_at ?? '').slice(0, 10).replace(/-/g, '.').slice(2)
  const isWebForm = String(c.source) === 'web_form'
  return {
    id: idx + 1,
    _cid: cid,
    category: ov.category ?? cat,
    stage: ov.stage ?? String(c.stage ?? 'none'),
    mailStatus: ov.mailStatus ?? String(c.mail_tags ?? ''),
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
    reference: ov.reference ?? String(c.reference ?? ''),
    totalExp: String(c.experience ?? ''),
    notice: ov.notice ?? '',
    preference: String(c.preferences ?? ''),
    applied: ov.applied ?? String(c.job_prefs ?? ''),
    proposal: ov.proposal ?? String(c.recruiter_memo ?? ''),
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
    history: ov.history ?? String(c.past_placement ?? ''),
  }
}
const SROWS_I: StatusRow[] = [
  { id: 's1', label: '인터뷰', bg: '#fff', text: '아르테4977 강서프라5513 5271', h: 40 },
  { id: 's2', label: '제안', bg: '#ffff00', text: '에더빈5092', h: 40 },
  { id: 's3', label: '체결', bg: '#ff9900', text: '키베918/해운대사4583/실리4763/서초프라4681', h: 40 },
]

function initCols(): ColDef[] {
  return [
    { key: 'rowNum', label: '#', w: 42, type: 'idx', v: true },
    { key: 'email', label: '메일', w: 190, type: 't', v: true },
    { key: 'name', label: '이름', w: 140, type: 't', v: true },
    { key: 'photo', label: '사진', w: 65, type: 'photo', v: true },
    { key: 'mgtNum', label: '번호', w: 65, type: 't', v: true },
    { key: 'arc', label: 'ARC', w: 120, type: 't', v: true },
    { key: 'nationality', label: '국적', w: 62, type: 't', v: true },
    { key: 'background', label: '배경', w: 75, type: 't', v: true },
    { key: 'age', label: '나이', w: 46, type: 't', v: true },
    { key: 'gender', label: '성별', w: 46, type: 't', v: true },
    { key: 'currentLoc', label: '현위치', w: 62, type: 't', v: true },
    { key: 'startDate', label: '시작', w: 78, type: 't', v: true },
    { key: 'university', label: '대상', w: 50, type: 't', v: true },
    { key: 'prefRegion', label: '선호지역', w: 75, type: 't', v: true },
    { key: 'reference', label: '레퍼런스', w: 210, type: 'long', v: true },
    { key: 'totalExp', label: '총경력', w: 62, type: 't', v: true },
    { key: 'notice', label: '통보', w: 52, type: 't', v: true },
    { key: 'preference', label: '선호/인터뷰', w: 190, type: 'long', v: true },
    { key: 'applied', label: '지원/요청', w: 175, type: 'long', v: true },
    { key: 'proposal', label: '포지션제안', w: 175, type: 'long', v: true },
    { key: 'mailAction', label: '메일발송', w: 85, type: 'mail', v: true },
    { key: 'mailStatus', label: '발송상태', w: 210, type: 'tags', v: true },
    { key: 'stage', label: '진행단계', w: 140, type: 'stage', v: true },
    { key: 'curSalary', label: '현급여', w: 62, type: 't', v: true },
    { key: 'hopeSalary', label: '희망', w: 62, type: 't', v: true },
    { key: 'interviewCol', label: '인터뷰', w: 78, type: 't', v: true },
    { key: 'degree', label: '학위', w: 58, type: 't', v: true },
    { key: 'major', label: '전공', w: 72, type: 't', v: true },
    { key: 'cert', label: '자격증', w: 70, type: 't', v: true },
    { key: 'docs', label: '서류', w: 65, type: 't', v: true },
    { key: 'health', label: '건강', w: 52, type: 't', v: true },
    { key: 'tattooPiercing', label: '타투피어싱', w: 75, type: 't', v: true },
    { key: 'family', label: '가족', w: 52, type: 't', v: true },
    { key: 'married', label: '결혼', w: 48, type: 't', v: true },
    { key: 'housing', label: '숙소', w: 100, type: 'dropdown', opts: H_OPTS, v: true },
    { key: 'religion', label: '종교', w: 52, type: 't', v: true },
    { key: 'e2visa', label: 'E2', w: 52, type: 't', v: true },
    { key: 'kakao', label: '카톡', w: 100, type: 't', v: true },
    { key: 'phone', label: '폰번호', w: 125, type: 't', v: true },
    { key: 'crimCheck', label: '범죄', w: 55, type: 't', v: true },
    { key: 'domesticCrim', label: '국내범죄', w: 70, type: 't', v: true },
    { key: 'infoProvide', label: '정보제공', w: 65, type: 't', v: true },
    { key: 'verified', label: '사실확인', w: 65, type: 't', v: true },
    { key: 'source', label: '경로', w: 65, type: 't', v: true },
    { key: 'timestamp', label: '타임', w: 85, type: 't', v: true },
    { key: 'hired', label: '채용', w: 65, type: 't', v: true },
    { key: 'wage', label: '급여', w: 60, type: 't', v: true },
    { key: 'moveIn', label: '개시일', w: 70, type: 't', v: true },
    { key: 'housingCost', label: '숙박', w: 55, type: 't', v: true },
    { key: 'introFee', label: '소개료', w: 100, type: 'dropdown', opts: FEE_OPTS, v: true },
    { key: 'process', label: '처리여부', w: 100, type: 'dropdown', opts: PROC_OPTS, v: true },
    { key: 'history', label: '과거기록', w: 150, type: 'long', v: true },
  ]
}

function mkRow(id: number, cat: string): DataRow {
  const r: DataRow = { id, category: cat, stage: 'none', mailStatus: '', photoUrl: '', photoSize: 50 }
  initCols().forEach(c => { if (!['rowNum', 'stage', 'mailStatus', 'photo'].includes(c.key)) r[c.key] = '' })
  return r
}

function mkD(): DataStore {
  return {
    active: [
      { id: 59, email: 'aceyumull@gmail.com', name: 'Ace Darrick Yumul', photoUrl: '', photoSize: 50, mgtNum: '5671', arc: 'E2 26/06/28', nationality: '미국', background: 'EPIK 2yr', age: '91', gender: 'M', currentLoc: '서울', startDate: '26.03.08', university: '무', prefRegion: '수도권', reference: 'SLA전주2511', totalExp: '7년', notice: '', preference: 'LOR', applied: '', proposal: '', mailAction: '', mailStatus: '', stage: 'interview', curSalary: '2.2', hopeSalary: '', interviewCol: '', degree: '학사', major: '경영', cert: '', docs: '', health: '', tattooPiercing: '', family: '', married: '', housing: '숙소제공', religion: '', e2visa: 'E2', kakao: 'aceyumul', phone: '010-1234-5678', crimCheck: '', domesticCrim: '', infoProvide: '', verified: '', source: 'CL', timestamp: '26.01.15', hired: '', wage: '', moveIn: '', housingCost: '', introFee: '', process: '', history: '', category: 'active' },
      { id: 53, email: 'sarahm@gmail.com', name: 'Sarah Mitchell', photoUrl: '', photoSize: 50, mgtNum: '5680', arc: 'E2 31/12/2025', nationality: '캐나다', background: 'Hagwon', age: '97', gender: 'F', currentLoc: '한국', startDate: '26.05.01', university: '유', prefRegion: '부산', reference: 'ABC Gijang\n010-9876-5432', totalExp: '1년', notice: '', preference: '초등/유치원', applied: '기장', proposal: '기장A 제안', mailAction: '', mailStatus: 'guide_done,contract_sent', stage: 'proposal', curSalary: '2.3', hopeSalary: '2.5', interviewCol: '3/5', degree: '학사', major: '교육', cert: 'CELTA', docs: 'O', health: '양호', tattooPiercing: 'X/귀', family: '미혼', married: 'X', housing: '월세제공', religion: '기독교', e2visa: 'O', kakao: 'sarah_m93', phone: '010-5555-1234', crimCheck: '완료', domesticCrim: '없음', infoProvide: 'O', verified: 'O', source: 'FB', timestamp: '26.02.01', hired: '', wage: '', moveIn: '', housingCost: '', introFee: '선금완료', process: '진행중', history: '', category: 'active' },
    ],
    past: [
      { id: 101, email: 'tomh@gmail.com', name: 'Tom Hughes', photoUrl: '', photoSize: 50, mgtNum: '5500', arc: 'E2 만료', nationality: '아일랜드', background: '2yr', age: '91', gender: 'M', currentLoc: '귀국', startDate: '25.03.01', university: '유', prefRegion: '서울', reference: 'GHI\n010-2222-3333', totalExp: '2년', notice: '', preference: '', applied: '', proposal: '종로A→완료', mailAction: '', mailStatus: 'guide_done,contract_done,ot_done', stage: 'guide_done', curSalary: '2.5', hopeSalary: '', interviewCol: '완료', degree: '학사', major: '역사', cert: '', docs: 'O', health: '양호', tattooPiercing: 'X', family: '미혼', married: 'X', housing: '숙소제공', religion: '가톨릭', e2visa: '만료', kakao: 'tom_ire', phone: '010-1111-2222', crimCheck: '완료', domesticCrim: '없음', infoProvide: 'O', verified: 'O', source: 'FB', timestamp: '25.01', hired: 'O', wage: '2.5', moveIn: '25.03', housingCost: '학원', introFee: '잔금완료', process: '완료', history: '계약만료', category: 'past' },
    ],
    blacklist: [
      { id: 201, email: 'chrisx@gmail.com', name: 'Chris Xavier', photoUrl: '', photoSize: 50, mgtNum: '5400', arc: '', nationality: '미국', background: '', age: '94', gender: 'M', currentLoc: '불명', startDate: '25.06', university: '', prefRegion: '서울', reference: '', totalExp: '', notice: '', preference: '', applied: '', proposal: '', mailAction: '', mailStatus: '', stage: 'lost', curSalary: '', hopeSalary: '', interviewCol: '', degree: '', major: '', cert: '', docs: '', health: '', tattooPiercing: '', family: '', married: '', housing: '', religion: '', e2visa: '취소', kakao: 'chris_x', phone: '010-9999-0000', crimCheck: '', domesticCrim: '', infoProvide: '', verified: '', source: 'CL', timestamp: '25.05', hired: 'X', wage: '', moveIn: '', housingCost: '', introFee: '장기연체', process: '무단이탈', history: '무단이탈', category: 'blacklist' },
    ],
  }
}

/* ─── Hov ─── */
interface HovProps extends React.HTMLAttributes<HTMLDivElement> { bg?: string }
function Hov({ children, bg, style, ...p }: HovProps) {
  const [h, setH] = useState(false)
  return (
    <div onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{ ...style, background: h ? (bg || '#f0f0f0') : (style?.background || 'transparent') }} {...p}>
      {children}
    </div>
  )
}

/* ─── Main ─── */
export default function BridgeAdminSheet() {
  const { headers, adminKey } = useAdminAuth()
  const [data, setData] = useState<DataStore>({ active: [], past: [], blacklist: [] })
  const [tab, setTab] = useState<TabKey>('active')
  const [sRows, setSR] = useState<StatusRow[]>(SROWS_I)
  const [cols, setCols] = useState<ColDef[]>(initCols)
  const [rh, setRh] = useState<Record<number, number>>({})
  const [q, setQ] = useState('')
  const [filters, setFi] = useState<Record<string, Set<string>>>({})
  const [showFi, setShowFi] = useState<string | null>(null)
  const [ec, setEc] = useState<EditCellState | null>(null)
  const [ev, setEv] = useState('')
  const [esId, setEsId] = useState<string | null>(null)
  const [esV, setEsV] = useState('')
  const [sel, setSel] = useState<Set<number>>(new Set())
  const [ctx, setCtx] = useState<CtxMenu | null>(null)
  const [linkPanelRow, setLinkPanelRow] = useState<DataRow | null>(null)
  const [sk, setSk] = useState<string | null>(null)
  const [sd, setSd] = useState<'asc' | 'desc'>('asc')
  const [ready, setReady] = useState(false)
  const [mmOpen, setMmOpen] = useState(false)
  const [mmRecs, setMmRecs] = useState<DataRow[]>([])
  const [mmTmpl, setMmTmpl] = useState('custom')
  const [mmSubj, setMmSubj] = useState('')
  const [mmBody, setMmBody] = useState('')
  const [mmFiles, setMmFiles] = useState<File[]>([])
  const [frozenCols, setFC] = useState(3)
  const [colMenu, setColMenu] = useState<ColMenuState | null>(null)
  const [rnCol, setRnCol] = useState<string | null>(null)
  const [rnVal, setRnVal] = useState('')
  const [photoTarget, setPT] = useState<number | null>(null)
  const [eSRL, setESRL] = useState<string | null>(null)
  const [eSRV, setESRV] = useState('')
  const [undoStack, setUS] = useState<UndoSnapshot[]>([])
  const [dbAll, setDbAll] = useState<DataRow[]>([])       // DB 원본 (append)
  const [dbTotal, setDbTotal] = useState(0)               // DB 전체 건수
  const [loading, setLoading] = useState(false)
  const [lastSync, setLastSync] = useState('')
  const [newCount, setNewCount] = useState(0)

  // fetch 제어 refs
  const dbFetchingRef = useRef(false)
  const dbOffsetRef = useRef(0)        // 다음 로드 시작 offset
  const allLoadedRef = useRef(false)   // 모두 로드됐으면 true
  const wakeRetryRef = useRef(0)

  const eR = useRef<HTMLTextAreaElement>(null)
  const cR = useRef<{ i: number; sx: number; sw: number } | null>(null)
  const rR = useRef<{ id: number; sy: number; sh: number } | null>(null)
  const sRR = useRef<{ idx: number; sy: number; sh: number } | null>(null)
  const topRef = useRef<HTMLDivElement>(null)
  const tblRef = useRef<HTMLDivElement>(null)
  const syncR = useRef(false)
  const fRef = useRef<HTMLInputElement>(null)
  const photoRef = useRef<HTMLInputElement>(null)
  const editedCids = useRef<Set<string>>(new Set())

  const pushU = useCallback(() => {
    setUS(p => [...p, { d: JSON.parse(JSON.stringify(data)), s: JSON.parse(JSON.stringify(sRows)), db: JSON.parse(JSON.stringify(dbAll)) }].slice(-10))
  }, [data, sRows, dbAll])

  const undo = useCallback(() => {
    if (!undoStack.length) return
    const prev = undoStack[undoStack.length - 1]
    setData(prev.d); setSR(prev.s); if (prev.db) setDbAll(prev.db); setUS(p => p.slice(0, -1))
  }, [undoStack])

  /* localStorage — SSR 안전 */
  useEffect(() => {
    try {
      const s = localStorage.getItem(SK)
      if (s) {
        const p = JSON.parse(s) as { cw?: Record<string, number>; cl?: Record<string, string>; cv?: Record<string, boolean>; rh?: Record<number, number>; fc?: number }
        if (p.cw) setCols(pv => pv.map(c => ({ ...c, w: p.cw?.[c.key] ?? c.w, label: p.cl?.[c.key] || c.label, v: p.cv?.[c.key] !== undefined ? (p.cv[c.key] ?? true) : true })))
        if (p.rh) setRh(p.rh)
        if (p.fc !== undefined) setFC(p.fc)
      }
      // 수동 탭 데이터 복원 (구직활동중/체결완료/블랙리스트)
      const sd = localStorage.getItem(SK_DATA)
      if (sd) {
        const d = JSON.parse(sd) as DataStore
        if (d.active || d.past || d.blacklist)
          setData({ active: d.active || [], past: d.past || [], blacklist: d.blacklist || [] })
      }
    } catch { /* ignore */ }
    setReady(true)
  }, [])

  useEffect(() => {
    if (!ready) return
    try {
      const cw: Record<string, number> = {}; const cl: Record<string, string> = {}; const cv: Record<string, boolean> = {}
      cols.forEach(c => { cw[c.key] = c.w; cl[c.key] = c.label; cv[c.key] = c.v !== false })
      localStorage.setItem(SK, JSON.stringify({ cw, cl, cv, rh, fc: frozenCols }))
    } catch { /* ignore */ }
  }, [cols, rh, ready, frozenCols])

  // 수동 탭(active/past/blacklist) 변경 시 localStorage 저장
  useEffect(() => {
    if (!ready) return
    try { localStorage.setItem(SK_DATA, JSON.stringify(data)) } catch { /* ignore */ }
  }, [data, ready])

  /* DB 연동 — 150건씩 append 로드 (가상스크롤) */
  const loadMore = useCallback(async () => {
    if (dbFetchingRef.current || allLoadedRef.current) return
    dbFetchingRef.current = true
    setLoading(true)
    const currentOffset = dbOffsetRef.current
    const edits = loadEdits()
    const ctrl = new AbortController()
    const ctrlTimer = setTimeout(() => ctrl.abort(), 5000)
    let res: Response
    try {
      res = await fetch(
        `${API}/api/admin/candidates?limit=${PAGE_SIZE}&offset=${currentOffset}`,
        { headers: headers(), signal: ctrl.signal },
      )
      clearTimeout(ctrlTimer)
    } catch (e: unknown) {
      clearTimeout(ctrlTimer)
      dbFetchingRef.current = false
      setLoading(false)
      const isAbort = e instanceof DOMException && e.name === 'AbortError'
      wakeRetryRef.current += 1
      if (isAbort && wakeRetryRef.current <= 20) {
        setTimeout(() => loadMore(), 3000)
      }
      return
    }
    wakeRetryRef.current = 0
    try {
      if (!res.ok) return
      const json = await res.json()
      const rawRows: Record<string, unknown>[] = json.data?.candidates ?? []
      const total: number = json.data?.total ?? 0
      setDbTotal(total)
      const newRows = rawRows.map((c, i) => mapCandidateToRow(c, currentOffset + i, edits))
      setDbAll(prev => {
        const combined = [...prev, ...newRows]
        dbOffsetRef.current = combined.length
        return combined
      })
      if (rawRows.length < PAGE_SIZE) allLoadedRef.current = true
      if (currentOffset === 0) {
        const nc = rawRows.filter(r => String(r.source ?? r.how_to ?? '') === 'web_form').length
        setNewCount(nc)
      }
      setLastSync(new Date().toLocaleTimeString())
    } catch { /* ignore */ } finally {
      dbFetchingRef.current = false
      setLoading(false)
    }
  }, [headers])

  useEffect(() => {
    // 초기 로드: 첫 150건
    loadMore()
    // 60초마다 신규 web_form 폼 제출 감지
    const iv = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/admin/candidates?status=Active&limit=50`, { headers: headers() })
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

  /* Ctrl+Z */
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key === 'z') { e.preventDefault(); undo() } }
    document.addEventListener('keydown', h)
    return () => document.removeEventListener('keydown', h)
  }, [undo])

  /* Clipboard paste (image) */
  useEffect(() => {
    const h = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items
      if (!items) return
      for (const item of Array.from(items)) {
        if (item.type.startsWith('image/')) {
          e.preventDefault()
          const blob = item.getAsFile()
          if (!blob) return
          const rd = new FileReader()
          rd.onload = ev2 => {
            const t = photoTarget ?? [...sel][0]
            if (t === undefined) return
            pushU()
            setData(p => {
              const u: DataStore = { active: [], past: [], blacklist: [] }
              for (const k of Object.keys(p) as CategoryKey[]) u[k] = p[k].map(x => x.id === t ? { ...x, photoUrl: ev2.target?.result as string } : x)
              return u
            })
          }
          rd.readAsDataURL(blob)
          break
        }
      }
    }
    document.addEventListener('paste', h)
    return () => document.removeEventListener('paste', h)
  }, [photoTarget, sel, pushU])

  /* Mail modal */
  const openMM = (r: DataRow[]) => { setMmRecs(r); setMmTmpl('custom'); setMmSubj(''); setMmBody(''); setMmFiles([]); setMmOpen(true) }
  useEffect(() => {
    if (!mmOpen) return
    const t = MTP.find(m => m.key === mmTmpl)
    if (t && mmTmpl !== 'custom') { setMmSubj(t.s); setMmBody(t.b) }
  }, [mmTmpl, mmOpen])

  /* Scroll sync */
  const onTS = useCallback(() => {
    if (syncR.current) return; syncR.current = true
    if (tblRef.current && topRef.current) tblRef.current.scrollLeft = topRef.current.scrollLeft
    syncR.current = false
  }, [])
  const onBS = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    if (syncR.current) return; syncR.current = true
    if (topRef.current && tblRef.current) topRef.current.scrollLeft = tblRef.current.scrollLeft
    syncR.current = false
    // 스크롤 하단 200px 이내 → 다음 배치 append
    const el = e.currentTarget
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 200) loadMore()
  }, [loadMore])

  /* Derived */
  const visCols = useMemo(() => cols.filter(c => c.v !== false), [cols])
  // 전체 탭 = DB 원본(dbAll), 나머지 탭 = dbAll을 category로 필터링
  const allTD = useMemo(() => tab === 'all' ? dbAll : dbAll.filter(r => r.category === tab), [tab, dbAll])
  const cur = useMemo(() => {
    let it = [...allTD]
    Object.entries(filters).forEach(([k, v]) => { if (v?.size > 0) it = it.filter(r => v.has(String(r[k] || ''))) })
    if (q.trim()) { const s = q.toLowerCase(); it = it.filter(r => Object.values(r).some(v2 => String(v2).toLowerCase().includes(s))) }
    if (sk) it.sort((a, b) => { const av = String(a[sk] || ''), bv = String(b[sk] || ''); return sd === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av) })
    return it
  }, [allTD, filters, q, sk, sd])
  const rowVirtualizer = useVirtualizer({
    count: cur.length,
    getScrollElement: () => tblRef.current,
    estimateSize: useCallback((i: number) => rh[cur[i]?.id] || 58, [rh, cur]),
    overscan: 15,
  })
  const cnt = useMemo(() => ({
    active: dbAll.filter(r => r.category === 'active').length,
    past: dbAll.filter(r => r.category === 'past').length,
    blacklist: dbAll.filter(r => r.category === 'blacklist').length,
    all: dbTotal || dbAll.length,
  }), [dbAll, dbTotal])
  const gFO = useCallback((k: string) => { const v = new Set<string>(); allTD.forEach(r => { const val = String(r[k] || ''); if (val) v.add(val) }); return [...v].sort() }, [allTD])

  /* Column resize */
  const onCD = useCallback((e: React.MouseEvent, i: number) => {
    e.preventDefault(); cR.current = { i, sx: e.clientX, sw: visCols[i].w }
    const m = (ev2: MouseEvent) => { if (!cR.current) return; const key = visCols[cR.current.i].key; setCols(p => p.map(c => c.key === key ? { ...c, w: Math.max(30, cR.current!.sw + (ev2.clientX - cR.current!.sx)) } : c)) }
    const u = () => { cR.current = null; document.removeEventListener('mousemove', m); document.removeEventListener('mouseup', u) }
    document.addEventListener('mousemove', m); document.addEventListener('mouseup', u)
  }, [visCols])

  /* Row resize */
  const gH = useCallback((id: number) => rh[id] || 58, [rh])
  const onRD = useCallback((e: React.MouseEvent, id: number) => {
    e.preventDefault(); rR.current = { id, sy: e.clientY, sh: rh[id] || 58 }
    const m = (ev2: MouseEvent) => { if (!rR.current) return; setRh(p => ({ ...p, [rR.current!.id]: Math.max(30, rR.current!.sh + (ev2.clientY - rR.current!.sy)) })) }
    const u = () => { rR.current = null; document.removeEventListener('mousemove', m); document.removeEventListener('mouseup', u) }
    document.addEventListener('mousemove', m); document.addEventListener('mouseup', u)
  }, [rh])

  /* Status row resize */
  const onSRD = useCallback((e: React.MouseEvent, idx: number) => {
    e.preventDefault(); sRR.current = { idx, sy: e.clientY, sh: sRows[idx].h || 40 }
    const m = (ev2: MouseEvent) => { if (!sRR.current) return; setSR(p => p.map((r, i) => i === sRR.current!.idx ? { ...r, h: Math.max(22, sRR.current!.sh + (ev2.clientY - sRR.current!.sy)) } : r)) }
    const u = () => { sRR.current = null; document.removeEventListener('mousemove', m); document.removeEventListener('mouseup', u) }
    document.addEventListener('mousemove', m); document.addEventListener('mouseup', u)
  }, [sRows])

  /* Sort */
  const tS = (k: string) => { if (sk === k) setSd(d => d === 'asc' ? 'desc' : 'asc'); else { setSk(k); setSd('asc') } }

  /* Cell edit */
  const sE = (id: number, key: string, val: string) => {
    if (['rowNum', 'photo', 'mailAction', 'mailStatus', 'stage'].includes(key)) return
    if (cols.find(c => c.key === key)?.type === 'dropdown') return
    setEc({ id, key }); setEv(val || '')
  }
  const cE = () => {
    if (!ec) return; pushU()
    const row = [...data.active, ...data.past, ...data.blacklist, ...dbAll].find(r => r.id === ec.id)
    const cid = String(row?._cid ?? '')
    if (cid) {
      editedCids.current.add(cid)
      saveEdit(cid, { [ec.key]: ev } as EditOverride)
      patchDB(cid, { [FB_MAP[ec.key] || ec.key]: ev })
    }
    const applyEdit = (x: DataRow) => x.id === ec!.id ? { ...x, [ec!.key]: ev } : x
    setData(p => { const u: DataStore = { active: [], past: [], blacklist: [] }; for (const k of Object.keys(p) as CategoryKey[]) u[k] = p[k].map(applyEdit); return u })
    setDbAll(p => p.map(applyEdit))
    setEc(null)
  }
  useEffect(() => { if (ec && eR.current) eR.current.focus() }, [ec])

  /* Status row edit */
  const cSE = () => { if (!esId) return; pushU(); setSR(p => p.map(r => r.id === esId ? { ...r, text: esV } : r)); setEsId(null) }

  /* Stage / Field / Tag */
  const upData = (fn: (x: DataRow) => DataRow) => { pushU(); setData(p => { const u: DataStore = { active: [], past: [], blacklist: [] }; for (const k of Object.keys(p) as CategoryKey[]) u[k] = p[k].map(fn); return u }); setDbAll(p => p.map(fn)) }
  const patchDB = (cid: string, body: Record<string, unknown>) => {
    if (!cid) return
    fetch(`${API}/api/admin/candidates/${cid}`, {
      method: 'PATCH',
      headers: { ...headers(), 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).catch(() => {})
  }
  const setSt = (rid: number, s: string) => {
    const row = [...data.active, ...data.past, ...data.blacklist, ...dbAll].find(r => r.id === rid)
    const cid = String(row?._cid ?? '')
    if (cid) { editedCids.current.add(cid); saveEdit(cid, { stage: s }); patchDB(cid, { stage: s }) }
    upData(x => x.id === rid ? { ...x, stage: s } : x)
  }
  const setField = (rid: number, key: string, val: string) => {
    const row = [...data.active, ...data.past, ...data.blacklist, ...dbAll].find(r => r.id === rid)
    const cid = String(row?._cid ?? '')
    if (cid) { editedCids.current.add(cid); saveEdit(cid, { [key]: val } as EditOverride); patchDB(cid, { [FB_MAP[key] || key]: val }) }
    upData(x => x.id === rid ? { ...x, [key]: val } : x)
  }
  const tMT = (rid: number, tk: string) => {
    const row = [...data.active, ...data.past, ...data.blacklist, ...dbAll].find(r => r.id === rid)
    if (!row) return
    const c = String(row.mailStatus || '').split(',').filter(Boolean)
    const ms = (c.includes(tk) ? c.filter(i => i !== tk) : [...c, tk]).join(',')
    const cid = String(row._cid ?? '')
    if (cid) { editedCids.current.add(cid); saveEdit(cid, { mailStatus: ms }); patchDB(cid, { mail_tags: ms }) }
    upData(x => x.id === rid ? { ...x, mailStatus: ms } : x)
  }

  /* Context menu */
  const hC = (e: React.MouseEvent, row: DataRow) => { e.preventDefault(); setCtx({ x: e.clientX, y: e.clientY, row }) }
  const mv = (row: DataRow, cat: CategoryKey) => {
    pushU()
    const cid = String(row._cid ?? '')
    if (cid) saveEdit(cid, { category: cat })
    // category를 dbAll에서 업데이트 (모든 탭 공통)
    setDbAll(p => p.map(x => x.id === row.id ? { ...x, category: cat } : x))
    setData(p => { const u: DataStore = { active: [], past: [], blacklist: [] }; for (const k of Object.keys(p) as CategoryKey[]) u[k] = p[k].filter(x => x.id !== row.id); u[cat] = [...u[cat], { ...row, category: cat }]; return u })
    setCtx(null)
  }
  // 전체 탭에서는 삭제 불가 (DB 원본), 수동 탭에서만 삭제
  const dR = (row: DataRow) => {
    if (tab === 'all') { setCtx(null); return }
    pushU()
    setData(p => { const u: DataStore = { active: [], past: [], blacklist: [] }; for (const k of Object.keys(p) as CategoryKey[]) u[k] = p[k].filter(x => x.id !== row.id); return u })
    setCtx(null)
  }
  const delSR = (id: string) => { pushU(); setSR(p => p.filter(r => r.id !== id)) }
  const addSR = () => { pushU(); setSR(p => [...p, { id: 's' + Date.now(), label: 'New', bg: '#fff', text: '', h: 40 }]) }

  useEffect(() => {
    const h = () => { setCtx(null); setShowFi(null); setColMenu(null) }
    document.addEventListener('click', h); return () => document.removeEventListener('click', h)
  }, [])

  /* Add rows */
  const maxId = () => Math.max(...[...data.active, ...data.past, ...data.blacklist, ...dbAll].map(r => r.id), 0)
  const addN = () => {
    pushU(); const tt: CategoryKey = tab === 'all' ? 'active' : tab as CategoryKey
    const newRow = mkRow(maxId() + 1, tt)
    setData(p => ({ ...p, [tt]: [...p[tt], newRow] }))
    setDbAll(p => [...p, newRow])
  }
  const addRow = (aid: number) => {
    pushU(); const tt: CategoryKey = tab === 'all' ? 'active' : tab as CategoryKey
    const newRow = mkRow(maxId() + 1, tt)
    setData(p => { const u = { ...p }; const a = [...u[tt]]; const i = a.findIndex(r => r.id === aid); a.splice(i + 1, 0, newRow); u[tt] = a; return u })
    setDbAll(p => { const a = [...p]; const i = a.findIndex(r => r.id === aid); a.splice(i + 1, 0, newRow); return a })
  }

  /* Photo */
  const handlePhoto = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!photoTarget) return
    const f = e.target.files?.[0]; if (!f) return
    const tid = photoTarget; setPT(null)

    // 1) 서버 업로드 → DB PATCH → 로컬 state 갱신
    const fd = new FormData(); fd.append('file', f)
    fetch(`${API}/api/admin/upload-image`, { method: 'POST', headers: headers(), body: fd })
      .then(r => r.ok ? r.json() : null)
      .then(async j => {
        const url: string = j?.data?.url ?? ''
        // 로컬 state 갱신 (전체 + 수동 탭 모두)
        const fullUrl = url.startsWith('http') ? url : `${API}${url}`
        const applyUrl = (x: DataRow) => x.id === tid ? { ...x, photoUrl: fullUrl } : x
        pushU()
        upData(applyUrl)
        setDbAll(p => p.map(applyUrl))
        // DB PATCH (candidate_id 있는 경우)
        const targetRow = [...data.active, ...data.past, ...data.blacklist, ...dbAll].find(r => r.id === tid)
        const cid = String(targetRow?._cid ?? '')
        if (cid && url) {
          await fetch(`${API}/api/admin/candidates/${cid}`, {
            method: 'PATCH',
            headers: { ...headers(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ photo_url: url }),
          })
        }
      })
      .catch(() => {
        // 업로드 실패 시 base64 폴백
        const rd = new FileReader()
        rd.onload = ev2 => { pushU(); upData(x => x.id === tid ? { ...x, photoUrl: ev2.target?.result as string } : x) }
        rd.readAsDataURL(f)
      })
  }

  /* CSV */
  const expCSV = () => {
    const fc = visCols.filter(c => !['rowNum', 'photo', 'mailAction'].includes(c.key))
    const h = fc.map(c => c.label).join(',')
    const rs = cur.map(r => fc.map(c => `"${String(r[c.key] || '').replace(/"/g, '""').replace(/\n/g, ' ')}"`).join(','))
    const b = new Blob(['\uFEFF' + [h, ...rs].join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(b); const a = document.createElement('a'); a.href = url; a.download = `bridge_${tab}_${new Date().toISOString().slice(0, 10)}.csv`; a.click()
  }

  /* Selection */
  const tR = (id: number) => setSel(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n })
  const tA = () => setSel(p => p.size === cur.length ? new Set<number>() : new Set(cur.map(r => r.id)))
  const tF = (ck: string, v: string) => setFi(p => { const c = p[ck] ? new Set(p[ck]) : new Set<string>(); c.has(v) ? c.delete(v) : c.add(v); const n = { ...p }; if (!c.size) delete n[ck]; else n[ck] = c; return n })

  /* Helpers */
  const hdn = cols.filter(c => !c.v).length
  const tw = visCols.reduce((s, c) => s + c.w, 0) + 36
  const cti = TABS.find(t => t.key === tab)
  const getBg = (row: DataRow, ri: number, isSel: boolean) => {
    if (isSel) return '#bfdbfe'
    const st = STAGES.find(s => s.key === (row.stage || 'none'))
    if (st && st.key !== 'none') return st.color
    if (row.category === 'blacklist') return '#fee2e2'
    if (row.category === 'past') return '#f3f4f6'
    return ri % 2 === 0 ? '#fff' : '#fafbfc'
  }
  const isRed = (v: string) => Boolean(v && (v.includes('연체') || v.includes('무단')))

  if (!ready) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>Loading...</div>

  return (
    <div className="gs-sheet" style={{ fontFamily: "Roboto, Arial, 'Malgun Gothic', sans-serif", background: '#ffffff', height: '100%', minHeight: 400, fontSize: 13, display: 'flex', flexDirection: 'column', color: '#202124' }}>
      <input ref={photoRef} type="file" accept="image/*" onChange={handlePhoto} style={{ display: 'none' }} />

      {/* 상단 바 */}
      <div style={{ background: '#fff', padding: '8px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0, flexWrap: 'wrap', gap: 6, borderBottom: '2px solid #e2e8f0' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#0f172a' }}>원어민 관리</span>
          <span style={{ fontSize: 11, color: '#dc2626', background: '#fee2e2', padding: '2px 7px', borderRadius: 4, fontWeight: 700, border: '1px solid #fca5a5', letterSpacing: 1 }}>ADMIN</span>
          {newCount > 0 && (
            <span style={{ fontSize: 12, color: '#fff', background: '#ef4444', padding: '2px 9px', borderRadius: 12, fontWeight: 700, animation: 'pulse 2s infinite' }}>
              NEW {newCount}
            </span>
          )}
          {loading && <span style={{ fontSize: 12, color: '#2563eb' }}>로딩 중...</span>}
          {lastSync && !loading && <span style={{ fontSize: 11, color: '#9ca3af' }}>{dbAll.length.toLocaleString()} / {dbTotal > 0 ? dbTotal.toLocaleString() : '?'}건 · {lastSync}</span>}
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          <button onClick={undo} disabled={!undoStack.length} style={{ padding: '4px 10px', fontSize: 12, border: undoStack.length ? '1px solid #fca5a5' : '1px solid #e2e8f0', borderRadius: 5, background: undoStack.length ? '#fef2f2' : '#f8fafc', color: undoStack.length ? '#dc2626' : '#aaa', cursor: undoStack.length ? 'pointer' : 'default', fontWeight: 600 }}>↩ {undoStack.length}</button>
          {sel.size > 0 && <button onClick={() => { openMM(dbAll.filter(r => sel.has(r.id))) }} style={{ padding: '4px 10px', fontSize: 12, border: 'none', borderRadius: 5, background: '#7c3aed', color: '#fff', cursor: 'pointer', fontWeight: 600 }}>✉ {sel.size}명</button>}
          <button onClick={() => { dbFetchingRef.current = false; allLoadedRef.current = false; dbOffsetRef.current = 0; setDbAll([]); setTimeout(loadMore, 0) }} style={{ padding: '4px 10px', fontSize: 12, border: '1px solid #bfdbfe', borderRadius: 5, cursor: 'pointer', color: '#2563eb', background: '#eff6ff' }}>⟳ 동기화</button>
          <button onClick={addSR} style={{ padding: '4px 10px', fontSize: 12, border: '1px solid #e2e8f0', borderRadius: 5, cursor: 'pointer', color: '#475569' }}>+상태행</button>
          <button onClick={expCSV} style={{ padding: '4px 10px', fontSize: 12, border: '1px solid #e2e8f0', borderRadius: 5, cursor: 'pointer', color: '#475569' }}>↓CSV</button>
          <button onClick={addN} style={{ padding: '4px 12px', fontSize: 12, border: 'none', borderRadius: 5, background: '#2563eb', color: '#fff', cursor: 'pointer', fontWeight: 600 }}>+ 새 후보자</button>
        </div>
      </div>

      {/* 탭 */}
      <div style={{ background: '#fff', display: 'flex', borderBottom: '2px solid ' + (cti?.color || '#e2e8f0'), flexShrink: 0 }}>
        {TABS.map(t => { const ia = tab === t.key; return (
          <button key={t.key} onClick={() => { setTab(t.key); setSel(new Set()); setFi({}) }}
            style={{ flex: 1, padding: '9px 8px', fontSize: 13, fontWeight: ia ? 700 : 400, border: 'none', borderBottom: ia ? '2px solid ' + t.color : '2px solid transparent', background: ia ? t.bg : '#fff', color: ia ? t.accent : '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, transition: 'all 0.15s' }}>
            {t.label}
            <span style={{ fontSize: 11, fontWeight: 600, background: ia ? t.color : '#f1f5f9', color: ia ? '#fff' : '#64748b', padding: '1px 7px', borderRadius: 10 }}>{cnt[t.key]}</span>
          </button>
        )})}
      </div>

      {/* 툴바 */}
      <div style={{ background: '#f8fafc', padding: '8px 20px', display: 'flex', alignItems: 'center', gap: 12, borderBottom: '1px solid #e2e8f0', flexShrink: 0, flexWrap: 'wrap' }}>
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="⌕ 검색..." style={{ padding: '8px 14px', fontSize: 15, border: '2px solid #cbd5e1', borderRadius: 8, outline: 'none', width: 220 }} />
        <span style={{ fontSize: 14, fontWeight: 700 }}>열고정:</span>
        <select value={frozenCols} onChange={e => setFC(Number(e.target.value))} style={{ fontSize: 14, padding: '4px 8px', borderRadius: 6, border: '1px solid #cbd5e1' }}>
          {[0, 1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}</option>)}
        </select>
        {hdn > 0 && <button onClick={() => setCols(p => p.map(c => ({ ...c, v: true })))} style={{ padding: '4px 12px', fontSize: 13, border: '1px solid #06b6d4', borderRadius: 6, background: '#ecfeff', color: '#0e7490', cursor: 'pointer' }}>숨긴{hdn}열 표시</button>}
        <div style={{ display: 'flex', gap: 6, marginLeft: 'auto', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: 14, fontWeight: 700 }}>색:</span>
          {STAGES.filter(s => s.key !== 'none').map(s => <span key={s.key} style={{ fontSize: 13, padding: '4px 10px', borderRadius: 6, background: s.color, color: s.text }}>{s.label}</span>)}
        </div>
      </div>

      {/* 전체 탭: AG Grid + 스크롤 기반 append 로드 */}
      {tab === 'all' && (
        <AllCandidatesGrid
          rows={dbAll as Record<string, string | number>[]}
          onCopyTo={mv as (row: Record<string, string | number>, cat: 'active' | 'past' | 'blacklist') => void}
          loading={loading}
          total={dbTotal}
          onLoadMore={loadMore}
        />
      )}

      {/* 수동 탭: 상단 스크롤바 + 테이블 */}
      {tab !== 'all' && (
      <>
      <div ref={topRef} onScroll={onTS} style={{ overflowX: 'auto', overflowY: 'hidden', flexShrink: 0, height: 16, background: '#e2e8f0' }}>
        <div style={{ width: tw, height: 1 }} />
      </div>

      {/* 테이블 */}
      <div ref={tblRef} onScroll={onBS} className="gs-table" style={{ flex: 1, minHeight: 300, overflow: 'auto', background: '#fff' }}>
        <table style={{ borderCollapse: 'collapse', width: tw, minWidth: '100%', tableLayout: 'fixed' }}>
          <colgroup>
            <col style={{ width: 34 }} />
            {visCols.map((c, i) => <col key={i} style={{ width: c.w }} />)}
          </colgroup>
          <thead>
            {sRows.map((s, si) => (
              <tr key={s.id} style={{ height: s.h || 40 }}>
                <td style={{ background: '#f8fafc', border: '1px solid #d1d5db', textAlign: 'center', fontSize: 11, color: '#aaa', cursor: 'pointer', position: 'relative' }} onClick={() => delSR(s.id)}>
                  ×<div onMouseDown={e => onSRD(e, si)} style={{ position: 'absolute', bottom: -2, left: 0, right: 0, height: 5, cursor: 'row-resize' }} />
                </td>
                <td onDoubleClick={() => { setESRL(s.id); setESRV(s.label) }} style={{ padding: '4px 8px', border: '1px solid #d1d5db', fontWeight: 900, fontSize: 17, background: s.bg, cursor: 'pointer', minWidth: 60 }}>
                  {eSRL === s.id
                    ? <input value={eSRV} onChange={e => setESRV(e.target.value)} onBlur={() => { pushU(); setSR(p => p.map(r => r.id === eSRL ? { ...r, label: eSRV } : r)); setESRL(null) }} onKeyDown={e => { if (e.key === 'Enter') { pushU(); setSR(p => p.map(r => r.id === eSRL ? { ...r, label: eSRV } : r)); setESRL(null) } if (e.key === 'Escape') setESRL(null) }} autoFocus style={{ width: '100%', fontSize: 17, fontWeight: 900, border: '2px solid #2563eb', padding: '2px 6px', borderRadius: 3, boxSizing: 'border-box' }} />
                    : s.label}
                </td>
                <td colSpan={visCols.length - 1} onDoubleClick={() => { setEsId(s.id); setEsV(s.text) }} style={{ padding: '4px 8px', border: '1px solid #d1d5db', fontSize: 15, whiteSpace: 'pre-wrap', wordBreak: 'break-all', cursor: 'cell', background: s.bg === '#fff' ? '#fff' : s.bg + '25', position: 'relative' }}>
                  {esId === s.id ? <textarea ref={eR} value={esV} onChange={e => setEsV(e.target.value)} onBlur={cSE} onKeyDown={e => { if (e.key === 'Escape') setEsId(null) }} style={{ width: '100%', minHeight: 28, fontSize: 15, border: '2px solid #2563eb', padding: 3, resize: 'vertical' }} /> : s.text}
                  <div onMouseDown={e => onSRD(e, si)} style={{ position: 'absolute', bottom: -2, left: 0, right: 0, height: 5, cursor: 'row-resize' }} />
                </td>
              </tr>
            ))}
            <tr style={{ position: 'sticky', top: 0, zIndex: 30 }}>
              <th style={{ padding: 4, background: '#e2e8f0', border: '1px solid #94a3b8' }}>
                <input type="checkbox" checked={sel.size === cur.length && cur.length > 0} onChange={tA} style={{ cursor: 'pointer', width: 17, height: 17 }} />
              </th>
              {visCols.map((col, i) => {
                const hf = (filters[col.key]?.size || 0) > 0
                const isFr = i < frozenCols
                const leftOffset = 34 + visCols.slice(0, i).reduce((s, c) => s + c.w, 0)
                return (
                  <th key={col.key} onDoubleClick={() => { setRnCol(col.key); setRnVal(col.label) }} onContextMenu={e => { e.preventDefault(); e.stopPropagation(); setColMenu({ x: e.clientX, y: e.clientY, key: col.key }) }}
                    style={{ padding: '6px 4px', textAlign: 'center', fontWeight: 900, fontSize: 14, userSelect: 'none', position: isFr ? 'sticky' : 'relative', left: isFr ? leftOffset + 'px' : undefined, zIndex: isFr ? 31 : undefined, whiteSpace: 'normal', wordBreak: 'break-all', background: hf ? '#dbeafe' : '#e2e8f0', border: '1px solid #94a3b8' }}>
                    {rnCol === col.key
                      ? <input value={rnVal} onChange={e => setRnVal(e.target.value)} onBlur={() => { setCols(p => p.map(c => c.key === rnCol ? { ...c, label: rnVal } : c)); setRnCol(null) }} onKeyDown={e => { if (e.key === 'Enter') { setCols(p => p.map(c => c.key === rnCol ? { ...c, label: rnVal } : c)); setRnCol(null) } if (e.key === 'Escape') setRnCol(null) }} autoFocus style={{ width: '100%', fontSize: 13, border: '2px solid #2563eb', padding: '2px', textAlign: 'center', fontWeight: 800, borderRadius: 3, boxSizing: 'border-box' }} />
                      : <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 3, flexWrap: 'wrap' }}>
                          <span onClick={() => !['rowNum', 'photo', 'mailAction', 'mailStatus', 'stage'].includes(col.key) && col.type !== 'dropdown' && tS(col.key)} style={{ cursor: 'pointer' }}>{col.label}</span>
                          {sk === col.key && <span style={{ fontSize: 10, color: '#2563eb' }}>{sd === 'asc' ? '▲' : '▼'}</span>}
                          {!['rowNum', 'photo', 'mailAction', 'stage'].includes(col.key) && col.type !== 'dropdown' && <span onClick={e => { e.stopPropagation(); setShowFi(showFi === col.key ? null : col.key) }} style={{ cursor: 'pointer', fontSize: 10, color: hf ? '#2563eb' : '#94a3b8' }}>▼</span>}
                        </div>}
                    {showFi === col.key && (
                      <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', left: 0, zIndex: 100, background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, boxShadow: '0 4px 20px rgba(0,0,0,0.12)', minWidth: 180, maxHeight: 240, overflow: 'auto', textAlign: 'left', padding: 6 }}>
                        <div style={{ padding: '6px 10px', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between' }}>
                          <b style={{ fontSize: 13 }}>{col.label}</b>
                          {hf && <span onClick={() => setFi(p => { const n = { ...p }; delete n[col.key]; return n })} style={{ fontSize: 12, color: '#2563eb', cursor: 'pointer' }}>초기화</span>}
                        </div>
                        {gFO(col.key).map(opt => <label key={opt} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', cursor: 'pointer', fontSize: 14 }}><input type="checkbox" checked={!!filters[col.key]?.has(opt)} onChange={() => tF(col.key, opt)} style={{ width: 15, height: 15 }} />{opt}</label>)}
                      </div>
                    )}
                    <div onMouseDown={e => onCD(e, i)} style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 5, cursor: 'col-resize' }} />
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {cur.length === 0 && <tr><td colSpan={visCols.length + 1} style={{ textAlign: 'center', padding: 60, color: '#aaa', fontSize: 16 }}>No data</td></tr>}
            {cur.length > 0 && (() => {
              const virtualItems = rowVirtualizer.getVirtualItems()
              const topPad = virtualItems[0]?.start ?? 0
              const btmPad = rowVirtualizer.getTotalSize() - (virtualItems[virtualItems.length - 1]?.end ?? 0)
              return (<>
                {topPad > 0 && <tr><td colSpan={visCols.length + 1} style={{ height: topPad, padding: 0, border: 'none' }} /></tr>}
                {virtualItems.map(vRow => {
                  const ri = vRow.index
                  const row = cur[ri]
                  if (!row) return null
              const h = gH(row.id); const isSel = sel.has(row.id); const bg = getBg(row, ri, isSel)
              const stI = STAGES.find(s => s.key === (row.stage || 'none')) || STAGES[0]
              const mTags = String(row.mailStatus || '').split(',').filter(Boolean)
              const ps = Number(row.photoSize) || 50
              return (
                <tr key={row.id} data-index={ri} ref={rowVirtualizer.measureElement} onContextMenu={e => hC(e, row)} style={{ height: h, background: bg, position: 'relative' }}>
                  <td style={{ textAlign: 'center', border: '1px solid #d1d5db', background: isSel ? '#93c5fd' : '#f8fafc', padding: 0, position: 'relative' }}>
                    <input type="checkbox" checked={isSel} onChange={() => tR(row.id)} style={{ cursor: 'pointer', width: 16, height: 16 }} />
                    <div onMouseDown={e => onRD(e, row.id)} style={{ position: 'absolute', bottom: -2, left: 0, right: 0, height: 5, cursor: 'row-resize' }} />
                  </td>
                  {visCols.map((col, ci) => {
                    const val = col.key === 'rowNum' ? String(row.id) : String(row[col.key] || '')
                    const isE = ec?.id === row.id && ec?.key === col.key
                    const isFr = ci < frozenCols
                    const leftOffset = 34 + visCols.slice(0, ci).reduce((s, c) => s + c.w, 0)
                    const frS: React.CSSProperties = isFr ? { position: 'sticky', left: leftOffset + 'px', zIndex: 10, background: bg } : {}

                    if (col.key === 'photo') return (
                      <td key={col.key} style={{ padding: 1, border: '1px solid #d1d5db', textAlign: 'center', verticalAlign: 'middle', cursor: 'pointer', ...frS }} onClick={() => setPT(row.id)} onDoubleClick={() => { setPT(row.id); photoRef.current?.click() }} onWheel={e => { e.preventDefault(); upData(x => x.id === row.id ? { ...x, photoSize: Math.max(30, Math.min(120, Number(x.photoSize || 50) + (e.deltaY < 0 ? 5 : -5))) } : x) }}>
                        {row.photoUrl
                          ? <SecureAdminImage
                              fileUrl={String(row.photoUrl)}
                              adminKey={adminKey}
                              width={ps} height={ps}
                              style={{ borderRadius: 4, objectFit: 'cover' }}
                              alt={String(row.name)}
                              fallback={<div style={{ width: ps, height: ps, borderRadius: 4, background: PC[row.id % PC.length], color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: ps * 0.4, fontWeight: 900 }}>{(String(row.name) || '?')[0]?.toUpperCase()}</div>}
                            />
                          : <div style={{ width: ps, height: ps, borderRadius: 4, background: PC[row.id % PC.length], color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: ps * 0.4, fontWeight: 900 }}>{(String(row.name) || '?')[0]?.toUpperCase()}</div>
                        }
                      </td>
                    )
                    if (col.key === 'rowNum') return <td key={col.key} style={{ padding: '3px 4px', textAlign: 'center', fontSize: 14, fontWeight: 700, background: '#f8fafc', border: '1px solid #d1d5db', ...frS }}>{val}</td>
                    if (col.key === 'mailAction') return (
                      <td key={col.key} style={{ padding: 3, border: '1px solid #d1d5db', textAlign: 'center', ...frS }}>
                        <button onClick={() => openMM([row])} style={{ padding: '6px 12px', fontSize: 14, border: '2px solid #2563eb', borderRadius: 6, background: '#eff6ff', color: '#2563eb', cursor: 'pointer', fontWeight: 800 }}>메일발송</button>
                      </td>
                    )
                    if (col.key === 'mailStatus') return (
                      <td key={col.key} style={{ padding: '4px 5px', border: '1px solid #d1d5db', verticalAlign: 'top', ...frS }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {MTAGS.map(mt => { const a = mTags.includes(mt.key); return <span key={mt.key} onClick={() => tMT(row.id, mt.key)} style={{ fontSize: 14, padding: '4px 10px', borderRadius: 6, cursor: 'pointer', fontWeight: a ? 800 : 500, background: a ? mt.c + '25' : '#f1f5f9', color: a ? mt.c : '#999', border: '2px solid ' + (a ? mt.c : '#e2e8f0') }}>{(a ? '✓ ' : '') + mt.label}</span> })}
                        </div>
                      </td>
                    )
                    if (col.key === 'stage') return (
                      <td key={col.key} style={{ padding: 3, border: '1px solid #d1d5db', ...frS }}>
                        <select value={String(row.stage || 'none')} onChange={e => setSt(row.id, e.target.value)} style={{ width: '100%', fontSize: 15, padding: '6px 4px', borderRadius: 6, border: '2px solid ' + (stI.color === '#fff' ? '#d1d5db' : stI.color), background: stI.color, color: stI.text, fontWeight: 700, cursor: 'pointer', outline: 'none' }}>
                          {STAGES.map(s => <option key={s.key} value={s.key}>{s.label}</option>)}
                        </select>
                      </td>
                    )
                    if (col.type === 'dropdown') return (
                      <td key={col.key} style={{ padding: 3, border: '1px solid #d1d5db', ...frS }}>
                        <select value={val} onChange={e => setField(row.id, col.key, e.target.value)} style={{ width: '100%', fontSize: 14, padding: '5px 4px', borderRadius: 6, border: '1px solid ' + (isRed(val) ? '#dc2626' : '#d1d5db'), background: isRed(val) ? '#fee2e2' : '#fff', color: isRed(val) ? '#dc2626' : '#000', fontWeight: isRed(val) ? 800 : 500, cursor: 'pointer', outline: 'none' }}>
                          <option value="">--</option>
                          {(col.opts || []).map(o => <option key={o} value={o}>{o}</option>)}
                        </select>
                      </td>
                    )
                    return (
                      <td key={col.key} onDoubleClick={() => sE(row.id, col.key, val)} style={{ padding: isE ? 0 : '3px 5px', border: '1px solid #d1d5db', fontSize: 15, lineHeight: '1.35', overflow: 'hidden', whiteSpace: 'pre-wrap', wordBreak: 'break-all', cursor: 'cell', verticalAlign: 'top', color: '#000', ...frS }}>
                        {isE ? <textarea ref={eR} value={ev} onChange={e => setEv(e.target.value)} onBlur={cE} onKeyDown={e => { if (e.key === 'Escape') setEc(null) }} style={{ width: '100%', minHeight: 40, fontSize: 15, border: '2px solid #2563eb', padding: 3, resize: 'vertical', background: '#eff6ff', borderRadius: 3, boxSizing: 'border-box' }} /> : val}
                      </td>
                    )
                  })}
                </tr>
              )
                })}
                {btmPad > 0 && <tr><td colSpan={visCols.length + 1} style={{ height: btmPad, padding: 0, border: 'none' }} /></tr>}
              </>)
            })()}
          </tbody>
        </table>
      </div>
      </>
      )}

      {/* 하단 Google Sheets 스타일 탭 바 */}
      <div className="gs-tabs-bottom">
        {TABS.map(t => (
          <div
            key={t.key}
            className={`gs-tab ${tab === t.key ? 'gs-tab-active' : ''}`}
            onClick={() => { setTab(t.key); setSel(new Set()); setFi({}) }}
          >
            {t.label}
            <span className="gs-tab-count">{cnt[t.key] ?? 0}</span>
          </div>
        ))}
      </div>

      {/* 하단 상태바 */}
      <div style={{ background: '#f1f5f9', padding: '10px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '3px solid #cbd5e1', flexShrink: 0, flexWrap: 'wrap', gap: 8 }}>
        <div style={{ display: 'flex', gap: 20, fontSize: 17, fontWeight: 800 }}>
          <span>전체 <b style={{ fontSize: 22 }}>{cnt.all}</b></span>
          <span>👤<b style={{ color: '#2563eb', fontSize: 22 }}>{cnt.active}</b></span>
          <span>✅<b style={{ color: '#16a34a', fontSize: 22 }}>{cnt.past}</b></span>
          <span>⛔<b style={{ color: '#dc2626', fontSize: 22 }}>{cnt.blacklist}</b></span>
        </div>
        <div style={{ display: 'flex', gap: 14, fontSize: 14, color: '#475569' }}>
          <span>dbl=편집</span><span>Ctrl+Z=되돌리기</span>
          <span style={{ color: '#16a34a', fontWeight: 800 }}>✓저장</span>
        </div>
      </div>

      {/* 열 메뉴 */}
      {colMenu && (
        <div onClick={e => e.stopPropagation()} style={{ position: 'fixed', top: colMenu.y, left: colMenu.x, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 10, zIndex: 1000, minWidth: 170, fontSize: 15, boxShadow: '0 6px 24px rgba(0,0,0,0.12)', overflow: 'hidden' }}>
          <Hov bg="#f0f0f0" style={{ padding: '10px 16px', cursor: 'pointer' }} onClick={() => { setRnCol(colMenu.key); setRnVal(cols.find(c => c.key === colMenu.key)?.label || ''); setColMenu(null) }}>✏️ 이름</Hov>
          <Hov bg="#f0f0f0" style={{ padding: '10px 16px', cursor: 'pointer' }} onClick={() => { setCols(p => p.map(c => c.key === colMenu.key ? { ...c, v: false } : c)); setColMenu(null) }}>👁 숨기기</Hov>
        </div>
      )}

      {/* 컨텍스트 메뉴 */}
      {ctx && (
        <div onClick={e => e.stopPropagation()} style={{ position: 'fixed', top: ctx.y, left: ctx.x, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 10, zIndex: 1000, minWidth: 200, fontSize: 15, boxShadow: '0 6px 24px rgba(0,0,0,0.12)', overflow: 'hidden' }}>
          <div style={{ padding: '8px 16px', fontSize: 12, color: '#94a3b8', borderBottom: '1px solid #f1f5f9' }}>#{ctx.row.id} {String(ctx.row.name)}</div>
          <Hov bg="#eff6ff" style={{ padding: '10px 16px', cursor: 'pointer' }} onClick={() => { openMM([ctx.row]); setCtx(null) }}>✉ 메일</Hov>
          <Hov bg="#f0fdf4" style={{ padding: '10px 16px', cursor: 'pointer' }} onClick={() => { setLinkPanelRow(ctx.row); setCtx(null) }}>매칭 연동</Hov>
          <Hov bg="#f0f0f0" style={{ padding: '10px 16px', cursor: 'pointer' }} onClick={() => { addRow(ctx.row.id); setCtx(null) }}>+ 행 추가</Hov>
          {ctx.row.category !== 'active' && <Hov bg="#dbeafe" style={{ padding: '10px 16px', cursor: 'pointer' }} onClick={() => mv(ctx.row, 'active')}>👤 구직활동중</Hov>}
          {ctx.row.category !== 'past' && <Hov bg="#dcfce7" style={{ padding: '10px 16px', cursor: 'pointer' }} onClick={() => mv(ctx.row, 'past')}>✅ 체결완료</Hov>}
          {ctx.row.category !== 'blacklist' && <Hov bg="#fee2e2" style={{ padding: '10px 16px', cursor: 'pointer' }} onClick={() => mv(ctx.row, 'blacklist')}>⛔ 블랙리스트</Hov>}
          <div style={{ borderTop: '1px solid #f1f5f9' }} />
          <Hov bg="#fee2e2" style={{ padding: '10px 16px', cursor: 'pointer', color: '#dc2626' }} onClick={() => dR(ctx.row)}>× 삭제</Hov>
        </div>
      )}

      {/* 메일 모달 */}
      {mmOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={() => setMmOpen(false)}>
          <div onClick={e => e.stopPropagation()} style={{ background: '#fff', borderRadius: 16, width: '85vw', maxWidth: 1100, height: '88vh', overflow: 'auto', boxShadow: '0 24px 80px rgba(0,0,0,0.3)', display: 'flex', flexDirection: 'column', resize: 'both', minWidth: 500, minHeight: 400 }}>
            <div style={{ padding: '16px 24px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', flexShrink: 0 }}>
              <b style={{ fontSize: 22 }}>Mail Compose</b>
              <button onClick={() => setMmOpen(false)} style={{ border: 'none', background: 'transparent', fontSize: 26, cursor: 'pointer' }}>×</button>
            </div>
            <div style={{ padding: '12px 24px', borderBottom: '1px solid #f1f5f9', flexShrink: 0 }}>
              <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                {MTP.map(m => <button key={m.key} onClick={() => setMmTmpl(m.key)} style={{ padding: '8px 16px', fontSize: 14, borderRadius: 8, border: mmTmpl === m.key ? '2px solid #2563eb' : '1px solid #e2e8f0', background: mmTmpl === m.key ? '#2563eb' : '#fff', color: mmTmpl === m.key ? '#fff' : '#333', cursor: 'pointer', fontWeight: mmTmpl === m.key ? 800 : 500 }}>{m.label}</button>)}
              </div>
            </div>
            <div style={{ padding: '10px 24px', borderBottom: '1px solid #f1f5f9', flexShrink: 0 }}>
              <span style={{ fontSize: 15, fontWeight: 700, background: '#fef9c3', padding: '4px 14px', borderRadius: 6 }}>From: bridgejobkr@gmail.com</span>
            </div>
            <div style={{ padding: '10px 24px', borderBottom: '1px solid #f1f5f9', flexShrink: 0 }}>
              <span style={{ fontSize: 14, color: '#666' }}>To: </span>
              {mmRecs.map(r => <span key={r.id} style={{ fontSize: 14, padding: '3px 10px', background: '#f1f5f9', borderRadius: 6, marginLeft: 4 }}>{String(r.name)} &lt;{String(r.email)}&gt;</span>)}
            </div>
            <div style={{ padding: '10px 24px', flexShrink: 0 }}>
              <input value={mmSubj} onChange={e => setMmSubj(e.target.value)} placeholder="Subject" style={{ width: '100%', padding: '12px 16px', fontSize: 17, border: '1px solid #d1d5db', borderRadius: 8, outline: 'none', boxSizing: 'border-box' }} />
            </div>
            <div style={{ padding: '10px 24px', flex: 1, display: 'flex', flexDirection: 'column' }}>
              <textarea value={mmBody} onChange={e => setMmBody(e.target.value)} placeholder="Body" style={{ flex: 1, width: '100%', minHeight: 200, padding: '16px 18px', fontSize: 16, border: '1px solid #d1d5db', borderRadius: 8, outline: 'none', resize: 'none', boxSizing: 'border-box', lineHeight: 1.8 }} />
              <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>Vars: {'{{name}}'} {'{{region}}'} {'{{city}}'}</div>
            </div>
            <div style={{ padding: '10px 24px', borderTop: '1px solid #f1f5f9', flexShrink: 0 }}>
              <div style={{ border: '2px dashed #d1d5db', borderRadius: 10, padding: 18, textAlign: 'center', cursor: 'pointer', color: '#94a3b8' }} onClick={() => fRef.current?.click()}>파일을 드래그하거나 클릭하여 첨부</div>
              <input ref={fRef} type="file" multiple onChange={e => setMmFiles(p => [...p, ...Array.from(e.target.files || [])])} style={{ display: 'none' }} />
              {mmFiles.length > 0 && <div style={{ marginTop: 6, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {mmFiles.map((f, i) => <span key={i} style={{ fontSize: 13, padding: '4px 12px', background: '#f1f5f9', borderRadius: 6 }}>📎{f.name}<span onClick={() => setMmFiles(p => p.filter((_, j) => j !== i))} style={{ cursor: 'pointer', color: '#ef4444', marginLeft: 8 }}>×</span></span>)}
              </div>}
            </div>
            <div style={{ padding: '16px 24px', borderTop: '2px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0, flexWrap: 'wrap', gap: 8 }}>
              <div>
                <span style={{ fontSize: 14, background: '#fef9c3', padding: '3px 10px', borderRadius: 4 }}>bridgejobkr@gmail.com</span>
                <div style={{ fontSize: 12, color: '#dc2626', fontWeight: 700, marginTop: 4 }}>* 타인 정보 절대 미노출 · 1:1 개별 발송</div>
              </div>
              <button onClick={() => { alert('발송: ' + mmRecs.map(r => r.email).join(', ') + '\n' + mmSubj); setMmOpen(false) }} disabled={!mmSubj || !mmBody} style={{ padding: '14px 32px', fontSize: 18, border: 'none', borderRadius: 12, background: mmSubj && mmBody ? '#03c75a' : '#aaa', color: '#fff', cursor: mmSubj && mmBody ? 'pointer' : 'default', fontWeight: 900 }}>
                보내기 ({mmRecs.length}명 개별발송)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 후보자 연동 패널 ── */}
      {linkPanelRow && (
        <LinkPanel
          mode="candidate"
          candidateId={typeof linkPanelRow.id === 'number' ? linkPanelRow.id : Number(linkPanelRow.id)}
          candidateName={String(linkPanelRow.name || '')}
          candidateNumber={linkPanelRow.sheet_number ? String(linkPanelRow.sheet_number) : undefined}
          onClose={() => setLinkPanelRow(null)}
        />
      )}
    </div>
  )
}
