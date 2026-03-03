'use client'

/**
 * /admin/candidates — Candidate Spreadsheet Grid
 * AG Grid Community v35 기반 고밀도 스프레드시트 UI.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { AgGridReact } from 'ag-grid-react'
import type { ColDef, GridReadyEvent, NewValueParams } from 'ag-grid-community'
import {
  ClientSideRowModelModule,
  ModuleRegistry,
  TextEditorModule,
  SelectEditorModule,
  TextFilterModule,
} from 'ag-grid-community'
import AdminNav from '@/components/admin/AdminNav'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'

import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-balham.css'

ModuleRegistry.registerModules([
  ClientSideRowModelModule,
  TextEditorModule,
  SelectEditorModule,
  TextFilterModule,
])

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

interface Candidate {
  id:                string
  status:            string | null
  photo_url:         string | null
  thumb_url:         string | null
  full_name:         string | null
  email:             string | null
  nationality:       string | null
  ancestry:          string | null
  gender:            string | null
  dob:               string | null
  current_location:  string | null
  e_visa:            string | null
  mobile_phone:      string | null
  kakaotalk:         string | null
  start_date:        string | null
  target:            string | null
  area_prefs:        string | null
  experience:        string | null
  employment:        string | null
  certification:     string | null
  desired_salary:    string | null
  current_salary:    string | null
  job_prefs:         string | null
  reference:         string | null
  arc_holders:       string | null
  housing:           string | null
  criminal_record:   string | null
  passport:          string | null
  source:            string | null
  admin_notes:       string | null
  created_at:        string | null
  updated_at:        string | null
}

const STATUS_VALUES = ['Active', 'Placed', 'Hold', 'Closed', 'Duplicate']

function buildColumns(onSave: (id: string, field: string, value: string) => void): ColDef[] {
  const base: Partial<ColDef> = {
    resizable: true, sortable: true, filter: true, editable: false, minWidth: 80,
  }

  const editable: Partial<ColDef> = {
    ...base,
    editable: true,
    cellStyle: { borderLeft: '2px solid #3b82f6' },
    onCellValueChanged: (e: NewValueParams) => {
      if (e.newValue !== e.oldValue) {
        onSave(e.data.id, e.colDef.field!, e.newValue ?? '')
      }
    },
  }

  return [
    { ...base, field: 'id', headerName: 'ID', width: 120, pinned: 'left',
      valueFormatter: (p) => String(p.value ?? '').slice(0, 14) },
    { ...editable, field: 'status', headerName: '상태', width: 100, pinned: 'left',
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: STATUS_VALUES },
      cellStyle: (p: { value: string }) => {
        const color: Record<string, string> = {
          Active: '#22c55e', Placed: '#3b82f6', Hold: '#eab308',
          Closed: '#6b7280', Duplicate: '#ef4444', Inactive: '#94a3b8',
        }
        return { color: color[p.value] ?? '#94a3b8', fontWeight: 600, borderLeft: '2px solid #3b82f6' }
      },
    },
    { ...base, field: 'thumb_url', headerName: '사진', width: 60,
      filter: false, sortable: false,
      cellRenderer: (p: { value: string | null; data: { photo_url?: string | null } }) => {
        if (!p.value) return ''
        const apiBase = typeof window !== 'undefined'
          ? (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000') : ''
        const src = p.value.startsWith('http') ? p.value : `${apiBase}${p.value}`
        const fullSrc = p.data.photo_url
          ? (p.data.photo_url.startsWith('http') ? p.data.photo_url : `${apiBase}${p.data.photo_url}`)
          : src
        return `<img src="${src}" alt="photo" style="width:24px;height:24px;border-radius:50%;object-fit:cover;cursor:pointer" onclick="window.__bridgePhotoModal__('${fullSrc}')" />`
      },
    },
    { ...base, field: 'full_name', headerName: '이름', width: 140 },
    { ...base, field: 'email', headerName: '이메일', width: 200 },
    { ...base, field: 'nationality', headerName: '국적', width: 100 },
    { ...base, field: 'ancestry', headerName: '혈통', width: 90 },
    { ...base, field: 'gender', headerName: '성별', width: 70 },
    { ...base, field: 'dob', headerName: '생년월일', width: 100 },
    { ...base, field: 'current_location', headerName: '현재위치', width: 100 },
    { ...base, field: 'e_visa', headerName: '비자', width: 100 },
    { ...base, field: 'mobile_phone', headerName: '전화', width: 130 },
    { ...base, field: 'kakaotalk', headerName: '카카오톡', width: 110 },
    { ...base, field: 'start_date', headerName: '시작가능일', width: 100 },
    { ...base, field: 'target', headerName: '희망지역', width: 100,
      valueGetter: (p) => [p.data?.target, p.data?.area_prefs].filter(Boolean).join(' / ') },
    { ...base, field: 'experience', headerName: '경력', width: 80 },
    { ...base, field: 'employment', headerName: '고용형태', width: 100 },
    { ...base, field: 'certification', headerName: '자격증', width: 140 },
    { ...base, field: 'desired_salary', headerName: '희망급여', width: 100 },
    { ...base, field: 'current_salary', headerName: '현재급여', width: 100 },
    { ...base, field: 'job_prefs', headerName: '직무선호', width: 120 },
    { ...editable, field: 'reference', headerName: '레퍼런스', width: 180,
      headerComponentParams: { template: '<span title="더블클릭 편집 가능">✏ 레퍼런스</span>' } },
    { ...base, field: 'arc_holders', headerName: 'ARC소지', width: 90 },
    { ...base, field: 'housing', headerName: '숙소', width: 80 },
    { ...base, field: 'criminal_record', headerName: '범죄기록', width: 100,
      cellStyle: (p: { value: string }) => p.value ? { color: '#fbbf24' } : null },
    { ...base, field: 'passport', headerName: '여권', width: 110 },
    { ...base, field: 'source', headerName: '지원경로', width: 100 },
    { ...editable, field: 'admin_notes', headerName: '메모', width: 220,
      headerComponentParams: { template: '<span title="더블클릭 편집 가능">✏ 메모</span>' } },
    { ...base, field: 'created_at', headerName: '타임스탬프', width: 130,
      valueFormatter: (p) => p.value ? new Date(p.value).toLocaleDateString('ko-KR') : '—' },
  ]
}

export default function CandidatesPage() {
  const { adminKey, authed, login, headers } = useAdminAuth()

  const [rows, setRows] = useState<Candidate[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [saveMsg, setSaveMsg] = useState('')
  const [photoModal, setPhotoModal] = useState<string | null>(null)

  const gridRef = useRef<AgGridReact>(null)

  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).__bridgePhotoModal__ = (url: string) => setPhotoModal(url)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return () => { delete (window as any).__bridgePhotoModal__ }
  }, [])

  const fetchData = useCallback(async (q: string = '') => {
    setLoading(true)
    setError(null)
    try {
      const h: Record<string, string> = {}
      if (adminKey) h['x-admin-key'] = adminKey

      const params = new URLSearchParams({ limit: '500', offset: '0' })
      if (q) params.set('search', q)

      const res = await fetch(`${API}/api/admin/candidates?${params}`, { headers: h })
      const json = await res.json()
      if (res.status === 403) { setError('관리자 키가 올바르지 않습니다.'); return }
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Error')
      setRows(json.data.candidates)
      setTotal(json.data.total)
    } catch (e) {
      setError(e instanceof Error ? e.message : '데이터 로드 실패')
    } finally {
      setLoading(false)
    }
  }, [adminKey])

  useEffect(() => {
    if (authed) fetchData()
  }, [authed, fetchData])

  const handleSave = useCallback(async (id: string, field: string, value: string) => {
    try {
      const res = await fetch(`${API}/api/admin/candidates/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body: JSON.stringify({ [field]: value }),
      })
      if (!res.ok) throw new Error('저장 실패')
      setSaveMsg(`✓ 저장됨 (${new Date().toLocaleTimeString('ko-KR')})`)
      setTimeout(() => setSaveMsg(''), 3000)
    } catch (e) {
      setSaveMsg('⚠ 저장 실패 — ' + (e instanceof Error ? e.message : ''))
    }
  }, [adminKey])

  const handleDelete = useCallback(async () => {
    const sel = gridRef.current?.api.getSelectedRows() ?? []
    if (!sel.length) return
    if (!confirm(`${sel.length}명을 삭제(soft delete)하시겠습니까?`)) return
    for (const row of sel) {
      await fetch(`${API}/api/admin/candidates/${row.id}`, {
        method: 'DELETE',
        headers: { 'x-admin-key': adminKey },
      })
    }
    fetchData(search)
  }, [adminKey, fetchData, search])

  const colDefs = buildColumns(handleSave)

  if (!authed) return <AdminAuth onLogin={login} error={error} />

  return (
    <div className="flex flex-col h-screen -mt-6 -mx-4">
      <div className="px-4 pt-4 shrink-0">
        <AdminNav active="/admin/candidates" />
      </div>

      {/* Header Bar */}
      <div className="flex items-center gap-4 px-4 py-3 bg-white border-b border-gray-200 shrink-0">
        <div>
          <h1 className="text-lg font-bold leading-none text-gray-900">지원자 관리</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            {loading ? '로딩 중…' : `${total}명 (표시: ${rows.length}명)`}
          </p>
        </div>
        <input
          className="input w-56 text-sm py-1.5"
          placeholder="이름 검색…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') fetchData(search) }}
        />
        <button type="button" className="text-sm text-blue-600 hover:underline"
          onClick={() => fetchData(search)}>↻ 새로고침</button>
        <button type="button" className="ml-2 text-sm text-red-500 hover:underline"
          onClick={handleDelete}>🗑 선택 삭제</button>
        {saveMsg && <span className="ml-auto text-xs text-green-600">{saveMsg}</span>}
      </div>

      {/* Editing hint */}
      <div className="px-4 py-1.5 bg-blue-50 border-b border-blue-100 text-xs text-blue-700 shrink-0">
        ✏ 파란 테두리 컬럼(<strong>레퍼런스</strong>, <strong>관리자 메모</strong>, <strong>상태</strong>)은 <strong>더블클릭</strong>으로 즉시 편집 가능합니다.
        &nbsp;·&nbsp; 행 선택(클릭) 후 「선택 삭제」로 Soft Delete.
      </div>

      {error && (
        <div className="px-4 py-2 bg-red-50 text-red-600 text-sm shrink-0">{error}</div>
      )}

      {/* AG Grid */}
      <div
        className="ag-theme-balham flex-1"
        style={{ '--ag-font-size': '12px', '--ag-row-height': '28px' } as React.CSSProperties}
      >
        <AgGridReact
          ref={gridRef}
          rowData={rows}
          columnDefs={colDefs}
          rowSelection="multiple"
          suppressRowClickSelection={false}
          animateRows={false}
          defaultColDef={{
            resizable: true, sortable: true, filter: true, editable: false,
          }}
          onGridReady={(e: GridReadyEvent) => e.api.sizeColumnsToFit()}
          loadingOverlayComponent={() => (
            <div className="text-gray-400 text-sm animate-pulse">데이터 로딩 중…</div>
          )}
          noRowsOverlayComponent={() => (
            <div className="text-gray-500 text-sm">지원자 없음</div>
          )}
        />
      </div>

      {/* Photo Modal */}
      {photoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
          onClick={() => setPhotoModal(null)}>
          <div className="relative max-w-lg max-h-[80vh]" onClick={(e) => e.stopPropagation()}>
            <img src={photoModal} alt="Candidate photo" className="max-w-full max-h-[80vh] rounded-xl shadow-2xl" />
            <button type="button" onClick={() => setPhotoModal(null)}
              className="absolute -top-3 -right-3 w-8 h-8 bg-white rounded-full shadow text-gray-600 hover:text-gray-900 flex items-center justify-center text-lg font-bold">
              &times;
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
