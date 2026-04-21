'use client'

/**
 * /admin/introduce-mail — 소개 메일 발송
 * 원어민 강사 프로필을 구인자(client_inquiries)에게 자동 발송.
 * API:
 *   GET  /api/admin/employers-for-mail   — 구인자 목록
 *   POST /api/admin/mail/introduce       — 소개 메일 발송
 *   GET  /api/admin/mail/introduce-log   — 발송 이력
 */

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import AdminAuth from '@/components/admin/AdminAuth'
import { API_URL } from '@/lib/api'

interface Employer {
  id: number
  school_name: string
  location: string
  contact_name: string
  email: string
  teaching_age: string
  start_date: string
  salary_raw: string
}

interface SendLog {
  id: number
  sent_at: string
  candidate_ids: string
  to_email: string
  school_name: string
  contact_name: string
  subject: string
  status: string
  error: string | null
  sender_email: string
  link_expiry_days: number
}

interface SendResult {
  sent: number
  failed: number
  total_employers: number
  candidate_count: number
  errors: { email: string; error: string }[]
}

/* ── 진입점 ── */
export default function IntroduceMailPage() {
  const { authed, login, waking } = useAdminAuth()
  if (!authed) return <AdminAuth onLogin={login} waking={waking} />
  return (
    <Suspense fallback={null}>
      <IntroduceMailContent />
    </Suspense>
  )
}

/* ── 메인 콘텐츠 ── */
function IntroduceMailContent() {
  const { adminFetch } = useAdminAuth()
  const searchParams = useSearchParams()

  /* ── 강사 입력 (URL query string 자동 주입) ── */
  const [candidateInput, setCandidateInput] = useState(() => {
    const c = searchParams.get('candidates')
    return c ? c.replace(/,/g, '\n') : ''
  })

  /* ── 구인자 ── */
  const [employers, setEmployers] = useState<Employer[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [locFilter, setLocFilter] = useState('')
  const [ageFilter, setAgeFilter] = useState('')
  const [loadingEmp, setLoadingEmp] = useState(false)
  const [totalEmp, setTotalEmp] = useState(0)

  /* ── 발송 설정 ── */
  const [sender, setSender] = useState<'naver' | 'gmail'>('naver')
  const [expiryDays, setExpiryDays] = useState(10)
  const [customMsg, setCustomMsg] = useState('')

  /* ── 상태 ── */
  const [sending, setSending] = useState(false)
  const [sendResult, setSendResult] = useState<SendResult | null>(null)
  const [sendError, setSendError] = useState<string | null>(null)
  const [logs, setLogs] = useState<SendLog[]>([])
  const [loadingLog, setLoadingLog] = useState(false)
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null)
  const [showPreview, setShowPreview] = useState(false)
  const [previewHtml, setPreviewHtml] = useState('')
  const [loadingPreview, setLoadingPreview] = useState(false)

  function showToast(msg: string, ok = true) {
    setToast({ msg, ok })
    setTimeout(() => setToast(null), 3500)
  }

  /* ── 강사 번호 파싱 (preview에서도 사용) ── */
  function parseCandidateNums(raw: string): string[] {
    return raw.split(/[\n,\s]+/).map(s => s.trim()).filter(s => s && /^\d+$/.test(s))
  }

  /* ── 메일 미리보기 ── */
  const loadPreview = useCallback(async () => {
    const ids = parseCandidateNums(candidateInput)
    if (ids.length === 0) { showToast('강사 번호를 먼저 입력하세요.', false); return }
    setLoadingPreview(true)
    setShowPreview(true)
    try {
      const res = await adminFetch(`${API_URL}/api/admin/mail/introduce-preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_ids: ids,
          custom_message: customMsg.trim(),
          link_expiry_days: expiryDays,
        }),
      })
      const data = await res.json()
      setPreviewHtml(data.data?.html || '<p style="color:#999">미리보기를 생성할 수 없습니다.</p>')
    } catch {
      setPreviewHtml('<p style="color:#dc2626">미리보기 로드 실패 — 강사 번호 확인 후 재시도</p>')
    } finally {
      setLoadingPreview(false)
    }
  }, [adminFetch, candidateInput, customMsg, expiryDays])

  /* ── 구인자 불러오기 ── */
  const loadEmployers = useCallback(async () => {
    setLoadingEmp(true)
    setSelectedIds(new Set())
    try {
      const p = new URLSearchParams({ per_page: '200' })
      if (locFilter.trim()) p.set('location', locFilter.trim())
      if (ageFilter.trim()) p.set('teaching_age', ageFilter.trim())
      const res = await adminFetch(`${API_URL}/api/admin/employers-for-mail?${p}`)
      const data = await res.json()
      setEmployers(data.data?.employers ?? [])
      setTotalEmp(data.data?.total ?? 0)
    } catch {
      showToast('구인자 목록 불러오기 실패', false)
    } finally {
      setLoadingEmp(false)
    }
  }, [adminFetch, locFilter, ageFilter])

  /* ── 발송 이력 ── */
  const loadLog = useCallback(async () => {
    setLoadingLog(true)
    try {
      const res = await adminFetch(`${API_URL}/api/admin/mail/introduce-log?limit=50`)
      const data = await res.json()
      setLogs(data.data?.logs ?? [])
    } catch { /* silent */ } finally {
      setLoadingLog(false)
    }
  }, [adminFetch])

  useEffect(() => {
    loadEmployers()
    loadLog()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  /* ── 선택 토글 ── */
  function toggleEmp(id: number) {
    setSelectedIds(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  /* ── 강사 번호 파싱 ── */
  function getCandidateIds(): string[] {
    return candidateInput
      .split(/[\n,\s]+/)
      .map(s => s.trim())
      .filter(s => s && /^\d+$/.test(s))
  }

  /* ── v2.0: 강사별 CV 처리 상태 (chip 표시용) ── */
  interface CvStatus {
    status: string
    has_cv: boolean
    processed_at: string
    attempts: number
    last_error: string
  }
  const [cvStatuses, setCvStatuses] = useState<Record<string, CvStatus>>({})
  const [statusLoading, setStatusLoading] = useState(false)

  useEffect(() => {
    const ids = candidateInput
      .split(/[\n,\s]+/).map(s => s.trim()).filter(s => s && /^\d+$/.test(s))
    if (ids.length === 0) { setCvStatuses({}); return }
    const ctl = new AbortController()
    const timer = setTimeout(async () => {
      setStatusLoading(true)
      try {
        const res = await adminFetch(`${API_URL}/api/admin/candidates/check-processed-status`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sheet_numbers: ids.map(x => parseInt(x, 10)) }),
          signal: ctl.signal,
        })
        if (res.ok) {
          const j = await res.json()
          setCvStatuses(j.data?.statuses || {})
        }
      } catch { /* abort or network */ }
      finally { setStatusLoading(false) }
    }, 350) // debounce
    return () => { clearTimeout(timer); ctl.abort() }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateInput])

  const cvStatusBadge = (sn: string): { label: string; color: string; bg: string; title: string } => {
    const s = cvStatuses[sn]
    if (!s) return { label: '...', color: '#6B7280', bg: '#F3F4F6', title: '조회 중' }
    if (s.status === 'done' && s.has_cv) return { label: '✓', color: '#047857', bg: '#D1FAE5', title: `이력서 처리됨 (${s.processed_at.slice(0,10)})` }
    if (s.status === 'running' || s.status === 'queued') return { label: '⏳', color: '#B45309', bg: '#FEF3C7', title: `처리중 (시도 ${s.attempts}회)` }
    if (s.status === 'failed' || s.status === 'dlq') return { label: '✗', color: '#B91C1C', bg: '#FEE2E2', title: `실패: ${s.last_error || '알 수 없음'}` }
    if (s.status === 'not_found') return { label: '?', color: '#9CA3AF', bg: '#F3F4F6', title: '존재하지 않는 강사번호' }
    return { label: '·', color: '#6B7280', bg: '#F3F4F6', title: '미처리(pending)' }
  }

  /* ── 발송 ── */
  async function handleSend() {
    const candidateIds = getCandidateIds()
    if (candidateIds.length === 0) { showToast('강사 번호를 입력해주세요.', false); return }
    if (selectedIds.size === 0) { showToast('구인자를 선택해주세요.', false); return }
    if (!confirm(`${candidateIds.length}명 강사 프로필을 ${selectedIds.size}개 기관에 발송할까요?`)) return

    setSending(true)
    setSendResult(null)
    setSendError(null)

    try {
      const res = await adminFetch(`${API_URL}/api/admin/mail/introduce`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_ids: candidateIds,
          employer_ids: Array.from(selectedIds),
          sender,
          link_expiry_days: expiryDays,
          custom_message: customMsg.trim(),
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || '발송 실패')
      setSendResult(data.data)
      const skippedMsg = data.data.skipped_duplicate
        ? ` (중복 ${data.data.skipped_duplicate}건 제외)` : ''
      showToast(`${data.data.sent}건 발송 완료${skippedMsg}`)
      // 발송 성공 후 선택 초기화 — 실수 재발송 방지
      setSelectedIds(new Set())
      loadLog()
    } catch (e) {
      const msg = e instanceof Error ? e.message : '발송 실패'
      setSendError(msg)
      showToast(msg, false)
    } finally {
      setSending(false)
    }
  }

  const candidateIds = getCandidateIds()

  const fmtDt = (s: string) =>
    new Date(s).toLocaleString('ko-KR', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })

  const parseCandidateIds = (raw: string) => {
    try { return (JSON.parse(raw) as string[]).join(', ') }
    catch { return raw }
  }

  return (
    <div>
      {/* 헤더 */}
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, color: '#1d1d1f', margin: 0 }}>
          소개 메일 발송
        </h1>
        <p style={{ color: '#6B7280', fontSize: 13, marginTop: 4, marginBottom: 0 }}>
          원어민 강사 프로필을 구인자(학교·학원)에게 자동 발송합니다. 이력서 S3 presigned URL 포함.
        </p>
      </div>

      {/* 3열 패널 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.6fr 1fr', gap: 14, marginBottom: 16 }}>

        {/* ── 패널 1: 강사 선택 ── */}
        <div style={CARD}>
          <PanelTitle>강사 선택</PanelTitle>
          <p style={{ fontSize: 12, color: '#9CA3AF', margin: '0 0 8px' }}>
            원어민 관리 시트에서 강사번호(◼XXXX)를 복사해 입력하세요.
          </p>
          <textarea
            placeholder={'강사번호 입력 (쉼표·줄바꿈 구분)\n예: 1001, 1003\n또는\n1001\n1003'}
            value={candidateInput}
            onChange={e => setCandidateInput(e.target.value)}
            rows={9}
            style={TA}
          />
          {candidateIds.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
                입력된 강사: <strong>{candidateIds.length}명</strong>
                {statusLoading && <span style={{ marginLeft: 8, color: '#9CA3AF' }}>상태 조회중…</span>}
                {(() => {
                  const missing = candidateIds.filter(id => {
                    const s = cvStatuses[id]
                    return !s || !(s.status === 'done' && s.has_cv)
                  })
                  if (missing.length === 0) return null
                  return (
                    <span style={{ marginLeft: 10, color: '#B91C1C', fontWeight: 700 }}>
                      ⚠ 이력서 미처리 {missing.length}명 — 발송 차단됨
                    </span>
                  )
                })()}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {candidateIds.map(id => {
                  const b = cvStatusBadge(id)
                  return (
                    <span key={id} style={CHIP} title={b.title}>
                      {id}
                      <span style={{
                        marginLeft: 4, padding: '0 5px', borderRadius: 3,
                        fontSize: 11, fontWeight: 700,
                        color: b.color, background: b.bg,
                      }}>{b.label}</span>
                    </span>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* ── 패널 2: 구인자 선택 ── */}
        <div style={CARD}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <PanelTitle>구인자 선택</PanelTitle>
            <span style={{ fontSize: 12, color: '#6B7280' }}>
              {selectedIds.size} / {employers.length}명 선택
            </span>
          </div>

          {/* 필터 행 */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 8 }}>
            <input
              placeholder="위치 (예: 서울, Busan)"
              value={locFilter}
              onChange={e => setLocFilter(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && loadEmployers()}
              style={INPUT}
            />
            <input
              placeholder="대상 연령 (예: 유아, 초등)"
              value={ageFilter}
              onChange={e => setAgeFilter(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && loadEmployers()}
              style={INPUT}
            />
          </div>

          {/* 버튼 행 */}
          <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
            <button onClick={loadEmployers} disabled={loadingEmp} style={BTN_SM}>
              {loadingEmp ? '로딩 중...' : '불러오기'}
            </button>
            <button onClick={() => setSelectedIds(new Set(employers.map(e => e.id)))} style={BTN_SM}>
              전체선택
            </button>
            <button onClick={() => setSelectedIds(new Set())} style={BTN_SM}>
              선택해제
            </button>
          </div>

          {/* 구인자 목록 */}
          <div style={{
            height: 276, overflowY: 'auto',
            border: '1px solid #E5E7EB', borderRadius: 8,
          }}>
            {employers.length === 0 ? (
              <div style={{ padding: 24, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
                {loadingEmp ? '로딩 중...' : '불러오기 버튼을 눌러 구인자 목록을 로드하세요.'}
              </div>
            ) : employers.map(emp => {
              const checked = selectedIds.has(emp.id)
              return (
                <div
                  key={emp.id}
                  onClick={() => toggleEmp(emp.id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '7px 11px', borderBottom: '1px solid #F3F4F6',
                    cursor: 'pointer', background: checked ? '#EFF6FF' : 'transparent',
                    transition: 'background 0.1s',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleEmp(emp.id)}
                    onClick={e => e.stopPropagation()}
                    style={{ width: 14, height: 14, cursor: 'pointer', flexShrink: 0 }}
                  />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: 13, color: '#111', ...ELLIPSIS }}>
                      {emp.school_name || emp.contact_name || '(이름없음)'}
                    </div>
                    <div style={{ fontSize: 11, color: '#6B7280', ...ELLIPSIS }}>
                      {[emp.location, emp.teaching_age, emp.email].filter(Boolean).join(' · ')}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {totalEmp > 200 && (
            <p style={{ fontSize: 11, color: '#F59E0B', marginTop: 6, margin: '6px 0 0' }}>
              전체 {totalEmp}명 중 200명 표시 — 필터로 범위를 좁히세요.
            </p>
          )}
        </div>

        {/* ── 패널 3: 발송 설정 ── */}
        <div style={CARD}>
          <PanelTitle>발송 설정</PanelTitle>

          <FieldLabel>발신자</FieldLabel>
          <select value={sender} onChange={e => setSender(e.target.value as 'naver' | 'gmail')} style={{ ...INPUT, marginBottom: 12 }}>
            <option value="naver">Naver (bridgejobkr)</option>
            <option value="gmail">Gmail (bridgejobkr)</option>
          </select>

          <FieldLabel>CV 링크 유효기간: {expiryDays}일</FieldLabel>
          <input
            type="range" min={1} max={7} step={1}
            value={Math.min(expiryDays, 7)}
            onChange={e => setExpiryDays(Number(e.target.value))}
            style={{ width: '100%', marginBottom: 2 }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#9CA3AF', marginBottom: 4 }}>
            <span>1일</span><span>7일 (AWS S3 max)</span>
          </div>
          <p style={{ fontSize: 10, color: '#9CA3AF', margin: '0 0 12px' }}>
            AWS S3 presigned URL은 최대 7일까지 유효합니다.
          </p>

          <FieldLabel>추가 메시지 (선택)</FieldLabel>
          <textarea
            placeholder="메일 상단에 추가될 메시지"
            value={customMsg}
            onChange={e => setCustomMsg(e.target.value)}
            rows={3}
            style={{ ...TA, marginBottom: 12 }}
          />

          {/* 요약 박스 */}
          <div style={{
            background: '#F8FAFC', border: '1px solid #E2E8F0',
            borderRadius: 8, padding: '10px 12px', marginBottom: 14, fontSize: 13,
          }}>
            <div style={{ color: '#374151', lineHeight: 1.9 }}>
              <div>강사: <strong style={{ color: candidateIds.length ? '#111' : '#9CA3AF' }}>{candidateIds.length}명</strong></div>
              <div>구인자: <strong style={{ color: selectedIds.size ? '#111' : '#9CA3AF' }}>{selectedIds.size}개 기관</strong></div>
              <div>링크 유효: <strong>{expiryDays}일</strong></div>
            </div>
          </div>

          {/* 미리보기 버튼 */}
          <button
            onClick={loadPreview}
            disabled={loadingPreview || candidateIds.length === 0}
            style={{
              width: '100%', padding: '9px 0', marginBottom: 8,
              background: '#fff', color: '#0ea5e9',
              border: '1.5px solid #0ea5e9', borderRadius: 8,
              fontWeight: 700, fontSize: 13, cursor: 'pointer',
              opacity: (loadingPreview || candidateIds.length === 0) ? 0.45 : 1,
              transition: 'opacity 0.15s',
            }}
          >
            {loadingPreview ? '미리보기 생성 중...' : '메일 미리보기'}
          </button>

          {/* 발송 버튼 — v2.0: 이력서 미처리 강사가 있으면 disable */}
          {(() => {
            const missingCvCount = candidateIds.filter(id => {
              const s = cvStatuses[id]
              return !s || !(s.status === 'done' && s.has_cv)
            }).length
            const blocked = sending || candidateIds.length === 0 || selectedIds.size === 0 || missingCvCount > 0
            return (
              <button
                onClick={handleSend}
                disabled={blocked}
                title={missingCvCount > 0 ? `이력서 미처리 강사 ${missingCvCount}명 — 재처리 필요` : undefined}
                style={{
                  width: '100%', padding: '12px 0',
                  background: missingCvCount > 0 ? '#9CA3AF' : '#111', color: '#fff', border: 'none',
                  borderRadius: 8, fontWeight: 700, fontSize: 14, cursor: blocked ? 'not-allowed' : 'pointer',
                  opacity: blocked ? 0.55 : 1,
                  transition: 'opacity 0.15s',
                }}
              >
                {sending
                  ? '발송 중...'
                  : missingCvCount > 0
                    ? `발송 불가 — 이력서 미처리 ${missingCvCount}명`
                    : `소개 메일 발송 (${selectedIds.size}개 기관)`}
              </button>
            )
          })()}

          {/* 결과 */}
          {sendResult && (
            <div style={{
              marginTop: 12, background: '#F0FDF4',
              border: '1px solid #BBF7D0', borderRadius: 8, padding: '10px 12px',
            }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#15803D' }}>
                발송 완료: {sendResult.sent}건
              </div>
              {sendResult.failed > 0 && (
                <div style={{ fontSize: 12, color: '#DC2626', marginTop: 4 }}>
                  실패: {sendResult.failed}건
                  {sendResult.errors.slice(0, 3).map((e, i) => (
                    <div key={i} style={{ fontSize: 11, marginTop: 2 }}>• {e.email}: {e.error}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          {sendError && (
            <div style={{
              marginTop: 12, background: '#FEF2F2',
              border: '1px solid #FECACA', borderRadius: 8, padding: '10px 12px',
            }}>
              <div style={{ fontSize: 13, color: '#DC2626' }}>{sendError}</div>
            </div>
          )}
        </div>
      </div>

      {/* ── 메일 미리보기 패널 ── */}
      {showPreview && (
        <div style={{ ...CARD, marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <PanelTitle>메일 미리보기</PanelTitle>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={loadPreview} disabled={loadingPreview} style={BTN_SM}>
                {loadingPreview ? '생성 중...' : '새로고침'}
              </button>
              <button onClick={() => setShowPreview(false)} style={{ ...BTN_SM, color: '#9CA3AF' }}>닫기</button>
            </div>
          </div>
          {loadingPreview ? (
            <div style={{ padding: '40px 0', textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
              강사 프로필 블록 생성 중...
            </div>
          ) : (
            <div
              style={{
                border: '1px solid #E5E7EB', borderRadius: 8,
                padding: '20px 24px', background: '#FAFAFA',
                maxHeight: 480, overflowY: 'auto',
              }}
              dangerouslySetInnerHTML={{ __html: previewHtml }}
            />
          )}
        </div>
      )}

      {/* ── 발송 이력 ── */}
      <div style={CARD}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <PanelTitle>발송 이력</PanelTitle>
          <button onClick={loadLog} disabled={loadingLog} style={BTN_SM}>
            {loadingLog ? '로딩 중...' : '새로고침'}
          </button>
        </div>

        {logs.length === 0 ? (
          <div style={{ padding: '28px 0', textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
            {loadingLog ? '로딩 중...' : '발송 이력이 없습니다.'}
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ background: '#F9FAFB', borderBottom: '2px solid #E5E7EB' }}>
                  {['발송일시', '수신자', '학교/기관', '강사 번호', '상태', '링크 유효', '오류'].map(h => (
                    <th key={h} style={{
                      padding: '8px 10px', textAlign: 'left',
                      fontWeight: 600, color: '#374151', whiteSpace: 'nowrap',
                    }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                    <td style={TD}>{fmtDt(log.sent_at)}</td>
                    <td style={TD}>{log.to_email}</td>
                    <td style={{ ...TD, maxWidth: 160, ...ELLIPSIS }}>
                      {log.school_name || log.contact_name || '—'}
                    </td>
                    <td style={TD}>
                      <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#6B7280' }}>
                        {parseCandidateIds(log.candidate_ids)}
                      </span>
                    </td>
                    <td style={TD}>
                      <span style={{
                        padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 700,
                        background: log.status === 'sent' ? '#D1FAE5' : '#FEE2E2',
                        color: log.status === 'sent' ? '#065F46' : '#991B1B',
                      }}>
                        {log.status === 'sent' ? '발송' : '실패'}
                      </span>
                    </td>
                    <td style={{ ...TD, whiteSpace: 'nowrap' }}>{log.link_expiry_days}일</td>
                    <td style={{ ...TD, color: '#DC2626', maxWidth: 200, ...ELLIPSIS }}>
                      {log.error || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
          background: toast.ok ? '#111' : '#DC2626', color: '#fff',
          padding: '12px 20px', borderRadius: 10,
          fontSize: 14, fontWeight: 600,
          boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
        }}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}

/* ── 스타일 상수 ── */

const CARD: React.CSSProperties = {
  background: '#fff', border: '1px solid #E5E7EB', borderRadius: 12, padding: '16px 18px',
}

const INPUT: React.CSSProperties = {
  width: '100%', padding: '8px 10px', border: '1px solid #D1D5DB',
  borderRadius: 7, fontSize: 13, outline: 'none', boxSizing: 'border-box',
}

const TA: React.CSSProperties = {
  width: '100%', padding: '8px 10px', border: '1px solid #D1D5DB',
  borderRadius: 7, fontSize: 13, outline: 'none', boxSizing: 'border-box',
  resize: 'vertical', fontFamily: 'inherit', lineHeight: 1.6,
}

const BTN_SM: React.CSSProperties = {
  padding: '6px 12px', background: '#F3F4F6', border: '1px solid #D1D5DB',
  borderRadius: 7, fontSize: 12, cursor: 'pointer', color: '#374151', fontWeight: 600,
}

const CHIP: React.CSSProperties = {
  display: 'inline-flex', background: '#EFF6FF', color: '#1D4ED8',
  borderRadius: 6, padding: '2px 8px', fontSize: 12, fontWeight: 600,
}

const ELLIPSIS: React.CSSProperties = {
  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
}

const TD: React.CSSProperties = {
  padding: '8px 10px', color: '#374151', verticalAlign: 'middle',
}

/* ── 소형 컴포넌트 ── */

function PanelTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 style={{ fontSize: 14, fontWeight: 700, color: '#1d1d1f', margin: '0 0 10px' }}>
      {children}
    </h2>
  )
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label style={{
      display: 'block', fontSize: 12, fontWeight: 600,
      color: '#374151', margin: '0 0 5px',
    }}>
      {children}
    </label>
  )
}
