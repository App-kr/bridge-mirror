'use client'

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL

interface Inquiry {
  id: number
  school_name: string | null
  email: string | null
  phone: string | null
  location: string | null
  contact_name: string | null
  raw_email_body: string | null
  memo: string | null
  inbox_status: string
  submitted_at: string | null
  start_date: string | null
  vacancies: string | null
  teaching_age: string | null
  salary_raw: string | null
  source: string | null
  is_new?: number
}

const STATUS_OPTIONS = ['open', 'contacted', 'hired', 'hold', 'closed', 'blacklist']

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-sky-800 text-white',
  contacted: 'bg-yellow-600 text-white',
  hired: 'bg-green-700 text-white',
  hold: 'bg-gray-600 text-white',
  closed: 'bg-gray-500 text-white',
  blacklist: 'bg-red-700 text-white',
}

function Toast({ msg, onClose }: { msg: string; onClose: () => void }) {
  useEffect(() => {
    const t = setTimeout(onClose, 2500)
    return () => clearTimeout(t)
  }, [onClose])
  return (
    <div className="fixed bottom-6 right-6 z-[9999] bg-gray-900 text-white text-[13px] px-4 py-2.5 rounded-xl shadow-2xl flex items-center gap-2">
      <span>✓</span>
      <span>{msg}</span>
    </div>
  )
}

interface InquiryCardProps {
  inq: Inquiry
  apiBase: string
  authHeaders: () => Record<string, string>
  onUpdated: (id: number, patch: Partial<Inquiry>) => void
  onNewConfirmed: (id: number) => void
}

function InquiryCard({ inq, apiBase, authHeaders, onUpdated, onNewConfirmed }: InquiryCardProps) {
  const [memo, setMemo] = useState(inq.memo ?? '')
  const [bodyText, setBodyText] = useState(inq.raw_email_body ?? '')
  const [bodyEdit, setBodyEdit] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [isNew, setIsNew] = useState(!!inq.is_new)

  const [infoRegion, setInfoRegion] = useState(inq.location ?? '')
  const [infoCompany, setInfoCompany] = useState(inq.school_name ?? '')
  const [infoEmail, setInfoEmail] = useState(inq.email ?? '')
  const [infoPhone, setInfoPhone] = useState(inq.phone ?? '')
  const [infoContact, setInfoContact] = useState(inq.contact_name ?? '')

  const showToast = (msg: string) => setToast(msg)

  const patch = useCallback(async (payload: Record<string, string>) => {
    const res = await fetch(`${apiBase}/api/admin/inquiries/${inq.id}`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error('저장 실패')
    return res.json()
  }, [apiBase, inq.id, authHeaders])

  const saveMemo = useCallback(async () => {
    try {
      await patch({ memo })
      onUpdated(inq.id, { memo })
      showToast('메모 저장 완료')
    } catch {
      showToast('메모 저장 실패')
    }
  }, [patch, memo, inq.id, onUpdated])

  const saveInfo = useCallback(async () => {
    try {
      await patch({
        location: infoRegion,
        school_name: infoCompany,
        email: infoEmail,
        phone: infoPhone,
      })
      onUpdated(inq.id, {
        location: infoRegion,
        school_name: infoCompany,
        email: infoEmail,
        phone: infoPhone,
      })
      showToast('정보 저장 완료')
    } catch {
      showToast('정보 저장 실패')
    }
  }, [patch, infoRegion, infoCompany, infoEmail, infoPhone, inq.id, onUpdated])

  const saveBody = useCallback(async () => {
    try {
      await patch({ raw_email_body: bodyText })
      onUpdated(inq.id, { raw_email_body: bodyText })
      setBodyEdit(false)
      showToast('본문 저장 완료')
    } catch {
      showToast('본문 저장 실패')
    }
  }, [patch, bodyText, inq.id, onUpdated])

  const changeStatus = useCallback(async (status: string) => {
    try {
      await patch({ inbox_status: status })
      onUpdated(inq.id, { inbox_status: status })
      showToast(`상태: ${status}`)
    } catch {
      showToast('상태 변경 실패')
    }
  }, [patch, inq.id, onUpdated])

  const confirmNew = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/admin/inquiries/${inq.id}/confirm-new`, {
        method: 'PATCH',
        headers: authHeaders(),
      })
      if (!res.ok) throw new Error('확인 실패')
      setIsNew(false)
      onNewConfirmed(inq.id)
      showToast('NEW 확인 완료')
    } catch {
      showToast('NEW 확인 실패')
    }
  }, [apiBase, inq.id, authHeaders, onNewConfirmed])

  const currentStatus = inq.inbox_status

  return (
    <div className="rounded-xl overflow-hidden shadow-sm border border-amber-200">
      {toast && <Toast msg={toast} onClose={() => setToast(null)} />}

      {/* 노란 박스 — MEMO + 정보 */}
      <div className="bg-amber-50 p-4 space-y-3">
        {/* MEMO 섹션 */}
        <div>
          <div className="flex items-center gap-2">
            <label className="text-[11px] font-bold text-amber-700 uppercase tracking-wider">MEMO</label>
            {isNew && (
              <span
                className="text-[10px] font-bold text-white bg-red-500 rounded px-1.5 py-0.5 leading-none"
                style={{ animation: 'blink-badge 1s step-end infinite' }}
              >
                NEW
              </span>
            )}
          </div>
          <textarea
            value={memo}
            onChange={e => setMemo(e.target.value)}
            rows={3}
            placeholder="메모를 입력하세요..."
            className="w-full mt-1 px-3 py-2 text-[13px] bg-white border border-amber-200 rounded-lg resize-y focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
          <div className="flex items-center gap-2 mt-1">
            <button
              type="button"
              onClick={saveMemo}
              className="text-[12px] px-3 py-1.5 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors"
            >
              저장
            </button>
            {isNew && (
              <button
                type="button"
                onClick={confirmNew}
                className="text-[12px] px-3 py-1.5 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
              >
                NEW 확인
              </button>
            )}
          </div>
        </div>

        {/* 구분선 */}
        <div className="border-t-2 border-amber-300" />

        {/* 정보 섹션 */}
        <div>
          <label className="text-[11px] font-bold text-amber-700 uppercase tracking-wider">정보</label>
          <div className="grid grid-cols-2 gap-2 mt-2">
            <div>
              <label className="text-[10px] text-amber-600 font-semibold">지역</label>
              <input
                type="text"
                value={infoRegion}
                onChange={e => setInfoRegion(e.target.value)}
                placeholder="지역"
                className="w-full mt-0.5 px-2 py-1.5 text-[12px] bg-white border border-amber-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400"
              />
            </div>
            <div>
              <label className="text-[10px] text-amber-600 font-semibold">업체명</label>
              <input
                type="text"
                value={infoCompany}
                onChange={e => setInfoCompany(e.target.value)}
                placeholder="업체명"
                className="w-full mt-0.5 px-2 py-1.5 text-[12px] bg-white border border-amber-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400"
              />
            </div>
            <div>
              <label className="text-[10px] text-amber-600 font-semibold">이메일</label>
              <input
                type="text"
                value={infoEmail}
                onChange={e => setInfoEmail(e.target.value)}
                placeholder="이메일"
                className="w-full mt-0.5 px-2 py-1.5 text-[12px] bg-white border border-amber-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400"
              />
            </div>
            <div>
              <label className="text-[10px] text-amber-600 font-semibold">전화</label>
              <input
                type="text"
                value={infoPhone}
                onChange={e => setInfoPhone(e.target.value)}
                placeholder="전화번호"
                className="w-full mt-0.5 px-2 py-1.5 text-[12px] bg-white border border-amber-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400"
              />
            </div>
            <div className="col-span-2">
              <label className="text-[10px] text-amber-600 font-semibold">담당자</label>
              <input
                type="text"
                value={infoContact}
                onChange={e => setInfoContact(e.target.value)}
                placeholder="담당자명"
                className="w-full mt-0.5 px-2 py-1.5 text-[12px] bg-white border border-amber-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400"
              />
            </div>
          </div>
          <button
            type="button"
            onClick={saveInfo}
            className="mt-2 text-[12px] px-3 py-1.5 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors"
          >
            정보 저장
          </button>
        </div>
      </div>

      {/* 본문 영역 */}
      <div className="bg-white border-t border-amber-200 p-4">
        {/* 헤더: inq_번호 · 지역 · 업체명 */}
        <div className="flex items-center gap-2 mb-2 text-[12px] text-gray-500 flex-wrap">
          <span className="font-mono font-bold text-gray-700">#{inq.id}</span>
          {inq.location && (
            <>
              <span className="text-gray-300">·</span>
              <span>{inq.location}</span>
            </>
          )}
          {inq.school_name && (
            <>
              <span className="text-gray-300">·</span>
              <span className="font-medium text-gray-700">{inq.school_name}</span>
            </>
          )}
          {inq.submitted_at && (
            <>
              <span className="text-gray-300">·</span>
              <span className="text-gray-400">{inq.submitted_at.slice(0, 10)}</span>
            </>
          )}
        </div>
        <hr className="border-gray-100 mb-3" />

        {/* 본문 텍스트 or textarea */}
        {bodyEdit ? (
          <div>
            <textarea
              value={bodyText}
              onChange={e => setBodyText(e.target.value)}
              rows={10}
              className="w-full px-3 py-2 text-[13px] font-mono border border-gray-200 rounded-lg resize-y focus:outline-none focus:ring-2 focus:ring-blue-400"
              style={{ whiteSpace: 'pre-wrap' }}
            />
            <div className="flex gap-2 mt-2">
              <button
                type="button"
                onClick={saveBody}
                className="text-[12px] px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                저장
              </button>
              <button
                type="button"
                onClick={() => { setBodyText(inq.raw_email_body ?? ''); setBodyEdit(false) }}
                className="text-[12px] px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
              >
                취소
              </button>
            </div>
          </div>
        ) : (
          <div>
            {bodyText ? (
              <pre className="text-[13px] text-gray-800 whitespace-pre-wrap leading-relaxed font-sans">{bodyText}</pre>
            ) : (
              <p className="text-[13px] text-gray-400 italic">본문 없음</p>
            )}
            <button
              type="button"
              onClick={() => setBodyEdit(true)}
              className="mt-2 text-[12px] text-orange-500 hover:text-orange-700 transition-colors"
            >
              수정
            </button>
          </div>
        )}

        {/* 상태 태그 */}
        <div className="flex gap-1.5 mt-3 flex-wrap">
          {STATUS_OPTIONS.map(s => (
            <button
              key={s}
              type="button"
              onClick={() => changeStatus(s)}
              className={`px-2.5 py-1 rounded-full text-[11px] font-semibold transition-colors ${
                currentStatus === s
                  ? (STATUS_COLORS[s] ?? 'bg-gray-800 text-white')
                  : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function AdminEmployerContent() {
  const { authed, headers } = useAdminAuth()
  const [inquiries, setInquiries] = useState<Inquiry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const LIMIT = 20

  const fetchInquiries = useCallback(async (pg: number, q: string, st: string) => {
    if (!authed) return
    setLoading(true)
    setError(null)
    try {
      const offset = pg * LIMIT
      const params = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) })
      if (q) params.set('q', q)
      const res = await fetch(`${API}/api/admin/inquiries?${params}`, { headers: headers() })
      if (!res.ok) {
        if (res.status === 403) { setError('인증 오류. 다시 로그인해주세요.'); return }
        throw new Error('데이터 로딩 실패')
      }
      const json = await res.json()
      if (!json.success) throw new Error(json.message ?? 'Error')
      let rows: Inquiry[] = json.data?.inquiries ?? []
      if (st) rows = rows.filter((r: Inquiry) => r.inbox_status === st)
      setInquiries(rows)
      setTotal(json.data?.total ?? rows.length)
    } catch (e) {
      setError(e instanceof Error ? e.message : '불러오기 실패')
    } finally {
      setLoading(false)
    }
  }, [authed, headers])

  useEffect(() => {
    fetchInquiries(page, search, filterStatus)
  }, [fetchInquiries, page, search, filterStatus])

  const handleUpdated = useCallback((id: number, patch: Partial<Inquiry>) => {
    setInquiries(prev => prev.map(inq => inq.id === id ? { ...inq, ...patch } : inq))
  }, [])

  const handleNewConfirmed = useCallback((id: number) => {
    setInquiries(prev => prev.map(inq => inq.id === id ? { ...inq, is_new: 0 } : inq))
  }, [])

  const confirmAllNew = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/admin/inquiries/confirm-all-new`, {
        method: 'PATCH',
        headers: headers(),
      })
      if (!res.ok) throw new Error('일괄 확인 실패')
      setInquiries(prev => prev.map(inq => ({ ...inq, is_new: 0 })))
    } catch (e) {
      setError(e instanceof Error ? e.message : '일괄 확인 실패')
    }
  }, [headers])

  const handleSearch = () => {
    setPage(0)
    setSearch(searchInput)
  }

  const totalPages = Math.ceil(total / LIMIT)

  return (
    <div className="space-y-5">
      <style>{`
        @keyframes blink-badge {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
      {/* 헤더 */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-[22px] font-bold text-[#1d1d1f] tracking-tight">구인자관리</h1>
          <p className="text-[13px] text-[#86868b] mt-0.5">
            {loading ? '로딩 중...' : `${total}건 전체 / 현재 ${inquiries.length}건`}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {/* 검색 */}
          <input
            type="text"
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleSearch() }}
            placeholder="업체명, 이메일, 메모 검색..."
            className="px-3 py-1.5 text-[13px] border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 w-48"
          />
          <button
            type="button"
            onClick={handleSearch}
            className="px-4 py-1.5 text-[13px] bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            검색
          </button>
          {search && (
            <button
              type="button"
              onClick={() => { setSearchInput(''); setSearch(''); setPage(0) }}
              className="text-[12px] text-red-500 hover:text-red-700"
            >
              초기화
            </button>
          )}
          {/* 상태 필터 */}
          <select
            value={filterStatus}
            onChange={e => { setFilterStatus(e.target.value); setPage(0) }}
            className="px-3 py-1.5 text-[13px] border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="">전체 상태</option>
            {STATUS_OPTIONS.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
            <option value="new">new</option>
          </select>
          <button
            type="button"
            onClick={() => fetchInquiries(page, search, filterStatus)}
            className="text-[12px] text-[#0071e3] hover:underline font-medium"
          >
            새로고침
          </button>
          {inquiries.some(inq => inq.is_new) && (
            <button
              type="button"
              onClick={confirmAllNew}
              className="text-[12px] px-3 py-1.5 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors font-medium"
            >
              전체 NEW 확인
            </button>
          )}
        </div>
      </div>

      {/* 에러 */}
      {error && <div className="p-4 bg-red-50 text-red-600 text-[13px] rounded-2xl">{error}</div>}

      {/* 로딩 */}
      {loading && <div className="text-center py-16 text-[#86868b] animate-pulse text-[14px]">로딩 중...</div>}

      {/* 카드 목록 */}
      {!loading && !error && (
        <>
          {inquiries.length === 0 && (
            <div className="text-center py-16 text-[#86868b] text-[14px]">데이터가 없습니다.</div>
          )}
          <div className="space-y-4">
            {inquiries.map(inq => (
              <InquiryCard
                key={inq.id}
                inq={inq}
                apiBase={API}
                authHeaders={headers}
                onUpdated={handleUpdated}
                onNewConfirmed={handleNewConfirmed}
              />
            ))}
          </div>

          {/* 페이지네이션 */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <button
                type="button"
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1.5 text-[13px] bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                이전
              </button>
              <span className="text-[13px] text-gray-500">
                {page + 1} / {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="px-3 py-1.5 text-[13px] bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                다음
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default function AdminEmployerPage() {
  const { authed, login, waking } = useAdminAuth()

  if (!authed) {
    return <AdminAuth onLogin={login} waking={waking} />
  }

  return <AdminEmployerContent />
}
