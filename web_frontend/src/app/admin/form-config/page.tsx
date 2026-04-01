'use client'

/**
 * /admin/form-config — Apply & Inquiry 폼 옵션 관리
 *
 * 자동 폴백 정책:
 * - 백엔드 정상  → DB 저장값 표시
 * - 404 / 연결불가 → 하드코딩 기본값 자동 표시 (amber 배너, 에러창 없음)
 * - 403 인증 오류 → 로그인 화면 표시 (정상 동작)
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import { APPLY_DEFAULTS, INQUIRY_DEFAULTS } from '@/lib/form-defaults'

const API = API_URL

// ── 필드 메타데이터 ────────────────────────────────────────────────────────

const APPLY_FIELDS: { key: string; label: string }[] = [
  { key: 'HOW_TO',          label: 'How did you know about BRIDGE?' },
  { key: 'NATIONALITIES',   label: 'Nationality' },
  { key: 'ANCESTRY',        label: 'Family Ancestry Background' },
  { key: 'EDUCATION',       label: 'Educational Background' },
  { key: 'CERTIFICATION',   label: 'Certification' },
  { key: 'E_VISA',          label: 'E Visa' },
  { key: 'PASSPORT',        label: 'Passport' },
  { key: 'CRIMINAL_RECORD', label: 'Criminal Record' },
  { key: 'DOC_STATUS',      label: 'Document Status' },
  { key: 'TARGET_AGE',      label: 'Preferred Age Group' },
  { key: 'AREA_PREFS',      label: 'Area Preferences' },
  { key: 'EXPERIENCE',      label: 'Teaching Experience in Korea' },
  { key: 'EMPLOYMENT',      label: 'Employment' },
  { key: 'MARITAL',         label: 'Marital Status' },
  { key: 'HOUSING',         label: 'Housing' },
  { key: 'DEPENDENTS_PETS', label: 'Dependents & Pets' },
  { key: 'PERSONAL',        label: 'Personal Considerations' },
  { key: 'RELIGION',        label: 'Religion' },
  { key: 'HEALTH',          label: 'Health Information' },
  { key: 'CRC',             label: 'Criminal Record Check' },
  { key: 'KR_CRC',          label: 'Criminal Record in Korea' },
]

const INQUIRY_FIELDS: { key: string; label: string }[] = [
  { key: 'BUSINESS_REG',        label: '사업자 (Business Registration)' },
  { key: 'HIRE_HIST',           label: '채용이력 (Hiring History)' },
  { key: 'NATIVE_COUNT',        label: '원어민강사 수 (Native Count)' },
  { key: 'VACANCIES',           label: '채용인원 (Vacancies)' },
  { key: 'CONTRACT_TYPE',       label: '계약구분 (Contract Type)' },
  { key: 'TEACHING_AGE',        label: '수업대상 (Teaching Age)' },
  { key: 'CLASS_SIZE',          label: '학생수 (Class Size)' },
  { key: 'AVG_LESSONS',         label: '평균강의 (Avg Lessons/Week)' },
  { key: 'PREFERRED_CANDIDATE', label: '선호대상 (Preferred Candidate)' },
  { key: 'SALARY_RANGES',       label: '급여조건 (Salary Ranges)' },
  { key: 'TRAVEL_SUPPORT',      label: '이동지원 (Travel Support)' },
  { key: 'MEAL_OPTS',           label: '식사/식대 (Meal Options)' },
  { key: 'HOUSING_OPTS',        label: '숙소제공 (Housing Options)' },
  { key: 'BENEFITS_OPTS',       label: '복지 (Benefits)' },
  { key: 'VACATION_INC',        label: '휴일포함여부 (Vacation Includes)' },
]

// ── 오프라인 모드 유형 ────────────────────────────────────────────────────

type OfflineReason = null | 'not_deployed' | 'network' | 'server_error'

function offlineMsg(reason: OfflineReason): string {
  if (reason === 'not_deployed') return 'Render 백엔드 미배포 — 기본값 표시 중. 배포 후 새로고침하면 저장 가능합니다.'
  if (reason === 'network')      return '서버 연결 불가 — 기본값 표시 중. 연결 복구 후 새로고침하세요.'
  if (reason === 'server_error') return '서버 오류 — 기본값 표시 중. 잠시 후 새로고침하세요.'
  return ''
}

// ── FieldEditor 컴포넌트 ─────────────────────────────────────────────────

function FieldEditor({
  formName, fieldKey, fieldLabel, options, offline, onSaved, signedFetch,
}: {
  formName: 'apply' | 'inquiry'
  fieldKey: string
  fieldLabel: string
  options: string[]
  offline: boolean
  onSaved: (key: string, opts: string[]) => void
  signedFetch: (url: string, init?: RequestInit) => Promise<Response>
}) {
  const [localOpts, setLocalOpts] = useState<string[]>(options)
  const [newOpt, setNewOpt]       = useState('')
  const [saving, setSaving]       = useState(false)
  const [resetting, setResetting] = useState(false)
  const [msg, setMsg]             = useState<{ text: string; ok: boolean } | null>(null)

  useEffect(() => { setLocalOpts(options) }, [options])

  function flash(text: string, ok: boolean) {
    setMsg({ text, ok })
    setTimeout(() => setMsg(null), 4000)
  }

  function handleAdd() {
    const v = newOpt.trim()
    if (!v || localOpts.includes(v)) return
    setLocalOpts(prev => [...prev, v])
    setNewOpt('')
  }

  function handleDelete(idx: number) {
    setLocalOpts(prev => prev.filter((_, i) => i !== idx))
  }

  function handleMoveUp(idx: number) {
    if (idx === 0) return
    setLocalOpts(prev => { const a = [...prev]; [a[idx-1], a[idx]] = [a[idx], a[idx-1]]; return a })
  }

  function handleMoveDown(idx: number) {
    setLocalOpts(prev => {
      if (idx >= prev.length - 1) return prev
      const a = [...prev]; [a[idx], a[idx+1]] = [a[idx+1], a[idx]]; return a
    })
  }

  async function handleSave() {
    if (localOpts.length === 0) { flash('최소 1개 이상 필요합니다.', false); return }
    setSaving(true)
    try {
      const res  = await signedFetch(
        `${API}/api/admin/form-config/${formName}/${fieldKey}`,
        { method: 'PUT', body: JSON.stringify({ options: localOpts }) },
      )
      if (res.status === 404) {
        flash('백엔드 미배포 — Render 배포 후 저장 가능합니다.', false)
        return
      }
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? '저장 실패')
      onSaved(fieldKey, localOpts)
      flash('저장 완료', true)
    } catch (e) {
      const msg = e instanceof Error ? e.message : '저장 실패'
      flash(msg.includes('fetch') || msg.includes('network') ? '서버 연결 실패' : msg, false)
    } finally {
      setSaving(false)
    }
  }

  async function handleReset() {
    if (!confirm(`"${fieldLabel}" 항목을 기본값으로 초기화할까요?`)) return
    setResetting(true)
    try {
      const res  = await signedFetch(
        `${API}/api/admin/form-config/${formName}/${fieldKey}/reset`,
        { method: 'POST' },
      )
      if (res.status === 404) {
        // 백엔드 없으면 클라이언트 측 기본값으로 복원
        const clientDefaults = (formName === 'apply' ? APPLY_DEFAULTS : INQUIRY_DEFAULTS)[fieldKey] ?? []
        setLocalOpts(clientDefaults)
        onSaved(fieldKey, clientDefaults)
        flash('기본값 복원 (로컬)', true)
        return
      }
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? '초기화 실패')
      setLocalOpts(json.data?.options ?? [])
      onSaved(fieldKey, json.data?.options ?? [])
      flash('기본값으로 초기화 완료', true)
    } catch (e) {
      const msg = e instanceof Error ? e.message : '초기화 실패'
      flash(msg.includes('fetch') || msg.includes('network') ? '서버 연결 실패' : msg, false)
    } finally {
      setResetting(false)
    }
  }

  return (
    <div className="border border-gray-200 rounded-xl p-4 space-y-3 bg-white">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-mono text-gray-400 mr-2">{fieldKey}</span>
          <span className="text-sm font-semibold text-gray-800">{fieldLabel}</span>
        </div>
        <span className="text-xs text-gray-400">{localOpts.length}개</span>
      </div>

      {/* 옵션 목록 */}
      <div className="space-y-1 max-h-64 overflow-y-auto">
        {localOpts.map((opt, idx) => (
          <div key={idx} className="flex items-center gap-1.5 group">
            <span className="text-xs text-gray-400 w-5 text-right shrink-0">{idx + 1}</span>
            <span className="flex-1 text-sm bg-gray-50 rounded px-2 py-1 truncate">{opt}</span>
            <button type="button" onClick={() => handleMoveUp(idx)} disabled={idx === 0}
              className="text-gray-300 hover:text-gray-600 text-xs px-1 disabled:opacity-20" title="위로">▲</button>
            <button type="button" onClick={() => handleMoveDown(idx)} disabled={idx === localOpts.length - 1}
              className="text-gray-300 hover:text-gray-600 text-xs px-1 disabled:opacity-20" title="아래로">▼</button>
            <button type="button" onClick={() => handleDelete(idx)}
              className="text-gray-300 hover:text-red-400 text-xs px-1" title="삭제">✕</button>
          </div>
        ))}
        {localOpts.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-2">항목 없음</p>
        )}
      </div>

      {/* 새 항목 추가 */}
      <div className="flex gap-2">
        <input
          type="text"
          value={newOpt}
          onChange={(e) => setNewOpt(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAdd() } }}
          placeholder="새 항목 입력 후 Enter"
          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-400"
        />
        <button type="button" onClick={handleAdd} disabled={!newOpt.trim()}
          className="text-sm px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 disabled:opacity-40">
          추가
        </button>
      </div>

      {/* 저장 / 초기화 */}
      <div className="flex items-center gap-2 pt-1">
        <button type="button" onClick={handleSave} disabled={saving || offline}
          className="flex-1 text-sm py-2 rounded-lg font-semibold text-white disabled:opacity-50"
          style={{ background: offline ? '#9ca3af' : '#1a1a2e' }}
          title={offline ? 'Render 배포 후 저장 가능' : undefined}>
          {saving ? '저장 중...' : offline ? '저장 불가 (미배포)' : '저장'}
        </button>
        <button type="button" onClick={handleReset} disabled={resetting}
          className="text-sm px-4 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40">
          {resetting ? '초기화 중...' : '기본값'}
        </button>
      </div>

      {msg && (
        <p className={`text-xs text-center font-medium ${msg.ok ? 'text-green-600' : 'text-red-500'}`}>
          {msg.text}
        </p>
      )}
    </div>
  )
}

// ── 메인 페이지 ───────────────────────────────────────────────────────────

type FormName = 'apply' | 'inquiry'

export default function FormConfigPage() {
  const { authed, login, signedFetch, waking } = useAdminAuth()

  const [activeForm,     setActiveForm]     = useState<FormName>('apply')
  const [config,         setConfig]         = useState<Record<string, string[]>>({})
  const [loading,        setLoading]        = useState(false)
  const [offlineReason,  setOfflineReason]  = useState<OfflineReason>(null)

  const fields = activeForm === 'apply' ? APPLY_FIELDS : INQUIRY_FIELDS

  /** API 호출 → 실패 시 하드코딩 기본값 자동 폴백 (에러 블로킹 없음) */
  const fetchConfig = useCallback(async (form: FormName) => {
    setLoading(true)
    setOfflineReason(null)
    try {
      const res  = await signedFetch(`${API}/api/admin/form-config/${form}`)
      const json = await res.json().catch(() => ({}))

      if (res.status === 404) {
        // 엔드포인트 없음 → 백엔드 미배포
        setOfflineReason('not_deployed')
        setConfig(form === 'apply' ? APPLY_DEFAULTS : INQUIRY_DEFAULTS)
        return
      }
      if (res.status === 403) {
        // 인증 오류는 useAdminAuth가 처리 (authed=false → AdminAuth 표시)
        return
      }
      if (!res.ok || !json.success) {
        setOfflineReason('server_error')
        setConfig(form === 'apply' ? APPLY_DEFAULTS : INQUIRY_DEFAULTS)
        return
      }

      // 성공 — DB에 없는 키는 기본값으로 보충
      const dbData: Record<string, string[]> = json.data ?? {}
      const fallback = form === 'apply' ? APPLY_DEFAULTS : INQUIRY_DEFAULTS
      const merged: Record<string, string[]> = {}
      for (const { key } of (form === 'apply' ? APPLY_FIELDS : INQUIRY_FIELDS)) {
        merged[key] = dbData[key] ?? fallback[key] ?? []
      }
      setConfig(merged)
    } catch {
      // 네트워크 오류
      setOfflineReason('network')
      setConfig(form === 'apply' ? APPLY_DEFAULTS : INQUIRY_DEFAULTS)
    } finally {
      setLoading(false)
    }
  }, [signedFetch])

  useEffect(() => {
    if (authed) fetchConfig(activeForm)
  }, [authed, activeForm, fetchConfig])

  function handleSaved(key: string, opts: string[]) {
    setConfig(prev => ({ ...prev, [key]: opts }))
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="space-y-6 pb-16">
      {/* 헤더 */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">폼 옵션 관리</h1>
        <p className="text-gray-500 text-sm">
          지원폼·구인폼의 드롭다운 / 체크리스트 항목을 직접 수정합니다.
          저장 후 최대 5분 내 사이트에 반영됩니다.
        </p>
      </div>

      {/* 오프라인 배너 (에러창 대신 소프트 안내) */}
      {offlineReason && (
        <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl px-4 py-3 text-sm">
          <span className="text-lg shrink-0">⚠️</span>
          <div className="flex-1">
            <p className="font-semibold">기본값 표시 중</p>
            <p className="text-amber-700 mt-0.5">{offlineMsg(offlineReason)}</p>
          </div>
          <button
            type="button"
            onClick={() => fetchConfig(activeForm)}
            className="shrink-0 text-xs text-amber-600 underline hover:text-amber-800 mt-0.5"
          >
            재연결
          </button>
        </div>
      )}

      {/* 폼 탭 */}
      <div className="flex gap-2 border-b border-gray-200">
        {(['apply', 'inquiry'] as FormName[]).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => { setActiveForm(f); setConfig({}) }}
            className={`px-5 py-2.5 text-sm font-semibold rounded-t-lg transition-all -mb-px border
              ${activeForm === f
                ? 'bg-white border-gray-200 border-b-white text-blue-600'
                : 'bg-gray-50 border-transparent text-gray-500 hover:text-gray-700'
              }`}
          >
            {f === 'apply' ? '지원폼 (Apply)' : '구인폼 (Inquiry)'}
          </button>
        ))}
      </div>

      {/* 로딩 */}
      {loading && (
        <div className="text-center py-12 text-gray-400 text-sm">불러오는 중...</div>
      )}

      {/* 필드 목록 */}
      {!loading && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {fields.map(({ key, label }) => (
            <FieldEditor
              key={`${activeForm}-${key}`}
              formName={activeForm}
              fieldKey={key}
              fieldLabel={label}
              options={config[key] ?? []}
              offline={offlineReason !== null}
              onSaved={handleSaved}
              signedFetch={signedFetch}
            />
          ))}
        </div>
      )}
    </div>
  )
}
