'use client'

/**
 * Minimal markdown renderer — no external deps.
 * Supports: ## headings, **bold**, *italic*, `code`, [link](url), bullet lists, numbered lists, ---
 * URL auto-linking: bare URLs become clickable links
 */
export default function MarkdownBody({ text }: { text: string }) {
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []

  let i = 0
  while (i < lines.length) {
    const line = lines[i]

    // Heading
    const h3 = line.match(/^### (.+)/)
    const h2 = line.match(/^## (.+)/)
    const h1 = line.match(/^# (.+)/)
    if (h3) { elements.push(<h3 key={i} className="text-base font-semibold mt-5 mb-1.5 text-[#1d1d1f]">{inline(h3[1])}</h3>); i++; continue }
    if (h2) { elements.push(<h2 key={i} className="text-lg font-bold mt-6 mb-2 text-[#1d1d1f]">{inline(h2[1])}</h2>); i++; continue }
    if (h1) { elements.push(<h1 key={i} className="text-xl font-bold mt-7 mb-2 text-[#1d1d1f]">{inline(h1[1])}</h1>); i++; continue }

    // HR
    if (line.trim() === '---') { elements.push(<hr key={i} className="border-gray-200 my-5" />); i++; continue }

    // Bullet list
    if (line.match(/^[-*] /)) {
      const items: string[] = []
      while (i < lines.length && lines[i].match(/^[-*] /)) {
        items.push(lines[i].replace(/^[-*] /, ''))
        i++
      }
      elements.push(
        <ul key={`ul-${i}`} className="list-disc list-inside space-y-1 text-[#424245] my-3 pl-1">
          {items.map((it, j) => <li key={j}>{inline(it)}</li>)}
        </ul>
      )
      continue
    }

    // Numbered list
    if (line.match(/^\d+\. /)) {
      const items: string[] = []
      while (i < lines.length && lines[i].match(/^\d+\. /)) {
        items.push(lines[i].replace(/^\d+\. /, ''))
        i++
      }
      elements.push(
        <ol key={`ol-${i}`} className="list-decimal list-inside space-y-1 text-[#424245] my-3 pl-1">
          {items.map((it, j) => <li key={j}>{inline(it)}</li>)}
        </ol>
      )
      continue
    }

    // Empty line → paragraph break
    if (line.trim() === '') { elements.push(<div key={i} className="h-3" />); i++; continue }

    // Regular paragraph
    elements.push(<p key={i} className="text-[#424245] leading-[1.9]">{inline(line)}</p>)
    i++
  }

  return <div className="space-y-1">{elements}</div>
}

function inline(text: string): React.ReactNode {
  // Split by code spans first
  const parts = text.split(/(`[^`]+`)/)
  return parts.map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={i} className="bg-[#f5f5f7] text-[#0071e3] px-1.5 py-0.5 rounded text-[13px] font-mono">{part.slice(1, -1)}</code>
    }
    // Bold
    const boldSplit = part.split(/(\*\*[^*]+\*\*)/)
    return boldSplit.map((s, j) => {
      if (s.startsWith('**') && s.endsWith('**')) {
        return <strong key={`${i}-${j}`} className="text-[#1d1d1f] font-semibold">{s.slice(2, -2)}</strong>
      }
      // Italic
      const italicSplit = s.split(/(\*[^*]+\*)/)
      return italicSplit.map((t, k) => {
        if (t.startsWith('*') && t.endsWith('*')) {
          return <em key={`${i}-${j}-${k}`} className="text-[#6e6e73] italic">{t.slice(1, -1)}</em>
        }
        // Links [text](url) + bare URLs
        return linkify(t, `${i}-${j}-${k}`)
      })
    })
  })
}

function linkify(text: string, keyPrefix: string): React.ReactNode {
  // First: markdown links [text](url)
  const mdLinkRe = /\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g
  // Then: bare URLs
  const bareUrlRe = /(https?:\/\/[^\s<]+)/g

  // Combine both patterns
  const combined = /(\[([^\]]+)\]\((https?:\/\/[^\)]+)\))|(https?:\/\/[^\s<]+)/g
  const out: React.ReactNode[] = []
  let last = 0
  let m: RegExpExecArray | null

  while ((m = combined.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index))

    if (m[1]) {
      // Markdown link
      out.push(
        <a key={`${keyPrefix}-${m.index}`} href={m[3]} target="_blank" rel="noopener noreferrer"
          className="text-[#0071e3] hover:underline underline-offset-2">
          {m[2]}
        </a>
      )
    } else if (m[4]) {
      // Bare URL → auto-link
      out.push(
        <a key={`${keyPrefix}-${m.index}`} href={m[4]} target="_blank" rel="noopener noreferrer"
          className="text-[#0071e3] hover:underline underline-offset-2 break-all">
          {m[4]}
        </a>
      )
    }
    last = m.index + m[0].length
  }
  if (last < text.length) out.push(text.slice(last))
  return out.length > 0 ? out : text
}
