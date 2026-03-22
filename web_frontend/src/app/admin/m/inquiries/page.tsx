'use client'

import { useCallback, useEffect, useState, useRef } from 'react'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import AdminAuth from '@/components/admin/AdminAuth'
import PullToRefresh from '../components/PullToRefresh'
import InquiryCard from '../components/InquiryCard'
import { Search, Phone, Mail, ChevronLeft, X } from 'lucide-react'
import Link from 'next/link'

const API = API_URL
const PAGE_SIZE = 30

interface Inquiry {
  id: number
  school_name: string | null
  contact_name: string | null
  location: string | null
  email: string | null
  phone: string | null
  inbox_status: string | null
  submitted_at: string | null
  memo: string | null
  vacancies: string | null
  teaching_age: string | null
  salary_raw: string | null
  housing_type: string | null
  benefits: string | null
  working_hours: string | null
  schedule: string | null
  start_date: string | null
  notes: string | null
  assigned_to: string | null
}

const STATUS_TABS = [
  { key: 'all', label: '전체' },
  { key: 'new', label: '신규' },
  { key: 'pending', label: '대기' },
  { key: 'processing', label: '처리중' },
  { key: 'completed', label: '완료' },
]

function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl border border-[#e5e5e7] px-4 py-3 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="h-4 w-32 bg-[#f5f5f7] rounded" />
        <div className="h-5 w-12 bg-[#f5f5f7] rounded-full" />
      </div>
      <div className="h-3 w-24 bg-[#f5f5f7] rounded mt-2" />
      <div className="h-3 w-16 bg-[#f5f5f7] rounded mt-2" />
    </div>
  )
}

export default function InquiriesPage() {
  const { authed, waking, login, adminFetch, signedFetch } = useAdminAuth()
  const [inquiries, setInquiries] = useState<Inquiry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [offset, setOffset] = useState(0)
  const notesTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetchInquiries = useCallback(async (reset = true) => {
    if (reset) {
      setLoading(true)
      setOffset(0)
    } else {
      setLoadingMore(true)
    }

    try {
      const currentOffset = reset ? 0 : offset
      let url = `${API}/api/admin/inquiries?limit=${PAGE_SIZE}&offset=${currentOffset}`
      if (search.trim()) url += `&q=${encodeURIComponent(search.trim())}`

      const res = await adminFetch(url)
      const json = await res.json()

      if (json.success) {
        const list: Inquiry[] = json.data?.inquiries ?? []
        setTotal(json.data?.total ?? 0)
        if (reset) {
          setInquiries(list)
          setOffset(PAGE_SIZE)
        } else {
          setInquiries(prev => [...prev, ...list])
          setOffset(prev => prev + PAGE_SIZE)
        }
      }
    } catch {
      // silently fail, user can pull to refresh
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [adminFetch, search, offset])

  useEffect(() => {
    if (authed) fetchInquiries(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed, statusFilter])

  const handleSearch = useCallback(() => {
    fetchInquiries(true)
  }, [fetchInquiries])

  const handleStatusChange = useCallback(async (id: number, status: string) => {
    try {
      await signedFetch(`${API}/api/admin/inquiries/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ inbox_status: status }),
      })
      setInquiries(prev =>
        prev.map(inq => inq.id === id ? { ...inq, inbox_status: status } : inq)
      )
    } catch {
      // silent fail
    }
  }, [signedFetch])

  const handleNotesChange = useCallback((id: number, notes: string) => {
    setInquiries(prev =>
      prev.map(inq => inq.id === id ? { ...inq, notes } : inq)
    )
    if (notesTimerRef.current) clearTimeout(notesTimerRef.current)
    notesTimerRef.current = setTimeout(async () => {
      try {
        await signedFetch(`${API}/api/admin/inquiries/${id}`, {
          method: 'PUT',
          body: JSON.stringify({ notes }),
        })
      } catch {
        // silent
      }
    }, 1000)
  }, [signedFetch])

  const filteredInquiries = statusFilter === 'all'
    ? inquiries
    : inquiries.filter(inq => (inq.inbox_status || 'new') === statusFilter)

  const hasMore = inquiries.length < total

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <PullToRefresh onRefresh={() => fetchInquiries(true)}>
        <div className="px-4 pb-8 pt-safe">

          {/* Header */}
          <div className="flex items-center gap-3 pt-4 pb-3">
            <Link
              href="/admin/m"
              className="w-9 h-9 flex items-center justify-center rounded-full bg-white border border-[#e5e5e7] shrink-0"
            >
              <ChevronLeft size={18} className="text-[#1d1d1f]" />
            </Link>
            <div className="flex-1">
              <h1 className="text-xl font-bold text-[#1d1d1f]">문의 관리</h1>
              <p className="text-xs text-[#86868b]">{total}건</p>
            </div>
          </div>

          {/* Search bar */}
          <div className="relative mb-3">
            <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#86868b]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSearch() }}
              placeholder="학원명, 지역, 담당자 검색..."
              className="w-full pl-10 pr-10 py-2.5 rounded-full bg-white border border-[#e5e5e7] text-sm text-[#1d1d1f] placeholder:text-[#aeaeb2] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 min-h-[44px]"
            />
            {search && (
              <button
                type="button"
                onClick={() => { setSearch(''); setTimeout(() => fetchInquiries(true), 0) }}
                className="absolute right-3.5 top-1/2 -translate-y-1/2"
              >
                <X size={16} className="text-[#aeaeb2]" />
              </button>
            )}
          </div>

          {/* Status filter tabs */}
          <div className="flex gap-2 overflow-x-auto pb-3 -mx-4 px-4 scrollbar-hide">
            {STATUS_TABS.map(tab => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setStatusFilter(tab.key)}
                className={`shrink-0 px-3.5 py-1.5 rounded-full text-sm font-medium min-h-[36px] transition-colors ${
                  statusFilter === tab.key
                    ? 'bg-[#1d1d1f] text-white'
                    : 'bg-white border border-[#e5e5e7] text-[#86868b]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Inquiry list */}
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map(i => <SkeletonCard key={i} />)}
            </div>
          ) : filteredInquiries.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-[#86868b] text-sm">문의 내역이 없습니다</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredInquiries.map(inq => (
                <div key={inq.id}>
                  <InquiryCard
                    inquiry={inq}
                    onTap={(id) => setExpandedId(expandedId === id ? null : id)}
                    onStatusChange={handleStatusChange}
                  />

                  {/* Expanded detail */}
                  {expandedId === inq.id && (
                    <div className="bg-white rounded-2xl border border-[#e5e5e7] mt-1 px-4 py-4 space-y-4 animate-in slide-in-from-top-2 duration-200">
                      {/* Contact info */}
                      <div className="space-y-2">
                        <h3 className="text-xs font-semibold text-[#86868b] uppercase tracking-wider">연락처</h3>
                        <div className="grid grid-cols-2 gap-2">
                          {inq.contact_name && (
                            <div className="text-sm text-[#1d1d1f]">
                              <span className="text-[#86868b]">담당자: </span>{inq.contact_name}
                            </div>
                          )}
                          {inq.email && (
                            <div className="text-sm text-[#1d1d1f] truncate">
                              <span className="text-[#86868b]">이메일: </span>{inq.email}
                            </div>
                          )}
                          {inq.phone && (
                            <div className="text-sm text-[#1d1d1f]">
                              <span className="text-[#86868b]">전화: </span>{inq.phone}
                            </div>
                          )}
                          {inq.location && (
                            <div className="text-sm text-[#1d1d1f]">
                              <span className="text-[#86868b]">지역: </span>{inq.location}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Job details */}
                      <div className="space-y-2">
                        <h3 className="text-xs font-semibold text-[#86868b] uppercase tracking-wider">채용 정보</h3>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          {inq.vacancies && (
                            <div><span className="text-[#86868b]">모집인원: </span>{inq.vacancies}명</div>
                          )}
                          {inq.teaching_age && (
                            <div><span className="text-[#86868b]">대상 연령: </span>{inq.teaching_age}</div>
                          )}
                          {inq.salary_raw && (
                            <div><span className="text-[#86868b]">급여: </span>{inq.salary_raw}</div>
                          )}
                          {inq.housing_type && (
                            <div><span className="text-[#86868b]">숙소: </span>{inq.housing_type}</div>
                          )}
                          {inq.start_date && (
                            <div><span className="text-[#86868b]">시작일: </span>{inq.start_date}</div>
                          )}
                          {inq.working_hours && (
                            <div><span className="text-[#86868b]">근무시간: </span>{inq.working_hours}</div>
                          )}
                        </div>
                        {inq.benefits && (
                          <div className="text-sm">
                            <span className="text-[#86868b]">복리후생: </span>{inq.benefits}
                          </div>
                        )}
                        {inq.schedule && (
                          <div className="text-sm">
                            <span className="text-[#86868b]">스케줄: </span>{inq.schedule}
                          </div>
                        )}
                      </div>

                      {/* Memo */}
                      {inq.memo && (
                        <div className="space-y-1">
                          <h3 className="text-xs font-semibold text-[#86868b] uppercase tracking-wider">메모</h3>
                          <p className="text-sm text-[#1d1d1f] bg-[#f5f5f7] rounded-xl px-3 py-2">{inq.memo}</p>
                        </div>
                      )}

                      {/* Quick actions */}
                      <div className="flex gap-2">
                        {inq.phone && (
                          <a
                            href={`tel:${inq.phone}`}
                            className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-green-50 text-green-700 text-sm font-medium min-h-[44px]"
                          >
                            <Phone size={16} />
                            전화
                          </a>
                        )}
                        {inq.email && (
                          <a
                            href={`mailto:${inq.email}`}
                            className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-blue-50 text-blue-700 text-sm font-medium min-h-[44px]"
                          >
                            <Mail size={16} />
                            이메일
                          </a>
                        )}
                      </div>

                      {/* Status change buttons */}
                      <div className="space-y-1">
                        <h3 className="text-xs font-semibold text-[#86868b] uppercase tracking-wider">상태 변경</h3>
                        <div className="flex gap-2 flex-wrap">
                          {(['new', 'pending', 'processing', 'completed'] as const).map(s => {
                            const labels: Record<string, string> = { new: '신규', pending: '대기', processing: '처리중', completed: '완료' }
                            const isActive = (inq.inbox_status || 'new') === s
                            return (
                              <button
                                key={s}
                                type="button"
                                onClick={() => handleStatusChange(inq.id, s)}
                                className={`px-3 py-1.5 rounded-full text-xs font-medium min-h-[32px] transition-colors ${
                                  isActive
                                    ? 'bg-[#1d1d1f] text-white'
                                    : 'bg-[#f5f5f7] text-[#86868b]'
                                }`}
                              >
                                {labels[s]}
                              </button>
                            )
                          })}
                        </div>
                      </div>

                      {/* Notes textarea */}
                      <div className="space-y-1">
                        <h3 className="text-xs font-semibold text-[#86868b] uppercase tracking-wider">내부 메모</h3>
                        <textarea
                          value={inq.notes || ''}
                          onChange={(e) => handleNotesChange(inq.id, e.target.value)}
                          placeholder="메모를 입력하세요..."
                          rows={3}
                          className="w-full px-3 py-2 rounded-xl bg-[#f5f5f7] border border-[#e5e5e7] text-sm text-[#1d1d1f] placeholder:text-[#aeaeb2] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 resize-none"
                        />
                        <p className="text-[10px] text-[#aeaeb2]">입력 후 자동 저장</p>
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {/* Load more */}
              {hasMore && (
                <button
                  type="button"
                  onClick={() => fetchInquiries(false)}
                  disabled={loadingMore}
                  className="w-full py-3 rounded-2xl bg-white border border-[#e5e5e7] text-sm font-medium text-[#0071e3] min-h-[44px] disabled:opacity-50"
                >
                  {loadingMore ? '불러오는 중...' : '더 보기'}
                </button>
              )}
            </div>
          )}
        </div>
      </PullToRefresh>
    </div>
  )
}
