'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import type { DataRow } from './engine/types'
import { MAIL_TEMPLATES } from './engine/types'

interface MailModalProps {
  open: boolean
  recipients: DataRow[]
  onClose: () => void
  onSend: (subject: string, body: string, files: File[], recipients: DataRow[]) => void
}

export default function MailModal({ open, recipients, onClose, onSend }: MailModalProps) {
  const [tmpl, setTmpl] = useState('custom')
  const [subj, setSubj] = useState('')
  const [body, setBody] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const fileRef = useRef<HTMLInputElement>(null)
  const dropRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    setTmpl('custom')
    setSubj('')
    setBody('')
    setFiles([])
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

  if (!open) return null

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
          display: 'flex', justifyContent: 'space-between', flexShrink: 0,
        }}>
          <b style={{ fontSize: 22 }}>Mail Compose</b>
          <button onClick={onClose} style={{
            border: 'none', background: 'transparent', fontSize: 26, cursor: 'pointer',
          }}>x</button>
        </div>

        {/* Template buttons */}
        <div style={{ padding: '12px 24px', borderBottom: '1px solid #f1f5f9', flexShrink: 0 }}>
          <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
            {MAIL_TEMPLATES.map(m => (
              <button
                key={m.key}
                onClick={() => setTmpl(m.key)}
                style={{
                  padding: '8px 16px', fontSize: 14, borderRadius: 8,
                  border: tmpl === m.key ? '2px solid #2563eb' : '1px solid #e2e8f0',
                  background: tmpl === m.key ? '#2563eb' : '#fff',
                  color: tmpl === m.key ? '#fff' : '#333',
                  cursor: 'pointer', fontWeight: tmpl === m.key ? 800 : 500,
                }}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>

        {/* From */}
        <div style={{ padding: '10px 24px', borderBottom: '1px solid #f1f5f9', flexShrink: 0 }}>
          <span style={{
            fontSize: 15, fontWeight: 700, background: '#fef9c3',
            padding: '4px 14px', borderRadius: 6,
          }}>
            From: bridgejobkr@gmail.com
          </span>
        </div>

        {/* To */}
        <div style={{ padding: '10px 24px', borderBottom: '1px solid #f1f5f9', flexShrink: 0 }}>
          <span style={{ fontSize: 14, color: '#666' }}>To: </span>
          {recipients.map(r => (
            <span key={r.id} style={{
              fontSize: 14, padding: '3px 10px', background: '#f1f5f9',
              borderRadius: 6, marginLeft: 4,
            }}>
              {String(r.name)} &lt;{String(r.email)}&gt;
            </span>
          ))}
        </div>

        {/* Subject */}
        <div style={{ padding: '10px 24px', flexShrink: 0 }}>
          <input
            value={subj} onChange={e => setSubj(e.target.value)}
            placeholder="Subject"
            style={{
              width: '100%', padding: '12px 16px', fontSize: 17,
              border: '1px solid #d1d5db', borderRadius: 8,
              outline: 'none', boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Body */}
        <div style={{ padding: '10px 24px', flex: 1, display: 'flex', flexDirection: 'column' }}>
          <textarea
            value={body} onChange={e => setBody(e.target.value)}
            placeholder="Body"
            style={{
              flex: 1, width: '100%', minHeight: 200, padding: '16px 18px',
              fontSize: 16, border: '1px solid #d1d5db', borderRadius: 8,
              outline: 'none', resize: 'none', boxSizing: 'border-box', lineHeight: 1.8,
            }}
          />
          <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>
            {'Vars: {{name}} {{region}} {{city}}'}
          </div>
        </div>

        {/* File attach */}
        <div style={{ padding: '10px 24px', borderTop: '1px solid #f1f5f9', flexShrink: 0 }}>
          <div
            ref={dropRef}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={() => fileRef.current?.click()}
            style={{
              border: '2px dashed #d1d5db', borderRadius: 10, padding: 18,
              textAlign: 'center', cursor: 'pointer', color: '#94a3b8',
            }}
          >
            파일을 드래그하거나 클릭하여 첨부
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
                  fontSize: 13, padding: '4px 12px', background: '#f1f5f9', borderRadius: 6,
                }}>
                  {f.name}
                  <span
                    onClick={() => setFiles(p => p.filter((_, j) => j !== i))}
                    style={{ cursor: 'pointer', color: '#ef4444', marginLeft: 8 }}
                  >
                    x
                  </span>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 24px', borderTop: '2px solid #e2e8f0',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          flexShrink: 0, flexWrap: 'wrap', gap: 8,
        }}>
          <div>
            <span style={{
              fontSize: 14, background: '#fef9c3', padding: '3px 10px', borderRadius: 4,
            }}>
              bridgejobkr@gmail.com
            </span>
            <div style={{ fontSize: 12, color: '#dc2626', fontWeight: 700, marginTop: 4 }}>
              * 타인 정보 절대 미노출 / 1:1 개별 발송
            </div>
          </div>
          <button
            onClick={() => { onSend(subj, body, files, recipients); onClose() }}
            disabled={!subj || !body}
            style={{
              padding: '14px 32px', fontSize: 18, border: 'none', borderRadius: 12,
              background: subj && body ? '#03c75a' : '#aaa',
              color: '#fff', cursor: subj && body ? 'pointer' : 'default', fontWeight: 900,
            }}
          >
            보내기 ({recipients.length}명 개별발송)
          </button>
        </div>
      </div>
    </div>
  )
}
