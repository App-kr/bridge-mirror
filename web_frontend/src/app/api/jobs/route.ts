import { NextRequest, NextResponse } from 'next/server'
import { getJobs } from '@/lib/db'

/* ── Month parsing helpers ── */
const MONTHS = [
  'january', 'february', 'march', 'april', 'may', 'june',
  'july', 'august', 'september', 'october', 'november', 'december',
]
const MONTH_DISPLAY = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

const NOTE_RE = /visa|welcome|prefer|christian|couple|bilingual|residing|qualified|contract|eligible|only|holder|pgce|korean|kyopo|gyopo/i
const PII_RE = /\b\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{4}\b|@/

function parseAgeGroups(raw: string | null): string[] | null {
  if (!raw) return null
  const map: Record<string, string> = {
    kindy: 'kindergarten', kindergarten: 'kindergarten',
    elem: 'elementary', elementary: 'elementary',
    pre_k: 'pre_k', 'pre-k': 'pre_k', prek: 'pre_k',
    middle: 'middle', high: 'high', adult: 'adult',
  }
  const groups: string[] = []
  for (const t of raw.toLowerCase().split(/[,/\-&·\s]+/)) {
    const key = t.trim()
    if (map[key] && !groups.includes(map[key])) groups.push(map[key])
  }
  return groups.length > 0 ? groups : null
}

/** Find month index (0-11) from a text fragment, or -1 */
function findMonth(text: string): number {
  const lower = text.toLowerCase()
  for (let m = 0; m < 12; m++) {
    if (lower.includes(MONTHS[m].substring(0, 3))) return m
  }
  return -1
}

/** Convert past months → ASAP, extract non-date notes */
function convertStartDate(raw: unknown): { date: string | null; notes: string[] } {
  if (!raw || typeof raw !== 'string' || !raw.trim()) return { date: null, notes: [] }

  const currentMonth = new Date().getMonth()
  const notes: string[] = []
  const converted: string[] = []

  const parts = raw.split(/[,|;]+/).map(s => s.trim()).filter(Boolean)

  for (const part of parts) {
    const lower = part.toLowerCase().trim()
    if (!lower) continue

    // ASAP variants
    if (lower.includes('asap')) {
      if (!converted.includes('ASAP')) converted.push('ASAP')
      const rest = part.replace(/asap/gi, '').replace(/[~\-–\s]+/g, ' ').trim()
      if (rest && NOTE_RE.test(rest)) notes.push(rest)
      continue
    }

    // Year-round / ongoing
    if (lower.includes('year-round') || lower.includes('ongoing')) {
      if (!converted.includes('ASAP')) converted.push('ASAP')
      continue
    }

    // Pure note (no month)
    if (NOTE_RE.test(lower) && findMonth(lower) < 0) {
      notes.push(part.trim())
      continue
    }

    // Has note content AND a month
    if (NOTE_RE.test(lower)) {
      const m = findMonth(lower)
      if (m >= 0) {
        const ahead = (m - currentMonth + 12) % 12
        if (ahead <= 6) converted.push(MONTH_DISPLAY[m])
        else if (!converted.includes('ASAP')) converted.push('ASAP')
      }
      let noteText = part
      for (const mn of MONTH_DISPLAY) noteText = noteText.replace(new RegExp(mn, 'gi'), '')
      noteText = noteText.replace(/^[\s,|;\-–~.]+|[\s,|;\-–~.]+$/g, '').trim()
      if (noteText) notes.push(noteText)
      continue
    }

    // Pure date part
    const m = findMonth(lower)
    if (m >= 0) {
      const ahead = (m - currentMonth + 12) % 12
      if (ahead <= 6) converted.push(MONTH_DISPLAY[m])
      else if (!converted.includes('ASAP')) converted.push('ASAP')
    }
    // If no month found, ignore (random text like "End of", numbers, etc.)
  }

  const unique = [...new Set(converted)]
  return {
    date: unique.length > 0 ? unique.join(', ') : 'ASAP',
    notes: notes.filter(Boolean),
  }
}

function stripPII(text: string | null): string | null {
  if (!text) return null
  return PII_RE.test(text) ? null : text
}

function cleanRawText(text: unknown): string | null {
  if (!text || typeof text !== 'string') return null
  let t = text.replace(/\([^)]*\)/g, '')
  t = t.replace(PII_RE, '')
  t = t.split('\n').filter(l => l.trim()).join('\n')
  return t.trim() || null
}

function rowToPublic(row: Record<string, unknown>) {
  const benefits = String(row.benefits ?? '')
  const { date, notes } = convertStartDate(row.start_date)

  return {
    location:                String(row.city || row.location || ''),
    job_id:                  String(row.job_code ?? ''),
    starting_date:           date,
    teaching_age:            parseAgeGroups(row.teaching_age as string | null),
    teaching_age_raw:        row.teaching_age ? String(row.teaching_age) : null,
    class_size:              stripPII(row.class_size ? String(row.class_size) : null),
    working_hours:           row.working_hours ? String(row.working_hours) : null,
    monthly_salary:          row.salary_raw ? String(row.salary_raw) : null,
    teaching_hours_per_week: row.teach_hrs_week ? String(row.teach_hrs_week) : null,
    vacation:                row.vacation ? String(row.vacation) : null,
    native_teacher_count:    row.native_count ? String(row.native_count) : null,
    housing:                 stripPII(row.housing ? String(row.housing) : null),
    preferences:             null,
    notes,
    employee_benefits:       benefits ? benefits.split(',').map(b => b.trim()).filter(Boolean) : null,
    raw_text:                cleanRawText(row.raw_text),
    is_hot:                  Boolean(row.is_hot),
    employment_type:         row.is_part_time ? 'part_time' as const : 'full_time' as const,
    hours_per_day:           row.daily_hours ?? null,
    status:                  row.status ? String(row.status) : 'open',
  }
}

const RENDER_API = process.env.NEXT_PUBLIC_API_URL || 'https://bridge-n7hk.onrender.com'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl
    const city = searchParams.get('city')?.trim().toLowerCase()
    const isHot = searchParams.get('is_hot')
    const limit = Math.min(Number(searchParams.get('limit') ?? 50), 100)
    const offset = Number(searchParams.get('offset') ?? 0)
    const includeAll = searchParams.get('include_all') === 'true'

    // PRIMARY: Render API (live DB data)
    try {
      const proxyUrl = `${RENDER_API}/api/jobs?${searchParams.toString()}`
      const resp = await fetch(proxyUrl, { next: { revalidate: 1800 } })
      if (resp.ok) {
        const json = await resp.json()
        if (json.success && Array.isArray(json.data) && json.data.length > 0) {
          return NextResponse.json(json)
        }
      }
    } catch {
      // Render unreachable — fall through to static JSON
    }

    // FALLBACK: static JSON (stale but available offline)
    let rows = getJobs()
    if (rows.length === 0) {
      return NextResponse.json({ success: true, message: '0건 조회', data: [] })
    }

    // Public: only open, non-deleted jobs
    if (!includeAll) {
      rows = rows.filter(r => String(r.status ?? 'open') === 'open' && !r.is_deleted)
    }

    if (city) {
      rows = rows.filter(r =>
        String(r.city ?? '').toLowerCase().includes(city) ||
        String(r.location ?? '').toLowerCase().includes(city)
      )
    }
    if (isHot === 'true') rows = rows.filter(r => Boolean(r.is_hot))
    if (isHot === 'false') rows = rows.filter(r => !r.is_hot)

    const paged = rows.slice(offset, offset + limit)
    const data = paged.map(rowToPublic)

    return NextResponse.json({ success: true, message: `${data.length}건 조회 (fallback)`, data })
  } catch {
    return NextResponse.json({ success: false, message: 'Failed to load jobs' }, { status: 500 })
  }
}
