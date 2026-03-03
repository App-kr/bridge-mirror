import { NextRequest, NextResponse } from 'next/server'
import { getDb } from '@/lib/db'

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
  const benefits = (row.benefits as string) ?? ''
  return {
    location:                (row.city as string) || (row.location as string) || null,
    job_id:                  (row.job_code as string) ?? '',
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
    employee_benefits:       benefits ? benefits.split(',').map((b: string) => b.trim()).filter(Boolean) : null,
    is_hot:                  Boolean(row.is_hot),
    employment_type:         row.is_part_time ? 'part_time' : 'full_time',
    hours_per_day:           row.daily_hours ?? null,
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl
    const city = searchParams.get('city')?.trim().slice(0, 50)
    const isHot = searchParams.get('is_hot')
    const limit = Math.min(Number(searchParams.get('limit') ?? 50), 1000)
    const offset = Number(searchParams.get('offset') ?? 0)

    const db = getDb()
    const where = ['status = ?', 'is_deleted = 0']
    const params: (string | number)[] = ['open']

    if (city) {
      where.push('(city LIKE ? OR location LIKE ?)')
      params.push(`%${city}%`, `%${city}%`)
    }
    if (isHot !== null && isHot !== undefined) {
      where.push('is_hot = ?')
      params.push(isHot === 'true' ? 1 : 0)
    }

    const sql = `SELECT * FROM jobs WHERE ${where.join(' AND ')} ORDER BY is_hot DESC, created_at DESC LIMIT ? OFFSET ?`
    params.push(limit, offset)

    const rows = db.prepare(sql).all(...params) as Record<string, unknown>[]
    const data = rows.map(rowToPublic)

    return NextResponse.json({ success: true, message: `${data.length}건 조회`, data })
  } catch (e) {
    console.error('API /api/jobs error:', e)
    return NextResponse.json(
      { success: false, message: 'Failed to load jobs' },
      { status: 500 },
    )
  }
}
