'use client'

/**
 * /admin/inquiries — 채용의뢰 관리
 * client_inquiries 테이블 조회/수정.
 */

import { useCallback, useEffect, useState } from 'react'
import AdminNav from '@/components/admin/AdminNav'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { STAFF_NAMES } from '@/lib/team'

import { API_URL } from '@/lib/api'

const API = API_URL

interface Inquiry {
  id:             number
  submitted_at:   string | null
  email:          string | null
  school_name:    string | null
  location:       string | null
  contact_name:   string | null
  phone:          string | null
  start_date:     string | null
  vacancies:      string | null
  teaching_age:   string | null
  salary_raw:     string | null
  housing_type:   string | null
  housing_detail: string | null
  benefits:       string | null
  working_hours:  string | null
  memo:           string | null
  source:         string | null
  inbox_status:   string | null
  notes:          string | null
  assigned_to:    string | null
  last_activity:  string | null
}

const STATUS_OPTIONS = ['pending', 'processing', 'completed']

export default function InquiriesPage() {
  const { adminKey, authed, login, waking } = useAdminAuth()

  const [rows, setRows] = useState<Inquiry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [saveMsg, setSaveMsg] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/inquiries?limit=200`, {
        headers: { 'x-admin-key': adminKey },
      })
      const json = await res.json()
      if (res.status === 403) { setError('관리자 키가 올바르지 않습니다.'); return }
      if (!res.ok || !json.success) throw new Error(json.detail ?? 'Error')
      setRows(json.data.inquiries)
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

  const handleUpdate = useCallback(async (id: number, field: string, value: string) => {
    try {
      const res = await fetch(`${API}/api/admin/inquiries/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body: JSON.stringify({ [field]: value }),
      })
      if (!res.ok) throw new Error('저장 실패')
      setSaveMsg(`#${id} ${field} 저장됨`)
      setTimeout(() => setSaveMsg(''), 3000)
      // Update local row
      setRows((prev) =>
        prev.map((r) => (r.id === id ? { ...r, [field]: value } : r))
      )
    } catch (e) {
      setSaveMsg('저장 실패: ' + (e instanceof Error ? e.message : ''))
    }
  }, [adminKey])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="max-w-[1400px] mx-auto px-4 py-6">
      <AdminNav active="/admin/inquiries" />

      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-lg font-bold text-gray-900">채용의뢰 관리</h1>
          <p className="text-xs text-gray-500">
            {loading ? '로딩 중…' : `총 ${total}건`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveMsg && <span className="text-xs text-green-600 font-medium">{saveMsg}</span>}
          <button type="button" className="text-sm text-blue-600 hover:underline"
            onClick={fetchData}>↻ 새로고침</button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg">{error}</div>
      )}

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-3 py-2 text-left w-12">ID</th>
              <th className="px-3 py-2 text-left">업체명</th>
              <th className="px-3 py-2 text-left">담당자</th>
              <th className="px-3 py-2 text-left">이메일</th>
              <th className="px-3 py-2 text-left">전화</th>
              <th className="px-3 py-2 text-left">포지션</th>
              <th className="px-3 py-2 text-left">지역</th>
              <th className="px-3 py-2 text-left">내용</th>
              <th className="px-3 py-2 text-left">상태</th>
              <th className="px-3 py-2 text-left">접수일</th>
              <th className="px-3 py-2 text-left w-10"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((inq) => (
              <TableRow
                key={inq.id}
                inq={inq}
                expanded={expanded === inq.id}
                onToggle={() => setExpanded(expanded === inq.id ? null : inq.id)}
                onUpdate={handleUpdate}
              />
            ))}
            {!loading && rows.length === 0 && (
              <tr><td colSpan={11} className="px-4 py-8 text-center text-gray-400">채용의뢰 없음</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function TableRow({ inq, expanded, onToggle, onUpdate }: {
  inq: Inquiry
  expanded: boolean
  onToggle: () => void
  onUpdate: (id: number, field: string, value: string) => void
}) {
  const statusColor: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-700',
    processing: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
  }

  return (
    <>
      <tr className="hover:bg-gray-50 cursor-pointer" onClick={onToggle}>
        <td className="px-3 py-2 text-gray-400">{inq.id}</td>
        <td className="px-3 py-2 font-medium text-gray-900">{inq.school_name ?? '—'}</td>
        <td className="px-3 py-2">{inq.contact_name ?? '—'}</td>
        <td className="px-3 py-2 text-xs text-gray-500">{inq.email ?? '—'}</td>
        <td className="px-3 py-2 text-xs">{inq.phone ?? '—'}</td>
        <td className="px-3 py-2 text-xs">{inq.vacancies ?? '—'}</td>
        <td className="px-3 py-2">{inq.location ?? '—'}</td>
        <td className="px-3 py-2 text-xs text-gray-500 max-w-[160px] truncate">{inq.memo ?? '—'}</td>
        <td className="px-3 py-2">
          <select
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColor[inq.inbox_status ?? ''] ?? 'bg-gray-100 text-gray-600'}`}
            value={inq.inbox_status ?? 'pending'}
            onClick={(e) => e.stopPropagation()}
            onChange={(e) => onUpdate(inq.id, 'inbox_status', e.target.value)}
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </td>
        <td className="px-3 py-2 text-xs text-gray-500">
          {inq.submitted_at ? new Date(inq.submitted_at).toLocaleDateString('ko-KR') : '—'}
        </td>
        <td className="px-3 py-2 text-gray-400">{expanded ? '▲' : '▼'}</td>
      </tr>

      {expanded && (
        <tr>
          <td colSpan={11} className="px-4 py-4 bg-gray-50">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs mb-4">
              <InfoItem label="시작일" value={inq.start_date} />
              <InfoItem label="교육대상" value={inq.teaching_age} />
              <InfoItem label="급여" value={inq.salary_raw} />
              <InfoItem label="근무시간" value={inq.working_hours} />
              <InfoItem label="숙소" value={`${inq.housing_type ?? ''} ${inq.housing_detail ?? ''}`} />
              <InfoItem label="복리후생" value={inq.benefits} />
              <InfoItem label="경로" value={inq.source} />
              <InfoItem label="담당자" value={inq.assigned_to} />
            </div>
            {inq.memo && (
              <div className="mb-3 text-xs">
                <span className="font-medium text-gray-600">메모:</span>
                <p className="text-gray-700 mt-1 whitespace-pre-wrap">{inq.memo}</p>
              </div>
            )}
            <div className="flex items-start gap-3">
              <div className="flex-1">
                <label className="text-xs font-medium text-gray-500 mb-1 block">관리자 메모</label>
                <textarea
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs resize-none"
                  rows={2}
                  defaultValue={inq.notes ?? ''}
                  onBlur={(e) => {
                    if (e.target.value !== (inq.notes ?? '')) {
                      onUpdate(inq.id, 'notes', e.target.value)
                    }
                  }}
                />
              </div>
              <div className="w-40">
                <label className="text-xs font-medium text-gray-500 mb-1 block">담당자 배정</label>
                <select
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs"
                  defaultValue={inq.assigned_to ?? ''}
                  onChange={(e) => {
                    if (e.target.value !== (inq.assigned_to ?? '')) {
                      onUpdate(inq.id, 'assigned_to', e.target.value)
                    }
                  }}
                >
                  <option value="">— 선택 —</option>
                  {STAFF_NAMES.map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

function InfoItem({ label, value }: { label: string; value: string | null | undefined }) {
  const display = value?.trim() || '—'
  return (
    <div>
      <span className="font-medium text-gray-500">{label}</span>
      <p className="text-gray-800 mt-0.5">{display}</p>
    </div>
  )
}
