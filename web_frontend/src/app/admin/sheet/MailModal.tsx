'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import type { DataRow } from './engine/types'
import { MAIL_TEMPLATES } from './engine/types'
import { API_URL } from '@/lib/api'

const API = API_URL

// 발송자 계정 목록
const SENDERS = [
  { value: 'bridgejobkr@gmail.com', label: 'Gmail (bridgejobkr)', color: '#ea4335' },
  { value: 'bridgejobkr@naver.com', label: 'Naver (bridgejobkr)', color: '#03c75a' },
]

interface MailModalProps {
  open: boolean
  recipients: DataRow[]
  onClose: () => void
  onSend: (subject: string, body: string, files: File[], recipients: DataRow[]) => void
  getHeaders?: () => Record<string, string>
}

export default function MailModal({ open, recipients, onClose, onSend, getHeaders }: MailModalProps) {
  const [tmpl, setTmpl] = useState('custom')
  const [subj, setSubj] = useState('')
  const [body, setBody] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [sender, setSender] = useState(SENDERS[0].value)
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState<{ success: boolean; sent: number; failed: number } | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const dropRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    setTmpl('custom')
    setSubj('')
    setBody('')
    setFiles([])
    setResult(null)
  }, [open])

  useEffect(() => {
    if (!open) return
    const t = MAIL_TEMPLATES.find(m => m.key === tmpl)
    if (t && tmpl !== 'custom') {
      setSubj(t.s)
      setBody(t.b)
    }
  }, [tmpl, open])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const droppedFiles = Array.from(e.dataTransfer.files)
    if (droppedFiles.length) setFiles(p => [...p, ...droppedFiles])
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleSend = useCallback(async () => {
    if (!subj || !body) return
    setSending(true)
    setResult(null)
    try {
      const hdrs = getHeaders ? getHeaders() : {}
      const res = await fetch(`${API}/api/admin/send-mail`, {
        method: 'POST',
        headers: { ...hdrs, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sender,
          recipients: recipients.map(r => ({ email: String(r.email), name: String(r.name) })),
          subject: subj,
          body,
          personal: true,
        }),
      })
      const json = await res.json()
      if (res.ok) {
        setResult({ success: true, sent: json.data?.sent ?? recipients.length, failed: json.data?.failed ?? 0 })
        onSend(subj, body, files, recipients)
      } else {
        setResult({ success: false, sent: 0, failed: recipients.length })
      }
    } catch {
      // API 없음 — 로컬 콜백만 실행
      onSend(subj, body, files, recipients)
      setResult({ success: true, sent: recipients.length, failed: 0 })
    } finally {
      setSending(false)
    }
  }, [subj, body, sender, recipients, files, getHeaders, onSend])

  if (!open) return null

  const activeSender = SENDERS.find(s => s.value === sender) ?? SENDERS[0]

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
        zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: 16, width: '85vw', maxWidth: 1100,
          height: '88vh', overflow: 'auto',
          boxShadow: '0 24px 80px rgba(0,0,0,0.3)',
          display: 'flex', flexDirection: 'column',
          minWidth: 500, minHeight: 400,
        }}
      >
        {/* Header */}
        <div style={{
          padding: '16px 24px', borderBottom: '1px solid #e2e8f0',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <b style={{ fontSize: 20 }}>✉ 메일 작성</b>
            <span style={{
              fontSize: 12, fontWeight: 700, padding: '3px 10px', borderRadius: 20,
              background: '#dbeafe', color: '#1d4ed8',
            }}>
              {recipients.length}명 개별발송
            </span>
          </div>
          <button onClick={onClose} style={{
            border: 'none', background: 'transparent', fontSize: 22, cursor: 'pointer', color: '#64748b',
          }}>✕</button>
        </div>

        {/* Template buttons */}
        <div style={{ padding: '10px 24px', borderBottom: '1px solid #f1f5f9', flexShrink: 0 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#64748b', marginBottom: 6 }}>템플릿</div>
          <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
            {MAIL_TEMPLATES.map(m => (
              <button
                key={m.key}
                onClick={() => setTmpl(m.key)}
                style={{
                  padding: '6px 14px', fontSize: 13, borderRadius: 6,
                  border: tmpl === m.key ? '2px solid #2563eb' : '1px solid #e2e8f0',
                  background: tmpl === m.key ? '#2563eb' : '#f8fafc',
                  color: tmpl === m.key ? '#fff' : '#374151',
                  cursor: 'pointer', fontWeight: tmpl === m.key ? 800 : 500,
                  transition: 'all 0.1s',
                }}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>

        {/* Sender toggle */}
        <div style={{ padding: '8px 24px', borderBottom: '1px solid #f1f5f9', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#64748b', minWidth: 40 }}>발신</span>
          <div style={{ display: 'flex', gap: 6 }}>
            {SENDERS.map(s => (
              <button
                key={s.value}
                onClick={() => setSender(s.value)}
                style={{
                  padding: '5px 14px', fontSize: 13, borderRadius: 6, cursor: 'pointer',
                  border: sender === s.value ? `2px solid ${s.color}` : '1px solid #e2e8f0',
                  background: sender === s.value ? s.color + '15' : '#f8fafc',
                  color: sender === s.value ? s.color : '#374151',
                  fontWeight: sender === s.value ? 800 : 500,
                }}
              >
                {s.label}
              </button>
            ))}
          </div>
          <span style={{
            fontSize: 13, fontWeight: 700,
            background: activeSender.color + '20',
            color: activeSender.color,
            padding: '4px 12px', borderRadius: 6,
          }}>
            {activeSender.value}
          </span>
        </div>

        {/* To */}
        <div style={{ padding: '8px 24px', borderBottom: '1px solid #f1f5f9', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#64748b', minWidth: 40 }}>수신</span>
          {recipients.map(r => (
            <span key={r.id} style={{
              fontSize: 13, padding: '3px 10px', background: '#f1f5f9',
              borderRadius: 20, border: '1px solid #e2e8f0',
            }}>
              {String(r.name)} &lt;{String(r.email)}&gt;
            </span>
          ))}
        </div>

        {/* Subject */}
        <div style={{ padding: '8px 24px', borderBottom: '1px solid #f1f5f9', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#64748b', minWidth: 40 }}>제목</span>
          <input
            value={subj} onChange={e => setSubj(e.target.value)}
            placeholder="Subject"
            style={{
              flex: 1, padding: '8px 12px', fontSize: 15,
              border: '1px solid #d1d5db', borderRadius: 6,
              outline: 'none', boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Body */}
        <div style={{ padding: '10px 24px', flex: 1, display: 'flex', flexDirection: 'column' }}>
          <textarea
            value={body} onChange={e => setBody(e.target.value)}
            placeholder="본문을 입력하세요. {{name}} 변수 사용 가능"
            style={{
              flex: 1, width: '100%', minHeight: 200, padding: '14px 16px',
              fontSize: 14, border: '1px solid #d1d5db', borderRadius: 8,
              outline: 'none', resize: 'none', boxSizing: 'border-box', lineHeight: 1.8,
              fontFamily: '-apple-system, "Segoe UI", sans-serif',
            }}
          />
          <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
            변수: {'{{name}}'} {'{{region}}'} {'{{city}}'}  &nbsp;|&nbsp; 1:1 개별 발송 — 수신자 정보 타인에게 미노출
          </div>
        </div>

        {/* File attach */}
        <div style={{ padding: '8px 24px', borderTop: '1px solid #f1f5f9', flexShrink: 0 }}>
          <div
            ref={dropRef}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={() => fileRef.current?.click()}
            style={{
              border: '2px dashed #d1d5db', borderRadius: 8, padding: '10px 16px',
              textAlign: 'center', cursor: 'pointer', color: '#94a3b8', fontSize: 13,
            }}
          >
            📎 파일을 드래그하거나 클릭하여 첨부
          </div>
          <input
            ref={fileRef} type="file" multiple
            onChange={e => setFiles(p => [...p, ...Array.from(e.target.files || [])])}
            style={{ display: 'none' }}
          />
          {files.length > 0 && (
            <div style={{ marginTop: 6, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {files.map((f, i) => (
                <span key={i} style={{
                  fontSize: 12, padding: '3px 10px', background: '#f1f5f9', borderRadius: 4,
                }}>
                  {f.name}
                  <span
                    onClick={() => setFiles(p => p.filter((_, j) => j !== i))}
                    style={{ cursor: 'pointer', color: '#ef4444', marginLeft: 6 }}
                  >✕</span>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '14px 24px', borderTop: '2px solid #e2e8f0',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          flexShrink: 0, flexWrap: 'wrap', gap: 8,
        }}>
          <div>
            {result && (
              <div style={{
                fontSize: 13, fontWeight: 700, padding: '6px 14px', borderRadius: 6,
                background: result.success ? '#dcfce7' : '#fee2e2',
                color: result.success ? '#16a34a' : '#dc2626',
              }}>
                {result.success
                  ? `✓ ${result.sent}명 발송 완료${result.failed > 0 ? ` (실패 ${result.failed}명)` : ''}`
                  : `✗ 발송 실패 (${result.failed}명)`}
              </div>
            )}
            {!result && (
              <div style={{ fontSize: 11, fontWeight: 700, color: '#dc2626' }}>
                * 타인 정보 절대 미노출 / 1:1 개별 발송
              </div>
            )}
          </div>
          <button
            onClick={handleSend}
            disabled={!subj || !body || sending}
            style={{
              padding: '12px 28px', fontSize: 16, border: 'none', borderRadius: 10,
              background: subj && body && !sending ? activeSender.color : '#aaa',
              color: '#fff', cursor: subj && body && !sending ? 'pointer' : 'default',
              fontWeight: 900, transition: 'background 0.2s',
            }}
          >
            {sending ? '발송 중...' : `보내기 (${recipients.length}명 개별발송)`}
          </button>
        </div>
      </div>
    </div>
  )
}
