'use client'

/**
 * /admin/mail-send - 메일 발송 (Naver-style UI)
 * - 기본 서명 + 법적 고지 자동 삽입
 * - 개인발송 토글 강조 배지
 * - 네이버 스타일 툴바
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import DOMPurify from 'dompurify'
import { API_URL } from '@/lib/api'
import { Mail, Send, Users, FileText, AlertCircle, CheckCircle2, Paperclip, ChevronDown } from 'lucide-react'

const API = API_URL
const DRAFT_KEY    = 'bridge_mail_draft'
const HEADER_KEY   = 'bridge_mail_header'
const FOOTER_KEY   = 'bridge_mail_footer'
const BODY_DEFAULT_KEY = 'bridge_mail_body_default'

function loadSaved(key: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  return localStorage.getItem(key) || fallback
}

interface Template {
  template_key: string
  subject: string
  body_html: string
}

interface SendResult {
  success: boolean
  sent: number
  failed: number
  errors?: string[]
}

const SENDERS = [
  { value: 'bridgejobkr@gmail.com', label: 'Gmail (bridgejobkr)' },
  { value: 'bridgejobkr@naver.com', label: 'Naver (bridgejobkr)' },
]

const FONTS = [
  { value: 'Nanum Gothic, sans-serif', label: '나눔고딕' },
  { value: 'Arial, sans-serif', label: 'Arial' },
  { value: 'Times New Roman, serif', label: 'Times New Roman' },
]

const BODY_HEADER = `<div style="font-family:'Nanum Gothic',Arial,sans-serif;max-width:600px;margin:0 auto">
<div style="background:#1a57c8;padding:20px 28px;border-radius:8px 8px 0 0">
  <span style="color:#fff;font-size:20px;font-weight:800;letter-spacing:1px">BRIDGE</span>
  <span style="color:rgba(255,255,255,0.7);font-size:12px;margin-left:8px">Recruitment</span>
</div>
<div style="background:#fff;border:1px solid #e5e5e7;border-top:none;padding:28px 28px 0 28px;border-radius:0 0 8px 8px">
<p style="margin:0 0 18px;font-size:15px;color:#222">Dear Teacher,</p>
<p style="margin:0 0 16px">&nbsp;</p>
<p style="margin:0 0 16px">&nbsp;</p>`

const BODY_FOOTER = `<p style="margin:24px 0 8px;font-size:14px;color:#222">Kind Regards,</p>
<p style="margin:0 0 4px;font-size:14px;font-weight:700;color:#1a57c8">BRIDGE Recruitment Team</p>
<p style="margin:0 0 4px;font-size:12px;color:#555">📧 bridgejobkr@gmail.com &nbsp;|&nbsp; 🌐 bridgejob.co.kr</p>
<hr style="border:none;border-top:1px solid #eee;margin:20px 0"/>
<p style="font-size:10px;color:#aaa;line-height:1.6;padding-bottom:20px">
[기밀성 및 법적 고지] 본 메일은 지정된 수신자에게만 전달된 것으로, 고용주 또는 채용 관리자가 아니거나 퇴사자일 경우 열람·보관·전달을 금지하며 즉시 수신자 제거 요청 후 삭제해주시기 바랍니다. 특히 영어 강사로 근무 중이시더라도 과거에 잠시 이력서 관리 업무를 담당하셨던 경우라면, 현재 권한이 없으므로 반드시 삭제 및 수신 거부 요청을 해주셔야 합니다. 무단 수신은 법적 책임이 발생할 수 있으며, 본 메일은 분쟁 시 증거로 활용될 수 있습니다.<br/><br/>
This email is intended for the designated recipient only. If you are not the intended recipient, or even if you are an English instructor who previously handled resume management but no longer holds that responsibility, please reply requesting removal from our mailing list and delete this email immediately.
</p>
</div>
</div>`


export default function MailSendPage() {
  const { adminKey, authed, login, signedFetch, waking } = useAdminAuth()

  const [activeTab, setActiveTab] = useState<'mail' | 'builder'>('mail')
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(false)
  const [showTemplateMenu, setShowTemplateMenu] = useState(false)

  // Form state
  const [sender, setSender] = useState<string>(SENDERS[0].value)
  const [recipientText, setRecipientText] = useState('')
  const [subject, setSubject] = useState('')
  const [bodyHtml, setBodyHtml] = useState(() => {
    // 전체 본문 저장값 우선, 없으면 헤더+푸터 조합
    const saved = typeof window !== 'undefined' ? localStorage.getItem(BODY_DEFAULT_KEY) : null
    if (saved) return saved
    const h = loadSaved(HEADER_KEY, BODY_HEADER)
    const f = loadSaved(FOOTER_KEY, BODY_FOOTER)
    return `${h}\n\n${f}`
  })
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState<SendResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showPreview, setShowPreview] = useState(false)
  const [personalSend, setPersonalSend] = useState(false)
  const [font, setFont] = useState(FONTS[0].value)

  // 기본값 설정 (localStorage에서 로드)
  const [customHeader, setCustomHeader] = useState(() => loadSaved(HEADER_KEY, BODY_HEADER))
  const [customFooter, setCustomFooter] = useState(() => loadSaved(FOOTER_KEY, BODY_FOOTER))
  const [showDefaults, setShowDefaults] = useState(false)
  const [defaultsSaved, setDefaultsSaved] = useState(false)
  const [bodySaved, setBodySaved] = useState(false)

  // 템플릿 관리 패널
  const [showTplPanel, setShowTplPanel] = useState(false)
  const [tplTab, setTplTab] = useState<'list'|'edit'|'new'>('list')
  const [editTpl, setEditTpl] = useState<Template|null>(null)
  const [editTplSubject, setEditTplSubject] = useState('')
  const [editTplBody, setEditTplBody] = useState('')
  const [newTplKey, setNewTplKey] = useState('')
  const [newTplSubject, setNewTplSubject] = useState('')
  const [newTplBody, setNewTplBody] = useState('')
  const [tplSaving, setTplSaving] = useState(false)
  const [tplMsg, setTplMsg] = useState('')

  const fileInputRef = useRef<HTMLInputElement>(null)
  const templateMenuRef = useRef<HTMLDivElement>(null)

  // Load templates
  const fetchTemplates = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API}/api/admin/email-templates`, {
        headers: { 'x-admin-key': adminKey },
      })
      const json = await res.json()
      if (res.ok && json.success) {
        setTemplates(json.data || [])
      }
    } catch {
      // silent fail
    } finally {
      setLoading(false)
    }
  }, [adminKey])

  useEffect(() => {
    if (authed) fetchTemplates()
  }, [authed, fetchTemplates])

  // Close template dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (templateMenuRef.current && !templateMenuRef.current.contains(e.target as Node)) {
        setShowTemplateMenu(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Apply template: insert between header and footer
  const applyTemplate = (key: string) => {
    setSelectedTemplate(key)
    setShowTemplateMenu(false)
    const t = templates.find(tp => tp.template_key === key)
    if (t) {
      setSubject(t.subject)
      setBodyHtml(`${customHeader}\n\n${t.body_html}\n\n${customFooter}`)
    }
  }

  // 현재 본문을 기본값으로 저장
  const saveBodyAsDefault = () => {
    localStorage.setItem(BODY_DEFAULT_KEY, bodyHtml)
    setBodySaved(true)
    setTimeout(() => setBodySaved(false), 2500)
  }

  // 템플릿 저장 (PUT)
  const saveTpl = async () => {
    if (!editTpl) return
    setTplSaving(true)
    try {
      await fetch(`${API}/api/admin/email-templates/${editTpl.template_key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body: JSON.stringify({ subject: editTplSubject, body_html: editTplBody }),
      })
      setTplMsg('저장 완료'); setTimeout(() => setTplMsg(''), 2000)
      fetchTemplates(); setTplTab('list')
    } catch { setTplMsg('저장 실패') }
    finally { setTplSaving(false) }
  }

  // 템플릿 생성 (PUT — INSERT OR REPLACE)
  const createTpl = async () => {
    if (!newTplKey.trim()) return
    setTplSaving(true)
    try {
      await fetch(`${API}/api/admin/email-templates/${newTplKey.trim()}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'x-admin-key': adminKey },
        body: JSON.stringify({ subject: newTplSubject, body_html: newTplBody }),
      })
      setTplMsg('생성 완료'); setTimeout(() => setTplMsg(''), 2000)
      fetchTemplates(); setNewTplKey(''); setNewTplSubject(''); setNewTplBody(''); setTplTab('list')
    } catch { setTplMsg('생성 실패') }
    finally { setTplSaving(false) }
  }

  // 기본값(헤더/서명) 저장
  const saveDefaults = () => {
    localStorage.setItem(HEADER_KEY, customHeader)
    localStorage.setItem(FOOTER_KEY, customFooter)
    setDefaultsSaved(true)
    setTimeout(() => setDefaultsSaved(false), 2500)
    // 현재 본문도 새 기본값으로 리셋
    setBodyHtml(`${customHeader}\n\n${customFooter}`)
  }

  // Save draft to localStorage
  const saveDraft = () => {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({ sender, recipientText, subject, bodyHtml }))
    alert('임시저장 완료')
  }

  // Parse recipients
  const parseRecipients = (): string[] =>
    recipientText
      .split(/[\n,;]+/)
      .map(e => e.trim())
      .filter(e => e && e.includes('@'))

  // Send
  const handleSend = async () => {
    const recipients = parseRecipients()
    if (recipients.length === 0) { setError('수신자 이메일을 입력해주세요.'); return }
    if (!subject.trim()) { setError('제목을 입력해주세요.'); return }
    if (!bodyHtml.trim()) { setError('본문을 입력해주세요.'); return }

    setSending(true)
    setError(null)
    setResult(null)

    try {
      const res = await signedFetch(`${API}/api/admin/mail/send-bulk`, {
        method: 'POST',
        body: JSON.stringify({
          sender,
          recipients,
          subject: subject.trim(),
          body_html: bodyHtml.trim(),
          personal_send: personalSend,
        }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || json.message || `Error ${res.status}`)
      setResult({
        success: true,
        sent: json.data?.sent ?? recipients.length,
        failed: json.data?.failed ?? 0,
        errors: json.data?.errors,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : '발송 실패')
    } finally {
      setSending(false)
    }
  }

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  const recipients = parseRecipients()

  return (
    <div className="max-w-[1100px] mx-auto space-y-4">
      <style>{`
        @keyframes templateGlow {
          0%, 100% { box-shadow: 0 0 0 0 rgba(251,191,36,0.7), 0 2px 8px rgba(245,158,11,0.3); }
          50% { box-shadow: 0 0 0 5px rgba(251,191,36,0.2), 0 2px 14px rgba(245,158,11,0.5); }
        }
      `}</style>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-[22px] font-bold text-[#1d1d1f] tracking-tight flex items-center gap-2">
            <Mail size={22} className="text-blue-600" />
            메일 발송
          </h1>
          <p className="text-[13px] text-[#86868b] mt-0.5">직접 수신자를 입력하여 메일을 발송합니다</p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="https://mail.naver.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-white text-[13px] font-semibold no-underline transition-opacity hover:opacity-85"
            style={{ background: '#03C75A', boxShadow: '0 2px 6px rgba(3,199,90,0.3)' }}
          >
            <span style={{ width: 16, height: 16, background: 'rgba(255,255,255,0.3)', borderRadius: 3, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 900, color: '#fff', flexShrink: 0 }}>N</span>
            네이버 메일
          </a>
          <a
            href="https://mail.google.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[#444] text-[13px] font-semibold no-underline border border-[#ddd] transition-opacity hover:opacity-85"
            style={{ background: '#fff', boxShadow: '0 2px 6px rgba(0,0,0,0.08)' }}
          >
            <span style={{ width: 16, height: 16, background: '#EA4335', borderRadius: 3, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 900, color: '#fff', flexShrink: 0 }}>M</span>
            Gmail
          </a>
        </div>
      </div>

      {/* ── Tab Switch ── */}
      <div className="flex gap-1 border-b border-[#e5e5e7]">
        <button
          onClick={() => setActiveTab('mail')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'mail'
              ? 'border-[#0071e3] text-[#0071e3]'
              : 'border-transparent text-[#6e6e73] hover:text-[#1d1d1f]'
          }`}
        >
          <Mail size={14} className="inline mr-1.5 -mt-0.5" />
          메일 발송
        </button>
        <button
          onClick={() => setActiveTab('builder')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'builder'
              ? 'border-[#0071e3] text-[#0071e3]'
              : 'border-transparent text-[#6e6e73] hover:text-[#1d1d1f]'
          }`}
        >
          <FileText size={14} className="inline mr-1.5 -mt-0.5" />
          프로필 빌더
        </button>
      </div>

      {/* ── Profile Builder Tab ── */}
      {activeTab === 'builder' && (
        <ProfileBuilder
          onInsert={(html) => {
            setBodyHtml(html)
            setSubject('\ud83d\udce2BRIDGE \uc6d0\uc5b4\ubbfc \uac15\uc0ac \uc18c\uc2dd ! \uad6d\ub0b4/\ud574\uc678 \ud504\ub85c\ud544 \ud655\uc778\ud558\uc138\uc694')
            setActiveTab('mail')
          }}
          signedFetch={signedFetch}
          adminKey={adminKey}
        />
      )}

      {/* ── Mail Tab ── */}
      {activeTab === 'mail' && (<>

      {/* ── Naver-style Toolbar ── */}
      <div className="bg-[#f0f4fb] border border-[#c8d6f0] rounded-xl px-4 py-2.5 flex items-center gap-2 flex-wrap">
        <button
          type="button"
          onClick={handleSend}
          disabled={sending || recipients.length === 0}
          className="flex items-center gap-1.5 px-4 py-1.5 bg-[#1a57c8] text-white text-[13px] font-bold rounded-md hover:bg-[#1444a8] disabled:opacity-40 transition-colors"
        >
          <Send size={14} />
          보내기
        </button>

        <button
          type="button"
          onClick={() => setShowPreview(!showPreview)}
          className="flex items-center gap-1.5 px-4 py-1.5 bg-white border border-[#c8d6f0] text-[#1a57c8] text-[13px] font-semibold rounded-md hover:bg-[#e8eef8] transition-colors"
        >
          미리보기
        </button>

        <button
          type="button"
          onClick={saveDraft}
          className="flex items-center gap-1.5 px-4 py-1.5 bg-white border border-[#c8d6f0] text-[#555] text-[13px] font-semibold rounded-md hover:bg-[#e8eef8] transition-colors"
        >
          임시저장
        </button>

        {/* Template dropdown */}
        <div className="relative" ref={templateMenuRef}>
          <button
            type="button"
            onClick={() => setShowTemplateMenu(v => !v)}
            className="flex items-center gap-1 px-4 py-1.5 text-[13px] font-bold rounded-md transition-colors"
            style={{
              background: 'linear-gradient(135deg, #fbbf24, #f59e0b)',
              color: '#fff',
              border: '1px solid #d97706',
              animation: 'templateGlow 1.8s ease-in-out infinite',
            }}
          >
            <FileText size={13} />
            템플릿 ✨
            <ChevronDown size={12} />
          </button>
          {showTemplateMenu && (
            <div className="absolute left-0 top-full mt-1 z-50 bg-white border border-[#d2d2d7] rounded-xl shadow-lg min-w-[220px] max-h-[300px] overflow-y-auto">
              {loading ? (
                <div className="px-4 py-3 text-[12px] text-[#86868b]">로딩 중...</div>
              ) : templates.length === 0 ? (
                <div className="px-4 py-3 text-[12px] text-[#86868b]">템플릿 없음</div>
              ) : (
                templates.map(t => (
                  <button
                    key={t.template_key}
                    type="button"
                    onClick={() => applyTemplate(t.template_key)}
                    className={`w-full text-left px-4 py-2.5 text-[13px] hover:bg-[#f5f5f7] transition-colors ${
                      selectedTemplate === t.template_key ? 'bg-blue-50 text-blue-700' : 'text-[#1d1d1f]'
                    }`}
                  >
                    <div className="font-medium truncate">{t.template_key}</div>
                    <div className="text-[11px] text-[#86868b] truncate">{t.subject}</div>
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        <div className="flex-1" />

        {/* Font selector */}
        <select
          value={font}
          onChange={e => setFont(e.target.value)}
          className="px-3 py-1.5 bg-white border border-[#c8d6f0] text-[12px] rounded-md text-[#555] focus:outline-none"
        >
          {FONTS.map(f => (
            <option key={f.value} value={f.value}>{f.label}</option>
          ))}
        </select>

        {/* File attach */}
        <input ref={fileInputRef} type="file" multiple className="hidden" />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-1 px-3 py-1.5 bg-white border border-[#c8d6f0] text-[12px] text-[#555] rounded-md hover:bg-[#e8eef8] transition-colors"
        >
          <Paperclip size={13} />
          내 PC
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-5">
        {/* Left: Compose */}
        <div className="space-y-3">
          {/* Sender */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4">
            <label className="block text-[11px] font-semibold text-[#86868b] uppercase tracking-wider mb-1.5">발신자</label>
            <select
              value={sender}
              onChange={e => setSender(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-[#d2d2d7] text-[14px] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            >
              {SENDERS.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          {/* Recipients + Personal Send Toggle */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4">
            <div className="flex items-center justify-between mb-2">
              <label className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider flex items-center gap-1.5">
                <Users size={13} />
                수신자 <span className="text-[#86868b] font-normal normal-case">({recipients.length}명)</span>
              </label>

              {/* ── 개인발송 강조 토글 ── */}
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  background: '#1a1a2e',
                  color: '#fff',
                  padding: '6px 14px',
                  borderRadius: '20px',
                  cursor: 'pointer',
                  fontWeight: 700,
                  fontSize: '13px',
                  border: `2px solid ${personalSend ? '#ff4444' : '#4f8ef7'}`,
                  boxShadow: `0 0 8px ${personalSend ? 'rgba(255,68,68,0.4)' : 'rgba(79,142,247,0.4)'}`,
                  whiteSpace: 'nowrap',
                  userSelect: 'none',
                  transition: 'all 0.2s',
                }}
              >
                <input
                  type="checkbox"
                  checked={personalSend}
                  onChange={e => setPersonalSend(e.target.checked)}
                  style={{ width: '16px', height: '16px', accentColor: personalSend ? '#ff4444' : '#4f8ef7', cursor: 'pointer' }}
                />
                {personalSend ? '개인 발송 ✓' : '개인 발송'}
              </label>
            </div>
            <textarea
              value={recipientText}
              onChange={e => setRecipientText(e.target.value)}
              placeholder="이메일 주소를 입력하세요 (줄바꿈, 콤마, 세미콜론으로 구분)&#10;예: teacher1@school.com&#10;teacher2@academy.kr"
              rows={4}
              className="w-full px-3 py-2.5 rounded-xl border border-[#d2d2d7] text-[13px] resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono"
            />
          </div>

          {/* Subject */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4">
            <label className="block text-[11px] font-semibold text-[#86868b] uppercase tracking-wider mb-1.5">제목</label>
            <input
              type="text"
              value={subject}
              onChange={e => setSubject(e.target.value)}
              placeholder="이메일 제목"
              className="w-full px-3 py-2 rounded-xl border border-[#d2d2d7] text-[14px] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>

          {/* Body — 분할 뷰 (에디터 + 실시간 미리보기) */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4">
            <div className="flex items-center justify-between mb-3">
              <label className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider">본문 (HTML)</label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={saveBodyAsDefault}
                  className={`text-[11px] font-semibold px-2.5 py-1 rounded-lg border transition-colors ${
                    bodySaved
                      ? 'bg-green-50 border-green-300 text-green-700'
                      : 'bg-[#f5f5f7] border-[#d2d2d7] text-[#555] hover:bg-[#e8e8ed]'
                  }`}
                >
                  {bodySaved ? '✅ 저장됨' : '📌 기본값 저장'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowPreview(!showPreview)}
                  className={`text-[11px] font-semibold px-2.5 py-1 rounded-lg border transition-colors ${
                    showPreview
                      ? 'bg-blue-600 border-blue-600 text-white'
                      : 'bg-[#f5f5f7] border-[#d2d2d7] text-[#555] hover:bg-[#e8e8ed]'
                  }`}
                >
                  {showPreview ? '◧ 분할보기 ON' : '◧ 분할보기'}
                </button>
              </div>
            </div>

            {showPreview ? (
              /* ── 분할 뷰 ── */
              <div className="grid grid-cols-2 gap-3" style={{ minHeight: 420 }}>
                {/* 좌: HTML 에디터 */}
                <div className="flex flex-col">
                  <div className="text-[10px] font-semibold text-[#86868b] uppercase tracking-wider mb-1.5 flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-[#ff5f56] inline-block" />
                    HTML 편집
                  </div>
                  <textarea
                    value={bodyHtml}
                    onChange={e => setBodyHtml(e.target.value)}
                    className="flex-1 w-full px-3 py-2.5 rounded-xl border border-[#d2d2d7] text-[11px] resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono bg-[#1e1e2e] text-[#cdd6f4]"
                    style={{ minHeight: 400 }}
                    spellCheck={false}
                  />
                </div>
                {/* 우: 실시간 미리보기 */}
                <div className="flex flex-col">
                  <div className="text-[10px] font-semibold text-[#86868b] uppercase tracking-wider mb-1.5 flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-[#27c93f] inline-block" />
                    실시간 미리보기
                  </div>
                  <div
                    className="flex-1 rounded-xl border border-[#d2d2d7] overflow-y-auto"
                    style={{ minHeight: 400, background: '#f6f6f6' }}
                  >
                    {/* 이메일 외곽 래퍼 */}
                    <div style={{ maxWidth: 600, margin: '16px auto', background: '#fff', borderRadius: 8, boxShadow: '0 2px 12px rgba(0,0,0,0.10)', padding: '24px 32px', fontFamily: font, fontSize: 14, lineHeight: 1.7, color: '#222' }}>
                      {subject && (
                        <div style={{ fontSize: 12, color: '#888', marginBottom: 16, paddingBottom: 12, borderBottom: '1px solid #eee' }}>
                          <strong>제목:</strong> {subject}
                        </div>
                      )}
                      <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(bodyHtml) }} />
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* ── 단독 에디터 ── */
              <textarea
                value={bodyHtml}
                onChange={e => setBodyHtml(e.target.value)}
                rows={14}
                className="w-full px-3 py-2.5 rounded-xl border border-[#d2d2d7] text-[12px] resize-y focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono"
              />
            )}
          </div>

          {/* Error / Result */}
          {error && (
            <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-xl text-[13px] text-red-700">
              <AlertCircle size={16} />
              {error}
            </div>
          )}
          {result && (
            <div className={`flex items-center gap-2 p-4 rounded-xl text-[13px] border ${
              result.failed === 0
                ? 'bg-green-50 border-green-200 text-green-700'
                : 'bg-yellow-50 border-yellow-200 text-yellow-700'
            }`}>
              <CheckCircle2 size={16} />
              {result.sent}건 발송 완료{result.failed > 0 ? `, ${result.failed}건 실패` : ''}
            </div>
          )}

          {/* Send Button */}
          <button
            type="button"
            onClick={handleSend}
            disabled={sending || recipients.length === 0}
            className="w-full py-3.5 bg-[#1a57c8] text-white text-[15px] font-bold rounded-2xl hover:bg-[#1444a8] disabled:opacity-40 transition-colors flex items-center justify-center gap-2"
          >
            {sending ? '발송 중...' : <><Send size={18} />메일 발송 ({recipients.length}명)</>}
          </button>
        </div>

        {/* Right: Info panel */}
        <div className="space-y-4">
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4">
            <h3 className="text-[13px] font-semibold text-[#1d1d1f] mb-3 flex items-center gap-1.5">
              <FileText size={15} />
              발송 안내
            </h3>
            <div className="space-y-1.5 text-[12px] text-[#86868b]">
              <p>• 개별 발송 (CC/BCC 사용 안 함)</p>
              <p>• 발송 간격: 3초</p>
              <p>• 일일 한도: 200건</p>
              <p>• Reply-To: bridgejobkr@gmail.com</p>
              <p>• 발송 기록은 메일 로그에서 확인</p>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4">
            <h3 className="text-[13px] font-semibold text-[#1d1d1f] mb-3">개인발송 안내</h3>
            <div className="space-y-1.5 text-[12px] text-[#86868b]">
              <p>• <span className="font-semibold text-[#ff4444]">개인 발송 ON</span>: 수신자별 개별 연결</p>
              <p>• OFF: 일반 대량 발송 모드</p>
              <p>• 개인정보 노출 방지를 위해 중요 메일은 ON 권장</p>
            </div>
          </div>

          {/* ── 기본값 설정 ── */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden">
            <button
              type="button"
              onClick={() => setShowDefaults(v => !v)}
              className="w-full flex items-center justify-between px-4 py-3 text-[13px] font-semibold text-[#1d1d1f] hover:bg-[#f5f5f7] transition-colors"
            >
              <span>⚙️ 기본 서명 · 헤더 설정</span>
              <span className="text-[11px] text-[#86868b]">{showDefaults ? '▲' : '▼'}</span>
            </button>
            {showDefaults && (
              <div className="px-4 pb-4 space-y-3 border-t border-[#f0f0f0]">
                <div className="pt-3">
                  <label className="block text-[11px] font-semibold text-[#86868b] uppercase tracking-wider mb-1.5">편지 시작 (Header)</label>
                  <textarea
                    value={customHeader}
                    onChange={e => setCustomHeader(e.target.value)}
                    rows={4}
                    className="w-full px-3 py-2 rounded-xl border border-[#d2d2d7] text-[11px] font-mono resize-y focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-[#86868b] uppercase tracking-wider mb-1.5">서명 · 법적고지 (Footer)</label>
                  <textarea
                    value={customFooter}
                    onChange={e => setCustomFooter(e.target.value)}
                    rows={8}
                    className="w-full px-3 py-2 rounded-xl border border-[#d2d2d7] text-[11px] font-mono resize-y focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                </div>
                <button
                  type="button"
                  onClick={saveDefaults}
                  className="w-full py-2 rounded-xl bg-[#1d1d1f] text-white text-[13px] font-semibold hover:bg-[#424245] transition-colors"
                >
                  {defaultsSaved ? '✅ 저장됨!' : '💾 기본값으로 저장'}
                </button>
                <p className="text-[11px] text-[#86868b]">저장하면 이 브라우저에서 항상 이 서명이 기본으로 적용됩니다.</p>
              </div>
            )}
          </div>

          {/* ── 템플릿 관리 패널 ── */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden">
            <button type="button" onClick={() => setShowTplPanel(v => !v)}
              className="w-full flex items-center justify-between px-4 py-3 text-[13px] font-semibold text-[#1d1d1f] hover:bg-[#f5f5f7] transition-colors">
              <span>📋 템플릿 관리</span>
              <span className="text-[11px] text-[#86868b]">{showTplPanel ? '▲' : '▼'}</span>
            </button>
            {showTplPanel && (
              <div className="border-t border-[#f0f0f0]">
                {/* 탭 */}
                <div className="flex border-b border-[#f0f0f0]">
                  {(['list','edit','new'] as const).map(tab => (
                    <button key={tab} type="button" onClick={() => setTplTab(tab)}
                      className={`flex-1 py-2 text-[11px] font-semibold transition-colors ${
                        tplTab === tab ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600' : 'text-[#86868b] hover:bg-[#f5f5f7]'
                      }`}>
                      {tab === 'list' ? '목록' : tab === 'edit' ? '편집' : '새 템플릿'}
                    </button>
                  ))}
                </div>
                <div className="px-3 py-3">
                  {tplMsg && <p className="text-[11px] text-green-600 mb-2 font-medium">{tplMsg}</p>}

                  {/* 목록 */}
                  {tplTab === 'list' && (
                    <div className="space-y-0.5 max-h-[260px] overflow-y-auto">
                      {templates.length === 0
                        ? <p className="text-[11px] text-[#86868b] py-4 text-center">템플릿 없음</p>
                        : templates.map(t => (
                          <div key={t.template_key} className="flex items-center gap-1 py-2 border-b border-[#f5f5f7] last:border-0">
                            <div className="flex-1 min-w-0">
                              <div className="text-[11px] font-semibold text-[#1d1d1f] truncate">{t.template_key}</div>
                              <div className="text-[10px] text-[#86868b] truncate">{t.subject || '(제목 없음)'}</div>
                            </div>
                            <button type="button" onClick={() => applyTemplate(t.template_key)}
                              className="shrink-0 px-2 py-1 text-[10px] font-semibold text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100 transition-colors">적용</button>
                            <button type="button" onClick={() => { setEditTpl(t); setEditTplSubject(t.subject); setEditTplBody(t.body_html); setTplTab('edit'); }}
                              className="shrink-0 px-2 py-1 text-[10px] font-semibold text-[#555] bg-[#f5f5f7] rounded-md hover:bg-[#e8e8ed] transition-colors">편집</button>
                          </div>
                        ))
                      }
                    </div>
                  )}

                  {/* 편집 */}
                  {tplTab === 'edit' && (editTpl ? (
                    <div className="space-y-2">
                      <p className="text-[11px] font-semibold text-blue-600">{editTpl.template_key}</p>
                      <input value={editTplSubject} onChange={e => setEditTplSubject(e.target.value)} placeholder="제목"
                        className="w-full px-2 py-1.5 rounded-lg border border-[#d2d2d7] text-[12px] focus:outline-none focus:ring-1 focus:ring-blue-500"/>
                      <textarea value={editTplBody} onChange={e => setEditTplBody(e.target.value)} rows={8}
                        className="w-full px-2 py-1.5 rounded-lg border border-[#d2d2d7] text-[11px] font-mono resize-y focus:outline-none focus:ring-1 focus:ring-blue-500"/>
                      <div className="flex gap-2">
                        <button type="button" onClick={saveTpl} disabled={tplSaving}
                          className="flex-1 py-1.5 bg-[#0071e3] text-white text-[12px] font-semibold rounded-lg disabled:opacity-40 hover:bg-[#0077ED] transition-colors">
                          {tplSaving ? '저장 중...' : '저장'}
                        </button>
                        <button type="button" onClick={() => setTplTab('list')}
                          className="px-4 py-1.5 bg-[#f5f5f7] text-[#555] text-[12px] font-semibold rounded-lg hover:bg-[#e8e8ed] transition-colors">취소</button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-[11px] text-[#86868b] py-4 text-center">목록에서 템플릿을 선택하세요</p>
                  ))}

                  {/* 새 템플릿 */}
                  {tplTab === 'new' && (
                    <div className="space-y-2">
                      <input value={newTplKey} onChange={e => setNewTplKey(e.target.value.replace(/[^a-z0-9_]/g, ''))} placeholder="template_key (소문자, 언더스코어)"
                        className="w-full px-2 py-1.5 rounded-lg border border-[#d2d2d7] text-[12px] focus:outline-none focus:ring-1 focus:ring-blue-500"/>
                      <input value={newTplSubject} onChange={e => setNewTplSubject(e.target.value)} placeholder="이메일 제목"
                        className="w-full px-2 py-1.5 rounded-lg border border-[#d2d2d7] text-[12px] focus:outline-none focus:ring-1 focus:ring-blue-500"/>
                      <textarea value={newTplBody} onChange={e => setNewTplBody(e.target.value)} rows={6} placeholder="<p>HTML 본문</p>"
                        className="w-full px-2 py-1.5 rounded-lg border border-[#d2d2d7] text-[11px] font-mono resize-y focus:outline-none focus:ring-1 focus:ring-blue-500"/>
                      <button type="button" onClick={createTpl} disabled={tplSaving || !newTplKey.trim()}
                        className="w-full py-1.5 bg-[#34c759] text-white text-[12px] font-semibold rounded-lg disabled:opacity-40 hover:bg-[#2db84e] transition-colors">
                        {tplSaving ? '생성 중...' : '+ 템플릿 생성'}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      </>)}
    </div>
  )
}


/* ── ProfileBuilder Component ── */
interface ProfileCandidate {
  candidate_id: string
  sheet_number?: number | null
  nationality?: string
  current_location?: string
  photo_url?: string
  thumb_url?: string
  area_prefs?: string
  status?: string
  gender?: string
  dob?: string
}

function ProfileBuilder({
  onInsert,
  signedFetch,
  adminKey,
}: {
  onInsert: (html: string) => void
  signedFetch: (url: string, init?: RequestInit) => Promise<Response>
  adminKey: string
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<ProfileCandidate[]>([])
  const [selected, setSelected] = useState<ProfileCandidate[]>([])
  const [previewHtml, setPreviewHtml] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!adminKey) return
      try {
        const res = await signedFetch(
          `${API}/api/admin/candidates/profile-search?q=${encodeURIComponent(query)}&limit=20`
        )
        const data = await res.json()
        setResults(data.data || [])
      } catch {
        /* silent */
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [query, adminKey, signedFetch])

  const addCandidate = (c: ProfileCandidate) => {
    if (!selected.find((s) => s.candidate_id === c.candidate_id)) {
      setSelected(prev => [...prev, c])
    }
  }

  const moveUp = (idx: number) => {
    if (idx === 0) return
    setSelected(prev => {
      const arr = [...prev]
      ;[arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]]
      return arr
    })
  }

  const moveDown = (idx: number) => {
    setSelected(prev => {
      if (idx >= prev.length - 1) return prev
      const arr = [...prev]
      ;[arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]]
      return arr
    })
  }

  const buildHtml = async () => {
    if (selected.length === 0) return
    setLoading(true)
    try {
      const res = await signedFetch(`${API}/api/admin/candidates/build-profile-html`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_ids: selected.map((c) => c.candidate_id),
          include_intro: true,
          include_footer: true,
        }),
      })
      const data = await res.json()
      setPreviewHtml(data.data?.html || '')
    } catch {
      /* silent */
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex gap-4 h-[calc(100vh-200px)]">
      {/* Left: Search + Results */}
      <div className="w-72 flex flex-col gap-3 shrink-0">
        <input
          type="text"
          placeholder="국적/지역 검색..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          className="w-full px-3 py-2 border border-[#d2d2d7] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
        />
        <div className="flex-1 overflow-y-auto border border-[#d2d2d7] rounded-lg divide-y divide-[#f0f0f0]">
          {results.map((c: ProfileCandidate) => (
            <button
              key={c.candidate_id}
              onClick={() => addCandidate(c)}
              className="w-full px-3 py-2 text-left text-sm hover:bg-[#f5f5f7] flex items-center gap-2"
            >
              {c.photo_url || c.thumb_url ? (
                <img src={c.photo_url || c.thumb_url} className="w-8 h-8 rounded-full object-cover object-top shrink-0" alt="" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-[#e5e7eb] flex items-center justify-center text-xs shrink-0">{'\ud83d\udc64'}</div>
              )}
              <div className="min-w-0">
                <div className="font-medium truncate">{c.sheet_number || c.candidate_id}</div>
                <div className="text-[#6e6e73] text-xs truncate">{c.nationality} · {c.current_location}</div>
              </div>
            </button>
          ))}
          {results.length === 0 && (
            <div className="px-3 py-6 text-center text-[#86868b] text-xs">
              {query ? '결과 없음' : '최근 후보자 로딩 중...'}
            </div>
          )}
        </div>
      </div>

      {/* Center: Selected list */}
      <div className="w-56 flex flex-col gap-2 shrink-0">
        <div className="text-xs font-medium text-[#6e6e73]">선택된 후보자 ({selected.length})</div>
        <div className="flex-1 overflow-y-auto border border-[#d2d2d7] rounded-lg divide-y divide-[#f0f0f0]">
          {selected.map((c: ProfileCandidate, idx: number) => (
            <div key={c.candidate_id} className="px-3 py-2 flex items-center gap-1 text-sm">
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{c.sheet_number || c.candidate_id}</div>
                <div className="text-[#6e6e73] text-xs truncate">{c.nationality}</div>
              </div>
              <div className="flex flex-col gap-0.5">
                <button onClick={() => moveUp(idx)} className="text-[#6e6e73] hover:text-[#1d1d1f] leading-none text-xs">{'\u25b2'}</button>
                <button onClick={() => moveDown(idx)} className="text-[#6e6e73] hover:text-[#1d1d1f] leading-none text-xs">{'\u25bc'}</button>
              </div>
              <button
                onClick={() => setSelected(prev => prev.filter((_, i) => i !== idx))}
                className="text-[#ff3b30] hover:text-red-700 text-xs ml-1"
              >{'\u2715'}</button>
            </div>
          ))}
        </div>
        <button
          onClick={buildHtml}
          disabled={selected.length === 0 || loading}
          className="w-full py-2 bg-[#0071e3] text-white text-sm font-medium rounded-lg disabled:opacity-40 hover:bg-[#0077ed] transition-colors"
        >
          {loading ? '생성 중...' : 'HTML 생성'}
        </button>
      </div>

      {/* Right: Preview */}
      <div className="flex-1 flex flex-col gap-2 min-w-0">
        <div className="text-xs font-medium text-[#6e6e73]">HTML 미리보기</div>
        <div className="flex-1 border border-[#d2d2d7] rounded-lg overflow-auto bg-white p-4">
          {previewHtml ? (
            <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(previewHtml) }} />
          ) : (
            <div className="text-[#6e6e73] text-sm text-center mt-8">
              후보자를 선택 후 &quot;HTML 생성&quot; 클릭
            </div>
          )}
        </div>
        <button
          onClick={() => previewHtml && onInsert(previewHtml)}
          disabled={!previewHtml}
          className="py-2 bg-[#34c759] text-white text-sm font-medium rounded-lg disabled:opacity-40 hover:bg-[#2db34a] transition-colors"
        >
          {'\u2705'} 본문에 삽입 (메일 발송 탭으로 이동)
        </button>
      </div>
    </div>
  )
}
