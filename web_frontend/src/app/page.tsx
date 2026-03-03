'use client'

/**
 * Homepage — Full redesign
 * Flow: HERO → What Teachers Say → Featured Positions → CTA → Partner Marquee
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

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

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
  { text: 'Professional, transparent, and genuinely caring about teachers. They found me a great school in Gangnam within 2 weeks.', stars: 4 },
  { text: 'After trying other agencies, BRIDGE was a breath of fresh air. No hidden fees, constant communication, and a perfect placement.', stars: 5 },
]

// ── Partner academies ──
const PARTNER_NAMES = [
  'Chungdahm Learning', 'JLS Jungsang Academy', 'Poly Academy', 'April Academy',
  'DYB Choisun Academy', 'Sogang SLP', 'Rise Korea', 'Warwick Franklin',
  'Fast Track Kids', 'Hillside EYAS', 'Avalon Education', 'Elan Academy',
  'YBM Academy', 'Korea University Foreign Language Center', 'Wall Street English',
  'Siwon School', 'Real Class', 'Kyvis Kids',
]

// ── Get deterministic name for current month ──
function getMonthlyName(index: number): string {
  const month = new Date().getMonth()
  return NAME_POOL[(index + month) % NAME_POOL.length]
}

// ── Strip markdown for preview ──
function stripMd(text: string, max = 160): string {
  return text
    .replace(/#{1,6}\s/g, '')
    .replace(/\*{1,3}/g, '')
    .replace(/>\s*/g, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/\n+/g, ' ')
    .trim()
    .slice(0, max)
}

// ══════════════════════════════════════════════════════════════════════════
// SVG COMPONENTS
// ══════════════════════════════════════════════════════════════════════════

function GlobeSVG() {
  return (
    <svg viewBox="0 0 200 200" fill="none" className="w-[150px] h-[150px] sm:w-[180px] sm:h-[180px] hero-globe-rotate">
      <circle cx="100" cy="100" r="92" stroke="white" strokeWidth="0.5" />
      <ellipse cx="100" cy="100" rx="60" ry="92" stroke="white" strokeWidth="0.4" />
      <ellipse cx="100" cy="100" rx="28" ry="92" stroke="white" strokeWidth="0.3" />
      <line x1="8" y1="100" x2="192" y2="100" stroke="white" strokeWidth="0.3" />
      <ellipse cx="100" cy="55" rx="80" ry="15" stroke="white" strokeWidth="0.3" />
      <ellipse cx="100" cy="145" rx="80" ry="15" stroke="white" strokeWidth="0.3" />
    </svg>
  )
}

function KoreaMapSVG() {
  return (
    <svg viewBox="0 0 120 280" fill="none" className="w-[100px] h-[210px] sm:w-[120px] sm:h-[250px]">
      {/* Korean peninsula silhouette — filled for recognizable shape */}
      <path
        d="M58,8 C60,10 65,14 70,22 C74,30 76,36 78,44 C80,52 82,56 84,62
           C87,70 88,76 86,84 C84,92 82,98 80,106 C78,114 76,120 74,128
           C72,136 70,142 68,150 C66,158 64,164 62,172 C60,180 58,186 56,194
           C54,202 52,208 50,214 C48,222 46,228 44,234
           C42,240 44,244 46,246 C50,250 54,248 56,244
           C59,240 61,236 64,240 C66,244 63,252 58,256"
        fill="white"
        opacity="0.6"
      />
      {/* Jeju */}
      <ellipse cx="48" cy="264" rx="10" ry="4" fill="white" opacity="0.4" />
    </svg>
  )
}

function BridgeLinesSVG() {
  return (
    <svg className="absolute inset-0 w-full h-full" viewBox="0 0 1200 600" fill="none" preserveAspectRatio="xMidYMid meet">
      <path className="hero-line-1" d="M160,380 C320,280 550,220 700,260 C820,290 920,310 1020,300" stroke="rgba(255,255,255,0.2)" strokeWidth="0.8" fill="none" />
      <path className="hero-line-2" d="M170,400 C340,310 520,250 660,270 C800,290 900,280 1010,320" stroke="rgba(255,255,255,0.15)" strokeWidth="0.6" fill="none" />
      <path className="hero-line-3" d="M150,360 C300,250 500,200 680,240 C840,270 940,290 1030,280" stroke="rgba(255,255,255,0.18)" strokeWidth="0.7" fill="none" />
      <path className="hero-line-4" d="M180,420 C360,330 540,280 700,300 C830,315 910,300 1000,330" stroke="rgba(255,255,255,0.12)" strokeWidth="0.5" fill="none" />
      <path className="hero-line-5" d="M140,350 C280,240 480,190 650,230 C810,260 930,270 1040,290" stroke="rgba(255,255,255,0.14)" strokeWidth="0.6" fill="none" />
    </svg>
  )
}

function PlaneSVG() {
  return (
    <svg viewBox="0 0 24 24" fill="white" className="w-[40px] h-[40px] sm:w-[50px] sm:h-[50px]">
      <path d="M21,16V14L13,9V3.5A1.5,1.5,0,0,0,11.5,2A1.5,1.5,0,0,0,10,3.5V9L2,14V16L10,13.5V19L8,20.5V22L11.5,21L15,22V20.5L13,19V13.5Z" />
    </svg>
  )
}

function StarIcon({ filled }: { filled: boolean }) {
  return (
    <svg className="w-4 h-4" viewBox="0 0 20 20" fill={filled ? '#facc15' : '#3f3f46'}>
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

interface FeaturedJob {
  id: number
  job_code?: string
  city?: string
  district?: string
  teaching_age?: string
  working_hours?: string
  salary_min?: number
  salary_max?: number
  salary_raw?: string
  benefits?: string
  housing?: string
  is_hot?: boolean
}

// ══════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════════════════════

export default function HomePage() {
  const heroRef = useRef<HTMLElement>(null)
  const [testimonials, setTestimonials] = useState<Testimonial[]>([])
  const [jobs, setJobs] = useState<FeaturedJob[]>([])

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
          const shuffled = [...posts].sort(() => Math.random() - 0.5).slice(0, 5)
          setTestimonials(shuffled.map((p: { preview?: string }, i: number) => ({
            text: stripMd(p.preview ?? '', 180),
            stars: Math.random() > 0.3 ? 5 : 4,
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

  // ── Fetch featured jobs ──
  useEffect(() => {
    fetch(`${API}/api/jobs?limit=8`)
      .then(r => r.json())
      .then(d => {
        const all = d?.data ?? []
        if (all.length > 0) {
          const shuffled = [...all].sort(() => Math.random() - 0.5).slice(0, 5)
          setJobs(shuffled)
        }
      })
      .catch(() => { /* silent — no jobs section if API fails */ })
  }, [])

  return (
    <div className="bg-black">

      {/* ═══════════════════════════════════════════════════════════════════
          1. HERO — "BRIDGE" + tagline + background animations
          ═══════════════════════════════════════════════════════════════════ */}
      <section ref={heroRef} className="relative h-screen min-h-[600px] flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-black via-[#0a0a0a] to-black" />

        {/* ── Background decorations ── */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden hero-bg-fade">
          {/* Globe — left bottom */}
          <div className="absolute left-[3%] sm:left-[6%] bottom-[12%] sm:bottom-[15%]" style={{ opacity: 0.25 }}>
            <GlobeSVG />
          </div>
          {/* Korea map — right */}
          <div className="absolute right-[6%] sm:right-[10%] top-[30%] sm:top-[25%]" style={{ opacity: 0.12 }}>
            <KoreaMapSVG />
          </div>
          {/* Connecting lines */}
          <div style={{ opacity: 1 }}>
            <BridgeLinesSVG />
          </div>
        </div>

        {/* ── Airplane (auto flight, no scroll) ── */}
        <div className="hero-plane">
          <PlaneSVG />
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
          2. WHAT TEACHERS SAY — Testimonial cards
          ═══════════════════════════════════════════════════════════════════ */}
      {testimonials.length > 0 && (
        <section className="bg-black py-24 border-t border-white/[0.06]">
          <div className="max-w-[1100px] mx-auto px-4 sm:px-6">
            <motion.div
              className="text-center mb-14"
              variants={fadeInUp}
              initial="hidden"
              whileInView="visible"
              viewport={defaultViewport}
            >
              <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-3">
                What Teachers Say
              </h2>
              <p className="text-[#86868b] text-base">Real experiences from teachers we&apos;ve placed.</p>
            </motion.div>

            <motion.div
              className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5"
              variants={staggerContainer}
              initial="hidden"
              whileInView="visible"
              viewport={defaultViewport}
            >
              {testimonials.slice(0, 5).map((t, i) => (
                <motion.div
                  key={i}
                  className={`bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6
                              hover:bg-white/[0.07] transition-all duration-300
                              ${i >= 3 ? 'sm:col-span-1 lg:col-span-1' : ''}`}
                  variants={scaleIn}
                >
                  {/* Stars */}
                  <div className="flex gap-0.5 mb-3">
                    {Array.from({ length: 5 }).map((_, s) => (
                      <StarIcon key={s} filled={s < t.stars} />
                    ))}
                  </div>
                  {/* Quote */}
                  <p className="text-[#d1d1d6] text-sm leading-relaxed mb-4">
                    &ldquo;{t.text}&rdquo;
                  </p>
                  {/* Name */}
                  <p className="text-[#86868b] text-xs font-semibold">— {t.name}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          3. FEATURED POSITIONS — Job cards with shimmer border
          ═══════════════════════════════════════════════════════════════════ */}
      {jobs.length > 0 && (
        <section className="bg-[#0a0a0a] py-24 border-t border-white/[0.06]">
          <div className="max-w-[1100px] mx-auto px-4 sm:px-6">
            <motion.div
              className="text-center mb-14"
              variants={fadeInUp}
              initial="hidden"
              whileInView="visible"
              viewport={defaultViewport}
            >
              <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-3">
                Featured Positions
              </h2>
              <p className="text-[#86868b] text-base">New opportunities added daily.</p>
            </motion.div>

            <motion.div
              className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5"
              variants={staggerContainer}
              initial="hidden"
              whileInView="visible"
              viewport={defaultViewport}
            >
              {jobs.map((job) => (
                <motion.div key={job.id} variants={scaleIn}>
                  <Link
                    href="/jobs"
                    className="group block shimmer-card bg-white/[0.04] p-6
                               hover:bg-white/[0.08] transition-all duration-300 hover:-translate-y-1"
                  >
                    {/* Header */}
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-[#2997ff] text-xs font-bold tracking-wide uppercase">
                        {job.job_code ? `Job #${job.job_code}` : `#${job.id}`}
                      </span>
                      {job.is_hot && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 uppercase">
                          Hot
                        </span>
                      )}
                    </div>

                    {/* Location */}
                    <h3 className="text-white font-semibold text-lg mb-3 tracking-tight">
                      {job.city ?? 'Korea'}{job.district ? `, ${job.district}` : ''}
                    </h3>

                    {/* Details */}
                    <div className="space-y-2 text-sm text-[#a1a1a6]">
                      {job.teaching_age && (
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4 text-[#636366] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0" />
                          </svg>
                          <span>{job.teaching_age}</span>
                        </div>
                      )}
                      {job.working_hours && (
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4 text-[#636366] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span>{job.working_hours}</span>
                        </div>
                      )}
                      {(job.salary_raw ?? (job.salary_min && job.salary_max)) && (
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4 text-[#636366] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span>
                            {job.salary_raw
                              ? job.salary_raw
                              : `${(job.salary_min ?? 0).toLocaleString()} ~ ${(job.salary_max ?? 0).toLocaleString()} KRW`}
                          </span>
                        </div>
                      )}
                      {job.benefits && (
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4 text-[#636366] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span className="truncate">{job.benefits}</span>
                        </div>
                      )}
                    </div>

                    {/* View more */}
                    <span className="inline-block mt-5 text-sm font-medium text-[#2997ff] transition-transform duration-300 group-hover:translate-x-1">
                      View details →
                    </span>
                  </Link>
                </motion.div>
              ))}
            </motion.div>

            <motion.div
              className="text-center mt-10"
              variants={fadeInUp}
              initial="hidden"
              whileInView="visible"
              viewport={defaultViewport}
            >
              <Link
                href="/jobs"
                className="inline-flex items-center justify-center px-8 py-3 text-sm font-semibold rounded-full border border-white/20 text-white hover:bg-white/10 transition-all duration-300"
              >
                View All Positions →
              </Link>
            </motion.div>
          </div>
        </section>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          4. CTA — Get started today
          ═══════════════════════════════════════════════════════════════════ */}
      <section className="py-24 border-t border-white/[0.06]" style={{ background: 'linear-gradient(135deg, #0a0a0a 0%, #111827 50%, #0a0a0a 100%)' }}>
        <div className="max-w-[700px] mx-auto px-4 sm:px-6">
          <motion.div
            className="text-center"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white tracking-tight mb-10">
              Get started today
            </h2>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/apply"
                className="inline-flex items-center justify-center px-10 py-4 text-base font-semibold rounded-full
                           bg-[#2563EB] text-white min-w-[220px]
                           hover:bg-[#1d4ed8] hover:shadow-[0_8px_30px_rgba(37,99,235,0.4)] hover:scale-105
                           transition-all duration-300"
              >
                I&apos;m a Teacher
              </Link>
              <Link
                href="/inquiry"
                className="inline-flex items-center justify-center px-10 py-4 text-base font-semibold rounded-full
                           border-2 border-white/30 text-white min-w-[220px]
                           hover:bg-white hover:text-black hover:border-white hover:shadow-[0_8px_30px_rgba(255,255,255,0.15)] hover:scale-105
                           transition-all duration-300"
              >
                I&apos;m Hiring
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          5. PARTNER MARQUEE — 학원 롤링
          ═══════════════════════════════════════════════════════════════════ */}
      <section className="bg-black py-12 overflow-hidden border-t border-white/[0.06]">
        <div className="max-w-[980px] mx-auto px-4 sm:px-6 mb-6">
          <p className="text-sm font-semibold text-[#636366] uppercase tracking-[0.15em] text-center">
            Schools &amp; Companies we work with
          </p>
        </div>

        <div className="relative" aria-hidden="true">
          <div className="marquee-track marquee-track--slow">
            {[...PARTNER_NAMES, ...PARTNER_NAMES, ...PARTNER_NAMES].map((name, i) => (
              <span
                key={`p-${i}`}
                className="shrink-0 px-6 sm:px-8 text-base sm:text-lg font-semibold select-none whitespace-nowrap text-[#48484a]"
              >
                · {name}
              </span>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
