'use client'

/**
 * Homepage — Emergency Quality Overhaul
 * Flow: HERO → Hear from Our Teachers → Featured Positions → Partner Marquee → CTA
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import {
  motion,
  useScroll,
  useTransform,
  AnimatePresence,
} from 'framer-motion'
import {
  fadeInUp,
  staggerContainer,
  scaleIn,
  defaultViewport,
} from '@/lib/animations'
import { useEditMode, SectionEditLink } from '@/components/EditModeBar'
import EarthGlobe from '@/components/EarthGlobe'
import { RefreshCw } from 'lucide-react'
import { seededShuffle } from '@/lib/seededShuffle'
import { TESTIMONIALS, type TestimonialEntry } from '@/data/testimonials'
import type { PublicJob, AgeGroup } from '@/types'
import { API_URL } from '@/lib/api'
import { sanitizeReviewText } from '@/lib/sanitizeText'

// ── Fallback testimonials (subset of static pool) ──
const FALLBACK_TESTIMONIALS: TestimonialEntry[] = TESTIMONIALS.slice(0, 4)

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

// ── Monthly seed: changes on the 1st of each month ──
function getMonthSeed(): number {
  const now = new Date()
  return now.getFullYear() * 12 + now.getMonth()
}

// ── Get override seed from localStorage (SSR-safe) ──
function getOverrideSeed(storageKey: string): number {
  const base = getMonthSeed()
  if (typeof window === 'undefined') return base
  const override = localStorage.getItem(storageKey)
  return override ? parseInt(override, 10) : base
}


// ── Fallback featured jobs (when API fails) ──
const FALLBACK_JOBS: PublicJob[] = [
  { job_id: 'BR-2401', location: 'Seoul', teaching_age: ['elementary'] as AgeGroup[], working_hours: 'Mon-Fri 9-6', monthly_salary: '2.5M KRW', housing: 'Housing + Severance', is_hot: false, starting_date: 'ASAP' } as PublicJob,
  { job_id: 'BR-2402', location: 'Busan', teaching_age: ['middle'] as AgeGroup[], working_hours: 'Mon-Fri 10-7', monthly_salary: '2.8M KRW', housing: 'Housing + Flight', is_hot: true, starting_date: 'ASAP' } as PublicJob,
  { job_id: 'BR-2403', location: 'Incheon', teaching_age: ['pre_k', 'kindergarten'] as AgeGroup[], working_hours: 'Mon-Fri 9-5', monthly_salary: '2.3M KRW', housing: 'Housing + Insurance', is_hot: false, starting_date: 'ASAP' } as PublicJob,
  { job_id: 'BR-2404', location: 'Daegu', teaching_age: ['elementary', 'middle'] as AgeGroup[], working_hours: 'Mon-Fri 10-6', monthly_salary: '2.6M KRW', housing: 'Housing + Bonus', is_hot: false, starting_date: 'ASAP' } as PublicJob,
]

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
  country: string
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
  const [testimonials, setTestimonials] = useState<Testimonial[]>(
    FALLBACK_TESTIMONIALS.map(t => ({ text: t.text, stars: t.stars, name: t.name, country: t.country }))
  )
  const [jobs, setJobs] = useState<PublicJob[]>(FALLBACK_JOBS)
  const [showBridge, setShowBridge] = useState(false)
  const [showTagline, setShowTagline] = useState(false)
  const [academyNames, setAcademyNames] = useState<string[]>(FALLBACK_ACADEMIES)
  const [schoolNames, setSchoolNames] = useState<string[]>(FALLBACK_SCHOOLS)
  const editMode = useEditMode()

  // Dynamic site settings
  const [siteName, setSiteName] = useState('BRIDGE')
  const [heroTagline, setHeroTagline] = useState('A career that changes your life')

  // Raw data ref for job re-shuffling
  const rawFetchedJobs = useRef<PublicJob[]>([])

  // Animation keys for AnimatePresence
  const [testimonialKey, setTestimonialKey] = useState(0)
  const [jobKey, setJobKey] = useState(0)

  // Toast
  const [toast, setToast] = useState('')

  // ── Trigger bridge animation (sync with BRIDGE text) ──
  useEffect(() => {
    const t1 = setTimeout(() => setShowBridge(true), 50)
    const t2 = setTimeout(() => setShowTagline(true), 50)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [])

  // ── Fetch site settings for dynamic hero ──
  useEffect(() => {
    fetch('/api/settings')
      .then(r => r.json())
      .then(d => {
        if (!d?.data?.settings) return
        const s = d.data.settings as Record<string, string>
        if (s.site_name) setSiteName(s.site_name)
        if (s.hero_tagline) setHeroTagline(s.hero_tagline)
      })
      .catch(() => { /* keep defaults */ })
  }, [])

  // ── Hero parallax ──
  const { scrollYProgress: heroProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  })
  const heroOpacity = useTransform(heroProgress, [0, 0.6], [1, 0])
  const heroScale = useTransform(heroProgress, [0, 0.6], [1, 0.95])
  const arrowOpacity = useTransform(heroProgress, [0, 0.15], [1, 0])

  // ── Testimonials from DB API (random 6), fallback to static pool ──
  const fetchTestimonials = useCallback(() => {
    fetch('/api/testimonials')
      .then(r => r.json())
      .then(d => {
        if (d?.success && d.data?.testimonials?.length > 0) {
          setTestimonials(d.data.testimonials.map((t: { review_text: string; rating: number; name: string; country: string }) => ({
            text: t.review_text,
            stars: t.rating,
            name: t.name,
            country: t.country,
          })))
        } else {
          loadFallback()
        }
      })
      .catch(() => { loadFallback() })
  }, [])

  const loadFallback = useCallback(() => {
    const seed = getOverrideSeed('bridge_featured_testimonials_override')
    const shuffled = seededShuffle(TESTIMONIALS, seed).slice(0, 6)
    setTestimonials(shuffled.map(t => ({
      text: t.text,
      stars: t.stars,
      name: t.name,
      country: t.country,
    })))
  }, [])

  useEffect(() => {
    fetchTestimonials()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Fetch featured jobs (monthly-seeded shuffle) ──
  useEffect(() => {
    fetch(`/api/jobs?limit=20`)
      .then(r => r.json())
      .then(d => {
        const all: PublicJob[] = d?.data ?? []
        if (all.length > 0) {
          rawFetchedJobs.current = all
          const seed = getOverrideSeed('bridge_featured_jobs_override')
          const shuffled = seededShuffle(all, seed)
          setJobs(shuffled.slice(0, 4))
        }
      })
      .catch(() => { setJobs(FALLBACK_JOBS) })
  }, [])

  // ── Fetch partners from API ──
  useEffect(() => {
    fetch('/api/partners')
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
      .catch(err => {
        console.error('[Partners API Error]', err)
        // Fallback 유지 — 데이터 로드 실패 시 기본값 사용
      })
  }, [])

  // ── Refresh handlers ──
  const showToast = useCallback((msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 2000)
  }, [])

  const handleRefreshTestimonials = useCallback(() => {
    fetch(`${API_URL || ''}/api/testimonials?limit=6&random=1`)
      .then(r => r.json())
      .then(d => {
        if (d?.success && d.data?.testimonials?.length > 0) {
          setTestimonials(d.data.testimonials.map((t: { review_text: string; rating: number; name: string; country: string }) => ({
            text: t.review_text,
            stars: t.rating,
            name: t.name,
            country: t.country,
          })))
        } else {
          const newSeed = Math.floor(Math.random() * 2147483647)
          localStorage.setItem('bridge_featured_testimonials_override', String(newSeed))
          const shuffled = seededShuffle(TESTIMONIALS, newSeed).slice(0, 6)
          setTestimonials(shuffled.map(t => ({ text: t.text, stars: t.stars, name: t.name, country: t.country })))
        }
      })
      .catch(() => {
        const newSeed = Math.floor(Math.random() * 2147483647)
        localStorage.setItem('bridge_featured_testimonials_override', String(newSeed))
        const shuffled = seededShuffle(TESTIMONIALS, newSeed).slice(0, 6)
        setTestimonials(shuffled.map(t => ({ text: t.text, stars: t.stars, name: t.name, country: t.country })))
      })
    setTestimonialKey(prev => prev + 1)
    showToast('새로운 항목으로 배치되었습니다')
  }, [showToast])

  const handleRefreshJobs = useCallback(() => {
    if (rawFetchedJobs.current.length === 0) return
    const newSeed = Math.floor(Math.random() * 2147483647)
    localStorage.setItem('bridge_featured_jobs_override', String(newSeed))
    const shuffled = seededShuffle(rawFetchedJobs.current, newSeed)
    setJobs(shuffled.slice(0, 4))
    setJobKey(prev => prev + 1)
    showToast('새로운 항목으로 배치되었습니다')
  }, [showToast])

  return (
    <div className="bg-black">

      {/* ═══════════════════════════════════════════════════════════════════
          1. HERO — "BRIDGE" + tagline + background animations
          ═══════════════════════════════════════════════════════════════════ */}
      <section ref={heroRef} className="relative h-[85vh] min-h-[500px] flex items-center justify-center overflow-hidden">
        {/* Edit mode: Hero settings */}
        {editMode && (
          <div className="absolute top-3 right-4 z-50">
            <SectionEditLink href="/admin/settings" label="히어로 설정" dark />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-b from-black via-[#0a0a0a] to-black" />

        {/* ── Earth — 3D 구체 상반구 (z:0, 다리 아래) ── */}
        <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 0 }}>
          <EarthGlobe />
          {/* 상단 블랙 유지 + 하단 자연스럽게 블렌딩 */}
          <div style={{
            position: 'absolute', inset: 0,
            background: 'linear-gradient(to bottom, #000 0%, #000 10%, rgba(0,0,0,0.25) 32%, rgba(0,0,0,0) 48%, rgba(0,0,0,0.2) 65%, rgba(0,0,0,0.65) 82%, #000 100%)',
          }} />
        </div>

        {/* ── Twinkling stars — 다리 위쪽 근처, 겹치지 않게 ── */}
        {[
          { top: '15%', left: '5%',  size: 2.5, delay: 0,   dur: 1.8 },
          { top: '22%', left: '85%', size: 3.5, delay: 0.6, dur: 1.5 },
          { top: '10%', left: '50%', size: 2,   delay: 0.3, dur: 2.0 },
          { top: '28%', left: '30%', size: 3,   delay: 1.0, dur: 1.6 },
          { top: '18%', left: '70%', size: 2.8, delay: 0.4, dur: 1.9 },
          { top: '30%', left: '10%', size: 2.2, delay: 0.8, dur: 1.7 },
          { top: '12%', left: '92%', size: 3.2, delay: 1.2, dur: 1.4 },
        ].map((star, i) => (
          <div
            key={`star-${i}`}
            className="hero-star"
            style={{
              position: 'absolute',
              top: star.top,
              left: star.left,
              width: star.size,
              height: star.size,
              borderRadius: '50%',
              background: 'white',
              zIndex: 1,
              animationDelay: `${star.delay}s`,
              animationDuration: `${star.dur}s`,
            }}
          />
        ))}

        {/* ── Suspension bridge — light sweep reveal ── */}
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
              <filter id="sweepGlow">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              {/* Taper mask — thick center, thin edges */}
              <mask id="taperMask">
                <linearGradient id="taperGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0" stopColor="white" stopOpacity="0" />
                  <stop offset="0.12" stopColor="white" stopOpacity="0.25" />
                  <stop offset="0.5" stopColor="white" stopOpacity="1" />
                  <stop offset="0.88" stopColor="white" stopOpacity="0.25" />
                  <stop offset="1" stopColor="white" stopOpacity="0" />
                </linearGradient>
                <rect x="0" y="0" width="1400" height="800" fill="url(#taperGrad)" />
              </mask>
              {/* Post-draw subtle light sweep — infinite (7s cycle, starts 3s) */}
              <linearGradient id="postSweep" gradientUnits="userSpaceOnUse" x1="-700" y1="400" x2="0" y2="400">
                <stop offset="0" stopColor="white" stopOpacity="0" />
                <stop offset="0.35" stopColor="white" stopOpacity="0" />
                <stop offset="0.5" stopColor="white" stopOpacity="0.35" />
                <stop offset="0.65" stopColor="white" stopOpacity="0" />
                <stop offset="1" stopColor="white" stopOpacity="0" />
                <animate attributeName="x1" values="-700;1400" dur="3.5s" repeatCount="indefinite" begin="3s" />
                <animate attributeName="x2" values="0;2100" dur="3.5s" repeatCount="indefinite" begin="3s" />
              </linearGradient>
            </defs>

            {/* ── Arc group — breathing glow (arc only) ── */}
            <g className="bridge-arc-group">
              <path d="M 0 520 Q 700 180, 1400 520"
                className="bridge-arc"
                stroke="white" strokeWidth={0.8} strokeLinecap="round"
                filter="url(#cableGlow)"
              />
              <path d="M 0 520 Q 700 180, 1400 520"
                className="bridge-arc"
                stroke="white" strokeWidth={2.5} strokeLinecap="round"
                mask="url(#taperMask)" filter="url(#cableGlow)"
              />
            </g>

            {/* ── Glow sweep — subtle bright spot traveling L→R during draw ── */}
            <path d="M 0 520 Q 700 180, 1400 520"
              className="bridge-sweep"
              stroke="rgba(255,255,255,0.5)" strokeWidth={3} strokeLinecap="round"
              filter="url(#sweepGlow)"
            />

            {/* ── Towers — both simultaneous, static after ── */}
            <line x1={420} y1={520} x2={420} y2={280}
              className="bridge-tower" stroke="white" strokeWidth={2} strokeLinecap="round" />
            <line x1={980} y1={520} x2={980} y2={280}
              className="bridge-tower" stroke="white" strokeWidth={2} strokeLinecap="round" />

            {/* ── Stay cables — draw outward, static after ── */}
            <line x1={420} y1={280} x2={280} y2={410}
              className="bridge-stay bridge-stay-l1" stroke="white" strokeWidth={0.8} strokeLinecap="round"
              style={{ '--len': '191' } as React.CSSProperties} />
            <line x1={420} y1={280} x2={200} y2={465}
              className="bridge-stay bridge-stay-l2" stroke="white" strokeWidth={0.8} strokeLinecap="round"
              style={{ '--len': '287' } as React.CSSProperties} />
            <line x1={980} y1={280} x2={1120} y2={410}
              className="bridge-stay bridge-stay-r1" stroke="white" strokeWidth={0.8} strokeLinecap="round"
              style={{ '--len': '191' } as React.CSSProperties} />
            <line x1={980} y1={280} x2={1200} y2={465}
              className="bridge-stay bridge-stay-r2" stroke="white" strokeWidth={0.8} strokeLinecap="round"
              style={{ '--len': '287' } as React.CSSProperties} />

            {/* ── Post-draw infinite light sweep ── */}
            <path d="M 0 520 Q 700 180, 1400 520"
              stroke="url(#postSweep)" strokeWidth={4} strokeLinecap="round"
              opacity={0.5} filter="url(#cableGlow)"
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
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1.5, ease: 'easeOut' }}
          >
            {siteName}
          </motion.h1>

          <p className="text-xl sm:text-2xl md:text-3xl font-light tracking-tight">
            {heroTagline.split('').map((char, i) => (
              <span
                key={i}
                className={showTagline ? 'letter-star' : ''}
                style={{
                  opacity: showTagline ? undefined : 0,
                  animationDelay: showTagline ? `${i * 0.025}s` : undefined,
                  display: 'inline-block',
                  minWidth: char === ' ' ? '0.3em' : undefined,
                }}
              >
                {char}
              </span>
            ))}
          </p>
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
        <section className="bg-black py-24 sm:py-28 border-t border-white/[0.06] relative">
          {editMode && (
            <div className="absolute top-3 right-4 z-20">
              <SectionEditLink href="/admin/posts?board=testimonials" label="후기 관리" dark />
            </div>
          )}
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
              {editMode && (
                <button
                  type="button"
                  onClick={handleRefreshTestimonials}
                  className="mt-4 inline-flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white border border-zinc-700 rounded-lg px-3 py-1.5 transition-colors"
                >
                  <RefreshCw size={14} /> 새로 배치하기
                </button>
              )}
            </motion.div>

            <AnimatePresence mode="wait">
              <motion.div
                key={`testimonials-${testimonialKey}`}
                className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
              >
                {testimonials.slice(0, 6).map((t, i) => (
                  <motion.div
                    key={i}
                    className="testimonial-glass rounded-2xl p-6 flex flex-col justify-between min-h-[260px]
                               hover:bg-white/[0.08] hover:-translate-y-1 transition-all duration-300"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.4, delay: i * 0.08 }}
                  >
                    <div>
                      <span className="text-[#2997ff]/40 text-4xl font-serif leading-none select-none block mb-3">&ldquo;</span>
                      <p className="text-[#d1d1d6] text-sm leading-relaxed line-clamp-5">
                        {sanitizeReviewText(t.text)}
                      </p>
                    </div>
                    <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between">
                      <div className="flex gap-0.5">
                        {Array.from({ length: 5 }).map((_, s) => (
                          <StarIcon key={s} filled={s < t.stars} />
                        ))}
                      </div>
                      <p className="text-[#86868b] text-xs font-semibold tracking-wide">
                        {t.name} · {t.country}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            </AnimatePresence>

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
        <section className="bg-[#0a0a0a] py-24 sm:py-28 border-t border-white/[0.06] relative">
          {editMode && (
            <div className="absolute top-3 right-4 z-20">
              <SectionEditLink href="/admin/jobs" label="채용공고 관리" dark />
            </div>
          )}
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
              {editMode && (
                <button
                  type="button"
                  onClick={handleRefreshJobs}
                  className="mt-4 inline-flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white border border-zinc-700 rounded-lg px-3 py-1.5 transition-colors"
                >
                  <RefreshCw size={14} /> 새로 배치하기
                </button>
              )}
            </motion.div>

            <AnimatePresence mode="wait">
              <motion.div
                key={`jobs-${jobKey}`}
                className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
              >
                {jobs.slice(0, 4).map((job, i) => (
                  <motion.div
                    key={job.job_id}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.4, delay: i * 0.1 }}
                  >
                    <Link
                      href="/jobs"
                      className="group block shimmer-card bg-[#141414] border border-white/[0.06] rounded-xl p-6
                                 hover:bg-[#1a1a1a] transition-all duration-300 hover:-translate-y-1 hover:scale-[1.02]
                                 hover:shadow-[0_8px_32px_rgba(41,151,255,0.12)]"
                    >
                      <div className="mb-5">
                        <span className="inline-block text-[13px] font-bold px-3 py-1 rounded-full bg-white/[0.08] text-white mb-2">
                          {job.location ?? 'Korea'}
                        </span>
                        {job.is_hot && (
                          <span className="ml-2 text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 uppercase align-middle">
                            Hot
                          </span>
                        )}
                        <p className="text-white text-[14px] font-bold tracking-wide mt-1">
                          {job.job_id}
                        </p>
                      </div>

                      <div className="space-y-2 text-[13px]">
                        <div className="flex justify-between gap-2">
                          <span className="text-[#636366] font-medium shrink-0">Student Age</span>
                          <span className="text-[#a1a1a6] text-right">
                            {(job.teaching_age && job.teaching_age.length > 0) ? formatTeachingAge(job.teaching_age) : (job.teaching_age_raw || '—')}
                          </span>
                        </div>
                        <div className="flex justify-between gap-2">
                          <span className="text-[#636366] font-medium shrink-0">Hours</span>
                          <span className="text-[#a1a1a6] text-right">{job.working_hours || '—'}</span>
                        </div>
                        <div className="flex justify-between gap-2">
                          <span className="text-[#636366] font-medium shrink-0">Salary</span>
                          <span className="text-[#a1a1a6] text-right truncate">{job.monthly_salary || '—'}</span>
                        </div>
                        <div className="flex justify-between gap-2">
                          <span className="text-[#636366] font-medium shrink-0">Housing</span>
                          <span className="text-[#a1a1a6] text-right truncate max-w-[140px]">{job.housing || '—'}</span>
                        </div>
                        <div className="flex justify-between gap-2">
                          <span className="text-[#636366] font-medium shrink-0">Benefits</span>
                          <span className="text-[#a1a1a6] text-right truncate max-w-[140px]">
                            {(job.employee_benefits && job.employee_benefits.length > 0) ? job.employee_benefits.slice(0, 3).join(' · ') : '—'}
                          </span>
                        </div>
                      </div>

                      <div className="mt-5 pt-4 border-t border-white/[0.06] text-right">
                        <span className="inline-block text-xs font-semibold text-[#2997ff] transition-transform duration-300 group-hover:translate-x-1">
                          View details &rarr;
                        </span>
                      </div>
                    </Link>
                  </motion.div>
                ))}
              </motion.div>
            </AnimatePresence>

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
        <div className="mb-6">
          <p className="text-[11px] font-semibold text-white/60 uppercase tracking-[0.2em] text-center mb-4">
            Schools &amp; Institutions
          </p>
          <div className="relative overflow-hidden" aria-hidden="true">
            {/* Edge fade */}
            <div className="pointer-events-none absolute inset-y-0 left-0 w-16 z-10" style={{ background: 'linear-gradient(to right, #111111, transparent)' }} />
            <div className="pointer-events-none absolute inset-y-0 right-0 w-16 z-10" style={{ background: 'linear-gradient(to left, #111111, transparent)' }} />
            <motion.div
              className="flex items-center"
              style={{ width: 'max-content' }}
              animate={{ x: ['0%', '-50%'] }}
              transition={{ x: { duration: 45, ease: 'linear', repeat: Infinity, repeatType: 'loop' } }}
            >
              {[...schoolNames, ...schoolNames].map((name, i) => (
                <span
                  key={`s-${i}`}
                  className="shrink-0 px-5 sm:px-7 text-[0.9rem] font-semibold select-none whitespace-nowrap text-white tracking-[0.04em]"
                >
                  {name}
                  <span className="ml-5 sm:ml-7 text-white/25 text-xs">·</span>
                </span>
              ))}
            </motion.div>
          </div>
        </div>

        {/* Row 2 — Our Partner */}
        <div>
          <p className="text-[11px] font-semibold text-white/60 uppercase tracking-[0.2em] text-center mb-4">
            Our Partner
          </p>
          <div className="relative overflow-hidden" aria-hidden="true">
            {/* Edge fade */}
            <div className="pointer-events-none absolute inset-y-0 left-0 w-16 z-10" style={{ background: 'linear-gradient(to right, #111111, transparent)' }} />
            <div className="pointer-events-none absolute inset-y-0 right-0 w-16 z-10" style={{ background: 'linear-gradient(to left, #111111, transparent)' }} />
            <motion.div
              className="flex items-center"
              style={{ width: 'max-content' }}
              animate={{ x: ['0%', '-50%'] }}
              transition={{ x: { duration: 24, ease: 'linear', repeat: Infinity, repeatType: 'loop' } }}
            >
              {[...academyNames, ...academyNames].map((name, i) => (
                <span
                  key={`a-${i}`}
                  className="shrink-0 px-5 sm:px-7 text-[0.9rem] font-semibold select-none whitespace-nowrap text-white tracking-[0.04em]"
                >
                  {name}
                  <span className="ml-5 sm:ml-7 text-white/25 text-xs">·</span>
                </span>
              ))}
            </motion.div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          5. CTA — Your Next Chapter (Apple + Kakao MZ style)
          ═══════════════════════════════════════════════════════════════════ */}
      <section className="relative py-24 sm:py-32 border-t border-white/[0.06] overflow-hidden bg-black">
        {editMode && (
          <div className="absolute top-3 right-4 z-20">
            <SectionEditLink href="/admin/settings" label="CTA 설정" dark />
          </div>
        )}
        <div className="relative z-10 max-w-[900px] mx-auto px-5 sm:px-8">
          {/* Headline — Apple bold */}
          <motion.div
            className="text-center mb-16"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <h2 className="text-5xl sm:text-6xl md:text-[72px] font-bold text-white tracking-tight leading-[1.05]">
              Your Next Chapter
            </h2>
            <p className="text-white/40 text-lg sm:text-xl mt-5 font-medium">
              Choose your path. We&apos;ll handle the rest.
            </p>
          </motion.div>

          {/* Two cards — equal height */}
          <div className="grid sm:grid-cols-2 gap-5 sm:gap-6">
            {/* Teacher Card */}
            <motion.div
              className="flex"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              <Link
                href="/apply"
                className="cta-card group relative flex flex-col rounded-3xl p-8 sm:p-10 overflow-hidden transition-all duration-500 w-full
                           hover:scale-[1.02] hover:shadow-[0_20px_60px_rgba(59,130,246,0.25)] active:scale-[0.98]"
                style={{ background: 'linear-gradient(135deg, #1e3a5f 0%, #1a1a2e 100%)' }}
              >
                {/* Hover glow overlay */}
                <div className="absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                  style={{ background: 'linear-gradient(135deg, rgba(59,130,246,0.2), transparent 60%)', pointerEvents: 'none' }} />
                {/* Emoji — floats on hover */}
                <div className="cta-emoji text-[48px] mb-5 select-none leading-none w-fit transition-[filter] duration-500"
                  style={{ filter: 'drop-shadow(0 2px 6px rgba(59,130,246,0.15))' }}>
                  🎓
                </div>
                <h3 className="text-2xl sm:text-3xl font-bold text-white mb-3 tracking-tight">
                  I&apos;m a Teacher
                </h3>
                <p className="text-white/50 text-[15px] leading-relaxed mb-8 flex-1">
                  Find your dream ESL position in Korea. We connect you with top schools and academies.
                </p>
                <span className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-[14px] font-semibold
                               bg-[#3b82f6] text-white shadow-none
                               transition-all duration-300 group-hover:shadow-[0_6px_28px_rgba(59,130,246,0.5)] group-hover:gap-3 w-fit">
                  Apply Now
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </span>
              </Link>
            </motion.div>

            {/* Employer Card */}
            <motion.div
              className="flex"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: 0.25 }}
            >
              <Link
                href="/inquiry"
                className="cta-card group relative flex flex-col rounded-3xl p-8 sm:p-10 overflow-hidden transition-all duration-500 w-full
                           hover:scale-[1.02] hover:shadow-[0_20px_60px_rgba(245,158,11,0.25)] active:scale-[0.98]"
                style={{ background: 'linear-gradient(135deg, #422006 0%, #1a1a2e 100%)' }}
              >
                <div className="absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                  style={{ background: 'linear-gradient(135deg, rgba(245,158,11,0.2), transparent 60%)', pointerEvents: 'none' }} />
                {/* Emoji — floats on hover */}
                <div className="cta-emoji text-[48px] mb-5 select-none leading-none w-fit transition-[filter] duration-500"
                  style={{ filter: 'drop-shadow(0 2px 6px rgba(245,158,11,0.15))' }}>
                  🏫
                </div>
                <h3 className="text-2xl sm:text-3xl font-bold text-white mb-2 tracking-tight">
                  I&apos;m Hiring
                </h3>
                <p className="text-[15px] text-white/70 font-semibold mb-3 tracking-wide">
                  원어민 구인신청
                </p>
                <p className="text-white/50 text-[15px] leading-relaxed mb-8 flex-1">
                  Find qualified native English teachers. Fast, reliable, zero hassle recruitment.
                </p>
                <span className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-[14px] font-semibold
                               bg-[#f59e0b] text-black shadow-none
                               transition-all duration-300 group-hover:shadow-[0_6px_28px_rgba(245,158,11,0.5)] group-hover:gap-3 w-fit">
                  Request Teachers
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </span>
              </Link>
            </motion.div>
          </div>

          {/* Hashtag row — Kakao MZ style */}
          <motion.div
            className="mt-14 text-center"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3">
              {['#TeachInKorea', '#ESLJobs', '#원어민채용', '#FindYourMatch', '#BRIDGERecruitment'].map((tag) => (
                <span key={tag} className="px-4 py-1.5 rounded-full text-[13px] font-semibold text-white/40 border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.06] hover:text-white/60 transition-all duration-300 cursor-default">
                  {tag}
                </span>
              ))}
            </div>
            <p className="mt-8 text-white/20 text-sm tracking-wide">
              bridgejobkr@gmail.com
            </p>
          </motion.div>
        </div>
      </section>

      {/* Toast notification */}
      <AnimatePresence>
        {toast && (
          <motion.div
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-5 py-3 bg-zinc-800 text-white text-sm rounded-lg shadow-xl border border-zinc-700"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.2 }}
          >
            {toast}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
