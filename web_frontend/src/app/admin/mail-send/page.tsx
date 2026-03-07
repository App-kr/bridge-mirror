'use client'

/**
 * /admin/mail-send - 메일 발송
 * MailComposer를 독립 페이지로 제공 (수신자 직접 입력 + 템플릿 선택)
 */

import { useCallback, useEffect, useState } from 'react'
import AdminAuth from '@/components/admin/AdminAuth'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import DOMPurify from 'dompurify'
import { API_URL } from '@/lib/api'
import { Mail, Send, Users, FileText, AlertCircle, CheckCircle2 } from 'lucide-react'

const API = API_URL

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

export default function MailSendPage() {
  const { adminKey, authed, login, signedFetch, waking } = useAdminAuth()

  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(false)

  // Form state
  const [sender, setSender] = useState<string>(SENDERS[0].value)
  const [recipientText, setRecipientText] = useState('')
  const [subject, setSubject] = useState('')
  const [bodyHtml, setBodyHtml] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState<SendResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showPreview, setShowPreview] = useState(false)

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
      // silent fail - templates are optional
    } finally {
      setLoading(false)
    }
  }, [adminKey])

  useEffect(() => {
    if (authed) fetchTemplates()
  }, [authed, fetchTemplates])

  // Apply template
  const applyTemplate = (key: string) => {
    setSelectedTemplate(key)
    const t = templates.find(tp => tp.template_key === key)
    if (t) {
      setSubject(t.subject)
      setBodyHtml(t.body_html)
    }
  }

  // Parse recipients
  const parseRecipients = (): string[] => {
    return recipientText
      .split(/[\n,;]+/)
      .map(e => e.trim())
      .filter(e => e && e.includes('@'))
  }

  // Send
  const handleSend = async () => {
    const recipients = parseRecipients()
    if (recipients.length === 0) {
      setError('수신자 이메일을 입력해주세요.')
      return
    }
    if (!subject.trim()) {
      setError('제목을 입력해주세요.')
      return
    }
    if (!bodyHtml.trim()) {
      setError('본문을 입력해주세요.')
      return
    }

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
        }),
      })
      const json = await res.json()
      if (!res.ok) {
        throw new Error(json.detail || json.message || `Error ${res.status}`)
      }
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
    <div className="max-w-[1100px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[22px] font-bold text-[#1d1d1f] tracking-tight flex items-center gap-2">
            <Mail size={22} className="text-blue-600" />
            메일 발송
          </h1>
          <p className="text-[13px] text-[#86868b] mt-0.5">직접 수신자를 입력하여 메일을 발송합니다</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
        {/* Left: Compose */}
        <div className="space-y-4">
          {/* Sender */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
            <label className="block text-[12px] font-semibold text-[#86868b] uppercase tracking-wider mb-2">발신자</label>
            <select
              value={sender}
              onChange={e => setSender(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-[#d2d2d7] text-[14px] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            >
              {SENDERS.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          {/* Recipients */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
            <div className="flex items-center justify-between mb-2">
              <label className="text-[12px] font-semibold text-[#86868b] uppercase tracking-wider flex items-center gap-1.5">
                <Users size={14} />
                수신자
              </label>
              <span className="text-[12px] text-[#86868b]">{recipients.length}명</span>
            </div>
            <textarea
              value={recipientText}
              onChange={e => setRecipientText(e.target.value)}
              placeholder="이메일 주소를 입력하세요 (줄바꿈, 콤마, 세미콜론으로 구분)&#10;예: teacher1@school.com&#10;teacher2@academy.kr"
              rows={5}
              className="w-full px-4 py-3 rounded-xl border border-[#d2d2d7] text-[13px] resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono"
            />
          </div>

          {/* Subject */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
            <label className="block text-[12px] font-semibold text-[#86868b] uppercase tracking-wider mb-2">제목</label>
            <input
              type="text"
              value={subject}
              onChange={e => setSubject(e.target.value)}
              placeholder="이메일 제목"
              className="w-full px-4 py-2.5 rounded-xl border border-[#d2d2d7] text-[14px] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>

          {/* Body */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
            <div className="flex items-center justify-between mb-2">
              <label className="text-[12px] font-semibold text-[#86868b] uppercase tracking-wider">본문 (HTML)</label>
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
                className="w-full min-h-[200px] px-4 py-3 rounded-xl border border-[#d2d2d7] bg-[#fafafa] text-[13px] prose prose-sm max-w-none overflow-y-auto"
                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(bodyHtml) }}
              />
            ) : (
              <textarea
                value={bodyHtml}
                onChange={e => setBodyHtml(e.target.value)}
                placeholder="<p>HTML 본문을 입력하세요</p>"
                rows={10}
                className="w-full px-4 py-3 rounded-xl border border-[#d2d2d7] text-[13px] resize-y focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-mono"
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
            className="w-full py-3.5 bg-[#0071e3] text-white text-[15px] font-semibold rounded-2xl hover:bg-[#0077ED] disabled:opacity-40 transition-colors flex items-center justify-center gap-2"
          >
            {sending ? (
              <>발송 중...</>
            ) : (
              <>
                <Send size={18} />
                메일 발송 ({recipients.length}명)
              </>
            )}
          </button>
        </div>

        {/* Right: Templates */}
        <div className="space-y-4">
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
            <h3 className="text-[14px] font-semibold text-[#1d1d1f] mb-3 flex items-center gap-1.5">
              <FileText size={16} />
              템플릿
            </h3>
            {loading ? (
              <div className="py-6 text-center text-[13px] text-[#86868b]">로딩 중...</div>
            ) : templates.length === 0 ? (
              <div className="py-6 text-center text-[13px] text-[#86868b]">
                템플릿이 없습니다.<br />
                <a href="/admin/email-templates" className="text-blue-600 hover:underline">템플릿 관리</a>에서 생성하세요.
              </div>
            ) : (
              <div className="space-y-1.5 max-h-[500px] overflow-y-auto">
                {templates.map(t => (
                  <button
                    key={t.template_key}
                    type="button"
                    onClick={() => applyTemplate(t.template_key)}
                    className={`w-full text-left px-3 py-2.5 rounded-xl text-[13px] transition-colors ${
                      selectedTemplate === t.template_key
                        ? 'bg-blue-50 text-blue-700 border border-blue-200'
                        : 'hover:bg-[#f5f5f7] text-[#424245] border border-transparent'
                    }`}
                  >
                    <div className="font-medium truncate">{t.template_key}</div>
                    <div className="text-[11px] text-[#86868b] truncate mt-0.5">{t.subject}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Quick Info */}
          <div className="bg-white rounded-2xl border border-[#e5e5e7] p-5">
            <h3 className="text-[14px] font-semibold text-[#1d1d1f] mb-3">발송 안내</h3>
            <div className="space-y-2 text-[12px] text-[#86868b]">
              <p>&#x2022; 개별 발송 (CC/BCC 사용 안 함)</p>
              <p>&#x2022; 발송 간격: 3초</p>
              <p>&#x2022; 일일 한도: 200건</p>
              <p>&#x2022; Reply-To: bridgejobkr@gmail.com</p>
              <p>&#x2022; 발송 기록은 메일 로그에서 확인</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
