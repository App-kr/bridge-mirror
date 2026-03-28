'use client'

/**
 * /job-seekers — For Employers (구인자)
 * Recruitment solutions for Korean educational institutions
 */

import Link from 'next/link'
import { motion } from 'framer-motion'
import { fadeInUp, defaultViewport } from '@/lib/animations'

const FEATURES = [
  {
    icon: '🔍',
    title: 'Candidate Pool',
    desc: '3,000+ pre-screened international educators ready to teach',
  },
  {
    icon: '⚙️',
    title: 'Flexible Matching',
    desc: 'Post jobs and get matched with qualified candidates automatically',
  },
  {
    icon: '📊',
    title: 'Advanced Filtering',
    desc: 'Find teachers by experience, qualifications, location preferences',
  },
  {
    icon: '💬',
    title: 'Direct Communication',
    desc: 'Video interview platform built-in for seamless coordination',
  },
  {
    icon: '📋',
    title: 'Contract Support',
    desc: 'Template contracts and legal guidance included',
  },
  {
    icon: '🚀',
    title: 'Fast Placement',
    desc: 'Average 2-3 weeks from posting to signed contract',
  },
]

const SUCCESS_STATS = [
  { label: 'Institutions Hiring', value: '500+' },
  { label: 'Teachers Placed', value: '2,500+' },
  { label: 'Success Rate', value: '94%' },
  { label: 'Avg. Time to Hire', value: '21 days' },
]

const HIRING_PROCESS = [
  {
    num: '1',
    title: 'Post Your Needs',
    desc: 'Create a job posting detailing position requirements',
  },
  {
    num: '2',
    title: 'Browse Candidates',
    desc: 'Review profiles and qualifications from our vetted pool',
  },
  {
    num: '3',
    title: 'Interview',
    desc: 'Schedule and conduct interviews using our video platform',
  },
  {
    num: '4',
    title: 'Hire & Onboard',
    desc: 'Finalize contract and manage visa sponsorship coordination',
  },
]

export default function JobSeekersPage() {
  return (
    <main style={{ background: '#fff', minHeight: '100vh' }}>
      {/* HERO */}
      <section
        style={{
          background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)',
          color: '#fff',
          padding: '80px 20px 60px',
          textAlign: 'center',
        }}
      >
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          style={{
            fontSize: 'clamp(32px, 5vw, 52px)',
            fontWeight: 800,
            margin: '0 0 16px',
          }}
        >
          Recruit International Educators
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          style={{
            fontSize: 'clamp(16px, 2.5vw, 20px)',
            color: '#94a3b8',
            maxWidth: 640,
            margin: '0 auto 24px',
          }}
        >
          Connect with qualified ESL teachers in Korea. Access a pre-screened pool of 3,000+ educators ready to join your institution.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <Link
            href="/inquiry"
            style={{
              display: 'inline-block',
              background: '#f97316',
              color: '#fff',
              padding: '14px 32px',
              borderRadius: 8,
              textDecoration: 'none',
              fontSize: 16,
              fontWeight: 600,
              transition: 'all 0.3s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#ea580c'
              e.currentTarget.style.transform = 'scale(1.05)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#f97316'
              e.currentTarget.style.transform = 'scale(1)'
            }}
          >
            Post Your Job Now
          </Link>
        </motion.div>
      </section>

      {/* STATS */}
      <section style={{ background: '#f8fafc', padding: '60px 20px' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: 32,
              textAlign: 'center',
            }}
          >
            {SUCCESS_STATS.map((stat, i) => (
              <motion.div
                key={i}
                initial="hidden"
                whileInView="visible"
                viewport={defaultViewport}
                variants={{ ...fadeInUp, hidden: { opacity: 0, y: 30 } }}
                transition={{ delay: i * 0.1 }}
              >
                <div
                  style={{
                    fontSize: 40,
                    fontWeight: 800,
                    color: '#f97316',
                    marginBottom: 8,
                  }}
                >
                  {stat.value}
                </div>
                <p style={{ fontSize: 15, color: '#64748b' }}>
                  {stat.label}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURES GRID */}
      <section style={{ maxWidth: 1200, margin: '0 auto', padding: '80px 20px' }}>
        <motion.h2
          initial="hidden"
          whileInView="visible"
          viewport={defaultViewport}
          variants={fadeInUp}
          style={{
            fontSize: 36,
            fontWeight: 700,
            textAlign: 'center',
            color: '#0f172a',
            marginBottom: 48,
          }}
        >
          Why Choose BRIDGE?
        </motion.h2>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: 32,
          }}
        >
          {FEATURES.map((feature, i) => (
            <motion.div
              key={i}
              initial="hidden"
              whileInView="visible"
              viewport={defaultViewport}
              variants={{ ...fadeInUp, hidden: { opacity: 0, y: 30 } }}
              transition={{ delay: i * 0.1 }}
              style={{
                background: '#f8fafc',
                padding: 32,
                borderRadius: 12,
                border: '1px solid #e2e8f0',
              }}
            >
              <div style={{ fontSize: 40, marginBottom: 12 }}>{feature.icon}</div>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: '#0f172a', marginBottom: 8 }}>
                {feature.title}
              </h3>
              <p style={{ fontSize: 15, color: '#475569', lineHeight: 1.6 }}>
                {feature.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section
        style={{
          background: '#f8fafc',
          padding: '80px 20px',
        }}
      >
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <motion.h2
            initial="hidden"
            whileInView="visible"
            viewport={defaultViewport}
            variants={fadeInUp}
            style={{
              fontSize: 36,
              fontWeight: 700,
              textAlign: 'center',
              color: '#0f172a',
              marginBottom: 48,
            }}
          >
            Simple Hiring Process
          </motion.h2>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 24 }}>
            {HIRING_PROCESS.map((item, i) => (
              <motion.div
                key={i}
                initial="hidden"
                whileInView="visible"
                viewport={defaultViewport}
                variants={{ ...fadeInUp, hidden: { opacity: 0, y: 30 } }}
                transition={{ delay: i * 0.1 }}
                style={{
                  textAlign: 'center',
                }}
              >
                <div
                  style={{
                    width: 60,
                    height: 60,
                    background: '#f97316',
                    color: '#fff',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 24,
                    fontWeight: 700,
                    margin: '0 auto 16px',
                  }}
                >
                  {item.num}
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#0f172a', marginBottom: 8 }}>
                  {item.title}
                </h3>
                <p style={{ fontSize: 14, color: '#64748b' }}>
                  {item.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section
        style={{
          background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)',
          color: '#fff',
          padding: '80px 20px',
          textAlign: 'center',
        }}
      >
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={defaultViewport}
          transition={{ duration: 0.6 }}
          style={{
            fontSize: 'clamp(28px, 5vw, 40px)',
            fontWeight: 800,
            marginBottom: 16,
          }}
        >
          Find Your Perfect Teacher Today
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={defaultViewport}
          transition={{ duration: 0.6, delay: 0.2 }}
          style={{
            fontSize: 18,
            color: '#cbd5e1',
            marginBottom: 32,
            maxWidth: 600,
            margin: '0 auto 32px',
          }}
        >
          Join 500+ institutions already recruiting through BRIDGE
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={defaultViewport}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <Link
            href="/inquiry"
            style={{
              display: 'inline-block',
              background: '#f97316',
              color: '#fff',
              padding: '16px 40px',
              borderRadius: 8,
              textDecoration: 'none',
              fontSize: 16,
              fontWeight: 600,
              transition: 'all 0.3s',
              marginRight: 16,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#ea580c'
              e.currentTarget.style.transform = 'scale(1.05)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#f97316'
              e.currentTarget.style.transform = 'scale(1)'
            }}
          >
            Post Job Now
          </Link>
          <Link
            href="/about"
            style={{
              display: 'inline-block',
              background: 'transparent',
              color: '#fff',
              padding: '16px 40px',
              borderRadius: 8,
              border: '2px solid #fff',
              textDecoration: 'none',
              fontSize: 16,
              fontWeight: 600,
              transition: 'all 0.3s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#fff'
              e.currentTarget.style.color = '#0f172a'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.color = '#fff'
            }}
          >
            Learn More
          </Link>
        </motion.div>
      </section>
    </main>
  )
}
