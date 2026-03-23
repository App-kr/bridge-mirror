'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useAdminAuth } from '@/hooks/useAdminAuth'
import { usePushNotification } from '@/hooks/usePushNotification'
import AdminAuth from '@/components/admin/AdminAuth'
import {
  Bell, BellOff, ChevronLeft, Download, Shield,
  Smartphone, TestTube, CheckCircle2, XCircle, Info,
} from 'lucide-react'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

export default function SettingsPage() {
  const router = useRouter()
  const { authed, adminKey, waking, login, logout } = useAdminAuth()
  const { state: pushState, error: pushError, subscribe, unsubscribe, testPush } = usePushNotification(adminKey)
  const [testResult, setTestResult] = useState<string | null>(null)
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null)
  const [isInstalled, setIsInstalled] = useState(false)

  // Detect if already installed as PWA
  useEffect(() => {
    if (typeof window === 'undefined') return
    const mq = window.matchMedia('(display-mode: standalone)')
    setIsInstalled(mq.matches || (navigator as unknown as { standalone?: boolean }).standalone === true)

    const handler = (e: Event) => {
      e.preventDefault()
      setInstallPrompt(e as BeforeInstallPromptEvent)
    }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  const handleInstall = useCallback(async () => {
    if (!installPrompt) return
    await installPrompt.prompt()
    const result = await installPrompt.userChoice
    if (result.outcome === 'accepted') {
      setIsInstalled(true)
      setInstallPrompt(null)
    }
  }, [installPrompt])

  const handleTestPush = useCallback(async () => {
    setTestResult(null)
    const sent = await testPush()
    setTestResult(sent > 0 ? `${sent}개 디바이스로 발송 완료` : '발송 실패 — 구독자 없음')
    setTimeout(() => setTestResult(null), 4000)
  }, [testPush])

  if (!authed) return <AdminAuth onLogin={login} waking={waking} />

  const pushStateLabel: Record<string, { text: string; color: string; icon: typeof Bell }> = {
    loading:      { text: '확인 중...', color: '#86868b', icon: Bell },
    unsupported:  { text: '지원 안됨', color: '#ff3b30', icon: XCircle },
    denied:       { text: '차단됨', color: '#ff3b30', icon: BellOff },
    prompt:       { text: '미설정', color: '#ff9f0a', icon: Bell },
    subscribed:   { text: '활성', color: '#34c759', icon: CheckCircle2 },
    unsubscribed: { text: '비활성', color: '#86868b', icon: BellOff },
  }

  const psl = pushStateLabel[pushState] ?? pushStateLabel.loading

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <div className="px-4 pb-8">
        {/* Header */}
        <div className="flex items-center gap-3 pt-6 pb-4">
          <button
            onClick={() => router.back()}
            className="w-8 h-8 rounded-full bg-white border border-[#e5e5e7] flex items-center justify-center"
          >
            <ChevronLeft size={18} className="text-[#1d1d1f]" />
          </button>
          <h1 className="text-xl font-bold text-[#1d1d1f]">Settings</h1>
        </div>

        {/* ── Push Notifications Section ── */}
        <div className="mb-6">
          <h2 className="text-xs font-semibold text-[#86868b] uppercase tracking-wider mb-3 px-1">
            Push Notifications
          </h2>
          <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden divide-y divide-[#f5f5f7]">

            {/* Status row */}
            <div className="flex items-center justify-between px-4 py-3.5">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ backgroundColor: `${psl.color}15` }}>
                  <psl.icon size={16} style={{ color: psl.color }} />
                </div>
                <div>
                  <p className="text-[15px] font-medium text-[#1d1d1f]">알림 상태</p>
                  <p className="text-xs" style={{ color: psl.color }}>{psl.text}</p>
                </div>
              </div>

              {/* Toggle button */}
              {(pushState === 'prompt' || pushState === 'unsubscribed') && (
                <button
                  onClick={subscribe}
                  className="px-4 py-1.5 rounded-full bg-[#0071e3] text-white text-sm font-medium active:scale-95 transition-transform"
                >
                  활성화
                </button>
              )}
              {pushState === 'subscribed' && (
                <button
                  onClick={unsubscribe}
                  className="px-4 py-1.5 rounded-full bg-[#f5f5f7] text-[#86868b] text-sm font-medium active:scale-95 transition-transform"
                >
                  해제
                </button>
              )}
            </div>

            {/* Test push */}
            {pushState === 'subscribed' && (
              <button
                onClick={handleTestPush}
                className="flex items-center gap-3 w-full px-4 py-3.5 text-left active:bg-[#f5f5f7] transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-[#eff6ff] flex items-center justify-center">
                  <TestTube size={16} className="text-[#0071e3]" />
                </div>
                <span className="text-[15px] font-medium text-[#1d1d1f]">테스트 알림 보내기</span>
              </button>
            )}

            {/* Denied info */}
            {pushState === 'denied' && (
              <div className="flex items-start gap-3 px-4 py-3.5">
                <Info size={16} className="text-[#ff9f0a] mt-0.5 shrink-0" />
                <p className="text-xs text-[#86868b]">
                  브라우저 설정에서 bridgejob.co.kr의 알림을 허용해주세요.
                  (설정 &gt; 사이트 설정 &gt; 알림)
                </p>
              </div>
            )}
          </div>

          {/* Error / result toast */}
          {(pushError || testResult) && (
            <div className={`mt-2 px-4 py-2 rounded-xl text-sm font-medium ${
              pushError ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'
            }`}>
              {pushError || testResult}
            </div>
          )}
        </div>

        {/* ── App Install Section ── */}
        <div className="mb-6">
          <h2 className="text-xs font-semibold text-[#86868b] uppercase tracking-wider mb-3 px-1">
            App
          </h2>
          <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden divide-y divide-[#f5f5f7]">
            {isInstalled ? (
              <div className="flex items-center gap-3 px-4 py-3.5">
                <div className="w-8 h-8 rounded-full bg-[#ecfdf5] flex items-center justify-center">
                  <Smartphone size={16} className="text-[#34c759]" />
                </div>
                <div>
                  <p className="text-[15px] font-medium text-[#1d1d1f]">앱 설치됨</p>
                  <p className="text-xs text-[#34c759]">홈 화면에서 바로 접근 가능</p>
                </div>
              </div>
            ) : installPrompt ? (
              <button
                onClick={handleInstall}
                className="flex items-center gap-3 w-full px-4 py-3.5 text-left active:bg-[#f5f5f7] transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-[#eff6ff] flex items-center justify-center">
                  <Download size={16} className="text-[#0071e3]" />
                </div>
                <div className="flex-1">
                  <p className="text-[15px] font-medium text-[#1d1d1f]">홈 화면에 추가</p>
                  <p className="text-xs text-[#86868b]">앱처럼 바로 실행할 수 있습니다</p>
                </div>
                <span className="px-3 py-1 rounded-full bg-[#0071e3] text-white text-xs font-medium">설치</span>
              </button>
            ) : (
              <div className="flex items-start gap-3 px-4 py-3.5">
                <div className="w-8 h-8 rounded-full bg-[#f5f5f7] flex items-center justify-center shrink-0">
                  <Download size={16} className="text-[#86868b]" />
                </div>
                <div>
                  <p className="text-[15px] font-medium text-[#1d1d1f]">홈 화면에 추가</p>
                  <p className="text-xs text-[#86868b]">
                    {/iPhone|iPad/.test(typeof navigator !== 'undefined' ? navigator.userAgent : '')
                      ? '공유 버튼 → "홈 화면에 추가"를 눌러주세요'
                      : '브라우저 메뉴에서 "홈 화면에 추가"를 선택하세요'}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── Account Section ── */}
        <div className="mb-6">
          <h2 className="text-xs font-semibold text-[#86868b] uppercase tracking-wider mb-3 px-1">
            Account
          </h2>
          <div className="bg-white rounded-2xl border border-[#e5e5e7] overflow-hidden divide-y divide-[#f5f5f7]">
            <div className="flex items-center gap-3 px-4 py-3.5">
              <div className="w-8 h-8 rounded-full bg-[#ecfdf5] flex items-center justify-center">
                <Shield size={16} className="text-[#34c759]" />
              </div>
              <div className="flex-1">
                <p className="text-[15px] font-medium text-[#1d1d1f]">로그인 상태</p>
                <p className="text-xs text-[#34c759]">인증됨</p>
              </div>
            </div>
            <button
              onClick={() => { logout(); router.push('/') }}
              className="flex items-center gap-3 w-full px-4 py-3.5 text-left active:bg-red-50 transition-colors"
            >
              <div className="w-8 h-8 rounded-full bg-red-50 flex items-center justify-center">
                <XCircle size={16} className="text-red-500" />
              </div>
              <span className="text-[15px] font-medium text-red-500">로그아웃</span>
            </button>
          </div>
        </div>

        {/* Version */}
        <p className="text-center text-xs text-[#c7c7cc] mt-8">BRIDGE Admin v2.3</p>
      </div>
    </div>
  )
}
