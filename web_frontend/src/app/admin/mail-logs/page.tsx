'use client'

/**
 * /admin/mail-logs - 메일 수발신 관리
 * 발송 로그 조회 + 상태 확인
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import { MailCheck, Search, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'

const API = API_URL

interface MailLog {
  id: number
  sender: string | null
  recipient: string
  subject: string
  status: 'sent' | 'failed' | 'pending' | 'bounced'
  sent_at: string | null
  error_msg: string | null
  template_key: string | null
  created_at: string
}

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  sent:    { bg: 'bg-green-50',  text: 'text-green-700',  label: '발송완료' },
  failed:  { bg: 'bg-red-50',    text: 'text-red-700',    label: '실패' },
  pending: { bg: 'bg-yellow-50', text: 'text-yellow-700', label: '대기' },
  bounced: { bg: 'bg-orange-50', text: 'text-orange-700', label: '반송' },
}

const PER_PAGE = 50

function fmtDate(iso: string | null): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function MailLogsPage() {
  const { adminKey, authed, login, waking } = useAdminAuth()

  const [logs, setLogs] = useState<MailLog[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [searchQ, setSearchQ] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const fetchLogs = useCallback(async (q = searchQ, status = statusFilter, pg = page) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({
        limit: String(PER_PAGE),
        offset: String((pg - 1) * PER_PAGE),
      })
      if (q) params.set('q', q)
      if (status !== 'all') params.set('status', status)

      const res = await fetch(`${API}/api/admin/mail-logs?${params}`, {
        headers: { 'x-admin-key': adminKey },
      })
      const json = await res.json()
      if (!res.ok) {
        throw new Error(json.detail || json.message || `Error ${res.status}`)
      }
      setLogs(json.data?.logs || json.data || [])
      setTotal(json.data?.total ?? (json.data?.logs || json.data || []).length)
    } catch (e) {
      setError(e instanceof Error ? e.message : '데이터 로드 실패')
    } finally {
      setLoading(false)
    }
  }, [adminKey, searchQ, statusFilter, page])

  useEffect(() => {
    if (authed) fetchLogs()
  }, [authed, fetchLogs])

  const handleSearch = (val: string) => {
    setSearchQ(val)
    setPage(1)
    fetchLogs(val, statusFilter, 1)
  }

  const handleStatusFilter = (val: string) => {
    setStatusFilter(val)
    setPage(1)
    fetchLogs(searchQ, val, 1)
  }

  const handlePageChange = (pg: number) => {
    setPage(pg)
    setExpandedId(null)
    fetchLogs(searchQ, statusFilter, pg)
  }

  const totalPages = Math.ceil(total / PER_PAGE)

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  // Stats
  const sentCount = logs.filter(l => l.status === 'sent').length
  const failedCount = logs.filter(l => l.status === 'failed').length

  return (
    <div className="max-w-[1200px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[22px] font-bold text-[#1d1d1f] tracking-tight flex items-center gap-2">
            <MailCheck size={22} className="text-blue-600" />
            메일 수발신 관리
          </h1>
          <p className="text-[13px] text-[#86868b] mt-0.5">
            {loading ? '로딩 중...' : `총 ${total.toLocaleString()}건`}
          </p>
        </div>
        <button
          type="button"
          onClick={() => fetchLogs()}
          className="flex items-center gap-1.5 px-4 py-2 text-[13px] text-blue-600 hover:bg-blue-50 rounded-xl transition-colors font-medium"
        >
          <RefreshCw size={14} />
          새로고침
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: '전체', value: total, color: 'text-[#1d1d1f]', bg: 'bg-white' },
          { label: '발송완료', value: sentCount, color: 'text-green-600', bg: 'bg-green-50/50' },
          { label: '실패', value: failedCount, color: 'text-red-600', bg: 'bg-red-50/50' },
          { label: '이 페이지', value: logs.length, color: 'text-blue-600', bg: 'bg-blue-50/50' },
        ].map(s => (
          <div key={s.label} className={`${s.bg} rounded-2xl border border-[#e5e5e7] p-4 text-center`}>
            <div className={`text-[28px] font-bold ${s.color}`}>{s.value}</div>
            <div className="text-[12px] text-[#86868b] mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4 flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <div className="relative flex-1 w-full sm:w-auto">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#86868b]" />
          <input
            type="text"
            value={searchQ}
            onChange={e => handleSearch(e.target.value)}
            placeholder="수신자, 제목 검색..."
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-[#d2d2d7] text-[13px] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {['all', 'sent', 'failed', 'pending', 'bounced'].map(s => (
            <button
              key={s}
              type="button"
              onClick={() => handleStatusFilter(s)}
              className={`px-3.5 py-2 rounded-xl text-[12px] font-medium transition-colors ${
                statusFilter === s
                  ? 'bg-[#1d1d1f] text-white'
                  : 'bg-[#f5f5f7] text-[#424245] hover:bg-[#e8e8ed]'
              }`}
            >
              {s === 'all' ? '전체' : STATUS_STYLES[s]?.label ?? s}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-[13px] text-red-700">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="bg-white border border-[#e5e5e7] rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead className="bg-[#f5f5f7] text-[11px] text-[#86868b] uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 text-left w-12">ID</th>
                <th className="px-4 py-3 text-left">수신자</th>
                <th className="px-4 py-3 text-left">제목</th>
                <th className="px-4 py-3 text-left w-24">상태</th>
                <th className="px-4 py-3 text-left w-36">발송일시</th>
                <th className="px-4 py-3 text-left w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f0f2]">
              {logs.map(log => {
                const st = STATUS_STYLES[log.status] ?? STATUS_STYLES.pending
                const expanded = expandedId === log.id
                return (
                  <tr key={log.id} className="group">
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => setExpandedId(expanded ? null : log.id)}
                        className="text-[#86868b] hover:text-[#1d1d1f] font-mono text-[11px]"
                      >
                        {log.id}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-[#1d1d1f] font-medium max-w-[200px] truncate">
                      {log.recipient}
                    </td>
                    <td className="px-4 py-3 text-[#424245] max-w-[250px] truncate">
                      {log.subject}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center text-[11px] font-semibold px-2.5 py-1 rounded-full ${st.bg} ${st.text}`}>
                        {st.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[12px] text-[#86868b]">
                      {fmtDate(log.sent_at || log.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => setExpandedId(expanded ? null : log.id)}
                        className="text-[#86868b] hover:text-[#1d1d1f]"
                      >
                        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                    </td>
                  </tr>
                )
              })}
              {!loading && logs.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-16 text-center text-[#86868b]">
                    {searchQ ? `"${searchQ}" 검색 결과 없음` : '메일 로그가 없습니다'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Expanded Detail */}
        {expandedId && (() => {
          const log = logs.find(l => l.id === expandedId)
          if (!log) return null
          return (
            <div className="px-6 py-4 bg-[#fafafa] border-t border-[#e5e5e7]">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-[12px]">
                <div>
                  <span className="text-[#86868b] block mb-0.5">발신자</span>
                  <span className="text-[#1d1d1f] font-medium">{log.sender || '-'}</span>
                </div>
                <div>
                  <span className="text-[#86868b] block mb-0.5">수신자</span>
                  <span className="text-[#1d1d1f] font-medium">{log.recipient}</span>
                </div>
                <div>
                  <span className="text-[#86868b] block mb-0.5">템플릿</span>
                  <span className="text-[#1d1d1f] font-medium">{log.template_key || '-'}</span>
                </div>
                <div>
                  <span className="text-[#86868b] block mb-0.5">생성일</span>
                  <span className="text-[#1d1d1f] font-medium">{fmtDate(log.created_at)}</span>
                </div>
              </div>
              {log.error_msg && (
                <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl text-[12px] text-red-700">
                  <span className="font-semibold">오류:</span> {log.error_msg}
                </div>
              )}
            </div>
          )
        })()}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-[12px] text-[#86868b]">
            {((page - 1) * PER_PAGE + 1).toLocaleString()} - {Math.min(page * PER_PAGE, total).toLocaleString()} / {total.toLocaleString()}건
          </p>
          <div className="flex items-center gap-1">
            <button
              type="button"
              className="px-3 py-1.5 text-[12px] border border-[#d2d2d7] rounded-lg hover:bg-[#f5f5f7] disabled:opacity-40"
              disabled={page <= 1}
              onClick={() => handlePageChange(page - 1)}
            >
              이전
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              let pageNum: number
              if (totalPages <= 7) {
                pageNum = i + 1
              } else if (page <= 4) {
                pageNum = i + 1
              } else if (page >= totalPages - 3) {
                pageNum = totalPages - 6 + i
              } else {
                pageNum = page - 3 + i
              }
              return (
                <button
                  key={pageNum}
                  type="button"
                  className={`px-3 py-1.5 text-[12px] rounded-lg transition-colors ${
                    pageNum === page
                      ? 'bg-[#1d1d1f] text-white'
                      : 'border border-[#d2d2d7] hover:bg-[#f5f5f7]'
                  }`}
                  onClick={() => handlePageChange(pageNum)}
                >
                  {pageNum}
                </button>
              )
            })}
            <button
              type="button"
              className="px-3 py-1.5 text-[12px] border border-[#d2d2d7] rounded-lg hover:bg-[#f5f5f7] disabled:opacity-40"
              disabled={page >= totalPages}
              onClick={() => handlePageChange(page + 1)}
            >
              다음
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
