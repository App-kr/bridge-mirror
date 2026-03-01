'use client'

/**
 * /admin/candidates — Candidate Spreadsheet Grid
 *
 * AG Grid Community v35 기반 고밀도 스프레드시트 UI.
 * 인라인 더블클릭 편집: admin_notes, reference, status
 * 보호: X-Admin-Key (ADMIN_API_KEY)
 */

import { useCallback, useEffect, useRef, useState, useMemo } from 'react'
import { AgGridReact } from 'ag-grid-react'
import type { ColDef, GridReadyEvent, NewValueParams } from 'ag-grid-community'
import {
  ClientSideRowModelModule,
  ModuleRegistry,
  TextEditorModule,
  SelectEditorModule,
  TextFilterModule,
} from 'ag-grid-community'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyColDef = ColDef<any, any>

import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-balham.css'

ModuleRegistry.registerModules([
  ClientSideRowModelModule,
  TextEditorModule,
  SelectEditorModule,
  TextFilterModule,
])

const API     = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
// Admin key는 절대 NEXT_PUBLIC_ 접두어 사용 금지 (클라이언트 번들 노출)
const ENV_KEY = ''

// ── 타입 ──────────────────────────────────────────────────────────────────────
interface Candidate {
  id:               string
  full_name:        string | null
  email:            string | null
  nationality:      string | null
  ancestry:         string | null
  dob:              string | null
  gender:           string | null
  current_location: string | null
  e_visa:           string | null
  mobile_phone:     string | null
  kakaotalk:        string | null
  certification:    string | null
  employment:       string | null
  area_prefs:       string | null
  target_age:       string | null
  housing:          string | null
  reference:        string | null
  criminal_record:  string | null
  passport:         string | null
  photo_url:        string | null
  thumb_url:        string | null
  admin_notes:      string | null
  status:           string | null
  created_at:       string | null
  updated_at:       string | null
}

// ── 컬럼 정의 ─────────────────────────────────────────────────────────────────
const STATUS_VALUES = ['Active', 'Placed', 'Hold', 'Closed', 'Duplicate']

function buildColumns(onSave: (id: string, field: string, value: string) => void): ColDef[] {
  const base: Partial<ColDef> = {
    resizable:  true,
    sortable:   true,
    filter:     true,
    editable:   false,
    minWidth:   80,
  }

  const editable: Partial<ColDef> = {
    ...base,
    editable:        true,
    cellStyle:       { borderLeft: '2px solid #3b82f6' },
    onCellValueChanged: (e: NewValueParams) => {
      if (e.newValue !== e.oldValue) {
        onSave(e.data.id, e.colDef.field!, e.newValue ?? '')
      }
    },
  }

  return [
    // ── 식별 ────────────────────────────────────────────────────────────────
    { ...base, field: 'id',       headerName: 'ID',     width: 72,  pinned: 'left',
      valueFormatter: (p) => String(p.value ?? '').slice(0, 8) + '…' },
    { ...editable, field: 'status', headerName: '상태', width: 100, pinned: 'left',
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: STATUS_VALUES },
      cellStyle: (p: { value: string }) => {
        const color: Record<string, string> = {
          Active: '#22c55e', Placed: '#3b82f6', Hold: '#eab308',
          Closed: '#6b7280', Duplicate: '#ef4444',
        }
        return { color: color[p.value] ?? '#94a3b8', fontWeight: 600, borderLeft: '2px solid #3b82f6' }
      },
    },

    // ── 사진 ───────────────────────────────────────────────────────────────
    { ...base, field: 'thumb_url', headerName: '사진', width: 60,
      filter: false, sortable: false,
      cellRenderer: (p: { value: string | null; data: { photo_url?: string | null } }) => {
        if (!p.value) return ''
        const apiBase = typeof window !== 'undefined'
          ? (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000') : ''
        const src = p.value.startsWith('http') ? p.value : `${apiBase}${p.value}`
        const fullSrc = p.data.photo_url
          ? (p.data.photo_url.startsWith('http') ? p.data.photo_url : `${apiBase}${p.data.photo_url}`)
          : src
        return `<img src="${src}" alt="photo" style="width:24px;height:24px;border-radius:50%;object-fit:cover;cursor:pointer" onclick="window.__bridgePhotoModal__('${fullSrc}')" />`
      },
    },

    // ── 인적사항 ─────────────────────────────────────────────────────────────
    { ...base, field: 'full_name',        headerName: '이름',       width: 130 },
    { ...base, field: 'email',            headerName: '메일',       width: 200 },
    { ...base, field: 'nationality',      headerName: '국적',       width: 110 },
    { ...base, field: 'ancestry',         headerName: '혈통',       width: 90  },
    { ...base, field: 'gender',           headerName: '성별',       width: 70  },
    { ...base, field: 'dob',              headerName: '생년월일',   width: 110,
      valueFormatter: (p) => (p.value ?? '').slice(0, 10) },
    { ...base, field: 'current_location', headerName: '현재위치',   width: 140 },

    // ── 비자 & 연락처 ────────────────────────────────────────────────────────
    { ...base, field: 'e_visa',       headerName: '비자',     width: 120 },
    { ...base, field: 'mobile_phone', headerName: '전화',     width: 140 },
    { ...base, field: 'kakaotalk',    headerName: '카톡',     width: 120 },
    { ...base, field: 'passport',     headerName: '여권',     width: 130 },

    // ── 자격 & 경력 ──────────────────────────────────────────────────────────
    { ...base, field: 'certification', headerName: '자격',   width: 160 },
    { ...base, field: 'employment',    headerName: '학위/경력', width: 180 },
    { ...base, field: 'criminal_record', headerName: '범죄경력', width: 130,
      cellStyle: (p: { value: string }) => p.value ? { color: '#fbbf24' } : null },

    // ── 선호사항 ─────────────────────────────────────────────────────────────
    { ...base, field: 'target_age',  headerName: '선호연령',  width: 120 },
    { ...base, field: 'area_prefs',  headerName: '선호지역',  width: 150 },
    { ...base, field: 'housing',     headerName: '숙소',      width: 90  },

    // ── 편집 가능 컬럼 (더블클릭) ───────────────────────────────────────────
    { ...editable, field: 'reference',   headerName: '레퍼런스',     width: 200,
      headerComponentParams: { template: '<span title="더블클릭 편집 가능">✏ 레퍼런스</span>' } },
    { ...editable, field: 'admin_notes', headerName: '관리자 메모',  width: 240,
      headerComponentParams: { template: '<span title="더블클릭 편집 가능">✏ 관리자 메모</span>' } },

    // ── 날짜 ────────────────────────────────────────────────────────────────
    { ...base, field: 'created_at', headerName: '등록일', width: 130,
      valueFormatter: (p) => p.value ? new Date(p.value).toLocaleDateString('ko-KR') : '—' },
    { ...base, field: 'updated_at', headerName: '수정일', width: 130,
      valueFormatter: (p) => p.value ? new Date(p.value).toLocaleDateString('ko-KR') : '—' },
  ]
}

// ── Admin Navigation ──────────────────────────────────────────────────────────
function AdminNav({ active }: { active: string }) {
  const items = [
    { href: '/admin',              label: 'Ad Posts',     icon: '📢' },
    { href: '/admin/posts',        label: 'Posts',        icon: '📝' },
    { href: '/admin/interviews',   label: 'Interviews',   icon: '🎥' },
    { href: '/admin/applications', label: 'Applications', icon: '📋' },
    { href: '/admin/payments',     label: 'Payments',     icon: '💳' },
    { href: '/admin/candidates',   label: 'Candidates',   icon: '👥' },
  ]
  return (
    <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
      {items.map((nav) => (
        <a key={nav.href} href={nav.href}
          className={`card !p-3 text-center text-sm font-medium transition-all
            ${nav.href === active
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'hover:border-blue-300 text-gray-600 hover:text-blue-600'}`}>
          <span className="text-lg block mb-1">{nav.icon}</span>
          {nav.label}
        </a>
      ))}
    </div>
  )
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────────
export default function CandidatesPage() {
  const [adminKey,  setAdminKey]  = useState(ENV_KEY)
  const [keyInput,  setKeyInput]  = useState('')
  const [authed,    setAuthed]    = useState(Boolean(ENV_KEY))

  const [rows,      setRows]      = useState<Candidate[]>([])
  const [total,     setTotal]     = useState(0)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState<string | null>(null)
  const [search,    setSearch]    = useState('')
  const [saveMsg,   setSaveMsg]   = useState('')
  const [photoModal, setPhotoModal] = useState<string | null>(null)

  const gridRef = useRef<AgGridReact>(null)

  // Global handler for AG Grid cellRenderer onclick
  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).__bridgePhotoModal__ = (url: string) => setPhotoModal(url)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return () => { delete (window as any).__bridgePhotoModal__ }
  }, [])

  // ── Fetch ──────────────────────────────────────────────────────────────────
  const fetchData = useCallback(async (key: string, q: string = '') => {
    setLoading(true)
    setError(null)
    try {
      const headers: Record<string, string> = {}
      if (key) headers['x-admin-key'] = key

      const params = new URLSearchParams({ limit: '500', offset: '0' })
      if (q) params.set('search', q)

      const res  = await fetch(`${API}/api/admin/candidates?${params}`, { headers })
      const json = await res.json()

      if (res.status === 403) {
        setError('관리자 키가 올바르지 않습니다.')
        setAuthed(false)
        return
      }
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Error')

      setRows(json.data.candidates)
      setTotal(json.data.total)
      setAuthed(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : '데이터 로드 실패')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (authed) fetchData(adminKey)
  }, [authed, adminKey, fetchData])

  // ── 인라인 저장 ────────────────────────────────────────────────────────────
  const handleSave = useCallback(async (id: string, field: string, value: string) => {
    try {
      const res = await fetch(`${API}/api/admin/candidates/${id}`, {
        method:  'PATCH',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body:    JSON.stringify({ [field]: value }),
      })
      if (!res.ok) throw new Error('저장 실패')
      setSaveMsg(`✓ 저장됨 (${new Date().toLocaleTimeString('ko-KR')})`)
      setTimeout(() => setSaveMsg(''), 3000)
    } catch (e) {
      setSaveMsg('⚠ 저장 실패 — ' + (e instanceof Error ? e.message : ''))
    }
  }, [adminKey])

  // ── Soft Delete ────────────────────────────────────────────────────────────
  const handleDelete = useCallback(async () => {
    const sel = gridRef.current?.api.getSelectedRows() ?? []
    if (!sel.length) return
    if (!confirm(`${sel.length}명을 삭제(soft delete)하시겠습니까?`)) return
    for (const row of sel) {
      await fetch(`${API}/api/admin/candidates/${row.id}`, {
        method:  'DELETE',
        headers: { 'x-admin-key': adminKey },
      })
    }
    fetchData(adminKey, search)
  }, [adminKey, fetchData, search])

  // ── 컬럼 (memoized per onSave) ─────────────────────────────────────────────
  const colDefs = buildColumns(handleSave)

  // ── 인증 화면 ──────────────────────────────────────────────────────────────
  if (!authed) {
    return (
      <div className="max-w-sm mx-auto mt-32 space-y-6 text-center">
        <h1 className="text-2xl font-bold">관리자 인증</h1>
        <p className="text-gray-500 text-sm">ADMIN_API_KEY를 입력하세요</p>
        <input
          type="password"
          className="input text-center w-full"
          placeholder="Admin key"
          value={keyInput}
          onChange={(e) => setKeyInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { setAdminKey(keyInput); setAuthed(true) }
          }}
        />
        <button className="btn-primary w-full"
          onClick={() => { setAdminKey(keyInput); setAuthed(true) }}>
          접속
        </button>
        {error && <p className="text-red-400 text-sm">{error}</p>}
      </div>
    )
  }

  // ── 그리드 ────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-screen -mt-4">

      {/* ── Admin Navigation ──────────────────────────────────────────── */}
      <div className="px-4 pt-4 shrink-0">
        <AdminNav active="/admin/candidates" />
      </div>

      {/* ── 헤더 바 ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-4 px-4 py-3 bg-gray-950 border-b border-gray-800 shrink-0">
        <div>
          <h1 className="text-lg font-bold leading-none">지원자 관리</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            {loading ? '로딩 중…' : `${total}명 (표시: ${rows.length}명)`}
          </p>
        </div>

        {/* 검색 */}
        <input
          className="input w-56 text-sm py-1.5"
          placeholder="이름 검색…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') fetchData(adminKey, search) }}
        />
        <button
          className="text-sm text-blue-400 hover:underline"
          onClick={() => fetchData(adminKey, search)}
        >↻ 새로고침</button>

        {/* Soft Delete */}
        <button
          className="ml-2 text-sm text-red-400 hover:underline"
          onClick={handleDelete}
        >🗑 선택 삭제</button>

        {/* 저장 메시지 */}
        {saveMsg && (
          <span className="ml-auto text-xs text-green-400">{saveMsg}</span>
        )}

        {/* /admin 링크 */}
        <a href="/admin" className="ml-auto text-xs text-gray-600 hover:text-gray-400">
          ← Admin Home
        </a>
      </div>

      {/* ── 에디팅 안내 ──────────────────────────────────────────────────── */}
      <div className="px-4 py-1.5 bg-blue-950/40 border-b border-blue-900/40 text-xs text-blue-300 shrink-0">
        ✏ 파란 테두리 컬럼(<strong>레퍼런스</strong>, <strong>관리자 메모</strong>, <strong>상태</strong>)은 <strong>더블클릭</strong>으로 즉시 편집 가능합니다.
        &nbsp;·&nbsp; 행 선택(클릭) 후 「선택 삭제」로 Soft Delete.
      </div>

      {/* ── 오류 ────────────────────────────────────────────────────────── */}
      {error && (
        <div className="px-4 py-2 bg-red-900/40 text-red-300 text-sm shrink-0">
          {error}
        </div>
      )}

      {/* ── AG Grid ──────────────────────────────────────────────────────── */}
      <div
        className="ag-theme-balham-dark flex-1"
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
            resizable:  true,
            sortable:   true,
            filter:     true,
            editable:   false,
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

      {/* ── Photo Modal ──────────────────────────────────────────────────── */}
      {photoModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
          onClick={() => setPhotoModal(null)}
        >
          <div className="relative max-w-lg max-h-[80vh]" onClick={(e) => e.stopPropagation()}>
            <img src={photoModal} alt="Candidate photo" className="max-w-full max-h-[80vh] rounded-xl shadow-2xl" />
            <button
              type="button"
              onClick={() => setPhotoModal(null)}
              className="absolute -top-3 -right-3 w-8 h-8 bg-white rounded-full shadow text-gray-600 hover:text-gray-900 flex items-center justify-center text-lg font-bold"
            >
              &times;
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
