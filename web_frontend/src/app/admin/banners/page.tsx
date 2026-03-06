'use client'

/**
 * /admin/banners — 배너 관리
 * 목록, 추가, 활성/비활성 토글
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL

interface Banner {
  id: number
  image_url: string
  link_url: string | null
  position: string
  is_active: number
  sort_order: number
  created_at: string
}

const POSITIONS = ['main_top', 'board_top', 'sidebar'] as const
const positionLabel = (p: string) => {
  const map: Record<string, string> = { main_top: '메인 상단', board_top: '게시판 상단', sidebar: '사이드바' }
  return map[p] ?? p
}

export default function AdminBannersPage() {
  const { authed, login, headers, signedFetch, waking } = useAdminAuth()

  const [banners, setBanners] = useState<Banner[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  // New banner form
  const [showForm, setShowForm] = useState(false)
  const [newImageUrl, setNewImageUrl] = useState('')
  const [newLinkUrl, setNewLinkUrl] = useState('')
  const [newPosition, setNewPosition] = useState<string>('main_top')
  const [newOrder, setNewOrder] = useState(0)
  const [creating, setCreating] = useState(false)

  // Edit state
  const [editId, setEditId] = useState<number | null>(null)
  const [editImageUrl, setEditImageUrl] = useState('')
  const [editLinkUrl, setEditLinkUrl] = useState('')
  const [editPosition, setEditPosition] = useState('')
  const [editOrder, setEditOrder] = useState(0)
  const [saving, setSaving] = useState(false)

  const fetchBanners = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/banners`, { headers: headers() })
      if (res.status === 403) {
        const errBody = await res.json().catch(() => ({}))
        if (errBody.error?.includes?.('Access denied')) {
          setError('일시적으로 차단되었습니다. 자동 재시도 중...')
          const k = localStorage.getItem('bridge_admin_key') || ''
          await fetch(`${API}/api/admin/reset-blacklist`, { method: 'POST', headers: { 'x-admin-key': k } }).catch(() => {})
          setTimeout(() => window.location.reload(), 3000)
          return
        }
        setError('관리자 키가 올바르지 않습니다. 다시 로그인해주세요.')
        localStorage.removeItem('bridge_admin_key')
        return
      }
      const json = await res.json()
      if (json.success && json.data?.banners) {
        setBanners(json.data.banners)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => {
    if (authed) fetchBanners()
  }, [authed, fetchBanners])

  const handleCreate = async () => {
    if (!newImageUrl.trim()) { setActionMsg('이미지 URL을 입력하세요.'); return }
    setCreating(true)
    try {
      const bodyStr = JSON.stringify({
        image_url: newImageUrl.trim(),
        link_url: newLinkUrl.trim() || null,
        position: newPosition,
        sort_order: newOrder,
      })
      const res = await signedFetch(`${API}/api/admin/banners`, {
        method: 'POST',
        body: bodyStr,
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`배너 #${json.data.id} 생성 완료`)
      setNewImageUrl(''); setNewLinkUrl(''); setNewPosition('main_top'); setNewOrder(0); setShowForm(false)
      fetchBanners()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    } finally {
      setCreating(false)
    }
  }

  const startEdit = (b: Banner) => {
    setEditId(b.id)
    setEditImageUrl(b.image_url)
    setEditLinkUrl(b.link_url ?? '')
    setEditPosition(b.position)
    setEditOrder(b.sort_order)
  }

  const handleEdit = async () => {
    if (!editImageUrl.trim()) { setActionMsg('이미지 URL을 입력하세요.'); return }
    setSaving(true)
    try {
      const bodyStr = JSON.stringify({
        image_url: editImageUrl.trim(),
        link_url: editLinkUrl.trim() || null,
        position: editPosition,
        sort_order: editOrder,
      })
      const res = await signedFetch(`${API}/api/admin/banners/${editId}`, {
        method: 'PUT',
        body: bodyStr,
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`배너 #${editId} 수정 완료`)
      setEditId(null)
      fetchBanners()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    } finally {
      setSaving(false)
    }
  }

  const toggleActive = async (b: Banner) => {
    try {
      const newActive = b.is_active === 1 ? 0 : 1
      const bodyStr = JSON.stringify({ is_active: newActive })
      const res = await signedFetch(`${API}/api/admin/banners/${b.id}`, {
        method: 'PUT',
        body: bodyStr,
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`배너 #${b.id} ${newActive ? '활성화' : '비활성화'}`)
      fetchBanners()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="space-y-6">

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">배너 관리</h1>
          <p className="text-gray-500 text-sm">{banners.length} banners</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => setShowForm(!showForm)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              showForm ? 'bg-gray-200 text-gray-700' : 'bg-[#1d1d1f] text-white hover:bg-[#424245]'
            }`}>
            {showForm ? '취소' : '+ 새 배너'}
          </button>
          <button type="button" onClick={fetchBanners} className="text-sm text-blue-600 hover:underline px-2">↻ 새로고침</button>
        </div>
      </div>

      {/* New Banner Form */}
      {showForm && (
        <div className="card border-2 border-blue-200 bg-blue-50/30 space-y-4">
          <h2 className="font-bold text-gray-900">새 배너 추가</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-500 mb-1">이미지 URL</label>
              <input value={newImageUrl} onChange={(e) => setNewImageUrl(e.target.value)}
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="https://example.com/banner.jpg" maxLength={500} />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-500 mb-1">링크 URL (선택)</label>
              <input value={newLinkUrl} onChange={(e) => setNewLinkUrl(e.target.value)}
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="https://example.com/page" maxLength={500} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">위치</label>
              <select value={newPosition} onChange={(e) => setNewPosition(e.target.value)}
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
                {POSITIONS.map((p) => <option key={p} value={p}>{positionLabel(p)}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">정렬 순서</label>
              <input type="number" value={newOrder} onChange={(e) => setNewOrder(parseInt(e.target.value) || 0)}
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
          </div>
          {newImageUrl && (
            <div className="border rounded-lg p-2 bg-gray-50">
              <p className="text-xs text-gray-400 mb-1">미리보기</p>
              <img src={newImageUrl} alt="preview" className="max-h-32 rounded" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
            </div>
          )}
          <div className="flex justify-end">
            <button type="button" onClick={handleCreate} disabled={creating}
              className="px-6 py-2 rounded-full bg-[#1d1d1f] text-white text-sm font-medium hover:bg-[#424245] disabled:opacity-50 transition-colors">
              {creating ? '생성 중...' : '생성하기'}
            </button>
          </div>
        </div>
      )}

      {actionMsg && (
        <div className="card-flat bg-blue-50 border-blue-200 text-sm text-blue-700 flex justify-between items-center">
          <span>{actionMsg}</span>
          <button type="button" onClick={() => setActionMsg(null)} className="text-blue-500 hover:text-blue-700">×</button>
        </div>
      )}

      {loading ? (
        <div className="text-center py-16 text-gray-400 animate-pulse">로딩 중...</div>
      ) : error ? (
        <div className="text-center py-16 text-red-500">{error}</div>
      ) : banners.length === 0 ? (
        <div className="text-center py-16 text-gray-400">등록된 배너가 없습니다.</div>
      ) : (
        <div className="space-y-2">
          {banners.map((b) => (
            <div key={b.id}>
              <div className={`card !py-3 flex items-center gap-4 ${b.is_active === 0 ? 'opacity-50' : ''}`}>
                <div className="w-20 h-12 rounded overflow-hidden bg-gray-100 shrink-0 flex items-center justify-center">
                  <img src={b.image_url} alt={`banner-${b.id}`} className="max-w-full max-h-full object-cover"
                    onError={(e) => { (e.target as HTMLImageElement).replaceWith(document.createTextNode('No img')) }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="font-mono text-xs text-gray-400">#{b.id}</span>
                    <span className={`badge text-[10px] ${
                      b.position === 'main_top' ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                      b.position === 'board_top' ? 'bg-green-50 text-green-700 border border-green-200' :
                      'bg-purple-50 text-purple-700 border border-purple-200'
                    }`}>{positionLabel(b.position)}</span>
                  </div>
                  <p className="text-xs text-gray-500 truncate">{b.image_url}</p>
                  {b.link_url && <p className="text-xs text-blue-400 truncate">{b.link_url}</p>}
                </div>
                <span className="text-xs text-gray-400">순서: {b.sort_order}</span>
                <div className="flex gap-1 shrink-0">
                  <button type="button" onClick={() => startEdit(b)}
                    className="text-xs px-2 py-1 rounded border border-gray-200 hover:bg-gray-100 transition-colors">
                    ✏️
                  </button>
                  <button type="button" onClick={() => toggleActive(b)}
                    className={`text-xs px-2 py-1 rounded border transition-colors ${
                      b.is_active ? 'border-orange-200 text-orange-600 hover:bg-orange-50' : 'border-green-200 text-green-600 hover:bg-green-50'
                    }`}>
                    {b.is_active ? '비활성' : '활성'}
                  </button>
                </div>
              </div>

              {editId === b.id && (
                <div className="card border-2 border-yellow-200 bg-yellow-50/30 space-y-3 mt-1">
                  <h3 className="text-sm font-bold text-gray-700">배너 수정 #{b.id}</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="md:col-span-2">
                      <label className="block text-xs font-medium text-gray-500 mb-1">이미지 URL</label>
                      <input value={editImageUrl} onChange={(e) => setEditImageUrl(e.target.value)}
                        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
                        maxLength={500} />
                    </div>
                    <div className="md:col-span-2">
                      <label className="block text-xs font-medium text-gray-500 mb-1">링크 URL</label>
                      <input value={editLinkUrl} onChange={(e) => setEditLinkUrl(e.target.value)}
                        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
                        maxLength={500} />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">위치</label>
                      <select value={editPosition} onChange={(e) => setEditPosition(e.target.value)}
                        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400">
                        {POSITIONS.map((p) => <option key={p} value={p}>{positionLabel(p)}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">정렬 순서</label>
                      <input type="number" value={editOrder} onChange={(e) => setEditOrder(parseInt(e.target.value) || 0)}
                        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400" />
                    </div>
                  </div>
                  <div className="flex gap-2 justify-end">
                    <button type="button" onClick={() => setEditId(null)}
                      className="px-4 py-2 text-gray-600 bg-gray-100 rounded-lg text-sm hover:bg-gray-200">
                      취소
                    </button>
                    <button type="button" onClick={handleEdit} disabled={saving}
                      className="px-4 py-2 bg-yellow-500 text-white rounded-lg text-sm font-medium hover:bg-yellow-600 disabled:opacity-50">
                      {saving ? '저장 중...' : '수정 저장'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
