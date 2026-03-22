'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'
import { Paperclip, Send, X, Check } from 'lucide-react'

const API = API_URL

interface QuickMailProps {
  preSelectedEmail?: string
  preSelectedName?: string
  onClose?: () => void
  onSent?: () => void
}

const TEMPLATES = [
  {
    key: 'intro',
    label: 'Introduction',
    subject: 'Introduction — BRIDGE Recruitment',
    body: 'Dear {{name}},\n\nThank you for your interest in teaching English in Korea through BRIDGE.\n\nWe have reviewed your application and would like to discuss potential opportunities with you.\n\nPlease let us know your availability for a brief call or video meeting.\n\nBest regards,\nBRIDGE Recruitment Team',
  },
  {
    key: 'interview',
    label: 'Interview',
    subject: 'Interview Schedule — BRIDGE',
    body: 'Dear {{name}},\n\nWe would like to schedule an interview with you regarding teaching positions in Korea.\n\nPlease let us know your available dates and times, and we will coordinate accordingly.\n\nBest regards,\nBRIDGE Recruitment Team',
  },
  {
    key: 'contract',
    label: 'Contract',
    subject: 'Contract Details — BRIDGE',
    body: 'Dear {{name}},\n\nPlease find the contract details below.\n\nKindly review the terms and conditions at your earliest convenience and let us know if you have any questions.\n\nBest regards,\nBRIDGE Recruitment Team',
  },
  {
    key: 'followup',
    label: 'Follow Up',
    subject: 'Follow Up — BRIDGE',
    body: 'Dear {{name}},\n\nJust following up on our previous conversation.\n\nWe wanted to check if you had any questions or if there is anything else we can help with.\n\nBest regards,\nBRIDGE Recruitment Team',
  },
  {
    key: 'custom',
    label: 'Custom',
    subject: '',
    body: '',
  },
]

export default function QuickMail({ preSelectedEmail, preSelectedName, onClose, onSent }: QuickMailProps) {
  const { signedFetch } = useAdminAuth()
  const [to, setTo] = useState(preSelectedEmail || '')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [files, setFiles] = useState<File[]>([])
  const [sending, setSending] = useState(false)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  // Update 'to' field if preSelectedEmail changes
  useEffect(() => {
    if (preSelectedEmail) setTo(preSelectedEmail)
  }, [preSelectedEmail])

  const applyTemplate = useCallback((key: string) => {
    setSelectedTemplate(key)
    const tpl = TEMPLATES.find(t => t.key === key)
    if (!tpl) return
    const name = preSelectedName || 'Candidate'
    setSubject(tpl.subject)
    setBody(tpl.body.replace(/\{\{name\}\}/g, name))
  }, [preSelectedName])

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newFiles = Array.from(e.target.files || [])
    setFiles(prev => [...prev, ...newFiles])
    if (fileRef.current) fileRef.current.value = ''
  }, [])

  const removeFile = useCallback((idx: number) => {
    setFiles(prev => prev.filter((_, i) => i !== idx))
  }, [])

  const handleSend = useCallback(async () => {
    if (!to.trim()) {
      setToast({ type: 'error', message: '수신자 이메일을 입력하세요' })
      return
    }
    if (!subject.trim()) {
      setToast({ type: 'error', message: '제목을 입력하세요' })
      return
    }

    setSending(true)
    setToast(null)

    try {
      const formData = new FormData()
      formData.append('to', to.trim())
      formData.append('subject', subject.trim())
      // Wrap body in basic HTML
      const htmlBody = `<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px; line-height: 1.6; color: #333;">${body.replace(/\n/g, '<br>')}</div>`
      formData.append('body_html', htmlBody)
      files.forEach(f => formData.append('attachments', f))

      const res = await signedFetch(`${API}/api/admin/mail/send`, {
        method: 'POST',
        body: formData,
      })

      if (res.ok) {
        setToast({ type: 'success', message: '메일이 발송되었습니다' })
        setSubject('')
        setBody('')
        setFiles([])
        setSelectedTemplate(null)
        onSent?.()
      } else {
        const json = await res.json().catch(() => ({}))
        setToast({ type: 'error', message: json.error || '발송에 실패했습니다' })
      }
    } catch {
      setToast({ type: 'error', message: '네트워크 오류가 발생했습니다' })
    } finally {
      setSending(false)
    }
  }, [to, subject, body, files, signedFetch, onSent])

  // Auto-dismiss toast
  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 3000)
    return () => clearTimeout(timer)
  }, [toast])

  return (
    <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#f5f5f7]">
        <h3 className="text-[15px] font-semibold text-[#1d1d1f]">메일 작성</h3>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-[#f5f5f7]"
          >
            <X size={16} className="text-[#86868b]" />
          </button>
        )}
      </div>

      <div className="p-4 space-y-3">
        {/* To field */}
        <div>
          <label className="text-xs font-medium text-[#86868b] mb-1 block">To</label>
          <input
            type="email"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            placeholder="recipient@email.com"
            className="w-full px-3 py-2.5 rounded-xl bg-[#f5f5f7] border border-[#e5e5e7] text-sm text-[#1d1d1f] placeholder:text-[#aeaeb2] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 min-h-[44px]"
          />
        </div>

        {/* Template selector */}
        <div>
          <label className="text-xs font-medium text-[#86868b] mb-1.5 block">Template</label>
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
            {TEMPLATES.map(tpl => (
              <button
                key={tpl.key}
                type="button"
                onClick={() => applyTemplate(tpl.key)}
                className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-medium min-h-[32px] transition-colors ${
                  selectedTemplate === tpl.key
                    ? 'bg-[#0071e3] text-white'
                    : 'bg-[#f5f5f7] text-[#86868b] border border-[#e5e5e7]'
                }`}
              >
                {tpl.label}
              </button>
            ))}
          </div>
        </div>

        {/* Subject field */}
        <div>
          <label className="text-xs font-medium text-[#86868b] mb-1 block">Subject</label>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Email subject"
            className="w-full px-3 py-2.5 rounded-xl bg-[#f5f5f7] border border-[#e5e5e7] text-sm text-[#1d1d1f] placeholder:text-[#aeaeb2] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 min-h-[44px]"
          />
        </div>

        {/* Body textarea */}
        <div>
          <label className="text-xs font-medium text-[#86868b] mb-1 block">Body</label>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Write your message..."
            rows={5}
            className="w-full px-3 py-2.5 rounded-xl bg-[#f5f5f7] border border-[#e5e5e7] text-sm text-[#1d1d1f] placeholder:text-[#aeaeb2] focus:outline-none focus:ring-2 focus:ring-[#0071e3]/30 resize-y min-h-[120px]"
          />
        </div>

        {/* Attachments */}
        <div>
          <input
            ref={fileRef}
            type="file"
            multiple
            onChange={handleFileChange}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[#f5f5f7] text-sm text-[#86868b] font-medium min-h-[40px] active:opacity-80 transition-opacity"
          >
            <Paperclip size={14} />
            파일 첨부
          </button>
          {files.length > 0 && (
            <div className="mt-2 space-y-1">
              {files.map((f, i) => (
                <div key={`${f.name}-${i}`} className="flex items-center gap-2 text-xs text-[#1d1d1f] bg-[#f5f5f7] rounded-lg px-3 py-1.5">
                  <span className="flex-1 truncate">{f.name}</span>
                  <span className="text-[#aeaeb2] shrink-0">{(f.size / 1024).toFixed(0)}KB</span>
                  <button
                    type="button"
                    onClick={() => removeFile(i)}
                    className="shrink-0"
                  >
                    <X size={12} className="text-[#aeaeb2]" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Send button */}
        <button
          type="button"
          onClick={handleSend}
          disabled={sending || !to.trim() || !subject.trim()}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-[#0071e3] text-white text-sm font-semibold min-h-[48px] disabled:opacity-40 active:opacity-80 transition-opacity"
        >
          {sending ? (
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <Send size={16} />
              발송
            </>
          )}
        </button>
      </div>

      {/* Toast */}
      {toast && (
        <div className={`mx-4 mb-4 flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium ${
          toast.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {toast.type === 'success' ? <Check size={16} /> : <X size={16} />}
          {toast.message}
        </div>
      )}
    </div>
  )
}
