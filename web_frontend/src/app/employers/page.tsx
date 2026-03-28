'use client'

/**
 * /employers — For ESL Teachers (원어민)
 * Recruitment opportunities for international educators in Korea
 */

import Link from 'next/link'
import { motion } from 'framer-motion'
import { fadeInUp, defaultViewport } from '@/lib/animations'

const BENEFITS = [
  {
    icon: '💰',
    title: 'Competitive Salary',
    desc: '2.3M - 3.5M KRW monthly + housing, flight, insurance',
  },
  {
    icon: '🏠',
    title: 'Housing Provided',
    desc: 'Free accommodation or housing allowance included',
  },
  {
    icon: '✈️',
    title: 'Flight Support',
    desc: 'Round-trip airfare covered by employer',
  },
  {
    icon: '📝',
    title: 'Visa Sponsorship',
    desc: 'Full F-2 visa support and documentation',
  },
  {
    icon: '🛡️',
    title: 'Contract Review',
    desc: 'Free legal review before signing any contract',
  },
  {
    icon: '🤝',
    title: 'Ongoing Support',
    desc: 'Dedicated support team throughout your stay',
  },
]

const STEPS = [
  {
    num: '1',
    title: 'Create Profile',
    desc: 'Complete your profile with qualifications and experience',
  },
  {
    num: '2',
    title: 'Browse Positions',
    desc: 'View current job listings from 500+ Korean institutions',
  },
  {
    num: '3',
    title: 'Apply',
    desc: 'Submit applications to positions that match your interests',
  },
  {
    num: '4',
    title: 'Interview',
    desc: 'Connect with employers via video call or in-person',
  },
  {
    num: '5',
    title: 'Offer & Visa',
    desc: 'Receive offer and begin visa sponsorship process',
  },
  {
    num: '6',
    title: 'Depart',
    desc: 'Arrive in Korea and start your new career',
  },
]

export default function EmployersPage() {
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
          International Teaching Careers in Korea
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
          Join 3,000+ international educators finding rewarding positions at leading Korean institutions
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <Link
            href="/apply"
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
            Browse Jobs Now
          </Link>
        </motion.div>
      </section>

      {/* BENEFITS GRID */}
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
          Why Teach in Korea?
        </motion.h2>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: 32,
          }}
        >
          {BENEFITS.map((benefit, i) => (
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
              <div style={{ fontSize: 40, marginBottom: 12 }}>{benefit.icon}</div>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: '#0f172a', marginBottom: 8 }}>
                {benefit.title}
              </h3>
              <p style={{ fontSize: 15, color: '#475569', lineHeight: 1.6 }}>
                {benefit.desc}
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
            How It Works
          </motion.h2>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 24 }}>
            {STEPS.map((step, i) => (
              <motion.div
                key={i}
                initial="hidden"
                whileInView="visible"
                viewport={defaultViewport}
                variants={{ ...fadeInUp, hidden: { opacity: 0, y: 30 } }}
                transition={{ delay: i * 0.1 }}
                style={{
                  textAlign: 'center',
                  position: 'relative',
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
                  {step.num}
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: '#0f172a', marginBottom: 8 }}>
                  {step.title}
                </h3>
                <p style={{ fontSize: 14, color: '#64748b' }}>
                  {step.desc}
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
          Ready to Start Your Journey?
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
          Join thousands of teachers who found their perfect fit in Korea
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={defaultViewport}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <Link
            href="/apply"
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
            Create Profile
          </Link>
          <Link
            href="/jobs"
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
            View Job Board
          </Link>
        </motion.div>
      </section>
    </main>
  )
}
