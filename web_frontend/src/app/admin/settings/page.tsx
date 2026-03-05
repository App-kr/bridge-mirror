'use client'

/**
 * /admin/settings — 사이트 설정
 * 회사 정보, 연락처, SNS, 푸터 텍스트 관리
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL

interface SettingsMap {
  [key: string]: string
}

const SETTING_GROUPS = [
  {
    title: '회사 정보',
    fields: [
      { key: 'company_name', label: '회사명', placeholder: 'BRIDGE Agency' },
      { key: 'ceo_name', label: '대표자', placeholder: '홍길동' },
      { key: 'business_number', label: '사업자등록번호', placeholder: '000-00-00000' },
      { key: 'address', label: '주소', placeholder: '서울시 강남구...' },
    ],
  },
  {
    title: '연락처',
    fields: [
      { key: 'contact_email', label: '이메일', placeholder: 'bridgejobkr@gmail.com' },
      { key: 'contact_phone', label: '전화번호', placeholder: '010-0000-0000' },
    ],
  },
  {
    title: 'SNS',
    fields: [
      { key: 'kakao_channel', label: '카카오 채널', placeholder: 'https://pf.kakao.com/...' },
      { key: 'instagram', label: 'Instagram', placeholder: 'https://instagram.com/...' },
      { key: 'facebook', label: 'Facebook', placeholder: 'https://facebook.com/...' },
      { key: 'youtube', label: 'YouTube', placeholder: 'https://youtube.com/...' },
      { key: 'blog', label: '블로그', placeholder: 'https://blog.naver.com/...' },
    ],
  },
  {
    title: '푸터',
    fields: [
      { key: 'footer_description', label: '설명', placeholder: 'Korea ESL Recruitment Platform' },
      { key: 'footer_text', label: '저작권 문구', placeholder: '© 2026 BRIDGE Recruitment · bridgejob.co.kr' },
    ],
  },
]

export default function AdminSettingsPage() {
  const { authed, login, headers, signedFetch, waking } = useAdminAuth()

  const [settings, setSettings] = useState<SettingsMap>({})
  const [original, setOriginal] = useState<SettingsMap>({})
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  const fetchSettings = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API}/api/admin/settings`, { headers: headers() })
      if (!res.ok) return
      const json = await res.json()
      if (json.success && json.data?.settings) {
        const flat: SettingsMap = {}
        for (const [key, val] of Object.entries(json.data.settings)) {
          flat[key] = (val as { value: string }).value || ''
        }
        setSettings(flat)
        setOriginal(flat)
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => {
    if (authed) fetchSettings()
  }, [authed, fetchSettings])

  const hasChanges = () => {
    return Object.keys(settings).some(k => settings[k] !== (original[k] || ''))
  }

  const handleSave = async () => {
    const changed: SettingsMap = {}
    for (const [key, value] of Object.entries(settings)) {
      if (value !== (original[key] || '')) {
        changed[key] = value
      }
    }
    if (Object.keys(changed).length === 0) return

    setSaving(true)
    try {
      const res = await signedFetch(`${API}/api/admin/settings`, {
        method: 'PUT',
        body: JSON.stringify({ settings: changed }),
      })
      if (res.ok) {
        setActionMsg('저장 완료')
        setOriginal({ ...settings })
        setTimeout(() => setActionMsg(null), 3000)
      } else {
        setActionMsg('저장 실패')
        setTimeout(() => setActionMsg(null), 3000)
      }
    } catch {
      setActionMsg('네트워크 오류')
      setTimeout(() => setActionMsg(null), 3000)
    } finally {
      setSaving(false)
    }
  }

  if (!authed) {
    return <AdminAuth onLogin={login} waking={waking} />
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[22px] font-bold text-[#1d1d1f] tracking-tight">사이트 설정</h1>
          <p className="text-[13px] text-[#86868b] mt-1">회사 정보, 연락처, SNS, 푸터 텍스트를 관리합니다</p>
        </div>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !hasChanges()}
          className="px-5 py-2 bg-[#0071e3] text-white text-[13px] font-semibold rounded-lg hover:bg-[#0077ED] transition-colors disabled:opacity-50"
        >
          {saving ? '저장 중...' : '변경사항 저장'}
        </button>
      </div>

      {/* Action message */}
      {actionMsg && (
        <div className="mb-4 px-4 py-2.5 bg-green-50 border border-green-200 rounded-xl text-[13px] text-green-700 font-medium">
          {actionMsg}
        </div>
      )}

      {loading ? (
        <div className="p-8 text-center text-[#86868b] text-[14px]">로딩 중...</div>
      ) : (
        <div className="space-y-6">
          {SETTING_GROUPS.map(group => (
            <div key={group.title} className="bg-white rounded-2xl border border-[#e5e5e7] p-6">
              <h3 className="text-[15px] font-semibold text-[#1d1d1f] mb-4">{group.title}</h3>
              <div className="space-y-4">
                {group.fields.map(field => (
                  <div key={field.key} className="flex flex-col sm:flex-row sm:items-center gap-2">
                    <label className="text-[13px] font-medium text-[#424245] w-[140px] shrink-0">
                      {field.label}
                    </label>
                    <input
                      type="text"
                      value={settings[field.key] || ''}
                      onChange={e => setSettings(prev => ({ ...prev, [field.key]: e.target.value }))}
                      placeholder={field.placeholder}
                      className={`flex-1 px-3 py-2 border rounded-lg text-[14px] focus:outline-none focus:border-[#0071e3] transition-colors ${
                        settings[field.key] !== (original[field.key] || '')
                          ? 'border-[#0071e3] bg-blue-50/30'
                          : 'border-[#d2d2d7]'
                      }`}
                    />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
