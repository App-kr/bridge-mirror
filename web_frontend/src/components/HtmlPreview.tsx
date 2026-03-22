'use client'

import { useEffect, useRef, useState } from 'react'
import DOMPurify from 'dompurify'

// fallback: 단순 HTML (전체 문서 아닌 경우)
const ALLOWED_TAGS = [
  'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'ul', 'ol', 'li', 'a', 'img', 'strong', 'em', 'b', 'i', 'u',
  'br', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
  'div', 'span', 'blockquote', 'code', 'pre', 'sub', 'sup',
  'section', 'article', 'header', 'footer', 'nav', 'main',
  'figure', 'figcaption', 'details', 'summary', 'small',
]

const isFullDocument = (html: string) =>
  /<html[\s>]/i.test(html) || /<!DOCTYPE/i.test(html)

export default function HtmlPreview({ html }: { html: string }) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(500)

  const isFullDoc = isFullDocument(html)

  // iframe 높이 자동 조정
  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe || !isFullDoc) return
    const onLoad = () => {
      try {
        const doc = iframe.contentDocument
        if (doc?.body) setHeight(Math.max(doc.body.scrollHeight + 40, 300))
      } catch {}
    }
    iframe.addEventListener('load', onLoad)
    return () => iframe.removeEventListener('load', onLoad)
  }, [html, isFullDoc])

  // 전체 HTML 문서 → iframe으로 완전 격리 렌더링
  if (isFullDoc) {
    return (
      <iframe
        ref={iframeRef}
        srcDoc={html}
        sandbox=""
        style={{ width: '100%', height: `${height}px`, border: 'none', display: 'block', borderRadius: '8px' }}
        title="HTML content"
      />
    )
  }

  // 일반 HTML 스니펫 → DOMPurify 후 직접 렌더 (style 태그 제거 — CSS injection 방지)
  const htmlNoStyles = html.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
  const clean = DOMPurify.sanitize(htmlNoStyles, {
    ALLOWED_TAGS,
    ALLOWED_ATTR: ['href', 'src', 'alt', 'class', 'style', 'target', 'rel', 'width', 'height', 'colspan', 'rowspan', 'id'],
    FORCE_BODY: true,
  })

  return <div dangerouslySetInnerHTML={{ __html: clean }} />
}
