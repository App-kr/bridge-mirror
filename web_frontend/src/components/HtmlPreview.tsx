'use client'

import DOMPurify from 'dompurify'

const PURIFY_CONFIG = {
  ALLOWED_TAGS: [
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'a', 'img', 'strong', 'em', 'b', 'i', 'u',
    'br', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'div', 'span', 'blockquote', 'code', 'pre', 'sub', 'sup',
    'style', 'section', 'article', 'header', 'footer', 'nav',
    'figure', 'figcaption', 'details', 'summary', 'small',
  ],
  ALLOWED_ATTR: [
    'href', 'src', 'alt', 'class', 'style', 'target', 'rel',
    'width', 'height', 'colspan', 'rowspan', 'id',
  ],
  FORCE_BODY: true,
}

export default function HtmlPreview({ html }: { html: string }) {
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
