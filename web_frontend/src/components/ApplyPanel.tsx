'use client'

/**
 * ApplyPanel — 3-Step Quick Apply slide-in panel
 * Step 1: Your Profile  |  Step 2: Experience & Docs  |  Step 3: Review & Submit
 * Fixed overlay: z-50, slides in from the right.
 * JWT magic-link dedup: same token logic as /apply page.
 */

import { useEffect, useState } from 'react'
import type { PublicJob } from '@/types'

const API       = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'bridge_apply_token'

// ── Options ───────────────────────────────────────────────────────────────────
const NATIONALITIES = ['American','Canadian','British','Australian','New Zealander','South African','Irish','Other']
const VISA_OPTS     = ['E-2 (현재보유)','E-1','F-4','F-5','F-6','F-2','H-2','D-10','D-6','준비 중 (신규)','없음']
const EDUCATION     = ["Bachelor's Degree","Master's Degree","Doctorate (PhD)","Associate Degree","Other"]
const DOC_STATUS    = ['완비 (All Ready)','일부 준비 중','아직 없음 / 준비 필요']
const INTERVIEW     = ['Weekdays (Mon-Fri)','Weekends (Sat-Sun)','Evenings only','Flexible / Anytime']
const LOCATIONS     = ['Seoul','Incheon','Busan','Suwon','Daegu','Daejeon','Ulsan','Jeju','Gyeonggi','Gangwon','Any']
const AGE_GROUPS    = ['Pre-K','Kindergarten','Elementary','Middle School','High School','Adult / Conversation']
const HOW_TO        = ['BRIDGE 웹사이트','Facebook','Instagram','카카오톡','지인 소개','Craigslist','Google','기타']

const STEP_LABELS = ['Your Profile', 'Experience & Docs', 'Review & Submit']

// ── Sub-components ────────────────────────────────────────────────────────────
function Sec({ title }: { title: string }) {
  return <p className="section-heading">{title}</p>
}

function Lock({ label }: { label: string }) {
  return (
    <p className="text-xs text-amber-600 flex items-center gap-1 mt-0.5 mb-1">
      🔒 {label} — AES-256 암호화 저장
    </p>
  )
}

function SingleTog({
  value, onChange, options,
}: { value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((o) => (
        <button key={o} type="button" onClick={() => onChange(o)}
          className={value === o ? 'tog-on' : 'tog'}>
          {o}
        </button>
      ))}
    </div>
  )
}

function MultiTog({
  value, onChange, options,
}: { value: string[]; onChange: (v: string[]) => void; options: string[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((o) => (
        <button key={o} type="button"
          onClick={() => onChange(value.includes(o) ? value.filter((x) => x !== o) : [...value, o])}
          className={value.includes(o) ? 'tog-on' : 'tog'}>
          {o}
        </button>
      ))}
    </div>
  )
}

// ── Initial state ─────────────────────────────────────────────────────────────
const INIT = {
  full_name: '', email: '', how_to: '', file_urls: '',
  nationality: '', ancestry: '', dob: '', gender: '',
  current_location: '', marital_status: '', dependents: '', pets: '',
  education: '', major: '', certification: '',
  e_visa: '', arc_holders: '', passport: '', criminal_record: '', doc_status: '',
  start_date: '', area_prefs: [] as string[], target_age: [] as string[],
  job_prefs: '', experience: '', reference: '', interview_time: '',
  current_salary: '', desired_salary: '', housing: '', personal_considerations: '',
  religion: '', health_info: '', criminal_record_check: '',
  kakaotalk: '', mobile_phone: '',
  agreement: false, facts: false,
  admin_notes: '',
}

// ── Panel ─────────────────────────────────────────────────────────────────────
export default function ApplyPanel({
  job,
  onClose,
}: {
  job: PublicJob | null
  onClose: () => void
}) {
  const [step,     setStep]     = useState(1)
  const [form,     setForm]     = useState(INIT)
  const [status,   setStatus]   = useState<'idle' | 'submitting' | 'success' | 'error'>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  // Reset form when a new job is selected
  useEffect(() => {
    if (job) { setForm(INIT); setStatus('idle'); setErrorMsg(''); setStep(1) }
  }, [job?.job_id])

  // Close on Escape key; lock body scroll
  useEffect(() => {
    if (!job) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handler)
      document.body.style.overflow = ''
    }
  }, [job, onClose])

  if (!job) return null

  const set = (field: keyof typeof INIT) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((p) => ({ ...p, [field]: e.target.value }))

  function handleNext() {
    setErrorMsg('')
    if (step === 1 && !form.full_name.trim()) {
      setErrorMsg('Full name is required before continuing.')
      return
    }
    setStep((s) => Math.min(s + 1, 3))
  }

  function handleBack() {
    setErrorMsg('')
    setStep((s) => Math.max(s - 1, 1))
  }

  async function handleSubmit() {
    if (!form.agreement) { setErrorMsg('Please agree to the terms.'); return }
    setStatus('submitting')
    try {
      const existingToken = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null
      const payload = {
        ...form,
        area_prefs: (form.area_prefs as string[]).join(', '),
        target_age: (form.target_age as string[]).join(', '),
        agreement: form.agreement ? 'yes' : '',
        facts: form.facts ? 'yes' : '',
        source: 'web_form',
        admin_notes: form.admin_notes || `Quick Apply from /jobs — Job: ${job?.job_id ?? ''}`,
        ...(existingToken ? { apply_token: existingToken } : {}),
      }
      const res  = await fetch(`${API}/api/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const json = await res.json()
      if (!res.ok || !json.success) throw new Error(json.detail ?? json.message ?? 'Error')
      if (json.data?.apply_token && typeof window !== 'undefined') {
        localStorage.setItem(TOKEN_KEY, json.data.apply_token)
      }
      setStatus('success')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Submission failed.')
      setStatus('error')
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
        onClick={onClose}
        aria-hidden
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-full max-w-2xl bg-white z-50
                      shadow-2xl overflow-y-auto flex flex-col"
        style={{ animation: 'slideIn 0.28s ease-out' }}
      >
        <style>{`@keyframes slideIn{from{transform:translateX(100%)}to{transform:translateX(0)}}`}</style>

        {/* ── Sticky header ── */}
        <div className="sticky top-0 bg-white border-b border-gray-200 z-10 shrink-0">
          <div className="flex items-start justify-between px-6 py-4">
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-400 font-mono">{job.job_id}</p>
              <h2 className="font-bold text-gray-900 text-lg leading-tight">Quick Apply</h2>
              <p className="text-sm text-gray-500 truncate">{job.location} · {(job.teaching_age ?? []).join(', ')}</p>
            </div>
            <button
              onClick={onClose}
              className="w-9 h-9 ml-3 shrink-0 rounded-full bg-gray-100 hover:bg-gray-200
                         flex items-center justify-center text-gray-500 hover:text-gray-900
                         transition-colors text-lg"
            >✕</button>
          </div>

          {/* Step progress dots */}
          <div className="flex items-center px-6 pb-3 gap-2">
            {STEP_LABELS.map((label, i) => {
              const n     = i + 1
              const done  = n < step
              const active = n === step
              return (
                <div key={n} className="flex items-center flex-1 last:flex-none">
                  <div className="flex items-center gap-1.5 shrink-0">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all
                      ${done   ? 'bg-blue-600 text-white'
                      : active ? 'bg-blue-600 text-white ring-2 ring-blue-200 ring-offset-1'
                      :          'bg-gray-100 text-gray-400'}`}>
                      {done ? '✓' : n}
                    </div>
                    <span className={`text-xs font-medium hidden sm:block
                      ${active ? 'text-gray-800' : done ? 'text-gray-500' : 'text-gray-400'}`}>
                      {label}
                    </span>
                  </div>
                  {i < STEP_LABELS.length - 1 && (
                    <div className={`flex-1 h-px mx-2 ${n < step ? 'bg-blue-400' : 'bg-gray-200'}`} />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* ── Success ── */}
        {status === 'success' ? (
          <div className="flex flex-col items-center justify-center flex-1 gap-4 px-8 py-16 text-center">
            <div className="text-5xl">🎉</div>
            <h3 className="text-xl font-bold text-gray-900">Application Received!</h3>
            <p className="text-gray-500 text-sm">
              Our team will review your profile and contact you shortly.
              You can update your profile anytime by applying again.
            </p>
            <button onClick={onClose} className="btn-primary mt-2">Close Panel</button>
          </div>
        ) : (

        /* ── Form body ── */
        <div className="px-6 py-6 space-y-6">

          {/* ══ STEP 1: Your Profile ══ */}
          {step === 1 && (
            <>
              <section className="space-y-3">
                <Sec title="How did you find BRIDGE?" />
                <SingleTog
                  value={form.how_to}
                  onChange={(v) => setForm((p) => ({ ...p, how_to: v }))}
                  options={HOW_TO}
                />
              </section>

              <section className="space-y-4">
                <Sec title="Basic Information" />
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Full Name *</label>
                    <Lock label="이름 암호화 저장" />
                    <input className="input" placeholder="e.g. John Smith"
                      value={form.full_name} onChange={set('full_name')} />
                  </div>
                  <div>
                    <label className="label">Email</label>
                    <Lock label="이메일 암호화 저장" />
                    <input type="email" className="input" placeholder="you@example.com"
                      value={form.email} onChange={set('email')} />
                  </div>
                </div>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Mobile Phone</label>
                    <Lock label="전화번호 암호화 저장" />
                    <input className="input" placeholder="+1 555 000 0000"
                      value={form.mobile_phone} onChange={set('mobile_phone')} />
                  </div>
                  <div>
                    <label className="label">KakaoTalk ID</label>
                    <Lock label="카카오톡 ID 암호화 저장" />
                    <input className="input" placeholder="KakaoTalk username"
                      value={form.kakaotalk} onChange={set('kakaotalk')} />
                  </div>
                </div>
              </section>

              <section className="space-y-4">
                <Sec title="Personal Information" />
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Nationality</label>
                    <select className="input" value={form.nationality} onChange={set('nationality')}>
                      <option value="">Select…</option>
                      {NATIONALITIES.map((n) => <option key={n}>{n}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="label">Family Ancestry</label>
                    <input className="input" placeholder="e.g. Korean-American"
                      value={form.ancestry} onChange={set('ancestry')} />
                  </div>
                </div>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Date of Birth</label>
                    <input type="date" className="input" value={form.dob} onChange={set('dob')} />
                  </div>
                  <div>
                    <label className="label">Current Location</label>
                    <input className="input" placeholder="City, Country"
                      value={form.current_location} onChange={set('current_location')} />
                  </div>
                </div>
                <div>
                  <label className="label">Gender</label>
                  <SingleTog
                    value={form.gender}
                    onChange={(v) => setForm((p) => ({ ...p, gender: v }))}
                    options={['Male', 'Female', 'Non-binary', 'Prefer not to say']}
                  />
                </div>
                <div className="grid sm:grid-cols-3 gap-4">
                  <div>
                    <label className="label">Marital Status</label>
                    <select className="input" value={form.marital_status} onChange={set('marital_status')}>
                      <option value="">Select…</option>
                      {['Single','Married','Divorced','Widowed','Prefer not to say'].map((m) => <option key={m}>{m}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="label">Dependents</label>
                    <input className="input" placeholder="e.g. None, 1 child" value={form.dependents} onChange={set('dependents')} />
                  </div>
                  <div>
                    <label className="label">Pets</label>
                    <input className="input" placeholder="e.g. None, 1 dog" value={form.pets} onChange={set('pets')} />
                  </div>
                </div>
              </section>
            </>
          )}

          {/* ══ STEP 2: Experience & Docs ══ */}
          {step === 2 && (
            <>
              <section className="space-y-4">
                <Sec title="Education & Qualifications" />
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Education Level</label>
                    <select className="input" value={form.education} onChange={set('education')}>
                      <option value="">Select…</option>
                      {EDUCATION.map((e) => <option key={e}>{e}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="label">Major / Field of Study</label>
                    <input className="input" placeholder="e.g. English Literature"
                      value={form.major} onChange={set('major')} />
                  </div>
                </div>
                <div>
                  <label className="label">Certification (TESOL / TEFL / CELTA)</label>
                  <input className="input" placeholder="e.g. TESOL Certificate — 2023"
                    value={form.certification} onChange={set('certification')} />
                </div>
              </section>

              <section className="space-y-4">
                <Sec title="Visa & Documents" />
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Visa Status</label>
                    <select className="input" value={form.e_visa} onChange={set('e_visa')}>
                      <option value="">Select…</option>
                      {VISA_OPTS.map((v) => <option key={v}>{v}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="label">ARC Status</label>
                    <select className="input" value={form.arc_holders} onChange={set('arc_holders')}>
                      <option value="">Select…</option>
                      <option>Yes — ARC currently valid</option>
                      <option>No — Applying from abroad</option>
                      <option>Expired / In process</option>
                    </select>
                  </div>
                </div>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Passport</label>
                    <Lock label="여권 정보 암호화 저장" />
                    <input className="input" placeholder="e.g. Valid until 2028-05, US Passport"
                      value={form.passport} onChange={set('passport')} />
                  </div>
                  <div>
                    <label className="label">Document Status</label>
                    <select className="input" value={form.doc_status} onChange={set('doc_status')}>
                      <option value="">Select…</option>
                      {DOC_STATUS.map((d) => <option key={d}>{d}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="label">Criminal Record</label>
                  <Lock label="전과기록 암호화 저장" />
                  <input className="input" placeholder="If none, write 'None'"
                    value={form.criminal_record} onChange={set('criminal_record')} />
                </div>
              </section>

              <section className="space-y-4">
                <Sec title="Work Preferences" />
                <div>
                  <label className="label mb-2">Preferred Locations</label>
                  <MultiTog
                    value={form.area_prefs as string[]}
                    onChange={(arr) => setForm((p) => ({ ...p, area_prefs: arr }))}
                    options={LOCATIONS}
                  />
                </div>
                <div>
                  <label className="label mb-2">Teaching Age Groups</label>
                  <MultiTog
                    value={form.target_age as string[]}
                    onChange={(arr) => setForm((p) => ({ ...p, target_age: arr }))}
                    options={AGE_GROUPS}
                  />
                </div>
                <div>
                  <label className="label">Housing</label>
                  <SingleTog
                    value={form.housing}
                    onChange={(v) => setForm((p) => ({ ...p, housing: v }))}
                    options={['Yes - Need housing', 'No - Have own housing', 'Negotiable']}
                  />
                </div>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Start Date</label>
                    <input className="input" placeholder="e.g. ASAP, March 2026"
                      value={form.start_date} onChange={set('start_date')} />
                  </div>
                  <div>
                    <label className="label">Interview Availability</label>
                    <select className="input" value={form.interview_time} onChange={set('interview_time')}>
                      <option value="">Select…</option>
                      {INTERVIEW.map((i) => <option key={i}>{i}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="label">Job Notes / Preferences</label>
                  <textarea className="textarea h-20" placeholder="School type, schedule, any special requirements..."
                    value={form.job_prefs} onChange={set('job_prefs')} />
                </div>
              </section>

              <section className="space-y-4">
                <Sec title="Experience & Reference" />
                <div>
                  <label className="label">Teaching Experience</label>
                  <textarea className="textarea h-24" placeholder="Years, countries, age groups, subjects…"
                    value={form.experience} onChange={set('experience')} />
                </div>
                <div>
                  <label className="label">Employment Reference</label>
                  <textarea className="textarea h-16" placeholder="Name, Position, Contact"
                    value={form.reference} onChange={set('reference')} />
                </div>
              </section>

              <section className="space-y-4">
                <Sec title="Salary" />
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Current Salary (₩/month)</label>
                    <input className="input" placeholder="e.g. 2,500,000 KRW or N/A"
                      value={form.current_salary} onChange={set('current_salary')} />
                  </div>
                  <div>
                    <label className="label">Desired Salary (₩/month)</label>
                    <input className="input" placeholder="e.g. 2,800,000 ~ 3,200,000 KRW"
                      value={form.desired_salary} onChange={set('desired_salary')} />
                  </div>
                </div>
                <div>
                  <label className="label">Personal Considerations</label>
                  <input className="input" placeholder="e.g. Must be near subway"
                    value={form.personal_considerations} onChange={set('personal_considerations')} />
                </div>
              </section>

              <section className="space-y-3">
                <Sec title="Attach Files" />
                <p className="text-xs text-gray-400 -mt-1">Google Drive / Dropbox links (CV, degree, certificates)</p>
                <input className="input" placeholder="https://drive.google.com/…"
                  value={form.file_urls} onChange={set('file_urls')} />
              </section>
            </>
          )}

          {/* ══ STEP 3: Review & Submit ══ */}
          {step === 3 && (
            <>
              <section className="space-y-4 bg-amber-50 rounded-2xl border border-amber-200 p-4">
                <Sec title="Sensitive Information (AES-256 Encrypted)" />
                <p className="text-xs text-amber-700 -mt-2 mb-3">
                  Required by Korean visa law. All fields below are encrypted — never shared publicly.
                </p>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Religion</label>
                    <Lock label="종교 암호화 저장" />
                    <input className="input" placeholder="e.g. None, Christian, Prefer not to say"
                      value={form.religion} onChange={set('religion')} />
                  </div>
                  <div>
                    <label className="label">Health Information</label>
                    <Lock label="건강 정보 암호화 저장" />
                    <input className="input" placeholder="e.g. No issues, Asthma (controlled)"
                      value={form.health_info} onChange={set('health_info')} />
                  </div>
                </div>
                <div>
                  <label className="label">Criminal Record Check Status</label>
                  <Lock label="범죄경력조회 암호화 저장" />
                  <input className="input" placeholder="e.g. Clean — FBI check obtained 2025-01"
                    value={form.criminal_record_check} onChange={set('criminal_record_check')} />
                </div>
              </section>

              <section className="space-y-3">
                <Sec title="Agreement & Declaration" />
                <label className="flex items-start gap-3 cursor-pointer group">
                  <input
                    type="checkbox"
                    className="mt-1 w-4 h-4 accent-blue-600 shrink-0"
                    checked={form.agreement}
                    onChange={() => setForm((p) => ({ ...p, agreement: !p.agreement }))}
                  />
                  <span className="text-sm text-gray-700">
                    <strong>Agreement:</strong> I agree that BRIDGE may share my non-sensitive profile
                    with potential employers, and my contact details will only be released with my consent.
                  </span>
                </label>
                <label className="flex items-start gap-3 cursor-pointer group">
                  <input
                    type="checkbox"
                    className="mt-1 w-4 h-4 accent-blue-600 shrink-0"
                    checked={form.facts}
                    onChange={() => setForm((p) => ({ ...p, facts: !p.facts }))}
                  />
                  <span className="text-sm text-gray-700">
                    <strong>Facts:</strong> All information provided is accurate and truthful.
                  </span>
                </label>
              </section>
            </>
          )}

          {/* Error */}
          {(status === 'error' || errorMsg) && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
              {errorMsg}
            </div>
          )}

          {/* Navigation */}
          <div className="flex gap-3 pt-2">
            {step > 1 && (
              <button type="button" onClick={handleBack} className="btn-secondary flex-none px-5">
                ← Back
              </button>
            )}
            {step < 3 && (
              <button type="button" onClick={handleNext} className="btn-primary flex-1 py-2.5">
                Next Step →
              </button>
            )}
            {step === 3 && (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={status === 'submitting'}
                className="btn-primary flex-1 py-2.5"
              >
                {status === 'submitting' ? 'Submitting…' : 'Submit Application'}
              </button>
            )}
          </div>

          {/* Trust badge */}
          {step === 3 && (
            <div className="trust-badge border-t border-gray-100 pt-3">
              <span>🔒</span>
              <span>All personal data is AES-256 encrypted and securely protected.</span>
            </div>
          )}

        </div>
        )}
      </div>
    </>
  )
}
