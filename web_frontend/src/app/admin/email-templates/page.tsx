'use client'

/**
 * /admin/email-templates — 이메일 템플릿 관리
 * 카드 그리드 + 전체화면 에디터 오버레이 + 라이브 미리보기
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL

interface Template {
  template_key: string
  subject:      string
  body_html:    string
  updated_at:   string | null
}

/* ── 템플릿 라벨 + 카테고리 ── */
const TEMPLATE_LABELS: Record<string, string> = {
  contract_offer:       '계약 안내',
  immigration_guide:    '출입국 안내',
  overseas_visa_prep:   '영사 준비',
  job_transition_guide: '이직 안내',
  arrival_guide:        '입국 안내',
  candidate_profile:    '프로필 발송',
  interview_school:     '인터뷰 (학교)',
  interview_candidate:  '인터뷰 (후보자)',
}

type Category = 'contract' | 'immigration' | 'interview' | 'profile'

const TEMPLATE_CATEGORY: Record<string, Category> = {
  contract_offer:       'contract',
  immigration_guide:    'immigration',
  overseas_visa_prep:   'immigration',
  job_transition_guide: 'contract',
  arrival_guide:        'immigration',
  candidate_profile:    'profile',
  interview_school:     'interview',
  interview_candidate:  'interview',
}

const CATEGORY_STYLES: Record<Category, { bg: string; text: string; border: string; label: string }> = {
  contract:    { bg: 'bg-blue-50',   text: 'text-blue-700',   border: 'border-blue-200', label: '계약' },
  immigration: { bg: 'bg-green-50',  text: 'text-green-700',  border: 'border-green-200', label: '출입국' },
  interview:   { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', label: '인터뷰' },
  profile:     { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', label: '프로필' },
}

const DEFAULT_KEYS = Object.keys(TEMPLATE_LABELS)

/* ── 변수 치환 미리보기 ── */
const SAMPLE_VARS: Record<string, string> = {
  '{candidate_first_name}': 'John',
  '{candidate_name}':       'John Smith',
  '{scheduled_at}':         '2026-03-10 14:00',
  '{meet_link}':            'https://meet.google.com/abc-defg-hij',
  '{employer_name}':        'Seoul English Academy',
  '{school_name}':          'Seoul English Academy',
  '{position}':             'ESL Teacher',
  '{start_date}':           '2026-04-01',
  '{salary}':               '2,500,000 KRW',
}

function substituteVars(html: string): string {
  let result = html
  for (const [key, val] of Object.entries(SAMPLE_VARS)) {
    result = result.replaceAll(key, `<span style="background:#fef3c7;padding:0 2px;border-radius:2px">${val}</span>`)
  }
  return result
}

/* ── 메인 페이지 ── */
export default function EmailTemplatesPage() {
  const { adminKey, authed, login, waking } = useAdminAuth()

  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saveMsg, setSaveMsg] = useState('')

  /* ── 에디터 상태 ── */
  const [editing, setEditing] = useState<Template | null>(null)
  const [editSubject, setEditSubject] = useState('')
  const [editBody, setEditBody] = useState('')
  const [origSubject, setOrigSubject] = useState('')
  const [origBody, setOrigBody] = useState('')
  const [editorMode, setEditorMode] = useState<'html' | 'preview'>('html')
  const [mobileTab, setMobileTab] = useState<'editor' | 'preview'>('editor')
  const [saving, setSaving] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const hasChanges = editSubject !== origSubject || editBody !== origBody

  /* ── 데이터 로드 ── */
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/email-templates`, {
        headers: { 'x-admin-key': adminKey },
      })
      if (res.status === 403) {
        const errBody = await res.clone().json().catch(() => ({}))
        if (errBody.error?.includes?.('Access denied')) {
          setError('일시적으로 차단되었습니다. 자동 재시도 중...')
          const k = sessionStorage.getItem('bridge_admin_key') || ''
          await fetch(`${API}/api/admin/reset-blacklist`, { method: 'POST', headers: { 'x-admin-key': k } }).catch(() => {})
          setTimeout(() => window.location.reload(), 3000)
          return
        }
        setError('관리자 키가 올바르지 않습니다. 다시 로그인해주세요.')
        sessionStorage.removeItem('bridge_admin_key')
        return
      }
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? 'Error')
      setTemplates(json.data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '데이터 로드 실패')
    } finally {
      setLoading(false)
    }
  }, [adminKey])

  useEffect(() => {
    if (authed) fetchData()
  }, [authed, fetchData])

  /* ── 편집 열기 ── */
  const openEditor = useCallback((t: Template) => {
    setEditing(t)
    setEditSubject(t.subject)
    setEditBody(t.body_html)
    setOrigSubject(t.subject)
    setOrigBody(t.body_html)
    setEditorMode('html')
    setMobileTab('editor')
  }, [])

  /* ── 편집 닫기 ── */
  const closeEditor = useCallback(() => {
    if (hasChanges) {
      if (!window.confirm('저장하지 않은 변경사항이 있습니다. 닫으시겠습니까?')) return
    }
    setEditing(null)
  }, [hasChanges])

  /* ── 저장 ── */
  const handleSave = useCallback(async () => {
    if (!editing) return
    setSaving(true)
    try {
      const res = await fetch(`${API}/api/admin/email-templates/${editing.template_key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body: JSON.stringify({ subject: editSubject, body_html: editBody }),
      })
      if (!res.ok) throw new Error('저장 실패')
      setSaveMsg(`"${TEMPLATE_LABELS[editing.template_key] ?? editing.template_key}" 저장됨`)
      setTimeout(() => setSaveMsg(''), 3000)
      setOrigSubject(editSubject)
      setOrigBody(editBody)
      fetchData()
    } catch (e) {
      setSaveMsg('저장 실패: ' + (e instanceof Error ? e.message : ''))
    } finally {
      setSaving(false)
    }
  }, [adminKey, editing, editSubject, editBody, fetchData])

  /* ── 새 템플릿 생성 ── */
  const handleCreate = useCallback(async (key: string) => {
    try {
      const res = await fetch(`${API}/api/admin/email-templates/${key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body: JSON.stringify({
          subject: `[BRIDGE] ${TEMPLATE_LABELS[key] ?? key}`,
          body_html: '<p>내용을 입력하세요.</p>',
        }),
      })
      if (!res.ok) throw new Error('생성 실패')
      fetchData()
    } catch (e) {
      setSaveMsg('생성 실패: ' + (e instanceof Error ? e.message : ''))
    }
  }, [adminKey, fetchData])

  /* ── Esc 키로 닫기 ── */
  useEffect(() => {
    if (!editing) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeEditor()
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        handleSave()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [editing, closeEditor, handleSave])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  const existingKeys = new Set(templates.map((t) => t.template_key))
  const missingKeys = DEFAULT_KEYS.filter((k) => !existingKeys.has(k))

  const getCat = (key: string) => TEMPLATE_CATEGORY[key] ?? 'contract'
  const getCatStyle = (key: string) => CATEGORY_STYLES[getCat(key)]

  return (
    <div className="max-w-[1200px] mx-auto px-4 py-6">

      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-lg font-bold text-gray-900">이메일 템플릿 관리</h1>
          <p className="text-xs text-gray-500">
            {loading ? '로딩 중...' : `${templates.length}개 템플릿`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveMsg && <span className="text-xs text-green-600 font-medium">{saveMsg}</span>}
          <button type="button" className="text-sm text-blue-600 hover:underline" onClick={fetchData}>
            새로고침
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg">{error}</div>
      )}

      {/* 누락 템플릿 알림 */}
      {missingKeys.length > 0 && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-800">
          <span className="font-medium">기본 템플릿이 없습니다:</span>
          {missingKeys.map((k) => (
            <button key={k} type="button"
              className="ml-2 px-2 py-0.5 bg-yellow-200 rounded text-yellow-900 hover:bg-yellow-300"
              onClick={() => handleCreate(k)}>
              + {TEMPLATE_LABELS[k] ?? k}
            </button>
          ))}
        </div>
      )}

      {/* ── 카드 그리드 ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {templates.map((t) => {
          const cat = getCatStyle(t.template_key)
          return (
            <div
              key={t.template_key}
              className="group bg-white border border-gray-200 rounded-xl overflow-hidden cursor-pointer transition-all hover:shadow-lg hover:border-gray-300 hover:-translate-y-0.5"
              onClick={() => openEditor(t)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter') openEditor(t) }}
            >
              <div className="p-5">
                {/* 카테고리 필 + 날짜 */}
                <div className="flex items-center justify-between mb-3">
                  <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${cat.bg} ${cat.text} ${cat.border}`}>
                    {cat.label}
                  </span>
                  {t.updated_at && (
                    <span className="text-[11px] text-gray-400">
                      {new Date(t.updated_at).toLocaleDateString('ko-KR')}
                    </span>
                  )}
                </div>

                {/* 라벨 */}
                <p className="text-[11px] text-gray-400 font-medium mb-1">
                  {t.template_key}
                </p>

                {/* 제목 */}
                <h3 className="text-sm font-semibold text-gray-900 mb-2 line-clamp-1 group-hover:text-blue-600 transition-colors">
                  {TEMPLATE_LABELS[t.template_key] ?? t.template_key}
                </h3>

                {/* 제목(subject) 줄 */}
                <p className="text-xs text-gray-600 mb-3 line-clamp-1">
                  {t.subject || '(제목 없음)'}
                </p>

                {/* 미리보기 2줄 */}
                <div className="text-xs text-gray-400 line-clamp-2 border-t border-gray-100 pt-2 min-h-[2.5rem]">
                  {t.body_html
                    ? t.body_html.replace(/<[^>]*>/g, '').slice(0, 120) || '(빈 내용)'
                    : '(내용 없음)'}
                </div>
              </div>

              {/* 하단 액션 바 */}
              <div className="px-5 py-2.5 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
                <span className="text-[11px] text-gray-400">클릭하여 편집</span>
                <span className="text-xs text-blue-500 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                  편집 &rarr;
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {!loading && templates.length === 0 && (
        <div className="text-center py-12 text-gray-400 text-sm">
          이메일 템플릿이 없습니다. 위의 버튼으로 생성하세요.
        </div>
      )}

      {/* ══════════════════════════════════════════
          전체화면 에디터 오버레이
         ══════════════════════════════════════════ */}
      {editing && (
        <div
          className="fixed inset-0 bg-white flex flex-col"
          style={{ zIndex: 99999 }}
        >
          {/* ── 상단 바 ── */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white shrink-0">
            <div className="flex items-center gap-3">
              {/* 카테고리 필 */}
              {(() => {
                const cat = getCatStyle(editing.template_key)
                return (
                  <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${cat.bg} ${cat.text} ${cat.border}`}>
                    {cat.label}
                  </span>
                )
              })()}
              <span className="text-sm font-bold text-gray-900">
                {TEMPLATE_LABELS[editing.template_key] ?? editing.template_key}
              </span>
              {hasChanges && (
                <span className="text-[10px] text-orange-500 font-medium bg-orange-50 px-2 py-0.5 rounded-full">
                  변경됨
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {/* HTML / 미리보기 토글 (데스크톱) */}
              <div className="hidden md:flex items-center bg-gray-100 rounded-lg p-0.5">
                <button
                  type="button"
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                    editorMode === 'html' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                  }`}
                  onClick={() => setEditorMode('html')}
                >
                  HTML
                </button>
                <button
                  type="button"
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                    editorMode === 'preview' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                  }`}
                  onClick={() => setEditorMode('preview')}
                >
                  미리보기
                </button>
              </div>

              {/* Ctrl+S 힌트 */}
              <span className="hidden md:inline text-[10px] text-gray-400">Ctrl+S</span>

              {/* 저장 */}
              <button
                type="button"
                className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                onClick={handleSave}
                disabled={saving || !hasChanges}
              >
                {saving ? '저장 중...' : '저장'}
              </button>

              {/* 닫기 */}
              <button
                type="button"
                className="ml-1 p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                onClick={closeEditor}
                title="닫기 (Esc)"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* ── 제목 입력 ── */}
          <div className="px-4 py-2.5 border-b border-gray-100 bg-gray-50 shrink-0">
            <div className="flex items-center gap-2">
              <label className="text-xs font-medium text-gray-500 shrink-0">제목</label>
              <input
                className="flex-1 bg-white border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100"
                value={editSubject}
                onChange={(e) => setEditSubject(e.target.value)}
                placeholder="이메일 제목"
              />
            </div>
          </div>

          {/* ── 모바일 탭 전환 ── */}
          <div className="md:hidden flex border-b border-gray-200 bg-white shrink-0">
            <button
              type="button"
              className={`flex-1 py-2.5 text-xs font-medium text-center transition-colors ${
                mobileTab === 'editor'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-500'
              }`}
              onClick={() => setMobileTab('editor')}
            >
              HTML 편집
            </button>
            <button
              type="button"
              className={`flex-1 py-2.5 text-xs font-medium text-center transition-colors ${
                mobileTab === 'preview'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-500'
              }`}
              onClick={() => setMobileTab('preview')}
            >
              미리보기
            </button>
          </div>

          {/* ── 메인 에디터 영역 ── */}
          <div className="flex-1 flex overflow-hidden">
            {/* 데스크톱: split pane */}
            {/* 모바일: 탭 전환 */}

            {/* 에디터 패널 */}
            <div className={`flex-1 flex flex-col overflow-hidden border-r border-gray-200
              ${/* 데스크톱 */ ''}
              ${editorMode === 'preview' ? 'hidden md:flex' : 'flex'}
              ${/* 모바일 탭 */ ''}
              ${mobileTab === 'preview' ? 'hidden md:flex' : ''}
            `}>
              <div className="px-4 py-2 flex items-center justify-between bg-gray-50 border-b border-gray-100 shrink-0">
                <span className="text-[11px] font-medium text-gray-500">HTML 에디터</span>
                <span className="text-[10px] text-gray-400">
                  {editBody.length.toLocaleString()} 자
                </span>
              </div>
              <textarea
                ref={textareaRef}
                className="flex-1 w-full px-4 py-3 text-sm font-mono text-gray-800 resize-none focus:outline-none bg-white"
                value={editBody}
                onChange={(e) => setEditBody(e.target.value)}
                spellCheck={false}
                placeholder="<p>HTML 내용을 입력하세요.</p>"
              />
            </div>

            {/* 미리보기 패널 */}
            <div className={`flex-1 flex flex-col overflow-hidden
              ${editorMode === 'html' && mobileTab === 'editor' ? 'hidden md:hidden' : ''}
              ${editorMode === 'preview' || mobileTab === 'preview' ? 'flex' : 'hidden md:flex'}
            `}>
              <div className="px-4 py-2 flex items-center justify-between bg-gray-50 border-b border-gray-100 shrink-0">
                <span className="text-[11px] font-medium text-gray-500">미리보기</span>
                <span className="text-[10px] text-gray-400">
                  변수가 샘플 값으로 치환됩니다
                </span>
              </div>
              <div className="flex-1 overflow-y-auto p-6 bg-white">
                {/* 이메일 프레임 */}
                <div className="max-w-[640px] mx-auto">
                  <div className="mb-4 pb-3 border-b border-gray-200">
                    <p className="text-[11px] text-gray-400 mb-1">Subject</p>
                    <p className="text-sm font-medium text-gray-900">{editSubject || '(제목 없음)'}</p>
                  </div>
                  <div
                    className="prose prose-sm max-w-none text-gray-800"
                    dangerouslySetInnerHTML={{ __html: substituteVars(editBody) }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* ── 하단 상태바 ── */}
          <div className="px-4 py-2 border-t border-gray-200 bg-gray-50 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3">
              <span className="text-[10px] text-gray-400">
                템플릿: {editing.template_key}
              </span>
              {editing.updated_at && (
                <span className="text-[10px] text-gray-400">
                  마지막 수정: {new Date(editing.updated_at).toLocaleString('ko-KR')}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 text-[10px] text-gray-400">
              <span>Esc: 닫기</span>
              <span>Ctrl+S: 저장</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
