'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useEditMode } from '@/components/EditModeBar'

const navLinks = [
  { href: '/community/about',      label: 'About us' },
  { href: '/community/korea',      label: 'Korea' },
  { href: '/community/visa',       label: 'Visa' },
  { href: '/jobs',                  label: 'Job Board' },
]

interface SiteSettings {
  footer_text?: string
  footer_description?: string
  contact_email?: string
}

export default function Footer() {
  const [settings, setSettings] = useState<SiteSettings>({})
  const editMode = useEditMode()

  useEffect(() => {
    fetch('/api/settings')
      .then(r => r.json())
      .then(d => {
        if (d?.data?.settings) {
          setSettings(d.data.settings)
        }
      })
      .catch(() => { /* keep defaults */ })
  }, [])

  const description = settings.footer_description || 'Korea ESL Recruitment Platform'
  const copyright = settings.footer_text || '© 2026 BRIDGE Recruitment · bridgejob.co.kr'

  return (
    <footer className="border-t border-gray-200 bg-[#f5f5f7] relative">
      {editMode && (
        <div className="absolute top-3 right-4 z-20">
          <Link
            href="/admin/settings"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-500/90 text-white text-[12px] font-semibold rounded-lg hover:bg-amber-600 transition-colors shadow-lg"
          >
            ✏️ 푸터 설정
          </Link>
        </div>
      )}
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#6e6e73]">
          <div>
            <span className="font-semibold text-[#1d1d1f]">BRIDGE</span>
            {' '}&mdash; {description}
          </div>
          <div className="flex items-center gap-4">
            {navLinks.map((l) => (
              <Link key={l.href} href={l.href} className="hover:text-[#1d1d1f] transition-colors">
                {l.label}
              </Link>
            ))}
            <span>|</span>
            <Link href="/apply" className="hover:text-[#1d1d1f] transition-colors">Apply</Link>
            <Link href="/inquiry" className="hover:text-[#1d1d1f] transition-colors">Hire</Link>
          </div>
        </div>
        <div className="text-center text-[11px] text-[#86868b] mt-6">
          {copyright}
        </div>
      </div>
    </footer>
  )
}
