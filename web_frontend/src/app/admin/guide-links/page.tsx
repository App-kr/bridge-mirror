'use client'

/**
 * /admin/guide-links — 가이드 링크 관리
 * guide_links 테이블 편집.
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL

interface GuideLink {
  link_key:   string
  url:        string
  label:      string | null
  updated_at: string | null
}

export default function GuideLinksPage() {
  const { adminKey, authed, login, waking } = useAdminAuth()

  const [links, setLinks] = useState<GuideLink[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saveMsg, setSaveMsg] = useState('')
  const [newKey, setNewKey] = useState('')
  const [newUrl, setNewUrl] = useState('')
  const [newLabel, setNewLabel] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/guide-links`, {
        headers: { 'x-admin-key': adminKey },
      })
      const json = await res.json()
      if (res.status === 403) {
        const errBody = await res.json().catch(() => ({}))
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
      if (!res.ok || !json.success) throw new Error(json.detail ?? 'Error')
      setLinks(json.data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '데이터 로드 실패')
    } finally {
      setLoading(false)
    }
  }, [adminKey])

  useEffect(() => {
    if (authed) fetchData()
  }, [authed, fetchData])

  const handleSave = useCallback(async (linkKey: string, url: string, label: string) => {
    try {
      const res = await fetch(`${API}/api/admin/guide-links/${linkKey}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body: JSON.stringify({ url, label }),
      })
      if (!res.ok) throw new Error('저장 실패')
      setSaveMsg(`"${linkKey}" 저장됨`)
      setTimeout(() => setSaveMsg(''), 3000)
      fetchData()
    } catch (e) {
      setSaveMsg('저장 실패: ' + (e instanceof Error ? e.message : ''))
    }
  }, [adminKey, fetchData])

  const handleAdd = useCallback(async () => {
    if (!newKey.trim() || !newUrl.trim()) return
    await handleSave(newKey.trim(), newUrl.trim(), newLabel.trim())
    setNewKey('')
    setNewUrl('')
    setNewLabel('')
  }, [newKey, newUrl, newLabel, handleSave])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="max-w-[1000px] mx-auto px-4 py-6">

      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-lg font-bold text-gray-900">가이드 링크 관리</h1>
          <p className="text-xs text-gray-500">
            {loading ? '로딩 중…' : `${links.length}개 링크`}
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

      {/* Links Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden mb-4">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500">
            <tr>
              <th className="px-3 py-2 text-left w-48">키</th>
              <th className="px-3 py-2 text-left">URL</th>
              <th className="px-3 py-2 text-left w-40">라벨</th>
              <th className="px-3 py-2 text-left w-20">저장</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {links.map((link) => (
              <LinkRow key={link.link_key} link={link} onSave={handleSave} />
            ))}
          </tbody>
        </table>
      </div>

      {/* Add new */}
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <p className="text-xs font-medium text-gray-600 mb-2">새 링크 추가</p>
        <div className="flex gap-2">
          <input className="border border-gray-300 rounded-lg px-3 py-1.5 text-xs w-40"
            placeholder="link_key" value={newKey} onChange={(e) => setNewKey(e.target.value)} />
          <input className="border border-gray-300 rounded-lg px-3 py-1.5 text-xs flex-1"
            placeholder="https://..." value={newUrl} onChange={(e) => setNewUrl(e.target.value)} />
          <input className="border border-gray-300 rounded-lg px-3 py-1.5 text-xs w-32"
            placeholder="라벨" value={newLabel} onChange={(e) => setNewLabel(e.target.value)} />
          <button type="button"
            className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            onClick={handleAdd}>추가</button>
        </div>
      </div>
    </div>
  )
}

function LinkRow({ link, onSave }: { link: GuideLink; onSave: (key: string, url: string, label: string) => void }) {
  const [url, setUrl] = useState(link.url)
  const [label, setLabel] = useState(link.label ?? '')
  const changed = url !== link.url || label !== (link.label ?? '')

  return (
    <tr>
      <td className="px-3 py-2 font-mono text-xs text-gray-600">{link.link_key}</td>
      <td className="px-3 py-2">
        <input className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
          value={url} onChange={(e) => setUrl(e.target.value)} />
      </td>
      <td className="px-3 py-2">
        <input className="w-full border border-gray-200 rounded px-2 py-1 text-xs"
          value={label} onChange={(e) => setLabel(e.target.value)} />
      </td>
      <td className="px-3 py-2">
        {changed && (
          <button type="button"
            className="text-xs text-blue-600 font-medium hover:underline"
            onClick={() => onSave(link.link_key, url, label)}>저장</button>
        )}
      </td>
    </tr>
  )
}
