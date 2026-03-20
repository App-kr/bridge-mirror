'use client'

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

const API = API_URL

interface SecretMeta {
  key: string
  description: string
  updated_at: string
}

const KAKAO_FIELDS = [
  {
    key: 'KAKAO_CLIENT_ID',
    label: 'REST API 키',
    hint: 'developers.kakao.com → 내 애플리케이션 → 앱 설정 → 앱 키 → REST API 키',
  },
  {
    key: 'KAKAO_ADMIN_IDS',
    label: '관리자 카카오 ID',
    hint: '숫자로 된 본인 카카오 계정 ID — 아래 "내 ID 확인" 버튼으로 확인 가능',
  },
]

export default function KakaoSetupPage() {
  const { authed, login, headers, signedFetch, waking } = useAdminAuth()

  const [secrets, setSecrets] = useState<SecretMeta[]>([])
  const [values, setValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [msgs, setMsgs] = useState<Record<string, { text: string; ok: boolean }>>({})
  const [detectedId, setDetectedId] = useState<string | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    const kid = params.get('kakao_id')
    if (kid) {
      window.history.replaceState({}, '', window.location.pathname)
      setDetectedId(kid)
      setValues(prev => ({ ...prev, KAKAO_ADMIN_IDS: kid }))
    }
  }, [])

  const showMsg = (key: string, text: string, ok = true) => {
    setMsgs(prev => ({ ...prev, [key]: { text, ok } }))
    setTimeout(() => setMsgs(prev => { const n = { ...prev }; delete n[key]; return n }), 3000)
  }

  const fetchSecrets = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/admin/secrets`, { headers: headers() })
      if (!res.ok) return
      const json = await res.json()
      setSecrets(json.data?.secrets || [])
    } catch { /* ignore */ }
  }, [headers])

  useEffect(() => {
    if (authed) fetchSecrets()
  }, [authed, fetchSecrets])

  const handleSave = async (key: string, label: string) => {
    const value = values[key]?.trim()
    if (!value) { showMsg(key, '값을 입력하세요', false); return }
    setSaving(prev => ({ ...prev, [key]: true }))
    try {
      const res = await signedFetch(`${API}/api/admin/secrets`, {
        method: 'POST',
        body: JSON.stringify({ key, value, description: label }),
      })
      const json = await res.json()
      if (res.ok) {
        showMsg(key, '저장 완료 ✓')
        setValues(prev => ({ ...prev, [key]: '' }))
        fetchSecrets()
      } else {
        showMsg(key, json.detail || '저장 실패', false)
      }
    } catch { showMsg(key, '네트워크 오류', false) }
    finally { setSaving(prev => ({ ...prev, [key]: false })) }
  }

  const handleDelete = async (key: string) => {
    if (!confirm(`'${key}' 삭제?`)) return
    try {
      await signedFetch(`${API}/api/admin/secrets/${encodeURIComponent(key)}`, { method: 'DELETE' })
      fetchSecrets()
    } catch { /* ignore */ }
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  return (
    <div className="max-w-xl">
      <div className="mb-6">
        <h1 className="text-[22px] font-bold text-[#1d1d1f] tracking-tight">카카오 로그인 설정</h1>
        <p className="text-[13px] text-[#86868b] mt-1">2개 키를 등록하면 카카오로 관리자 로그인이 활성화됩니다</p>
      </div>

      {/* Redirect URI 안내 */}
      <div className="mb-6 p-4 bg-[#f5f5f7] rounded-2xl text-[13px] text-[#424245]">
        <p className="font-semibold mb-1">카카오 콘솔에서 먼저 설정:</p>
        <p className="mb-1">카카오 로그인 → <strong>활성화 ON</strong> → Redirect URI 추가:</p>
        <code className="block bg-white px-3 py-2 rounded-lg text-[12px] font-mono text-[#0071e3] break-all select-all">
          https://bridge-n7hk.onrender.com/api/admin/kakao/callback
        </code>
      </div>

      {/* 감지된 카카오 ID 배너 */}
      {detectedId && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-2xl">
          <p className="text-[13px] font-semibold text-green-700 mb-1">✓ 카카오 ID 확인됨</p>
          <p className="text-[12px] text-green-600">아래 ②번 입력칸에 자동으로 채워졌습니다. 저장 버튼을 눌러주세요.</p>
          <code className="block mt-2 text-[15px] font-mono font-bold text-green-800 select-all">{detectedId}</code>
        </div>
      )}

      {/* 2개 고정 입력 */}
      <div className="space-y-4">
        {KAKAO_FIELDS.map((field, idx) => {
          const saved = secrets.find(s => s.key === field.key)
          const msg = msgs[field.key]
          const isIdField = field.key === 'KAKAO_ADMIN_IDS'
          return (
            <div key={field.key} className="bg-white border border-[#e5e5e7] rounded-2xl p-5">
              <div className="flex items-center gap-3 mb-1">
                <span className="w-6 h-6 rounded-full bg-[#0071e3] text-white flex items-center justify-center font-bold text-[12px] shrink-0">
                  {idx + 1}
                </span>
                <span className="text-[15px] font-semibold text-[#1d1d1f]">{field.label}</span>
                {saved && (
                  <span className="ml-auto text-[11px] text-green-600 bg-green-50 px-2.5 py-0.5 rounded-full font-semibold">
                    등록됨 ✓
                  </span>
                )}
              </div>
              <p className="text-[12px] text-[#86868b] ml-9 mb-3">{field.hint}</p>
              {isIdField && !saved && (
                <p className="text-[12px] text-[#0071e3] ml-9 mb-2">
                  ① REST API 키를 먼저 저장 → 아래 &quot;로그인으로 ID 확인&quot; 클릭 → 자동으로 채워집니다
                </p>
              )}
              <div className="flex gap-2">
                <input
                  type={isIdField ? 'text' : 'password'}
                  placeholder={saved ? '새 값으로 덮어쓰기' : (isIdField ? '숫자 ID (예: 1234567890)' : '값 입력 후 저장')}
                  value={values[field.key] || ''}
                  onChange={e => setValues(prev => ({ ...prev, [field.key]: e.target.value }))}
                  onKeyDown={e => { if (e.key === 'Enter') handleSave(field.key, field.label) }}
                  onCopy={isIdField ? undefined : e => e.preventDefault()}
                  onCut={isIdField ? undefined : e => e.preventDefault()}
                  onContextMenu={isIdField ? undefined : e => e.preventDefault()}
                  className="flex-1 px-3 py-2.5 border border-[#d2d2d7] rounded-xl text-[14px] focus:outline-none focus:border-[#0071e3] transition-colors"
                  autoComplete="new-password"
                  data-form-type="other"
                />
                <button
                  type="button"
                  onClick={() => handleSave(field.key, field.label)}
                  disabled={saving[field.key] || !values[field.key]?.trim()}
                  className="px-5 py-2.5 bg-[#0071e3] text-white rounded-xl text-[13px] font-semibold hover:bg-[#0077ed] disabled:opacity-40 transition-colors shrink-0"
                >
                  {saving[field.key] ? '저장...' : '저장'}
                </button>
                {saved && (
                  <button
                    type="button"
                    onClick={() => handleDelete(field.key)}
                    className="px-3 py-2.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-xl text-[13px] transition-colors shrink-0"
                  >
                    삭제
                  </button>
                )}
              </div>
              {isIdField && !saved && secrets.find(s => s.key === 'KAKAO_CLIENT_ID') && (
                <button
                  type="button"
                  onClick={() => { window.location.href = `${API}/api/admin/kakao/login` }}
                  className="mt-2 ml-9 flex items-center gap-1.5 text-[12px] font-medium text-[#7a5c00] bg-[#FEE500] px-3 py-1.5 rounded-lg hover:brightness-95 transition-all"
                >
                  <span>💬</span> 카카오로 로그인하여 ID 자동 확인
                </button>
              )}
              {msg && (
                <p className={`mt-2 text-[12px] font-medium ml-9 ${msg.ok ? 'text-green-600' : 'text-red-500'}`}>
                  {msg.text}
                </p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
