'use client'

/**
 * /admin/mail-logs - 메일 수발신 관리
 * 백엔드 mail_logs 테이블: 배치 작업 로그 (manual_send, profile_broadcast 등)
 */

import { useCallback, useEffect, useState } from 'react'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import { MailCheck, Search, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'

const API = API_URL

interface MailLog {
  id: number
  log_type: string
  candidate_id: string | null
  employer_count: number
  sent_count: number
  failed_count: number
  status: string
  sent_at: string | null
  details: string | null
}

interface ParsedDetails {
  sender?: string
  subject?: string
  recipients_preview?: string
  [key: string]: unknown
}

const LOG_TYPE_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  manual_send:        { label: '수동발송', color: 'text-blue-700', bg: 'bg-blue-50' },
  profile_broadcast:  { label: '프로필발송', color: 'text-purple-700', bg: 'bg-purple-50' },
  auto_send:          { label: '자동발송', color: 'text-teal-700', bg: 'bg-teal-50' },
}

const STATUS_STYLES: Record<string, { label: string; color: string; bg: string }> = {
  completed: { label: '완료', color: 'text-green-700', bg: 'bg-green-50' },
  partial:   { label: '일부실패', color: 'text-yellow-700', bg: 'bg-yellow-50' },
  failed:    { label: '실패', color: 'text-red-700', bg: 'bg-red-50' },
  pending:   { label: '대기', color: 'text-gray-600', bg: 'bg-gray-50' },
}

const PER_PAGE = 50

function fmtDate(iso: string | null): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function parseDetails(raw: string | null): ParsedDetails {
  if (!raw) return {}
  try { return JSON.parse(raw) } catch { return {} }
}

export default function MailLogsPage() {
  const { adminKey, authed } = useAdminAuth()

  const [logs, setLogs] = useState<MailLog[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [searchQ, setSearchQ] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const fetchLogs = useCallback(async (logType = typeFilter, pg = page) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ limit: String(PER_PAGE) })
      if (logType !== 'all') params.set('log_type', logType)

      const res = await fetch(`${API}/api/admin/mail-logs?${params}`, {
        headers: { 'x-admin-key': adminKey },
      })
      const json = await res.json()
      if (!res.ok) {
        throw new Error(json.detail || json.message || `Error ${res.status}`)
      }
      const allLogs: MailLog[] = json.data || []

      // 클라이언트 검색 필터 (details JSON 내부 검색)
      const filtered = searchQ
        ? allLogs.filter(l => {
            const d = parseDetails(l.details)
            const hay = [
              l.log_type, l.status,
              d.sender, d.subject, d.recipients_preview,
            ].filter(Boolean).join(' ').toLowerCase()
            return hay.includes(searchQ.toLowerCase())
          })
        : allLogs

      // 페이지네이션 (클라이언트)
      const start = (pg - 1) * PER_PAGE
      setLogs(filtered.slice(start, start + PER_PAGE))
      setTotal(filtered.length)
    } catch (e) {
      setError(e instanceof Error ? e.message : '데이터 로드 실패')
    } finally {
      setLoading(false)
    }
  }, [adminKey, typeFilter, searchQ, page])

  useEffect(() => {
    if (authed) fetchLogs()
  }, [authed, fetchLogs])

  const handleSearch = (val: string) => {
    setSearchQ(val)
    setPage(1)
  }

  const handleTypeFilter = (val: string) => {
    setTypeFilter(val)
    setPage(1)
  }

  const handlePageChange = (pg: number) => {
    setPage(pg)
    setExpandedId(null)
  }

  const totalPages = Math.ceil(total / PER_PAGE)


  // Stats
  const totalSent = logs.reduce((s, l) => s + (l.sent_count || 0), 0)
  const totalFailed = logs.reduce((s, l) => s + (l.failed_count || 0), 0)

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
          { label: '작업 수', value: total, color: 'text-[#1d1d1f]', bg: 'bg-white' },
          { label: '발송 성공', value: totalSent, color: 'text-green-600', bg: 'bg-green-50/50' },
          { label: '발송 실패', value: totalFailed, color: 'text-red-600', bg: 'bg-red-50/50' },
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
            placeholder="발신자, 제목, 수신자 검색..."
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-[#d2d2d7] text-[13px] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {['all', 'manual_send', 'profile_broadcast'].map(t => (
            <button
              key={t}
              type="button"
              onClick={() => handleTypeFilter(t)}
              className={`px-3.5 py-2 rounded-xl text-[12px] font-medium transition-colors ${
                typeFilter === t
                  ? 'bg-[#1d1d1f] text-white'
                  : 'bg-[#f5f5f7] text-[#424245] hover:bg-[#e8e8ed]'
              }`}
            >
              {t === 'all' ? '전체' : LOG_TYPE_LABELS[t]?.label ?? t}
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
                <th className="px-4 py-3 text-left w-28">유형</th>
                <th className="px-4 py-3 text-left">제목 / 수신자</th>
                <th className="px-4 py-3 text-center w-20">성공</th>
                <th className="px-4 py-3 text-center w-20">실패</th>
                <th className="px-4 py-3 text-left w-24">상태</th>
                <th className="px-4 py-3 text-left w-36">발송일시</th>
                <th className="px-4 py-3 text-left w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f0f2]">
              {logs.map(log => {
                const st = STATUS_STYLES[log.status] ?? STATUS_STYLES.pending
                const lt = LOG_TYPE_LABELS[log.log_type] ?? { label: log.log_type, color: 'text-gray-600', bg: 'bg-gray-50' }
                const d = parseDetails(log.details)
                const expanded = expandedId === log.id
                return (
                  <tr key={log.id} className="group hover:bg-[#fafafa]">
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => setExpandedId(expanded ? null : log.id)}
                        className="text-[#86868b] hover:text-[#1d1d1f] font-mono text-[11px]"
                      >
                        {log.id}
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded-full ${lt.bg} ${lt.color}`}>
                        {lt.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 max-w-[280px]">
                      {d.subject ? (
                        <div className="truncate text-[#1d1d1f] font-medium">{d.subject}</div>
                      ) : null}
                      {d.recipients_preview ? (
                        <div className="truncate text-[11px] text-[#86868b]">{d.recipients_preview}</div>
                      ) : log.candidate_id ? (
                        <div className="truncate text-[11px] text-[#86868b]">후보자: {log.candidate_id}</div>
                      ) : (
                        <div className="text-[11px] text-[#aaa]">-</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-green-600 font-semibold">{log.sent_count}</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={log.failed_count > 0 ? 'text-red-600 font-semibold' : 'text-[#aaa]'}>{log.failed_count}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center text-[11px] font-semibold px-2.5 py-1 rounded-full ${st.bg} ${st.color}`}>
                        {st.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[12px] text-[#86868b]">
                      {fmtDate(log.sent_at)}
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
                  <td colSpan={8} className="px-4 py-16 text-center text-[#86868b]">
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
          const d = parseDetails(log.details)
          return (
            <div className="px-6 py-4 bg-[#fafafa] border-t border-[#e5e5e7]">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-[12px]">
                <div>
                  <span className="text-[#86868b] block mb-0.5">발신자</span>
                  <span className="text-[#1d1d1f] font-medium">{d.sender || '-'}</span>
                </div>
                <div>
                  <span className="text-[#86868b] block mb-0.5">수신자</span>
                  <span className="text-[#1d1d1f] font-medium">{d.recipients_preview || '-'}</span>
                </div>
                <div>
                  <span className="text-[#86868b] block mb-0.5">유형</span>
                  <span className="text-[#1d1d1f] font-medium">{log.log_type}</span>
                </div>
                <div>
                  <span className="text-[#86868b] block mb-0.5">구인자 수</span>
                  <span className="text-[#1d1d1f] font-medium">{log.employer_count || '-'}</span>
                </div>
              </div>
              {d.subject && (
                <div className="mt-3 text-[12px]">
                  <span className="text-[#86868b]">제목:</span>{' '}
                  <span className="text-[#1d1d1f] font-medium">{d.subject}</span>
                </div>
              )}
              {log.candidate_id && (
                <div className="mt-1 text-[12px]">
                  <span className="text-[#86868b]">후보자 ID:</span>{' '}
                  <span className="text-[#1d1d1f] font-medium">{log.candidate_id}</span>
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
