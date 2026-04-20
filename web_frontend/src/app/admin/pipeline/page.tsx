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
  const [seenDlqIds, setSeenDlqIds] = useState<Set<number>>(new Set())
  const [popupJob, setPopupJob] = useState<DlqJob | null>(null)
  const [notifPerm, setNotifPerm] = useState<NotificationPermission>('default')

  const showToast = (m: string) => { setToast(m); setTimeout(() => setToast(''), 3000) }

  // 브라우저 Notification 권한 요청 (최초 1회)
  useEffect(() => {
    if (typeof window === 'undefined' || !('Notification' in window)) return
    setNotifPerm(Notification.permission)
    if (Notification.permission === 'default') {
      Notification.requestPermission().then(p => setNotifPerm(p))
    }
  }, [])

  const fireDesktopNotification = useCallback((job: DlqJob) => {
    if (typeof window === 'undefined' || !('Notification' in window)) return
    if (Notification.permission !== 'granted') return
    try {
      let payloadInfo = ''
      try {
        const p = JSON.parse(job.payload_json)
        payloadInfo = `${p.file_type || ''} ${p.filename || ''}`.trim()
      } catch { /* ignore */ }
      const n = new Notification('🚨 BRIDGE 파이프라인 실패', {
        body: `Job #${job.id} [${job.job_type}]\n${payloadInfo}\n${job.last_error?.slice(0, 120) || ''}`,
        tag: `bridge-dlq-${job.id}`,
        requireInteraction: true,
      })
      n.onclick = () => { window.focus(); setPopupJob(job); n.close() }
    } catch (e) { console.error('notification', e) }
  }, [])

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [sRes, dRes, eRes] = await Promise.all([
        adminFetch(`${API_URL}/api/admin/pipeline/stats`),
        adminFetch(`${API_URL}/api/admin/pipeline/dlq?limit=50`),
        adminFetch(`${API_URL}/api/admin/pipeline/events?limit=50`),
      ])
      if (sRes.ok) { const j = await sRes.json(); setStats(j.data || null) }
      if (dRes.ok) {
        const j = await dRes.json()
        const jobs: DlqJob[] = j.data?.dlq_jobs || []
        setDlq(jobs)
        // 신규 DLQ 감지 → 알림 + 팝업
        const currentIds = new Set(jobs.map(x => x.id))
        const newOnes = jobs.filter(x => !seenDlqIds.has(x.id))
        if (newOnes.length > 0 && seenDlqIds.size > 0) {
          // 초기 로드가 아니고 신규 발생 → 알림
          newOnes.forEach(fireDesktopNotification)
          setPopupJob(newOnes[0])
          try {
            if (typeof Audio !== 'undefined') {
              // 간단 경고음 (브라우저 제약 있음)
              const a = new Audio('data:audio/wav;base64,UklGRhwDAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YdoCAACBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYE=')
              a.play().catch(() => {})
            }
          } catch { /* ignore */ }
        }
        setSeenDlqIds(currentIds)
      }
      if (eRes.ok) { const j = await eRes.json(); setEvents(j.data?.events || []) }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [adminFetch, seenDlqIds, fireDesktopNotification])

  useEffect(() => { loadAll() /* eslint-disable-next-line */ }, [])

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
                    <button onClick={() => setPopupJob(j)} style={{ padding: '3px 10px', background: '#6B7280', color: '#fff', border: 'none', borderRadius: 4, fontSize: 12, cursor: 'pointer', marginRight: 4 }}>상세</button>
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

      {/* 알림 권한 표시 */}
      {notifPerm !== 'granted' && (
        <div style={{
          position: 'fixed', top: 16, right: 16, maxWidth: 320,
          background: '#FEF3C7', border: '1px solid #F59E0B',
          borderRadius: 8, padding: '10px 14px', fontSize: 12, zIndex: 90,
        }}>
          <div style={{ fontWeight: 700, marginBottom: 4, color: '#92400E' }}>
            🔔 데스크톱 알림 {notifPerm === 'denied' ? '차단됨' : '비활성'}
          </div>
          <div style={{ color: '#78350F', lineHeight: 1.5 }}>
            {notifPerm === 'denied'
              ? '브라우저 주소창 자물쇠 아이콘 → 알림 허용으로 변경'
              : '알림 허용 시 파이프라인 실패를 즉시 감지'}
            {notifPerm === 'default' && (
              <button
                onClick={() => Notification.requestPermission().then(setNotifPerm)}
                style={{ marginLeft: 8, padding: '2px 10px', background: '#F59E0B', color: '#fff', border: 'none', borderRadius: 4, fontSize: 11, cursor: 'pointer' }}
              >허용</button>
            )}
          </div>
        </div>
      )}

      {/* 실패 팝업 모달 */}
      {popupJob && (
        <div
          onClick={() => setPopupJob(null)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
            zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 20,
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              background: '#fff', borderRadius: 12, maxWidth: 640, width: '100%',
              padding: 24, boxShadow: '0 24px 80px rgba(0,0,0,0.4)',
              borderTop: '6px solid #DC2626',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
              <span style={{ fontSize: 28 }}>🚨</span>
              <h2 style={{ fontSize: 20, fontWeight: 800, color: '#991B1B', margin: 0 }}>
                파이프라인 실패 — 관리자 개입 필요
              </h2>
            </div>
            {(() => {
              let payload: Record<string, string> = {}
              try { payload = JSON.parse(popupJob.payload_json) } catch {}
              return (
                <div style={{ fontSize: 13, lineHeight: 1.9 }}>
                  <Row k="Job ID" v={`#${popupJob.id}`} />
                  <Row k="Job Type" v={popupJob.job_type} />
                  <Row k="Candidate" v={String(payload.candidate_id || '-')} />
                  <Row k="File Type" v={String(payload.file_type || '-')} />
                  <Row k="Filename" v={String(payload.filename || '-')} />
                  <Row k="S3 Key" v={String(payload.s3_key || '-').slice(0, 80)} />
                  <Row k="Attempts" v={`${popupJob.attempts}/${popupJob.max_attempts}`} />
                  <div style={{ marginTop: 12, padding: 12, background: '#FEE2E2', borderRadius: 6 }}>
                    <div style={{ fontSize: 11, color: '#991B1B', fontWeight: 700, marginBottom: 4 }}>에러 메시지</div>
                    <pre style={{ fontSize: 12, color: '#7F1D1D', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                      {popupJob.last_error || '(no details)'}
                    </pre>
                  </div>
                  <div style={{ marginTop: 16, padding: 12, background: '#EFF6FF', borderRadius: 6, fontSize: 12 }}>
                    <div style={{ fontWeight: 700, color: '#1E40AF', marginBottom: 6 }}>💡 수동 처리 방법</div>
                    <div style={{ color: '#1E3A8A', lineHeight: 1.8 }}>
                      1. 로컬 폴더: <code style={{ background: '#fff', padding: '2px 6px', borderRadius: 3 }}>Q:\Claudework\bridge base\failed_files\FAIL_{popupJob.id}_*\</code><br />
                      2. 원본 파일 + 에러 로그 + metadata.json 자동 생성됨<br />
                      3. 파일 수정 후 재큐잉 → 자동 재처리<br />
                      4. 또는 직접 /admin/resume-converter 에서 수동 변환
                    </div>
                  </div>
                </div>
              )
            })()}
            <div style={{ display: 'flex', gap: 8, marginTop: 20, justifyContent: 'flex-end' }}>
              <button onClick={() => setPopupJob(null)} style={{ padding: '8px 18px', background: '#E5E7EB', color: '#374151', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>
                닫기
              </button>
              <button
                onClick={() => { requeue(popupJob.id); setPopupJob(null) }}
                style={{ padding: '8px 18px', background: '#1E40AF', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}
              >
                재큐잉
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 토스트 */}
      {toast && (
        <div style={{ position: 'fixed', bottom: 24, right: 24, padding: '10px 18px', background: '#111', color: '#fff', borderRadius: 6, fontSize: 13, zIndex: 100 }}>
          {toast}
        </div>
      )}
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div style={{ display: 'flex', borderBottom: '1px solid #F3F4F6', padding: '4px 0' }}>
      <div style={{ width: 110, color: '#6B7280', fontSize: 12 }}>{k}</div>
      <div style={{ flex: 1, fontFamily: 'monospace', fontSize: 12, wordBreak: 'break-all' }}>{v}</div>
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
