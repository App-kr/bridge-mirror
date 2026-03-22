'use client'

import { useCallback, useEffect, useState } from 'react'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import AdminAuth from '@/components/admin/AdminAuth'
import QuickMail from '../components/QuickMail'
import { ChevronLeft, Search, X, Clock } from 'lucide-react'
import Link from 'next/link'

const API = API_URL

interface Candidate {
  id: number
  name?: string
  email?: string
}

interface MailLog {
  id: number
  to: string
  subject: string
  sent_at: string
  status: string
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '방금'
  if (mins < 60) return `${mins}분 전`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}시간 전`
  const days = Math.floor(hours / 24)
  return `${days}일 전`
}

export default function MailPage() {
  const { authed, waking, login, adminFetch } = useAdminAuth()
  const [selectedEmail, setSelectedEmail] = useState('')
  const [selectedName, setSelectedName] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [mailLogs, setMailLogs] = useState<MailLog[]>([])
  const [logsAvailable, setLogsAvailable] = useState(true)
  const [sentCounter, setSentCounter] = useState(0)

  // Search candidates
  const searchCandidates = useCallback(async (q: string) => {
    if (!q.trim()) {
      setCandidates([])
      return
    }
    setSearchLoading(true)
    try {
      const res = await adminFetch(`${API}/api/admin/candidates?limit=10&q=${encodeURIComponent(q.trim())}`)
      const json = await res.json()
      if (json.success) {
        const list = json.data?.candidates ?? json.data ?? []
        setCandidates(list.slice(0, 10))
      }
    } catch {
      setCandidates([])
    } finally {
      setSearchLoading(false)
    }
  }, [adminFetch])

  // Debounced search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setCandidates([])
      return
    }
    const timer = setTimeout(() => searchCandidates(searchQuery), 300)
    return () => clearTimeout(timer)
  }, [searchQuery, searchCandidates])

  // Fetch mail logs
  const fetchLogs = useCallback(async () => {
    if (!logsAvailable) return
    try {
      const res = await adminFetch(`${API}/api/admin/mail/logs?limit=10`)
      if (res.status === 404) {
        setLogsAvailable(false)
        return
      }
      const json = await res.json()
      if (json.success) {
        setMailLogs(json.data ?? [])
      } else {
        setLogsAvailable(false)
      }
    } catch {
      setLogsAvailable(false)
    }
  }, [adminFetch, logsAvailable])

  useEffect(() => {
    if (authed) fetchLogs()
  }, [authed, fetchLogs, sentCounter])

  const handleSelectCandidate = useCallback((c: Candidate) => {
    setSelectedEmail(c.email || '')
    setSelectedName(c.name || '')
    setSearchQuery('')
    setCandidates([])
  }, [])

  const handleSent = useCallback(() => {
    setSentCounter(prev => prev + 1)
  }, [])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
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
            <h1 className="text-xl font-bold text-[#1d1d1f]">메일</h1>
          </div>
        </div>

        {/* Recipient search */}
        <div className="mb-4">
          <h2 className="text-xs font-semibold text-[#86868b] uppercase tracking-wider mb-2 px-1">
            수신자 검색
          </h2>
          <div className="relative">
            <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#86868b]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="후보자 이름으로 검색..."
              className="w-full pl-10 pr-10 py-2.5 rounded-full bg-white border border-[#e5e5e7] text-sm text-[#1d1d1f] placeholder:text-[#aeaeb2] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 min-h-[44px]"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => { setSearchQuery(''); setCandidates([]) }}
                className="absolute right-3.5 top-1/2 -translate-y-1/2"
              >
                <X size={16} className="text-[#aeaeb2]" />
              </button>
            )}
          </div>

          {/* Search results as pills */}
          {searchLoading && (
            <div className="mt-2 flex gap-2">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-8 w-24 bg-white border border-[#e5e5e7] rounded-full animate-pulse" />
              ))}
            </div>
          )}
          {!searchLoading && candidates.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {candidates.map(c => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => handleSelectCandidate(c)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white border border-[#e5e5e7] text-sm text-[#1d1d1f] font-medium min-h-[36px] active:scale-[0.97] transition-transform"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-[#0071e3] shrink-0" />
                  <span className="truncate max-w-[120px]">{c.name || `#${c.id}`}</span>
                </button>
              ))}
            </div>
          )}
          {!searchLoading && searchQuery.trim() && candidates.length === 0 && (
            <p className="mt-2 text-xs text-[#aeaeb2] px-1">검색 결과가 없습니다</p>
          )}
        </div>

        {/* Selected recipient indicator */}
        {selectedEmail && (
          <div className="mb-3 flex items-center gap-2 px-3 py-2 rounded-xl bg-blue-50 border border-blue-100">
            <span className="text-xs text-blue-700 font-medium flex-1 truncate">
              {selectedName && `${selectedName} — `}{selectedEmail}
            </span>
            <button
              type="button"
              onClick={() => { setSelectedEmail(''); setSelectedName('') }}
            >
              <X size={14} className="text-blue-400" />
            </button>
          </div>
        )}

        {/* Quick compose */}
        <div className="mb-6">
          <QuickMail
            preSelectedEmail={selectedEmail}
            preSelectedName={selectedName}
            onSent={handleSent}
          />
        </div>

        {/* Recent sends */}
        {logsAvailable && mailLogs.length > 0 && (
          <div>
            <h2 className="text-xs font-semibold text-[#86868b] uppercase tracking-wider mb-2 px-1">
              최근 발송
            </h2>
            <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden divide-y divide-[#f5f5f7]">
              {mailLogs.map(log => (
                <div key={log.id} className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium text-[#1d1d1f] truncate flex-1">
                      {log.subject || '(No subject)'}
                    </p>
                    <span className={`shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full ${
                      log.status === 'sent' || log.status === 'delivered'
                        ? 'bg-green-50 text-green-700'
                        : log.status === 'failed'
                        ? 'bg-red-50 text-red-700'
                        : 'bg-[#f5f5f7] text-[#86868b]'
                    }`}>
                      {log.status === 'sent' || log.status === 'delivered' ? '발송완료'
                        : log.status === 'failed' ? '실패'
                        : log.status || '전송'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <p className="text-xs text-[#86868b] truncate flex-1">{log.to}</p>
                    {log.sent_at && (
                      <span className="flex items-center gap-1 text-[10px] text-[#aeaeb2] shrink-0">
                        <Clock size={10} />
                        {timeAgo(log.sent_at)}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
