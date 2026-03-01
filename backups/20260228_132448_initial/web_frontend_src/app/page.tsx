'use client'

/**
 * Homepage — Apple Dark Immersive Experience
 * Flow: BRIDGE hero → scroll photos → stats → CTA → floating jobs → testimonials → partner marquee
 */

import { useEffect, useRef, useState, useMemo } from 'react'
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
  slideInLeft,
  slideInRight,
  defaultViewport,
} from '@/lib/animations'

// ── Daily seed: changes every day ──
function getDaySeed() {
  const now = Date.now()
  return Math.floor(now / (24 * 60 * 60 * 1000))
}
function seededShuffle<T>(arr: T[], seed: number): T[] {
  const copy = [...arr]
  let s = seed
  for (let i = copy.length - 1; i > 0; i--) {
    s = (s * 16807 + 0) % 2147483647
    const j = s % (i + 1)
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

// ── Teacher photos (scroll showcase) ──
const SHOWCASE_PHOTOS = [
  { src: 'https://images.unsplash.com/photo-1529390079861-591de354faf5?w=1400&h=900&fit=crop', caption: 'Teaching moments that matter' },
  { src: 'https://images.unsplash.com/photo-1523050854058-8df90110c7f1?w=1400&h=900&fit=crop', caption: 'Classrooms across Korea' },
  { src: 'https://images.unsplash.com/photo-1580582932707-520aed937b7b?w=1400&h=900&fit=crop', caption: 'Where learning comes alive' },
  { src: 'https://images.unsplash.com/photo-1509062522246-3755977927d7?w=1400&h=900&fit=crop', caption: 'Building futures together' },
  { src: 'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=1400&h=900&fit=crop', caption: 'Your journey starts here' },
]

// ── Stats ──
const COUNTERS = [
  { label: 'Teachers Placed', target: 5019, suffix: '+' },
  { label: 'Partner Schools', target: 2092, suffix: '+' },
  { label: 'Countries', target: 7, suffix: '' },
  { label: 'Years Experience', target: 10, suffix: '+' },
]

// ── Sample job pool (daily rotation picks 4) ──
const JOB_POOL = [
  { id: 'J-2401', location: 'Seoul, Gangnam', type: 'Kindergarten', salary: '2.5M KRW', tag: 'HOT' },
  { id: 'J-2402', location: 'Busan, Haeundae', type: 'Elementary', salary: '2.3M KRW', tag: 'NEW' },
  { id: 'J-2403', location: 'Incheon, Songdo', type: 'Academy', salary: '2.7M KRW', tag: 'HOT' },
  { id: 'J-2404', location: 'Seoul, Mapo', type: 'International', salary: '3.0M KRW', tag: '' },
  { id: 'J-2405', location: 'Gyeonggi, Bundang', type: 'Kindergarten', salary: '2.6M KRW', tag: 'NEW' },
  { id: 'J-2406', location: 'Daegu, Suseong', type: 'Elementary', salary: '2.4M KRW', tag: '' },
  { id: 'J-2407', location: 'Seoul, Songpa', type: 'Academy', salary: '2.8M KRW', tag: 'HOT' },
  { id: 'J-2408', location: 'Jeju City', type: 'Public School', salary: '2.2M KRW', tag: 'NEW' },
]

// ── Testimonial pool (daily rotation picks 5) ──
const TESTIMONIAL_POOL = [
  { name: 'Sarah J.', from: 'USA', city: 'Seoul', quote: 'BRIDGE made my transition to Korea seamless. From visa processing to finding the perfect school, they were there every step of the way.' },
  { name: 'James L.', from: 'UK', city: 'Busan', quote: 'I was nervous about teaching abroad for the first time. BRIDGE matched me with an amazing school and the support was incredible.' },
  { name: 'Emily R.', from: 'Canada', city: 'Incheon', quote: 'The best decision I ever made. BRIDGE found me a position that perfectly matched my experience and preferences.' },
  { name: 'Michael T.', from: 'Australia', city: 'Daegu', quote: 'Professional, responsive, and genuinely caring. BRIDGE treats you like a person, not just another placement.' },
  { name: 'Anna K.', from: 'South Africa', city: 'Gyeonggi', quote: 'From the first email to my arrival in Korea, everything was handled with care. I couldn\'t have done it without BRIDGE.' },
  { name: 'David M.', from: 'Ireland', city: 'Seoul', quote: 'Three years in Korea now and I still recommend BRIDGE to every teacher I meet. They set the standard.' },
  { name: 'Rachel P.', from: 'New Zealand', city: 'Jeju', quote: 'BRIDGE found me a dream position in Jeju. The island life and teaching — it doesn\'t get better than this.' },
  { name: 'Tom H.', from: 'USA', city: 'Bundang', quote: 'Transparent, honest, and fast. BRIDGE had me placed within two weeks. The school has been fantastic.' },
]

// ── Partner marquee — school types + Korean franchise names ──
const PARTNER_ITEMS = [
  // School types
  'English Centres',
  'International Schools',
  'Private Schools',
  'English Villages',
  'Government Education Centres',
  'Academies',
  'Kindergartens',
  'After-School Programs',
  'Public Schools',
  // Korean major franchises
  'YBM ECC',
  'Pagoda',
  'Chungdahm Learning',
  'Avalon English',
  'CDI / April',
  'SLP',
  'JLS Language',
  'Maple Bear',
  'POLY',
  'Wonderland',
  'GnB English',
  'Haba Kids',
  'LCI Kids Club',
  'YC College',
  'Jung Chul',
  'Sisa English',
  'English Channel',
  'Langcon',
  'ECC Junior',
  'Talktown',
  'SDA English',
  'Reading Town',
]
// First 9 are categories (styled differently)
const CATEGORY_COUNT = 9

// ── Animated counter hook ──
function useAnimatedCounter(target: number, duration: number, start: boolean) {
  const [value, setValue] = useState(0)
  useEffect(() => {
    if (!start) return
    let t0: number | null = null
    let frame: number
    const step = (ts: number) => {
      if (!t0) t0 = ts
      const p = Math.min((ts - t0) / duration, 1)
      setValue(Math.floor((1 - Math.pow(1 - p, 3)) * target))
      if (p < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [target, duration, start])
  return value
}

export default function HomePage() {
  const heroRef = useRef<HTMLElement>(null)
  const photoSectionRef = useRef<HTMLDivElement>(null)
  const countersRef = useRef<HTMLDivElement>(null)
  const [countersVisible, setCountersVisible] = useState(false)

  // ── Daily-rotated data ──
  const seed = getDaySeed()
  const dailyJobs = useMemo(() => seededShuffle(JOB_POOL, seed).slice(0, 4), [seed])
  const dailyTestimonials = useMemo(() => seededShuffle(TESTIMONIAL_POOL, seed + 1).slice(0, 5), [seed])

  // ── Hero parallax ──
  const { scrollYProgress: heroProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  })
  const heroOpacity = useTransform(heroProgress, [0, 0.6], [1, 0])
  const heroScale = useTransform(heroProgress, [0, 0.6], [1, 0.95])
  const arrowOpacity = useTransform(heroProgress, [0, 0.1], [1, 0])

  // ── Photo section scroll-linked index ──
  const { scrollYProgress: photoProgress } = useScroll({
    target: photoSectionRef,
    offset: ['start start', 'end end'],
  })
  const [activePhoto, setActivePhoto] = useState(0)
  useEffect(() => {
    const unsubscribe = photoProgress.on('change', (v) => {
      const idx = Math.min(
        Math.floor(v * SHOWCASE_PHOTOS.length),
        SHOWCASE_PHOTOS.length - 1
      )
      setActivePhoto(idx)
    })
    return unsubscribe
  }, [photoProgress])

  // ── Counter observer ──
  useEffect(() => {
    const el = countersRef.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setCountersVisible(true) },
      { threshold: 0.3 }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const cv = [
    useAnimatedCounter(COUNTERS[0].target, 2000, countersVisible),
    useAnimatedCounter(COUNTERS[1].target, 2000, countersVisible),
    useAnimatedCounter(COUNTERS[2].target, 1500, countersVisible),
    useAnimatedCounter(COUNTERS[3].target, 1500, countersVisible),
  ]

  return (
    <div className="bg-black">

      {/* ═══════════════════════════════════════════════════════════════════
          1. HERO — "BRIDGE" + tagline + blinking scroll arrow
          ═══════════════════════════════════════════════════════════════════ */}
      <section ref={heroRef} className="relative h-screen min-h-[600px] flex items-center justify-center overflow-hidden">
        {/* Subtle background gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-black via-[#0a0a0a] to-black" />

        <motion.div
          className="relative z-10 text-center px-4"
          style={{ opacity: heroOpacity, scale: heroScale }}
        >
          <motion.h1
            className="text-[clamp(80px,15vw,200px)] font-black text-white leading-none tracking-tighter mb-6"
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

        {/* Blinking scroll indicator */}
        <motion.div
          className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
          style={{ opacity: arrowOpacity }}
        >
          <span className="text-[11px] uppercase tracking-[0.2em] text-[#48484a] font-medium">Scroll</span>
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
          >
            <svg className="w-5 h-5 text-[#48484a]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </motion.div>
        </motion.div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          2. PHOTO SHOWCASE — Scroll-linked image transitions
          ═══════════════════════════════════════════════════════════════════ */}
      <div ref={photoSectionRef} style={{ height: `${SHOWCASE_PHOTOS.length * 100}vh` }}>
        <div className="sticky top-0 h-screen flex items-center justify-center overflow-hidden">
          {/* Photo */}
          <AnimatePresence mode="wait">
            <motion.div
              key={activePhoto}
              className="absolute inset-0"
              initial={{ opacity: 0, scale: 1.05 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={{ duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }}
            >
              <img
                src={SHOWCASE_PHOTOS[activePhoto].src}
                alt=""
                className="w-full h-full object-cover"
              />
              {/* Dark overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-black/50" />
            </motion.div>
          </AnimatePresence>

          {/* Caption */}
          <AnimatePresence mode="wait">
            <motion.div
              key={`caption-${activePhoto}`}
              className="relative z-10 text-center px-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
            >
              <p className="text-3xl sm:text-4xl md:text-5xl font-bold text-white tracking-tight">
                {SHOWCASE_PHOTOS[activePhoto].caption}
              </p>
            </motion.div>
          </AnimatePresence>

          {/* Progress dots */}
          <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex gap-2 z-10">
            {SHOWCASE_PHOTOS.map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full transition-all duration-300 ${
                  i === activePhoto ? 'bg-white w-6' : 'bg-white/30'
                }`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          3. STATS COUNTERS
          ═══════════════════════════════════════════════════════════════════ */}
      <section ref={countersRef} className="bg-black py-28 border-t border-white/[0.06]">
        <div className="max-w-[980px] mx-auto px-4 sm:px-6">
          <motion.div
            className="text-center mb-16"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <h2 className="text-4xl sm:text-5xl font-bold text-white tracking-tight">
              Numbers that speak.
            </h2>
          </motion.div>

          <motion.div
            className="grid grid-cols-2 md:grid-cols-4 gap-10"
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            {COUNTERS.map((c, i) => (
              <motion.div key={c.label} className="text-center" variants={fadeInUp}>
                <div className="text-5xl sm:text-6xl font-black text-white tabular-nums tracking-tight">
                  {cv[i].toLocaleString('en-US')}{c.suffix}
                </div>
                <div className="text-sm text-[#86868b] mt-3 font-medium">{c.label}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          4. CTA — Get started today (right after stats)
          ═══════════════════════════════════════════════════════════════════ */}
      <section className="bg-[#111111] py-28 border-t border-white/[0.06]">
        <div className="max-w-[800px] mx-auto px-4 sm:px-6 text-center">
          <motion.div
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <h2 className="text-4xl sm:text-5xl md:text-6xl font-bold text-white tracking-tight mb-6">
              Get started today.
            </h2>
            <p className="text-[#86868b] text-lg mb-12 max-w-md mx-auto">
              Whether you&apos;re looking for your next teaching position
              or searching for the perfect teacher — we&apos;re here.
            </p>
          </motion.div>

          <motion.div
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <Link
              href="/apply"
              className="inline-flex items-center justify-center px-8 py-4 text-base font-semibold rounded-full bg-white text-black hover:bg-[#e8e8ed] transition-all duration-300 min-w-[200px]"
            >
              I&apos;m a Teacher
            </Link>
            <Link
              href="/inquiry"
              className="inline-flex items-center justify-center px-8 py-4 text-base font-semibold rounded-full bg-[#2997ff] text-white hover:bg-[#0071e3] transition-all duration-300 min-w-[200px]"
            >
              I&apos;m Hiring
            </Link>
          </motion.div>

          <motion.p
            className="text-[#48484a] text-xs mt-8"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5 }}
          >
            No fees for teachers · Full visa support · Verified schools only
          </motion.p>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          5. FEATURED POSITIONS — Floating cards (daily rotation)
          ═══════════════════════════════════════════════════════════════════ */}
      <section className="bg-black py-28 border-t border-white/[0.06]">
        <div className="max-w-[1100px] mx-auto px-4 sm:px-6">
          <motion.div
            className="text-center mb-14"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <h2 className="text-4xl sm:text-5xl font-bold text-white tracking-tight mb-4">
              Open right now.
            </h2>
            <p className="text-[#86868b] text-lg">Featured positions updated daily.</p>
          </motion.div>

          <motion.div
            className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5"
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            {dailyJobs.map((job) => (
              <motion.div key={job.id} variants={scaleIn}>
                <Link
                  href={`/jobs?city=${encodeURIComponent(job.location.split(',')[0])}`}
                  className="block bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6
                             hover:bg-white/[0.08] hover:border-white/[0.15] transition-all duration-300
                             hover:-translate-y-1"
                >
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-xs font-mono text-[#48484a]">{job.id}</span>
                    {job.tag && (
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                        job.tag === 'HOT'
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-emerald-500/20 text-emerald-400'
                      }`}>
                        {job.tag}
                      </span>
                    )}
                  </div>
                  <h3 className="text-white font-semibold text-[15px] mb-1">{job.location}</h3>
                  <p className="text-[#86868b] text-sm mb-4">{job.type}</p>
                  <div className="text-[#2997ff] font-bold text-lg">{job.salary}</div>
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
            <Link href="/jobs" className="text-[#2997ff] font-medium text-sm hover:underline">
              View all open positions →
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          6. TESTIMONIALS — Daily rotating preview cards
          ═══════════════════════════════════════════════════════════════════ */}
      <section className="bg-[#111111] py-28 border-t border-white/[0.06]">
        <div className="max-w-[1100px] mx-auto px-4 sm:px-6">
          <motion.div
            className="text-center mb-14"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <h2 className="text-4xl sm:text-5xl font-bold text-white tracking-tight mb-4">
              Hear from our teachers.
            </h2>
            <p className="text-[#86868b] text-lg">Real stories from BRIDGE teachers around Korea.</p>
          </motion.div>

          <motion.div
            className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5"
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            {dailyTestimonials.slice(0, 3).map((t, i) => {
              const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
              return (
                <motion.div
                  key={t.name}
                  className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6"
                  variants={fadeInUp}
                >
                  <div className="flex items-center gap-3 mb-5">
                    <div
                      className="w-11 h-11 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0"
                      style={{ background: colors[i % colors.length] }}
                    >
                      {t.name.charAt(0)}
                    </div>
                    <div>
                      <div className="font-semibold text-white text-sm">{t.name}</div>
                      <div className="text-xs text-[#86868b]">{t.from} → {t.city}</div>
                    </div>
                  </div>
                  <p className="text-[#a1a1a6] text-sm leading-relaxed">
                    &ldquo;{t.quote}&rdquo;
                  </p>
                </motion.div>
              )
            })}
          </motion.div>

          <motion.div
            className="text-center mt-10"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <Link href="/community/testimonials" className="text-[#2997ff] font-medium text-sm hover:underline">
              Read more stories →
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          7. PARTNER MARQUEE — Bottom, infinite scrolling loop
          Schools & Companies we work with
          ═══════════════════════════════════════════════════════════════════ */}
      <section className="bg-black py-16 overflow-hidden border-t border-white/[0.06]">
        <div className="max-w-[980px] mx-auto px-4 sm:px-6 mb-8">
          <motion.p
            className="text-sm font-semibold text-[#636366] uppercase tracking-[0.15em] text-center"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            Schools &amp; Companies we work with
          </motion.p>
        </div>

        {/* Row 1 — left to right */}
        <div className="relative mb-4" aria-hidden="true">
          <div className="marquee-track">
            {[...PARTNER_ITEMS, ...PARTNER_ITEMS].map((name, i) => {
              const isCategory = i % PARTNER_ITEMS.length < CATEGORY_COUNT
              return (
                <span
                  key={`r1-${i}`}
                  className={`shrink-0 px-6 sm:px-8 text-base sm:text-lg font-semibold select-none whitespace-nowrap ${
                    isCategory ? 'text-[#636366]' : 'text-[#48484a]'
                  }`}
                >
                  {isCategory ? name : `· ${name}`}
                </span>
              )
            })}
          </div>
        </div>

        {/* Row 2 — right to left (reverse) */}
        <div className="relative" aria-hidden="true">
          <div className="marquee-track-reverse">
            {[...PARTNER_ITEMS, ...PARTNER_ITEMS].map((name, i) => {
              const offset = (i + Math.floor(PARTNER_ITEMS.length / 2)) % PARTNER_ITEMS.length
              const isCategory = offset < CATEGORY_COUNT
              const displayName = PARTNER_ITEMS[offset]
              return (
                <span
                  key={`r2-${i}`}
                  className={`shrink-0 px-6 sm:px-8 text-base sm:text-lg font-semibold select-none whitespace-nowrap ${
                    isCategory ? 'text-[#636366]' : 'text-[#48484a]'
                  }`}
                >
                  {isCategory ? displayName : `· ${displayName}`}
                </span>
              )
            })}
          </div>
        </div>
      </section>
    </div>
  )
}
