/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet — Shared Types & Constants
   ═══════════════════════════════════════════════════════ */

export type CategoryKey = 'active' | 'past' | 'blacklist'
export type TabKey = CategoryKey | 'all'
export type ColType = 'idx' | 't' | 'photo' | 'long' | 'mail' | 'tags' | 'stage' | 'dropdown'

export interface ColDef {
  key: string
  label: string
  w: number
  type: ColType
  v: boolean
  opts?: string[]
}

export interface DataRow {
  id: number
  _cid?: string
  category: string
  stage: string
  mailStatus: string
  photoUrl: string
  photoSize: number
  [key: string]: string | number | undefined
}

export interface Stage {
  key: string
  label: string
  color: string
  text: string
}

export interface MailTag {
  key: string
  label: string
  c: string
}

export interface TabDef {
  key: TabKey
  label: string
  color: string
  bg: string
  accent: string
  icon: string
}

export interface CellRef {
  row: number
  col: number
}

export interface GridCallbacks {
  onCellChange: (rowIdx: number, colKey: string, value: string) => void
  onCellClick: (rowIdx: number, colKey: string, row: DataRow) => void
  onSelectionChange: (selectedRows: Set<number>) => void
  onContextMenu: (e: MouseEvent, rowIdx: number, row: DataRow) => void
  onSort: (colKey: string) => void
  onColumnResize: (colKey: string, width: number) => void
  onRequestMore: () => void
  onPhotoClick: (rowIdx: number, row: DataRow) => void
  onMailClick: (rowIdx: number, row: DataRow) => void
  onStageChange: (rowIdx: number, stage: string) => void
}

/* ── Constants ── */
export const HEADER_H = 32
export const ROW_H = 36
export const FONT = '13px -apple-system,"Segoe UI",sans-serif'
export const HEADER_FONT = 'bold 12px -apple-system,"Segoe UI",sans-serif'

export const STAGES: Stage[] = [
  { key: 'none', label: '—', color: '#ffffff', text: '#000000' },
  { key: 'interview', label: '인터뷰', color: '#fef9c3', text: '#000000' },
  { key: 'proposal', label: '계약제안', color: '#fde68a', text: '#000000' },
  { key: 'signed', label: '서명완료', color: '#bbf7d0', text: '#000000' },
  { key: 'guide_sent', label: '안내발송', color: '#93c5fd', text: '#000000' },
  { key: 'guide_done', label: '안내완료', color: '#dbeafe', text: '#000000' },
  { key: 'caution', label: '주의', color: '#fecaca', text: '#000000' },
  { key: 'lost', label: '두절', color: '#e5e7eb', text: '#666666' },
]

export const TABS: TabDef[] = [
  { key: 'active', label: '구직활동중', color: '#2563eb', bg: '#dbeafe', accent: '#1d4ed8', icon: '👤' },
  { key: 'past', label: '체결완료', color: '#16a34a', bg: '#dcfce7', accent: '#166534', icon: '✅' },
  { key: 'blacklist', label: '블랙리스트', color: '#dc2626', bg: '#fee2e2', accent: '#991b1b', icon: '⛔' },
  { key: 'all', label: '전체', color: '#0f172a', bg: '#e2e8f0', accent: '#020617', icon: '📋' },
]

export const MTAGS: MailTag[] = [
  { key: 'guide_done', label: '가이드✓', c: '#16a34a' },
  { key: 'contract_sent', label: '계약발송', c: '#2563eb' },
  { key: 'contract_done', label: '계약✓', c: '#16a34a' },
  { key: 'visa_sent', label: '비자✓', c: '#7c3aed' },
  { key: 'housing_sent', label: '숙소✓', c: '#0891b2' },
  { key: 'ot_done', label: 'OT✓', c: '#16a34a' },
]

export const H_OPTS = ['숙소제공', '월세제공', '보증+월세', '불필요', '자체']
export const FEE_OPTS = ['선금완료', '잔금완료', '일시납완료', '연체중', '14일연체', '장기연체']
export const PROC_OPTS = ['진행중', '완료', '보류', '취소', '무단이탈']

export function defaultCols(): ColDef[] {
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
