'use client'

/**
 * /admin/form-config — Apply & Inquiry 폼 옵션 관리
 * 각 드롭다운/체크리스트 항목을 추가·삭제·저장·초기화
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

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

// ── 타입 ──────────────────────────────────────────────────────────────────

type FormName = 'apply' | 'inquiry'
type FieldConfig = Record<string, string[]>

// ── FieldEditor 컴포넌트 ─────────────────────────────────────────────────

function FieldEditor({
  formName, fieldKey, fieldLabel, options, onSaved, signedFetch,
}: {
  formName: FormName
  fieldKey: string
  fieldLabel: string
  options: string[]
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
    setTimeout(() => setMsg(null), 3000)
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
    setLocalOpts(prev => {
      const a = [...prev]
      ;[a[idx - 1], a[idx]] = [a[idx], a[idx - 1]]
      return a
    })
  }

  function handleMoveDown(idx: number) {
    setLocalOpts(prev => {
      if (idx >= prev.length - 1) return prev
      const a = [...prev]
      ;[a[idx], a[idx + 1]] = [a[idx + 1], a[idx]]
      return a
    })
  }

  async function handleSave() {
    if (localOpts.length === 0) { flash('최소 1개 이상 필요합니다.', false); return }
    setSaving(true)
    try {
      const res = await signedFetch(
        `${API}/api/admin/form-config/${formName}/${fieldKey}`,
        {
          method: 'PUT',
          body: JSON.stringify({ options: localOpts }),
        }
      )
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? '저장 실패')
      onSaved(fieldKey, localOpts)
      flash('저장 완료', true)
    } catch (e) {
      flash(e instanceof Error ? e.message : '저장 실패', false)
    } finally {
      setSaving(false)
    }
  }

  async function handleReset() {
    if (!confirm(`"${fieldLabel}" 항목을 기본값으로 초기화할까요?`)) return
    setResetting(true)
    try {
      const res = await signedFetch(
        `${API}/api/admin/form-config/${formName}/${fieldKey}/reset`,
        { method: 'POST' }
      )
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? '초기화 실패')
      setLocalOpts(json.data?.options ?? [])
      onSaved(fieldKey, json.data?.options ?? [])
      flash('기본값으로 초기화 완료', true)
    } catch (e) {
      flash(e instanceof Error ? e.message : '초기화 실패', false)
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
            <button
              type="button"
              onClick={() => handleMoveUp(idx)}
              disabled={idx === 0}
              className="text-gray-300 hover:text-gray-600 text-xs px-1 disabled:opacity-20"
              title="위로"
            >▲</button>
            <button
              type="button"
              onClick={() => handleMoveDown(idx)}
              disabled={idx === localOpts.length - 1}
              className="text-gray-300 hover:text-gray-600 text-xs px-1 disabled:opacity-20"
              title="아래로"
            >▼</button>
            <button
              type="button"
              onClick={() => handleDelete(idx)}
              className="text-gray-300 hover:text-red-400 text-xs px-1"
              title="삭제"
            >✕</button>
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
        <button
          type="button"
          onClick={handleAdd}
          disabled={!newOpt.trim()}
          className="text-sm px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 disabled:opacity-40"
        >
          추가
        </button>
      </div>

      {/* 저장 / 초기화 */}
      <div className="flex items-center gap-2 pt-1">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="flex-1 text-sm py-2 rounded-lg font-semibold text-white disabled:opacity-50"
          style={{ background: '#1a1a2e' }}
        >
          {saving ? '저장 중...' : '저장'}
        </button>
        <button
          type="button"
          onClick={handleReset}
          disabled={resetting}
          className="text-sm px-4 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
        >
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

export default function FormConfigPage() {
  const { authed, login, signedFetch, waking } = useAdminAuth()

  const [activeForm, setActiveForm] = useState<FormName>('apply')
  const [config, setConfig]         = useState<FieldConfig>({})
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState<string | null>(null)

  const fields = activeForm === 'apply' ? APPLY_FIELDS : INQUIRY_FIELDS

  const fetchConfig = useCallback(async (form: FormName) => {
    setLoading(true)
    setError(null)
    try {
      const res  = await signedFetch(`${API}/api/admin/form-config/${form}`)
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? '로드 실패')
      setConfig(json.data ?? {})
    } catch (e) {
      setError(e instanceof Error ? e.message : '로드 실패')
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

      {/* 폼 탭 */}
      <div className="flex gap-2 border-b border-gray-200 pb-0">
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

      {/* 로딩 / 에러 */}
      {loading && (
        <div className="text-center py-12 text-gray-400 text-sm">불러오는 중...</div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
          {error}
          <button type="button" onClick={() => fetchConfig(activeForm)} className="ml-3 underline text-red-500">
            재시도
          </button>
        </div>
      )}

      {/* 필드 목록 */}
      {!loading && !error && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {fields.map(({ key, label }) => (
            <FieldEditor
              key={`${activeForm}-${key}`}
              formName={activeForm}
              fieldKey={key}
              fieldLabel={label}
              options={config[key] ?? []}
              onSaved={handleSaved}
              signedFetch={signedFetch}
            />
          ))}
        </div>
      )}
    </div>
  )
}
