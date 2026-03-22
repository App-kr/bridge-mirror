'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import { MAIL_TEMPLATES } from './engine/types'
import type { DataRow } from './engine/types'

interface MailModalProps {
  open: boolean
  onClose: () => void
  recipients: DataRow[]
  adminKey: string
  apiUrl: string
}

export default function MailModal({ open, onClose, recipients, adminKey, apiUrl }: MailModalProps) {
  const [tmplKey, setTmplKey] = useState(MAIL_TEMPLATES[0].key)
  const [sender, setSender] = useState<'gmail' | 'naver'>('naver')
  const [subject, setSubject] = useState(MAIL_TEMPLATES[0].s)
  const [body, setBody] = useState(MAIL_TEMPLATES[0].b)
  const [attachments, setAttachments] = useState<File[]>([])
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState('')
  const [previewMode, setPreviewMode] = useState(false)
  const [previewIdx, setPreviewIdx] = useState(0)
  const fileRef = useRef<HTMLInputElement>(null)
  const dropRef = useRef<HTMLDivElement>(null)

  const senderEmail = sender === 'gmail' ? 'bridgejobkr@gmail.com' : 'bridgejobkr@naver.com'

  const applyVars = useCallback((text: string, r: DataRow) => {
    return text
      .replace(/\{\{name\}\}/g, String(r.name ?? r.email ?? 'Teacher'))
      .replace(/\{\{region\}\}/g, String(r.prefRegion ?? ''))
  }, [])

  const applyTemplate = (key: string) => {
    const t = MAIL_TEMPLATES.find(t => t.key === key)
    if (!t) return
    setTmplKey(key)
    setSubject(t.s)
    setBody(t.b)
    setPreviewMode(false)
    setResult('')
  }

  useEffect(() => {
    if (open) {
      applyTemplate(MAIL_TEMPLATES[0].key)
      setAttachments([])
      setResult('')
      setPreviewIdx(0)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  useEffect(() => {
    const el = dropRef.current
    if (!el) return
    const onDrop = (e: DragEvent) => {
      e.preventDefault()
      setAttachments(a => [...a, ...Array.from(e.dataTransfer?.files ?? [])])
    }
    const onDragOver = (e: DragEvent) => e.preventDefault()
    el.addEventListener('drop', onDrop)
    el.addEventListener('dragover', onDragOver)
    return () => { el.removeEventListener('drop', onDrop); el.removeEventListener('dragover', onDragOver) }
  }, [])

  const handleSend = async () => {
    if (!subject.trim() || !body.trim()) { alert('제목과 본문을 입력해주세요'); return }
    if (recipients.length === 0) { alert('수신자가 없습니다'); return }
    setSending(true); setResult('')
    let ok = 0, fail = 0
    for (const r of recipients) {
      const email = String(r.email ?? '')
      if (!email) { fail++; continue }
      try {
        const form = new FormData()
        form.append('sender', sender)
        form.append('to', email)
        form.append('to_name', String(r.name ?? r.email ?? ''))
        form.append('subject', applyVars(subject, r))
        form.append('body', applyVars(body, r))
        attachments.forEach(f => form.append('files', f))
        const res = await fetch(`${apiUrl}/api/admin/mail/send`, {
          method: 'POST',
          headers: { 'x-admin-key': adminKey },
          body: form,
        })
        if (res.ok) ok++; else fail++
      } catch { fail++ }
    }
    setSending(false)
    setResult(fail === 0 ? `✓ ${ok}명 발송 완료` : `✓ ${ok}명 성공 / ✗ ${fail}명 실패`)
  }

  const clearAll = () => {
    setSubject('')
    setBody('')
    setAttachments([])
    setResult('')
    setPreviewMode(false)
  }

  const copyBodyToClipboard = () => {
    const row = recipients[previewIdx]
    const text = row ? applyVars(body, row) : body
    navigator.clipboard.writeText(text).then(() => setResult('클립보드에 복사됨')).catch(() => {})
  }

  if (!open) return null

  const previewRow = recipients[previewIdx]

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'rgba(0,0,0,0.5)', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      padding: 16,
    }} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={{
        width: '95vw', maxWidth: 960, height: '92vh', background: '#fff',
        borderRadius: 16, display: 'flex', flexDirection: 'column',
        boxShadow: '0 25px 80px rgba(0,0,0,0.35)', overflow: 'hidden'
      }}>
        {/* ── Header ── */}
        <div style={{
          padding: '16px 24px', borderBottom: '2px solid #e8e8e8',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: '#1a1a2e'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ fontSize: 20, fontWeight: 800, color: '#fff' }}>
              ✉ 메일 발송
            </span>
            <span style={{
              background: '#4ade80', color: '#14532d', padding: '4px 14px',
              borderRadius: 20, fontSize: 14, fontWeight: 700
            }}>{recipients.length}명</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button onClick={clearAll} style={{
              background: 'rgba(255,255,255,0.15)', border: 'none', color: '#fff',
              fontSize: 13, cursor: 'pointer', padding: '5px 12px', borderRadius: 6, fontWeight: 600
            }}>🗑 초기화</button>
            <button onClick={onClose} style={{
              background: 'none', border: 'none', color: '#fff',
              fontSize: 22, cursor: 'pointer', padding: '0 6px'
            }}>✕</button>
          </div>
        </div>

        {/* ── Template tabs ── */}
        <div style={{
          padding: '10px 24px', borderBottom: '1px solid #f0f0f0',
          display: 'flex', gap: 8, overflowX: 'auto', background: '#fafafa'
        }}>
          {MAIL_TEMPLATES.map(t => (
            <button key={t.key} onClick={() => applyTemplate(t.key)}
              style={{
                padding: '6px 16px', fontSize: 14, borderRadius: 20, border: 'none',
                background: tmplKey === t.key ? '#1a1a2e' : '#eee',
                color: tmplKey === t.key ? '#fff' : '#555',
                cursor: 'pointer', fontWeight: tmplKey === t.key ? 700 : 500,
                whiteSpace: 'nowrap', flexShrink: 0
              }}>
              {t.label}
            </button>
          ))}
        </div>

        {/* ── Sender ── */}
        <div style={{
          padding: '10px 24px', display: 'flex', alignItems: 'center', gap: 12,
          borderBottom: '1px solid #f0f0f0', background: '#fafafa'
        }}>
          <span style={{ fontSize: 14, color: '#666', fontWeight: 600, width: 42 }}>발신</span>
          {(['gmail', 'naver'] as const).map(s => (
            <button key={s} onClick={() => setSender(s)} style={{
              padding: '5px 18px', fontSize: 14, borderRadius: 20,
              border: '2px solid ' + (sender === s ? '#1a1a2e' : '#ddd'),
              background: sender === s ? '#1a1a2e' : '#fff',
              color: sender === s ? '#fff' : '#555',
              cursor: 'pointer', fontWeight: sender === s ? 700 : 500
            }}>{s === 'gmail' ? 'Gmail' : 'Naver'}</button>
          ))}
          <span style={{ fontSize: 13, color: '#888', marginLeft: 4 }}>{senderEmail}</span>
        </div>

        {/* ── Recipients ── */}
        <div style={{
          padding: '10px 24px', display: 'flex', gap: 8, alignItems: 'center',
          borderBottom: '1px solid #f0f0f0', flexWrap: 'wrap',
          maxHeight: 90, overflowY: 'auto'
        }}>
          <span style={{ fontSize: 14, color: '#666', fontWeight: 600, flexShrink: 0 }}>수신</span>
          {recipients.map((r, i) => (
            <span key={i} onClick={() => { setPreviewIdx(i); setPreviewMode(true) }}
              style={{
                background: previewIdx === i && previewMode ? '#1a1a2e' : '#f0f4ff',
                color: previewIdx === i && previewMode ? '#fff' : '#333',
                border: '1px solid ' + (previewIdx === i && previewMode ? '#1a1a2e' : '#c5d0f0'),
                borderRadius: 16, padding: '4px 14px', fontSize: 13, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600
              }}>
              <span>{String(r.name ?? r.email ?? '')}</span>
              {r._cid && <span style={{ fontSize: 11, opacity: 0.6 }}>#{r._cid}</span>}
            </span>
          ))}
        </div>

        {/* ── Subject ── */}
        <div style={{
          padding: '10px 24px', display: 'flex', alignItems: 'center', gap: 12,
          borderBottom: '1px solid #f0f0f0'
        }}>
          <span style={{ fontSize: 14, color: '#666', fontWeight: 600, width: 42 }}>제목</span>
          <input value={subject} onChange={e => setSubject(e.target.value)}
            placeholder='Subject'
            style={{ flex: 1, border: 'none', outline: 'none', fontSize: 15, fontWeight: 600, color: '#111' }} />
        </div>

        {/* ── Preview bar ── */}
        {previewMode && previewRow && (
          <div style={{
            padding: '8px 24px', background: '#fff8e1',
            borderBottom: '1px solid #ffe082',
            display: 'flex', alignItems: 'center', gap: 10, fontSize: 13
          }}>
            <span style={{ fontWeight: 700 }}>👁 미리보기:</span>
            <select value={previewIdx}
              onChange={e => setPreviewIdx(Number(e.target.value))}
              style={{ fontSize: 13, border: '1px solid #ccc', borderRadius: 4, padding: '2px 8px' }}>
              {recipients.map((r, i) => (
                <option key={i} value={i}>
                  {String(r.name ?? r.email ?? '')} ({String(r.email ?? '')})
                </option>
              ))}
            </select>
            <button onClick={copyBodyToClipboard}
              style={{ fontSize: 12, padding: '3px 10px', border: '1px solid #ccc', borderRadius: 4, cursor: 'pointer', background: '#fff', fontWeight: 600 }}>
              📋 복사
            </button>
            <button onClick={() => setPreviewMode(false)}
              style={{ fontSize: 12, padding: '3px 10px', border: '1px solid #ccc', borderRadius: 4, cursor: 'pointer', background: '#fff', fontWeight: 600 }}>
              ← 편집
            </button>
          </div>
        )}

        {/* ── Body ── */}
        <div style={{ flex: 1, position: 'relative', minHeight: 250 }}>
          {previewMode && previewRow ? (
            <div style={{
              padding: '20px 24px', height: '100%', overflowY: 'auto',
              fontSize: 15, lineHeight: 1.8, whiteSpace: 'pre-wrap',
              color: '#111', fontFamily: 'Arial, sans-serif'
            }}>
              <div style={{ marginBottom: 10, color: '#888', fontSize: 13, fontWeight: 600 }}>
                제목: {applyVars(subject, previewRow)}
              </div>
              <hr style={{ border: 'none', borderTop: '1px solid #eee', marginBottom: 14 }} />
              {applyVars(body, previewRow)}
            </div>
          ) : (
            <textarea value={body} onChange={e => setBody(e.target.value)}
              placeholder='본문 입력 — {{name}} {{region}} 변수 사용 가능'
              style={{
                width: '100%', height: '100%', minHeight: 250,
                border: 'none', outline: 'none', resize: 'none',
                padding: '18px 24px', fontSize: 15, lineHeight: 1.8,
                fontFamily: 'Arial, sans-serif', color: '#111',
                boxSizing: 'border-box'
              }} />
          )}
        </div>

        {/* ── Variables hint + toggle ── */}
        <div style={{
          padding: '6px 24px', background: '#fafafa',
          borderTop: '1px solid #f0f0f0', fontSize: 13, color: '#888',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center'
        }}>
          <span>변수: {'{{name}}'} {'{{region}}'} · 1:1 개별 발송</span>
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={copyBodyToClipboard}
              style={{
                fontSize: 12, padding: '3px 12px', border: '1px solid #ccc',
                borderRadius: 4, cursor: 'pointer', background: '#fff', fontWeight: 600
              }}>📋 복사</button>
            <button onClick={() => setPreviewMode(p => !p)}
              style={{
                fontSize: 12, padding: '3px 12px', border: '1px solid #ccc',
                borderRadius: 4, cursor: 'pointer',
                background: previewMode ? '#1a1a2e' : '#fff',
                color: previewMode ? '#fff' : '#333', fontWeight: 600
              }}>
              {previewMode ? '✏ 편집' : '👁 미리보기'}
            </button>
          </div>
        </div>

        {/* ── Attachments ── */}
        <div ref={dropRef} onClick={() => fileRef.current?.click()}
          style={{
            margin: '10px 24px', border: '2px dashed #ccc', borderRadius: 10,
            padding: '14px', textAlign: 'center', cursor: 'pointer',
            background: '#fafafa', fontSize: 14, color: '#888'
          }}>
          📎 파일 드래그 또는 클릭하여 첨부
          {attachments.length > 0 && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', marginTop: 8 }}>
              {attachments.map((f, i) => (
                <span key={i} style={{
                  background: '#e8eaf6', padding: '4px 12px', borderRadius: 12,
                  fontSize: 13, display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600
                }}>
                  {f.name} <span style={{ fontSize: 11, color: '#999' }}>({(f.size/1024).toFixed(0)}KB)</span>
                  <span onClick={e => { e.stopPropagation(); setAttachments(a => a.filter((_, j) => j !== i)) }}
                    style={{ cursor: 'pointer', color: '#e53935', fontWeight: 700, fontSize: 14 }}>✕</span>
                </span>
              ))}
            </div>
          )}
        </div>
        <input ref={fileRef} type='file' multiple style={{ display: 'none' }}
          onChange={e => setAttachments(a => [...a, ...Array.from(e.target.files ?? [])])} />

        {/* ── Footer ── */}
        <div style={{
          padding: '14px 24px', borderTop: '2px solid #e8e8e8',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: '#fafafa'
        }}>
          <div>
            <div style={{ fontSize: 12, color: '#d32f2f', marginBottom: 3, fontWeight: 600 }}>
              * 타인 정보 절대 미노출 · 1:1 개별 발송
            </div>
            {result && (
              <div style={{ fontSize: 14, fontWeight: 700, color: result.startsWith('✓') ? '#2e7d32' : '#c62828' }}>
                {result}
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button onClick={onClose}
              style={{ padding: '10px 24px', fontSize: 15, cursor: 'pointer', border: '1px solid #ccc', borderRadius: 8, background: '#fff', fontWeight: 600 }}>
              취소
            </button>
            <button onClick={handleSend} disabled={sending}
              style={{
                padding: '10px 32px', fontSize: 15, cursor: sending ? 'not-allowed' : 'pointer',
                background: sending ? '#bbb' : '#1a1a2e', color: '#fff',
                border: 'none', borderRadius: 8, fontWeight: 800
              }}>
              {sending ? '발송중...' : `📧 보내기 (${recipients.length}명)`}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
