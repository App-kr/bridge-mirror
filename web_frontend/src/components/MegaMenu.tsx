'use client'

/**
 * MegaMenu — Apple-style dropdown + mobile hamburger.
 * layout.tsx 수정 불가이므로 DOM 이벤트로 기존 .nav-link에 hover 연동.
 * 검정 배경, 흰 텍스트, 200ms 슬라이드다운.
 */

import { useEffect, useState, useRef, useCallback } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

/* ── 드롭다운 데이터 ── */
interface SubItem { href: string; label: string; labelKr?: string }

const DROPDOWNS: Record<string, SubItem[]> = {
  '/community/about': [
    { href: '/community/about', label: 'About BRIDGE', labelKr: '회사 소개' },
    { href: '/community/about#process', label: 'How It Works', labelKr: '채용 프로세스' },
  ],
  '/community/information': [
    { href: '/community/information', label: 'Team', labelKr: '팀 소개' },
    { href: '/community/information#services', label: 'Services', labelKr: '서비스 안내' },
    { href: '/community/information#agency', label: 'About Agency', labelKr: '소개소 안내' },
  ],
  '/community/korea': [
    { href: '/community/korea', label: 'Living in Korea', labelKr: '한국 생활' },
    { href: '/community/korea?tag=culture', label: 'Korean Culture', labelKr: '한국 문화' },
    { href: '/community/korea?tag=city', label: 'City Guides', labelKr: '도시 가이드' },
  ],
  '/community/visa': [
    { href: '/community/visa', label: 'Visa Types', labelKr: '비자 종류' },
    { href: '/community/visa?tag=process', label: 'Visa Process', labelKr: '비자 절차' },
    { href: '/community/visa?tag=documents', label: 'Documents', labelKr: '필요 서류' },
  ],
  '/community/support': [
    { href: '/community/support', label: 'FAQ (Teachers)', labelKr: '강사용 FAQ' },
    { href: '/community/information', label: 'Information', labelKr: '팀·서비스 안내' },
    { href: '/inquiry', label: 'Contact Us', labelKr: '문의하기' },
  ],
  '/community/support_kr': [
    { href: '/community/support_kr', label: 'FAQ (기관용)', labelKr: '채용 FAQ' },
    { href: '/community/support_kr?tag=resources', label: '업무자료', labelKr: '채용 관련 자료' },
    { href: '/community/support_kr?tag=forms', label: '서식/양식', labelKr: '업무 서식' },
  ],
  '/community': [
    { href: '/community/testimonials', label: 'Testimonials', labelKr: '후기' },
    { href: '/community/tips', label: 'Tips', labelKr: '교사 팁' },
  ],
}

const MOBILE_LINKS = [
  { href: '/community/about', label: 'About us' },
  { href: '/community/korea', label: 'Korea' },
  { href: '/community/visa', label: 'Visa' },
  { href: '/jobs', label: 'Job Board' },
  { href: '/community/support', label: 'Support' },
  { href: '/community/support_kr', label: '업무지원' },
  { href: '/community', label: 'Community' },
]

export default function MegaMenu() {
  const [active, setActive] = useState<string | null>(null)
  const [mobileOpen, setMobileOpen] = useState(false)
  const pathname = usePathname()
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isAdminPage = pathname?.startsWith('/admin')

  // 네비게이션 시 닫기
  useEffect(() => {
    setMobileOpen(false)
    setActive(null)
  }, [pathname])

  // .nav-link 에 hover 리스너 부착 (일반 모드 전용)
  useEffect(() => {
    if (isAdminPage) return

    const links = document.querySelectorAll<HTMLAnchorElement>('.nav-link')
    const cleanups: (() => void)[] = []

    links.forEach((el) => {
      const p = el.pathname
      if (!DROPDOWNS[p]) return

      const enter = () => {
        if (timer.current) clearTimeout(timer.current)
        setActive(p)
      }
      const leave = () => {
        timer.current = setTimeout(() => setActive(null), 180)
      }

      el.addEventListener('mouseenter', enter)
      el.addEventListener('mouseleave', leave)
      cleanups.push(() => {
        el.removeEventListener('mouseenter', enter)
        el.removeEventListener('mouseleave', leave)
      })
    })

    return () => cleanups.forEach((fn) => fn())
  }, [pathname, isAdminPage])

  const panelEnter = useCallback(() => {
    if (timer.current) clearTimeout(timer.current)
  }, [])
  const panelLeave = useCallback(() => {
    timer.current = setTimeout(() => setActive(null), 150)
  }, [])


  // Desktop: Admin 버튼을 nav CTA 영역에 주입
  useEffect(() => {
    if (isAdminPage) return
    const applyLink = document.querySelector('nav.nav-glass a[href="/apply"]')
    const container = applyLink?.parentElement
    if (!container || container.querySelector('[data-admin-btn]')) return

    const link = document.createElement('a')
    link.href = '/admin'
    link.setAttribute('data-admin-btn', '1')
    link.style.cssText = 'background:#1a1a2e;color:#fff;border:1px solid rgba(255,255,255,0.2);border-radius:6px;padding:6px 14px;font-size:13px;font-weight:600;text-decoration:none;transition:background 0.2s;white-space:nowrap;'
    link.textContent = 'Admin'
    link.addEventListener('mouseenter', () => { link.style.background = '#2d2d4e' })
    link.addEventListener('mouseleave', () => { link.style.background = '#1a1a2e' })
    container.appendChild(link)

    return () => { link.remove() }
  }, [isAdminPage, pathname])

  // admin 페이지에서는 렌더링 안 함
  if (isAdminPage) return null

  const items = active ? DROPDOWNS[active] : null


  return (
    <>
      {/* ── Desktop Dropdown Panel ── */}
      {items && (
        <div
          className="mega-panel"
          onMouseEnter={panelEnter}
          onMouseLeave={panelLeave}
        >
          <div className="max-w-[1200px] mx-auto px-6 py-4 flex gap-2">
            {items.map((it) => (
              <Link
                key={it.href}
                href={it.href}
                className="mega-item"
                onClick={() => setActive(null)}
              >
                <span className="text-[13px] font-medium text-white">{it.label}</span>
                {it.labelKr && (
                  <span className="text-[11px] text-white/40 mt-0.5">{it.labelKr}</span>
                )}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* ── Mobile Hamburger ── */}
      <button
        type="button"
        className="mobile-hamburger"
        onClick={() => setMobileOpen((v) => !v)}
        aria-label="메뉴 열기"
      >
        <span className={`hb-line${mobileOpen ? ' hb-x1' : ''}`} />
        <span className={`hb-line${mobileOpen ? ' hb-hidden' : ''}`} />
        <span className={`hb-line${mobileOpen ? ' hb-x2' : ''}`} />
      </button>

      {/* ── Mobile Drawer ── */}
      {mobileOpen && (
        <>
          <div className="mobile-overlay" onClick={() => setMobileOpen(false)} />
          <nav className="mobile-drawer">
            {MOBILE_LINKS.map((l) => {
              const href = l.href
              return (
                <Link
                  key={l.href}
                  href={href}
                  className={`mobile-nav-link${pathname === l.href ? ' active' : ''}`}
                  onClick={() => setMobileOpen(false)}
                >
                  {l.label}
                </Link>
              )
            })}
            <div className="mt-4 pt-4 border-t border-gray-100 flex flex-col gap-2">
              <Link href="/apply" className="mobile-cta-primary" onClick={() => setMobileOpen(false)}>
                Apply Now
              </Link>
              <Link href="/inquiry" className="mobile-cta-outline" onClick={() => setMobileOpen(false)}>
                원어민채용의뢰
              </Link>
              <Link href="/admin" onClick={() => setMobileOpen(false)}
                style={{
                  background: '#1a1a2e', color: '#fff', border: '1px solid rgba(255,255,255,0.2)',
                  borderRadius: 6, padding: '8px 14px', fontSize: 13, fontWeight: 600,
                  textAlign: 'center', textDecoration: 'none',
                }}>
                Admin
              </Link>
            </div>
          </nav>
        </>
      )}
    </>
  )
}
