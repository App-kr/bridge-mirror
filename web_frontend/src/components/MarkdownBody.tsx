'use client'

/**
 * MarkdownBody — full-featured renderer (no external deps)
 * Supports: # h1–h4, **bold**, *italic*, `inline code`,
 *           [link](url), - bullet, 1. numbered, > blockquote,
 *           ``` fenced code blocks, | tables |, ---
 */
export default function MarkdownBody({ text }: { text: string }) {
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // ── Fenced code block ```
    if (line.trim().startsWith('```')) {
      i++
      const codeLines: string[] = []
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      i++ // skip closing ```
      elements.push(
        <pre key={`pre-${i}`} className="bg-[#f5f5f7] rounded-xl p-4 overflow-x-auto my-5 text-sm border border-[#e5e5ea]">
          <code className="font-mono text-[#1d1d1f] leading-relaxed whitespace-pre">
            {codeLines.join('\n')}
          </code>
        </pre>
      )
      continue
    }

    // ── Headings
    const h4 = line.match(/^#### (.+)/)
    const h3 = line.match(/^### (.+)/)
    const h2 = line.match(/^## (.+)/)
    const h1 = line.match(/^# (.+)/)
    if (h4) {
      elements.push(<h4 key={i} className="text-sm font-semibold mt-5 mb-1 text-[#1d1d1f] uppercase tracking-wide">{inline(h4[1])}</h4>)
      i++; continue
    }
    if (h3) {
      elements.push(<h3 key={i} className="text-[17px] font-bold mt-7 mb-2 text-[#1d1d1f]">{inline(h3[1])}</h3>)
      i++; continue
    }
    if (h2) {
      elements.push(
        <h2 key={i} className="text-[22px] font-bold mt-9 mb-3 text-[#1d1d1f] pb-2 border-b border-[#e5e5ea]">
          {inline(h2[1])}
        </h2>
      )
      i++; continue
    }
    if (h1) {
      elements.push(<h1 key={i} className="text-[26px] font-bold mt-8 mb-4 text-[#1d1d1f]">{inline(h1[1])}</h1>)
      i++; continue
    }

    // ── HR
    if (/^[-*_]{3,}$/.test(line.trim())) {
      elements.push(<hr key={i} className="border-[#e5e5ea] my-7" />)
      i++; continue
    }

    // ── Blockquote
    if (line.startsWith('> ') || line === '>') {
      const items: string[] = []
      while (i < lines.length && (lines[i].startsWith('> ') || lines[i] === '>')) {
        items.push(lines[i].replace(/^> ?/, ''))
        i++
      }
      elements.push(
        <blockquote key={`bq-${i}`} className="border-l-4 border-[#0071e3] pl-5 my-5 space-y-1">
          {items.map((it, j) => (
            <p key={j} className="text-[#6e6e73] italic leading-relaxed">{inline(it)}</p>
          ))}
        </blockquote>
      )
      continue
    }

    // ── Table (lines starting with |)
    if (line.trim().startsWith('|')) {
      const tableLines: string[] = []
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i])
        i++
      }

      const isSepRow = (l: string) => l.replace(/[\|\-\s:]/g, '').length === 0

      const parseRow = (l: string): string[] => {
        const parts = l.split('|')
        const cells: string[] = []
        for (let ci = 0; ci < parts.length; ci++) {
          const c = parts[ci].trim()
          if (ci === 0 && c === '') continue
          if (ci === parts.length - 1 && c === '') continue
          cells.push(c)
        }
        return cells
      }

      const dataRows = tableLines.filter(l => !isSepRow(l))
      if (dataRows.length >= 1) {
        const headers = parseRow(dataRows[0])
        const bodyRows = dataRows.slice(1)
        elements.push(
          <div key={`tbl-${i}`} className="overflow-x-auto my-5 rounded-xl border border-[#e5e5ea]">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-[#f5f5f7]">
                  {headers.map((h, ci) => (
                    <th key={ci} className="border-b border-[#e5e5ea] px-4 py-2.5 text-left font-semibold text-[#1d1d1f] whitespace-nowrap">
                      {inline(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {bodyRows.map((row, ri) => {
                  const cells = parseRow(row)
                  return (
                    <tr key={ri} className={ri % 2 === 1 ? 'bg-[#fafafa]' : ''}>
                      {cells.map((c, ci) => (
                        <td key={ci} className="border-t border-[#e5e5ea] px-4 py-2 text-[#424245] align-top">
                          {inline(c)}
                        </td>
                      ))}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )
      }
      continue
    }

    // ── Bullet list (-, *, +)
    if (/^[-*+] /.test(line)) {
      const items: Array<{ text: string; indent: number }> = []
      while (i < lines.length && /^(\s*)[-*+] /.test(lines[i])) {
        const m = lines[i].match(/^(\s*)[-*+] (.*)/)!
        items.push({ text: m[2], indent: m[1].length })
        i++
      }
      elements.push(
        <ul key={`ul-${i}`} className="list-disc list-outside space-y-1.5 text-[#424245] my-4 pl-5">
          {items.map((it, j) => (
            <li key={j} className="leading-relaxed" style={{ marginLeft: it.indent > 0 ? '1.25rem' : 0 }}>
              {inline(it.text)}
            </li>
          ))}
        </ul>
      )
      continue
    }

    // ── Numbered list
    if (/^\d+\. /.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^\d+\. /.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\. /, ''))
        i++
      }
      elements.push(
        <ol key={`ol-${i}`} className="list-decimal list-outside space-y-1.5 text-[#424245] my-4 pl-5">
          {items.map((it, j) => (
            <li key={j} className="leading-relaxed">{inline(it)}</li>
          ))}
        </ol>
      )
      continue
    }

    // ── Empty line
    if (line.trim() === '') {
      elements.push(<div key={i} className="h-2" />)
      i++; continue
    }

    // ── Regular paragraph
    elements.push(
      <p key={i} className="text-[#424245] leading-[1.9]">{inline(line)}</p>
    )
    i++
  }

  return <div className="space-y-0.5">{elements}</div>
}

// ── Inline formatting ──────────────────────────────────────────────────────

function inline(text: string): React.ReactNode {
  // Split on inline code spans first
  const parts = text.split(/(`[^`]+`)/)
  return parts.map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code key={i} className="bg-[#f5f5f7] text-[#0071e3] px-1.5 py-0.5 rounded text-[13px] font-mono border border-[#e5e5ea]">
          {part.slice(1, -1)}
        </code>
      )
    }
    return richInline(part, i)
  })
}

function richInline(text: string, keyBase: number | string): React.ReactNode {
  // Bold **text**
  const boldSplit = text.split(/(\*\*[^*]+\*\*|\*\*\*[^*]+\*\*\*)/)
  if (boldSplit.length > 1) {
    return boldSplit.map((s, j) => {
      if (s.startsWith('***') && s.endsWith('***')) {
        return <strong key={`${keyBase}-${j}`} className="text-[#1d1d1f] font-semibold italic">{s.slice(3, -3)}</strong>
      }
      if (s.startsWith('**') && s.endsWith('**')) {
        return <strong key={`${keyBase}-${j}`} className="text-[#1d1d1f] font-semibold">{s.slice(2, -2)}</strong>
      }
      return <span key={`${keyBase}-${j}`}>{italicInline(s, `${keyBase}-${j}`)}</span>
    })
  }
  return italicInline(text, keyBase)
}

function italicInline(text: string, keyBase: number | string): React.ReactNode {
  const split = text.split(/(\*[^*]+\*|_[^_]+_)/)
  if (split.length > 1) {
    return split.map((s, j) => {
      if ((s.startsWith('*') && s.endsWith('*')) || (s.startsWith('_') && s.endsWith('_'))) {
        return <em key={`${keyBase}-${j}`} className="italic text-[#6e6e73]">{s.slice(1, -1)}</em>
      }
      return <span key={`${keyBase}-${j}`}>{linkify(s, `${keyBase}-${j}`)}</span>
    })
  }
  return linkify(text, keyBase)
}

function linkify(text: string, keyPrefix: number | string): React.ReactNode {
  const combined = /(\[([^\]]+)\]\((https?:\/\/[^)]+)\))|(https?:\/\/[^\s<"']+)/g
  const out: React.ReactNode[] = []
  let last = 0
  let m: RegExpExecArray | null
  while ((m = combined.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index))
    if (m[1]) {
      out.push(
        <a key={`${keyPrefix}-${m.index}`} href={m[3]} target="_blank" rel="noopener noreferrer"
          className="text-[#0071e3] hover:underline underline-offset-2">
          {m[2]}
        </a>
      )
    } else if (m[4]) {
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
