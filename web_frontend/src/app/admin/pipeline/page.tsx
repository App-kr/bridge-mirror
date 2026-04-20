'use client'

/**
 * /admin/pipeline — Resume Pipeline v2.0 대시보드
 * 실시간 큐 상태 + DLQ + 이벤트 로그 모니터링
 * API:
 *   GET  /api/admin/pipeline/stats
 *   GET  /api/admin/pipeline/dlq
 *   POST /api/admin/pipeline/dlq/{id}/requeue
 *   GET  /api/admin/pipeline/events
 */

import { useState, useEffect, useCallback } from 'react'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import AdminAuth from '@/components/admin/AdminAuth'
import { API_URL } from '@/lib/api'

interface QueueStats {
  queue: Record<string, Record<string, number>>
  candidates_by_status: Record<string, number>
  total_candidates: number
  processed_done: number
  success_rate_pct: number
}

interface DlqJob {
  id: number
  job_type: string
  attempts: number
  max_attempts: number
  last_error: string
  created_at: string
  updated_at: string
  payload_json: string
}

interface PipelineEvent {
  id: number
  ts: string
  event_type: string
  candidate_id: string | null
  job_id: number | null
  severity: string
  details_json: string
}

export default function PipelineDashboardPage() {
  const { authed, login, waking, adminFetch } = useAdminAuth()
  if (!authed) return <AdminAuth onLogin={login} waking={waking} />
  return <DashboardContent adminFetch={adminFetch} />
}

type AdminFetch = (u: string, init?: RequestInit) => Promise<Response>

function DashboardContent({ adminFetch }: { adminFetch: AdminFetch }) {
  const [stats, setStats] = useState<QueueStats | null>(null)
  const [dlq, setDlq] = useState<DlqJob[]>([])
  const [events, setEvents] = useState<PipelineEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [toast, setToast] = useState<string>('')

  const showToast = (m: string) => { setToast(m); setTimeout(() => setToast(''), 3000) }

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [sRes, dRes, eRes] = await Promise.all([
        adminFetch(`${API_URL}/api/admin/pipeline/stats`),
        adminFetch(`${API_URL}/api/admin/pipeline/dlq?limit=50`),
        adminFetch(`${API_URL}/api/admin/pipeline/events?limit=50`),
      ])
      if (sRes.ok) { const j = await sRes.json(); setStats(j.data || null) }
      if (dRes.ok) { const j = await dRes.json(); setDlq(j.data?.dlq_jobs || []) }
      if (eRes.ok) { const j = await eRes.json(); setEvents(j.data?.events || []) }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [adminFetch])

  useEffect(() => { loadAll() }, [loadAll])

  useEffect(() => {
    if (!autoRefresh) return
    const iv = setInterval(() => loadAll(), 10_000)
    return () => clearInterval(iv)
  }, [autoRefresh, loadAll])

  async function requeue(id: number) {
    if (!confirm(`Job #${id} 재큐잉할까요?`)) return
    try {
      const res = await adminFetch(`${API_URL}/api/admin/pipeline/dlq/${id}/requeue`, { method: 'POST' })
      if (res.ok) {
        showToast(`Job #${id} 재큐잉 완료`)
        loadAll()
      } else {
        const j = await res.json().catch(() => ({}))
        showToast(`실패: ${j.error?.message || res.status}`)
      }
    } catch (e) { showToast(`실패: ${e}`) }
  }

  const sevColor = (s: string) => {
    if (s === 'critical') return '#B91C1C'
    if (s === 'error') return '#DC2626'
    if (s === 'warn') return '#D97706'
    return '#065F46'
  }

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800 }}>Resume Pipeline v2.0 대시보드</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
            <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} />
            자동새로고침 (10초)
          </label>
          <button onClick={loadAll} disabled={loading} style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid #D1D5DB', background: '#fff', cursor: 'pointer' }}>
            {loading ? '…' : '새로고침'}
          </button>
        </div>
      </div>

      {/* ── 성공률 카드 ── */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 12, marginBottom: 18 }}>
          <Card title="전체 후보자" value={stats.total_candidates.toLocaleString()} color="#1E40AF" />
          <Card title="처리 완료" value={stats.processed_done.toLocaleString()} color="#065F46" />
          <Card
            title="성공률"
            value={`${stats.success_rate_pct.toFixed(2)}%`}
            color={stats.success_rate_pct >= 95 ? '#065F46' : stats.success_rate_pct >= 50 ? '#D97706' : '#B91C1C'}
          />
          <Card title="DLQ" value={dlq.length.toString()} color={dlq.length > 0 ? '#B91C1C' : '#6B7280'} />
        </div>
      )}

      {/* ── 큐 상태 ── */}
      <section style={{ background: '#fff', border: '1px solid #E5E7EB', borderRadius: 10, padding: 16, marginBottom: 18 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 10 }}>큐 상태</h2>
        {stats?.queue && Object.keys(stats.queue).length > 0 ? (
          <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#F9FAFB', textAlign: 'left' }}>
                <th style={TH}>job_type</th>
                <th style={TH}>queued</th>
                <th style={TH}>running</th>
                <th style={TH}>done</th>
                <th style={TH}>failed</th>
                <th style={TH}>dlq</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(stats.queue).map(([k, v]) => (
                <tr key={k}>
                  <td style={TD}><strong>{k}</strong></td>
                  <td style={TD}>{v.queued || 0}</td>
                  <td style={TD}>{v.running || 0}</td>
                  <td style={TD}>{v.done || 0}</td>
                  <td style={TD}>{v.failed || 0}</td>
                  <td style={{ ...TD, color: (v.dlq || 0) > 0 ? '#B91C1C' : undefined, fontWeight: 700 }}>{v.dlq || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ color: '#6B7280', fontSize: 13 }}>작업 없음</div>
        )}

        {stats?.candidates_by_status && Object.keys(stats.candidates_by_status).length > 0 && (
          <>
            <h3 style={{ fontSize: 14, fontWeight: 700, margin: '16px 0 8px' }}>후보자 처리 상태 분포</h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {Object.entries(stats.candidates_by_status).map(([k, v]) => (
                <span key={k} style={{ fontSize: 12, padding: '3px 10px', borderRadius: 12, background: '#F3F4F6', border: '1px solid #E5E7EB' }}>
                  {k}: <strong>{v.toLocaleString()}</strong>
                </span>
              ))}
            </div>
          </>
        )}
      </section>

      {/* ── DLQ ── */}
      <section style={{ background: '#fff', border: '1px solid #E5E7EB', borderRadius: 10, padding: 16, marginBottom: 18 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 10 }}>
          Dead Letter Queue ({dlq.length}건)
        </h2>
        {dlq.length === 0 ? (
          <div style={{ color: '#6B7280', fontSize: 13 }}>DLQ 비어있음</div>
        ) : (
          <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#FEF2F2', textAlign: 'left' }}>
                <th style={TH}>id</th>
                <th style={TH}>type</th>
                <th style={TH}>attempts</th>
                <th style={TH}>last_error</th>
                <th style={TH}>updated_at</th>
                <th style={TH}>action</th>
              </tr>
            </thead>
            <tbody>
              {dlq.map(j => (
                <tr key={j.id}>
                  <td style={TD}>{j.id}</td>
                  <td style={TD}>{j.job_type}</td>
                  <td style={TD}>{j.attempts}/{j.max_attempts}</td>
                  <td style={{ ...TD, maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={j.last_error}>
                    {j.last_error || '-'}
                  </td>
                  <td style={TD}>{j.updated_at?.slice(0, 19)}</td>
                  <td style={TD}>
                    <button onClick={() => requeue(j.id)} style={{ padding: '3px 10px', background: '#1E40AF', color: '#fff', border: 'none', borderRadius: 4, fontSize: 12, cursor: 'pointer' }}>재큐잉</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* ── 이벤트 로그 ── */}
      <section style={{ background: '#fff', border: '1px solid #E5E7EB', borderRadius: 10, padding: 16 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 10 }}>최근 이벤트 ({events.length}건)</h2>
        <div style={{ maxHeight: 400, overflow: 'auto' }}>
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#F9FAFB', textAlign: 'left', position: 'sticky', top: 0 }}>
                <th style={TH}>ts</th>
                <th style={TH}>type</th>
                <th style={TH}>cid</th>
                <th style={TH}>job</th>
                <th style={TH}>sev</th>
                <th style={TH}>details</th>
              </tr>
            </thead>
            <tbody>
              {events.map(e => (
                <tr key={e.id}>
                  <td style={TD}>{e.ts?.slice(0, 19)}</td>
                  <td style={TD}><strong>{e.event_type}</strong></td>
                  <td style={TD}>{e.candidate_id || '-'}</td>
                  <td style={TD}>{e.job_id || '-'}</td>
                  <td style={{ ...TD, color: sevColor(e.severity), fontWeight: 700 }}>{e.severity}</td>
                  <td style={{ ...TD, maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={e.details_json}>
                    {e.details_json || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* 토스트 */}
      {toast && (
        <div style={{ position: 'fixed', bottom: 24, right: 24, padding: '10px 18px', background: '#111', color: '#fff', borderRadius: 6, fontSize: 13, zIndex: 100 }}>
          {toast}
        </div>
      )}
    </div>
  )
}

function Card({ title, value, color }: { title: string; value: string; color: string }) {
  return (
    <div style={{ background: '#fff', border: '1px solid #E5E7EB', borderRadius: 10, padding: 16 }}>
      <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 4 }}>{title}</div>
      <div style={{ fontSize: 24, fontWeight: 800, color }}>{value}</div>
    </div>
  )
}

const TH: React.CSSProperties = { padding: '8px 10px', fontWeight: 600, fontSize: 12, borderBottom: '1px solid #E5E7EB' }
const TD: React.CSSProperties = { padding: '6px 10px', borderBottom: '1px solid #F3F4F6', fontSize: 12 }
