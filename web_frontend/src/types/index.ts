// ============================================================
//  BRIDGE — Shared TypeScript Types
//  Mirrors the Supabase ATS schema
// ============================================================

export type VisaType = 'E-2' | 'E-1' | 'F-4' | 'F-5' | 'F-6' | 'F-2' | 'H-2' | 'D-10' | 'D-6' | 'G-1' | 'ARC'

export type CandidateStatus = 'Active' | 'Inactive' | 'Placed' | 'Blacklist'

export type JobStatus = 'open' | 'filled' | 'hold' | 'cancelled'

export type EmploymentType = 'full_time' | 'part_time' | 'contract'

export type AgeGroup = 'pre_k' | 'kindergarten' | 'elementary' | 'middle' | 'high' | 'adult'

export type ApplicationStatus =
  | 'applied' | 'reviewing' | 'interview'
  | 'offered'  | 'rejected'  | 'hired' | 'withdrawn'

// ── Database row types ────────────────────────────────────────

export interface Job {
  id:                  string
  legacy_id:           number | null
  employer_id:         string | null
  job_code:            string
  seq:                 number
  title:               string | null
  city:                string | null
  district:            string | null
  location_full:       string | null
  employment_type:     EmploymentType
  start_date:          string | null
  teaching_age_groups: AgeGroup[]
  class_size:          string | null
  working_hours:       string | null
  hours_per_day:       number | null
  hours_per_week:      string | null
  salary_min:          number | null
  salary_max:          number | null
  salary_raw:          string | null
  housing_provided:    boolean
  housing_detail:      string | null
  vacation_days:       string | null
  visa_sponsorship:    boolean
  benefits:            string[]
  native_count:        string | null
  is_hot:              boolean
  status:              JobStatus
  published_at:        string | null
  created_at:          string
  updated_at:          string
}

export interface Employer {
  id:               string
  legacy_id:        number | null
  company_name:     string
  company_type:     string | null
  email:            string | null
  phone:            string | null
  contact_name:     string | null
  location_full:    string | null
  city:             string | null
  is_active:        boolean
  created_at:       string
  updated_at:       string
}

// ── Form payloads (web form submissions) ─────────────────────

export interface CandidateApplyPayload {
  full_name:        string
  email?:           string
  nationality?:     string
  date_of_birth?:   string
  gender?:          string
  current_location?: string
  phone_primary?:   string
  phone_kakao?:     string
  visa_raw?:        string
  availability_date?: string
  preferred_age_groups?: AgeGroup[]
  preferred_locations?:  string[]
  experience_text?:  string
  certifications?:   string[]
  salary_desired_min?: number
  salary_desired_max?: number
  housing_needed?:   string
}

export interface ClientInquiryPayload {
  company_name:   string
  email?:         string
  phone?:         string
  contact_name?:  string
  location_full?: string
  start_date?:    string
  teaching_age_groups?: AgeGroup[]
  working_hours?: string
  salary_raw?:    string
  housing_type?:  string
  benefits?:      string
  memo?:          string
}

// ── API response wrapper ──────────────────────────────────────

export interface ApiResponse<T = unknown> {
  success: boolean
  message: string
  data?:   T
}

// ================================================================
//  PUBLIC VIEW TYPES  (Supabase views: public_jobs · public_candidates)
//
//  These interfaces are the ONLY permitted shapes for data that
//  reaches the browser.  All sensitive fields are absent by design.
//  Field names mirror the SQL view column aliases exactly.
// ================================================================

/**
 * public_jobs view
 * BLOCKED in view: employer_id · school_name · location_full · district
 *                  internal_notes · contact_person · phone · email
 */
export interface PublicJob {
  /** City only — never street address.  e.g. "Busan", "Seoul" */
  location:                 string | null

  /** Human-readable job reference.  e.g. "Job. 1003" */
  job_id:                   string

  /** e.g. "2026. 3. 1" or "ASAP" */
  starting_date:            string | null

  /** Normalised age-group array.  e.g. ["kindergarten","elementary"] */
  teaching_age:             AgeGroup[] | null

  /** e.g. "~12명 이내" */
  class_size:               string | null

  /** Exact schedule string.  e.g. "09:00~16:10" */
  working_hours:            string | null

  /**
   * Raw salary string preserved as-entered.
   * e.g. "2,40m KRW Not negotiable"  /  "2,50m - 2,80m KRW"
   */
  monthly_salary:           string | null

  /** e.g. "주 20-25시간" */
  teaching_hours_per_week:  string | null

  /** Paid leave summary */
  vacation:                 string | null

  /** e.g. "Approx. 3" */
  native_teacher_count:     string | null

  /**
   * Housing offer.
   * e.g. "Fully furnished provided"  /  "₩500,000/month allowance"  /  "Not provided"
   */
  housing:                  string | null

  /**
   * Teacher eligibility note.
   * e.g. "E-2 Visa Sponsorship · Open to overseas applicants"
   *   /  "Currently residing in Korea preferred"
   */
  preferences:              string | null

  /** Benefits array.  e.g. ["Visa sponsorship","Severance pay","Pension"] */
  employee_benefits:        string[] | null

  // ── UI helpers (non-sensitive) ──
  is_hot:                   boolean
  employment_type:          EmploymentType
  hours_per_day:            number | null
}

/**
 * public_candidates view
 * BLOCKED in view: id · legacy_id · full_name · first_name · last_name
 *                  email · phone_primary · phone_kakao
 *                  visa_types · arc_expiry · criminal_record · passport_country
 *                  documents_status · references_avail · salary_current
 */
export interface PublicCandidate {
  /** Sequential display number — never the internal UUID */
  ref_id:               number

  /** Country of citizenship.  e.g. "미국", "캐나다" */
  nationality:          string | null

  /**
   * Approximate birth year derived from age.
   * e.g. 1997  (never full date)
   */
  birth_year:           number | null

  /** City/country only.  e.g. "캐나다", "Seoul" */
  current_location:     string | null

  /** ISO-style date or descriptive.  e.g. "2026-03-01" */
  available_start_date: string | null

  /** Qualification array.  e.g. ["TESOL","BA Education","TEFL"] */
  certifications:       string[] | null

  /**
   * Teaching experience in or relevant to Korea.
   * e.g. "3 yr(s)"  /  "New to Korea"
   */
  korea_experience:     string | null

  /**
   * University major / degree field.
   * NULL until candidates.degree_major column is added to schema.
   */
  major:                string | null

  /**
   * Salary expectation (formatted).
   * e.g. "2.5m ~ 3.0m KRW"  /  "Negotiable"
   */
  desired_salary:       string | null
}
