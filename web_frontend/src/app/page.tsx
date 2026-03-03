'use client'

/**
 * Homepage — Apple Dark Immersive (Compact)
 * Flow: HERO → Stats + CTA (one scroll) → Info page navigation cards
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

// ── Hero background SVG components ──
function GlobeSVG() {
  return (
    <svg viewBox="0 0 320 320" fill="none" className="w-[200px] h-[200px] sm:w-[280px] sm:h-[280px] lg:w-[320px] lg:h-[320px]">
      <circle cx="160" cy="160" r="148" stroke="white" strokeWidth="0.6" />
      <ellipse cx="160" cy="160" rx="100" ry="148" stroke="white" strokeWidth="0.4" />
      <ellipse cx="160" cy="160" rx="50" ry="148" stroke="white" strokeWidth="0.4" />
      <line x1="12" y1="160" x2="308" y2="160" stroke="white" strokeWidth="0.4" />
      <ellipse cx="160" cy="80" rx="130" ry="22" stroke="white" strokeWidth="0.4" />
      <ellipse cx="160" cy="160" rx="148" ry="30" stroke="white" strokeWidth="0.3" />
      <ellipse cx="160" cy="240" rx="130" ry="22" stroke="white" strokeWidth="0.4" />
    </svg>
  )
}

function KoreaMapSVG() {
  return (
    <svg viewBox="0 0 180 360" fill="none" className="w-[120px] h-[240px] sm:w-[160px] sm:h-[320px] lg:w-[180px] lg:h-[360px]">
      {/* Simplified Korean peninsula outline */}
      <path
        d="M90,15 C95,20 105,28 110,40 C115,52 118,58 120,70 C122,82 125,88 128,95
           C132,105 130,115 125,125 C120,135 118,140 115,150 C112,160 108,170 105,180
           C102,190 100,195 98,205 C95,218 92,228 88,240 C84,252 80,260 76,270
           C72,280 70,288 68,295 C65,305 62,315 60,320 C58,328 62,332 65,335
           C70,340 75,338 78,335 C82,330 85,325 90,330 C92,335 88,345 82,350"
        stroke="white"
        strokeWidth="0.8"
        strokeLinecap="round"
      />
      {/* Jeju Island */}
      <ellipse cx="72" cy="345" rx="14" ry="6" stroke="white" strokeWidth="0.6" />
    </svg>
  )
}

function BridgeLineSVG() {
  return (
    <svg className="absolute inset-0 w-full h-full" viewBox="0 0 1200 600" fill="none" preserveAspectRatio="xMidYMid meet">
      <path
        className="hero-bridge-path"
        d="M200,320 C350,220 500,200 600,240 C700,280 850,260 1000,300"
        stroke="rgba(255,255,255,0.25)"
        strokeWidth="1"
        strokeLinecap="round"
        fill="none"
      />
      {/* Subtle dots along the path */}
      <circle cx="400" cy="235" r="2" fill="rgba(255,255,255,0.15)" className="hero-bg-fade" />
      <circle cx="600" cy="240" r="2" fill="rgba(255,255,255,0.15)" className="hero-bg-fade" />
      <circle cx="800" cy="270" r="2" fill="rgba(255,255,255,0.15)" className="hero-bg-fade" />
    </svg>
  )
}

function PlaneSVG() {
  return (
    <svg viewBox="0 0 24 24" fill="white" className="w-5 h-5 sm:w-6 sm:h-6">
      <path d="M21,16V14L13,9V3.5A1.5,1.5,0,0,0,11.5,2A1.5,1.5,0,0,0,10,3.5V9L2,14V16L10,13.5V19L8,20.5V22L11.5,21L15,22V20.5L13,19V13.5Z" />
    </svg>
  )
}

// ── Stats ──
const COUNTERS = [
  { label: 'Teachers Placed', target: 5019, suffix: '+' },
  { label: 'Partner Schools', target: 2092, suffix: '+' },
  { label: 'Countries', target: 7, suffix: '' },
  { label: 'Years Experience', target: 10, suffix: '+' },
]

// ── Info page navigation cards ──
const INFO_PAGES = [
  {
    href: '/jobs',
    title: 'Open Positions',
    desc: 'Browse teaching jobs across Korea — updated daily.',
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0" />
      </svg>
    ),
    accent: '#2997ff',
  },
  {
    href: '/apply',
    title: 'Apply as Teacher',
    desc: 'Start your teaching career in Korea — no fees, full support.',
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
      </svg>
    ),
    accent: '#30d158',
  },
  {
    href: '/inquiry',
    title: 'Hire a Teacher',
    desc: 'Find qualified ESL teachers for your school.',
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
      </svg>
    ),
    accent: '#ff9f0a',
  },
  {
    href: '/community',
    title: 'Community',
    desc: 'Visa guides, living tips, and teacher stories.',
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
      </svg>
    ),
    accent: '#bf5af2',
  },
]

// ── Partner marquee ──
const SCHOOL_TYPES = [
  'English Centres',
  'International Schools',
  'Private Schools',
  'English Villages',
  'Government Education Centres',
  'Academies',
  'Kindergartens',
  'After-School Programs',
  'Public Schools',
]

const FRANCHISE_NAMES = [
  'Chungdahm Learning', 'YBM ECC', 'Pagoda', 'Avalon English',
  'CDI / April', 'SLP', 'POLY', 'Maple Bear', 'GnB English',
  'DYB Choisun', 'Hackers', 'Wonderland', 'Haba Kids',
  'LCI Kids Club', 'Jung Chul', 'Sisa English', 'ECC Junior',
  'Reading Town', 'SDA English', 'Talktown', 'English Channel',
  'Langcon', 'JLS Language', 'YC College', 'Kids College',
  'English Moomoo', 'Tuntun English', 'Canada English',
  'Chungsol Academy', 'EiE',
]

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
  const countersRef = useRef<HTMLDivElement>(null)
  const [countersVisible, setCountersVisible] = useState(false)

  // ── Hero parallax ──
  const { scrollYProgress: heroProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  })
  const heroOpacity = useTransform(heroProgress, [0, 0.6], [1, 0])
  const heroScale = useTransform(heroProgress, [0, 0.6], [1, 0.95])
  const arrowOpacity = useTransform(heroProgress, [0, 0.15], [1, 0])

  // ── Airplane scroll animation ──
  const planeX = useTransform(heroProgress, [0, 0.5], ['5%', '80%'])
  const planeOpacity = useTransform(heroProgress, [0, 0.15, 0.45, 0.55], [0, 0.7, 0.5, 0])

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
        <div className="absolute inset-0 bg-gradient-to-b from-black via-[#0a0a0a] to-black" />

        {/* ── Background decorations (absolute, pointer-events-none) ── */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden hero-bg-fade" style={{ opacity: 0.12 }}>
          {/* Globe — left */}
          <div className="absolute left-[2%] sm:left-[5%] top-1/2 -translate-y-1/2">
            <GlobeSVG />
          </div>
          {/* Korea map — right */}
          <div className="absolute right-[4%] sm:right-[8%] top-1/2 -translate-y-[45%]">
            <KoreaMapSVG />
          </div>
          {/* Bridge line connecting globe → Korea */}
          <BridgeLineSVG />
        </div>

        {/* ── Airplane (scroll-driven) ── */}
        <motion.div
          className="absolute top-[38%] pointer-events-none z-[5] hero-plane-float"
          style={{ left: planeX, opacity: planeOpacity }}
        >
          <div className="-rotate-45">
            <PlaneSVG />
          </div>
        </motion.div>

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

        {/* Enhanced scroll indicator */}
        <motion.div
          className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-3"
          style={{ opacity: arrowOpacity }}
        >
          <span className="text-[13px] uppercase tracking-[0.25em] text-[#636366] font-semibold scroll-pulse">
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
          2. STATS + CTA — 한 장 스크롤 (통합 섹션)
          ═══════════════════════════════════════════════════════════════════ */}
      <section ref={countersRef} className="bg-black py-24 border-t border-white/[0.06]">
        <div className="max-w-[980px] mx-auto px-4 sm:px-6">
          {/* Stats */}
          <motion.div
            className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-20"
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            {COUNTERS.map((c, i) => (
              <motion.div key={c.label} className="text-center" variants={fadeInUp}>
                <div className="text-4xl sm:text-5xl font-black text-white tabular-nums tracking-tight">
                  {cv[i].toLocaleString('en-US')}{c.suffix}
                </div>
                <div className="text-sm text-[#86868b] mt-2 font-medium">{c.label}</div>
              </motion.div>
            ))}
          </motion.div>

          {/* CTA */}
          <motion.div
            className="text-center"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white tracking-tight mb-4">
              Get started today.
            </h2>
            <p className="text-[#86868b] text-lg mb-10 max-w-md mx-auto">
              Whether you&apos;re looking for your next teaching position
              or searching for the perfect teacher — we&apos;re here.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-6">
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
            </div>

            <p className="text-[#48484a] text-xs">
              No fees for teachers · Full visa support · Verified schools only
            </p>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          3. INFO PAGES — 정보 페이지 네비게이션 카드
          ═══════════════════════════════════════════════════════════════════ */}
      <section className="bg-[#111111] py-24 border-t border-white/[0.06]">
        <div className="max-w-[1100px] mx-auto px-4 sm:px-6">
          <motion.div
            className="text-center mb-14"
            variants={fadeInUp}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mb-3">
              Explore BRIDGE.
            </h2>
            <p className="text-[#86868b] text-base">Everything you need, one click away.</p>
          </motion.div>

          <motion.div
            className="grid sm:grid-cols-2 gap-5"
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
          >
            {INFO_PAGES.map((page) => (
              <motion.div key={page.href} variants={scaleIn}>
                <Link
                  href={page.href}
                  className="group block bg-white/[0.04] border border-white/[0.08] rounded-2xl p-7
                             hover:bg-white/[0.08] hover:border-white/[0.15] transition-all duration-300
                             hover:-translate-y-1"
                >
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center mb-5 transition-transform duration-300 group-hover:scale-110"
                    style={{ background: `${page.accent}20`, color: page.accent }}
                  >
                    {page.icon}
                  </div>
                  <h3 className="text-white font-semibold text-lg mb-2 tracking-tight">{page.title}</h3>
                  <p className="text-[#86868b] text-sm leading-relaxed">{page.desc}</p>
                  <span
                    className="inline-block mt-4 text-sm font-medium transition-transform duration-300 group-hover:translate-x-1"
                    style={{ color: page.accent }}
                  >
                    Explore →
                  </span>
                </Link>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          4. PARTNER MARQUEE — 하단 파트너 마키 (컴팩트)
          ═══════════════════════════════════════════════════════════════════ */}
      <section className="bg-black py-12 overflow-hidden border-t border-white/[0.06]">
        <div className="max-w-[980px] mx-auto px-4 sm:px-6 mb-6">
          <p className="text-sm font-semibold text-[#636366] uppercase tracking-[0.15em] text-center">
            Schools &amp; Companies we work with
          </p>
        </div>

        {/* Row 1 — School types */}
        <div className="relative mb-3" aria-hidden="true">
          <div className="marquee-track">
            {[...SCHOOL_TYPES, ...SCHOOL_TYPES, ...SCHOOL_TYPES].map((name, i) => (
              <span
                key={`r1-${i}`}
                className="shrink-0 px-6 sm:px-8 text-base sm:text-lg font-semibold select-none whitespace-nowrap text-[#636366]"
              >
                {name}
              </span>
            ))}
          </div>
        </div>

        {/* Row 2 — Franchise academies */}
        <div className="relative" aria-hidden="true">
          <div className="marquee-track marquee-track--slow">
            {[...FRANCHISE_NAMES, ...FRANCHISE_NAMES].map((name, i) => (
              <span
                key={`r2-${i}`}
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
