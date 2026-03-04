import { NextRequest, NextResponse } from 'next/server'
import { getJobs } from '@/lib/db'

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

function rowToPublic(row: Record<string, unknown>) {
  const benefits = String(row.benefits ?? '')
  return {
    location:                String(row.city || row.location || ''),
    job_id:                  String(row.job_code ?? ''),
    starting_date:           row.start_date ?? null,
    teaching_age:            parseAgeGroups(row.teaching_age as string | null),
    class_size:              row.class_size ?? null,
    working_hours:           row.working_hours ?? null,
    monthly_salary:          row.salary_raw ?? null,
    teaching_hours_per_week: row.teach_hrs_week ?? null,
    vacation:                row.vacation ?? null,
    native_teacher_count:    row.native_count ?? null,
    housing:                 row.housing ?? null,
    preferences:             null,
    employee_benefits:       benefits ? benefits.split(',').map(b => b.trim()).filter(Boolean) : null,
    is_hot:                  Boolean(row.is_hot),
    employment_type:         row.is_part_time ? 'part_time' : 'full_time',
    hours_per_day:           row.daily_hours ?? null,
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl
    const city = searchParams.get('city')?.trim().toLowerCase()
    const isHot = searchParams.get('is_hot')
    const limit = Math.min(Number(searchParams.get('limit') ?? 50), 1000)
    const offset = Number(searchParams.get('offset') ?? 0)

    let rows = getJobs()

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

    return NextResponse.json({ success: true, message: `${data.length}건 조회`, data })
  } catch {
    return NextResponse.json({ success: false, message: 'Failed to load jobs' }, { status: 500 })
  }
}
