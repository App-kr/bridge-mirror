'use client'

/**
 * /admin/partners — 파트너 관리
 * CRUD, 활성/비활성 토글, 카테고리 필터
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL

interface Partner {
  id: number
  name: string
  category: string
  logo_url: string | null
  website: string | null
  sort_order: number
  is_active: number
  created_at: string
  updated_at: string
}

export default function AdminPartnersPage() {
  const { authed, login, headers, signedFetch, waking } = useAdminAuth()

  const [partners, setPartners] = useState<Partner[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'academy' | 'school'>('all')

  // New partner form
  const [showForm, setShowForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [newCategory, setNewCategory] = useState<'academy' | 'school'>('academy')
  const [newWebsite, setNewWebsite] = useState('')
  const [creating, setCreating] = useState(false)

  // Edit state
  const [editId, setEditId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [editCategory, setEditCategory] = useState<'academy' | 'school'>('academy')
  const [editWebsite, setEditWebsite] = useState('')
  const [saving, setSaving] = useState(false)

  const fetchPartners = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/admin/partners`, { headers: headers() })
      if (!res.ok) {
        setError('데이터 로딩 실패')
        return
      }
      const json = await res.json()
      if (json.success && json.data?.partners) {
        setPartners(json.data.partners)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => {
    if (authed) fetchPartners()
  }, [authed, fetchPartners])

  const showMsg = (msg: string) => {
    setActionMsg(msg)
    setTimeout(() => setActionMsg(null), 3000)
  }

  const handleCreate = async () => {
    if (!newName.trim()) return
    setCreating(true)
    try {
      const res = await signedFetch(`${API}/api/admin/partners`, {
        method: 'POST',
        body: JSON.stringify({ name: newName.trim(), category: newCategory, website: newWebsite.trim() || null }),
      })
      if (res.ok) {
        showMsg('파트너 추가 완료')
        setNewName('')
        setNewWebsite('')
        setShowForm(false)
        fetchPartners()
      } else {
        const j = await res.json().catch(() => ({}))
        showMsg(j.detail || '추가 실패')
      }
    } catch {
      showMsg('네트워크 오류')
    } finally {
      setCreating(false)
    }
  }

  const handleToggleActive = async (partner: Partner) => {
    try {
      const res = await signedFetch(`${API}/api/admin/partners/${partner.id}`, {
        method: 'PUT',
        body: JSON.stringify({ is_active: partner.is_active ? 0 : 1 }),
      })
      if (res.ok) {
        showMsg(partner.is_active ? '비활성화 완료' : '활성화 완료')
        fetchPartners()
      }
    } catch {
      showMsg('변경 실패')
    }
  }

  const handleDelete = async (partner: Partner) => {
    if (!confirm(`"${partner.name}" 파트너를 삭제하시겠습니까?`)) return
    try {
      const res = await signedFetch(`${API}/api/admin/partners/${partner.id}`, {
        method: 'DELETE',
      })
      if (res.ok) {
        showMsg('삭제 완료')
        fetchPartners()
      }
    } catch {
      showMsg('삭제 실패')
    }
  }

  const startEdit = (partner: Partner) => {
    setEditId(partner.id)
    setEditName(partner.name)
    setEditCategory(partner.category as 'academy' | 'school')
    setEditWebsite(partner.website || '')
  }

  const handleSaveEdit = async () => {
    if (editId === null || !editName.trim()) return
    setSaving(true)
    try {
      const res = await signedFetch(`${API}/api/admin/partners/${editId}`, {
        method: 'PUT',
        body: JSON.stringify({ name: editName.trim(), category: editCategory, website: editWebsite.trim() || null }),
      })
      if (res.ok) {
        showMsg('수정 완료')
        setEditId(null)
        fetchPartners()
      }
    } catch {
      showMsg('수정 실패')
    } finally {
      setSaving(false)
    }
  }

  if (!authed) {
    return <AdminAuth onLogin={login} waking={waking} />
  }

  const filtered = filter === 'all' ? partners : partners.filter(p => p.category === filter)
  const academyCount = partners.filter(p => p.category === 'academy').length
  const schoolCount = partners.filter(p => p.category === 'school').length

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[22px] font-bold text-[#1d1d1f] tracking-tight">파트너 관리</h1>
          <p className="text-[13px] text-[#86868b] mt-1">
            총 {partners.length}개 (학원 {academyCount} · 학교 {schoolCount})
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-[#0071e3] text-white text-[13px] font-semibold rounded-lg hover:bg-[#0077ED] transition-colors"
        >
          + 파트너 추가
        </button>
      </div>

      {/* Action message */}
      {actionMsg && (
        <div className="mb-4 px-4 py-2.5 bg-green-50 border border-green-200 rounded-xl text-[13px] text-green-700 font-medium">
          {actionMsg}
        </div>
      )}

      {/* New partner form */}
      {showForm && (
        <div className="mb-6 bg-white rounded-2xl border border-[#e5e5e7] p-5">
          <h3 className="text-[15px] font-semibold text-[#1d1d1f] mb-4">새 파트너</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <input
              type="text"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              placeholder="파트너명"
              className="px-3 py-2 border border-[#d2d2d7] rounded-lg text-[14px] focus:outline-none focus:border-[#0071e3]"
            />
            <select
              value={newCategory}
              onChange={e => setNewCategory(e.target.value as 'academy' | 'school')}
              className="px-3 py-2 border border-[#d2d2d7] rounded-lg text-[14px] focus:outline-none focus:border-[#0071e3]"
            >
              <option value="academy">학원 (Academy)</option>
              <option value="school">학교 (School)</option>
            </select>
            <input
              type="text"
              value={newWebsite}
              onChange={e => setNewWebsite(e.target.value)}
              placeholder="웹사이트 (선택)"
              className="px-3 py-2 border border-[#d2d2d7] rounded-lg text-[14px] focus:outline-none focus:border-[#0071e3]"
            />
          </div>
          <div className="flex gap-2 mt-4">
            <button
              type="button"
              onClick={handleCreate}
              disabled={creating || !newName.trim()}
              className="px-4 py-2 bg-[#0071e3] text-white text-[13px] font-semibold rounded-lg hover:bg-[#0077ED] transition-colors disabled:opacity-50"
            >
              {creating ? '저장 중...' : '추가'}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 bg-[#f5f5f7] text-[#1d1d1f] text-[13px] font-medium rounded-lg hover:bg-[#e8e8ed] transition-colors"
            >
              취소
            </button>
          </div>
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex gap-2 mb-5">
        {[
          { key: 'all' as const, label: `전체 (${partners.length})` },
          { key: 'academy' as const, label: `학원 (${academyCount})` },
          { key: 'school' as const, label: `학교 (${schoolCount})` },
        ].map(tab => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setFilter(tab.key)}
            className={`px-4 py-1.5 rounded-full text-[13px] font-medium transition-colors ${
              filter === tab.key
                ? 'bg-[#0071e3] text-white'
                : 'bg-white text-[#424245] border border-[#d2d2d7] hover:bg-[#f5f5f7]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-[13px] text-red-600">
          {error}
        </div>
      )}

      {/* Partners table */}
      <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-[#86868b] text-[14px]">로딩 중...</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-[#86868b] text-[14px]">파트너가 없습니다</div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-[#e5e5e7] bg-[#fafafa]">
                <th className="px-5 py-3 text-[12px] font-semibold text-[#86868b] uppercase tracking-wider">이름</th>
                <th className="px-5 py-3 text-[12px] font-semibold text-[#86868b] uppercase tracking-wider">카테고리</th>
                <th className="px-5 py-3 text-[12px] font-semibold text-[#86868b] uppercase tracking-wider">상태</th>
                <th className="px-5 py-3 text-[12px] font-semibold text-[#86868b] uppercase tracking-wider">순서</th>
                <th className="px-5 py-3 text-[12px] font-semibold text-[#86868b] uppercase tracking-wider text-right">액션</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(partner => (
                <tr key={partner.id} className={`border-b border-[#f0f0f2] hover:bg-[#fafafa] transition-colors ${!partner.is_active ? 'opacity-50' : ''}`}>
                  <td className="px-5 py-3">
                    {editId === partner.id ? (
                      <input
                        type="text"
                        value={editName}
                        onChange={e => setEditName(e.target.value)}
                        className="px-2 py-1 border border-[#d2d2d7] rounded text-[14px] w-full focus:outline-none focus:border-[#0071e3]"
                      />
                    ) : (
                      <span className="text-[14px] font-medium text-[#1d1d1f]">{partner.name}</span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    {editId === partner.id ? (
                      <select
                        value={editCategory}
                        onChange={e => setEditCategory(e.target.value as 'academy' | 'school')}
                        className="px-2 py-1 border border-[#d2d2d7] rounded text-[13px]"
                      >
                        <option value="academy">학원</option>
                        <option value="school">학교</option>
                      </select>
                    ) : (
                      <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
                        partner.category === 'school'
                          ? 'bg-blue-50 text-blue-600'
                          : 'bg-orange-50 text-orange-600'
                      }`}>
                        {partner.category === 'school' ? '학교' : '학원'}
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <button
                      type="button"
                      onClick={() => handleToggleActive(partner)}
                      className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold cursor-pointer transition-colors ${
                        partner.is_active
                          ? 'bg-green-50 text-green-600 hover:bg-green-100'
                          : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                      }`}
                    >
                      {partner.is_active ? '활성' : '비활성'}
                    </button>
                  </td>
                  <td className="px-5 py-3 text-[13px] text-[#86868b]">{partner.sort_order}</td>
                  <td className="px-5 py-3 text-right">
                    {editId === partner.id ? (
                      <div className="flex gap-1 justify-end">
                        <button
                          type="button"
                          onClick={handleSaveEdit}
                          disabled={saving}
                          className="px-3 py-1 bg-[#0071e3] text-white text-[12px] font-semibold rounded-md hover:bg-[#0077ED] transition-colors disabled:opacity-50"
                        >
                          {saving ? '...' : '저장'}
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditId(null)}
                          className="px-3 py-1 bg-[#f5f5f7] text-[#424245] text-[12px] font-medium rounded-md hover:bg-[#e8e8ed] transition-colors"
                        >
                          취소
                        </button>
                      </div>
                    ) : (
                      <div className="flex gap-1 justify-end">
                        <button
                          type="button"
                          onClick={() => startEdit(partner)}
                          className="px-3 py-1 bg-[#f5f5f7] text-[#424245] text-[12px] font-medium rounded-md hover:bg-[#e8e8ed] transition-colors"
                        >
                          수정
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(partner)}
                          className="px-3 py-1 bg-red-50 text-red-500 text-[12px] font-medium rounded-md hover:bg-red-100 transition-colors"
                        >
                          삭제
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
