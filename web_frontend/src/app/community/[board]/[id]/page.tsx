'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import MarkdownBody from '@/components/MarkdownBody'
import HtmlPreview from '@/components/HtmlPreview'
import { getBoardConfig } from '@/lib/boards'
import { EditButton } from '@/components/EditModeBar'
import { API_URL } from '@/lib/api'

const API = API_URL

interface Post {
  id: number
  title: string
  body: string
  author_hash: string
  pinned: number
  views: number
  created_at: string
  image_paths?: string
  content_type?: string
}

export default function PostDetailPage() {
  const { board, id } = useParams<{ board: string; id: string }>()
  const config = getBoardConfig(board)

  const [post, setPost] = useState<Post | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (!config) { setNotFound(true); setLoading(false); return }
    fetch(`${API}/api/community/${board}/${id}`)
      .then((r) => { if (!r.ok) { setNotFound(true); return null } return r.json() })
      .then((j) => { if (j?.success) setPost(j.data) })
      .finally(() => setLoading(false))
  }, [board, id, config])

  if (loading) {
    return <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 text-center text-[#86868b]">Loading...</div>
  }

  if (notFound || !post || !config) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-16 text-center text-[#86868b]">
        <p className="text-lg">Post not found.</p>
        <Link href={`/community/${board}`} className="text-[#0071e3] mt-2 block">← Back to board</Link>
      </div>
    )
  }

  // Extract links from body (URLs on their own line)
  const urlRegex = /(https?:\/\/[^\s<]+)/g
  const hasExternalLinks = urlRegex.test(post.body)

  const images: string[] = (() => {
    try { return JSON.parse(post.image_paths ?? '[]') }
    catch { return [] }
  })()

  return (
    <>
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
      {/* Disclaimer notice */}
      <div className="disclaimer-notice">
        <p style={{ marginBottom: '6px' }}>
          All information is subject to change without notice according to institutional policies. Please contact the relevant institution directly to verify the latest information before proceeding.
        </p>
        <p style={{ margin: 0 }}>
          모든 정보는 예고 없이 해당 기관의 정책에 따라 변경될 수 있습니다. 진행 전 반드시 해당 기관에 직접 연락하여 최신 정보를 확인하시기 바랍니다.
        </p>
      </div>

      {/* Title + Edit Button */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <h1 className="text-[28px] sm:text-[36px] font-bold text-[#1d1d1f] leading-tight">
          {post.title}
        </h1>
        <EditButton postId={post.id} board={board} />
      </div>

      <div className="mb-8" />

      {/* Body */}
      <div className="post-body" style={{ fontSize: '15px', lineHeight: '1.9' }}>
        {post.content_type === 'html' ? (
          <HtmlPreview html={post.body} />
        ) : (
          <MarkdownBody text={post.body} />
        )}
      </div>

      {/* External link button */}
      {hasExternalLinks && (
        <div className="mt-8">
          {post.body.match(urlRegex)?.slice(0, 3).map((url, i) => (
            <a key={i} href={url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#0071e3] text-white text-sm font-medium rounded-full hover:bg-[#0077ED] transition-colors mr-2 mb-2">
              🔗 Visit Official Website →
            </a>
          ))}
        </div>
      )}

      {/* Images */}
      {images.length > 0 && (
        <div className="mt-8 space-y-2">
          <p className="text-xs font-medium text-[#86868b] uppercase">Attachments</p>
          <div className="grid grid-cols-2 gap-3">
            {images.map((url, i) => (
              <a key={i} href={url} target="_blank" rel="noopener noreferrer"
                className="block rounded-xl overflow-hidden border border-gray-100 hover:border-[#0071e3] transition-colors">
                <img src={url} alt={`Attachment ${i + 1}`} className="w-full h-auto" />
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Back link */}
      <Link href={`/community/${board}`}
        className="inline-block mt-8 text-sm text-[#0071e3] hover:underline">
        ← Back to {config.label}
      </Link>
    </div>
    </>
  )
}
