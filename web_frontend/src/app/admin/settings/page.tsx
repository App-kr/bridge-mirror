'use client'

/**
 * /admin/settings — 사이트 설정 (확장)
 * 사이트 이름, 네비게이션, CTA 버튼, 히어로, 회사 정보, 연락처, SNS, 푸터 관리
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import { Plus, Trash2, GripVertical, ChevronUp, ChevronDown } from 'lucide-react'

const API = API_URL

interface SettingsMap {
  [key: string]: string
}

interface SecretMeta {
  key: string
  description: string
  updated_at: string
}

interface NavItem {
  href: string
  label: string
}

interface CtaButton {
  href: string
  label: string
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

function parseJson<T>(val: string | undefined, fallback: T): T {
  if (!val) return fallback
  try { return JSON.parse(val) as T } catch { return fallback }
}

export default function AdminSettingsPage() {
  const { authed, login, headers, signedFetch, waking } = useAdminAuth()

  const [settings, setSettings] = useState<SettingsMap>({})
  const [original, setOriginal] = useState<SettingsMap>({})
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  // Secrets
  const [secrets, setSecrets] = useState<SecretMeta[]>([])
  const [kakaoValues, setKakaoValues] = useState<Record<string, string>>({})
  const [kakaoSaving, setKakaoSaving] = useState<Record<string, boolean>>({})
  const [kakaoMsg, setKakaoMsg] = useState<Record<string, { text: string; ok: boolean }>>({})

  const KAKAO_FIELDS = [
    { key: 'KAKAO_CLIENT_ID',     label: 'REST API 키',    hint: 'developers.kakao.com → 앱 키 → REST API 키' },
    { key: 'KAKAO_CLIENT_SECRET', label: 'Client Secret',  hint: '카카오 로그인 → 보안 탭 → Client Secret 코드' },
    { key: 'KAKAO_ADMIN_IDS',     label: '관리자 ID',      hint: '허용할 카카오 숫자 ID (콤마 구분, 예: 1234567890)' },
  ]

  const showKakaoMsg = (key: string, text: string, ok = true) => {
    setKakaoMsg(prev => ({ ...prev, [key]: { text, ok } }))
    setTimeout(() => setKakaoMsg(prev => { const n = { ...prev }; delete n[key]; return n }), 3000)
  }

  const fetchSecrets = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/admin/secrets`, { headers: headers() })
      if (!res.ok) return
      const json = await res.json()
      setSecrets(json.data?.secrets || [])
    } catch { /* ignore */ }
  }, [headers])

  const handleSaveKakaoKey = async (key: string, desc: string) => {
    const value = kakaoValues[key]?.trim()
    if (!value) { showKakaoMsg(key, '값을 입력하세요', false); return }
    setKakaoSaving(prev => ({ ...prev, [key]: true }))
    try {
      const res = await signedFetch(`${API}/api/admin/secrets`, {
        method: 'POST',
        body: JSON.stringify({ key, value, description: desc }),
      })
      const json = await res.json()
      if (res.ok) {
        showKakaoMsg(key, '저장 완료 ✓')
        setKakaoValues(prev => ({ ...prev, [key]: '' }))
        fetchSecrets()
      } else {
        showKakaoMsg(key, json.detail || '저장 실패', false)
      }
    } catch { showKakaoMsg(key, '네트워크 오류', false) }
    finally { setKakaoSaving(prev => ({ ...prev, [key]: false })) }
  }

  const handleDeleteSecret = async (key: string) => {
    if (!confirm(`'${key}' 를 삭제하시겠습니까?`)) return
    try {
      const res = await signedFetch(`${API}/api/admin/secrets/${encodeURIComponent(key)}`, { method: 'DELETE' })
      const json = await res.json()
      if (res.ok) { fetchSecrets() }
      else { alert(json.detail || '삭제 실패') }
    } catch { alert('네트워크 오류') }
  }

  // Nav menu items
  const [navItems, setNavItems] = useState<NavItem[]>([])
  const [navOriginal, setNavOriginal] = useState<string>('')

  // CTA buttons
  const [cta1, setCta1] = useState<CtaButton>({ href: '/apply', label: 'Apply' })
  const [cta2, setCta2] = useState<CtaButton>({ href: '/inquiry', label: '원어민채용의뢰' })
  const [ctaOriginal1, setCtaOriginal1] = useState<string>('')
  const [ctaOriginal2, setCtaOriginal2] = useState<string>('')

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

        // Parse nav_menu
        const navData = parseJson<NavItem[]>(flat.nav_menu, [])
        setNavItems(navData)
        setNavOriginal(flat.nav_menu || '')

        // Parse CTA buttons
        const c1 = parseJson<CtaButton>(flat.nav_cta_1, { href: '/apply', label: 'Apply' })
        const c2 = parseJson<CtaButton>(flat.nav_cta_2, { href: '/inquiry', label: '원어민채용의뢰' })
        setCta1(c1)
        setCta2(c2)
        setCtaOriginal1(flat.nav_cta_1 || '')
        setCtaOriginal2(flat.nav_cta_2 || '')
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => {
    if (authed) { fetchSettings(); fetchSecrets() }
  }, [authed, fetchSettings, fetchSecrets])

  const showMsg = (msg: string) => {
    setActionMsg(msg)
    setTimeout(() => setActionMsg(null), 3000)
  }

  // --- Generic settings save ---
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
        showMsg('저장 완료')
        setOriginal({ ...settings })
      } else {
        showMsg('저장 실패')
      }
    } catch {
      showMsg('네트워크 오류')
    } finally {
      setSaving(false)
    }
  }

  // --- Nav menu save ---
  const navChanged = () => JSON.stringify(navItems) !== (navOriginal || '[]')

  const handleNavSave = async () => {
    const json = JSON.stringify(navItems)
    setSaving(true)
    try {
      const res = await signedFetch(`${API}/api/admin/settings`, {
        method: 'PUT',
        body: JSON.stringify({ settings: { nav_menu: json } }),
      })
      if (res.ok) {
        showMsg('네비게이션 저장 완료')
        setNavOriginal(json)
        setSettings(prev => ({ ...prev, nav_menu: json }))
        setOriginal(prev => ({ ...prev, nav_menu: json }))
      } else {
        showMsg('저장 실패')
      }
    } catch {
      showMsg('네트워크 오류')
    } finally {
      setSaving(false)
    }
  }

  const addNavItem = () => {
    setNavItems(prev => [...prev, { href: '/', label: 'New Link' }])
  }

  const removeNavItem = (idx: number) => {
    setNavItems(prev => prev.filter((_, i) => i !== idx))
  }

  const moveNavItem = (idx: number, dir: 'up' | 'down') => {
    const next = dir === 'up' ? idx - 1 : idx + 1
    if (next < 0 || next >= navItems.length) return
    setNavItems(prev => {
      const arr = [...prev]
      ;[arr[idx], arr[next]] = [arr[next], arr[idx]]
      return arr
    })
  }

  const updateNavItem = (idx: number, field: 'href' | 'label', val: string) => {
    setNavItems(prev => prev.map((item, i) => i === idx ? { ...item, [field]: val } : item))
  }

  // --- CTA save ---
  const ctaChanged = () =>
    JSON.stringify(cta1) !== (ctaOriginal1 || '{}') ||
    JSON.stringify(cta2) !== (ctaOriginal2 || '{}')

  const handleCtaSave = async () => {
    const json1 = JSON.stringify(cta1)
    const json2 = JSON.stringify(cta2)
    setSaving(true)
    try {
      const res = await signedFetch(`${API}/api/admin/settings`, {
        method: 'PUT',
        body: JSON.stringify({ settings: { nav_cta_1: json1, nav_cta_2: json2 } }),
      })
      if (res.ok) {
        showMsg('CTA 버튼 저장 완료')
        setCtaOriginal1(json1)
        setCtaOriginal2(json2)
        setSettings(prev => ({ ...prev, nav_cta_1: json1, nav_cta_2: json2 }))
        setOriginal(prev => ({ ...prev, nav_cta_1: json1, nav_cta_2: json2 }))
      } else {
        showMsg('저장 실패')
      }
    } catch {
      showMsg('네트워크 오류')
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
          <p className="text-[13px] text-[#86868b] mt-1">사이트 전체 설정을 관리합니다</p>
        </div>
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

          {/* ── Site Name + Hero ── */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-[15px] font-semibold text-[#1d1d1f]">사이트 기본</h3>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || !hasChanges()}
                className="px-4 py-1.5 bg-[#0071e3] text-white text-[12px] font-semibold rounded-lg hover:bg-[#0077ED] transition-colors disabled:opacity-50"
              >
                {saving ? '저장 중...' : '저장'}
              </button>
            </div>
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                <label className="text-[13px] font-medium text-[#424245] w-[140px] shrink-0">사이트명</label>
                <input
                  type="text"
                  value={settings.site_name || ''}
                  onChange={e => setSettings(prev => ({ ...prev, site_name: e.target.value }))}
                  placeholder="BRIDGE"
                  className={`flex-1 px-3 py-2 border rounded-lg text-[14px] focus:outline-none focus:border-[#0071e3] transition-colors ${
                    settings.site_name !== (original.site_name || '') ? 'border-[#0071e3] bg-blue-50/30' : 'border-[#d2d2d7]'
                  }`}
                />
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                <label className="text-[13px] font-medium text-[#424245] w-[140px] shrink-0">히어로 태그라인</label>
                <input
                  type="text"
                  value={settings.hero_tagline || ''}
                  onChange={e => setSettings(prev => ({ ...prev, hero_tagline: e.target.value }))}
                  placeholder="A career that changes your life"
                  className={`flex-1 px-3 py-2 border rounded-lg text-[14px] focus:outline-none focus:border-[#0071e3] transition-colors ${
                    settings.hero_tagline !== (original.hero_tagline || '') ? 'border-[#0071e3] bg-blue-50/30' : 'border-[#d2d2d7]'
                  }`}
                />
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                <label className="text-[13px] font-medium text-[#424245] w-[140px] shrink-0">히어로 부제</label>
                <input
                  type="text"
                  value={settings.hero_subtitle || ''}
                  onChange={e => setSettings(prev => ({ ...prev, hero_subtitle: e.target.value }))}
                  placeholder="Korea's #1 ESL recruitment platform"
                  className={`flex-1 px-3 py-2 border rounded-lg text-[14px] focus:outline-none focus:border-[#0071e3] transition-colors ${
                    settings.hero_subtitle !== (original.hero_subtitle || '') ? 'border-[#0071e3] bg-blue-50/30' : 'border-[#d2d2d7]'
                  }`}
                />
              </div>
            </div>
          </div>

          {/* ── Navigation Menu Editor ── */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-[15px] font-semibold text-[#1d1d1f]">네비게이션 메뉴</h3>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={addNavItem}
                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-[#f5f5f7] text-[#1d1d1f] text-[12px] font-medium rounded-lg hover:bg-[#e8e8ed] transition-colors"
                >
                  <Plus size={14} /> 추가
                </button>
                <button
                  type="button"
                  onClick={handleNavSave}
                  disabled={saving || !navChanged()}
                  className="px-4 py-1.5 bg-[#0071e3] text-white text-[12px] font-semibold rounded-lg hover:bg-[#0077ED] transition-colors disabled:opacity-50"
                >
                  {saving ? '저장 중...' : '저장'}
                </button>
              </div>
            </div>
            {navItems.length === 0 ? (
              <p className="text-[13px] text-[#86868b]">메뉴 항목이 없습니다. 추가 버튼을 눌러주세요.</p>
            ) : (
              <div className="space-y-2">
                {navItems.map((item, idx) => (
                  <div key={idx} className="flex items-center gap-2 p-2 bg-[#f5f5f7] rounded-lg group">
                    <GripVertical size={14} className="text-[#86868b] shrink-0" />
                    <input
                      type="text"
                      value={item.label}
                      onChange={e => updateNavItem(idx, 'label', e.target.value)}
                      placeholder="라벨"
                      className="w-[140px] px-2 py-1.5 border border-[#d2d2d7] rounded text-[13px] focus:outline-none focus:border-[#0071e3]"
                    />
                    <input
                      type="text"
                      value={item.href}
                      onChange={e => updateNavItem(idx, 'href', e.target.value)}
                      placeholder="/path"
                      className="flex-1 px-2 py-1.5 border border-[#d2d2d7] rounded text-[13px] focus:outline-none focus:border-[#0071e3]"
                    />
                    <div className="flex items-center gap-0.5 shrink-0">
                      <button type="button" onClick={() => moveNavItem(idx, 'up')} disabled={idx === 0}
                        className="p-1 hover:bg-white rounded disabled:opacity-30 transition-colors">
                        <ChevronUp size={14} />
                      </button>
                      <button type="button" onClick={() => moveNavItem(idx, 'down')} disabled={idx === navItems.length - 1}
                        className="p-1 hover:bg-white rounded disabled:opacity-30 transition-colors">
                        <ChevronDown size={14} />
                      </button>
                      <button type="button" onClick={() => removeNavItem(idx)}
                        className="p-1 hover:bg-red-50 text-red-500 rounded transition-colors">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ── CTA Buttons ── */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-[15px] font-semibold text-[#1d1d1f]">CTA 버튼</h3>
              <button
                type="button"
                onClick={handleCtaSave}
                disabled={saving || !ctaChanged()}
                className="px-4 py-1.5 bg-[#0071e3] text-white text-[12px] font-semibold rounded-lg hover:bg-[#0077ED] transition-colors disabled:opacity-50"
              >
                {saving ? '저장 중...' : '저장'}
              </button>
            </div>
            <div className="space-y-4">
              <div className="p-3 bg-[#f5f5f7] rounded-lg">
                <p className="text-[12px] font-medium text-[#86868b] mb-2">버튼 1 (우측 상단)</p>
                <div className="flex gap-2">
                  <input type="text" value={cta1.label}
                    onChange={e => setCta1(prev => ({ ...prev, label: e.target.value }))}
                    placeholder="라벨" className="w-[140px] px-2 py-1.5 border border-[#d2d2d7] rounded text-[13px] focus:outline-none focus:border-[#0071e3]" />
                  <input type="text" value={cta1.href}
                    onChange={e => setCta1(prev => ({ ...prev, href: e.target.value }))}
                    placeholder="/path" className="flex-1 px-2 py-1.5 border border-[#d2d2d7] rounded text-[13px] focus:outline-none focus:border-[#0071e3]" />
                </div>
              </div>
              <div className="p-3 bg-[#f5f5f7] rounded-lg">
                <p className="text-[12px] font-medium text-[#86868b] mb-2">버튼 2 (우측 상단)</p>
                <div className="flex gap-2">
                  <input type="text" value={cta2.label}
                    onChange={e => setCta2(prev => ({ ...prev, label: e.target.value }))}
                    placeholder="라벨" className="w-[140px] px-2 py-1.5 border border-[#d2d2d7] rounded text-[13px] focus:outline-none focus:border-[#0071e3]" />
                  <input type="text" value={cta2.href}
                    onChange={e => setCta2(prev => ({ ...prev, href: e.target.value }))}
                    placeholder="/path" className="flex-1 px-2 py-1.5 border border-[#d2d2d7] rounded text-[13px] focus:outline-none focus:border-[#0071e3]" />
                </div>
              </div>
            </div>
          </div>

          {/* ── Existing setting groups (회사 정보, 연락처, SNS, 푸터) ── */}
          {SETTING_GROUPS.map(group => (
            <div key={group.title} className="bg-white rounded-2xl border border-[#e5e5e7] p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-[15px] font-semibold text-[#1d1d1f]">{group.title}</h3>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saving || !hasChanges()}
                  className="px-4 py-1.5 bg-[#0071e3] text-white text-[12px] font-semibold rounded-lg hover:bg-[#0077ED] transition-colors disabled:opacity-50"
                >
                  {saving ? '저장 중...' : '저장'}
                </button>
              </div>
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
          {/* ── 비밀키 관리 ── */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-[15px] font-semibold text-[#1d1d1f]">비밀키 관리</h3>
                <p className="text-[12px] text-[#86868b] mt-0.5">외부 API 키는 여기서만 입력 — AES-256 암호화 저장, 값 재표시 불가</p>
              </div>
            </div>

            {/* 카카오 OAuth 3개 고정 입력 */}
            <div className="space-y-3 mb-5">
              {KAKAO_FIELDS.map((field, idx) => {
                const saved = secrets.find(s => s.key === field.key)
                const msg = kakaoMsg[field.key]
                return (
                  <div key={field.key} className="border border-[#e5e5e7] rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="w-5 h-5 rounded-full bg-[#f5f5f7] text-[#424245] flex items-center justify-center font-bold text-[11px] shrink-0">{idx + 1}</span>
                      <span className="text-[13px] font-semibold text-[#1d1d1f]">{field.label}</span>
                      <span className="font-mono text-[11px] text-[#86868b]">{field.key}</span>
                      {saved && (
                        <span className="ml-auto text-[11px] text-green-600 bg-green-50 px-2 py-0.5 rounded-full font-medium">등록됨 ✓</span>
                      )}
                    </div>
                    <p className="text-[11px] text-[#86868b] mb-2.5">{field.hint}</p>
                    <div className="flex gap-2">
                      <input
                        type="password"
                        placeholder={saved ? '새 값으로 덮어쓰기' : '값 입력 (저장 후 재표시 불가)'}
                        value={kakaoValues[field.key] || ''}
                        onChange={e => setKakaoValues(prev => ({ ...prev, [field.key]: e.target.value }))}
                        className="flex-1 px-3 py-2 border border-[#d2d2d7] rounded-lg text-[13px] focus:outline-none focus:border-[#0071e3]"
                        autoComplete="new-password"
                        onKeyDown={e => { if (e.key === 'Enter') handleSaveKakaoKey(field.key, field.label) }}
                      />
                      <button
                        type="button"
                        onClick={() => handleSaveKakaoKey(field.key, field.label)}
                        disabled={kakaoSaving[field.key] || !kakaoValues[field.key]?.trim()}
                        className="px-4 py-2 bg-[#1d1d1f] text-white rounded-lg text-[13px] font-medium hover:bg-[#333] disabled:opacity-40 transition-colors shrink-0"
                      >
                        {kakaoSaving[field.key] ? '저장...' : saved ? '덮어쓰기' : '저장'}
                      </button>
                      {saved && (
                        <button
                          type="button"
                          onClick={() => handleDeleteSecret(field.key)}
                          className="px-3 py-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg text-[13px] transition-colors shrink-0"
                        >
                          삭제
                        </button>
                      )}
                    </div>
                    {msg && (
                      <p className={`mt-1.5 text-[12px] font-medium ${msg.ok ? 'text-green-600' : 'text-red-500'}`}>{msg.text}</p>
                    )}
                  </div>
                )
              })}
            </div>

            {/* 기타 저장된 키 (카카오 외) */}
            {secrets.filter(s => !KAKAO_FIELDS.some(f => f.key === s.key)).length > 0 && (
              <div className="border-t border-[#f0f0f2] pt-4">
                <p className="text-[12px] font-medium text-[#86868b] mb-2">기타 비밀키</p>
                <div className="space-y-2">
                  {secrets.filter(s => !KAKAO_FIELDS.some(f => f.key === s.key)).map(s => (
                    <div key={s.key} className="flex items-center gap-3 px-3 py-2.5 bg-[#f5f5f7] rounded-xl">
                      <div className="flex-1 min-w-0">
                        <div className="text-[13px] font-mono font-semibold text-[#1d1d1f]">{s.key}</div>
                        {s.description && <div className="text-[11px] text-[#86868b] truncate">{s.description}</div>}
                      </div>
                      <div className="text-[12px] font-mono text-[#aeaeb2] tracking-widest select-none">••••••••</div>
                      <button type="button" onClick={() => handleDeleteSecret(s.key)}
                        className="text-[11px] text-red-400 hover:text-red-600 transition-colors px-2 py-1 rounded-lg hover:bg-red-50">삭제</button>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>

        </div>
      )}
    </div>
  )
}
