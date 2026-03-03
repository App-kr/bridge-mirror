'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import MarkdownBody from './MarkdownBody'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

interface Props {
  board: string
  boardLabel: string
  accentClass: string
}

type Tab = 'write' | 'preview'

export default function NewPostForm({ board, boardLabel, accentClass }: Props) {
  const router = useRouter()
  const [tab, setTab] = useState<Tab>('write')
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [state, setState] = useState<'idle' | 'submitting' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim() || !body.trim()) { setErrorMsg('Title and body are required.'); return }
    if (body.trim().length < 10) { setErrorMsg('Body must be at least 10 characters.'); return }
    setState('submitting')
    setErrorMsg('')
    try {
      const res = await fetch(`${API}/api/community/${board}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim(), body: body.trim() }),
      })
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Failed')
      router.push(`/community/${board}/${json.data.id}`)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Submission failed.')
      setState('error')
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-12 space-y-6">
      <div>
        <div className="flex items-center gap-2 text-sm text-[#86868b]">
          <Link href="/community" className="hover:text-[#1d1d1f] transition-colors">Community</Link>
          <span>/</span>
          <Link href={`/community/${board}`} className={`hover:text-[#1d1d1f] transition-colors ${accentClass}`}>{boardLabel}</Link>
          <span>/</span>
          <span className="text-[#1d1d1f]">New Post</span>
        </div>
        <h1 className="text-2xl font-bold text-[#1d1d1f] mt-2">New Post</h1>
      </div>

      <div className="bg-[#FFF8E1] border border-[#FFE082] rounded-xl px-5 py-4 text-sm text-[#6e6e73]">
        🔒 Do not include phone numbers, email addresses, or personal contact info. Such posts will be blocked.
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-[#1d1d1f] mb-1.5">Title *</label>
          <input
            required
            className="w-full rounded-xl border border-[#d2d2d7] bg-white px-4 py-3 text-[15px] text-[#1d1d1f] placeholder:text-[#86868b] focus:outline-none focus:ring-2 focus:ring-[#0071e3] focus:border-transparent transition-shadow"
            placeholder="Post title…"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={200}
          />
          <div className="text-right text-xs text-[#86868b] mt-1">{title.length}/200</div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-[#1d1d1f]">
              Body * {board === 'visa' && <span className="text-[#86868b] font-normal">(Markdown supported)</span>}
            </label>
            <div className="flex rounded-lg overflow-hidden border border-[#d2d2d7] text-xs">
              <button type="button" onClick={() => setTab('write')}
                className={`px-3 py-1 transition-colors ${tab === 'write' ? 'bg-[#1d1d1f] text-white' : 'text-[#86868b] hover:text-[#1d1d1f]'}`}>
                Write
              </button>
              <button type="button" onClick={() => setTab('preview')}
                className={`px-3 py-1 transition-colors ${tab === 'preview' ? 'bg-[#1d1d1f] text-white' : 'text-[#86868b] hover:text-[#1d1d1f]'}`}>
                Preview
              </button>
            </div>
          </div>

          {tab === 'write' ? (
            <textarea
              className="w-full h-64 resize-y rounded-xl border border-[#d2d2d7] bg-white px-4 py-3 text-sm text-[#1d1d1f] font-mono placeholder:text-[#86868b] focus:outline-none focus:ring-2 focus:ring-[#0071e3] focus:border-transparent transition-shadow"
              placeholder={board === 'visa'
                ? "## Heading\n\nWrite your post here. **Bold**, *italic*, `code`, [links](https://example.com), and bullet lists are supported."
                : "Write your post here…"}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              maxLength={10000}
            />
          ) : (
            <div className="h-64 overflow-y-auto rounded-xl border border-[#d2d2d7] bg-[#f5f5f7] px-4 py-3">
              {body.trim() ? <MarkdownBody text={body} /> : (
                <p className="text-[#86868b] text-sm italic">Nothing to preview yet…</p>
              )}
            </div>
          )}
          <div className="text-right text-xs text-[#86868b] mt-1">{body.length}/10,000</div>
        </div>

        {(state === 'error' || errorMsg) && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
            {errorMsg}
          </div>
        )}

        <div className="flex gap-3">
          <Link href={`/community/${board}`}
            className="flex-1 text-center py-2.5 rounded-full border border-[#d2d2d7] text-[#1d1d1f] hover:bg-[#f5f5f7] text-sm font-medium transition-colors">
            Cancel
          </Link>
          <button
            type="submit"
            disabled={state === 'submitting'}
            className="flex-1 py-2.5 rounded-full bg-[#1d1d1f] text-white text-sm font-medium hover:bg-[#424245] disabled:opacity-50 transition-colors"
          >
            {state === 'submitting' ? 'Posting…' : 'Post'}
          </button>
        </div>
      </form>
    </div>
  )
}
