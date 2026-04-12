'use client'

/**
 * /admin/inbox/[id] — 수신함 상세
 * 지원자/문의 상세 정보 + 상태 변경 + 메모 + 액션
 */

import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'

import { API_URL } from '@/lib/api'
import { STAFF_NAMES } from '@/lib/team'

const API = API_URL

const STATUS_OPTIONS = [
  { key: 'new',       label: '신규',   color: 'bg-green-100 text-green-700' },
  { key: 'reviewed',  label: '검토',   color: 'bg-blue-100 text-blue-700' },
  { key: 'contacted', label: '연락',   color: 'bg-yellow-100 text-yellow-700' },
  { key: 'interview', label: '면접',   color: 'bg-orange-100 text-orange-700' },
  { key: 'hired',     label: '채용',   color: 'bg-emerald-100 text-emerald-700' },
  { key: 'rejected',  label: '거절',   color: 'bg-red-100 text-red-700' },
]

export default function InboxDetailPage() {
  const params = useParams()
  const itemId = params?.id as string
  const { authed, login, headers, waking } = useAdminAuth()

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [detail, setDetail] = useState<Record<string, any> | null>(null)
  const [itemType, setItemType] = useState<'candidate' | 'inquiry'>('candidate')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  // Notes
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)

  // Assign
  const [assignTo, setAssignTo] = useState('')

  const fetchDetail = useCallback(async () => {
    if (!itemId) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/inbox/${itemId}`, { headers: headers() })
      if (res.status === 403) {
        const errBody = await res.json().catch(() => ({}))
        if (errBody.error?.includes?.('Access denied')) {
          setError('일시적으로 차단되었습니다. 자동 재시도 중...')
          const k = sessionStorage.getItem('bridge_admin_key') || ''
          await fetch(`${API}/api/admin/reset-blacklist`, { method: 'POST', headers: { 'x-admin-key': k } }).catch(() => {})
          setTimeout(() => window.location.reload(), 3000)
          return
        }
        setError('관리자 키가 올바르지 않습니다. 다시 로그인해주세요.')
        sessionStorage.removeItem('bridge_admin_key')
        return
      }
      if (res.status === 404) { setError('항목을 찾을 수 없습니다.'); return }
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Error')

      setItemType(json.data?.type || 'candidate')
      setDetail(json.data?.detail || null)
      setNotes((json.data?.detail?.notes as string) || (json.data?.detail?.admin_notes as string) || '')
      setAssignTo((json.data?.detail?.assigned_to as string) || '')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [itemId, headers])

  useEffect(() => {
    if (authed && itemId) fetchDetail()
  }, [authed, itemId, fetchDetail])

  const handleStatusChange = async (newStatus: string) => {
    try {
      const res = await fetch(`${API}/api/admin/inbox/${itemId}/status`, {
        method: 'PATCH', headers: headers(),
        body: JSON.stringify({ status: newStatus }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`상태 변경: ${newStatus}`)
      fetchDetail()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  const handleSaveNotes = async () => {
    setSaving(true)
    try {
      const res = await fetch(`${API}/api/admin/inbox/${itemId}/notes`, {
        method: 'PATCH', headers: headers(),
        body: JSON.stringify({ notes }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg('메모 저장 완료')
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    } finally {
      setSaving(false)
    }
  }

  const handleAssign = async () => {
    try {
      const res = await fetch(`${API}/api/admin/inbox/${itemId}/assign`, {
        method: 'PATCH', headers: headers(),
        body: JSON.stringify({ assigned_to: assignTo }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`담당자 배정: ${assignTo}`)
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  const d = detail || {}
  const email = (d.email as string) || ''
  const currentStatus = (d.inbox_status as string) || (d.status as string) || 'new'

  return (
    <div className="space-y-6">

      {/* Back link */}
      <Link href="/admin/inbox" className="text-sm text-blue-600 hover:underline">← 수신함으로 돌아가기</Link>

      {loading ? (
        <div className="text-center py-32 text-gray-400 animate-pulse">로딩 중...</div>
      ) : error ? (
        <div className="text-center py-32 text-red-500">{error}</div>
      ) : !detail ? (
        <div className="text-center py-32 text-gray-400">데이터 없음</div>
      ) : (
        <>
          {actionMsg && (
            <div className="card-flat bg-blue-50 border-blue-200 text-sm text-blue-700 flex justify-between items-center">
              <span>{actionMsg}</span>
              <button type="button" onClick={() => setActionMsg(null)} className="text-blue-500">×</button>
            </div>
          )}

          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {(d.full_name as string) || (d.contact_name as string) || (d.school_name as string) || 'N/A'}
              </h1>
              <p className="text-gray-500 text-sm mt-1">
                {itemType === 'candidate' ? '교사 지원자' : '구인 문의'}
                {' · '}
                {d.created_at ? new Date(d.created_at as string).toLocaleDateString('ko-KR') : '—'}
              </p>
            </div>
            <span className={`badge text-sm border px-3 py-1 ${
              STATUS_OPTIONS.find(s => s.key === currentStatus)?.color || 'bg-gray-100 text-gray-600'
            } border-gray-200`}>
              {STATUS_OPTIONS.find(s => s.key === currentStatus)?.label || currentStatus}
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Info card */}
            <div className="lg:col-span-2 space-y-6">
              {/* Basic Info */}
              <div className="card">
                <h2 className="font-bold text-gray-900 mb-4">기본 정보</h2>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  {itemType === 'candidate' ? (
                    <>
                      <InfoRow label="이름" value={d.full_name as string} />
                      <InfoRow label="이메일" value={email} />
                      <InfoRow label="국적" value={d.nationality as string} />
                      <InfoRow label="현재 위치" value={d.current_location as string} />
                      <InfoRow label="희망 지역" value={d.area_prefs as string} />
                      <InfoRow label="비자" value={d.e_visa as string} />
                      <InfoRow label="자격" value={d.certification as string} />
                      <InfoRow label="경력" value={d.employment as string} />
                      <InfoRow label="성별" value={d.gender as string} />
                      <InfoRow label="생년월일" value={d.dob as string} />
                      <InfoRow label="소스" value={d.source as string} />
                      <InfoRow label="상태" value={d.status as string} />
                    </>
                  ) : (
                    <>
                      <InfoRow label="학원명" value={d.school_name as string} />
                      <InfoRow label="담당자" value={d.contact_name as string} />
                      <InfoRow label="이메일" value={email} />
                      <InfoRow label="전화" value={d.phone as string} />
                      <InfoRow label="위치" value={d.location as string} />
                      <InfoRow label="모집 인원" value={d.vacancies as string} />
                      <InfoRow label="대상 연령" value={d.teaching_age as string} />
                      <InfoRow label="급여" value={d.salary_raw as string} />
                    </>
                  )}
                </div>
              </div>

              {/* Parsed data / Raw email */}
              {d.parsed_data && (
                <div className="card">
                  <h2 className="font-bold text-gray-900 mb-4">파싱된 데이터</h2>
                  <pre className="bg-gray-50 rounded-lg p-4 text-xs text-gray-600 whitespace-pre-wrap overflow-auto max-h-64 font-mono">
                    {typeof d.parsed_data === 'string'
                      ? d.parsed_data
                      : JSON.stringify(d.parsed_data, null, 2)}
                  </pre>
                </div>
              )}

              {d.raw_email_body && (
                <div className="card">
                  <h2 className="font-bold text-gray-900 mb-4">원본 이메일</h2>
                  <pre className="bg-gray-50 rounded-lg p-4 text-xs text-gray-600 whitespace-pre-wrap overflow-auto max-h-96 font-mono">
                    {d.raw_email_body as string}
                  </pre>
                </div>
              )}
            </div>

            {/* Right: Actions */}
            <div className="space-y-6">
              {/* Status change */}
              <div className="card">
                <h2 className="font-bold text-gray-900 mb-3">상태 변경</h2>
                <div className="grid grid-cols-2 gap-2">
                  {STATUS_OPTIONS.map(s => (
                    <button key={s.key} type="button"
                      onClick={() => handleStatusChange(s.key)}
                      className={`px-3 py-2 rounded-lg text-xs font-medium border transition-colors ${
                        currentStatus === s.key
                          ? `${s.color} border-gray-300 ring-2 ring-blue-400`
                          : `${s.color} border-gray-200 hover:border-gray-400`
                      }`}>
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Assign */}
              <div className="card">
                <h2 className="font-bold text-gray-900 mb-3">담당자 배정</h2>
                <div className="flex gap-2">
                  <select value={assignTo}
                    onChange={e => setAssignTo(e.target.value)}
                    className="flex-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
                    <option value="">— 선택 —</option>
                    {STAFF_NAMES.map((n) => <option key={n} value={n}>{n}</option>)}
                  </select>
                  <button type="button" onClick={handleAssign}
                    className="px-4 py-2 rounded-lg bg-[#1d1d1f] text-white text-sm font-medium hover:bg-[#424245] transition-colors">
                    배정
                  </button>
                </div>
              </div>

              {/* Notes */}
              <div className="card">
                <h2 className="font-bold text-gray-900 mb-3">관리자 메모</h2>
                <textarea value={notes}
                  onChange={e => setNotes(e.target.value)}
                  className="w-full h-32 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-blue-400"
                  placeholder="메모를 입력하세요..." maxLength={5000} />
                <button type="button" onClick={handleSaveNotes} disabled={saving}
                  className="mt-2 w-full px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
                  {saving ? '저장 중...' : '메모 저장'}
                </button>
              </div>

              {/* Quick actions */}
              <div className="card">
                <h2 className="font-bold text-gray-900 mb-3">빠른 액션</h2>
                <div className="space-y-2">
                  {email && (
                    <>
                      <a href={`mailto:${email}?subject=RE: Teaching Position Application`}
                        className="block w-full px-4 py-2 rounded-lg border border-gray-200 text-sm text-center hover:bg-gray-50 transition-colors">
                        📧 답장
                      </a>
                      <a href={`mailto:${email}?subject=Interview Invitation - Bridge Recruitment&body=Dear ${(d.full_name as string) || 'Applicant'},%0D%0A%0D%0AWe are pleased to invite you for an interview.`}
                        className="block w-full px-4 py-2 rounded-lg border border-blue-200 text-sm text-center text-blue-700 hover:bg-blue-50 transition-colors">
                        🎥 면접 초대
                      </a>
                      <a href={`mailto:${email}?subject=Application Update - Bridge Recruitment&body=Dear ${(d.full_name as string) || 'Applicant'},%0D%0A%0D%0AThank you for your interest. Unfortunately, we are unable to proceed with your application at this time.`}
                        className="block w-full px-4 py-2 rounded-lg border border-red-200 text-sm text-center text-red-600 hover:bg-red-50 transition-colors">
                        ❌ 거절 메일
                      </a>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <span className="text-gray-400 text-xs">{label}</span>
      <p className="text-gray-900 mt-0.5">{value || '—'}</p>
    </div>
  )
}
