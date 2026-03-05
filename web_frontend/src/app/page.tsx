'use client'

/**
 * Homepage — Emergency Quality Overhaul
 * Flow: HERO → Hear from Our Teachers → Featured Positions → Partner Marquee → CTA
 */

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import {
  motion,
  useScroll,
  useTransform,
} from 'framer-motion'
import {
  fadeInUp,
  staggerContainer,
  scaleIn,
  defaultViewport,
} from '@/lib/animations'
import { useEditMode } from '@/components/EditModeBar'
import type { PublicJob, AgeGroup } from '@/types'
const API = ''

// ── Name pool for testimonials (rotates monthly) ──
const NAME_POOL = [
  'Sarah M.', 'James K.', 'Emily R.', 'Michael T.', 'Jessica L.',
  'David H.', 'Amanda W.', 'Chris P.', 'Rachel B.', 'Tom S.',
]

// ── Fallback testimonials ──
const FALLBACK_TESTIMONIALS = [
  { text: 'BRIDGE made the entire process seamless. From my first inquiry to settling into my apartment, I never felt lost or unsupported.', stars: 5 },
  { text: 'The team was incredibly responsive and helped me find a position that perfectly matched my preferences. Highly recommend!', stars: 5 },
  { text: 'I was nervous about moving to Korea, but BRIDGE handled everything — visa, housing, school matching. Best decision I ever made.', stars: 5 },
  { text: 'Professional, transparent, and genuinely caring about teachers. They found me a great school in Gangnam within 2 weeks.', stars: 5 },
]

// ── Partner lists (fallback when API fails) ──
const FALLBACK_ACADEMIES = [
  'Chungdahm Learning', 'YBM', 'Warwick Franklin', 'Poly',
  'Wall Street English', 'April', 'Hillside IYASkola', 'Sogang SLP',
  'Fast Track Kids', 'Avalon', 'DYB Choisun', 'Rise Korea',
  'JLS Jungsang', 'Real Class', 'Siwon School',
  'Korea University Foreign Language Center', 'Crecerse',
  'LinguaEdu', 'Simson Edu', 'LexKim English', 'MiEdu',
  'Twinkle Language', 'SDA', 'Wiz Island', 'Kids College',
]
const FALLBACK_SCHOOLS = [
  'Busan International Foreign School', 'Dalton School',
  'Taejon Christian International School', 'Busan Foreign School',
  'Gyeonggi English Village', 'Dulwich College Seoul',
  'Korea International School', 'Chadwick International',
  'Gangwon English Camp', 'Dwight School Seoul',
  'Yongsan International School of Seoul', 'Saint Paul Academy',
  'Paju English Village', 'Seoul Scholars International',
  'North London Collegiate School', 'Seoul Foreign School',
  'Daegu International School', 'British Council Korea',
  'Gyeonggi International School', 'Jeju International School',
  'Mountain Cherry Academy', 'Seoul International School',
]

// ── Get deterministic name — rotates monthly ──
function getMonthlyName(index: number): string {
  const month = new Date().getMonth()
  return NAME_POOL[(index + month) % NAME_POOL.length]
}

// ── Fallback featured jobs (when API fails) ──
const FALLBACK_JOBS: PublicJob[] = [
  { job_id: 'BR-2401', location: 'Seoul', teaching_age: ['elementary'] as AgeGroup[], working_hours: 'Mon-Fri 9-6', monthly_salary: '2.5M KRW', housing: 'Housing + Severance', is_hot: false, starting_date: 'ASAP' } as PublicJob,
  { job_id: 'BR-2402', location: 'Busan', teaching_age: ['middle'] as AgeGroup[], working_hours: 'Mon-Fri 10-7', monthly_salary: '2.8M KRW', housing: 'Housing + Flight', is_hot: true, starting_date: 'ASAP' } as PublicJob,
  { job_id: 'BR-2403', location: 'Incheon', teaching_age: ['pre_k', 'kindergarten'] as AgeGroup[], working_hours: 'Mon-Fri 9-5', monthly_salary: '2.3M KRW', housing: 'Housing + Insurance', is_hot: false, starting_date: 'ASAP' } as PublicJob,
  { job_id: 'BR-2404', location: 'Daegu', teaching_age: ['elementary', 'middle'] as AgeGroup[], working_hours: 'Mon-Fri 10-6', monthly_salary: '2.6M KRW', housing: 'Housing + Bonus', is_hot: false, starting_date: 'ASAP' } as PublicJob,
]

// ── Strip markdown for preview ──
function stripMd(text: string, max = 140): string {
  return text
    .replace(/#{1,6}\s/g, '')
    .replace(/\*{1,3}/g, '')
    .replace(/>\s*/g, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/\n+/g, ' ')
    .trim()
    .slice(0, max)
}

// ── Seed-based hash for deterministic weekly shuffle ──
function seedHash(s: string, seed: number): number {
  let h = seed
  for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0
  return Math.abs(h)
}

// ── Format teaching age groups to short labels ──
const AGE_LABELS: Record<AgeGroup, string> = {
  pre_k: 'Pre-K', kindergarten: 'Kindy', elementary: 'Elem',
  middle: 'Middle', high: 'High', adult: 'Adult',
}
function formatTeachingAge(ages: AgeGroup[] | null): string {
  if (!ages || ages.length === 0) return ''
  return ages.map(a => AGE_LABELS[a] ?? a).join(' · ')
}

// ══════════════════════════════════════════════════════════════════════════
// SVG COMPONENTS
// ══════════════════════════════════════════════════════════════════════════

function StarIcon({ filled }: { filled: boolean }) {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 20 20" fill={filled ? '#facc15' : '#3f3f46'}>
      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
    </svg>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// INTERFACES
// ══════════════════════════════════════════════════════════════════════════

interface Testimonial {
  text: string
  stars: number
  name: string
}


// ══════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════════════════════

// ── Suspension bridge geometry ──
// Main cable: M 0 520 Q 700 180, 1400 520
// Left tower:  M 420 520 L 420 280
// Right tower: M 980 520 L 980 280
// Stay cables from tower tops to cable anchor points

export default function HomePage() {
  const heroRef = useRef<HTMLElement>(null)
  const [testimonials, setTestimonials] = useState<Testimonial[]>([])
  const [jobs, setJobs] = useState<PublicJob[]>([])
  const [showBridge, setShowBridge] = useState(false)
  const [academyNames, setAcademyNames] = useState<string[]>(FALLBACK_ACADEMIES)
  const [schoolNames, setSchoolNames] = useState<string[]>(FALLBACK_SCHOOLS)
  const editMode = useEditMode()

  // ── Trigger bridge drawing animation ──
  useEffect(() => {
    const t = setTimeout(() => setShowBridge(true), 300)
    return () => clearTimeout(t)
  }, [])

  // ── Hero parallax ──
  const { scrollYProgress: heroProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  })
  const heroOpacity = useTransform(heroProgress, [0, 0.6], [1, 0])
  const heroScale = useTransform(heroProgress, [0, 0.6], [1, 0.95])
  const arrowOpacity = useTransform(heroProgress, [0, 0.15], [1, 0])

  // ── Fetch testimonials ──
  useEffect(() => {
    fetch(`${API}/api/community/testimonials?limit=10`)
      .then(r => r.json())
      .then(d => {
        const posts = d?.data?.posts ?? []
        if (posts.length > 0) {
          const month = new Date().getMonth()
          const seeded = [...posts].sort((a, b) => {
            const ha = ((JSON.stringify(a).length * 31 + month) % 1000) / 1000
            const hb = ((JSON.stringify(b).length * 31 + month) % 1000) / 1000
            return ha - hb
          })
          const shuffled = seeded.slice(0, 4)
          setTestimonials(shuffled.map((p: { preview?: string }, i: number) => ({
            text: stripMd(p.preview ?? '', 140),
            stars: 5,
            name: getMonthlyName(i),
          })))
        } else {
          setTestimonials(FALLBACK_TESTIMONIALS.map((t, i) => ({ ...t, name: getMonthlyName(i) })))
        }
      })
      .catch(() => {
        setTestimonials(FALLBACK_TESTIMONIALS.map((t, i) => ({ ...t, name: getMonthlyName(i) })))
      })
  }, [])

  // ── Fetch featured jobs (weekly-seeded shuffle) ──
  useEffect(() => {
    fetch(`${API}/api/jobs?limit=20`)
      .then(r => r.json())
      .then(d => {
        const all: PublicJob[] = d?.data ?? []
        if (all.length > 0) {
          const now = new Date()
          const week = Math.floor((now.getTime() - new Date(now.getFullYear(), 0, 1).getTime()) / (7 * 86400000))
          const seeded = [...all].sort((a, b) => seedHash(a.job_id, week) - seedHash(b.job_id, week))
          setJobs(seeded.slice(0, 4))
        }
      })
      .catch(() => { setJobs(FALLBACK_JOBS) })
  }, [])

  // ── Fetch partners from API ──
  useEffect(() => {
    fetch(`${API}/api/partners`)
      .then(r => r.json())
      .then(d => {
        const partners = d?.data?.partners ?? []
        if (partners.length > 0) {
          const academies = partners.filter((p: { category: string }) => p.category === 'academy').map((p: { name: string }) => p.name)
          const schools = partners.filter((p: { category: string }) => p.category === 'school').map((p: { name: string }) => p.name)
          if (academies.length > 0) setAcademyNames(academies)
          if (schools.length > 0) setSchoolNames(schools)
        }
      })
      .catch(() => { /* keep fallback */ })
  }, [])

  return (
    <div className="bg-black">

      {/* ═══════════════════════════════════════════════════════════════════
          1. HERO — "BRIDGE" + tagline + background animations
          ═══════════════════════════════════════════════════════════════════ */}
      <section ref={heroRef} className="relative h-[85vh] min-h-[500px] flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-black via-[#0a0a0a] to-black" />

        {/* ── Suspension bridge ── */}
        <div className={showBridge ? 'bridge-active' : ''} style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
          <svg
            viewBox="0 0 1400 800"
            style={{ position: 'absolute', width: '100%', height: '100%' }}
            preserveAspectRatio="xMidYMid slice"
            fill="none"
          >
            <defs>
              <filter id="cableGlow">
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              <filter id="cableGlowStrong">
                <feGaussianBlur stdDeviation="8" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              <clipPath id="tClip">
                <rect x="0" y="0" width="1400" height="521" />
              </clipPath>
              {/* Light sweep gradient — bright spot travels left→right, infinite */}
              <linearGradient id="sweepGrad" gradientUnits="userSpaceOnUse" x1="-700" y1="400" x2="0" y2="400">
                <stop offset="0" stopColor="white" stopOpacity="0" />
                <stop offset="0.35" stopColor="white" stopOpacity="0" />
                <stop offset="0.5" stopColor="white" stopOpacity="0.7" />
                <stop offset="0.65" stopColor="white" stopOpacity="0" />
                <stop offset="1" stopColor="white" stopOpacity="0" />
                <animate attributeName="x1" values="-700;1400" dur="6s" repeatCount="indefinite" begin="2s" />
                <animate attributeName="x2" values="0;2100" dur="6s" repeatCount="indefinite" begin="2s" />
              </linearGradient>
            </defs>

            {/* ── Phase 1: Towers rise from bottom (0s ~ 0.8s) ── */}
            <g clipPath="url(#tClip)">
              <line x1={420} y1={520} x2={420} y2={280}
                className="bridge-tower"
                stroke="white" strokeWidth={2.5} strokeLinecap="round"
              />
            </g>
            <g clipPath="url(#tClip)">
              <line x1={980} y1={520} x2={980} y2={280}
                className="bridge-tower bridge-tower-r"
                stroke="white" strokeWidth={2.5} strokeLinecap="round"
              />
            </g>

            {/* ── Phase 2: Main cable draw with glow (0.6s ~ 1.4s) ── */}
            <path d="M 0 520 Q 700 180, 1400 520"
              className="bridge-cable"
              stroke="white" strokeWidth={2.5} strokeLinecap="round"
              filter="url(#cableGlow)"
            />
            {/* Glow sweep — bright dot chases cable draw, fades after */}
            <path d="M 0 520 Q 700 180, 1400 520"
              className="bridge-cable-glow"
              stroke="white" strokeWidth={4} strokeLinecap="round"
              filter="url(#cableGlowStrong)"
            />
            {/* Light sweep — SpaceX atmospheric glow, infinite after draw */}
            <path d="M 0 520 Q 700 180, 1400 520"
              stroke="url(#sweepGrad)" strokeWidth={4} strokeLinecap="round"
              opacity={0.7}
              filter="url(#cableGlowStrong)"
            />

            {/* ── Phase 3: Stay cables stagger spread (1.2s ~ 2.0s) ── */}
            <line x1={420} y1={280} x2={280} y2={410}
              className="bridge-stay bridge-stay-1"
              stroke="white" strokeWidth={0.8} strokeLinecap="round"
              strokeDasharray="180"
              style={{ '--d': '180' } as React.CSSProperties}
            />
            <line x1={420} y1={280} x2={200} y2={465}
              className="bridge-stay bridge-stay-2"
              stroke="white" strokeWidth={0.8} strokeLinecap="round"
              strokeDasharray="280"
              style={{ '--d': '280' } as React.CSSProperties}
            />
            <line x1={980} y1={280} x2={1120} y2={410}
              className="bridge-stay bridge-stay-3"
              stroke="white" strokeWidth={0.8} strokeLinecap="round"
              strokeDasharray="180"
              style={{ '--d': '180' } as React.CSSProperties}
            />
            <line x1={980} y1={280} x2={1200} y2={465}
              className="bridge-stay bridge-stay-4"
              stroke="white" strokeWidth={0.8} strokeLinecap="round"
              strokeDasharray="280"
              style={{ '--d': '280' } as React.CSSProperties}
            />
          </svg>
        </div>

        {/* ── Main text ── */}
        <motion.div
          className="relative z-10 text-center px-4"
          style={{ opacity: heroOpacity, scale: heroScale }}
        >
          <motion.h1
            className="text-[clamp(70px,14vw,180px)] font-semibold text-white leading-none tracking-tight mb-6"
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.2, ease: [0.25, 0.1, 0.25, 1] }}
          >
            BRIDGE
          </motion.h1>

          <motion.p
            className="text-xl sm:text-2xl md:text-3xl text-[#a1a1a6] font-medium tracking-tight"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
          >
            A career that changes your life.
          </motion.p>
        </motion.div>

        {/* ── Scroll indicator ── */}
        <motion.div
          className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-3"
          style={{ opacity: arrowOpacity }}
        >
          <span className="text-sm uppercase tracking-[0.3em] text-[#636366] font-semibold scroll-pulse">
            Scroll
          </span>
          <div className="scroll-bounce">
            <svg className="w-6 h-6 text-[#636366]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </div>
        </motion.div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          2. HEAR FROM OUR TEACHERS — Glassmorphism testimonial cards
          ═══════════════════════════════════════════════════════════════════ */}
      {testimonials.length > 0 && (
        <section className="bg-black py-24 sm:py-28 border-t border-white/[0.06]">
          <div className="max-w-[1120px] mx-auto px-5 sm:px-8">
            <motion.div
              className="text-center mb-16"
              variants={fadeInUp}
              initial="hidden"
              whileInView="visible"
              viewport={defaultViewport}
            >
              <p className="text-[#2997ff] text-sm font-semibold uppercase tracking-[0.2em] mb-3">Testimonials</p>
              <h2 className="text-3xl sm:text-4xl lg:text-[42px] font-bold text-white tracking-tight">
                Hear from Our Teachers
              </h2>
            </motion.div>

            <motion.div
              className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5"
              variants={staggerContainer}
              initial="hidden"
              whileInView="visible"
              viewport={defaultViewport}
            >
              {testimonials.slice(0, 4).map((t, i) => (
                <motion.div
                  key={i}
                  className="testimonial-glass rounded-2xl p-6 flex flex-col justify-between min-h-[220px]
                             hover:bg-white/[0.08] hover:-translate-y-1 transition-all duration-300"
                  variants={scaleIn}
                >
                  {/* Big quote icon */}
                  <div>
                    <span className="text-[#2997ff]/40 text-5xl font-serif leading-none select-none block mb-3">&ldquo;</span>
                    <p className="text-[#d1d1d6] text-sm leading-relaxed line-clamp-3">
                      {t.text}
                    </p>
                  </div>

                  {/* Name + Stars at bottom */}
                  <div className="mt-5 pt-4 border-t border-white/[0.06]">
                    <div className="flex gap-0.5 mb-1.5">
                      {Array.from({ length: 5 }).map((_, s) => (
                        <StarIcon key={s} filled={s < t.stars} />
                      ))}
                    </div>
                    <p className="text-[#86868b] text-xs font-semibold tracking-wide">{t.name}</p>
                  </div>
                </motion.div>
              ))}
            </motion.div>

            {/* "더 보러가기" link */}
            <motion.div
              className="text-center mt-10"
              variants={fadeInUp}
              initial="hidden"
              whileInView="visible"
              viewport={defaultViewport}
            >
              <Link
                href="/community/testimonials"
                className="text-sm font-medium text-white/50 hover:text-white/100 underline underline-offset-4 transition-all duration-300"
              >
                See more reviews &rarr;
              </Link>
            </motion.div>
          </div>
        </section>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          3. FEATURED POSITIONS — 4-card horizontal grid with shimmer
          ═══════════════════════════════════════════════════════════════════ */}
      {jobs.length > 0 && (
        <section className="bg-[#0a0a0a] py-24 sm:py-28 border-t border-white/[0.06]">
          <div className="max-w-[1120px] mx-auto px-5 sm:px-8">
            <motion.div
              className="text-center mb-16"
              variants={fadeInUp}
              initial="hidden"
              whileInView="visible"
              viewport={defaultViewport}
            >
              <p className="text-[#2997ff] text-sm font-semibold uppercase tracking-[0.2em] mb-3">Opportunities</p>
              <h2 className="text-3xl sm:text-4xl lg:text-[42px] font-bold text-white tracking-tight">
                Featured Positions
              </h2>
            </motion.div>

            <motion.div
              className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5"
              variants={staggerContainer}
              initial="hidden"
              whileInView="visible"
              viewport={defaultViewport}
            >
              {jobs.slice(0, 4).map((job) => (
                <motion.div key={job.job_id} variants={scaleIn}>
                  <Link
                    href="/jobs"
                    className="group block shimmer-card bg-[#141414] border border-white/[0.06] rounded-xl p-6
                               hover:bg-[#1a1a1a] transition-all duration-300 hover:-translate-y-1 hover:scale-[1.02]
                               hover:shadow-[0_8px_32px_rgba(41,151,255,0.12)]"
                  >
                    {/* Location pill + Job ID */}
                    <div className="mb-5">
                      <span className="inline-block text-[11px] font-semibold px-3 py-1 rounded-full bg-white/[0.08] text-[#a1a1a6] mb-2">
                        {job.location ?? 'Korea'}
                      </span>
                      {job.is_hot && (
                        <span className="ml-2 text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 uppercase align-middle">
                          Hot
                        </span>
                      )}
                      <p className="text-[#2997ff] text-xs font-bold tracking-wide mt-1">
                        Job #{job.job_id}
                      </p>
                    </div>

                    {/* Detail rows */}
                    <div className="space-y-2 text-[13px]">
                      {job.teaching_age && job.teaching_age.length > 0 && (
                        <div className="flex justify-between gap-2">
                          <span className="text-[#636366] font-medium shrink-0">Student Age</span>
                          <span className="text-[#a1a1a6] text-right">{formatTeachingAge(job.teaching_age)}</span>
                        </div>
                      )}
                      {job.working_hours && (
                        <div className="flex justify-between gap-2">
                          <span className="text-[#636366] font-medium shrink-0">Hours</span>
                          <span className="text-[#a1a1a6] text-right">{job.working_hours}</span>
                        </div>
                      )}
                      {job.monthly_salary && (
                        <div className="flex justify-between gap-2">
                          <span className="text-[#636366] font-medium shrink-0">Salary</span>
                          <span className="text-[#a1a1a6] text-right truncate">{job.monthly_salary}</span>
                        </div>
                      )}
                      {job.housing && (
                        <div className="flex justify-between gap-2">
                          <span className="text-[#636366] font-medium shrink-0">Benefits</span>
                          <span className="text-[#a1a1a6] text-right truncate max-w-[140px]">{job.housing}</span>
                        </div>
                      )}
                    </div>

                    {/* View details link */}
                    <div className="mt-5 pt-4 border-t border-white/[0.06] text-right">
                      <span className="inline-block text-xs font-semibold text-[#2997ff] transition-transform duration-300 group-hover:translate-x-1">
                        View details &rarr;
                      </span>
                    </div>
                  </Link>
                </motion.div>
              ))}
            </motion.div>

            <motion.div
              className="text-center mt-12"
              variants={fadeInUp}
              initial="hidden"
              whileInView="visible"
              viewport={defaultViewport}
            >
              <Link
                href="/jobs"
                className="inline-flex items-center justify-center gap-2 px-8 py-3.5 text-sm font-semibold rounded-full
                           border border-white/[0.15] text-white
                           hover:bg-white/[0.08] hover:border-white/[0.25] transition-all duration-300"
              >
                View all positions &rarr;
              </Link>
            </motion.div>
          </div>
        </section>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          4. PARTNER MARQUEE — Academies + Schools 2줄
          ═══════════════════════════════════════════════════════════════════ */}
      <section className="bg-[#111111] py-14 overflow-hidden border-t border-white/[0.06] relative">
        {editMode && (
          <div className="absolute top-3 right-4 z-20">
            <Link
              href="/admin/partners"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-500/90 text-white text-[12px] font-semibold rounded-lg hover:bg-amber-600 transition-colors shadow-lg"
            >
              ✏️ 파트너 관리
            </Link>
          </div>
        )}
        {/* Row 1 — Schools & Institutions */}
        <div className="mb-4">
          <p className="text-[11px] font-semibold text-white/40 uppercase tracking-[0.15em] text-center mb-3">
            Schools &amp; Institutions
          </p>
          <div className="relative" aria-hidden="true">
            <div className="marquee-track marquee-track--slow">
              {[...schoolNames, ...schoolNames, ...schoolNames].map((name, i) => (
                <span
                  key={`s-${i}`}
                  className="shrink-0 px-6 sm:px-8 text-[0.85rem] font-semibold select-none whitespace-nowrap text-white/50 tracking-[0.05em]"
                >
                  {name}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Row 2 — Our Partner */}
        <div>
          <p className="text-[11px] font-semibold text-white/40 uppercase tracking-[0.15em] text-center mb-3">
            Our Partner
          </p>
          <div className="relative" aria-hidden="true">
            <div className="marquee-track marquee-track--mid">
              {[...academyNames, ...academyNames, ...academyNames].map((name, i) => (
                <span
                  key={`a-${i}`}
                  className="shrink-0 px-6 sm:px-8 text-[0.85rem] font-semibold select-none whitespace-nowrap text-white/50 tracking-[0.05em]"
                >
                  {name}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          5. CTA — Start Your Journey
          ═══════════════════════════════════════════════════════════════════ */}
      <section
        className="relative py-20 sm:py-[80px] border-t border-white/[0.06] overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)' }}
      >
        <div className="relative z-10 max-w-[700px] mx-auto px-5 sm:px-8">
          <motion.div
            className="text-center"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <h2 className="text-4xl sm:text-5xl md:text-[56px] font-semibold text-white tracking-tight leading-[1.1] mb-5">
              Start Your Journey
            </h2>
            <p className="text-white/60 text-base sm:text-lg leading-relaxed mb-12 max-w-[480px] mx-auto">
              Whether you&apos;re a teacher or an employer, we&apos;ll find the perfect match.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/apply"
                className="cta-btn-primary inline-flex items-center justify-center px-8 sm:px-10 py-4 text-base font-semibold rounded-lg
                           bg-[#2563EB] text-white w-full sm:w-auto sm:min-w-[220px]
                           hover:brightness-[1.15] hover:scale-[1.03] hover:shadow-[0_8px_30px_rgba(37,99,235,0.45)]
                           active:scale-[0.98] transition-all duration-300"
              >
                I&apos;m a Teacher
              </Link>
              <Link
                href="/inquiry"
                className="cta-btn-outline inline-flex items-center justify-center px-8 sm:px-10 py-4 text-base font-semibold rounded-lg
                           border border-white text-white w-full sm:w-auto sm:min-w-[220px]
                           hover:bg-white/10 hover:scale-[1.03]
                           active:scale-[0.98] transition-all duration-300"
              >
                I&apos;m Hiring
              </Link>
            </div>

            {/* Contact info */}
            <p className="mt-10 text-white/30 text-sm">
              bridgejobkr@gmail.com
            </p>
          </motion.div>
        </div>
      </section>
    </div>
  )
}
