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

  if (!open) return null

  const previewRow = recipients[previewIdx]

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'rgba(0,0,0,0.45)', display: 'flex',
      alignItems: 'center', justifyContent: 'center'
    }} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={{
        width: 680, maxHeight: '90vh', background: '#fff',
        borderRadius: 10, display: 'flex', flexDirection: 'column',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)', overflow: 'hidden'
      }}>
        {/* 헤더 */}
        <div style={{
          padding: '14px 20px', borderBottom: '1px solid #e8e8e8',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: '#1a1a2e'
        }}>
          <span style={{ fontSize: 15, fontWeight: 700, color: '#fff' }}>
            메일 발송 — 구직자
          </span>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: '#fff',
            fontSize: 18, cursor: 'pointer', padding: '0 4px'
          }}>✕</button>
        </div>

        {/* 템플릿 탭 */}
        <div style={{
          padding: '8px 20px', borderBottom: '1px solid #f0f0f0',
          display: 'flex', gap: 6, overflowX: 'auto', background: '#fafafa'
        }}>
          {MAIL_TEMPLATES.map(t => (
            <button key={t.key} onClick={() => applyTemplate(t.key)}
              style={{
                padding: '4px 12px', fontSize: 12, borderRadius: 16, border: 'none',
                background: tmplKey === t.key ? '#1a1a2e' : '#eee',
                color: tmplKey === t.key ? '#fff' : '#555',
                cursor: 'pointer', fontWeight: tmplKey === t.key ? 700 : 400,
                whiteSpace: 'nowrap', flexShrink: 0
              }}>
              {t.label}
            </button>
          ))}
        </div>

        {/* 발신자 선택 */}
        <div style={{
          padding: '8px 20px', display: 'flex', alignItems: 'center', gap: 8,
          borderBottom: '1px solid #f0f0f0', background: '#fafafa'
        }}>
          <span style={{ fontSize: 12, color: '#888', width: 36 }}>발신</span>
          {(['gmail', 'naver'] as const).map(s => (
            <button key={s} onClick={() => setSender(s)} style={{
              padding: '3px 14px', fontSize: 12, borderRadius: 20,
              border: '1.5px solid ' + (sender === s ? '#1a1a2e' : '#ddd'),
              background: sender === s ? '#1a1a2e' : '#fff',
              color: sender === s ? '#fff' : '#555',
              cursor: 'pointer', fontWeight: sender === s ? 700 : 400
            }}>{s === 'gmail' ? 'Gmail' : 'Naver'}</button>
          ))}
          <span style={{ fontSize: 11, color: '#aaa', marginLeft: 4 }}>{senderEmail}</span>
          <div style={{ marginLeft: 'auto' }}>
            <span style={{
              background: '#e8f5e9', color: '#2e7d32', padding: '3px 10px',
              borderRadius: 12, fontSize: 11, fontWeight: 700
            }}>{recipients.length}명 개별발송</span>
          </div>
        </div>

        {/* 수신자 칩 */}
        <div style={{
          padding: '8px 20px', display: 'flex', gap: 6, alignItems: 'center',
          borderBottom: '1px solid #f0f0f0', flexWrap: 'wrap',
          maxHeight: 80, overflowY: 'auto'
        }}>
          <span style={{ fontSize: 12, color: '#888', flexShrink: 0 }}>수신</span>
          {recipients.map((r, i) => (
            <span key={i} onClick={() => { setPreviewIdx(i); setPreviewMode(true) }}
              style={{
                background: '#f0f4ff', border: '1px solid #c5d0f0', borderRadius: 12,
                padding: '3px 10px', fontSize: 11, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 4
              }}>
              <span>{String(r.name ?? r.email ?? '')}</span>
              <span style={{ color: '#888', fontSize: 10 }}>({String(r.email ?? '')})</span>
            </span>
          ))}
        </div>

        {/* 제목 */}
        <div style={{
          padding: '8px 20px', display: 'flex', alignItems: 'center', gap: 8,
          borderBottom: '1px solid #f0f0f0'
        }}>
          <span style={{ fontSize: 12, color: '#888', width: 36 }}>제목</span>
          <input value={subject} onChange={e => setSubject(e.target.value)}
            placeholder='Subject'
            style={{ flex: 1, border: 'none', outline: 'none', fontSize: 13, color: '#111' }} />
        </div>

        {/* 미리보기 바 */}
        {previewMode && previewRow && (
          <div style={{
            padding: '6px 20px', background: '#fff8e1',
            borderBottom: '1px solid #ffe082',
            display: 'flex', alignItems: 'center', gap: 8, fontSize: 11
          }}>
            <span>미리보기:</span>
            <select value={previewIdx}
              onChange={e => setPreviewIdx(Number(e.target.value))}
              style={{ fontSize: 11, border: '1px solid #ccc', borderRadius: 3 }}>
              {recipients.map((r, i) => (
                <option key={i} value={i}>
                  {String(r.name ?? r.email ?? '')} ({String(r.email ?? '')})
                </option>
              ))}
            </select>
            <button onClick={() => setPreviewMode(false)}
              style={{ fontSize: 11, border: '1px solid #ccc', borderRadius: 3, padding: '2px 8px', cursor: 'pointer', background: '#fff' }}>
              편집으로 돌아가기
            </button>
          </div>
        )}

        {/* 본문 */}
        <div style={{ flex: 1, position: 'relative', minHeight: 200 }}>
          {previewMode && previewRow ? (
            <div style={{
              padding: '16px 20px', height: '100%', overflowY: 'auto',
              fontSize: 13, lineHeight: 1.7, whiteSpace: 'pre-wrap',
              color: '#111', fontFamily: 'Arial, sans-serif'
            }}>
              <div style={{ marginBottom: 8, color: '#888', fontSize: 11 }}>
                제목: {applyVars(subject, previewRow)}
              </div>
              <hr style={{ border: 'none', borderTop: '1px solid #eee', marginBottom: 12 }} />
              {applyVars(body, previewRow)}
            </div>
          ) : (
            <textarea value={body} onChange={e => setBody(e.target.value)}
              placeholder='본문 입력 — {{name}} {{region}} 변수 사용 가능'
              style={{
                width: '100%', height: '100%', minHeight: 200,
                border: 'none', outline: 'none', resize: 'none',
                padding: '14px 20px', fontSize: 13, lineHeight: 1.7,
                fontFamily: 'Arial, sans-serif', color: '#111',
                boxSizing: 'border-box'
              }} />
          )}
        </div>

        {/* 변수 힌트 + 미리보기 토글 */}
        <div style={{
          padding: '4px 20px', background: '#fafafa',
          borderTop: '1px solid #f0f0f0', fontSize: 11, color: '#888',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center'
        }}>
          <span>변수: {'{{name}}'} {'{{region}}'} | 1:1 개별 발송</span>
          <button onClick={() => setPreviewMode(p => !p)}
            style={{
              fontSize: 11, padding: '2px 10px', border: '1px solid #ccc',
              borderRadius: 3, cursor: 'pointer',
              background: previewMode ? '#1a1a2e' : '#fff',
              color: previewMode ? '#fff' : '#333'
            }}>
            {previewMode ? '편집' : '미리보기'}
          </button>
        </div>

        {/* 첨부파일 */}
        <div ref={dropRef} onClick={() => fileRef.current?.click()}
          style={{
            margin: '8px 20px', border: '1.5px dashed #ccc', borderRadius: 6,
            padding: '10px', textAlign: 'center', cursor: 'pointer',
            background: '#fafafa', fontSize: 12, color: '#888'
          }}>
          📎 파일 드래그 또는 클릭하여 첨부
          {attachments.length > 0 && (
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'center', marginTop: 6 }}>
              {attachments.map((f, i) => (
                <span key={i} style={{
                  background: '#e8eaf6', padding: '2px 8px', borderRadius: 10,
                  fontSize: 11, display: 'flex', alignItems: 'center', gap: 4
                }}>
                  {f.name}
                  <span onClick={e => { e.stopPropagation(); setAttachments(a => a.filter((_, j) => j !== i)) }}
                    style={{ cursor: 'pointer', color: '#999' }}>✕</span>
                </span>
              ))}
            </div>
          )}
        </div>
        <input ref={fileRef} type='file' multiple style={{ display: 'none' }}
          onChange={e => setAttachments(a => [...a, ...Array.from(e.target.files ?? [])])} />

        {/* 하단 */}
        <div style={{
          padding: '10px 20px', borderTop: '1px solid #e8e8e8',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: '#fafafa'
        }}>
          <div>
            <div style={{ fontSize: 11, color: '#d32f2f', marginBottom: 2 }}>
              * 타인 정보 절대 미노출 / 1:1 개별 발송
            </div>
            {result && (
              <div style={{ fontSize: 12, fontWeight: 700, color: result.startsWith('✓') ? '#2e7d32' : '#c62828' }}>
                {result}
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={onClose}
              style={{ padding: '7px 18px', fontSize: 13, cursor: 'pointer', border: '1px solid #ccc', borderRadius: 6, background: '#fff' }}>
              취소
            </button>
            <button onClick={handleSend} disabled={sending}
              style={{
                padding: '7px 22px', fontSize: 13, cursor: sending ? 'not-allowed' : 'pointer',
                background: sending ? '#bbb' : '#1a1a2e', color: '#fff',
                border: 'none', borderRadius: 6, fontWeight: 700
              }}>
              {sending ? '발송중...' : `보내기 (${recipients.length}명)`}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
