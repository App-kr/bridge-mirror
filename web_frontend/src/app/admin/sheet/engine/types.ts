/* ═══════════════════════════════════════════════════════
   BRIDGE Canvas Spreadsheet — Shared Types & Constants
   ═══════════════════════════════════════════════════════ */

export type CategoryKey = 'active' | 'past' | 'blacklist'
export type TabKey = CategoryKey | 'all' | 'focus'
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
  onTagToggle: (rowIdx: number, tagKey: string) => void
  onTagCellClick: (rowIdx: number, row: DataRow, x: number, y: number) => void
  onPhotoUpload: (rowIdx: number) => void
  onPhotoWheel: (rowIdx: number, delta: number) => void
  onHeaderCheckToggle: () => void
  onAddRow: () => void
  onFilterClick: (colKey: string, x: number, y: number) => void
  onHeaderContextMenu: (e: MouseEvent, colKey: string) => void
  onRowHeightChange: (cid: string, height: number) => void
}

export interface CellStyle {
  fontSize?: number
  color?: string
  bgColor?: string
  bold?: boolean
  italic?: boolean
  strikethrough?: boolean
  align?: 'left' | 'center' | 'right'
}

export interface MailTemplate {
  key: string
  label: string
  s: string
  b: string
}

export const MAIL_TEMPLATES: MailTemplate[] = [
  { key: 'interview', label: 'Interview', s: '[BRIDGE] Interview', b: 'Dear {{name}},\n\nInterview arranged.\n\nBRIDGE' },
  { key: 'contract', label: 'Contract', s: '[BRIDGE] Contract', b: 'Dear {{name}},\n\nContract attached.\n\nBRIDGE' },
  { key: 'visa', label: 'Visa', s: '[BRIDGE] Visa Guide', b: 'Dear {{name}},\n\nVisa guide attached.\n\nBRIDGE' },
  { key: 'settle', label: 'Settlement', s: '[BRIDGE] Settlement', b: 'Dear {{name}},\n\nSettlement guide.\n\nBRIDGE' },
  { key: 'tax', label: 'Tax', s: '[BRIDGE] Tax Info', b: 'Dear {{name}},\n\nTax info.\n\nBRIDGE' },
  { key: 'transfer', label: 'Transfer', s: '[BRIDGE] Transfer', b: 'Dear {{name}},\n\nTransfer guide.\n\nBRIDGE' },
  { key: 'renewal', label: 'Renewal', s: '[BRIDGE] Renewal', b: 'Dear {{name}},\n\nRenewal info.\n\nBRIDGE' },
  { key: 'custom', label: 'Write', s: '', b: '' },
]

/* ── Constants ── */
export const HEADER_H = 56
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
  { key: 'active', label: '구직자', color: '#fff', bg: '#2E7D32', accent: '#1B5E20', icon: '👤' },
  { key: 'focus', label: '집중관리', color: '#fff', bg: '#6D4C41', accent: '#4E342E', icon: '🎯' },
  { key: 'past', label: '체결완료', color: '#fff', bg: '#1976D2', accent: '#0D47A1', icon: '✅' },
  { key: 'blacklist', label: '블랙리스트', color: '#fff', bg: '#C62828', accent: '#B71C1C', icon: '⛔' },
  { key: 'all', label: '전체', color: '#fff', bg: '#37474F', accent: '#263238', icon: '📋' },
]

export const MTAGS: MailTag[] = [
  // 진행단계
  { key: 'interview',     label: '인터뷰',   c: '#d97706' },
  { key: 'proposal',      label: '계약제안', c: '#ca8a04' },
  { key: 'signed',        label: '서명완료', c: '#16a34a' },
  { key: 'guide_sent',    label: '안내발송', c: '#2563eb' },
  { key: 'guide_done',    label: '안내완료', c: '#1d4ed8' },
  { key: 'caution',       label: '주의',     c: '#ef4444' },
  { key: 'lost',          label: '두절',     c: '#9ca3af' },
  // 발송완료
  { key: 'contract_sent', label: '계약발송', c: '#2563eb' },
  { key: 'contract_done', label: '계약완료', c: '#16a34a' },
  { key: 'visa_sent',     label: '비자완료', c: '#7c3aed' },
  { key: 'housing_sent',  label: '숙소완료', c: '#0891b2' },
  { key: 'ot_done',       label: 'OT완료',   c: '#16a34a' },
  // 역할
  { key: 'role_kindy',    label: '유치원',   c: '#ec4899' },
  { key: 'role_elem',     label: '초등',     c: '#f97316' },
  { key: 'role_middle',   label: '중등',     c: '#8b5cf6' },
  { key: 'role_high',     label: '고등',     c: '#0f172a' },
  { key: 'role_hogwan',   label: '학원',     c: '#06b6d4' },
  { key: 'role_camp',     label: '캠프',     c: '#84cc16' },
]

/** Column alphabet label: 0→A, 1→B, ... 25→Z, 26→AA, 27→AB */
export function colAlphabet(i: number): string {
  if (i < 26) return String.fromCharCode(65 + i)
  return String.fromCharCode(65 + Math.floor(i / 26) - 1) + String.fromCharCode(65 + (i % 26))
}

export const H_OPTS = ['숙소제공', '월세제공', '보증+월세', '불필요', '자체']
export const FEE_OPTS = ['선금완료', '잔금완료', '일시납완료', '연체중', '14일연체', '장기연체']
export const PROC_OPTS = ['선금대기', '선금완료', '잔금대기', '잔금완료', '일시납대기', '일시납완료', '연체중', '장기연체', '특이사항']

export function defaultCols(): ColDef[] {
  return [
    { key: 'rowNum', label: '', w: 52, type: 'idx', v: true },
    { key: 'email', label: '메일', w: 190, type: 't', v: true },
    { key: 'name', label: '이름', w: 140, type: 't', v: true },
    { key: 'photo', label: '사진', w: 65, type: 'photo', v: true },
    { key: 'mgtNum', label: '번호', w: 65, type: 't', v: true },
    { key: 'arc', label: 'ARC', w: 120, type: 't', v: true },
    { key: 'nationality', label: '국적', w: 72, type: 't', v: true },
    { key: 'background', label: '배경', w: 75, type: 't', v: true },
    { key: 'age', label: '나이', w: 46, type: 't', v: true },
    { key: 'gender', label: '성별', w: 46, type: 't', v: true },
    { key: 'currentLoc', label: '현위치', w: 72, type: 't', v: true },
    { key: 'startDate', label: '시작', w: 78, type: 't', v: true },
    { key: 'university', label: '대상', w: 50, type: 't', v: true },
    { key: 'prefRegion', label: '선호지역', w: 75, type: 't', v: true },
    { key: 'reference', label: '레퍼런스', w: 210, type: 'long', v: true },
    { key: 'totalExp', label: '총경력', w: 62, type: 't', v: true },
    { key: 'employment', label: '직업', w: 75, type: 't', v: true },
    { key: 'notice', label: '기피', w: 70, type: 't', v: true },
    { key: 'preference', label: '선호/인터뷰', w: 190, type: 'long', v: true },
    { key: 'applied', label: '지원/요청', w: 175, type: 'long', v: true },
    { key: 'contractOffer', label: '계약제안', w: 120, type: 'long', v: true },
    { key: 'proposal', label: '포지션제안', w: 175, type: 'long', v: true },
    { key: 'mailAction', label: '메일발송', w: 85, type: 'mail', v: true },
    { key: 'stage', label: '진행단계', w: 140, type: 'stage', v: true },
    { key: 'resumeStatus', label: '변환', w: 60, type: 't', v: true },
    { key: 'curSalary', label: '현급여', w: 62, type: 't', v: true },
    { key: 'hopeSalary', label: '희망', w: 62, type: 't', v: true },
    { key: 'interviewCol', label: '인터뷰', w: 78, type: 't', v: true },
    { key: 'degree', label: '학위', w: 58, type: 't', v: true },
    { key: 'major', label: '전공', w: 72, type: 't', v: true },
    { key: 'cert', label: '자격증', w: 70, type: 't', v: true },
    { key: 'docs', label: '서류', w: 65, type: 't', v: true },
    { key: 'health', label: '건강', w: 52, type: 't', v: true },
    { key: 'personalNote', label: '고려사항', w: 100, type: 'long', v: true },
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
    // 인재 게시판 관리 컬럼 (Phase 3.8)
    { key: 'talent_visible', label: '공개', w: 45, type: 't', v: false },
    { key: 'talent_badge', label: '배지', w: 60, type: 't', v: false },
    { key: 'talent_reference_star', label: '별점', w: 45, type: 't', v: false },
    { key: 'talent_summary', label: '강사소개', w: 120, type: 'long', v: false },
  ]
}
