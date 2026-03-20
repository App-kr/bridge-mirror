import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import Link from 'next/link'
import Footer from '@/components/Footer'
import PageTracker from '@/components/PageTracker'
import './globals.css'
import './custom.css'

const inter = Inter({
  subsets: ['latin', 'latin-ext'],
  variable: '--font-inter',
  display: 'swap',
})

export const metadata: Metadata = {
  metadataBase: new URL('https://bridgejob.co.kr'),
  title: 'BRIDGE | ESL Teaching Jobs in Korea',
  description: "Korea's #1 ESL recruitment platform — 원어민 영어강사 채용 전문",
  keywords: ['원어민 강사', 'ESL Korea', 'teaching jobs Korea', 'BRIDGE 채용'],
  manifest: '/manifest.json',
  appleWebApp: { capable: true, statusBarStyle: 'default', title: 'BRIDGE' },
  openGraph: {
    title: 'BRIDGE Recruitment',
    description: 'ESL Teaching Jobs in Korea',
    url: 'https://bridgejob.co.kr',
    siteName: 'BRIDGE',
    locale: 'en_US',
    type: 'website',
    images: [{ url: '/og-image.png', width: 1200, height: 630, alt: 'BRIDGE — ESL Teaching Jobs in Korea' }],
  },
}

export const viewport: Viewport = {
  themeColor: '#ffffff',
  width: 'device-width',
  initialScale: 1,
}

const navLinks = [
  { href: '/community/about',      label: 'About us' },
  { href: '/community/korea',      label: 'Korea' },
  { href: '/community/visa',       label: 'Visa' },
  { href: '/jobs',                  label: 'Job Board' },
  { href: '/community/support',    label: 'Support' },
  { href: '/community/support_kr', label: '업무지원' },
  { href: '/community',            label: 'Community' },
]

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <head>
        <link rel="apple-touch-icon" href="/icon-192.png" />
        <link rel="preconnect" href="https://cdn.jsdelivr.net" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.css"
        />
        <script src="/register-sw.js" defer />
      </head>
      <body>
        {/* ── Navigation — Apple-style glass blur ── */}
        <nav className="nav-glass">
          <div className="max-w-[1200px] mx-auto px-4 sm:px-6 flex items-center h-11">
            {/* Left: Logo */}
            <Link href="/" className="text-[17px] font-bold text-[#1d1d1f] tracking-tight mr-auto">
              BRIDGE
            </Link>

            {/* Right: Nav + CTA */}
            <div className="hidden md:flex items-center gap-0">
              {navLinks.map((link) => (
                <Link key={link.href} href={link.href} className="nav-link">
                  {link.label}
                </Link>
              ))}
            </div>

            <div className="flex items-center gap-2 ml-3">
              <Link href="/apply" className="nav-cta">
                Apply
              </Link>
              <Link href="/inquiry" className="nav-cta">
                원어민채용의뢰
              </Link>
            </div>
          </div>
        </nav>

        {/* ── Content ── */}
        <main>
          {children}
        </main>

        {/* ── Footer ── */}
        <Footer />
        <PageTracker />
      </body>
    </html>
  )
}
