'use client'

/**
 * AllCandidatesGrid — 전체 탭 전용 AG Grid 가상 스크롤 뷰
 * 3059행 즉시 렌더링, 딜레이 없음
 */

import { useCallback, useMemo } from 'react'
import { AgGridReact } from 'ag-grid-react'
import {
  AllCommunityModule,
  ModuleRegistry,
  ColDef,
  ICellRendererParams,
  GetContextMenuItemsParams,
  MenuItemDef,
  GridReadyEvent,
  BodyScrollEvent,
} from 'ag-grid-community'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-quartz.css'

ModuleRegistry.registerModules([AllCommunityModule])

/* ─── Types ─── */
type CategoryKey = 'active' | 'past' | 'blacklist'
type DataRow = Record<string, string | number>

interface Props {
  rows: DataRow[]
  onCopyTo: (row: DataRow, cat: CategoryKey) => void
  loading: boolean
  total?: number
  onLoadMore?: () => void
}

/* ─── Cell renderers ─── */
function PhotoRenderer({ value }: ICellRendererParams) {
  if (!value) return <span style={{ color: '#bbb', fontSize: 11 }}>—</span>
  return (
    <img
      src={String(value)}
      alt=""
      style={{ width: 34, height: 34, objectFit: 'cover', borderRadius: 4, verticalAlign: 'middle' }}
      onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
    />
  )
}

function StageRenderer({ value }: ICellRendererParams) {
  const MAP: Record<string, { label: string; bg: string }> = {
    interview:   { label: '인터뷰', bg: '#fef9c3' },
    proposal:    { label: '계약제안', bg: '#fde68a' },
    signed:      { label: '서명완료', bg: '#bbf7d0' },
    guide_sent:  { label: '안내발송', bg: '#93c5fd' },
    guide_done:  { label: '안내완료', bg: '#dbeafe' },
    caution:     { label: '주의', bg: '#fecaca' },
    lost:        { label: '두절', bg: '#e5e7eb' },
  }
  const s = MAP[String(value || '')]
  if (!s) return null
  return (
    <span style={{ background: s.bg, padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 700 }}>
      {s.label}
    </span>
  )
}

function TagsRenderer({ value }: ICellRendererParams) {
  if (!value) return null
  const tags = String(value).split(',').filter(Boolean)
  const colors: Record<string, string> = {
    guide_done: '#16a34a', contract_sent: '#2563eb', contract_done: '#16a34a',
    visa_sent: '#7c3aed', housing_sent: '#0891b2', ot_done: '#16a34a',
  }
  const labels: Record<string, string> = {
    guide_done: '가이드✓', contract_sent: '계약발송', contract_done: '계약✓',
    visa_sent: '비자✓', housing_sent: '숙소✓', ot_done: 'OT✓',
  }
  return (
    <span style={{ display: 'flex', gap: 3, flexWrap: 'wrap', alignItems: 'center' }}>
      {tags.map(t => (
        <span key={t} style={{ fontSize: 11, color: '#fff', background: colors[t] || '#888', padding: '1px 6px', borderRadius: 8 }}>
          {labels[t] || t}
        </span>
      ))}
    </span>
  )
}

function NewBadgeRenderer({ value }: ICellRendererParams) {
  const v = String(value || '')
  if (v.includes('★NEW')) {
    return (
      <span style={{ background: '#ef4444', color: '#fff', padding: '2px 8px', borderRadius: 10, fontSize: 12, fontWeight: 900 }}>
        ★ NEW
      </span>
    )
  }
  return <span>{v}</span>
}

/* ─── Column definitions ─── */
function buildColDefs(): ColDef[] {
  const base: Array<{ field: string; headerName: string; width: number; pinned?: 'left'; cellRenderer?: string }> = [
    { field: 'rowNum',       headerName: '#',         width: 52,  pinned: 'left' },
    { field: 'email',        headerName: '메일',       width: 200, pinned: 'left' },
    { field: 'name',         headerName: '이름',       width: 140, pinned: 'left' },
    { field: 'photoUrl',     headerName: '사진',       width: 60,  cellRenderer: 'photoRenderer' },
    { field: 'mgtNum',       headerName: '번호',       width: 65 },
    { field: 'arc',          headerName: 'ARC',        width: 120 },
    { field: 'nationality',  headerName: '국적',        width: 62 },
    { field: 'background',   headerName: '배경',        width: 75 },
    { field: 'age',          headerName: '나이',        width: 46 },
    { field: 'gender',       headerName: '성별',        width: 46 },
    { field: 'currentLoc',   headerName: '현위치',      width: 80 },
    { field: 'startDate',    headerName: '시작',        width: 78 },
    { field: 'university',   headerName: '대상',        width: 50 },
    { field: 'prefRegion',   headerName: '선호지역',    width: 80 },
    { field: 'reference',    headerName: '레퍼런스',    width: 200 },
    { field: 'totalExp',     headerName: '총경력',      width: 62 },
    { field: 'preference',   headerName: '선호/인터뷰',  width: 190 },
    { field: 'applied',      headerName: '지원/요청',   width: 175 },
    { field: 'proposal',     headerName: '포지션제안',  width: 175 },
    { field: 'mailStatus',   headerName: '발송상태',    width: 200, cellRenderer: 'tagsRenderer' },
    { field: 'stage',        headerName: '진행단계',    width: 120, cellRenderer: 'stageRenderer' },
    { field: 'curSalary',    headerName: '현급여',      width: 62 },
    { field: 'hopeSalary',   headerName: '희망',        width: 62 },
    { field: 'interviewCol', headerName: '인터뷰',      width: 78 },
    { field: 'degree',       headerName: '학위',        width: 58 },
    { field: 'major',        headerName: '전공',        width: 72 },
    { field: 'cert',         headerName: '자격증',      width: 70 },
    { field: 'docs',         headerName: '서류',        width: 65 },
    { field: 'health',       headerName: '건강',        width: 52 },
    { field: 'tattooPiercing', headerName: '타투피어싱', width: 75 },
    { field: 'family',       headerName: '가족',        width: 52 },
    { field: 'married',      headerName: '결혼',        width: 48 },
    { field: 'housing',      headerName: '숙소',        width: 100 },
    { field: 'religion',     headerName: '종교',        width: 52 },
    { field: 'e2visa',       headerName: 'E2',          width: 52 },
    { field: 'kakao',        headerName: '카톡',        width: 100 },
    { field: 'phone',        headerName: '폰번호',      width: 125 },
    { field: 'crimCheck',    headerName: '범죄',        width: 55 },
    { field: 'domesticCrim', headerName: '국내범죄',    width: 70 },
    { field: 'infoProvide',  headerName: '정보제공',    width: 65 },
    { field: 'verified',     headerName: '사실확인',    width: 65 },
    { field: 'source',       headerName: '경로',        width: 80, cellRenderer: 'newBadgeRenderer' },
    { field: 'timestamp',    headerName: '타임',        width: 85 },
    { field: 'hired',        headerName: '채용',        width: 65 },
    { field: 'wage',         headerName: '급여',        width: 60 },
    { field: 'moveIn',       headerName: '개시일',      width: 70 },
    { field: 'housingCost',  headerName: '숙박',        width: 55 },
    { field: 'introFee',     headerName: '소개료',      width: 100 },
    { field: 'process',      headerName: '처리여부',    width: 100 },
    { field: 'history',      headerName: '과거기록',    width: 150 },
  ]

  return base.map((c, i) => ({
    field: c.field,
    headerName: c.headerName,
    width: c.width,
    pinned: c.pinned,
    cellRenderer: c.cellRenderer,
    sortable: true,
    filter: true,
    resizable: true,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    valueGetter: c.field === 'rowNum' ? (p: any) => (p.node?.rowIndex ?? 0) + 1 : undefined,
    suppressMovable: false,
    headerTooltip: c.headerName,
    // 이메일, 이름은 bold
    cellStyle: (i < 3) ? { fontWeight: 700 } : undefined,
  }))
}

/* ─── Main Component ─── */
export default function AllCandidatesGrid({ rows, onCopyTo, loading, total, onLoadMore }: Props) {

  const colDefs = useMemo(() => buildColDefs(), [])

  const defaultColDef = useMemo<ColDef>(() => ({
    sortable: true,
    filter: true,
    resizable: true,
    wrapText: false,
    autoHeight: false,
    suppressMovable: false,
  }), [])

  const components = useMemo(() => ({
    photoRenderer: PhotoRenderer,
    stageRenderer: StageRenderer,
    tagsRenderer: TagsRenderer,
    newBadgeRenderer: NewBadgeRenderer,
  }), [])

  const getContextMenuItems = useCallback(
    (params: GetContextMenuItemsParams): MenuItemDef[] => {
      const row = params.node?.data as DataRow | undefined
      if (!row) return []
      return [
        { name: '👤 구직활동중으로 복사', action: () => onCopyTo(row, 'active') },
        { name: '✅ 체결완료로 복사', action: () => onCopyTo(row, 'past') },
        { name: '⛔ 블랙리스트로 복사', action: () => onCopyTo(row, 'blacklist') },
      ]
    },
    [onCopyTo]
  )

  const onGridReady = useCallback((_e: GridReadyEvent) => {
    // sizeColumnsToFit 제거 — 48컬럼 전체 너비 재계산 불필요, 정의된 너비 그대로 유지
  }, [])

  const onBodyScroll = useCallback((e: BodyScrollEvent) => {
    if (!onLoadMore) return
    const api = e.api
    const lastRow = api.getLastDisplayedRowIndex()
    const totalRows = api.getDisplayedRowCount()
    if (totalRows > 0 && lastRow >= totalRows - 5) onLoadMore()
  }, [onLoadMore])

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const rowStyle = useCallback((params: any): Record<string, string | number> | undefined => {
    if (String(params.data?.source ?? '').includes('★NEW')) {
      return { background: '#fef2f2', fontWeight: 700 }
    }
    return undefined
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      {/* 로딩 바 */}
      {loading && (
        <div style={{ background: '#eff6ff', borderBottom: '1px solid #bfdbfe', padding: '6px 16px', fontSize: 13, color: '#2563eb', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>⟳</span>
          DB 로딩 중...
        </div>
      )}
      {/* 안내 */}
      {!loading && rows.length > 0 && (
        <div style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', padding: '4px 16px', fontSize: 12, color: '#64748b', flexShrink: 0 }}>
          <b>{rows.length.toLocaleString()}</b> / 전체 {total ? total.toLocaleString() : '?'}건 로드됨 · 스크롤하면 추가 로드 · 우클릭→탭 복사 · 헤더 클릭→정렬
        </div>
      )}
      {!loading && rows.length === 0 && (
        <div style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', padding: '12px 16px', fontSize: 14, color: '#64748b', flexShrink: 0, textAlign: 'center' }}>
          데이터 없음
        </div>
      )}
      <div
        className="ag-theme-quartz"
        style={{ flex: 1, width: '100%', minHeight: 0 }}
      >
        <AgGridReact
          rowData={rows}
          columnDefs={colDefs}
          defaultColDef={defaultColDef}
          components={components}
          rowHeight={38}
          headerHeight={36}
          suppressCellFocus={false}
          enableCellTextSelection
          suppressRowClickSelection
          getContextMenuItems={getContextMenuItems}
          onGridReady={onGridReady}
          onBodyScroll={onBodyScroll}
          getRowStyle={rowStyle}
          animateRows={false}
          suppressAnimationFrame={false}
          rowBuffer={20}
          domLayout="normal"
        />
      </div>
    </div>
  )
}
