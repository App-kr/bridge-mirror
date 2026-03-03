'use client'

/**
 * Homepage — Emergency Quality Overhaul
 * Flow: HERO → Hear from Our Teachers → Featured Positions → CTA → Partner Marquee
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

// ── Partner lists (schools vs academies) ──
const ACADEMY_NAMES = [
  'Chungdahm Learning', 'JLS Jungsang', 'Poly', 'April', 'DYB Choisun',
  'Sogang SLP', 'Rise Korea', 'Warwick Franklin', 'Fast Track Kids',
  'Hillside IYASkola', 'Avalon', 'Elan', 'YBM', 'Wall Street English',
  'Siwon School', 'Real Class', 'Kyvis Kids',
]
const SCHOOL_NAMES = [
  'Korea University Foreign Language Center', 'Seoul International School',
  'Yongsan International School', 'Busan Foreign School',
  'Daegu International School', 'Jeju International School',
  'EPIK', 'GEPIK', 'SMOE', 'Gyeonggi English Village',
  'Paju English Village', 'Gangwon English Camp', 'British Council Korea',
]

// ── Get deterministic name — rotates weekly ──
function getWeeklyName(index: number): string {
  const now = new Date()
  const week = Math.floor((now.getTime() - new Date(now.getFullYear(), 0, 1).getTime()) / (7 * 24 * 60 * 60 * 1000))
  return NAME_POOL[(index + week) % NAME_POOL.length]
}

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
// Main cable: parabolic arc  |  Deck: horizontal line at y=680
// Vertical hangers connect cable to deck at regular intervals
const CABLE_Y = (x: number) => 680 - 380 * (1 - ((x - 700) / 700) ** 2) // parabola peak at center
const HANGER_XS = Array.from({ length: 21 }, (_, i) => i * 70)           // every 70px across 1400

export default function HomePage() {
  const heroRef = useRef<HTMLElement>(null)
  const [testimonials, setTestimonials] = useState<Testimonial[]>([])
  const [jobs, setJobs] = useState<PublicJob[]>([])
  const [showBridge, setShowBridge] = useState(false)

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
          const week = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 1).getTime()) / (7 * 86400000))
          const seeded = [...posts].sort((a, b) => {
            const ha = ((JSON.stringify(a).length * 31 + week) % 1000) / 1000
            const hb = ((JSON.stringify(b).length * 31 + week) % 1000) / 1000
            return ha - hb
          })
          const shuffled = seeded.slice(0, 4)
          setTestimonials(shuffled.map((p: { preview?: string }, i: number) => ({
            text: stripMd(p.preview ?? '', 140),
            stars: 5,
            name: getWeeklyName(i),
          })))
        } else {
          setTestimonials(FALLBACK_TESTIMONIALS.map((t, i) => ({ ...t, name: getWeeklyName(i) })))
        }
      })
      .catch(() => {
        setTestimonials(FALLBACK_TESTIMONIALS.map((t, i) => ({ ...t, name: getWeeklyName(i) })))
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
      .catch(() => { /* silent — no jobs section if API fails */ })
  }, [])

  return (
    <div className="bg-black">

      {/* ═══════════════════════════════════════════════════════════════════
          1. HERO — "BRIDGE" + tagline + background animations
          ═══════════════════════════════════════════════════════════════════ */}
      <section ref={heroRef} className="relative h-[85vh] min-h-[500px] flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-black via-[#0a0a0a] to-black" />

        {/* ── Suspension bridge silhouette ── */}
        <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
          <svg
            viewBox="0 0 1400 800"
            style={{ position: 'absolute', width: '100%', height: '100%' }}
            preserveAspectRatio="xMidYMid slice"
            fill="none"
          >
            <defs>
              <linearGradient id="cableGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="white" stopOpacity="0" />
                <stop offset="30%" stopColor="white" stopOpacity="0.15" />
                <stop offset="50%" stopColor="white" stopOpacity="0.25" />
                <stop offset="70%" stopColor="white" stopOpacity="0.15" />
                <stop offset="100%" stopColor="white" stopOpacity="0" />
              </linearGradient>
              <linearGradient id="deckGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="white" stopOpacity="0" />
                <stop offset="20%" stopColor="white" stopOpacity="0.08" />
                <stop offset="50%" stopColor="white" stopOpacity="0.12" />
                <stop offset="80%" stopColor="white" stopOpacity="0.08" />
                <stop offset="100%" stopColor="white" stopOpacity="0" />
              </linearGradient>
              <filter id="glow">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>

            {/* Main cable — parabolic arc */}
            <path
              d={`M 0 680 Q 700 ${680 - 380}, 1400 680`}
              stroke="url(#cableGrad)"
              strokeWidth={2.5}
              strokeLinecap="round"
              strokeDasharray="2200"
              strokeDashoffset={showBridge ? 0 : 2200}
              filter="url(#glow)"
              style={{ transition: 'stroke-dashoffset 2.5s cubic-bezier(0.16, 1, 0.3, 1) 0.2s' }}
            />

            {/* Deck line */}
            <line
              x1="0" y1="680" x2="1400" y2="680"
              stroke="url(#deckGrad)"
              strokeWidth={1}
              strokeDasharray="1400"
              strokeDashoffset={showBridge ? 0 : 1400}
              style={{ transition: 'stroke-dashoffset 2s cubic-bezier(0.16, 1, 0.3, 1) 0.6s' }}
            />

            {/* Vertical hangers — cable to deck */}
            {HANGER_XS.map((x, i) => {
              const cy = CABLE_Y(x)
              if (cy >= 678) return null // skip edges where cable meets deck
              return (
                <line
                  key={i}
                  x1={x} y1={cy} x2={x} y2={680}
                  stroke="white"
                  strokeWidth={0.5}
                  opacity={showBridge ? 0.06 + 0.04 * (1 - Math.abs(x - 700) / 700) : 0}
                  style={{ transition: `opacity 0.8s ease ${0.8 + i * 0.05}s` }}
                />
              )
            })}

            {/* Tower pillars at 1/4 and 3/4 */}
            {[350, 1050].map((tx) => (
              <line
                key={tx}
                x1={tx} y1={CABLE_Y(tx)} x2={tx} y2={750}
                stroke="white"
                strokeWidth={1.5}
                opacity={showBridge ? 0.1 : 0}
                style={{ transition: 'opacity 1.2s ease 0.4s' }}
              />
            ))}
          </svg>
        </div>

        {/* ── Starlink-style fan curves overlay ── */}
        <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
          <svg
            viewBox="0 0 1400 800"
            style={{ position: 'absolute', width: '100%', height: '100%' }}
            preserveAspectRatio="xMidYMid slice"
            fill="none"
          >
            <defs>
              <filter id="starGlow">
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>

            {/* Line 1 — widest arc, topmost */}
            <path
              d="M 0 750 Q 700 200, 1400 750"
              stroke="white"
              strokeWidth={1.5}
              strokeLinecap="round"
              opacity={showBridge ? 0.04 : 0}
              strokeDasharray="2000"
              strokeDashoffset={showBridge ? 0 : 2000}
              style={{ transition: 'stroke-dashoffset 2.5s cubic-bezier(0.25, 0.1, 0.25, 1) 0s, opacity 0.6s ease 0s' }}
            />

            {/* Line 2 */}
            <path
              d="M 0 760 Q 700 300, 1400 760"
              stroke="white"
              strokeWidth={1.8}
              strokeLinecap="round"
              opacity={showBridge ? 0.06 : 0}
              strokeDasharray="2000"
              strokeDashoffset={showBridge ? 0 : 2000}
              style={{ transition: 'stroke-dashoffset 2.5s cubic-bezier(0.25, 0.1, 0.25, 1) 0.3s, opacity 0.6s ease 0.3s' }}
            />

            {/* Line 3 — main curve (glow base) */}
            <path
              d="M 0 770 Q 700 380, 1400 770"
              stroke="white"
              strokeWidth={6}
              strokeLinecap="round"
              opacity={showBridge ? 0.08 : 0}
              filter="url(#starGlow)"
              strokeDasharray="2000"
              strokeDashoffset={showBridge ? 0 : 2000}
              style={{ transition: 'stroke-dashoffset 2.5s cubic-bezier(0.25, 0.1, 0.25, 1) 0.6s, opacity 0.8s ease 0.6s' }}
            />
            {/* Line 3 — main curve (crisp) */}
            <path
              d="M 0 770 Q 700 380, 1400 770"
              stroke="white"
              strokeWidth={2.5}
              strokeLinecap="round"
              opacity={showBridge ? 0.12 : 0}
              strokeDasharray="2000"
              strokeDashoffset={showBridge ? 0 : 2000}
              style={{ transition: 'stroke-dashoffset 2.5s cubic-bezier(0.25, 0.1, 0.25, 1) 0.6s, opacity 0.6s ease 0.6s' }}
            />

            {/* Line 4 */}
            <path
              d="M 0 780 Q 700 440, 1400 780"
              stroke="white"
              strokeWidth={1.8}
              strokeLinecap="round"
              opacity={showBridge ? 0.06 : 0}
              strokeDasharray="2000"
              strokeDashoffset={showBridge ? 0 : 2000}
              style={{ transition: 'stroke-dashoffset 2.5s cubic-bezier(0.25, 0.1, 0.25, 1) 0.9s, opacity 0.6s ease 0.9s' }}
            />

            {/* Line 5 — lowest arc */}
            <path
              d="M 0 790 Q 700 500, 1400 790"
              stroke="white"
              strokeWidth={1.2}
              strokeLinecap="round"
              opacity={showBridge ? 0.03 : 0}
              strokeDasharray="2000"
              strokeDashoffset={showBridge ? 0 : 2000}
              style={{ transition: 'stroke-dashoffset 2.5s cubic-bezier(0.25, 0.1, 0.25, 1) 1.2s, opacity 0.6s ease 1.2s' }}
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
                className="inline-flex items-center gap-2 text-sm font-semibold text-[#2997ff] hover:text-[#6cb6ff] transition-colors duration-200"
              >
                더 보러가기
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
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
                    className="group block shimmer-card bg-white/[0.03] border border-white/[0.08] rounded-2xl p-6
                               hover:bg-white/[0.07] transition-all duration-300 hover:-translate-y-1 hover:scale-[1.02]
                               hover:shadow-[0_8px_32px_rgba(41,151,255,0.12)]"
                  >
                    {/* Location + Job ID header */}
                    <div className="mb-5">
                      <h3 className="text-white font-semibold text-base tracking-tight leading-snug">
                        {job.location ?? 'Korea'}
                      </h3>
                      <span className="text-[#2997ff] text-xs font-bold tracking-wide">
                        {job.job_id}
                      </span>
                      {job.is_hot && (
                        <span className="ml-2 text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 uppercase align-middle">
                          Hot
                        </span>
                      )}
                    </div>

                    {/* Detail rows */}
                    <div className="space-y-2 text-[13px]">
                      {job.starting_date && (
                        <div className="flex justify-between gap-2">
                          <span className="text-[#636366] font-medium shrink-0">Starting Date</span>
                          <span className="text-[#a1a1a6] text-right truncate">{job.starting_date}</span>
                        </div>
                      )}
                      {job.teaching_age && job.teaching_age.length > 0 && (
                        <div className="flex justify-between gap-2">
                          <span className="text-[#636366] font-medium shrink-0">Teaching Age</span>
                          <span className="text-[#a1a1a6] text-right">{formatTeachingAge(job.teaching_age)}</span>
                        </div>
                      )}
                      {job.working_hours && (
                        <div className="flex justify-between gap-2">
                          <span className="text-[#636366] font-medium shrink-0">Working Hours</span>
                          <span className="text-[#a1a1a6] text-right">{job.working_hours}</span>
                        </div>
                      )}
                      {job.monthly_salary && (
                        <div className="flex justify-between gap-2">
                          <span className="text-[#636366] font-medium shrink-0">Monthly Salary</span>
                          <span className="text-[#a1a1a6] text-right truncate">{job.monthly_salary}</span>
                        </div>
                      )}
                      {job.housing && (
                        <div className="flex justify-between gap-2">
                          <span className="text-[#636366] font-medium shrink-0">Housing</span>
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
                전체 채용 보기
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </Link>
            </motion.div>
          </div>
        </section>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          4. CTA — Start Your Journey
          ═══════════════════════════════════════════════════════════════════ */}
      <section className="relative py-28 sm:py-32 border-t border-white/[0.06] overflow-hidden bg-black">

        <div className="relative z-10 max-w-[700px] mx-auto px-5 sm:px-8">
          <motion.div
            className="text-center"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <p className="text-[#2997ff] text-sm font-semibold uppercase tracking-[0.2em] mb-4">Get Started</p>
            <h2 className="text-4xl sm:text-5xl md:text-[56px] font-bold text-white tracking-tight leading-[1.1] mb-5">
              Start Your Journey
            </h2>
            <p className="text-[#a1a1a6] text-base sm:text-lg leading-relaxed mb-12 max-w-[480px] mx-auto">
              Whether you&apos;re looking to teach in Korea or find the perfect teacher, BRIDGE connects you.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/apply"
                className="cta-btn-primary inline-flex items-center justify-center px-10 py-4 text-base font-semibold rounded-full
                           bg-[#2563EB] text-white min-w-[220px]
                           hover:bg-[#1d4ed8] hover:shadow-[0_8px_30px_rgba(37,99,235,0.45)]
                           active:scale-[0.98] transition-all duration-300"
              >
                I&apos;m a Teacher
              </Link>
              <Link
                href="/inquiry"
                className="cta-btn-outline inline-flex items-center justify-center px-10 py-4 text-base font-semibold rounded-full
                           border-2 border-white/25 text-white min-w-[220px]
                           hover:bg-white hover:text-black hover:border-white hover:shadow-[0_8px_30px_rgba(255,255,255,0.12)]
                           active:scale-[0.98] transition-all duration-300"
              >
                I&apos;m Hiring
              </Link>
            </div>

            {/* Contact info */}
            <p className="mt-10 text-[#636366] text-sm">
              bridgejobkr@gmail.com
            </p>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          5. PARTNER MARQUEE — 학교/캠프 + 학원 2줄
          ═══════════════════════════════════════════════════════════════════ */}
      <section className="bg-black py-14 overflow-hidden border-t border-white/[0.06]">
        <div className="max-w-[980px] mx-auto px-5 sm:px-8 mb-6">
          <p className="text-[11px] font-semibold text-[#48484a] uppercase tracking-[0.2em] text-center">
            Trusted by schools &amp; organizations across Korea
          </p>
        </div>

        {/* Row 1 — Academies */}
        <div className="mb-2">
          <p className="text-[10px] font-semibold text-[#636366] uppercase tracking-[0.15em] text-center mb-3">
            Academies
          </p>
          <div className="relative" aria-hidden="true">
            <div className="marquee-track marquee-track--slow">
              {[...ACADEMY_NAMES, ...ACADEMY_NAMES, ...ACADEMY_NAMES].map((name, i) => (
                <span
                  key={`a-${i}`}
                  className="shrink-0 px-6 sm:px-8 text-base sm:text-lg font-semibold select-none whitespace-nowrap text-[#3a3a3c]"
                >
                  {name}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Row 2 — Schools & Organizations */}
        <div>
          <p className="text-[10px] font-semibold text-[#636366] uppercase tracking-[0.15em] text-center mb-3">
            Schools &amp; Organizations
          </p>
          <div className="relative" aria-hidden="true">
            <div className="marquee-track marquee-track--slow" style={{ animationDirection: 'reverse' }}>
              {[...SCHOOL_NAMES, ...SCHOOL_NAMES, ...SCHOOL_NAMES].map((name, i) => (
                <span
                  key={`s-${i}`}
                  className="shrink-0 px-6 sm:px-8 text-base sm:text-lg font-semibold select-none whitespace-nowrap text-[#3a3a3c]"
                >
                  {name}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          6. SETTLING IN KOREA — Internet services + Social links
          ═══════════════════════════════════════════════════════════════════ */}
      <section className="bg-black py-16 sm:py-20 border-t border-white/[0.06]">
        <div className="max-w-[980px] mx-auto px-5 sm:px-8">

          {/* Internet Services */}
          <motion.div
            className="text-center mb-14"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <p className="text-[#2997ff] text-sm font-semibold uppercase tracking-[0.2em] mb-3">Settling In</p>
            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-3">
              Internet &amp; Mobile in Korea
            </h2>
            <p className="text-[#86868b] text-sm max-w-lg mx-auto">
              We help you set up internet and mobile service from day one. Korea has the world&apos;s fastest internet — here are the top providers.
            </p>
          </motion.div>

          <motion.div
            className="grid grid-cols-3 gap-4 sm:gap-6 max-w-lg mx-auto mb-16"
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            {/* KT */}
            <motion.div variants={fadeInUp} className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-white/[0.04] border border-white/[0.06] hover:bg-white/[0.07] transition-colors">
              <div className="w-12 h-12 rounded-xl bg-[#e4002b]/10 flex items-center justify-center">
                <span className="text-lg font-black text-[#e4002b]">KT</span>
              </div>
              <span className="text-xs font-semibold text-[#a1a1a6]">olleh</span>
            </motion.div>

            {/* SKT */}
            <motion.div variants={fadeInUp} className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-white/[0.04] border border-white/[0.06] hover:bg-white/[0.07] transition-colors">
              <div className="w-12 h-12 rounded-xl bg-[#e4002b]/10 flex items-center justify-center">
                <span className="text-sm font-black text-[#e4002b]">SK</span>
              </div>
              <span className="text-xs font-semibold text-[#a1a1a6]">T world</span>
            </motion.div>

            {/* LG U+ */}
            <motion.div variants={fadeInUp} className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-white/[0.04] border border-white/[0.06] hover:bg-white/[0.07] transition-colors">
              <div className="w-12 h-12 rounded-xl bg-[#e6007e]/10 flex items-center justify-center">
                <span className="text-sm font-black text-[#e6007e]">U+</span>
              </div>
              <span className="text-xs font-semibold text-[#a1a1a6]">LG Uplus</span>
            </motion.div>
          </motion.div>

          {/* Social Media */}
          <motion.div
            className="text-center"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <p className="text-[#86868b] text-sm mb-5">Follow us &amp; join the community</p>
            <div className="flex items-center justify-center gap-5">
              {/* YouTube */}
              <a href="https://youtube.com" target="_blank" rel="noopener noreferrer"
                className="w-11 h-11 rounded-full bg-white/[0.06] border border-white/[0.08] flex items-center justify-center hover:bg-[#ff0000]/20 hover:border-[#ff0000]/30 transition-all group">
                <svg className="w-5 h-5 text-[#636366] group-hover:text-[#ff0000] transition-colors" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                </svg>
              </a>
              {/* Facebook */}
              <a href="https://facebook.com" target="_blank" rel="noopener noreferrer"
                className="w-11 h-11 rounded-full bg-white/[0.06] border border-white/[0.08] flex items-center justify-center hover:bg-[#1877f2]/20 hover:border-[#1877f2]/30 transition-all group">
                <svg className="w-5 h-5 text-[#636366] group-hover:text-[#1877f2] transition-colors" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                </svg>
              </a>
              {/* Threads */}
              <a href="https://threads.net" target="_blank" rel="noopener noreferrer"
                className="w-11 h-11 rounded-full bg-white/[0.06] border border-white/[0.08] flex items-center justify-center hover:bg-white/[0.15] hover:border-white/[0.25] transition-all group">
                <svg className="w-5 h-5 text-[#636366] group-hover:text-white transition-colors" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.59 12c.025 3.083.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.96-.065-1.182.408-2.26 1.332-3.031.88-.735 2.088-1.18 3.59-1.323.98-.094 1.975-.059 2.96.104.026-.82-.065-1.555-.267-2.186-.277-.865-.775-1.452-1.478-1.744-.758-.315-1.72-.327-2.86-.037l-.536-1.953c1.54-.39 2.946-.357 4.07.096 1.07.431 1.856 1.268 2.28 2.421.294.8.44 1.74.44 2.818l.002.348c.986.56 1.77 1.334 2.262 2.36.722 1.507.842 4.065-1.16 6.028-1.79 1.756-4.016 2.548-7.21 2.572zm2.032-8.081c-.94-.176-1.89-.218-2.828-.126-1.14.109-2.025.44-2.633.983-.55.49-.78 1.087-.648 1.684.166.752.86 1.336 1.885 1.59.423.104.88.154 1.347.154.609 0 1.235-.09 1.765-.266.89-.294 1.547-.834 1.96-1.604.37-.687.564-1.544.59-2.55a8.658 8.658 0 0 0-1.438.135z"/>
                </svg>
              </a>
              {/* Reddit */}
              <a href="https://reddit.com" target="_blank" rel="noopener noreferrer"
                className="w-11 h-11 rounded-full bg-white/[0.06] border border-white/[0.08] flex items-center justify-center hover:bg-[#ff4500]/20 hover:border-[#ff4500]/30 transition-all group">
                <svg className="w-5 h-5 text-[#636366] group-hover:text-[#ff4500] transition-colors" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 .029-.463.33.33 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z"/>
                </svg>
              </a>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  )
}
