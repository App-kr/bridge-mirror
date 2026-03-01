import { createClient } from '@supabase/supabase-js'
import type { Job, Employer, PublicJob, PublicCandidate } from '@/types'

const supabaseUrl  = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

if (!supabaseUrl || !supabaseAnon) {
  throw new Error('Missing Supabase environment variables. Check .env.local')
}

export const supabase = createClient(supabaseUrl, supabaseAnon)

// ── Query helpers ─────────────────────────────────────────────

export async function getOpenJobs(options?: {
  city?:   string
  isHot?:  boolean
  limit?:  number
  offset?: number
}): Promise<Job[]> {
  const { city, isHot, limit = 50, offset = 0 } = options ?? {}

  let query = supabase
    .from('jobs')
    .select(`
      id, job_code, seq, title, city, district,
      employment_type, start_date, teaching_age_groups,
      salary_min, salary_max, salary_raw,
      hours_per_day, housing_provided, visa_sponsorship,
      benefits, is_hot, status, published_at
    `)
    .eq('status', 'open')
    .order('is_hot',     { ascending: false })
    .order('created_at', { ascending: false })
    .range(offset, offset + limit - 1)

  if (city)          query = query.ilike('city', `%${city}%`)
  if (isHot != null) query = query.eq('is_hot', isHot)

  const { data, error } = await query
  if (error) throw error
  return (data ?? []) as Job[]
}

export async function getJob(id: string): Promise<Job | null> {
  const { data, error } = await supabase
    .from('jobs')
    .select(
      `id, job_code, seq, title, city, district,
       employment_type, start_date, teaching_age_groups,
       class_size, working_hours, hours_per_day, hours_per_week,
       salary_min, salary_max, salary_raw,
       housing_provided, housing_detail,
       vacation_days, visa_sponsorship,
       benefits, native_count,
       is_hot, status, published_at`
    )
    .eq('id', id)
    .eq('status', 'open')
    .single()

  if (error) return null
  return data as Job
}

export async function getEmployer(id: string): Promise<Employer | null> {
  const { data, error } = await supabase
    .from('employers')
    .select('id, company_name, company_type, city, location_full, is_active')
    .eq('id', id)
    .single()

  if (error) return null
  return data as Employer
}

// ── Public view queries  (no sensitive data ever returned) ────

/**
 * Query `public_jobs` view.
 * Returns only the columns defined in the view — school name,
 * address, contact info are absent at the database level.
 */
export async function getPublicJobs(options?: {
  city?:   string
  isHot?:  boolean
  limit?:  number
  offset?: number
}): Promise<PublicJob[]> {
  const { city, isHot, limit = 50, offset = 0 } = options ?? {}

  let query = supabase
    .from('public_jobs')
    .select('*')
    .order('is_hot',     { ascending: false })
    .order('hours_per_day', { ascending: true, nullsFirst: false })
    .range(offset, offset + limit - 1)

  if (city)          query = query.ilike('location', `%${city}%`)
  if (isHot != null) query = query.eq('is_hot', isHot)

  const { data, error } = await query
  if (error) throw error
  return (data ?? []) as PublicJob[]
}

/**
 * Query `public_candidates` view.
 * Name, email, phone, visa docs are absent at the database level.
 */
export async function getPublicCandidates(options?: {
  nationality?: string
  limit?:       number
  offset?:      number
}): Promise<PublicCandidate[]> {
  const { nationality, limit = 50, offset = 0 } = options ?? {}

  let query = supabase
    .from('public_candidates')
    .select('*')
    .range(offset, offset + limit - 1)

  if (nationality) query = query.ilike('nationality', `%${nationality}%`)

  const { data, error } = await query
  if (error) throw error
  return (data ?? []) as PublicCandidate[]
}
