'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import { MAIL_TEMPLATES } from './engine/types'
import type { DataRow, MailTemplate } from './engine/types'

const F = '"Pretendard Variable", Pretendard, -apple-system, "Noto Sans KR", "Malgun Gothic", sans-serif'
const LS_KEY = 'bridge_mail_templates'

interface MailModalProps {
  open: boolean
  onClose: () => void
  recipients: DataRow[]
  adminKey: string
  apiUrl: string
}

function loadSavedTemplates(): MailTemplate[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(LS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

function persistTemplates(all: MailTemplate[]) {
  if (typeof window === 'undefined') return
  const toSave = all.filter(t => {
    const def = MAIL_TEMPLATES.find(d => d.key === t.key)
    if (!def) return true
    return def.s !== t.s || def.b !== t.b
  })
  localStorage.setItem(LS_KEY, JSON.stringify(toSave))
}

function mergeTemplates(): MailTemplate[] {
  const saved = loadSavedTemplates()
  const merged = MAIL_TEMPLATES.map(d => {
    const override = saved.find(s => s.key === d.key)
    return override ? { ...d, s: override.s, b: override.b } : { ...d }
  })
  for (const s of saved) {
    if (!MAIL_TEMPLATES.find(d => d.key === s.key)) merged.push(s)
  }
  return merged
}

export default function MailModal({ open, onClose, recipients, adminKey, apiUrl }: MailModalProps) {
  const [templates, setTemplates] = useState<MailTemplate[]>([])
  const [tmplKey, setTmplKey] = useState('')
  const [sender, setSender] = useState<'gmail' | 'naver'>('naver')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [attachments, setAttachments] = useState<File[]>([])
  const [attachCv, setAttachCv] = useState(false)
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState('')
  const [previewMode, setPreviewMode] = useState(false)
  const [previewIdx, setPreviewIdx] = useState(0)
  const [showAddInput, setShowAddInput] = useState(false)
  const [newTmplName, setNewTmplName] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)
  const dropRef = useRef<HTMLDivElement>(null)
  const addInputRef = useRef<HTMLInputElement>(null)

  const senderEmail = sender === 'gmail' ? 'bridgejobkr@gmail.com' : 'bridgejobkr@naver.com'

  const applyVars = useCallback((text: string, r: DataRow) => {
    return text
      .replace(/\{\{name\}\}/g, String(r.name ?? r.email ?? 'Teacher'))
      .replace(/\{\{region\}\}/g, String(r.prefRegion ?? ''))
  }, [])

  const selectTemplate = useCallback((key: string, list?: MailTemplate[]) => {
    const pool = list || templates
    const t = pool.find(t => t.key === key)
    if (!t) return
    setTmplKey(key)
    setSubject(t.s)
    setBody(t.b)
    setPreviewMode(false)
    setResult('')
  }, [templates])

  useEffect(() => {
    if (open) {
      const m = mergeTemplates()
      setTemplates(m)
      if (m.length > 0) selectTemplate(m[0].key, m)
      setAttachments([])
      setResult('')
      setPreviewIdx(0)
      setShowAddInput(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  useEffect(() => {
    if (showAddInput && addInputRef.current) addInputRef.current.focus()
  }, [showAddInput])

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

  /* ── Template CRUD ── */
  const handleSaveTemplate = () => {
    const updated = templates.map(t =>
      t.key === tmplKey ? { ...t, s: subject, b: body } : t
    )
    setTemplates(updated)
    persistTemplates(updated)
    flash('템플릿 저장 완료')
  }

  const handleAddTemplate = () => {
    const name = newTmplName.trim()
    if (!name) return
    const key = `user_${Date.now()}`
    const t: MailTemplate = { key, label: name, s: subject, b: body }
    const updated = [...templates, t]
    setTemplates(updated)
    setTmplKey(key)
    persistTemplates(updated)
    setNewTmplName('')
    setShowAddInput(false)
    flash('새 템플릿 추가됨')
  }

  const handleDeleteTemplate = () => {
    const isDef = MAIL_TEMPLATES.find(d => d.key === tmplKey)
    if (isDef) {
      const updated = templates.map(t => t.key === tmplKey ? { ...isDef } : t)
      setTemplates(updated)
      setSubject(isDef.s)
      setBody(isDef.b)
      persistTemplates(updated)
      flash('기본값으로 복원됨')
    } else {
      const updated = templates.filter(t => t.key !== tmplKey)
      setTemplates(updated)
      persistTemplates(updated)
      if (updated.length > 0) selectTemplate(updated[0].key, updated)
      flash('템플릿 삭제됨')
    }
  }

  const flash = (msg: string) => {
    setResult(`✓ ${msg}`)
    setTimeout(() => setResult(''), 2500)
  }

  /* ── Send (1:1 individual) ── */
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
        if (attachCv && r._cid) form.append('attach_cv_ids', String(r._cid))
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

  const copyBody = () => {
    const row = recipients[previewIdx]
    const text = row ? applyVars(body, row) : body
    navigator.clipboard.writeText(text).then(() => flash('클립보드 복사됨')).catch(() => {})
  }

  if (!open) return null

  const previewRow = recipients[previewIdx]
  const isDefault = !!MAIL_TEMPLATES.find(d => d.key === tmplKey)

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'rgba(0,0,0,0.4)', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      padding: 16, backdropFilter: 'blur(4px)',
      fontFamily: F,
    }} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={{
        width: '95vw', maxWidth: 980, height: '93vh', background: '#fff',
        borderRadius: 20, display: 'flex', flexDirection: 'column',
        boxShadow: '0 25px 80px rgba(0,0,0,0.25)', overflow: 'hidden',
      }}>

        {/* ═══ Header ═══ */}
        <div style={{
          padding: '18px 28px', borderBottom: '1px solid #e5e5e5',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: '#fff',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <span style={{ fontSize: 22, fontWeight: 600, color: '#000', fontFamily: F }}>
              메일 발송
            </span>
            <span style={{
              background: '#f0f0f0', color: '#000', padding: '5px 16px',
              borderRadius: 20, fontSize: 16, fontWeight: 500, fontFamily: F,
            }}>{recipients.length}명 선택</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button onClick={handleSaveTemplate} style={{
              background: '#f5f5f5', border: '1px solid #ddd', color: '#000',
              fontSize: 16, fontWeight: 500, cursor: 'pointer',
              padding: '9px 22px', borderRadius: 10, fontFamily: F,
              transition: 'background 0.15s',
            }} onMouseEnter={e => (e.currentTarget.style.background = '#eee')}
               onMouseLeave={e => (e.currentTarget.style.background = '#f5f5f5')}>
              저장
            </button>
            <button onClick={handleSend} disabled={sending} style={{
              background: sending ? '#ccc' : '#007AFF', border: 'none',
              color: '#fff', fontSize: 16, fontWeight: 500,
              cursor: sending ? 'not-allowed' : 'pointer',
              padding: '9px 28px', borderRadius: 10, fontFamily: F,
              transition: 'background 0.15s',
            }}>
              {sending ? '발송중...' : `보내기 (${recipients.length}명)`}
            </button>
            <button onClick={onClose} style={{
              background: 'none', border: 'none', color: '#999',
              fontSize: 24, cursor: 'pointer', padding: '0 4px',
              lineHeight: 1, marginLeft: 4,
            }}>✕</button>
          </div>
        </div>

        {/* ═══ Template tabs ═══ */}
        <div style={{
          padding: '12px 28px', borderBottom: '1px solid #f0f0f0',
          display: 'flex', alignItems: 'center', gap: 8,
          background: '#fafafa', flexWrap: 'wrap',
        }}>
          {templates.map(t => (
            <button key={t.key} onClick={() => selectTemplate(t.key)}
              style={{
                padding: '7px 18px', fontSize: 15, borderRadius: 10, fontFamily: F,
                border: tmplKey === t.key ? '2px solid #007AFF' : '1px solid #ddd',
                background: tmplKey === t.key ? '#EBF5FF' : '#fff',
                color: tmplKey === t.key ? '#007AFF' : '#333',
                cursor: 'pointer', fontWeight: 500,
                whiteSpace: 'nowrap', flexShrink: 0,
                transition: 'all 0.15s',
              }}>
              {t.label}
            </button>
          ))}
          {/* Add template */}
          {showAddInput ? (
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input ref={addInputRef} value={newTmplName}
                onChange={e => setNewTmplName(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleAddTemplate(); if (e.key === 'Escape') setShowAddInput(false) }}
                placeholder="템플릿 이름"
                style={{
                  border: '1px solid #ccc', borderRadius: 8, padding: '6px 12px',
                  fontSize: 14, width: 120, outline: 'none', fontFamily: F,
                  color: '#000',
                }} />
              <button onClick={handleAddTemplate} style={{
                background: '#007AFF', color: '#fff', border: 'none',
                borderRadius: 8, padding: '6px 14px', fontSize: 14,
                cursor: 'pointer', fontWeight: 500, fontFamily: F,
              }}>추가</button>
              <button onClick={() => setShowAddInput(false)} style={{
                background: 'none', border: 'none', color: '#999',
                fontSize: 18, cursor: 'pointer', padding: '0 4px',
              }}>✕</button>
            </div>
          ) : (
            <button onClick={() => setShowAddInput(true)} style={{
              padding: '7px 14px', fontSize: 15, borderRadius: 10,
              border: '1px dashed #ccc', background: '#fff', color: '#888',
              cursor: 'pointer', fontWeight: 500, fontFamily: F,
            }}>+ 추가</button>
          )}
          {/* Delete / Reset */}
          <button onClick={handleDeleteTemplate} style={{
            padding: '7px 14px', fontSize: 14, borderRadius: 10,
            border: '1px solid #eee', background: '#fff', color: '#999',
            cursor: 'pointer', fontWeight: 500, fontFamily: F, marginLeft: 'auto',
          }}>
            {isDefault ? '복원' : '삭제'}
          </button>
        </div>

        {/* ═══ Sender ═══ */}
        <div style={{
          padding: '12px 28px', display: 'flex', alignItems: 'center', gap: 14,
          borderBottom: '1px solid #f0f0f0',
        }}>
          <span style={{ fontSize: 16, color: '#000', fontWeight: 500, width: 48, fontFamily: F }}>발신</span>
          <button onClick={() => setSender('gmail')} style={{
            padding: '8px 22px', fontSize: 16, borderRadius: 10, fontFamily: F,
            border: sender === 'gmail' ? '2px solid #dc2626' : '1px solid #fecaca',
            background: sender === 'gmail' ? '#fef2f2' : '#fff',
            color: sender === 'gmail' ? '#dc2626' : '#999',
            cursor: 'pointer', fontWeight: 500,
            transition: 'all 0.15s',
          }}>Gmail</button>
          <button onClick={() => setSender('naver')} style={{
            padding: '8px 22px', fontSize: 16, borderRadius: 10, fontFamily: F,
            border: sender === 'naver' ? '2px solid #16a34a' : '1px solid #bbf7d0',
            background: sender === 'naver' ? '#f0fdf4' : '#fff',
            color: sender === 'naver' ? '#16a34a' : '#999',
            cursor: 'pointer', fontWeight: 500,
            transition: 'all 0.15s',
          }}>Naver</button>
          <span style={{ fontSize: 15, color: '#666', marginLeft: 6, fontFamily: F }}>{senderEmail}</span>
        </div>

        {/* ═══ Recipients ═══ */}
        <div style={{
          padding: '12px 28px', display: 'flex', gap: 8, alignItems: 'center',
          borderBottom: '1px solid #f0f0f0', flexWrap: 'wrap',
          maxHeight: 100, overflowY: 'auto',
        }}>
          <span style={{ fontSize: 16, color: '#000', fontWeight: 500, flexShrink: 0, fontFamily: F }}>수신</span>
          {recipients.map((r, i) => (
            <span key={i} onClick={() => { setPreviewIdx(i); setPreviewMode(true) }}
              style={{
                background: previewIdx === i && previewMode ? '#007AFF' : '#f5f5f5',
                color: previewIdx === i && previewMode ? '#fff' : '#000',
                border: 'none',
                borderRadius: 20, padding: '6px 16px', fontSize: 15, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 6, fontWeight: 500, fontFamily: F,
                transition: 'all 0.15s',
              }}>
              <span>{String(r.name ?? r.email ?? '')}</span>
              {r._cid && <span style={{ fontSize: 12, opacity: 0.5 }}>#{r._cid}</span>}
            </span>
          ))}
        </div>

        {/* ═══ Subject ═══ */}
        <div style={{
          padding: '12px 28px', display: 'flex', alignItems: 'center', gap: 14,
          borderBottom: '1px solid #f0f0f0',
        }}>
          <span style={{ fontSize: 16, color: '#000', fontWeight: 500, width: 48, fontFamily: F }}>제목</span>
          <input value={subject} onChange={e => setSubject(e.target.value)}
            placeholder="메일 제목을 입력하세요"
            style={{
              flex: 1, border: 'none', outline: 'none', fontSize: 17,
              fontWeight: 500, color: '#000', fontFamily: F,
              padding: '4px 0',
            }} />
        </div>

        {/* ═══ Attachments (under subject) ═══ */}
        <div ref={dropRef} style={{
          padding: '10px 28px', borderBottom: '1px solid #f0f0f0',
          display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
          minHeight: 48,
        }}>
          <label style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: attachCv ? '#EEF2FF' : '#f5f5f5',
            border: attachCv ? '1px solid #6366F1' : '1px solid #ddd',
            borderRadius: 10, padding: '7px 14px', fontSize: 14,
            cursor: 'pointer', fontWeight: 500, fontFamily: F,
            color: attachCv ? '#4338CA' : '#555', flexShrink: 0,
            transition: 'all 0.15s', userSelect: 'none',
          }}>
            <input type="checkbox" checked={attachCv} onChange={e => setAttachCv(e.target.checked)}
              style={{ accentColor: '#6366F1' }} />
            이력서 자동첨부
          </label>
          <button onClick={() => fileRef.current?.click()} style={{
            background: '#f5f5f5', border: '1px solid #ddd', borderRadius: 10,
            padding: '7px 18px', fontSize: 15, cursor: 'pointer',
            color: '#555', fontWeight: 500, fontFamily: F, flexShrink: 0,
            transition: 'background 0.15s',
          }} onMouseEnter={e => (e.currentTarget.style.background = '#eee')}
             onMouseLeave={e => (e.currentTarget.style.background = '#f5f5f5')}>
            대용량첨부(14일후 만료)
          </button>
          {attachments.length === 0 && (
            <span style={{ fontSize: 14, color: '#bbb', fontFamily: F }}>
              파일을 드래그하거나 버튼을 클릭하세요
            </span>
          )}
          {attachments.map((f, i) => (
            <span key={i} style={{
              background: '#f0f4ff', padding: '5px 14px', borderRadius: 10,
              fontSize: 14, display: 'flex', alignItems: 'center', gap: 8,
              fontWeight: 500, fontFamily: F, color: '#000',
            }}>
              {f.name}
              <span style={{ fontSize: 12, color: '#888' }}>({(f.size / 1024).toFixed(0)}KB)</span>
              <span onClick={e => { e.stopPropagation(); setAttachments(a => a.filter((_, j) => j !== i)) }}
                style={{ cursor: 'pointer', color: '#dc2626', fontWeight: 500, fontSize: 16, lineHeight: 1 }}>✕</span>
            </span>
          ))}
        </div>
        <input ref={fileRef} type="file" multiple style={{ display: 'none' }}
          onChange={e => setAttachments(a => [...a, ...Array.from(e.target.files ?? [])])} />

        {/* ═══ Preview bar ═══ */}
        {previewMode && previewRow && (
          <div style={{
            padding: '10px 28px', background: '#FFFBEB',
            borderBottom: '1px solid #FDE68A',
            display: 'flex', alignItems: 'center', gap: 12, fontSize: 15, fontFamily: F,
          }}>
            <span style={{ fontWeight: 500, color: '#000' }}>미리보기</span>
            <select value={previewIdx}
              onChange={e => setPreviewIdx(Number(e.target.value))}
              style={{
                fontSize: 15, border: '1px solid #ddd', borderRadius: 8,
                padding: '4px 10px', fontFamily: F, color: '#000',
              }}>
              {recipients.map((r, i) => (
                <option key={i} value={i}>
                  {String(r.name ?? r.email ?? '')} ({String(r.email ?? '')})
                </option>
              ))}
            </select>
            <button onClick={copyBody} style={{
              fontSize: 14, padding: '5px 14px', border: '1px solid #ddd',
              borderRadius: 8, cursor: 'pointer', background: '#fff',
              fontWeight: 500, fontFamily: F, color: '#000',
            }}>복사</button>
            <button onClick={() => setPreviewMode(false)} style={{
              fontSize: 14, padding: '5px 14px', border: '1px solid #ddd',
              borderRadius: 8, cursor: 'pointer', background: '#fff',
              fontWeight: 500, fontFamily: F, color: '#000',
            }}>편집으로</button>
          </div>
        )}

        {/* ═══ Body ═══ */}
        <div style={{ flex: 1, position: 'relative', minHeight: 200 }}>
          {previewMode && previewRow ? (
            <div style={{
              padding: '22px 28px', height: '100%', overflowY: 'auto',
              fontSize: 17, lineHeight: 1.8, whiteSpace: 'pre-wrap',
              color: '#000', fontFamily: F,
            }}>
              <div style={{ marginBottom: 12, color: '#666', fontSize: 15, fontWeight: 500 }}>
                제목: {applyVars(subject, previewRow)}
              </div>
              <hr style={{ border: 'none', borderTop: '1px solid #eee', marginBottom: 16 }} />
              {applyVars(body, previewRow)}
            </div>
          ) : (
            <textarea value={body} onChange={e => setBody(e.target.value)}
              placeholder="본문 입력 — {{name}} {{region}} 변수 사용 가능"
              style={{
                width: '100%', height: '100%', minHeight: 200,
                border: 'none', outline: 'none', resize: 'none',
                padding: '22px 28px', fontSize: 17, lineHeight: 1.8,
                fontFamily: F, color: '#000', boxSizing: 'border-box',
              }} />
          )}
        </div>

        {/* ═══ Footer ═══ */}
        <div style={{
          padding: '14px 28px', borderTop: '1px solid #e5e5e5',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: '#fafafa',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ fontSize: 14, color: '#888', fontFamily: F }}>
              {'{{name}}'} {'{{region}}'} 변수 사용 가능
            </span>
            <span style={{ fontSize: 14, color: '#dc2626', fontWeight: 500, fontFamily: F }}>
              1:1 개별발송
            </span>
            {result && (
              <span style={{
                fontSize: 15, fontWeight: 500, fontFamily: F,
                color: result.includes('실패') ? '#dc2626' : '#16a34a',
              }}>{result}</span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={copyBody} style={{
              padding: '9px 18px', fontSize: 15, cursor: 'pointer',
              border: '1px solid #ddd', borderRadius: 10, background: '#fff',
              fontWeight: 500, fontFamily: F, color: '#000',
              transition: 'background 0.15s',
            }} onMouseEnter={e => (e.currentTarget.style.background = '#f5f5f5')}
               onMouseLeave={e => (e.currentTarget.style.background = '#fff')}>
              복사
            </button>
            <button onClick={() => setPreviewMode(p => !p)} style={{
              padding: '9px 18px', fontSize: 15, cursor: 'pointer',
              border: '1px solid #ddd', borderRadius: 10,
              background: previewMode ? '#007AFF' : '#fff',
              color: previewMode ? '#fff' : '#000',
              fontWeight: 500, fontFamily: F,
              transition: 'all 0.15s',
            }}>
              {previewMode ? '편집' : '미리보기'}
            </button>
            <button onClick={onClose} style={{
              padding: '9px 22px', fontSize: 15, cursor: 'pointer',
              border: '1px solid #ddd', borderRadius: 10, background: '#fff',
              fontWeight: 500, fontFamily: F, color: '#000',
              transition: 'background 0.15s',
            }} onMouseEnter={e => (e.currentTarget.style.background = '#f5f5f5')}
               onMouseLeave={e => (e.currentTarget.style.background = '#fff')}>
              닫기
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
