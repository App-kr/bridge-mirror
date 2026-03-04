'use client'

/**
 * /admin/candidates — Candidate Spreadsheet Grid
 * AG Grid Community v35 기반 고밀도 스프레드시트 UI.
 * 탭(활성/지난) + 드롭다운 + 이메일 발송 버튼 + 프로필 발송 + 일괄 작업.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { AgGridReact } from 'ag-grid-react'
import type { ColDef, GridReadyEvent, NewValueParams, ICellRendererParams } from 'ag-grid-community'
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
import { API_URL } from '@/lib/api'

import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-balham.css'

ModuleRegistry.registerModules([
  ClientSideRowModelModule,
  TextEditorModule,
  SelectEditorModule,
  TextFilterModule,
])

const API = API_URL

/* ── 상태/옵션 상수 ── */
const STATUS_VALUES = ['new', 'reviewing', 'interviewing', 'offered', 'placed', 'rejected', 'withdrawn', 'inactive']
const ACTIVE_STATUSES = ['new', 'reviewing', 'interviewing', 'offered']
const PAST_STATUSES = ['placed', 'rejected', 'withdrawn', 'inactive']

const START_DETAIL_OPTIONS = ['', '즉시 가능', '3월 시작', '4월 시작', '5월 시작', '6월 시작', '7월 시작', '8월 시작', '9월 시작', '10월 시작', '11월 시작', '12월 시작', '1월 시작', '2월 시작', '비자 발급 후 즉시', '현 계약 종료 후', '기타']
const HOUSING_TYPE_OPTIONS = ['', '하우징 희망', '월세지원 희망', '하우징 희망(반려동물)', '하우징 희망(가족)', '하우징 희망(커플)', '월세지원 희망(반려동물)', '월세지원 희망(가족)', '자가 해결', '무관', '기타']
const YN_OPTIONS = ['', 'Y', 'N']
const RESIDENCE_OPTIONS = ['', '국내거주', '해외거주']
const TARGET_LEVEL_CHOICES = ['유치부', '유초등', '초등', '초중등', '중등', '중고등', '고등', '성인', '유치부선호', '유초등선호', '초등선호', '초중등선호', '중고등선호', '성인선호', '무관', '기타']

const TEMPLATE_MAP: Record<string, { key: string; label: string }> = {
  email_contract:    { key: 'contract_offer',       label: '계약 안내' },
  email_immigration: { key: 'immigration_guide',    label: '출입국 안내' },
  email_overseas:    { key: 'overseas_visa_prep',   label: '영사 준비' },
  email_transition:  { key: 'job_transition_guide', label: '이직 안내' },
  email_arrival:     { key: 'arrival_guide',        label: '입국 안내' },
}

type TabType = 'active' | 'past'

/* ── 이메일 발송 셀 렌더러 ── */
function EmailCellRenderer(props: ICellRendererParams & { colDef: { field?: string } }) {
  const value = props.value
  const field = props.colDef.field ?? ''
  const candidateId = props.data?.id
  const candidateName = props.data?.full_name ?? '지원자'
  const tpl = TEMPLATE_MAP[field]

  if (value) {
    return <span style={{ color: '#6b7280', fontSize: 11 }}>완료 ({value})</span>
  }

  const handleSend = async () => {
    if (!tpl) return
    if (!confirm(`${candidateName}님에게 [${tpl.label}]를 발송하시겠습니까?`)) return
    try {
      const adminKey = document.querySelector<HTMLMetaElement>('meta[name="admin-key"]')?.content ?? ''
      const res = await fetch(`${API}/api/admin/candidates/${candidateId}/send-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body: JSON.stringify({ template_key: tpl.key }),
      })
      const json = await res.json()
      if (!res.ok) { alert(json.detail ?? '발송 실패'); return }
      alert(`발송 완료: ${json.data?.sent_to ?? ''}`)
      props.api.applyTransaction({
        update: [{ ...props.data, [field]: new Date().toISOString().slice(0, 10) }],
      })
    } catch {
      alert('발송 중 오류 발생')
    }
  }

  return (
    <button
      type="button"
      onClick={handleSend}
      style={{
        background: '#2563eb', color: '#fff', border: 'none', borderRadius: 4,
        padding: '2px 8px', fontSize: 11, cursor: 'pointer', fontWeight: 600,
      }}
    >
      발송
    </button>
  )
}

/* ── Target Level 다중선택 팝업 셀 렌더러 ── */
function TargetLevelRenderer(props: ICellRendererParams) {
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<string[]>(() => {
    const v = props.value ?? ''
    return v ? v.split(',').map((s: string) => s.trim()).filter(Boolean) : []
  })

  const handleToggle = (item: string) => {
    setSelected((prev) => {
      const next = prev.includes(item) ? prev.filter((x) => x !== item) : [...prev, item]
      return next
    })
  }

  const handleSave = () => {
    const newVal = selected.join(', ')
    setOpen(false)
    const adminKey = document.querySelector<HTMLMetaElement>('meta[name="admin-key"]')?.content ?? ''
    fetch(`${API}/api/admin/candidates/${props.data.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
      body: JSON.stringify({ target_level: newVal }),
    })
    props.node.setDataValue('target_level', newVal)
  }

  return (
    <div style={{ position: 'relative' }}>
      <span
        onClick={() => setOpen(!open)}
        style={{ cursor: 'pointer', borderBottom: '1px dashed #3b82f6', fontSize: 11 }}
      >
        {props.value || '선택'}
      </span>
      {open && (
        <div style={{
          position: 'absolute', top: 24, left: 0, zIndex: 100,
          background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8,
          padding: 8, width: 200, maxHeight: 260, overflowY: 'auto',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        }}>
          {TARGET_LEVEL_CHOICES.map((ch) => (
            <label key={ch} style={{ display: 'flex', gap: 4, fontSize: 11, padding: '2px 0', cursor: 'pointer' }}>
              <input type="checkbox" checked={selected.includes(ch)} onChange={() => handleToggle(ch)} />
              {ch}
            </label>
          ))}
          <button
            type="button"
            onClick={handleSave}
            style={{
              marginTop: 6, width: '100%', background: '#2563eb', color: '#fff',
              border: 'none', borderRadius: 4, padding: '4px 0', fontSize: 11,
              cursor: 'pointer', fontWeight: 600,
            }}
          >
            저장
          </button>
        </div>
      )}
    </div>
  )
}

/* ── 컬럼 빌드 ── */
function buildColumns(onSave: (id: string, field: string, value: string) => void): ColDef[] {
  const base: Partial<ColDef> = {
    resizable: true, sortable: true, filter: true, editable: false, minWidth: 70,
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

  const dropdown = (field: string, headerName: string, values: string[], width = 100): ColDef => ({
    ...editable,
    field,
    headerName,
    width,
    cellEditor: 'agSelectCellEditor',
    cellEditorParams: { values },
  })

  const emailSendCol = (field: string, headerName: string): ColDef => ({
    ...base,
    field,
    headerName,
    width: 100,
    editable: false,
    cellRenderer: EmailCellRenderer,
  })

  return [
    /* ── 기본 정보 (2-2 순서) ── */
    { ...base, field: 'id', headerName: 'ID', width: 110, pinned: 'left',
      headerCheckboxSelection: true, checkboxSelection: true,
      valueFormatter: (p) => String(p.value ?? '').slice(0, 14) },
    { ...editable, field: 'status', headerName: '상태', width: 100, pinned: 'left',
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: STATUS_VALUES },
      cellStyle: (p: { value: string }) => {
        const c: Record<string, string> = {
          new: '#22c55e', reviewing: '#eab308', interviewing: '#3b82f6', offered: '#8b5cf6',
          placed: '#0ea5e9', rejected: '#ef4444', withdrawn: '#94a3b8', inactive: '#6b7280',
        }
        return { color: c[p.value] ?? '#94a3b8', fontWeight: '600', borderLeft: '2px solid #3b82f6' }
      },
    },
    { ...base, field: 'thumb_url', headerName: '사진', width: 50, filter: false, sortable: false,
      cellRenderer: (p: ICellRendererParams) => {
        const src = p.value
        if (!src) return ''
        const full = p.data?.photo_url ?? src
        const url = src.startsWith('http') ? src : `${API}${src}`
        const fullUrl = full.startsWith('http') ? full : `${API}${full}`
        return `<img src="${url}" alt="" style="width:22px;height:22px;border-radius:50%;object-fit:cover;cursor:pointer" onclick="window.__bridgePhotoModal__('${fullUrl}')" />`
      },
    },
    { ...base, field: 'full_name', headerName: '이름', width: 130 },
    { ...base, field: 'email', headerName: '이메일', width: 180 },
    { ...base, field: 'nationality', headerName: '국적', width: 90 },
    { ...base, field: 'ancestry', headerName: '혈통', width: 80 },
    { ...base, field: 'gender', headerName: '성별', width: 60 },
    { ...base, field: 'dob', headerName: '생년월일', width: 95 },
    { ...base, field: 'current_location', headerName: '현재위치', width: 90 },
    { ...base, field: 'e_visa', headerName: '비자', width: 90 },
    { ...base, field: 'mobile_phone', headerName: '전화', width: 120 },
    { ...base, field: 'kakaotalk', headerName: '카카오톡', width: 100 },
    { ...base, field: 'start_date', headerName: '시작가능일', width: 95 },
    { ...base, field: 'area_prefs', headerName: '희망지역', width: 90 },
    { ...base, field: 'experience', headerName: '경력', width: 75 },
    { ...base, field: 'education_level', headerName: '학위', width: 80 },
    { ...base, field: 'major', headerName: '전공', width: 90 },
    { ...base, field: 'certification', headerName: '자격증', width: 120 },
    { ...base, field: 'desired_salary', headerName: '희망급여', width: 90 },
    { ...base, field: 'current_salary', headerName: '현재급여', width: 90 },
    { ...base, field: 'interview_time', headerName: '인터뷰시간', width: 100 },
    { ...base, field: 'employment', headerName: '고용형태', width: 80 },
    { ...base, field: 'job_prefs', headerName: '직무선호', width: 100 },
    { ...editable, field: 'reference', headerName: '레퍼런스', width: 140 },
    { ...base, field: 'arc_holders', headerName: 'ARC소지', width: 80 },
    { ...base, field: 'health_info', headerName: '건강정보', width: 90 },
    { ...base, field: 'personal_consideration', headerName: '개인고려', width: 90 },
    { ...base, field: 'piercings', headerName: '피어싱', width: 70 },
    { ...base, field: 'dependents', headerName: '부양가족', width: 80 },
    { ...base, field: 'pets', headerName: '반려동물', width: 80 },
    { ...base, field: 'married', headerName: '결혼여부', width: 80 },
    { ...base, field: 'housing', headerName: '숙소', width: 70 },
    { ...base, field: 'religion', headerName: '종교', width: 70 },
    { ...base, field: 'criminal_record', headerName: '범죄기록', width: 80 },
    { ...base, field: 'korean_criminal_record', headerName: '한국범죄기록', width: 100 },
    { ...base, field: 'consent', headerName: '동의', width: 60 },
    { ...base, field: 'fact_check', headerName: '사실확인', width: 80 },
    { ...base, field: 'source', headerName: '지원경로', width: 90 },
    { ...base, field: 'created_at', headerName: '타임스탬프', width: 100,
      valueFormatter: (p) => p.value ? new Date(p.value).toLocaleDateString('ko-KR') : '—' },

    /* ── 관리 컬럼 (2-3) ── */
    dropdown('residence_type', '거주구분', RESIDENCE_OPTIONS, 90),
    { ...base, field: 'target_level', headerName: '교육대상', width: 130,
      cellRenderer: TargetLevelRenderer },
    dropdown('start_detail', '시작상세', START_DETAIL_OPTIONS, 120),
    dropdown('housing_type', '주거형태', HOUSING_TYPE_OPTIONS, 130),
    { ...editable, field: 'recruiter_memo', headerName: '리크루터메모', width: 160 },
    { ...editable, field: 'preferences', headerName: '희망사항', width: 140 },
    { ...editable, field: 'dislikes', headerName: '기피사항', width: 140 },
    dropdown('contract_offered', '계약제안', YN_OPTIONS, 80),
    dropdown('contract_progress', '진행여부', YN_OPTIONS, 80),

    /* ── 이메일 발송 (2-5) ── */
    emailSendCol('email_contract', '메일1(계약)'),
    emailSendCol('email_immigration', '메일2(출입국)'),
    emailSendCol('email_overseas', '메일3(영사)'),
    emailSendCol('email_transition', '메일4(이직)'),
    emailSendCol('email_arrival', '메일5(입국)'),

    /* ── 배치/관리 ── */
    { ...editable, field: 'placed_company', headerName: '채용처', width: 120 },
    { ...editable, field: 'placed_salary', headerName: '임금', width: 90 },
    { ...editable, field: 'start_month', headerName: '개시월', width: 80 },
    { ...editable, field: 'housing_detail', headerName: '숙박내용', width: 110 },
    { ...editable, field: 'referral_fee', headerName: '소개비용', width: 90 },
    { ...editable, field: 'process_date', headerName: '처리일자', width: 90 },
    { ...editable, field: 'past_placement', headerName: '과거채용', width: 100 },

    /* ── 내부 메모 ── */
    { ...editable, field: 'admin_notes', headerName: '메모', width: 200 },
    { ...editable, field: 'assigned_to', headerName: '담당자', width: 90 },
  ]
}

/* ── 프로필 발송 모달 ── */
function ProfileSendModal({
  candidates, adminKey, onClose,
}: {
  candidates: { id: string; full_name: string | null; nationality: string | null; recruiter_memo: string | null; preferences: string | null; dislikes: string | null }[]
  adminKey: string
  onClose: () => void
}) {
  const [toEmail, setToEmail] = useState('')
  const [schoolName, setSchoolName] = useState('')
  const [sending, setSending] = useState(false)
  const [memos, setMemos] = useState<Record<string, { recruiter_memo: string; preferences: string; dislikes: string }>>(() => {
    const m: Record<string, { recruiter_memo: string; preferences: string; dislikes: string }> = {}
    for (const c of candidates) {
      m[c.id] = {
        recruiter_memo: c.recruiter_memo ?? '',
        preferences: c.preferences ?? '',
        dislikes: c.dislikes ?? '',
      }
    }
    return m
  })

  const handleSend = async () => {
    if (!toEmail || !toEmail.includes('@')) { alert('유효한 이메일을 입력하세요.'); return }
    setSending(true)
    try {
      // 메모 먼저 저장
      for (const c of candidates) {
        const m = memos[c.id]
        if (m) {
          await fetch(`${API}/api/admin/candidates/${c.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
            body: JSON.stringify({
              recruiter_memo: m.recruiter_memo,
              preferences: m.preferences,
              dislikes: m.dislikes,
            }),
          })
        }
      }
      // 프로필 발송
      const res = await fetch(`${API}/api/admin/candidates/send-profiles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body: JSON.stringify({
          candidate_ids: candidates.map((c) => Number(c.id)),
          to_email: toEmail,
          school_name: schoolName || undefined,
        }),
      })
      const json = await res.json()
      if (!res.ok) { alert(json.detail ?? '발송 실패'); return }
      alert(`프로필 발송 완료: ${toEmail}`)
      onClose()
    } catch {
      alert('발송 중 오류 발생')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-[640px] max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}>
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-base font-bold text-gray-900">프로필 발송</h2>
          <p className="text-xs text-gray-500 mt-0.5">{candidates.length}명 선택됨 · 이름/이메일/전화/카카오/주소 제외</p>
        </div>

        <div className="px-6 py-4 space-y-3">
          <div>
            <label className="text-xs font-medium text-gray-600 block mb-1">수신 이메일 (교육기관)</label>
            <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="school@example.com" value={toEmail} onChange={(e) => setToEmail(e.target.value)} />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 block mb-1">학교/기관명 (선택)</label>
            <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="OO 어학원" value={schoolName} onChange={(e) => setSchoolName(e.target.value)} />
          </div>
        </div>

        <div className="px-6 py-3 border-t border-gray-100">
          <p className="text-xs font-medium text-gray-600 mb-2">선택된 후보자 (메모 빠른 편집)</p>
          {candidates.map((c) => (
            <div key={c.id} className="bg-gray-50 rounded-lg p-3 mb-2 text-xs">
              <div className="flex items-center gap-2 mb-2">
                <span className="font-bold text-gray-800">ID #{String(c.id).slice(0, 10)}</span>
                <span className="text-gray-500">{c.nationality ?? ''}</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <span className="text-gray-500 block mb-0.5">리크루터메모</span>
                  <textarea className="w-full border rounded px-2 py-1 text-xs resize-none" rows={2}
                    value={memos[c.id]?.recruiter_memo ?? ''}
                    onChange={(e) => setMemos((p) => ({ ...p, [c.id]: { ...p[c.id], recruiter_memo: e.target.value } }))} />
                </div>
                <div>
                  <span className="text-gray-500 block mb-0.5">희망사항</span>
                  <textarea className="w-full border rounded px-2 py-1 text-xs resize-none" rows={2}
                    value={memos[c.id]?.preferences ?? ''}
                    onChange={(e) => setMemos((p) => ({ ...p, [c.id]: { ...p[c.id], preferences: e.target.value } }))} />
                </div>
                <div>
                  <span className="text-gray-500 block mb-0.5">기피사항</span>
                  <textarea className="w-full border rounded px-2 py-1 text-xs resize-none" rows={2}
                    value={memos[c.id]?.dislikes ?? ''}
                    onChange={(e) => setMemos((p) => ({ ...p, [c.id]: { ...p[c.id], dislikes: e.target.value } }))} />
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-2">
          <button type="button" className="px-4 py-2 text-xs text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
            onClick={onClose}>취소</button>
          <button type="button"
            className="px-4 py-2 text-xs text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            disabled={sending || !toEmail}
            onClick={handleSend}>
            {sending ? '발송 중…' : '프로필 발송'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── 메인 페이지 ── */
export default function CandidatesPage() {
  const { adminKey, authed, login, waking } = useAdminAuth()

  const [rows, setRows] = useState<Record<string, string | null>[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [saveMsg, setSaveMsg] = useState('')
  const [photoModal, setPhotoModal] = useState<string | null>(null)
  const [tab, setTab] = useState<TabType>('active')
  const [bulkStatus, setBulkStatus] = useState('')
  const [bulkEmail, setBulkEmail] = useState('')
  const [profileModal, setProfileModal] = useState(false)

  const gridRef = useRef<AgGridReact>(null)

  // admin key를 meta 태그로 노출 (셀 렌더러에서 접근)
  useEffect(() => {
    let meta = document.querySelector<HTMLMetaElement>('meta[name="admin-key"]')
    if (!meta) {
      meta = document.createElement('meta')
      meta.name = 'admin-key'
      document.head.appendChild(meta)
    }
    meta.content = adminKey
  }, [adminKey])

  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).__bridgePhotoModal__ = (url: string) => setPhotoModal(url)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return () => { delete (window as any).__bridgePhotoModal__ }
  }, [])

  const fetchData = useCallback(async (q: string = '', statusFilter: TabType = tab) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ limit: '500', offset: '0', status: statusFilter })
      if (q) params.set('search', q)

      const res = await fetch(`${API}/api/admin/candidates?${params}`, {
        headers: { 'x-admin-key': adminKey },
      })
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
  }, [adminKey, tab])

  useEffect(() => {
    if (authed) fetchData(search, tab)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed, tab])

  const handleSave = useCallback(async (id: string, field: string, value: string) => {
    try {
      const res = await fetch(`${API}/api/admin/candidates/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body: JSON.stringify({ [field]: value }),
      })
      if (!res.ok) throw new Error('저장 실패')
      setSaveMsg(`저장됨 (${new Date().toLocaleTimeString('ko-KR')})`)
      setTimeout(() => setSaveMsg(''), 3000)
    } catch (e) {
      setSaveMsg('저장 실패: ' + (e instanceof Error ? e.message : ''))
    }
  }, [adminKey])

  const handleDelete = useCallback(async () => {
    const sel = gridRef.current?.api.getSelectedRows() ?? []
    if (!sel.length) return
    if (!confirm(`${sel.length}명을 삭제(soft delete)하시겠습니까?`)) return
    for (const row of sel) {
      await fetch(`${API}/api/admin/candidates/${row.id}`, {
        method: 'DELETE', headers: { 'x-admin-key': adminKey },
      })
    }
    fetchData(search, tab)
  }, [adminKey, fetchData, search, tab])

  const handleBulkStatus = useCallback(async () => {
    if (!bulkStatus) return
    const sel = gridRef.current?.api.getSelectedRows() ?? []
    if (!sel.length) { alert('행을 선택해주세요.'); return }
    if (!confirm(`${sel.length}명의 상태를 "${bulkStatus}"로 변경하시겠습니까?`)) return
    try {
      const res = await fetch(`${API}/api/admin/candidates/bulk-status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body: JSON.stringify({ ids: sel.map((r: Record<string, string | null>) => r.id), status: bulkStatus }),
      })
      if (!res.ok) throw new Error('일괄 변경 실패')
      setSaveMsg(`${sel.length}명 → ${bulkStatus}`)
      setTimeout(() => setSaveMsg(''), 3000)
      fetchData(search, tab)
    } catch (e) {
      setSaveMsg('일괄 변경 실패: ' + (e instanceof Error ? e.message : ''))
    }
  }, [adminKey, bulkStatus, fetchData, search, tab])

  const handleBulkEmail = useCallback(async () => {
    if (!bulkEmail) return
    const sel = gridRef.current?.api.getSelectedRows() ?? []
    if (!sel.length) { alert('행을 선택해주세요.'); return }
    const tpl = TEMPLATE_MAP[bulkEmail]
    if (!tpl) return
    if (!confirm(`${sel.length}명에게 [${tpl.label}]를 일괄 발송하시겠습니까?`)) return
    try {
      const res = await fetch(`${API}/api/admin/candidates/bulk-send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body: JSON.stringify({
          candidate_ids: sel.map((r: Record<string, string | null>) => Number(r.id)),
          template_key: tpl.key,
        }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? '일괄 발송 실패')
      setSaveMsg(json.message ?? '일괄 발송 완료')
      setTimeout(() => setSaveMsg(''), 5000)
      fetchData(search, tab)
    } catch (e) {
      setSaveMsg('일괄 발송 실패: ' + (e instanceof Error ? e.message : ''))
    }
  }, [adminKey, bulkEmail, fetchData, search, tab])

  const handleExportCsv = useCallback(() => {
    gridRef.current?.api.exportDataAsCsv({
      fileName: `candidates_${tab}_${new Date().toISOString().slice(0, 10)}.csv`,
    })
  }, [tab])

  const getSelectedForProfile = useCallback(() => {
    const sel = gridRef.current?.api.getSelectedRows() ?? []
    return sel.map((r: Record<string, string | null>) => ({
      id: r.id ?? '',
      full_name: r.full_name ?? null,
      nationality: r.nationality ?? null,
      recruiter_memo: r.recruiter_memo ?? null,
      preferences: r.preferences ?? null,
      dislikes: r.dislikes ?? null,
    }))
  }, [])

  const colDefs = buildColumns(handleSave)

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="flex flex-col h-screen -mt-6 -mx-4">
      <div className="px-4 pt-4 shrink-0">
        <AdminNav active="/admin/candidates" />
      </div>

      {/* Header */}
      <div className="flex items-center gap-4 px-4 py-3 bg-white border-b border-gray-200 shrink-0">
        <div>
          <h1 className="text-lg font-bold leading-none text-gray-900">지원자 관리</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            {loading ? '로딩 중…' : `${total}명 (표시: ${rows.length}명)`}
          </p>
        </div>

        {/* Tabs */}
        <div className="flex bg-gray-100 rounded-lg p-0.5 ml-2">
          <button type="button"
            className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
              tab === 'active' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => setTab('active')}>
            활성 지원자
          </button>
          <button type="button"
            className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
              tab === 'past' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => setTab('past')}>
            지난 지원자
          </button>
        </div>

        <input
          className="input w-48 text-sm py-1.5"
          placeholder="이름/이메일 검색…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') fetchData(search, tab) }}
        />
        <button type="button" className="text-sm text-blue-600 hover:underline"
          onClick={() => fetchData(search, tab)}>새로고침</button>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 border-b border-gray-200 shrink-0 text-xs flex-wrap">
        <span className="text-gray-500 font-medium">일괄:</span>

        {/* 상태 변경 */}
        <select className="border border-gray-300 rounded px-2 py-1 text-xs bg-white"
          value={bulkStatus} onChange={(e) => setBulkStatus(e.target.value)}>
          <option value="">상태 선택</option>
          {(tab === 'active' ? PAST_STATUSES : ACTIVE_STATUSES).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <button type="button"
          className="px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-40"
          onClick={handleBulkStatus} disabled={!bulkStatus}>
          {tab === 'active' ? '지난으로 이동' : '활성으로 이동'}
        </button>

        <span className="text-gray-300">|</span>

        {/* 일괄 메일 */}
        <select className="border border-gray-300 rounded px-2 py-1 text-xs bg-white"
          value={bulkEmail} onChange={(e) => setBulkEmail(e.target.value)}>
          <option value="">메일 선택</option>
          {Object.entries(TEMPLATE_MAP).map(([field, tpl]) => (
            <option key={field} value={field}>{tpl.label}</option>
          ))}
        </select>
        <button type="button"
          className="px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-40"
          onClick={handleBulkEmail} disabled={!bulkEmail}>
          일괄 발송
        </button>

        <span className="text-gray-300">|</span>

        {/* 프로필 발송 */}
        <button type="button"
          className="px-2 py-1 bg-purple-600 text-white rounded hover:bg-purple-700"
          onClick={() => {
            const sel = getSelectedForProfile()
            if (!sel.length) { alert('행을 선택해주세요.'); return }
            setProfileModal(true)
          }}>
          프로필 발송
        </button>

        <button type="button" className="text-red-500 hover:underline" onClick={handleDelete}>삭제</button>

        <div className="ml-auto flex items-center gap-3">
          <button type="button" className="text-gray-500 hover:text-gray-700" onClick={handleExportCsv}>CSV</button>
          {saveMsg && <span className="text-green-600 font-medium">{saveMsg}</span>}
        </div>
      </div>

      {/* Hint */}
      <div className="px-4 py-1 bg-blue-50 border-b border-blue-100 text-[11px] text-blue-700 shrink-0">
        파란 테두리 컬럼은 <strong>더블클릭</strong> 편집 · 체크박스 선택 → 일괄 작업 · 교육대상 클릭 → 다중선택
      </div>

      {error && <div className="px-4 py-2 bg-red-50 text-red-600 text-sm shrink-0">{error}</div>}

      {/* AG Grid */}
      <div className="ag-theme-balham flex-1"
        style={{ '--ag-font-size': '12px', '--ag-row-height': '28px' } as React.CSSProperties}>
        <AgGridReact
          ref={gridRef}
          rowData={rows}
          columnDefs={colDefs}
          rowSelection="multiple"
          suppressRowClickSelection={true}
          animateRows={false}
          getRowId={(p) => String(p.data.id ?? p.data.candidate_id ?? '')}
          defaultColDef={{ resizable: true, sortable: true, filter: true, editable: false }}
          onGridReady={(e: GridReadyEvent) => e.api.sizeColumnsToFit()}
          loadingOverlayComponent={() => <div className="text-gray-400 text-sm animate-pulse">데이터 로딩 중…</div>}
          noRowsOverlayComponent={() => <div className="text-gray-500 text-sm">지원자 없음</div>}
        />
      </div>

      {/* Photo Modal */}
      {photoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
          onClick={() => setPhotoModal(null)}>
          <div className="relative max-w-lg max-h-[80vh]" onClick={(e) => e.stopPropagation()}>
            <img src={photoModal} alt="Photo" className="max-w-full max-h-[80vh] rounded-xl shadow-2xl" />
            <button type="button" onClick={() => setPhotoModal(null)}
              className="absolute -top-3 -right-3 w-8 h-8 bg-white rounded-full shadow text-gray-600 hover:text-gray-900 flex items-center justify-center text-lg font-bold">
              &times;
            </button>
          </div>
        </div>
      )}

      {/* Profile Send Modal */}
      {profileModal && (
        <ProfileSendModal
          candidates={getSelectedForProfile()}
          adminKey={adminKey}
          onClose={() => { setProfileModal(false); fetchData(search, tab) }}
        />
      )}
    </div>
  )
}
