'use client'

/**
 * /admin/email-templates — 이메일 템플릿 관리
 * 6개 템플릿 카드 + 편집 + 미리보기.
 */

import { useCallback, useEffect, useState } from 'react'
import AdminNav from '@/components/admin/AdminNav'
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

const TEMPLATE_LABELS: Record<string, string> = {
  contract_offer:       '계약 안내',
  immigration_guide:    '출입국 안내',
  overseas_visa_prep:   '영사 준비',
  job_transition_guide: '이직 안내',
  arrival_guide:        '입국 안내',
  candidate_profile:    '프로필 발송',
}

const DEFAULT_KEYS = Object.keys(TEMPLATE_LABELS)

export default function EmailTemplatesPage() {
  const { adminKey, authed, login, waking } = useAdminAuth()

  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<string | null>(null)
  const [editSubject, setEditSubject] = useState('')
  const [editBody, setEditBody] = useState('')
  const [preview, setPreview] = useState<string | null>(null)
  const [saveMsg, setSaveMsg] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/email-templates`, {
        headers: { 'x-admin-key': adminKey },
      })
      const json = await res.json()
      if (res.status === 403) { setError('관리자 키가 올바르지 않습니다.'); return }
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

  const handleEdit = useCallback((t: Template) => {
    setEditing(t.template_key)
    setEditSubject(t.subject)
    setEditBody(t.body_html)
    setPreview(null)
  }, [])

  const handleSave = useCallback(async () => {
    if (!editing) return
    try {
      const res = await fetch(`${API}/api/admin/email-templates/${editing}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body: JSON.stringify({ subject: editSubject, body_html: editBody }),
      })
      if (!res.ok) throw new Error('저장 실패')
      setSaveMsg(`"${TEMPLATE_LABELS[editing] ?? editing}" 저장됨`)
      setTimeout(() => setSaveMsg(''), 3000)
      setEditing(null)
      setPreview(null)
      fetchData()
    } catch (e) {
      setSaveMsg('저장 실패: ' + (e instanceof Error ? e.message : ''))
    }
  }, [adminKey, editing, editSubject, editBody, fetchData])

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

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  const existingKeys = new Set(templates.map((t) => t.template_key))
  const missingKeys = DEFAULT_KEYS.filter((k) => !existingKeys.has(k))

  return (
    <div className="max-w-[1200px] mx-auto px-4 py-6">
      <AdminNav active="/admin/email-templates" />

      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-lg font-bold text-gray-900">이메일 템플릿 관리</h1>
          <p className="text-xs text-gray-500">
            {loading ? '로딩 중…' : `${templates.length}개 템플릿`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saveMsg && <span className="text-xs text-green-600 font-medium">{saveMsg}</span>}
          <button type="button" className="text-sm text-blue-600 hover:underline"
            onClick={fetchData}>새로고침</button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg">{error}</div>
      )}

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

      {/* Template Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {templates.map((t) => {
          const isEditing = editing === t.template_key

          return (
            <div key={t.template_key} className={`bg-white border rounded-xl overflow-hidden ${isEditing ? 'border-blue-400 col-span-full' : 'border-gray-200'}`}>
              {isEditing ? (
                <div className="p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-xs font-mono bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                      {TEMPLATE_LABELS[t.template_key] ?? t.template_key}
                    </span>
                    <button type="button" className="text-xs text-blue-600 font-medium hover:underline"
                      onClick={handleSave}>저장</button>
                    <button type="button" className="text-xs text-gray-500 hover:underline"
                      onClick={() => { setEditing(null); setPreview(null) }}>취소</button>
                    <button type="button" className="text-xs text-purple-600 hover:underline ml-auto"
                      onClick={() => setPreview(preview ? null : editBody)}>
                      {preview ? '에디터' : '미리보기'}
                    </button>
                  </div>

                  <label className="text-xs font-medium text-gray-500 mb-1 block">제목</label>
                  <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-3"
                    value={editSubject} onChange={(e) => setEditSubject(e.target.value)} />

                  {preview ? (
                    <div className="border border-gray-200 rounded-lg p-4 bg-white max-h-[400px] overflow-y-auto">
                      <p className="text-xs text-gray-400 mb-2">미리보기 (변수는 치환 전 상태)</p>
                      <div className="text-sm" dangerouslySetInnerHTML={{ __html: editBody }} />
                    </div>
                  ) : (
                    <>
                      <label className="text-xs font-medium text-gray-500 mb-1 block">본문 (HTML)</label>
                      <textarea
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono resize-y"
                        rows={14}
                        value={editBody}
                        onChange={(e) => setEditBody(e.target.value)}
                      />
                    </>
                  )}
                </div>
              ) : (
                <div className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                      {TEMPLATE_LABELS[t.template_key] ?? t.template_key}
                    </span>
                    <div className="flex items-center gap-2">
                      {t.updated_at && (
                        <span className="text-[11px] text-gray-400">
                          {new Date(t.updated_at).toLocaleDateString('ko-KR')}
                        </span>
                      )}
                      <button type="button" className="text-xs text-blue-600 hover:underline"
                        onClick={() => handleEdit(t)}>편집</button>
                    </div>
                  </div>
                  <h3 className="text-sm font-medium text-gray-900 mb-2 line-clamp-1">{t.subject || '(제목 없음)'}</h3>
                  <div
                    className="text-xs text-gray-500 max-h-20 overflow-hidden border-t border-gray-100 pt-2"
                    dangerouslySetInnerHTML={{ __html: t.body_html?.slice(0, 300) || '<em>내용 없음</em>' }}
                  />
                </div>
              )}
            </div>
          )
        })}
      </div>

      {!loading && templates.length === 0 && (
        <div className="text-center py-12 text-gray-400 text-sm">
          이메일 템플릿이 없습니다. 위의 버튼으로 생성하세요.
        </div>
      )}
    </div>
  )
}
