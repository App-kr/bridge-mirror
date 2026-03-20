'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { fadeInUp, defaultViewport } from '@/lib/animations'

const VALUES = [
  { icon: '🤝', title: 'Trust & Transparency', desc: 'We provide honest information and realistic expectations — no hidden fees, no false promises' },
  { icon: '🌏', title: 'Cultural Bridge', desc: 'Connecting international educators with Korean institutions through deep understanding of both cultures' },
  { icon: '⚡', title: 'Speed & Efficiency', desc: 'Streamlined process from application to placement — we respect your time at every step' },
  { icon: '🛡️', title: 'Full Support', desc: 'Visa guidance, contract review, relocation help, and ongoing support throughout your journey' },
]

const STATS = [
  { num: '3,000+', label: 'Registered Teachers' },
  { num: '1,000+', label: 'Job Listings' },
  { num: '1,200+', label: 'Employer Inquiries' },
  { num: '8+', label: 'Years of Experience' },
]

export default function AboutPage() {
  return (
    <main style={{ background: '#fff', minHeight: '100vh' }}>
      {/* HERO */}
      <section style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)',
        color: '#fff', padding: '80px 20px 60px', textAlign: 'center',
      }}>
        <motion.h1
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          style={{ fontSize: 'clamp(28px, 5vw, 48px)', fontWeight: 800, margin: '0 0 16px' }}
        >
          About BRIDGE
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          style={{ fontSize: 'clamp(16px, 2.5vw, 20px)', color: '#94a3b8', maxWidth: 640, margin: '0 auto' }}
        >
          Korea&rsquo;s dedicated ESL recruitment platform — connecting qualified teachers with reputable institutions since 2018
        </motion.p>
      </section>

      {/* MISSION */}
      <section style={{ maxWidth: 800, margin: '0 auto', padding: '60px 20px 40px' }}>
        <motion.div initial="hidden" whileInView="visible" viewport={defaultViewport} variants={fadeInUp}>
          <h2 style={{ fontSize: 28, fontWeight: 700, color: '#0f172a', marginBottom: 16 }}>Our Mission</h2>
          <p style={{ fontSize: 17, lineHeight: 1.8, color: '#334155' }}>
            BRIDGE was founded with a simple belief: the right teacher in the right school changes lives.
            We specialize in ESL recruitment across South Korea — from international schools and universities
            to public schools and private academies. Our team personally vets every candidate and employer
            to ensure quality matches that lead to lasting placements.
          </p>
        </motion.div>
      </section>

      {/* STATS */}
      <section style={{ background: '#f8fafc', padding: '48px 20px' }}>
        <div style={{
          maxWidth: 900, margin: '0 auto',
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 24,
        }}>
          {STATS.map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
              viewport={defaultViewport}
              transition={{ duration: 0.4, delay: i * 0.1 }}
              style={{ textAlign: 'center', padding: 24 }}
            >
              <div style={{ fontSize: 36, fontWeight: 800, color: '#1e3a5f' }}>{s.num}</div>
              <div style={{ fontSize: 14, color: '#64748b', marginTop: 4 }}>{s.label}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* VALUES */}
      <section style={{ maxWidth: 900, margin: '0 auto', padding: '60px 20px' }}>
        <motion.h2
          initial="hidden" whileInView="visible" viewport={defaultViewport} variants={fadeInUp}
          style={{ fontSize: 28, fontWeight: 700, color: '#0f172a', marginBottom: 32, textAlign: 'center' }}
        >
          What Sets Us Apart
        </motion.h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 24 }}>
          {VALUES.map((v, i) => (
            <motion.div
              key={v.title}
              initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
              viewport={defaultViewport}
              transition={{ duration: 0.4, delay: i * 0.1 }}
              style={{
                background: '#f8fafc', borderRadius: 12, padding: 28,
                border: '1px solid #e2e8f0',
              }}
            >
              <div style={{ fontSize: 32, marginBottom: 12 }}>{v.icon}</div>
              <h3 style={{ fontSize: 17, fontWeight: 700, color: '#0f172a', marginBottom: 8 }}>{v.title}</h3>
              <p style={{ fontSize: 14, lineHeight: 1.7, color: '#475569', margin: 0 }}>{v.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* TEAM */}
      <section style={{ background: '#0f172a', color: '#fff', padding: '60px 20px' }}>
        <div style={{ maxWidth: 700, margin: '0 auto', textAlign: 'center' }}>
          <motion.h2
            initial="hidden" whileInView="visible" viewport={defaultViewport} variants={fadeInUp}
            style={{ fontSize: 28, fontWeight: 700, marginBottom: 32 }}
          >
            Our Team
          </motion.h2>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 48, flexWrap: 'wrap' }}>
            {[
              { name: 'Scarlett', role: 'CEO & Founder', desc: 'Oversees all recruitment operations and employer partnerships' },
              { name: 'Violet', role: 'Operations Director', desc: 'Manages teacher screening, placement coordination, and day-to-day operations' },
            ].map((m, i) => (
              <motion.div
                key={m.name}
                initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={defaultViewport}
                transition={{ duration: 0.4, delay: i * 0.15 }}
                style={{ maxWidth: 260, textAlign: 'center' }}
              >
                <div style={{
                  width: 80, height: 80, borderRadius: '50%', margin: '0 auto 16px',
                  background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 28, fontWeight: 800, color: '#fff',
                }}>
                  {m.name[0]}
                </div>
                <h3 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 4px' }}>{m.name}</h3>
                <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 8 }}>{m.role}</div>
                <p style={{ fontSize: 14, color: '#cbd5e1', lineHeight: 1.6, margin: 0 }}>{m.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: '60px 20px', textAlign: 'center' }}>
        <motion.div initial="hidden" whileInView="visible" viewport={defaultViewport} variants={fadeInUp}>
          <h2 style={{ fontSize: 24, fontWeight: 700, color: '#0f172a', marginBottom: 12 }}>
            Ready to Start Your Journey?
          </h2>
          <p style={{ fontSize: 16, color: '#64748b', marginBottom: 28 }}>
            Whether you&rsquo;re a teacher looking for your next opportunity or an employer searching for the perfect candidate
          </p>
          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link href="/apply" style={{
              background: '#1e3a5f', color: '#fff', padding: '14px 32px', borderRadius: 8,
              fontWeight: 700, fontSize: 15, textDecoration: 'none',
            }}>
              Apply as Teacher
            </Link>
            <Link href="/inquiry" style={{
              background: '#fff', color: '#1e3a5f', padding: '14px 32px', borderRadius: 8,
              fontWeight: 700, fontSize: 15, textDecoration: 'none',
              border: '2px solid #1e3a5f',
            }}>
              Hire a Teacher
            </Link>
          </div>
        </motion.div>
      </section>
    </main>
  )
}
