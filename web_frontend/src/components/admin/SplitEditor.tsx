'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { API_URL } from '@/lib/api'
import MarkdownBody from '@/components/MarkdownBody'

interface SplitEditorProps {
  mode: 'create' | 'edit'
  board: string
  postId?: number
  initialTitle?: string
  initialBody?: string
  signedFetch: (url: string, opts?: RequestInit) => Promise<Response>
  onSave: () => void
  onClose: () => void
}

const TOOLBAR_ITEMS = [
  { label: 'B', md: '**', wrap: true, title: 'Bold' },
  { label: 'I', md: '*', wrap: true, title: 'Italic' },
  { label: 'H1', md: '# ', wrap: false, title: 'Heading 1' },
  { label: 'H2', md: '## ', wrap: false, title: 'Heading 2' },
  { label: 'List', md: '- ', wrap: false, title: 'Bullet List' },
  { label: 'Link', md: 'link', wrap: false, title: 'Insert Link' },
]

export default function SplitEditor({
  mode, board, postId,
  initialTitle = '', initialBody = '',
  signedFetch, onSave, onClose,
}: SplitEditorProps) {
  const [title, setTitle] = useState(initialTitle)
  const [body, setBody] = useState(initialBody)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Lock body scroll
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  // Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const insertMarkdown = useCallback((item: typeof TOOLBAR_ITEMS[0]) => {
    const ta = textareaRef.current
    if (!ta) return
    const start = ta.selectionStart
    const end = ta.selectionEnd
    const selected = body.slice(start, end)

    if (item.md === 'link') {
      const linkText = selected || 'text'
      const insert = `[${linkText}](url)`
      const next = body.slice(0, start) + insert + body.slice(end)
      setBody(next)
      requestAnimationFrame(() => {
        ta.focus()
        const urlStart = start + linkText.length + 3
        ta.setSelectionRange(urlStart, urlStart + 3)
      })
      return
    }

    if (item.wrap) {
      const wrapped = `${item.md}${selected || 'text'}${item.md}`
      const next = body.slice(0, start) + wrapped + body.slice(end)
      setBody(next)
      requestAnimationFrame(() => {
        ta.focus()
        if (selected) {
          ta.setSelectionRange(start, start + wrapped.length)
        } else {
          ta.setSelectionRange(start + item.md.length, start + item.md.length + 4)
        }
      })
    } else {
      // Line prefix (H1, H2, List)
      const lineStart = body.lastIndexOf('\n', start - 1) + 1
      const next = body.slice(0, lineStart) + item.md + body.slice(lineStart)
      setBody(next)
      requestAnimationFrame(() => {
        ta.focus()
        ta.setSelectionRange(start + item.md.length, end + item.md.length)
      })
    }
  }, [body])

  const handleSave = async () => {
    if (!title.trim()) { setError('Title is required'); return }
    if (body.trim().length < 10) { setError('Body must be at least 10 characters'); return }

    setSaving(true)
    setError('')
    try {
      const payload = JSON.stringify({ title: title.trim(), body: body.trim() })
      let res: Response

      if (mode === 'create') {
        res = await signedFetch(`${API_URL}/api/community/${board}`, {
          method: 'POST',
          body: payload,
        })
      } else {
        res = await signedFetch(`${API_URL}/api/admin/community/${board}/${postId}`, {
          method: 'PATCH',
          body: payload,
        })
      }

      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(j.detail || j.error || `Error ${res.status}`)
      }

      onSave()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal container */}
      <div className="relative z-10 flex flex-col w-full h-full max-w-[1400px] mx-auto"
        onClick={(e) => e.stopPropagation()}>

        {/* Top bar */}
        <div className="flex items-center justify-between px-5 py-3 bg-zinc-900 border-b border-zinc-800 shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-zinc-400 text-sm font-medium">{board}</span>
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300">
              {mode === 'create' ? 'New Post' : 'Edit Post'}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Main content: left editor + right preview */}
        <div className="flex flex-1 min-h-0">
          {/* Left: Editor */}
          <div className="w-1/2 flex flex-col bg-zinc-900 border-r border-zinc-800">
            {/* Title input */}
            <div className="px-4 pt-4 pb-2 shrink-0">
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Post title..."
                maxLength={200}
                className="w-full bg-zinc-800 border border-zinc-700 text-white rounded-lg px-4 py-2.5 text-sm placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            {/* Markdown toolbar */}
            <div className="flex items-center gap-1 px-4 py-2 shrink-0">
              {TOOLBAR_ITEMS.map((item) => (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => insertMarkdown(item)}
                  title={item.title}
                  className="px-2.5 py-1.5 text-xs font-medium text-zinc-400 bg-zinc-800 border border-zinc-700 rounded hover:text-white hover:border-zinc-600 transition-colors"
                >
                  {item.label}
                </button>
              ))}
              <span className="ml-auto text-xs text-zinc-600">
                {body.length.toLocaleString()} / 10,000
              </span>
            </div>

            {/* Body textarea */}
            <div className="flex-1 px-4 pb-4 min-h-0">
              <textarea
                ref={textareaRef}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Write in markdown..."
                maxLength={10000}
                className="w-full h-full bg-zinc-800 border border-zinc-700 text-zinc-200 rounded-lg px-4 py-3 text-sm font-mono resize-none placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition-colors leading-relaxed"
              />
            </div>
          </div>

          {/* Right: Preview */}
          <div className="w-1/2 bg-zinc-950 overflow-y-auto">
            <div className="p-6">
              <div className="bg-white rounded-xl p-6 min-h-[200px]">
                {title && (
                  <h1 className="text-xl font-bold text-[#1d1d1f] mb-4">{title}</h1>
                )}
                {body ? (
                  <MarkdownBody text={body} />
                ) : (
                  <p className="text-zinc-400 text-sm italic">Preview will appear here...</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="flex items-center justify-between px-5 py-3 bg-zinc-900 border-t border-zinc-800 shrink-0">
          <div className="text-sm text-red-400 max-w-[60%] truncate">
            {error}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-zinc-300 bg-zinc-700 rounded-lg hover:bg-zinc-600 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="px-5 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
