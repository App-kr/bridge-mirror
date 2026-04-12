'use client'

/**
 * /admin/boards — 게시판 관리
 * 목록, 추가/수정, 순서 변경, 숨김 토글
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL

interface Board {
  id: string
  label: string
  label_kr: string | null
  display_mode: string
  sort_order: number
  is_hidden: number
  created_at: string
}

const DISPLAY_MODES = ['list', 'card', 'gallery'] as const

export default function AdminBoardsPage() {
  const { authed, login, headers, signedFetch, waking } = useAdminAuth()

  const [boards, setBoards] = useState<Board[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  // New board form
  const [showForm, setShowForm] = useState(false)
  const [newId, setNewId] = useState('')
  const [newLabel, setNewLabel] = useState('')
  const [newLabelKr, setNewLabelKr] = useState('')
  const [newMode, setNewMode] = useState<string>('list')
  const [creating, setCreating] = useState(false)

  // Edit state
  const [editId, setEditId] = useState<string | null>(null)
  const [editLabel, setEditLabel] = useState('')
  const [editLabelKr, setEditLabelKr] = useState('')
  const [editMode, setEditMode] = useState('')
  const [editOrder, setEditOrder] = useState(0)
  const [saving, setSaving] = useState(false)

  const fetchBoards = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/boards`, { headers: headers() })
      const json = await res.json()
      if (res.status === 403) {
        if (json.error?.includes?.('Access denied')) {
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
      if (json.success && json.data?.boards) {
        setBoards(json.data.boards)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => {
    if (authed) fetchBoards()
  }, [authed, fetchBoards])

  const handleCreate = async () => {
    if (!newId.trim() || !newLabel.trim()) { setActionMsg('ID와 표시명을 입력하세요.'); return }
    if (!/^[a-z0-9_]+$/.test(newId)) { setActionMsg('ID는 영소문자, 숫자, _ 만 가능합니다.'); return }
    setCreating(true)
    try {
      const bodyStr = JSON.stringify({ id: newId.trim(), label: newLabel.trim(), label_kr: newLabelKr.trim() || null, display_mode: newMode })
      const res = await signedFetch(`${API}/api/admin/boards`, {
        method: 'POST',
        body: bodyStr,
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`게시판 '${newId}' 생성 완료`)
      setNewId(''); setNewLabel(''); setNewLabelKr(''); setNewMode('list'); setShowForm(false)
      fetchBoards()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    } finally {
      setCreating(false)
    }
  }

  const startEdit = (b: Board) => {
    setEditId(b.id)
    setEditLabel(b.label)
    setEditLabelKr(b.label_kr ?? '')
    setEditMode(b.display_mode)
    setEditOrder(b.sort_order)
  }

  const handleEdit = async () => {
    if (!editLabel.trim()) { setActionMsg('표시명을 입력하세요.'); return }
    setSaving(true)
    try {
      const bodyStr = JSON.stringify({
        label: editLabel.trim(),
        label_kr: editLabelKr.trim() || null,
        display_mode: editMode,
        sort_order: editOrder,
      })
      const res = await signedFetch(`${API}/api/admin/boards/${editId}`, {
        method: 'PUT',
        body: bodyStr,
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`게시판 '${editId}' 수정 완료`)
      setEditId(null)
      fetchBoards()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    } finally {
      setSaving(false)
    }
  }

  const toggleHidden = async (b: Board) => {
    try {
      const newHidden = b.is_hidden === 1 ? 0 : 1
      const bodyStr = JSON.stringify({ is_hidden: newHidden })
      const res = await signedFetch(`${API}/api/admin/boards/${b.id}`, {
        method: 'PUT',
        body: bodyStr,
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail ?? 'Failed')
      setActionMsg(`게시판 '${b.id}' ${newHidden ? '숨김' : '공개'} 처리`)
      fetchBoards()
    } catch (e) {
      setActionMsg(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="space-y-6">

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">게시판 관리</h1>
          <p className="text-gray-500 text-sm">{boards.length} boards</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => setShowForm(!showForm)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              showForm ? 'bg-gray-200 text-gray-700' : 'bg-[#1d1d1f] text-white hover:bg-[#424245]'
            }`}>
            {showForm ? '취소' : '+ 새 게시판'}
          </button>
          <button type="button" onClick={fetchBoards} className="text-sm text-blue-600 hover:underline px-2">↻ 새로고침</button>
        </div>
      </div>

      {/* New Board Form */}
      {showForm && (
        <div className="card border-2 border-blue-200 bg-blue-50/30 space-y-4">
          <h2 className="font-bold text-gray-900">새 게시판 추가</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">ID (slug)</label>
              <input value={newId} onChange={(e) => setNewId(e.target.value)}
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="예: notices" maxLength={50} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">표시명 (EN)</label>
              <input value={newLabel} onChange={(e) => setNewLabel(e.target.value)}
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="예: Notices" maxLength={100} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">표시명 (KR)</label>
              <input value={newLabelKr} onChange={(e) => setNewLabelKr(e.target.value)}
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="예: 공지사항" maxLength={100} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">표시 형식</label>
              <select value={newMode} onChange={(e) => setNewMode(e.target.value)}
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
                {DISPLAY_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
          </div>
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
      ) : boards.length === 0 ? (
        <div className="text-center py-16 text-gray-400">등록된 게시판이 없습니다.</div>
      ) : (
        <div className="space-y-2">
          {boards.map((b) => (
            <div key={b.id}>
              <div className={`card !py-3 flex items-center gap-4 ${b.is_hidden ? 'opacity-50' : ''}`}>
                <div className="font-mono text-sm text-gray-500 w-28 shrink-0">{b.id}</div>
                <div className="flex-1 min-w-0">
                  <span className="font-semibold text-gray-900">{b.label}</span>
                  {b.label_kr && <span className="text-gray-400 text-sm ml-2">({b.label_kr})</span>}
                </div>
                <span className="badge bg-gray-100 text-gray-600 text-xs">{b.display_mode}</span>
                <span className="text-xs text-gray-400">순서: {b.sort_order}</span>
                <div className="flex gap-1 shrink-0">
                  <button type="button" onClick={() => startEdit(b)}
                    className="admin-btn admin-btn-edit">
                    ✏️ 수정
                  </button>
                  <button type="button" onClick={() => toggleHidden(b)}
                    className={`text-xs px-2 py-1 rounded border transition-colors ${
                      b.is_hidden ? 'border-green-200 text-green-600 hover:bg-green-50' : 'border-orange-200 text-orange-600 hover:bg-orange-50'
                    }`}>
                    {b.is_hidden ? '공개' : '숨김'}
                  </button>
                </div>
              </div>

              {editId === b.id && (
                <div className="card border-2 border-yellow-200 bg-yellow-50/30 space-y-3 mt-1">
                  <h3 className="text-sm font-bold text-gray-700">게시판 수정: {b.id}</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">표시명 (EN)</label>
                      <input value={editLabel} onChange={(e) => setEditLabel(e.target.value)}
                        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
                        maxLength={100} />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">표시명 (KR)</label>
                      <input value={editLabelKr} onChange={(e) => setEditLabelKr(e.target.value)}
                        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
                        maxLength={100} />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">표시 형식</label>
                      <select value={editMode} onChange={(e) => setEditMode(e.target.value)}
                        className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400">
                        {DISPLAY_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
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
                      className="admin-btn admin-btn-cancel">
                      ✕ 취소
                    </button>
                    <button type="button" onClick={handleEdit} disabled={saving}
                      className="admin-btn admin-btn-save">
                      {saving ? '저장 중...' : '💾 저장'}
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
