'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Eye, Bold, Italic, Heading1, Heading2, List,
  Link2, Plus, X,
} from 'lucide-react'
import MarkdownBody from '@/components/MarkdownBody'

export interface LinkItem {
  name: string
  url: string
}

export interface PostData {
  title: string
  content: string
  links?: LinkItem[]
}

interface SplitEditorProps {
  isOpen: boolean
  onClose: () => void
  onSave: (data: PostData) => Promise<void> | void
  initialData?: { title: string; content: string; links?: LinkItem[] }
  previewType: 'faq' | 'list' | 'card' | 'testimonial'
  label?: string
}

export default function SplitEditor({
  isOpen, onClose, onSave, initialData, previewType, label,
}: SplitEditorProps) {
  const [title, setTitle] = useState(initialData?.title ?? '')
  const [content, setContent] = useState(initialData?.content ?? '')
  const [links, setLinks] = useState<LinkItem[]>(initialData?.links ?? [])
  const [linkName, setLinkName] = useState('')
  const [linkUrl, setLinkUrl] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!isOpen) return
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  const insertMd = useCallback((type: string) => {
    const ta = textareaRef.current
    if (!ta) return
    const start = ta.selectionStart
    const end = ta.selectionEnd
    const selected = content.slice(start, end)

    if (type === 'bold' || type === 'italic') {
      const md = type === 'bold' ? '**' : '*'
      const wrapped = `${md}${selected || 'text'}${md}`
      const next = content.slice(0, start) + wrapped + content.slice(end)
      setContent(next)
      requestAnimationFrame(() => {
        ta.focus()
        if (selected) {
          ta.setSelectionRange(start, start + wrapped.length)
        } else {
          ta.setSelectionRange(start + md.length, start + md.length + 4)
        }
      })
      return
    }

    const prefixMap: Record<string, string> = { h1: '# ', h2: '## ', list: '- ' }
    const prefix = prefixMap[type]
    if (prefix) {
      const lineStart = content.lastIndexOf('\n', start - 1) + 1
      const next = content.slice(0, lineStart) + prefix + content.slice(lineStart)
      setContent(next)
      requestAnimationFrame(() => {
        ta.focus()
        ta.setSelectionRange(start + prefix.length, end + prefix.length)
      })
    }
  }, [content])

  const addLink = useCallback(() => {
    if (!linkName.trim() || !linkUrl.trim()) return
    setLinks(prev => [...prev, { name: linkName.trim(), url: linkUrl.trim() }])
    setLinkName('')
    setLinkUrl('')
  }, [linkName, linkUrl])

  const removeLink = useCallback((index: number) => {
    setLinks(prev => prev.filter((_, i) => i !== index))
  }, [])

  const handleSave = useCallback(async () => {
    if (!title.trim()) { setError('Title is required'); return }
    if (content.trim().length < 2) { setError('Content is required'); return }
    setSaving(true)
    setError('')
    try {
      await onSave({
        title: title.trim(),
        content: content.trim(),
        links: links.length > 0 ? links : undefined,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }, [title, content, links, onSave])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div
        className="relative z-10 flex flex-col w-full max-w-6xl mx-4 h-[85vh] bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top bar */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800 shrink-0">
          <span className="text-sm font-medium text-zinc-300">
            {label ?? (previewType === 'faq' ? 'FAQ Editor' : 'Post Editor')}
          </span>
          <button type="button" onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors">
            ✕
          </button>
        </div>

        {/* Main: left editor + right preview */}
        <div className="flex flex-1 min-h-0">
          {/* Left: Editor */}
          <div className="w-1/2 flex flex-col bg-zinc-900 border-r border-zinc-800">
            {/* Title input */}
            <div className="px-4 pt-4 pb-2 shrink-0">
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={previewType === 'faq' ? 'Question...' : 'Post title...'}
                maxLength={200}
                className="w-full bg-zinc-800 border border-zinc-700 text-white rounded-lg px-4 py-3 text-lg placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            {/* Markdown toolbar */}
            <div className="flex items-center gap-1 px-4 py-2 shrink-0">
              {[
                { key: 'bold', Icon: Bold, title: 'Bold' },
                { key: 'italic', Icon: Italic, title: 'Italic' },
                { key: 'h1', Icon: Heading1, title: 'Heading 1' },
                { key: 'h2', Icon: Heading2, title: 'Heading 2' },
                { key: 'list', Icon: List, title: 'Bullet List' },
              ].map(item => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => insertMd(item.key)}
                  title={item.title}
                  className="p-2 text-zinc-400 bg-zinc-800 border border-zinc-700 rounded hover:text-white hover:border-zinc-600 transition-colors"
                >
                  <item.Icon size={16} />
                </button>
              ))}
              <span className="ml-auto text-xs text-zinc-600">
                {content.length.toLocaleString()}
              </span>
            </div>

            {/* Body textarea */}
            <div className="flex-1 px-4 min-h-0">
              <textarea
                ref={textareaRef}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder={previewType === 'faq' ? 'Answer...' : 'Write in markdown...'}
                maxLength={10000}
                className="w-full h-full bg-zinc-800 border border-zinc-700 text-zinc-200 rounded-lg px-4 py-3 text-sm font-mono resize-none placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition-colors leading-relaxed"
                style={{ minHeight: '300px' }}
              />
            </div>

            {/* Link management */}
            <div className="px-4 py-3 border-t border-zinc-800 shrink-0">
              <div className="flex items-center gap-2 mb-2">
                <Link2 size={14} className="text-zinc-500 shrink-0" />
                <input
                  type="text"
                  value={linkName}
                  onChange={(e) => setLinkName(e.target.value)}
                  placeholder="Link name"
                  className="flex-1 bg-zinc-800 border border-zinc-700 text-zinc-200 rounded px-3 py-1.5 text-xs placeholder-zinc-500 focus:outline-none focus:border-blue-500"
                />
                <input
                  type="text"
                  value={linkUrl}
                  onChange={(e) => setLinkUrl(e.target.value)}
                  placeholder="URL"
                  onKeyDown={(e) => { if (e.key === 'Enter') addLink() }}
                  className="flex-1 bg-zinc-800 border border-zinc-700 text-zinc-200 rounded px-3 py-1.5 text-xs placeholder-zinc-500 focus:outline-none focus:border-blue-500"
                />
                <button
                  type="button"
                  onClick={addLink}
                  disabled={!linkName.trim() || !linkUrl.trim()}
                  className="p-1.5 text-zinc-400 hover:text-blue-400 disabled:opacity-30 transition-colors"
                >
                  <Plus size={16} />
                </button>
              </div>
              {links.length > 0 && (
                <div className="space-y-1">
                  {links.map((link, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <Link2 size={12} className="text-blue-400 shrink-0" />
                      <span className="text-blue-300 truncate">{link.name}</span>
                      <span className="text-zinc-600 truncate flex-1">{link.url}</span>
                      <button type="button" onClick={() => removeLink(i)}
                        className="p-0.5 text-zinc-500 hover:text-red-400 transition-colors">
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right: Preview */}
          <div className="w-1/2 bg-zinc-950 overflow-y-auto">
            <div className="px-4 py-3 border-b border-zinc-800 flex items-center gap-2">
              <Eye size={14} className="text-zinc-500" />
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Preview</span>
            </div>
            <div className="p-6">
              <PreviewRenderer title={title} content={content} links={links} type={previewType} />
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-zinc-800 shrink-0">
          <div className="text-sm text-red-400 max-w-[60%] truncate">{error}</div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-zinc-300 bg-zinc-700 rounded-lg hover:bg-zinc-600 transition-colors">
              Cancel
            </button>
            <button type="button" onClick={handleSave} disabled={saving}
              className="px-5 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Preview Renderers ──────────────────────────────────────────────────────

function PreviewRenderer({ title, content, links, type }: {
  title: string; content: string; links: LinkItem[]; type: string
}) {
  if (!title && !content) {
    return <p className="text-zinc-600 text-sm italic">Preview will appear here...</p>
  }

  switch (type) {
    case 'faq':
      return <FaqPreview q={title} a={content} />
    case 'card':
      return <CardPreview title={title} content={content} links={links} />
    case 'testimonial':
      return <TestimonialPreview title={title} content={content} />
    default:
      return <ListPreview title={title} content={content} links={links} />
  }
}

function FaqPreview({ q, a }: { q: string; a: string }) {
  return (
    <div className="rounded-xl overflow-hidden" style={{
      background: 'rgba(255,255,255,0.05)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #3b82f6',
    }}>
      <div className="flex items-center gap-3 px-5 py-4">
        <span className="shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white bg-blue-500">
          1
        </span>
        <span className="text-[15px] font-medium text-white/90">{q || 'Question...'}</span>
      </div>
      <div className="px-5 pb-4 pl-[52px]">
        <p className="text-sm text-white/60 leading-relaxed whitespace-pre-line break-words">
          {a || 'Answer...'}
        </p>
      </div>
    </div>
  )
}

function ListPreview({ title, content, links }: { title: string; content: string; links: LinkItem[] }) {
  return (
    <div className="bg-white rounded-xl p-6 min-h-[200px]">
      {title && <h1 className="text-xl font-bold text-[#1d1d1f] mb-4">{title}</h1>}
      {content ? (
        <MarkdownBody text={content} />
      ) : (
        <p className="text-zinc-400 text-sm italic">Content...</p>
      )}
      {links.length > 0 && (
        <div className="mt-4 pt-4 border-t border-zinc-200 space-y-1">
          {links.map((link, i) => (
            <a key={i} href={link.url} target="_blank" rel="noopener noreferrer"
              className="block text-sm text-[#0071e3] hover:underline">{link.name}</a>
          ))}
        </div>
      )}
    </div>
  )
}

function CardPreview({ title, content, links }: { title: string; content: string; links: LinkItem[] }) {
  return (
    <div className="bg-white rounded-2xl p-5 border border-[#e5e5ea]">
      <h3 className="text-[17px] font-bold text-[#1d1d1f] mb-2">{title || 'Title...'}</h3>
      <div className="text-sm text-[#6e6e73] line-clamp-4 mb-4">
        {content ? <MarkdownBody text={content} /> : <p className="italic">Content...</p>}
      </div>
      {links.length > 0 && (
        <div className="space-y-1 mb-3">
          {links.map((link, i) => (
            <a key={i} href={link.url} target="_blank" rel="noopener noreferrer"
              className="block text-xs text-[#0071e3] hover:underline">{link.name}</a>
          ))}
        </div>
      )}
      <span className="text-sm font-medium text-[#0071e3]">Read more &rarr;</span>
    </div>
  )
}

function TestimonialPreview({ title, content }: { title: string; content: string }) {
  const name = title?.split('—')[0]?.trim() || 'Name'
  return (
    <div className="bg-white rounded-2xl p-5 border border-[#e5e5ea]">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-[52px] h-[52px] rounded-full flex items-center justify-center text-white text-lg font-bold shrink-0 bg-[#4ECDC4]">
          {name.charAt(0)}
        </div>
        <div>
          <div className="font-semibold text-[#1d1d1f] text-sm">{name}</div>
          <div className="text-xs text-[#86868b]">English Teacher &middot; BRIDGE</div>
        </div>
      </div>
      <span className="text-3xl text-[#d1d1d6] leading-none">&ldquo;</span>
      <div className="text-sm text-[#424245] italic mt-1">
        {content ? <MarkdownBody text={content} /> : <p>Story...</p>}
      </div>
    </div>
  )
}
