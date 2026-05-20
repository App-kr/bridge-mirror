/**
 * Sanitizes user-generated text that may contain raw HTML entities or tags.
 * Decodes common HTML entities and converts <br> tags to newlines.
 * Does NOT use dangerouslySetInnerHTML — safe for plain-text rendering.
 */
export function sanitizeReviewText(text: string): string {
  if (!text) return ''
  return (
    text
      // Decode numeric HTML entities (e.g. &#034; → ", &#39; → ')
      .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(parseInt(code, 10)))
      // Decode hex HTML entities (e.g. &#x22; → ")
      .replace(/&#x([0-9a-fA-F]+);/g, (_, code) => String.fromCharCode(parseInt(code, 16)))
      // Decode named HTML entities
      .replace(/&quot;/g, '"')
      .replace(/&apos;/g, "'")
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&nbsp;/g, ' ')
      .replace(/&ldquo;/g, '\u201C')
      .replace(/&rdquo;/g, '\u201D')
      .replace(/&lsquo;/g, '\u2018')
      .replace(/&rsquo;/g, '\u2019')
      // Convert <br> tags to newlines
      .replace(/<br\s*\/?>/gi, '\n')
      // Strip any remaining HTML tags
      .replace(/<[^>]+>/g, '')
      // Replace AI-style em-dashes / full-width separators with comma-space
      .replace(/\s*[—–―｜ー]+\s*/g, ', ')
      // Korean stand-alone filler "ㅡ" (U+3161) → comma
      .replace(/\s*[ㅡ]+\s*/g, ', ')
      // Collapse repeated punctuation/spaces
      .replace(/,\s*,+/g, ',')
      .replace(/\s{2,}/g, ' ')
      .trim()
  )
}
