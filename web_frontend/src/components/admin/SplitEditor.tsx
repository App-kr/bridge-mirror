'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Eye, Bold, Italic, Heading1, Heading2, List,
  Link2, Plus, X, Paperclip, ImageIcon, Loader2,
} from 'lucide-react'
import DOMPurify from 'dompurify'
import MarkdownBody from '@/components/MarkdownBody'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { API_URL } from '@/lib/api'

export type ContentType = 'markdown' | 'html'

export interface LinkItem {
  name: string
  url: string
}

export interface AttachmentItem {
  name: string
  size: number
  file?: File
}

export interface PostData {
  title: string
  content: string
  contentType: ContentType
  links?: LinkItem[]
  attachments?: AttachmentItem[]
}

interface SplitEditorProps {
  isOpen: boolean
  onClose: () => void
  onSave: (data: PostData) => Promise<void> | void
  initialData?: { title: string; content: string; contentType?: ContentType; links?: LinkItem[] }
  previewType: 'faq' | 'list' | 'card' | 'testimonial'
  label?: string
  // 게시판 이미지 영구 보존 (Cafe24 FTP 방식 — postId 있을 때만 표시)
  board?: string
  postId?: number
  initialImagePaths?: string[]
  signedFetch?: (url: string, init?: RequestInit) => Promise<Response>
}

const PURIFY_CONFIG = {
  ALLOWED_TAGS: [
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'a', 'img', 'strong', 'em', 'b', 'i', 'u',
    'br', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'div', 'span', 'blockquote', 'code', 'pre', 'sub', 'sup',
  ],
  ALLOWED_ATTR: [
    'href', 'src', 'alt', 'class', 'style', 'target', 'rel',
    'width', 'height', 'colspan', 'rowspan',
  ],
}

function HtmlPreview({ html }: { html: string }) {
  const clean = DOMPurify.sanitize(html, PURIFY_CONFIG)
  return (
    <>
      <style>{`
        .prose-bridge h1 { font-size: 1.5rem; font-weight: 700; margin: 1.25rem 0 0.5rem; color: #1d1d1f; }
        .prose-bridge h2 { font-size: 1.25rem; font-weight: 700; margin: 1rem 0 0.5rem; color: #1d1d1f; }
        .prose-bridge h3 { font-size: 1.1rem; font-weight: 600; margin: 0.75rem 0 0.375rem; color: #1d1d1f; }
        .prose-bridge p { color: #424245; line-height: 1.9; margin: 0.25rem 0; }
        .prose-bridge ul { list-style: disc inside; color: #424245; margin: 0.75rem 0; padding-left: 0.25rem; }
        .prose-bridge ol { list-style: decimal inside; color: #424245; margin: 0.75rem 0; padding-left: 0.25rem; }
        .prose-bridge li { margin: 0.25rem 0; }
        .prose-bridge a { color: #0071e3; text-decoration: none; }
        .prose-bridge a:hover { text-decoration: underline; }
        .prose-bridge img { max-width: 100%; border-radius: 0.5rem; margin: 0.5rem 0; }
        .prose-bridge blockquote { border-left: 3px solid #d1d1d6; padding-left: 1rem; color: #6e6e73; margin: 0.75rem 0; }
        .prose-bridge code { background: #f5f5f7; color: #0071e3; padding: 0.125rem 0.375rem; border-radius: 0.25rem; font-size: 0.8125rem; font-family: monospace; }
        .prose-bridge pre { background: #f5f5f7; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; margin: 0.75rem 0; }
        .prose-bridge pre code { background: transparent; padding: 0; }
        .prose-bridge table { width: 100%; border-collapse: collapse; margin: 0.75rem 0; }
        .prose-bridge th, .prose-bridge td { border: 1px solid #e5e5ea; padding: 0.5rem 0.75rem; text-align: left; font-size: 0.875rem; }
        .prose-bridge th { background: #f5f5f7; font-weight: 600; }
        .prose-bridge hr { border: none; border-top: 1px solid #e5e5ea; margin: 1.25rem 0; }
      `}</style>
      <div className="prose-bridge" dangerouslySetInnerHTML={{ __html: clean }} />
    </>
  )
}

export default function SplitEditor({
  isOpen, onClose, onSave, initialData, previewType, label,
  board, postId, initialImagePaths, signedFetch,
}: SplitEditorProps) {
  const [title, setTitle] = useState(initialData?.title ?? '')
  const [content, setContent] = useState(initialData?.content ?? '')
  const [contentType, setContentType] = useState<ContentType>(initialData?.contentType ?? 'markdown')
  const [links, setLinks] = useState<LinkItem[]>(initialData?.links ?? [])
  const [linkName, setLinkName] = useState('')
  const [linkUrl, setLinkUrl] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [attachments, setAttachments] = useState<AttachmentItem[]>([])
  const [showLinkPopover, setShowLinkPopover] = useState(false)
  const [inlineLinkUrl, setInlineLinkUrl] = useState('')
  const [inlineLinkText, setInlineLinkText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)

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

  const insertAtCursor = useCallback((text: string) => {
    const ta = textareaRef.current
    if (!ta) {
      setContent(prev => prev + text)
      return
    }
    const start = ta.selectionStart
    const end = ta.selectionEnd
    const next = content.slice(0, start) + text + content.slice(end)
    setContent(next)
    requestAnimationFrame(() => {
      ta.focus()
      const pos = start + text.length
      ta.setSelectionRange(pos, pos)
    })
  }, [content])

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

  // File attachment handler
  const handleFileAttach = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return
    const maxSize = 10 * 1024 * 1024
    const allowed = ['.pdf', '.doc', '.docx', '.xlsx', '.ppt', '.pptx', '.txt', '.zip']
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      const ext = '.' + file.name.split('.').pop()?.toLowerCase()
      if (!allowed.includes(ext)) {
        setError(`Unsupported file type: ${ext}`)
        continue
      }
      if (file.size > maxSize) {
        setError(`File too large: ${file.name} (max 10MB)`)
        continue
      }
      setAttachments(prev => [...prev, { name: file.name, size: file.size, file }])
    }
    e.target.value = ''
  }, [])

  // Image insert handler — upload to server, insert URL (never base64)
  const [imageUploading, setImageUploading] = useState(false)
  const { adminKey } = useAdminAuth()

  const handleImageInsert = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const maxSize = 5 * 1024 * 1024
    if (file.size > maxSize) {
      setError('Image too large (max 5MB)')
      e.target.value = ''
      return
    }
    e.target.value = ''
    setImageUploading(true)
    setError('')
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${API_URL}/api/admin/upload-image`, {
        method: 'POST',
        headers: { 'x-admin-key': adminKey },
        body: form,
      })
      const json = await res.json()
      if (!res.ok || !json.success) {
        setError(json.detail || json.error || 'Upload failed')
        return
      }
      const url = `${API_URL}${json.data.url}`
      if (contentType === 'html') {
        insertAtCursor(`<img src="${url}" alt="${file.name}" />`)
      } else {
        insertAtCursor(`![${file.name}](${url})`)
      }
    } catch {
      setError('Image upload failed')
    } finally {
      setImageUploading(false)
    }
  }, [contentType, insertAtCursor, adminKey])

  // Inline link insert
  const handleInlineLinkInsert = useCallback(() => {
    if (!inlineLinkUrl.trim()) return
    const text = inlineLinkText.trim() || inlineLinkUrl.trim()
    const url = inlineLinkUrl.trim()
    if (contentType === 'html') {
      insertAtCursor(`<a href="${url}" target="_blank">${text}</a>`)
    } else {
      insertAtCursor(`[${text}](${url})`)
    }
    setInlineLinkUrl('')
    setInlineLinkText('')
    setShowLinkPopover(false)
  }, [contentType, inlineLinkUrl, inlineLinkText, insertAtCursor])

  const removeAttachment = useCallback((index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index))
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
        contentType,
        links: links.length > 0 ? links : undefined,
        attachments: attachments.length > 0 ? attachments : undefined,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }, [title, content, contentType, links, attachments, onSave])

  if (!isOpen) return null

  const isFaq = previewType === 'faq'

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
            {label ?? (isFaq ? 'FAQ Editor' : 'Post Editor')}
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
                placeholder={isFaq ? 'Question...' : 'Post title...'}
                maxLength={200}
                className="w-full bg-zinc-800 border border-zinc-700 text-white rounded-lg px-4 py-3 text-lg placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>

            {/* Toolbar */}
            <div className="flex items-center gap-1 px-4 py-2 shrink-0 flex-wrap">
              {/* Mode tabs (not shown for FAQ — always markdown) */}
              {!isFaq && (
                <div className="flex items-center bg-zinc-800 rounded-lg p-0.5 mr-2">
                  <button
                    type="button"
                    onClick={() => setContentType('markdown')}
                    className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                      contentType === 'markdown' ? 'bg-zinc-600 text-white' : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                  >Markdown</button>
                  <button
                    type="button"
                    onClick={() => setContentType('html')}
                    className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                      contentType === 'html' ? 'bg-zinc-600 text-white' : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                  >HTML</button>
                </div>
              )}

              {/* Markdown toolbar buttons */}
              {contentType === 'markdown' && [
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

              {/* HTML mode label */}
              {contentType === 'html' && (
                <span className="text-xs text-zinc-500 italic mr-1">Raw HTML</span>
              )}

              {/* Shared buttons: file, image, link */}
              <div className="flex items-center gap-1 ml-1">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  title="Attach file"
                  className="p-2 text-zinc-400 bg-zinc-800 border border-zinc-700 rounded hover:text-white hover:border-zinc-600 transition-colors"
                >
                  <Paperclip size={16} />
                </button>
                <button
                  type="button"
                  onClick={() => imageInputRef.current?.click()}
                  disabled={imageUploading}
                  title="Insert image"
                  className="p-2 text-zinc-400 bg-zinc-800 border border-zinc-700 rounded hover:text-white hover:border-zinc-600 transition-colors disabled:opacity-50"
                >
                  {imageUploading ? <Loader2 size={16} className="animate-spin" /> : <ImageIcon size={16} />}
                </button>
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowLinkPopover(!showLinkPopover)}
                    title="Insert inline link"
                    className="p-2 text-zinc-400 bg-zinc-800 border border-zinc-700 rounded hover:text-white hover:border-zinc-600 transition-colors"
                  >
                    <Link2 size={16} />
                  </button>
                  {showLinkPopover && (
                    <div className="absolute top-full left-0 mt-1 z-20 bg-zinc-800 border border-zinc-700 rounded-lg p-3 w-64 shadow-xl">
                      <input
                        type="text"
                        value={inlineLinkText}
                        onChange={(e) => setInlineLinkText(e.target.value)}
                        placeholder="Link text"
                        className="w-full bg-zinc-700 border border-zinc-600 text-zinc-200 rounded px-2 py-1.5 text-xs mb-2 placeholder-zinc-500 focus:outline-none focus:border-blue-500"
                      />
                      <input
                        type="text"
                        value={inlineLinkUrl}
                        onChange={(e) => setInlineLinkUrl(e.target.value)}
                        placeholder="https://..."
                        onKeyDown={(e) => { if (e.key === 'Enter') handleInlineLinkInsert() }}
                        className="w-full bg-zinc-700 border border-zinc-600 text-zinc-200 rounded px-2 py-1.5 text-xs mb-2 placeholder-zinc-500 focus:outline-none focus:border-blue-500"
                      />
                      <div className="flex gap-1">
                        <button type="button" onClick={handleInlineLinkInsert}
                          className="flex-1 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-500 transition-colors">
                          Insert
                        </button>
                        <button type="button" onClick={() => setShowLinkPopover(false)}
                          className="px-2 py-1 text-xs text-zinc-400 hover:text-white transition-colors">
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <span className="ml-auto text-xs text-zinc-500">
                {content.length.toLocaleString()} chars
              </span>
            </div>

            {/* Hidden file inputs */}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.xlsx,.ppt,.pptx,.txt,.zip"
              className="hidden"
              onChange={handleFileAttach}
            />
            <input
              ref={imageInputRef}
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp"
              className="hidden"
              onChange={handleImageInsert}
            />

            {/* Body textarea */}
            <div className="flex-1 px-4 min-h-0">
              <textarea
                ref={textareaRef}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder={
                  isFaq ? 'Answer...' :
                  contentType === 'html' ? '<p>Write HTML here...</p>' : 'Write in markdown...'
                }
                className="w-full h-full bg-zinc-800 border border-zinc-700 text-zinc-200 rounded-lg px-4 py-3 text-sm font-mono resize-none placeholder-zinc-500 focus:outline-none focus:border-blue-500 transition-colors leading-relaxed"
                style={{ minHeight: '200px' }}
              />
            </div>

            {/* 영구 게시판 이미지 (Cafe24 FTP 대체) — 기존 글에만 표시 */}
            {board && postId && signedFetch && (
              <div className="px-4 py-3 border-t border-zinc-800 shrink-0">
                <BoardImageManager
                  board={board}
                  postId={postId}
                  initialPaths={initialImagePaths || []}
                  signedFetch={signedFetch}
                />
              </div>
            )}

            {/* Attachments list */}
            {attachments.length > 0 && (
              <div className="px-4 py-2 border-t border-zinc-800 shrink-0">
                <div className="text-xs text-zinc-500 mb-1 font-medium">Attachments ({attachments.length})</div>
                <div className="space-y-1 max-h-20 overflow-y-auto">
                  {attachments.map((att, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <Paperclip size={12} className="text-zinc-500 shrink-0" />
                      <span className="text-zinc-300 truncate">{att.name}</span>
                      <span className="text-zinc-600">{(att.size / 1024).toFixed(0)}KB</span>
                      <button type="button" onClick={() => removeAttachment(i)}
                        className="p-0.5 text-zinc-500 hover:text-red-400 transition-colors ml-auto">
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

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
              {contentType === 'html' && (
                <span className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">HTML</span>
              )}
            </div>
            <div className="p-6">
              <PreviewRenderer title={title} content={content} links={links} type={previewType} contentType={contentType} />
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

function PreviewRenderer({ title, content, links, type, contentType }: {
  title: string; content: string; links: LinkItem[]; type: string; contentType: ContentType
}) {
  if (!title && !content) {
    return <p className="text-zinc-600 text-sm italic">Preview will appear here...</p>
  }

  switch (type) {
    case 'faq':
      return <FaqPreview q={title} a={content} />
    case 'card':
      return <CardPreview title={title} content={content} links={links} contentType={contentType} />
    case 'testimonial':
      return <TestimonialPreview title={title} content={content} contentType={contentType} />
    default:
      return <ListPreview title={title} content={content} links={links} contentType={contentType} />
  }
}

function ContentRenderer({ content, contentType }: { content: string; contentType: ContentType }) {
  if (contentType === 'html') {
    return <HtmlPreview html={content} />
  }
  return <MarkdownBody text={content} />
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

function ListPreview({ title, content, links, contentType }: { title: string; content: string; links: LinkItem[]; contentType: ContentType }) {
  return (
    <div className="bg-white rounded-xl p-6 min-h-[200px]">
      {title && <h1 className="text-xl font-bold text-[#1d1d1f] mb-4">{title}</h1>}
      {content ? (
        <ContentRenderer content={content} contentType={contentType} />
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

function CardPreview({ title, content, links, contentType }: { title: string; content: string; links: LinkItem[]; contentType: ContentType }) {
  return (
    <div className="bg-white rounded-2xl p-5 border border-[#e5e5ea]">
      <h3 className="text-[17px] font-bold text-[#1d1d1f] mb-2">{title || 'Title...'}</h3>
      <div className="text-sm text-[#6e6e73] line-clamp-4 mb-4">
        {content ? <ContentRenderer content={content} contentType={contentType} /> : <p className="italic">Content...</p>}
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

function TestimonialPreview({ title, content, contentType }: { title: string; content: string; contentType: ContentType }) {
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
        {content ? <ContentRenderer content={content} contentType={contentType} /> : <p>Story...</p>}
      </div>
    </div>
  )
}

export { HtmlPreview }


// ════════════════════════════════════════════════════════════════════
// BoardImageManager — Cafe24 FTP 대체. 글당 영구 파일.
// 업로드/삭제 시 DB image_paths 자동 동기. 영구 보존.
// ════════════════════════════════════════════════════════════════════
function BoardImageManager({
  board, postId, initialPaths, signedFetch,
}: {
  board: string
  postId: number
  initialPaths: string[]
  signedFetch: (url: string, init?: RequestInit) => Promise<Response>
}) {
  const [paths, setPaths] = useState<string[]>(initialPaths)
  const [uploading, setUploading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setErr(null)
    setUploading(true)
    try {
      for (const file of Array.from(files)) {
        const fd = new FormData()
        fd.append('file', file)
        const res = await signedFetch(
          `${API_URL}/api/admin/community/${board}/${postId}/images`,
          { method: 'POST', body: fd }
        )
        if (!res.ok) {
          const j = await res.json().catch(() => ({}))
          throw new Error(j?.detail || j?.error || `HTTP ${res.status}`)
        }
        const j = await res.json()
        const newPaths = j?.data?.image_paths || j?.image_paths || []
        setPaths(newPaths)
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setErr(`업로드 실패: ${msg}`)
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  const deletePath = async (url: string) => {
    if (!confirm('이 이미지를 삭제하시겠습니까? (파일 영구 삭제)')) return
    setErr(null)
    try {
      const res = await signedFetch(
        `${API_URL}/api/admin/community/${board}/${postId}/images?url=${encodeURIComponent(url)}`,
        { method: 'DELETE' },
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setPaths(prev => prev.filter(p => p !== url))
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setErr(`삭제 실패: ${msg}`)
    }
  }

  const fullUrl = (path: string) => (path.startsWith('http') ? path : `${API_URL}${path}`)

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-zinc-400 font-medium">
          📁 게시판 이미지 ({paths.length}/10) — 서버 영구 저장
        </span>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={uploading || paths.length >= 10}
          className="px-2.5 py-1 rounded bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 disabled:opacity-40"
        >
          {uploading ? '업로드 중…' : '+ 이미지 첨부'}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
      {paths.length === 0 ? (
        <p className="text-xs text-zinc-600">아직 업로드된 이미지가 없습니다. 첫 번째 이미지가 카드 썸네일로 사용됩니다.</p>
      ) : (
        <div className="grid grid-cols-4 sm:grid-cols-6 gap-1.5">
          {paths.map((p, i) => (
            <div key={p} className="relative group aspect-square overflow-hidden rounded bg-zinc-800">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={fullUrl(p)}
                alt=""
                className="w-full h-full object-cover"
                onError={(e) => { (e.currentTarget as HTMLImageElement).style.opacity = '0.3' }}
              />
              {i === 0 && (
                <span className="absolute top-0.5 left-0.5 px-1 py-0.5 rounded bg-blue-600 text-white text-[8px] font-bold">
                  썸네일
                </span>
              )}
              <button
                type="button"
                onClick={() => deletePath(p)}
                className="absolute top-0.5 right-0.5 w-4 h-4 rounded-full bg-red-600 text-white text-[10px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-700"
                title="삭제"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
      {err && <p className="mt-1.5 text-[11px] text-red-400">{err}</p>}
      <p className="mt-1 text-[10px] text-zinc-600">
        Render 영구 디스크 저장 — 배포·코드 변경에도 사라지지 않음. 첫 번째가 카드 썸네일.
      </p>
    </div>
  )
}
