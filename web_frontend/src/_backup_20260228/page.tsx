'use client'

/**
 * Homepage — Ken Burns Hero + Animated Counters + CTA sections
 * Design: Apple-inspired, full-width hero with crossfading background images
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

// ── Ken Burns hero images (Unsplash, Korea school/teaching themes) ──
const HERO_IMAGES = [
  'https://images.unsplash.com/photo-1523050854058-8df90110c7f1?w=1920&h=1080&fit=crop',
  'https://images.unsplash.com/photo-1580582932707-520aed937b7b?w=1920&h=1080&fit=crop',
  'https://images.unsplash.com/photo-1509062522246-3755977927d7?w=1920&h=1080&fit=crop',
  'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=1920&h=1080&fit=crop',
]

// ── Counter targets ──
const COUNTERS = [
  { label: 'Teachers', target: 5019, suffix: '+' },
  { label: 'Workplaces', target: 2092, suffix: '+' },
  { label: 'Countries', target: 7, suffix: '' },
  { label: 'Years', target: 10, suffix: '+' },
]

function useAnimatedCounter(target: number, duration: number = 2000, start: boolean = false) {
  const [value, setValue] = useState(0)

  useEffect(() => {
    if (!start) return
    let startTime: number | null = null
    let frame: number

    const step = (timestamp: number) => {
      if (!startTime) startTime = timestamp
      const progress = Math.min((timestamp - startTime) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3) // easeOutCubic
      setValue(Math.floor(eased * target))
      if (progress < 1) {
        frame = requestAnimationFrame(step)
      }
    }

    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [target, duration, start])

  return value
}

function formatCounter(value: number): string {
  return value.toLocaleString('en-US')
}

export default function HomePage() {
  const [currentImage, setCurrentImage] = useState(0)
  const [countersVisible, setCountersVisible] = useState(false)
  const countersRef = useRef<HTMLDivElement>(null)

  // ── Image crossfade ──
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentImage((prev) => (prev + 1) % HERO_IMAGES.length)
    }, 6000)
    return () => clearInterval(interval)
  }, [])

  // ── Intersection observer for counters ──
  useEffect(() => {
    const el = countersRef.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setCountersVisible(true) },
      { threshold: 0.3 }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const c0 = useAnimatedCounter(COUNTERS[0].target, 2000, countersVisible)
  const c1 = useAnimatedCounter(COUNTERS[1].target, 2000, countersVisible)
  const c2 = useAnimatedCounter(COUNTERS[2].target, 1500, countersVisible)
  const c3 = useAnimatedCounter(COUNTERS[3].target, 1500, countersVisible)
  const counterValues = [c0, c1, c2, c3]

  return (
    <div>
      {/* ══════════════════════════════════════════════════════════════════════
          KEN BURNS HERO — Full viewport, crossfading backgrounds
          ══════════════════════════════════════════════════════════════════════ */}
      <section className="relative h-screen min-h-[600px] max-h-[900px] overflow-hidden">
        {/* Background images with Ken Burns */}
        {HERO_IMAGES.map((src, i) => (
          <div
            key={i}
            className="absolute inset-0 transition-opacity duration-[2000ms]"
            style={{ opacity: currentImage === i ? 1 : 0 }}
          >
            <img
              src={src}
              alt=""
              className="w-full h-full object-cover animate-kenburns"
              style={{ animationDelay: `${i * 5}s` }}
            />
          </div>
        ))}

        {/* Dark overlay */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/50 via-black/40 to-black/70" />

        {/* Hero content */}
        <div className="relative z-10 flex flex-col items-center justify-center h-full text-center px-4">
          <div className="animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
            <h1 className="text-5xl sm:text-6xl md:text-7xl font-black text-white leading-[1.1] tracking-tight mb-6">
              Teach English
              <br />
              <span className="text-white/90">in Korea.</span>
            </h1>
          </div>

          <div className="animate-fade-in-up" style={{ animationDelay: '0.6s', animationFillMode: 'both' }}>
            <p className="text-lg sm:text-xl text-white/80 max-w-xl mx-auto leading-relaxed mb-10">
              Korea&apos;s trusted recruitment partner connecting qualified teachers
              with verified schools since 2016.
            </p>
          </div>

          <div className="animate-fade-in-up flex flex-col sm:flex-row gap-3" style={{ animationDelay: '1.0s', animationFillMode: 'both' }}>
            <Link href="/jobs" className="btn-fill-white">
              Browse Open Positions
            </Link>
            <Link href="/apply" className="btn-outline-white">
              Apply Now
            </Link>
          </div>

          {/* Scroll indicator */}
          <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
            <svg className="w-6 h-6 text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          ANIMATED COUNTERS
          ══════════════════════════════════════════════════════════════════════ */}
      <section ref={countersRef} className="bg-[#f5f5f7] py-20">
        <div className="max-w-[980px] mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {COUNTERS.map((c, i) => (
              <div key={c.label} className="text-center">
                <div
                  className="text-4xl sm:text-5xl font-black text-[#1d1d1f] tabular-nums"
                  style={{
                    opacity: countersVisible ? 1 : 0,
                    transform: countersVisible ? 'translateY(0)' : 'translateY(20px)',
                    transition: `all 0.6s ease-out ${i * 0.15}s`,
                  }}
                >
                  {formatCounter(counterValues[i])}{c.suffix}
                </div>
                <div
                  className="text-sm text-[#86868b] mt-2 font-medium"
                  style={{
                    opacity: countersVisible ? 1 : 0,
                    transition: `opacity 0.6s ease-out ${i * 0.15 + 0.3}s`,
                  }}
                >
                  {c.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          ABOUT BRIDGE — Parallax-style section
          ══════════════════════════════════════════════════════════════════════ */}
      <section className="py-24 bg-white">
        <div className="max-w-[980px] mx-auto px-4 sm:px-6">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-sm font-semibold text-[#86868b] uppercase tracking-wider mb-4">
                About BRIDGE
              </h2>
              <h3 className="text-3xl sm:text-4xl font-bold text-[#1d1d1f] leading-tight mb-6">
                The most trusted name in
                <br />
                ESL recruitment.
              </h3>
              <p className="text-[#424245] leading-relaxed mb-6">
                BRIDGE connects qualified English teachers from 7 countries with
                verified schools across Korea. We handle the entire process —
                from document verification to visa support and arrival assistance.
              </p>
              <p className="text-[#424245] leading-relaxed mb-8">
                With over 10 years of experience and 5,000+ successful placements,
                we&apos;re not just a recruitment agency — we&apos;re your career partner in Korea.
              </p>
              <Link href="/community/about" className="text-[#0071e3] font-medium text-sm hover:underline">
                Learn more about BRIDGE →
              </Link>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                { icon: '🎓', title: 'Verified Teachers', desc: 'Background checked & certified' },
                { icon: '🏫', title: 'Trusted Schools', desc: 'Vetted educational institutions' },
                { icon: '📋', title: 'Full Visa Support', desc: 'E-2 visa processing assistance' },
                { icon: '🏠', title: 'Housing Arranged', desc: 'Accommodation provided or assisted' },
              ].map((item) => (
                <div key={item.title} className="bg-[#f5f5f7] rounded-2xl p-5 text-center">
                  <div className="text-3xl mb-3">{item.icon}</div>
                  <div className="text-sm font-semibold text-[#1d1d1f] mb-1">{item.title}</div>
                  <div className="text-xs text-[#86868b]">{item.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          CTA — For Teachers & Schools
          ══════════════════════════════════════════════════════════════════════ */}
      <section className="bg-[#f5f5f7] py-20">
        <div className="max-w-[980px] mx-auto px-4 sm:px-6">
          <div className="grid sm:grid-cols-2 gap-6">
            {/* Teachers CTA */}
            <div className="bg-[#1d1d1f] rounded-3xl p-8 sm:p-10 text-white">
              <h3 className="text-2xl sm:text-3xl font-bold leading-tight mb-4">
                Looking for a
                <br />
                teaching job?
              </h3>
              <p className="text-white/70 text-sm leading-relaxed mb-8">
                Browse verified positions across Korea.
                Apply in under 5 minutes. No hidden fees.
              </p>
              <div className="flex flex-col sm:flex-row gap-3">
                <Link href="/jobs" className="btn-fill-white text-center">
                  Browse Jobs
                </Link>
                <Link href="/apply" className="btn-outline-white text-center">
                  Apply Now
                </Link>
              </div>
            </div>

            {/* Schools CTA */}
            <div className="bg-white rounded-3xl border border-gray-200 p-8 sm:p-10">
              <h3 className="text-2xl sm:text-3xl font-bold text-[#1d1d1f] leading-tight mb-4">
                Hiring a
                <br />
                native teacher?
              </h3>
              <p className="text-[#6e6e73] text-sm leading-relaxed mb-8">
                Tell us your requirements. We match you with
                pre-screened candidates — full visa support included.
              </p>
              <div className="flex flex-col sm:flex-row gap-3">
                <Link href="/inquiry" className="btn-primary text-center">
                  Submit Inquiry
                </Link>
                <Link href="/community/about" className="btn-secondary text-center">
                  Learn More
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          COMMUNITY BOARDS — Quick access
          ══════════════════════════════════════════════════════════════════════ */}
      <section className="py-20 bg-white">
        <div className="max-w-[980px] mx-auto px-4 sm:px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-[#1d1d1f] mb-3">Community Resources</h2>
            <p className="text-[#86868b]">Guides, tips, and information for teachers and schools.</p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { href: '/community/visa', emoji: '📋', label: 'Visa Information', desc: 'E-2 visa requirements and process' },
              { href: '/community/korea', emoji: '🇰🇷', label: 'Life in Korea', desc: 'City guides and cultural tips' },
              { href: '/community/tips', emoji: '💡', label: 'Teacher Tips', desc: 'Application and interview advice' },
              { href: '/community/support', emoji: '📄', label: 'Documents & Support', desc: 'Essential forms and guides' },
              { href: '/community/support_kr', emoji: '🏢', label: '업무지원 (KR)', desc: '학원 운영자를 위한 서류 안내' },
              { href: '/community/testimonials', emoji: '💬', label: 'Testimonials', desc: 'Stories from BRIDGE teachers' },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="group flex items-start gap-4 bg-[#f5f5f7] rounded-2xl p-5 hover:bg-[#e8e8ed] transition-colors"
              >
                <span className="text-2xl shrink-0 mt-0.5">{item.emoji}</span>
                <div>
                  <div className="text-[15px] font-semibold text-[#1d1d1f] group-hover:text-[#0071e3] transition-colors">
                    {item.label}
                  </div>
                  <div className="text-xs text-[#86868b] mt-0.5">{item.desc}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
