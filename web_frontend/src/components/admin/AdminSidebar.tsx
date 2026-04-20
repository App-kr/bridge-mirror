'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
import { API_URL } from '@/lib/api'
import {
  LayoutDashboard,
  Users,
  Building2,
  Video,
  MessageSquare,
  Mail,
  FileText,
  MailCheck,
  Link2,
  Image,
  Megaphone,
  Handshake,
  Settings,
  CreditCard,
  Brain,
  Table2,
  HelpCircle,
  LogOut,
  KeyRound,
  Briefcase,
  Inbox,
  Layers,
  LayoutList,
  FilePen,
  ListChecks,
  ShieldCheck,
  CalendarCheck,
  Globe,
  Activity,
} from 'lucide-react'

interface NavItem {
  href: string
  label: string
  icon: React.ReactNode
}

interface NavCategory {
  title: string
  items: NavItem[]
}

const ICON_SIZE = 17
const ADMIN_KEY_STORAGE = 'bridge_admin_key'

const NAV_CATEGORIES: NavCategory[] = [
  {
    title: '',
    items: [
      { href: '/admin', label: '대시보드', icon: <LayoutDashboard size={ICON_SIZE} /> },
    ],
  },
  {
    title: '인력 관리',
    items: [
      { href: '/admin/jobs', label: '채용공고', icon: <Briefcase size={ICON_SIZE} /> },
      { href: '/admin/sheet', label: '원어민 관리', icon: <Table2 size={ICON_SIZE} /> },
      { href: '/admin/employers', label: '구인자 관리', icon: <Building2 size={ICON_SIZE} /> },
      { href: '/admin/applications', label: '업체 관리', icon: <Layers size={ICON_SIZE} /> },
      { href: '/admin/interviews', label: '인터뷰 관리', icon: <CalendarCheck size={ICON_SIZE} /> },
      { href: '/admin/interview-setup', label: '인터뷰 세팅', icon: <Video size={ICON_SIZE} /> },
      { href: '/admin/resume-converter', label: '이력서 편집기', icon: <FilePen size={ICON_SIZE} /> },
      { href: '/admin/pipeline', label: '파이프라인 상태', icon: <Activity size={ICON_SIZE} /> },
      { href: '/admin/talent-auth', label: '게시판 접근 관리', icon: <ShieldCheck size={ICON_SIZE} /> },
    ],
  },
  {
    title: '메일 관리',
    items: [
      { href: '/admin/inbox', label: '통합 수신함', icon: <Inbox size={ICON_SIZE} /> },
      { href: '/admin/mail-logs', label: '메일 수발신 관리', icon: <MailCheck size={ICON_SIZE} /> },
      { href: '/admin/mail-send', label: '메일 발송', icon: <Mail size={ICON_SIZE} /> },
      { href: '/admin/introduce-mail', label: '소개 메일 발송', icon: <Megaphone size={ICON_SIZE} /> },
    ],
  },
  {
    title: '게시판 관리',
    items: [
      { href: '/admin/posts', label: '전체 게시물', icon: <FileText size={ICON_SIZE} /> },
      { href: '/admin/boards', label: '게시판 설정', icon: <LayoutList size={ICON_SIZE} /> },
      { href: '/admin/faq', label: 'FAQ 관리', icon: <HelpCircle size={ICON_SIZE} /> },
      { href: '/admin/guide-links', label: '링크 관리', icon: <Link2 size={ICON_SIZE} /> },
    ],
  },
  {
    title: '광고 관리',
    items: [
      { href: '/admin/banners', label: '배너 관리', icon: <Image size={ICON_SIZE} /> },
      { href: '/admin/ad-posts', label: 'AD 광고 관리', icon: <Megaphone size={ICON_SIZE} /> },
      { href: '/admin/eslcafe', label: 'ESL 관리', icon: <Globe size={ICON_SIZE} /> },
      { href: '/admin/payments', label: '결제', icon: <CreditCard size={ICON_SIZE} /> },
    ],
  },
  {
    title: '사이트 관리',
    items: [
      { href: '/admin/kakao-setup', label: '카카오 로그인 설정', icon: <KeyRound size={ICON_SIZE} /> },
      { href: '/admin/partners', label: '파트너', icon: <Handshake size={ICON_SIZE} /> },
      { href: '/admin/settings', label: '기본 설정', icon: <Settings size={ICON_SIZE} /> },
      { href: '/admin/inquiries', label: '에이전시', icon: <MessageSquare size={ICON_SIZE} /> },
      { href: '/admin/matching', label: '프로필 매칭 (AI)', icon: <Brain size={ICON_SIZE} /> },
      { href: '/admin/form-config', label: '폼 옵션 관리', icon: <ListChecks size={ICON_SIZE} /> },
    ],
  },
]

const ADMIN_EXPIRY_STORAGE = 'bridge_admin_key_expiry'

export default function AdminSidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [newCount, setNewCount] = useState(0)
  const prevCountRef = useRef(0)
  const notifPermRef = useRef<NotificationPermission>('default')

  /* ── 브라우저 알림 권한 요청 (최초 1회) ── */
  useEffect(() => {
    if (typeof window === 'undefined' || !('Notification' in window)) return
    notifPermRef.current = Notification.permission
    if (Notification.permission === 'default') {
      Notification.requestPermission().then(p => { notifPermRef.current = p })
    }
  }, [])

  /* ── 알림음 (Web Audio API — 파일 불필요) ── */
  const playNotifSound = useCallback(() => {
    try {
      const ctx = new AudioContext()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain); gain.connect(ctx.destination)
      osc.frequency.value = 880
      osc.type = 'sine'
      gain.gain.value = 0.15
      osc.start(); osc.stop(ctx.currentTime + 0.15)
      setTimeout(() => {
        const osc2 = ctx.createOscillator()
        const gain2 = ctx.createGain()
        osc2.connect(gain2); gain2.connect(ctx.destination)
        osc2.frequency.value = 1100
        osc2.type = 'sine'
        gain2.gain.value = 0.12
        osc2.start(); osc2.stop(ctx.currentTime + 0.12)
      }, 180)
    } catch { /* AudioContext 차단 시 무시 */ }
  }, [])

  /* ── 새 문의 감지 → 데스크탑 알림 + 소리 ── */
  useEffect(() => {
    if (newCount > prevCountRef.current && prevCountRef.current >= 0) {
      const added = newCount - prevCountRef.current
      if (prevCountRef.current > 0 || newCount > 0) {
        // 최초 로드(0→N)에도 알림 (prev===0 && newCount>0)
        if (notifPermRef.current === 'granted') {
          try {
            new Notification('BRIDGE 새 에이전시', {
              body: `새로운 에이전시 ${added}건이 접수되었습니다`,
              icon: '/icon.svg',
              tag: 'bridge-inquiry',
            })
          } catch { /* SW 없는 환경 fallback */ }
        }
        if (prevCountRef.current > 0) playNotifSound() // 최초 로드 시 소리 안 남
      }
    }
    prevCountRef.current = newCount
  }, [newCount, playNotifSound])

  const handleLogout = () => {
    localStorage.removeItem(ADMIN_KEY_STORAGE)
    localStorage.removeItem(ADMIN_EXPIRY_STORAGE)
    document.cookie = 'bridge_edit_mode=; path=/; max-age=0; SameSite=Strict'
    router.push('/')
  }

  const pollNewCount = useCallback(() => {
    const key = typeof window !== 'undefined' ? localStorage.getItem(ADMIN_KEY_STORAGE) : ''
    if (!key) return
    fetch(`${API_URL}/api/admin/inquiries/new-count`, {
      headers: { 'x-admin-key': key },
    })
      .then(r => r.json())
      .then(j => { if (j.success) setNewCount(j.data?.count ?? 0) })
      .catch(() => {})
  }, [])

  useEffect(() => {
    pollNewCount()
    const timer = setInterval(pollNewCount, 5000)
    return () => clearInterval(timer)
  }, [pollNewCount])

  const isActive = (href: string) => {
    if (href === '/admin') return pathname === '/admin'
    return pathname?.startsWith(href) ?? false
  }

  const sidebarContent = (
    <nav className="flex flex-col h-full">
      {/* Logo — 클릭 시 항상 /admin 으로 이동 (같은 페이지여도 동작) */}
      <div className="px-5 pt-6 pb-4">
        <button
          type="button"
          onClick={() => { router.push('/admin'); router.refresh(); setMobileOpen(false) }}
          className="block text-left cursor-pointer"
        >
          <span className="text-[17px] font-bold tracking-tight text-[#1d1d1f]">BRIDGE</span>
          <span className="text-[13px] text-[#86868b] ml-1.5 font-medium">Admin</span>
        </button>
      </div>

      {/* Nav Items */}
      <div className="flex-1 overflow-y-auto px-3 pb-2">
        {NAV_CATEGORIES.map((cat) => (
          <div key={cat.title || '_dashboard'}>
            {cat.title && (
              <div className="px-2 mb-1 mt-5 text-[12px] font-semibold uppercase tracking-wider text-zinc-400">
                {cat.title}
              </div>
            )}
            <div className="space-y-0.5">
              {cat.items.map((item) => {
                const active = isActive(item.href)
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={`
                      group flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-[14px] font-medium transition-all duration-150
                      ${active
                        ? 'bg-blue-50 text-blue-600'
                        : 'text-[#424245] hover:bg-blue-50/50 hover:text-[#1d1d1f]'
                      }
                    `}
                  >
                    {active && (
                      <span className="absolute left-0 w-[3px] h-5 bg-blue-600 rounded-r-full" />
                    )}
                    <span className={`shrink-0 ${active ? 'text-blue-600' : item.href === '/admin/inquiries' && newCount > 0 ? 'text-red-500' : 'text-zinc-400 group-hover:text-zinc-600'}`}>
                      {item.icon}
                    </span>
                    <span>{item.label}</span>
                    {item.href === '/admin/inquiries' && newCount > 0 && (
                      <span className="ml-auto shrink-0 text-[10px] font-bold text-white bg-red-500 rounded-full min-w-[18px] text-center px-1.5 py-0.5 animate-pulse leading-none">
                        {newCount}
                      </span>
                    )}
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* 하단: 로그아웃 */}
      <div className="px-3 pb-4 pt-2 border-t border-[#f0f0f2]">
        <button
          type="button"
          onClick={handleLogout}
          className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg w-full text-[14px] font-medium text-red-400 transition-colors"
          style={{ background: 'rgba(255, 59, 48, 0.06)' }}
        >
          <LogOut size={ICON_SIZE} className="shrink-0 text-red-300" />
          <span>로그아웃</span>
        </button>
      </div>
    </nav>
  )

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-[240px] shrink-0 border-r border-[#e5e5e7] bg-white h-screen sticky top-0 flex-col relative">
        {sidebarContent}
      </aside>

      {/* Mobile hamburger */}
      <div className="lg:hidden fixed top-3 left-3 z-50">
        <button
          type="button"
          onClick={() => setMobileOpen(!mobileOpen)}
          className="w-10 h-10 flex items-center justify-center rounded-xl bg-white/90 backdrop-blur-sm shadow-sm border border-[#e5e5e7] text-[#1d1d1f]"
          aria-label="Toggle menu"
        >
          {mobileOpen ? (
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M4.5 4.5L13.5 13.5M4.5 13.5L13.5 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M3 5.5H15M3 9H15M3 12.5H15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
          )}
        </button>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div
            className="lg:hidden fixed inset-0 bg-black/30 backdrop-blur-sm z-40"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="lg:hidden fixed inset-y-0 left-0 w-[280px] bg-white z-50 shadow-2xl relative">
            {sidebarContent}
          </aside>
        </>
      )}
    </>
  )
}
