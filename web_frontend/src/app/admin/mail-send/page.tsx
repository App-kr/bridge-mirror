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

const BODY_HEADER = `<p>Dear Teacher,</p>

<p></p>

<p></p>`

const BODY_FOOTER = `<p>Kind Regards,<br/>
<strong>BRIDGE Recruitment Team</strong><br/>
📧 bridgejobkr@gmail.com<br/>
🌐 bridge-chi-lime.vercel.app</p>

<hr style="border:none;border-top:1px solid #eee;margin:20px 0"/>

<p style="font-size:11px;color:#888;line-height:1.6">
[기밀성 및 법적 고지] 본 메일은 지정된 수신자에게만 전달된 것으로, 고용주 또는 채용 관리자가 아니거나 퇴사자일 경우 열람·보관·전달을 금지하며 즉시 수신자 제거 요청 후 삭제해주시기 바랍니다. 특히 영어 강사로 근무 중이시더라도 과거에 잠시 이력서 관리 업무를 담당하셨던 경우라면, 현재 권한이 없으므로 반드시 삭제 및 수신 거부 요청을 해주셔야 합니다. 무단 수신은 법적 책임이 발생할 수 있으며, 본 메일은 분쟁 시 증거로 활용될 수 있습니다.<br/><br/>
This email is intended for the designated recipient only. If you are not the intended recipient, or even if you are an English instructor who previously handled resume management but no longer holds that responsibility, please reply requesting removal from our mailing list and delete this email immediately.
</p>`

const DEFAULT_BODY = `${BODY_HEADER}\n\n${BODY_FOOTER}`

export default function MailSendPage() {
  const { adminKey, authed, login, signedFetch, waking } = useAdminAuth()

  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(false)
  const [showTemplateMenu, setShowTemplateMenu] = useState(false)

  // Form state
  const [sender, setSender] = useState<string>(SENDERS[0].value)
  const [recipientText, setRecipientText] = useState('')
  const [subject, setSubject] = useState('')
  const [bodyHtml, setBodyHtml] = useState(() => {
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
            <img src="https://ssl.pstatic.net/static/mail/icons/favicon/favicon-32x32.png" width={16} height={16} style={{ borderRadius: 3 }} alt="naver" />
            네이버 메일
          </a>
          <a
            href="https://mail.google.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[#444] text-[13px] font-semibold no-underline border border-[#ddd] transition-opacity hover:opacity-85"
            style={{ background: '#fff', boxShadow: '0 2px 6px rgba(0,0,0,0.08)' }}
          >
            <img src="https://ssl.gstatic.com/ui/v1/icons/mail/rfr/gmail.ico" width={16} height={16} alt="gmail" />
            Gmail
          </a>
        </div>
      </div>

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
            className="flex items-center gap-1 px-4 py-1.5 bg-white border border-[#c8d6f0] text-[#555] text-[13px] font-semibold rounded-md hover:bg-[#e8eef8] transition-colors"
          >
            <FileText size={13} />
            템플릿
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

          {/* Body */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-4">
            <div className="flex items-center justify-between mb-2">
              <label className="text-[11px] font-semibold text-[#86868b] uppercase tracking-wider">본문 (HTML)</label>
              <button
                type="button"
                onClick={() => setShowPreview(!showPreview)}
                className="text-[12px] text-blue-600 hover:underline font-medium"
              >
                {showPreview ? 'HTML 편집' : '미리보기'}
              </button>
            </div>
            {showPreview ? (
              <div
                className="w-full min-h-[280px] px-4 py-3 rounded-xl border border-[#d2d2d7] bg-[#fafafa] text-[13px] prose prose-sm max-w-none overflow-y-auto"
                style={{ fontFamily: font, fontSize: '14px' }}
                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(bodyHtml) }}
              />
            ) : (
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
        </div>
      </div>
    </div>
  )
}
